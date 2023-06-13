import pandas as pd
import altair as alt
import numpy as np

from .utils import smooth

class Throttle:
    def __init__(self, df: pd.DataFrame, **kwargs) -> None:
        if not 'Throttle' in df.columns:
            raise ValueError("Throttle column not found in dataframe")
        if not 'TimeStamp' in df.columns:
            raise ValueError("TimeStamp column not found in dataframe")
        
        self._throttle = df['Throttle']
        self._time = df['TimeStamp']
        self._smoothed_throttle = smooth(self._throttle, **kwargs)

        self._throttle_difference_to_smoothed = abs(self._throttle - self._smoothed_throttle)/100
        self.harshness = np.trapz(self._throttle_difference_to_smoothed, self._time)

    
    def chart(self):
        throttle_json = [{'throttle': st, 'time': time, 'line': 'throttle'} for st, time in zip(self._throttle, self._time)]
        throttle_json.extend([{'throttle': st, 'time': time, 'line': 'smoothed_throttle'} for st, time in zip(self._smoothed_throttle, self._time)])
        throttle_df = pd.DataFrame(throttle_json)

        return alt.Chart(pd.DataFrame(throttle_df)).mark_line().encode(
            y='throttle:Q',
            x = 'time:T',
            color='line:N'
        )
    
    def difference_chart(self):
        throttle_difference_json = [{'throttle_difference': diff, 'time': time} for diff, time in zip(self._throttle_difference_to_smoothed, self._time)]
        throttle_difference_df = pd.DataFrame(throttle_difference_json)
        
        return alt.Chart(pd.DataFrame(throttle_difference_df)).mark_area(color='orange').encode(
            y='throttle_difference:Q',
            x = 'time:T'
        )