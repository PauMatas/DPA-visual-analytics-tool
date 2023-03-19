import numpy as np
import pandas as pd
import altair as alt

from .utils import smooth

class Steering:
    def __init__(self, df: pd.DataFrame, **kwargs):
        if not 'Steering' in df.columns:
            raise ValueError("Steering column not found in dataframe")
        if not 'TimeStamp' in df.columns:
            raise ValueError("TimeStamp column not found in dataframe")
        
        self._steering = df['Steering']
        self._time = df['TimeStamp']
        self._smoothed_steering = smooth(self._steering, **kwargs)

        self._angle_difference_to_smoothed = abs(self._steering - self._smoothed_steering)
        self.smoothness = np.trapz(self._angle_difference_to_smoothed, self._time)

    
    def chart(self):
        steering_json = [{'steering': st, 'time': time, 'line': 'steering'} for st, time in zip(self._steering, self._time)]
        steering_json.extend([{'steering': st, 'time': time, 'line': 'smoothed_steering'} for st, time in zip(self._smoothed_steering, self._time)])
        steering_df = pd.DataFrame(steering_json)

        return alt.Chart(pd.DataFrame(steering_df)).mark_line().encode(
            y='steering:Q',
            x = 'time:T',
            color='line:N'
        )
    
    
    def difference_chart(self):
        steering_difference_json = [{'steering_difference': diff, 'time': time} for diff, time in zip(self._angle_difference_to_smoothed, self._time)]
        steering_difference_df = pd.DataFrame(steering_difference_json)
        
        return alt.Chart(pd.DataFrame(steering_difference_df)).mark_line().encode(
            y='steering_difference:Q',
            x = 'time:T'
        )

        




