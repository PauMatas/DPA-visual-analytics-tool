import pandas as pd
import altair as alt
import numpy as np

from .lap import Lap

class Run:
    COLUMNS = ['TimeStamp', 'Throttle', 'Steering', 'VN_ax', 'VN_ay', 'xPosition', 'yPosition', 'zPosition', 'xVelocity', 'yVelocity', 'laps', 'laptime', 'globalDelta', 'delta', 'dist1']

    def __init__(self, csv_path: str) -> None:
        self.df = pd.read_csv(csv_path)[self.COLUMNS]
        self.laps = [
            Lap(lap_df.reset_index(), number=i, driver=np.random.choice(['Rodas', 'Matas']))
            for i, (_, lap_df) in enumerate(self.df.groupby('laps'))
        ]
    
    def describe(self):
        return self.df.describe()
    
    def steering_smoothness_chart(self):
        steering_json = [
            {'smoothness': lap.steering.smoothness, 'lap': lap.number, 'laptime': lap.laptime, 'driver': lap.driver}
            for lap in self.laps
            if lap.laptime is not None
        ]
        chart = self._smoothness_chart(pd.DataFrame(steering_json))
        return chart.properties(title='Steering smoothness')
    
    def throttle_smoothness_chart(self):
        throttle_json = [
            {'smoothness': lap.throttle.smoothness, 'lap': lap.number, 'laptime': lap.laptime, 'driver': lap.driver}
            for lap in self.laps
            if lap.laptime is not None
        ]
        chart = self._smoothness_chart(pd.DataFrame(throttle_json))
        return chart.properties(title='Throttle smoothness')

    def _smoothness_chart(self, df):
        return alt.Chart(df).mark_point().encode(
            y='laptime:Q',
            x = 'smoothness:Q',
            shape='driver:N',
            tooltip=['lap', 'laptime', 'driver']
        )