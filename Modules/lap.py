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
    
    # CHARTS
    
    def gg_diagram(self, sector: int | tuple = None) -> alt.Chart:
        domain = np.max(np.abs(self.df[['VN_ax', 'VN_ay']].quantile([0.05, 0.95]).values.tolist()))
        microsectors = False
        if isinstance(sector, tuple):
            microsectors = True
            sector = list(range(sector[0], sector[-1] + 1))
        if sector is None:
            chart = alt.Chart(self.df[::25])
        else:
            chart = alt.Chart(self.df[self.df['sector'] == sector][::25]) if not microsectors else alt.Chart(self.df[self.df['microsector'].isin(sector)][::25])

        sector_title = f"- Microsector{f's {sector[0]} to {sector[-1]}' if len(sector)>1 else f' {sector[0]}'}" if microsectors else f'- Sector {sector}'

        return chart.mark_point(filled=True).encode(
            x=alt.X('VN_ax:Q', axis=alt.Axis(title='Tansversal Acceleration [m/s²]'), scale=alt.Scale(domain=[-domain, domain])),
            y=alt.Y('VN_ay:Q', axis=alt.Axis(title='Longitudinal Acceleration [m/s²]'), scale=alt.Scale(domain=[-domain, domain])),
            color=alt.Color('laps:N', scale=alt.Scale(scheme='tableau10'), legend=alt.Legend(title='Lap number', orient='top')),
            tooltip=[alt.Tooltip(field='VN_ax', type='quantitative', title='Transversal Acc.'), alt.Tooltip(field='VN_ay', type='quantitative', title='Longitudinal Acc.')]
        ).properties(
            height=350,
            title="GG Diagram"
            # title=f"GG Diagram - Circuit: {self.filename.split('_')[0]} {sector_title if sector is not None else ''}"
        )
    
    def racing_line_df(self, curve_name: str = 'middle', sector: int | tuple = None) -> pd.DataFrame:
        microsectors = False
        if isinstance(sector, tuple):
            microsectors = True
            sector = list(range(sector[0], sector[-1] + 1))
        if sector is None:
            df = pd.DataFrame({
                'x': self.df['xPosition'],
                'y': self.df['yPosition'],
            })
        elif microsectors:
            df = pd.DataFrame({
                'x': self.df[self.df['microsector'].isin(sector)]['xPosition'],
                'y': self.df[self.df['microsector'].isin(sector)]['yPosition'],
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