import numpy as np
import pandas as pd
import altair as alt
import warnings

from .steering import Steering
from .throttle import Throttle

class Lap:

    class Section:
        def __init__(self, df: pd.DataFrame, start: float, end: float) -> None:
            self.start = start
            self.end = end

            self.time = self.section_time(df)

        def section_time(self, df: pd.DataFrame) -> float:
            # TODO
            pass

    def __init__(self, df: pd.DataFrame, **kwargs) -> None:
        self.number = kwargs.get('number', -1)
        run_info = kwargs.get('info', {})
        self.filename = kwargs.get('filename', 'Unknown')
        self.driver = run_info[self.filename].get('driver', 'Unknown')

        self.df = df

        # Times
        df['TimeStamp'] -= df['TimeStamp'].min()
        self.laptime = run_info[self.filename]['laps'][str(self.number)]['laptime'] if self.number != -1 else None

        # Controls
        self.steering = Steering(df)
        self.throttle = Throttle(df)
        self.breaking_points = self.breaking_points()

        # Vector Nav
        df['dist1'] -= df['dist1'].min()

        # Lap sections
        self.set_lap_sections()

    def set_lap_sections(self) -> None:
        # Sectors
        self.sector_changing_points = self.decide_changing_points()
        self.sectors = [Lap.Section(self.df, start, end) for start, end in zip(self.sector_changing_points[:-1], self.sector_changing_points[1:])]
        # Microsectors
        self.microsector_changing_points = self.decide_changing_points(self.sector_changing_points)
        self.microsectors = [Lap.Section(self.df, start, end) for start, end in zip(self.microsector_changing_points[:-1], self.microsector_changing_points[1:])]

    def decide_changing_points(self, needed_points: list | None = None) -> list:
        # TODO
        return []

    def expected_unique(self, column: str) -> float | None:
        unique = self.df[column].unique()
        if len(unique) == 1:
            return unique[0]
        
        warnings.warn(f"Multiple {column} found for lap {self.number}")
        return None
    
    def changing_points_df(self, column: str) -> pd.DataFrame:
        previous = None
        changing_points = []

        for i, (_, row) in enumerate(self.df[column].items()):
            if previous is None or row != previous:
                changing_points.append({'time': self.df['TimeStamp'][i], column: row})
                previous = row

        return pd.DataFrame(changing_points)
    
    def breaking_points(self) -> list:
        # TODO: no breaking column in this dataset
        # previous = False
        # breaking_points = []

        # for i, (_, row) in enumerate(self.df['BPE'].items()):
        #     if previous is False and row >= 3: # 3bar?
        #         breaking_points.append(self.df['dist1'][i])
        #         previous = True
        #     elif previous is True and row < 3:
        #         previous = False
                
        # return breaking_points
        return []
    
    # CHARTS
    
    def gg_diagram(self):
        return alt.Chart(self.df).mark_point().encode(
            x='VN_ax:Q',
            y='VN_ay:Q',
            color=alt.Color('laps:N', scale=alt.Scale(scheme='tableau10')),
            tooltip=['TimeStamp', 'VN_ax', 'VN_ay']
        )
    
    def racing_line_df(self, curve_name: str = 'middle', sector: int = None, microsectors: bool = False) -> pd.DataFrame:
        if sector is None:
            df = pd.DataFrame({
                'x': self.df['xPosition'],
                'y': self.df['yPosition'],
            })
        elif microsectors:
            df = pd.DataFrame({
                'x': self.df[self.df['microsector'] == sector]['xPosition'],
                'y': self.df[self.df['microsector'] == sector]['yPosition'],
            })
        else:
            df = pd.DataFrame({
                'x': self.df[self.df['sector'] == sector]['xPosition'],
                'y': self.df[self.df['sector'] == sector]['yPosition'],
            })

        df['curve'] = curve_name
        df['index'] = df.index
        return df

    def __repr__(self) -> str:
        return f"[Lap {self.number}] -> {self.driver}"