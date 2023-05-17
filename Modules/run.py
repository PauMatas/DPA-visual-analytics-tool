import pandas as pd
import altair as alt
import numpy as np
from os.path import basename
from sklearn.neighbors import KDTree

from tilke import Circuit

from .lap import Lap
from .breaking import get_breaking_stats
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
        sum.laps = self.laps + sum.laps
        sum.lap_map = self.lap_map + [lap_map + len(self.laps) for lap_map in other.lap_map]


        if self.info == other.info:
            sum.info = self.info

        return sum


    def steering_smoothness_chart(self, laps: list[int] = None) -> alt.Chart:
        steering_json = [
            {'smoothness': lap.steering.smoothness, 'lap': lap.number, 'laptime': lap.laptime, 'driver': lap.driver}
            for lap in (self.laps if laps is None else [self.laps[i] for i in laps])
            if lap.laptime is not None
        ]
        chart = self._smoothness_chart(pd.DataFrame(steering_json))
        return chart.properties(title='Steering smoothness vs laptime')
    
    def throttle_smoothness_chart(self, laps: list[int] = None) -> alt.Chart:
        throttle_json = [
            {'smoothness': lap.throttle.smoothness, 'lap': lap.number, 'laptime': lap.laptime, 'driver': lap.driver}
            for lap in (self.laps if laps is None else [self.laps[i] for i in laps])
            if lap.laptime is not None
        ]
        chart = self._smoothness_chart(pd.DataFrame(throttle_json))
        return chart.properties(title='Throttle smoothness vs laptime')

    def _smoothness_chart(self, df) -> alt.Chart:
        return alt.Chart(df).mark_point(filled=True).encode(
            y = alt.Y('laptime:Q', axis=alt.Axis(title='Laptime [s]')),
            x = alt.X('smoothness:Q', axis=alt.Axis(title='Smoothness')),
            color = alt.Color('lap:N', scale=alt.Scale(scheme='tableau10'), legend=alt.Legend(title='Lap number')),
            shape=alt.Shape('driver:N', legend=alt.Legend(title='Driver')),
            tooltip=['lap', 'laptime', 'driver']
        )
    
    def breaking_charts(self, turns_json: list[dict], chart_sections: int = 4, laps: list = []) -> tuple[alt.Chart]:
        radars = []
        axis_names, axis_idxs, lines, mean_v, out_v, distance_before_breaking = get_breaking_stats(turns_json, [lap.number for lap in self.laps], self.df, self.lap_map, lap_idxs=laps)
        for metric, title in zip([mean_v, out_v, distance_before_breaking], ['Mean velocity [m/s]', 'Velocity at the exit of the turn [m/s]', 'Distance before breaking once in the turn [m]']):
            df = pd.DataFrame({'axis_name': axis_names, 'axis': axis_idxs, 'line': lines, 'metric': metric})
            radars.append(RadarChart(df, chart_sections).chart.properties(title=title))
        
        return tuple(radars)
    
    def laps_delta_comparison_chart(self, circuit: Circuit,  lapA: int, lapB: int, intervals: int = None, sector: int | tuple = None) -> alt.Chart:
        microsectors = False
        if isinstance(sector, tuple):
            microsectors = True
            sector = list(range(sector[0], sector[-1] + 1))

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
        covered_distance = []
        circuit_length = self.laps[lapA].df['dist1'].sum()
        for i in range(intervals):
            door = circuit.middle_curve(start + ((end - start) * (i+1)/intervals))
            Ai = lapA_kdtree.query([door])[1][0][0]
            Bi = lapB_kdtree.query([door])[1][0][0]
            if self.laps[lapA].df['microsector'][Ai] == self.laps[lapB].df['microsector'][Bi]:
                delta.append(self.laps[lapA].df['delta'][:Ai].sum() - self.laps[lapB].df['delta'][:Bi].sum())
                covered_distance.append(((start + ((end - start) * (i+1)/intervals))/circuit.middle_curve.t[-1]) * circuit_length)

        data = pd.DataFrame({
            'delta': delta,
            'dist': covered_distance,
            'color': ['lapB' if d > 0 else 'lapA' for d in delta]
        })
        domain = np.max(np.abs(data['delta'].quantile([0.05, 0.95]).values.tolist()))

        return alt.Chart(data).mark_area(fillOpacity=0.75).encode(
                x=alt.X('dist:Q', axis=alt.Axis(title='Distance covered [m]')),
                y=alt.Y('delta:Q', impute={'value': 0}, axis=alt.Axis(title='Time difference [s]'), scale=alt.Scale(domain=[-domain, domain])),
                color=alt.Color(
                    'color:N',
                    scale=alt.Scale(scheme='tableau10'),
                    legend=alt.Legend(title='Fastest lap'),
                ),
                tooltip=['delta:Q']
            ).properties(
                title=f'Lap {lapA} time - Lap {lapB} time along track',
            )
