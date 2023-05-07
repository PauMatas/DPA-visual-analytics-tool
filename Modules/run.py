import pandas as pd
import altair as alt
import numpy as np
from os.path import basename

from .lap import Lap

class Run:
    COLUMNS = ['TimeStamp', 'Throttle', 'Steering', 'VN_ax', 'VN_ay', 'xPosition', 'yPosition', 'zPosition', 'Velocity', 'laps', 'delta', 'dist1', 'BPE', 'sector', 'microsector']

    def __init__(self, csv: str | None | pd.DataFrame = None, info: dict = None, filename: str = None) -> None:
        if info is not None:
            self.info = info
        else:
            self.info = {}

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
    
    def describe(self):
        return self.df.describe()
    
    def __add__(self, other):
        sum = Run()
        sum.df = pd.concat([self.df, other.df])

        sum.laps = other.laps
        for lap in sum.laps:
            lap.number += len(self.laps)
        sum.laps = self.laps + sum.laps

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
            shape='driver:N',
            tooltip=['lap', 'laptime', 'driver']
        )
    
    def breaking_points_chart(self) -> alt.Chart:
        breaking_points = self.breaking_points()
        chart = alt.Chart(pd.DataFrame(breaking_points)).mark_line().encode(
            y='mean(breaking_point):Q',
            x='breaking zone:N',
            color='driver:N',
            tooltip=['breaking_point', 'driver']
        )
        return chart.properties(title='Breaking points')
    
    def breaking_points(self) -> list:
        # TODO: determine the braking zones and the breaking points for each lap and brake zone
        # options:
        # - clustering algorithm to determine the zones (problem: if a driver brakes two times in the same zone, it will be counted as the furthest one)
        # - determine the zones by hand
        # - idk
        return []
