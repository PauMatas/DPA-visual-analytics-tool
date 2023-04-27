from os.path import dirname, join
import sys
sys.path.append(join(dirname(__file__), '..'))

import numpy as np
import pandas as pd
import altair as alt

from tilk_e import Circuit, Spline

def spline_chart_df(spline: Spline, precision: int = 1000, showcones: bool = True, curve_name: str = "N/D") -> tuple[pd.DataFrame]:
    """Plots a given spline with it"s highlighted points and true cones

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

def circuit_chart(circuit: Circuit) -> alt.Chart:
    """Charts the circuit layout

    Arguments:
        circuit (Circuit)
    Returns:
        chart (alt.Chart) : the chart of the circuit layout
    """
    curve_options = {
        "middle": circuit.middle_curve,
        "interior": circuit.interior_curve,
        "exterior": circuit.exterior_curve,
    }
    
    lines_df = pd.DataFrame(columns=["x", "y", "curve", "index"])
    circles_df = pd.DataFrame(columns=["x", "y", "type", "curve"])
    for curve_name, curve in curve_options.items():
        if curve is not None:
            aux_lines_df, aux_circles_df = spline_chart_df(curve, curve_name=curve_name)
            lines_df = pd.concat([lines_df, aux_lines_df])
            circles_df = pd.concat([circles_df, aux_circles_df])

    chart = (
        alt.Chart(lines_df).mark_line().encode(
            x=alt.X("x", axis=None),
            y=alt.Y("y", axis=None),
            color=alt.Color("curve", legend=None),
            order="index",
        ) + 
        alt.Chart(circles_df).mark_circle().encode(
            x=alt.X("x", axis=None),
            y=alt.Y("y", axis=None),
            shape=alt.Shape("type", legend=None),
            color=alt.Color("curve", legend=None),
        )
    )
    return chart