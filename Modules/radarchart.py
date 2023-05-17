import altair as alt
import pandas as pd
import numpy as np

COLORS = [ # tableau 10
    '#4E79A7', '#F28E2B', '#E15759', '#86BCB6', '#59A14F', '#F1CE63', '#B07AA1', '#FF9D9A', '#9D7660', '#BAB0AC']

# COLORS = [ # tableau 20
#     '#4E79A7', '#A0CBE8', '#F28E2B', '#FFBE7D', '#59A14F', '#8CD17D', '#B6992D', '#F1CE63', '#499894', '#86BCB6',
#     '#E15759', '#FF9D9A', '#79706E', '#BAB0AC', '#D37295', '#FABFD2', '#B07AA1', '#D4A6C8', '#9D7660', '#D7B5A6'] 

class RadarChart:
    def __init__(self, df: pd.DataFrame, n_ticks: int, **kwargs):
        """
        Create a radar chart from a dataframe and a number of axis ticks.

        The dataframe should have the following columns:
         - axis: the id of the axis starting from 0
         - axis_name: the name of the axis
         - metric: the value of the metric
         - line: the id of the line starting from 0
        """
        self.df = df
        self.n_ticks = n_ticks
        self.width = kwargs.get('width', 250)
        self.height = kwargs.get('height', 300)

        assert(self.df.axis.min() == 0)
        self.line_min = self.df.line.min()
        self.n_axis = len(self.df['axis'].unique())
        self.n_lines = self.df['line'].unique()
        self.max_value = int(self.df.metric.max()*1.05)
        self.min_value = int(self.df.metric.min()*0.95)

        self._add_line_closing()
        self._add_axis_ticks()
        self._add_trigonometric_coordinates()
        self.df.reset_index(drop=True, inplace=True)

        self._background = self._background_chart()
        self._axis = self._axis_chart()
        self._radars = self._radars_chart()

        self.chart = (self._background + self._radars + self._axis).properties(
            width=self.width,
            height=self.height
        )

    def _add_line_closing(self):
        """
        Add a closing point to each line.
        """
        aux = self.df[self.df['axis'] == 0].copy()
        aux['axis'] = self.n_axis
        self.df = pd.concat([self.df, aux])

    def _add_axis_ticks(self):
        """
        Add axis ticks to the dataframe.
        """
        json = []
        for i in [self.min_value + (i * (self.max_value - self.min_value) / self.n_ticks) for i in range(0, self.n_ticks + 1)]:
            json.append({
                'axis': 0,
                'axis_name': self.df['axis_name'].iloc[0],
                'metric': round(i),
                'line': -1})
        self.df = pd.concat([self.df, pd.DataFrame(json)])

    def _add_trigonometric_coordinates(self):
        """
        Add trigonometric coordinates to the dataframe.
        """
        self.df['sin'] = [np.sin(((-x) * 2 * np.pi / self.n_axis) + np.pi / 2) for x in self.df.axis]
        self.df['cos'] = [np.cos(((-x) * 2 * np.pi / self.n_axis) + np.pi / 2) for x in self.df.axis]

    def _background_chart(self):
        return self._background_gray() + self._background_lines()
    
    def _background_gray(self):
        return alt.Chart(self.df).transform_filter(
            (alt.datum.line == self.line_min)
        ).transform_calculate(
            dx=(self.max_value - self.min_value) * alt.datum.cos,
            dy=(self.max_value - self.min_value) * alt.datum.sin
        ).mark_line(strokeWidth=0, fillOpacity=0.1, fill='gray').encode(
            x=alt.X("dx:Q", axis=None),
            y=alt.Y("dy:Q", axis=None),
            order="axis:Q"
        ).properties(
            width=self.width,
            height=self.height
        )
    
    def _background_lines(self):
        lines = alt.LayerChart()

        for i in [i * (self.max_value - self.min_value) / self.n_ticks for i in range(1, self.n_ticks + 1)]:
            lines += alt.Chart(self.df).transform_filter(
                (alt.datum.line == self.line_min)
            ).transform_calculate(
                dx= i * alt.datum.cos,
                dy= i * alt.datum.sin
            ).mark_line(strokeDash=[5, 5], strokeWidth=1, strokeOpacity=0.5, color='gray').encode(
                x=alt.X("dx:Q", axis=None),
                y=alt.Y("dy:Q", axis=None),
                order="axis:Q"
            ).properties(
                width=self.width,
                height=self.height
            )
            
        return lines
    
    def _axis_chart(self):
        return self._axis_lines() + self._axis_labels() + self._axis_ticks()
    
    def _axis_lines(self):
        radii = alt.LayerChart()

        for axis in range(self.n_axis):
            radii += alt.Chart(self.df).transform_filter(
                (alt.datum.line == self.line_min)
            ).transform_calculate(
                dx=(alt.datum.axis == axis) * ((self.max_value - self.min_value) * alt.datum.cos),
                dy=(alt.datum.axis == axis) * ((self.max_value - self.min_value) * alt.datum.sin)
            ).mark_line(strokeWidth=1, strokeOpacity = 0.5, color="black").encode(
                x=alt.X("dx:Q", axis=None),
                y=alt.Y("dy:Q", axis=None),
                order="axis:Q"
            ).properties(
                width=self.width,
                height=self.height
            )
        return radii

    def _axis_ticks(self):
        return alt.Chart(self.df).transform_filter(
            (alt.datum.line == -1) 
        ).transform_calculate(
            dx=(alt.datum.metric - self.min_value) * alt.datum.cos + 0.1 * (self.max_value - self.min_value),
            dy=(alt.datum.metric - self.min_value) * alt.datum.sin,
            text=alt.datum.metric
        ).mark_text(fontStyle="bold", color="black").encode(
            x=alt.X("dx:Q", axis=None),
            y=alt.Y("dy:Q", axis=None),
            order="axis:Q",
            text="metric:Q"
        ).properties(
            width=self.width,
            height=self.height
        )
    
    def _axis_labels(self):
        return alt.Chart(self.df).transform_filter(
            (alt.datum.line == self.line_min) 
        ).transform_calculate(
            dx=((self.max_value - self.min_value) * alt.datum.cos + alt.datum.cos) * 1.1,
            dy=((self.max_value - self.min_value) * alt.datum.sin + alt.datum.sin) * 1.1,
            text=alt.datum.axis
        ).mark_text(fontStyle="bold").encode(
            x=alt.X("dx:Q", axis=None),
            y=alt.Y("dy:Q", axis=None),
            order="axis:Q",
            text="axis_name"
        ).properties(
            width=self.width,
            height=self.height
        )
    
    def _radar_chart(self, line: int, color: int) -> alt.Chart:
        return alt.Chart(self.df).transform_filter(
            (alt.datum.line == line)
        ).transform_calculate(
            dx=(alt.datum.metric - self.min_value) * alt.datum.cos,
            dy=(alt.datum.metric - self.min_value) * alt.datum.sin,
        ).mark_line(strokeWidth=2, strokeOpacity=1, color=COLORS[color]).encode(
            x=alt.X("dx:Q", axis=None),
            y=alt.Y("dy:Q", axis=None),
            order="axis",
            tooltip="metric:Q"
        ).properties(
            width=self.width,
            height=self.height
        )
    
    def _radars_chart(self):
        radars = alt.layer()
        for i, line in enumerate(self.n_lines):
            radars += self._radar_chart(line, color=i)

        return radars
