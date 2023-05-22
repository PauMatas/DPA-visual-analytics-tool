import numpy as np
import pandas as pd
import altair as alt

from tilke import Circuit, Spline


def spline_chart_df(spline: Spline | np.ndarray, info: list = ['None'], precision: int = 1000, showcones: bool = True, curve_name: str = "N/D") -> tuple[pd.DataFrame]:
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
        if isinstance(spline, Spline):
            tt = np.linspace(spline.t[0], spline.t[-1], precision)
            gamma = spline(tt)
        elif isinstance(spline, np.ndarray):
            gamma = spline
        lines_df = pd.DataFrame(gamma, columns=["x", "y"])
        lines_df['index'] = lines_df.index
        lines_df['curve'] = curve_name
        sectors = []
        sector_idx = []
        for i, sector in enumerate(info):
            sectors += [sector] * (len(lines_df) // len(info))
            sector_idx += [i] * (len(lines_df) // len(info))
        sectors += [info[-1]] * (len(lines_df) - len(sectors))
        sector_idx += [i] * (len(lines_df) - len(sector_idx))
        lines_df['sector'] = sectors
        lines_df['sector_idx'] = sector_idx
        
        return lines_df

def sector_spline(spline: Spline, sector: int, microsectors: bool, precision: int = None) -> np.ndarray:
    if sector is None:
        return spline
    
    if microsectors:
        sector_start = spline.t[-1] * sector[0] / CircuitChart.N_MICROSECTORS
        sector_end = spline.t[-1] * (sector[-1]+1) / CircuitChart.N_MICROSECTORS
    else:
        sector_start = spline.t[-1] * sector / CircuitChart.N_SECTORS
        sector_end = spline.t[-1] * (sector+1) / CircuitChart.N_SECTORS
    if precision is None:
        precision = int(np.ceil(1000 * (sector_end - sector_start) / spline.t[-1]))
    
    sector = np.linspace(sector_start, sector_end, precision)
    gamma = spline(sector)
    return gamma


class CircuitChart(Circuit):
    N_SECTORS = 3
    N_MICROSECTORS = 10 * N_SECTORS

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_sectors()

    def chart(self, middle_curve_df: pd.DataFrame = None, important_points: pd.DataFrame = None, sector: int | tuple = None, info: list = ['None']) -> alt.Chart:
        """Charts the circuit layout

        Arguments:
            self (Circuit) : the object itself
            middle_curve_df (pd.DataFrame) : the dataframe containing the middle curve
            important_points (pd.DataFrame) : the dataframe containing the important points
            sector (int | tuple) : the sector or microsectors to be plotted
            info (list) : the list of the color info to be displayed
        Returns:
            chart (alt.Chart) : the chart of the circuit layout
        """

        microsectors = False
        if isinstance(sector, tuple):
            microsectors = True
            sector = list(range(sector[0], sector[-1] + 1))

        curve_options = {
            "interior": sector_spline(self.interior_curve, sector=sector, microsectors=microsectors),
            "exterior": sector_spline(self.exterior_curve, sector=sector, microsectors=microsectors),
        }
        if middle_curve_df is None:
            curve_options["middle"] = sector_spline(self.middle_curve, sector=sector, microsectors=microsectors)

        lines_df = pd.DataFrame(columns=["x", "y", "curve", "index", "sector"]) if middle_curve_df is None else middle_curve_df
        if info != ['None'] and middle_curve_df is not None:
            sectors = []
            sector_idx = []
            for i, sector in enumerate(info):
                sectors += [sector] * (len(lines_df) // len(info))
                sector_idx += [i] * (len(lines_df) // len(info))
            sectors += [info[-1]] * (len(lines_df) - len(sectors))
            sector_idx += [i] * (len(lines_df) - len(sector_idx))
            lines_df['sector'] = sectors
            lines_df['sector_idx'] = sector_idx
        for curve_name, curve in curve_options.items():
            if curve is not None:
                lines_df = pd.concat([lines_df, spline_chart_df(curve, info=info, curve_name=curve_name)])

        chart_title = "Circuit Layout" if middle_curve_df is None else "Racing Line and Track Limits"

        if info == ['None']:
            color = alt.Color("curve:N", scale=alt.Scale(
                        range=['black', 'grey', 'black', '#4E79A7', '#F28E2B'],
                        domain=['interior', 'middle', 'exterior', 'lapA', 'lapB']),
                        legend=None)
        else:
            color = alt.condition(
                        ((alt.datum.curve != "interior") & (alt.datum.curve != "exterior")),
                        alt.Color("sector:N",
                            scale=alt.Scale(range=["purple", "green", "#e1d614"], domain=["best", "personal_best", "other"]),
                            legend=alt.Legend(title="Time Info")),
                        alt.value("black")
                    )

        return alt.Chart(lines_df).mark_line().encode(
            x=alt.X("x:Q", axis=None),
            y=alt.Y("y:Q", axis=None),
            color=color,
            order="index:O",
            strokeWidth=alt.condition(
                ((alt.datum.curve == "interior") | (alt.datum.curve == "exterior")),
                alt.value(0.5),
                alt.value(1.5)),
            strokeOpacity=alt.condition(
                ((alt.datum.curve == "interior") | (alt.datum.curve == "exterior")),
                alt.value(0.5),
                alt.value(1)),
            detail=alt.Detail(["curve:N", "sector_idx:N"]),
            tooltip=alt.value(None),
        ).properties(
            title=chart_title,
        )
    
    def track_chart(self, microsectors: bool = False) -> alt.Chart:
        """Charts the circuit layout with the sectors and microsectors

        Arguments:
            self (Circuit) : the object itself
            microsectors (bool) : if true colors the microsectors instead of the sectors
        Returns:
            chart (alt.Chart) : the chart of the circuit layout with the sectors and microsectors
        """

        df = pd.DataFrame(columns=["x", "y", "sector", "index", "curve"])
        doors_json = []

        for track_name, track in {"middle": self.middle_curve}.items():
            start = track.t[0]
            end = track.t[-1]
            precision = 1000
            sectors = self.N_MICROSECTORS if microsectors else self.N_SECTORS
            curve_df = pd.DataFrame(columns=["x", "y", "sector", "index"])

            for i in range(sectors):
                sector_start = start if i == 0 else end * i/sectors
                sector_end = end * (i+1)/sectors
                sector = np.linspace(sector_start, sector_end, num=precision//sectors)
                gamma = track(sector)
                sector_df = pd.DataFrame(gamma, columns=["x", "y"])
                sector_df["index"] = sector_df.index
                sector_df["sector"] = i + 1
                curve_df = pd.concat([curve_df, sector_df])

            curve_df["curve"] = track_name
            df = pd.concat([df, curve_df])

        for track_name, track in {"interior": self.interior_curve, "exterior": self.exterior_curve}.items():
            doors = [track(track.t[-1] * (i+1)/(self.N_MICROSECTORS if microsectors else self.N_SECTORS)) for i in range((self.N_MICROSECTORS if microsectors else self.N_SECTORS))]
            doors_json += [{
                "x": door[0],
                "y": door[1],
                "sector": i + 1,
            } for i, door in enumerate(doors)]
        doors_df = pd.DataFrame(doors_json)

        return alt.Chart(df).mark_line().encode(
            x=alt.X("x", axis=None),
            y=alt.Y("y", axis=None),
            order="index",
            detail=alt.Detail(["sector:N", "curve:N"]),
            strokeWidth=alt.value(10),
            strokeOpacity=alt.value(0.5),
            color=alt.value("grey"),
            tooltip=["sector:N"],
        ) + alt.Chart(doors_df).mark_line().encode(
            x=alt.X("x", axis=None),
            y=alt.Y("y", axis=None),
            detail="sector:N",
            color=alt.value("black"),
            tooltip=alt.value(None),
        ).properties(
            title="Circuit Layout",
        )
    
    def set_sectors(self):
        """Sets the sectors of the circuit"""
        self.sector_doors = [self.middle_curve(self.middle_curve.t[-1] * (i+1)/self.N_SECTORS) for i in range(self.N_SECTORS)]
        self.microsector_doors = [self.middle_curve(self.middle_curve.t[-1] * (i+1)/self.N_MICROSECTORS) for i in range(self.N_MICROSECTORS)]

    def colored_sectors_chart(self, info: list, microsectors: bool = False) -> alt.Chart:
        """Charts the circuit layout with the sectors colored depending on the time performance

        Arguments:
            self (Circuit) : the object itself
            info (list) : the info of the sectors time performance
            microsectors (bool) : if true colors the microsectors instead of the sectors
        Returns:
            chart (alt.Chart) : the chart of the circuit layout with the sectors colored
        """

        if (not microsectors and len(info) != self.N_SECTORS) or (microsectors and len(info) != self.N_MICROSECTORS):
            raise ValueError(f"The number of {'microsectors' if microsectors else 'sectors'} info must be equal to the number {'microsectors' if microsectors else 'sectors'} of the circuit")
        
        curve_options = {
            "middle": self.middle_curve,
            # "interior": self.interior_curve,
            # "exterior": self.exterior_curve,
        }

        df = pd.DataFrame(columns=["x", "y", "sector", "index", "curve", "delta"])

        for track_name, track in curve_options.items():
            start = track.t[0]
            end = track.t[-1]
            precision = 1000
            sectors = self.N_MICROSECTORS if microsectors else self.N_SECTORS
            curve_df = pd.DataFrame(columns=["x", "y", "sector", "index"])

            for i in range(sectors):
                sector_start = start if i == 0 else end * i/sectors
                sector_end = end * (i+1)/sectors
                sector = np.linspace(sector_start, sector_end, num=precision//sectors)
                gamma = track(sector)
                sector_df = pd.DataFrame(gamma, columns=["x", "y"])
                sector_df["index"] = sector_df.index
                sector_df["sector"] = i + 1
                sector_df["delta"] = info[i]
                curve_df = pd.concat([curve_df, sector_df])

            curve_df["curve"] = track_name
            df = pd.concat([df, curve_df])

        if 'best' in df["delta"].unique().tolist() or 'personal_best' in df["delta"].unique().tolist() or 'other' in df["delta"].unique().tolist():
            color=alt.Color(
                "delta:N",
                scale=alt.Scale(range=["purple", "green", "#e1d614"], domain=["best", "personal_best", "other"]),
            )
            tooltip_labels = {'sector': 'Microsector' if microsectors else 'Sector'}
        else:
            color = alt.condition(
                alt.datum.delta != -1,
                alt.Color("delta:N", scale=alt.Scale(scheme="tableau10"), legend=alt.Legend(title=f"Lap number")),
                alt.value("grey"),
            )
            tooltip_labels = {'delta': 'LapA time-LapB time', 'sector': 'Microsector' if microsectors else 'Sector'}

        return alt.Chart(df).mark_line().encode(
            x=alt.X("x", axis=None),
            y=alt.Y("y", axis=None),
            color=color,
            order="index",
            detail=alt.Detail(["curve:N", "sector:N"]),
            strokeWidth=alt.condition(
                alt.datum.curve == "middle",
                alt.value(10),
                alt.value(1)),
            strokeOpacity=alt.value(1),
            tooltip=[alt.Tooltip(field=field, title=label) for field, label in tooltip_labels.items()],
        ).properties(
            title=f"Fastest lap per {'microsector' if microsectors else 'sector'}"
        )
    
    def turns_chart(self, turns_json: list[dict]) -> alt.Chart:
        """Charts the circuit layout with the turns highlighted

        Arguments:
            self (Circuit) : the object itself
            turns_json (list[dict]) : the info of which microsectors comprend the turns
        Returns:
            chart (alt.Chart) : the chart of the circuit layout with the turns
        """
        track_name = "middle"
        track = self.middle_curve
        legend_values = [turn["name"] for turn in turns_json]
        turns_json_queue = turns_json.copy()

        df = pd.DataFrame(columns=["x", "y", "turn", "sector", "index", "curve"])

        start = track.t[0]
        end = track.t[-1]
        precision = 1000
        curve_df = pd.DataFrame(columns=["x", "y", "turn", "sector", "index"])
        if not turns_json_queue:
            raise ValueError("There has to be at least one turn in the turns_json list")
        current_turn = turns_json_queue.pop(0)

        for i in range(self.N_MICROSECTORS):
            sector_start = start if i == 0 else end * i/self.N_MICROSECTORS
            sector_end = end * (i+1)/self.N_MICROSECTORS
            sector = np.linspace(sector_start, sector_end, num=precision//self.N_MICROSECTORS)
            gamma = track(sector)
            sector_df = pd.DataFrame(gamma, columns=["x", "y"])
            sector_df["index"] = sector_df.index
            sector_df["sector"] = i + 1
            if i + 1 >= current_turn["first_ms"] and i + 1 <= current_turn["last_ms"]:
                sector_df["turn"] = current_turn["name"]
            else:
                sector_df["turn"] = None
            if i + 1 == current_turn["last_ms"] and turns_json_queue:
                    current_turn = turns_json_queue.pop(0)
            curve_df = pd.concat([curve_df, sector_df])

        curve_df["curve"] = track_name
        df = pd.concat([df, curve_df])

        return alt.Chart(df).mark_line().encode(
            x=alt.X("x", axis=None),
            y=alt.Y("y", axis=None),
            color=alt.condition(
                alt.datum.turn != None,
                alt.Color("turn:N", legend=alt.Legend(title="Turns", values=legend_values)),
                alt.value("grey")
            ),
            order="index",
            detail=alt.Detail(["curve:N", "sector:N"]),
            tooltip=['turn:N', 'sector:N'],
            strokeWidth=alt.value(10),
            strokeOpacity=alt.value(0.5), 
        ).properties(
            title="Turns chart"
        )