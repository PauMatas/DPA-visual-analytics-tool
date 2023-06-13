import pandas as pd
import altair as alt
import numpy as np
from os.path import basename
from sklearn.neighbors import KDTree

from tilke import Circuit

from .lap import Lap
from .braking import get_braking_stats
from .radarchart import RadarChart

class Run:
    COLUMNS = ['TimeStamp', 'Throttle', 'Steering', 'VN_ax', 'VN_ay', 'xPosition', 'yPosition', 'zPosition', 'Velocity', 'laps', 'delta', 'dist1', 'BPE', 'sector', 'microsector']

    def __init__(self, csv: str | None | pd.DataFrame = None, info: dict = None, filename: str = None) -> None:
        if info is None:
            self.info = {}
        else:
            self.info = info

        if csv is not None:
            if isinstance(csv, pd.DataFrame):
                if not all([col in csv.columns for col in self.COLUMNS]):
                    raise ValueError(f'csv must contain all of the following columns: {self.COLUMNS}')
                self.df = csv[self.COLUMNS]
            if isinstance(csv, str):
                self.df = pd.read_csv(csv)[self.COLUMNS]
                filename = basename(csv)
            if filename is None:
                raise ValueError('filename must be provided if csv is not a string')
            
            self.laps = [
                Lap(lap_df.reset_index(), number=i, info=self.info, filename=filename)
                for i, (_, lap_df) in enumerate(self.df.groupby('laps'))
            ]
            self.lap_map = [0 for _ in self.laps]
    
    def describe(self):
        return self.df.describe()
    
    def __add__(self, other):
        sum = Run()
        sum.df = pd.concat([self.df, other.df])

        sum.laps = other.laps
        for lap in sum.laps:
            lap.number += len(self.laps)
            lap.df['laps'] = lap.number
        sum.laps = self.laps + sum.laps
        sum.lap_map = self.lap_map + [lap_map + len(self.laps) for lap_map in other.lap_map]


        if self.info == other.info:
            sum.info = self.info

        return sum


    def steering_harshness_chart(self, laps: list[int] = None, drivers: bool = False, scheme: str = "tableau10") -> alt.Chart:
        steering_json = [
            {'harshness': lap.steering.harshness, 'lap': lap.number, 'laptime': lap.laptime, 'driver': lap.driver}
            for lap in (self.laps if laps is None else [self.laps[i] for i in laps])
            if lap.laptime is not None
        ]
        chart = self._harshness_chart(pd.DataFrame(steering_json), drivers=drivers, scheme=scheme)
        return chart.properties(title='Steering harshness vs laptime')
    
    def throttle_harshness_chart(self, laps: list[int] = None, drivers: bool = False, scheme: str = "tableau10") -> alt.Chart:
        throttle_json = [
            {'harshness': lap.throttle.harshness, 'lap': lap.number, 'laptime': lap.laptime, 'driver': lap.driver}
            for lap in (self.laps if laps is None else [self.laps[i] for i in laps])
            if lap.laptime is not None
        ]
        chart = self._harshness_chart(pd.DataFrame(throttle_json), drivers=drivers, scheme=scheme)
        return chart.properties(title='Throttle harshness vs laptime')

    def _harshness_chart(self, df: pd.DataFrame, drivers: bool, scheme: str) -> alt.Chart:
        if drivers:
            return alt.Chart(df).mark_point(filled=True).encode(
                y = alt.Y('mean(laptime):Q', axis=alt.Axis(title='Laptime [s]'), scale=alt.Scale(zero=False)),
                x = alt.X('mean(harshness):Q', axis=alt.Axis(title='Harshness'), scale=alt.Scale(zero=False)),
                color=alt.Color('driver:N', scale=alt.Scale(scheme='tableau10'), legend=alt.Legend(title='Driver')),
                shape=alt.Shape('driver:N', legend=alt.Legend(title='Driver')),
                tooltip=['driver', alt.Tooltip('mean(laptime)', format='.3f'), 'mean(harshness)']
            )
        return alt.Chart(df).mark_point(filled=True).encode(
            y = alt.Y('laptime:Q', axis=alt.Axis(title='Laptime [s]'), scale=alt.Scale(zero=False)),
            x = alt.X('harshness:Q', axis=alt.Axis(title='Harshness'), scale=alt.Scale(zero=False)),
            color = alt.Color('lap:N', scale=alt.Scale(scheme=scheme), legend=alt.Legend(title='Lap number')),
            shape=alt.Shape('driver:N', legend=alt.Legend(title='Driver')),
            tooltip=['lap', alt.Tooltip('laptime', format='.3f'), 'driver']
        )
    
    def braking_charts(self, turns_json: list[dict], chart_sections: int = 4, laps: list = [], drivers: bool = False) -> tuple[alt.Chart]:
        radars = []
        axis_names, axis_idxs, lines, drivers_names, mean_v, out_v, distance_before_braking = get_braking_stats(turns_json, [lap.number for lap in self.laps], self.df, self.lap_map, [lap.driver for lap in self.laps], lap_idxs=laps, groupby=drivers)
        
        for metric, title in zip([mean_v, out_v], ['Mean velocity [m/s]', 'Velocity at the exit of the turn [m/s]']):
            df = pd.DataFrame({'axis_name': axis_names, 'axis': axis_idxs, 'line': lines, 'metric': metric})
            radars.append(RadarChart(df, chart_sections).chart.properties(title=title))

        distance_before_braking_df = pd.DataFrame({'turn': axis_names, 'turn_id': axis_idxs, 'lap': lines, 'distance': distance_before_braking, 'driver': drivers_names})
        color = alt.Color('lap:N', scale=alt.Scale(scheme='tableau10'), legend=None) if not drivers else alt.Color('driver:N', scale=alt.Scale(scheme='tableau10'), legend=None)
        tooltip = ['lap', 'distance'] if not drivers else ['driver', 'distance']
        radars.append(
            alt.Chart(distance_before_braking_df).mark_point(filled=True).encode(
                column=alt.Column('turn:N', sort=axis_idxs, title=None),
                y=alt.Y('distance:Q', title=None, scale=alt.Scale(zero=False)),
                color=color,
                shape=alt.Shape('driver:N', legend=None),
                tooltip=tooltip,
            ).resolve_scale(
                y='independent'
            ).properties(
                title='Distance before braking once in the turn [m]',
                width=230//len(np.unique(axis_idxs)),
                height=120,
            )
        )
        
        return tuple(radars)
    
    def laps_delta_comparison_chart(self, circuit: Circuit,  lapA: int, lapB: int, intervals: int = None, sector: int | tuple = None) -> alt.Chart:
        microsectors = False
        if isinstance(sector, tuple):
            microsectors = True
            sector = None if not sector else list(range(sector[0], sector[-1] + 1))

        if sector is None:
            positionsA = self.laps[lapA].df[['xPosition', 'yPosition']]
            positionsB = self.laps[lapB].df[['xPosition', 'yPosition']]
            start = circuit.middle_curve.t[0]
            end = circuit.middle_curve.t[-1]
            intervals = 100
        elif microsectors:
            positionsA = self.laps[lapA].df[self.laps[lapA].df['microsector'].isin(sector)][['xPosition', 'yPosition']]
            positionsB = self.laps[lapB].df[self.laps[lapB].df['microsector'].isin(sector)][['xPosition', 'yPosition']]
            start = circuit.middle_curve.t[-1] * (sector[0] - 1) / circuit.N_MICROSECTORS
            end = circuit.middle_curve.t[-1] * sector[-1] / circuit.N_MICROSECTORS
            intervals = int(np.ceil(100 * (end-start) / (circuit.middle_curve.t[-1] - circuit.middle_curve.t[0])))
        else:
            positionsA = self.laps[lapA].df[self.laps[lapA].df['sector'] == sector][['xPosition', 'yPosition']]
            positionsB = self.laps[lapB].df[self.laps[lapB].df['sector'] == sector][['xPosition', 'yPosition']]
            start = circuit.middle_curve.t[-1] * (sector - 1) / circuit.N_SECTORS
            end = circuit.middle_curve.t[-1] * sector / circuit.N_SECTORS
            intervals = int(np.ceil(100 * (end-start) / (circuit.middle_curve.t[-1] - circuit.middle_curve.t[0])))

        lapA_kdtree = KDTree(positionsA)
        lapB_kdtree = KDTree(positionsB)

        delta = []
        color = []
        covered_distance = []
        circuit_length = self.laps[lapA].df['dist1'].sum()
        for i in range(intervals):
            door = circuit.middle_curve(start + ((end - start) * (i+1)/intervals))
            Ai = lapA_kdtree.query([door])[1][0][0]
            Bi = lapB_kdtree.query([door])[1][0][0]
            if self.laps[lapA].df['microsector'][Ai] == self.laps[lapB].df['microsector'][Bi]:
                delta.append(self.laps[lapA].df['delta'][:Ai].sum() - self.laps[lapB].df['delta'][:Bi].sum())
                color.append(-1 if delta[-1] == 0 else (lapA if delta[-1] < 0 else lapB))
                covered_distance.append(((start + ((end - start) * (i+1)/intervals))/circuit.middle_curve.t[-1]) * circuit_length)

        data = pd.DataFrame({
            'delta': delta,
            'dist': covered_distance,
            'color': color
        })
        domain = np.max(np.abs(data['delta'].quantile([0.05, 0.95]).values.tolist()))

        rulers_chart = self._laps_delta_comparison_rulers_chart(circuit, lapA, lapB, sector, microsectors, domain)

        return (alt.Chart(data).mark_area(fillOpacity=0.75).encode(
                x=alt.X('dist:Q', axis=alt.Axis(title='Distance covered [m]')),
                y=alt.Y('delta:Q', impute={'value': 0}, axis=alt.Axis(title='Time difference [s]'), scale=alt.Scale(domain=[-domain, domain])),
                color=alt.condition(
                    alt.datum.color != -1,
                    alt.Color(
                        'color:N',
                        scale=alt.Scale(
                            range=['#4E79A7', '#F28E2B'],
                            domain=[lapA, lapB]),
                        legend=alt.Legend(title='Lap number', orient='top')),
                    alt.ColorValue('grey'),
                ),
                tooltip=[alt.Tooltip('delta:Q', format='.3f')]
            ) + rulers_chart).properties(
                title=f'Time difference along track (lap {lapA} - lap {lapB})',
            )

    def _laps_delta_comparison_rulers_chart(self, circuit: Circuit, lapA: int, lapB: int, sector: None|int|list, microsectors: bool, domain: float) -> alt.Chart:
        circuit_length = self.laps[lapA].df['dist1'].sum()
        
        if sector is None:
            start = circuit.middle_curve.t[0]
            end = circuit.middle_curve.t[-1]
            intervals = circuit.N_MICROSECTORS if microsectors else circuit.N_SECTORS
            sector = [0, 1, 2]
        elif microsectors:
            start = circuit.middle_curve.t[-1] * (sector[0] - 1) / circuit.N_MICROSECTORS
            end = circuit.middle_curve.t[-1] * sector[-1] / circuit.N_MICROSECTORS
            intervals = len(sector)
        else:
            start = circuit.middle_curve.t[-1] * (sector - 1) / circuit.N_SECTORS
            end = circuit.middle_curve.t[-1] * sector / circuit.N_SECTORS
            intervals = 1
            sector = [sector]

        if 1 < intervals <= 10:
            rulers = [((start + ((end - start) * (i+1)/intervals))/circuit.middle_curve.t[-1]) * circuit_length for i in range(intervals)]
        else:
            rulers = []
            sector = []

        return alt.Chart(pd.DataFrame({'x': rulers})).mark_rule(strokeDash=[5, 5], strokeOpacity=0.5).encode(
            x='x:Q',
            tooltip=alt.value(None)
        ) + alt.Chart(pd.DataFrame({'x': [r - 3 for r in rulers], 'y': [domain] * len(rulers), 'sector': sector})).mark_text().encode(
            x='x:Q',
            y='y:Q',
            text='sector:N',
            tooltip=alt.value(None)
        )
            
