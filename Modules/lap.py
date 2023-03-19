import numpy as np
import pandas as pd
import altair as alt
import warnings

from .steering import Steering
from .throttle import Throttle

class Lap:
    def __init__(self, df: pd.DataFrame, **kwargs) -> None:
        self.number = kwargs.get('number', -1)
        self.driver = kwargs.get('driver', 'Unknown')

        self.df = df
        self.laptime = self.laptime()
        self.steering = Steering(df)
        self.throttle = Throttle(df)

    def laptime(self) -> float | None:
        unique = self.df['laptime'].unique()
        if len(unique) == 1:
            return unique[0]
        
        warnings.warn(f"Multiple laptimes found for lap {self.number}")
        return None

    def __repr__(self) -> str:
        return f"[Lap {self.number}] {self.laptime}s -> {self.driver}"