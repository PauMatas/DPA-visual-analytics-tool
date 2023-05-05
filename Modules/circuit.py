import numpy as np
import pandas as pd
import altair as alt

from tilke import Circuit, Spline


def spline_chart_df(spline: Spline, precision: int = 1000, showcones: bool = True, curve_name: str = "N/D") -> tuple[pd.DataFrame]:
        """Plots a given spline with it's highlighted points and true cones

        Arguments:
            precision (int) the precision to gen the points in eval interval
                Default is 1000
            showcones (bool) if true shows the true cones
                Default is True
            curve_name (str) the name of the curve
                Default is "N/D"
        Returns:
            pd.DataFrame : dataframe containing the curve
            pd.DataFrame : dataframe containing the cones
        """
        tt = np.linspace(spline.t[0], spline.t[-1], precision)
        gamma = spline(tt)
        lines_df = pd.DataFrame(gamma, columns=["x", "y"])
        lines_df['index'] = lines_df.index
        lines_df['curve'] = curve_name

        cones_df = pd.DataFrame(columns=["x", "y", "type", "curve"])
        points_df = pd.DataFrame(columns=["x", "y", "type", "curve"])
        if len(spline.true_cones) > 0 and showcones:
            hc = np.array([spline(c) for c in spline.true_cones])
            cones_df = pd.DataFrame(hc, columns=["x", "y"])
            cones_df['type'] = 'cone'
            cones_df['curve'] = curve_name
            
        if len(spline.highlighted_points) > 0:
            hp = np.array([spline(t) for t in spline.highlighted_points])
            points_df = pd.DataFrame(hp, columns=["x", "y"])
            points_df['type'] = 'point'
            points_df['curve'] = curve_name

        circles_df = pd.concat([cones_df, points_df])
        
        return lines_df, circles_df


class CircuitChart(Circuit):
    N_SECTORS = 3
    N_MICROSECTORS = 10 * N_SECTORS

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_sectors()

    def chart(self, middle_curve_df: pd.DataFrame = None, important_points: pd.DataFrame = None) -> alt.Chart:
        """Charts the circuit layout

        Arguments:
            self (Circuit) : the object itself
            middle_curve_df (pd.DataFrame) : the dataframe containing the middle curve
        Returns:
            chart (alt.Chart) : the chart of the circuit layout
        """
        curve_options = {
            "interior": self.interior_curve,
            "exterior": self.exterior_curve,
        }
        if middle_curve_df is None:
            curve_options["middle"] = self.middle_curve

        lines_df = pd.DataFrame(columns=["x", "y", "curve", "index"]) if middle_curve_df is None else middle_curve_df
        circles_df = pd.DataFrame(columns=["x", "y", "type", "curve"]) if important_points is None else important_points
        for curve_name, curve in curve_options.items():
            if curve is not None:
                aux_lines_df, aux_circles_df = spline_chart_df(curve, curve_name=curve_name)
                lines_df = pd.concat([lines_df, aux_lines_df])
                circles_df = pd.concat([circles_df, aux_circles_df])

        chart = (
            alt.Chart(lines_df).mark_line().encode(
                x=alt.X("x:Q", axis=None),
                y=alt.Y("y:Q", axis=None),
                color=alt.Color("curve:N", legend=None),
                order="index:O",
            ) + 
            alt.Chart(circles_df).mark_circle().encode(
                x=alt.X("x:Q", axis=None),
                y=alt.Y("y:Q", axis=None),
                shape=alt.Shape("type:N", legend=None),
                color=alt.Color("curve:N", legend=None),
            )
        )
        return chart
    
    def set_sectors(self):
        """Sets the sectors of the circuit"""
        self.sector_doors = [self.middle_curve(self.middle_curve.t[-1] * (i+1)/self.N_SECTORS) for i in range(self.N_SECTORS)]
        self.microsector_doors = [self.middle_curve(self.middle_curve.t[-1] * (i+1)/self.N_MICROSECTORS) for i in range(self.N_MICROSECTORS)]
