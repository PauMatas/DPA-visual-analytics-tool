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
        return chart.properties(title='Steering smoothness')
    
    def throttle_smoothness_chart(self, laps: list[int] = None) -> alt.Chart:
        throttle_json = [
            {'smoothness': lap.throttle.smoothness, 'lap': lap.number, 'laptime': lap.laptime, 'driver': lap.driver}
            for lap in (self.laps if laps is None else [self.laps[i] for i in laps])
            if lap.laptime is not None
        ]
        chart = self._smoothness_chart(pd.DataFrame(throttle_json))
        return chart.properties(title='Throttle smoothness')

    def _smoothness_chart(self, df) -> alt.Chart:
        return alt.Chart(df).mark_point().encode(
            y='laptime:Q',
            x = 'smoothness:Q',
            color = alt.Color('lap:N', scale=alt.Scale(scheme='tableau10')),
            shape='driver:N',
            tooltip=['lap', 'laptime', 'driver']
        )
    
    def breaking_charts(self, turns_json: list[dict], chart_sections: int = 4, laps: list = []) -> tuple[alt.Chart]:
        radars = []
        axis_names, axis_idxs, lines, mean_v, out_v, distance_before_breaking = get_breaking_stats(turns_json, [lap.number for lap in self.laps], self.df, self.lap_map, lap_idxs=laps)
        for metric in [mean_v, out_v, distance_before_breaking]:
            df = pd.DataFrame({'axis_name': axis_names, 'axis': axis_idxs, 'line': lines, 'metric': metric})
            radars.append(RadarChart(df, chart_sections).chart)
        
        return tuple(radars)
    
    def laps_delta_comparison_chart(self, circuit: Circuit,  lapA: int, lapB: int, intervals: int = 100) -> alt.Chart:
        lapA_kdtree = KDTree(self.laps[lapA].df[['xPosition', 'yPosition']])
        lapB_kdtree = KDTree(self.laps[lapB].df[['xPosition', 'yPosition']])

        delta = []
        for i in range(intervals):
            door = circuit.middle_curve(circuit.middle_curve.t[-1] * (i+1)/intervals)
            Ai = lapA_kdtree.query([door])[1][0][0]
            Bi = lapB_kdtree.query([door])[1][0][0]
            delta.append(self.laps[lapA].df['delta'][:Ai].sum() - self.laps[lapB].df['delta'][:Bi].sum())
        
        print(delta)

        data = pd.DataFrame({
            'delta': delta,
            'bin': list(range(intervals)),
            'color': ['lapA' if d > 0 else 'lapB' for d in delta]
        })

        print(data)

        return alt.Chart(data).mark_bar().encode(
            x=alt.X('delta:Q'),
            y=alt.Y('bin:N', axis=None),
            color=alt.condition(
                alt.datum.delta != 0,
                alt.Color('color:N', legend=None, scale=alt.Scale(scheme='tableau10')),
                alt.value('yellow')
            ),
            order='bin:Q',
            tooltip=['delta:Q']
        ).properties(
            height=500,
            title=f'Lap {lapA} - Lap {lapB} delta'
        )
