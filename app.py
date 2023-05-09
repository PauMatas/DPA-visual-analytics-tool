import streamlit as st
import pandas as pd
import altair as alt
import numpy as np
import json
from os import listdir
from os.path import dirname, abspath, join, isfile
import vegafusion as vf
vf.enable()

from Modules import Run, compute_sectors_deltas, compute_sectors_comparison
from Modules.circuit import CircuitChart
alt.data_transformers.disable_max_rows()


# ---------- DATA LOADING ----------
with open(join(dirname(abspath(__file__)), 'data', 'info.json'), 'r') as f:
    INFO = json.load(f)
RUNS = list(INFO.keys())
RUN_OBJECTS_DICT = {}

for run in RUNS:
    run_object = None
    for f in listdir(join(dirname(abspath(__file__)), 'data', run)):
        if isfile(join(dirname(abspath(__file__)), 'data', run, f)) and f.endswith('.csv'):
            new_run_object = Run(join(dirname(abspath(__file__)), 'data', run, f), INFO[run])
            run_object = new_run_object if run_object is None else run_object + new_run_object

    RUN_OBJECTS_DICT[run] = run_object

# ---------- APP SETUP ----------
st.set_page_config(
    page_title="DPA Visualization Tool",
    page_icon="🏎",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------- HEADER ----------
st.title('DPA Visualization Tool Header')

# ---------- SELECTORS ----------
selector_panel = st.container()
run_panel = st.container()
lap_panel = st.container()

with selector_panel:
    columns = st.columns([2,1,1])
    with columns[0]:
        run_selector = st.selectbox(
            'Select run',
            RUNS,
            index=0
        )

    with columns[1]:
        lapA_selector = st.selectbox(
            label = 'Select lap A',
            options = ['<select>'] + list(range(len(RUN_OBJECTS_DICT[run_selector].laps))),
            format_func = lambda x: f"Lap {x} [{RUN_OBJECTS_DICT[run_selector].laps[x].driver}]" if x != '<select>' else x,
            index=0
        )
    
    with columns[2]:
        lapB_options = set(range(len(RUN_OBJECTS_DICT[run_selector].laps))) - (set([int(lapA_selector)]) if lapA_selector != '<select>' else set())
        lapB_options = ['<select>'] + list(lapB_options)
        lapB_selector = st.selectbox(
            'Select lap B',
            options = lapB_options,
            format_func = lambda x: f"Lap {x} [{RUN_OBJECTS_DICT[run_selector].laps[x].driver}]" if x != '<select>' else x,
            index=0,
            disabled = True if lapA_selector == '<select>' else False
        )
    
# ---------- RUN PANEL ----------
try:
    with open(join(dirname(abspath(__file__)), 'data', run_selector, 'turns.json'), 'r') as f:
        turns_json = json.load(f)
except FileNotFoundError:
    turns_json = None

with run_panel:
    radars_panel, smoothness_panel = st.columns(2)
    with radars_panel:
        if lapA_selector == '<select>':
            mean_v_chart, out_v_chart, breaking_point_chart = RUN_OBJECTS_DICT[run_selector].breaking_charts(turns_json)
        else:
            lap_numbers = [int(lapA_selector), int(lapB_selector)] if lapB_selector != '<select>' else [int(lapA_selector)]
            mean_v_chart, out_v_chart, breaking_point_chart = RUN_OBJECTS_DICT[run_selector].breaking_charts(turns_json, laps=lap_numbers)
        
        columns = st.columns(2)
        with columns[0]:
            st.write('Average Speed per turn')
            st.altair_chart(mean_v_chart)
        
        with columns[1]:
            st.write('Speed at the end of the turn')
            st.altair_chart(out_v_chart)

        # breaking point chart centered in the middle of the container
        _, column, _ = st.columns([1,3,1])
        with column:
            st.write('Breaking point')
            st.altair_chart(breaking_point_chart)

    with smoothness_panel:
        if lapA_selector == '<select>':
            throttle_smoothness_chart = RUN_OBJECTS_DICT[run_selector].throttle_smoothness_chart()
            steering_smoothness_chart = RUN_OBJECTS_DICT[run_selector].steering_smoothness_chart()
        else:
            lap_numbers = [lapA_selector, lapB_selector] if lapB_selector != '<select>' else [int(lapA_selector)]
            throttle_smoothness_chart = RUN_OBJECTS_DICT[run_selector].throttle_smoothness_chart(laps=lap_numbers)
            steering_smoothness_chart = RUN_OBJECTS_DICT[run_selector].steering_smoothness_chart(laps=lap_numbers)

        st.altair_chart(throttle_smoothness_chart.properties(height=300), use_container_width=True)
        st.altair_chart(steering_smoothness_chart.properties(height=300), use_container_width=True)

# ---------- LAP PANEL ----------
with lap_panel:
    circuit = CircuitChart(seed=int(run_selector.split(':')[1]), random_orientation=False)
    
    video, track = st.columns([1,3])
    with video:
        if lapA_selector == '<select>' or lapB_selector == '<select>':
            st.write('Select two laps to compare')
            st.image("img/livegap.png", use_column_width=True)
        else:
            st.altair_chart(
                RUN_OBJECTS_DICT[run_selector].laps_delta_comparison_chart(
                    circuit, lapA_selector, lapB_selector),
                use_container_width=True
            )

    with track:
        sectors, microsectors, turns = st.tabs(['Sectors', 'Microsectors', 'Turns'])
        with sectors:
            sector = st.radio(
                'Select sector',
                options = ['All sectors'] + RUN_OBJECTS_DICT[run_selector].df['sector'].unique().tolist(),
                index = 0,
                format_func = lambda x: f"Sector {x}" if x != 'All sectors' else x,
                horizontal = True
            )

            if sector == 'All sectors':
                if lapA_selector == '<select>':
                    st.altair_chart(
                        circuit.track_chart(),
                    )
                elif lapB_selector == '<select>':
                    sectors_delta = compute_sectors_deltas(
                        info=RUN_OBJECTS_DICT[run_selector].info,
                        filename=RUN_OBJECTS_DICT[run_selector].laps[int(lapA_selector)].filename,
                        lap=lapA_selector
                        )
                    st.altair_chart(
                        circuit.colored_sectors_chart(sectors_delta),
                    )
                else:
                    sectors_comparison = compute_sectors_comparison(
                        info=RUN_OBJECTS_DICT[run_selector].info,
                        filenameA=RUN_OBJECTS_DICT[run_selector].laps[int(lapA_selector)].filename,
                        lapA=lapA_selector,
                        filenameB=RUN_OBJECTS_DICT[run_selector].laps[int(lapB_selector)].filename,
                        lapB=lapB_selector
                        )
                    st.altair_chart(
                        circuit.colored_sectors_chart(sectors_comparison),
                    )

            else:
                sector_idx = sector - 1
                
                sector_racing_line, sector_gg_diagram = st.columns([1,1])
                with sector_racing_line:
                    if lapA_selector == '<select>':
                        st.altair_chart(
                            circuit.chart(sector=sector_idx),
                        )
                    else:
                        racing_line_df = RUN_OBJECTS_DICT[run_selector].laps[int(lapA_selector)].racing_line_df(curve_name='lapA', sector=sector)
                        if lapB_selector != '<select>':
                            racing_line_df = pd.concat([racing_line_df, RUN_OBJECTS_DICT[run_selector].laps[int(lapB_selector)].racing_line_df(curve_name='lapB', sector=sector)])
                        st.altair_chart(
                            circuit.chart(middle_curve_df=racing_line_df, sector=sector_idx),
                        )
                
                with sector_gg_diagram:
                    if lapA_selector != '<select>':
                        gg_diagram = RUN_OBJECTS_DICT[run_selector].laps[int(lapA_selector)].gg_diagram(sector=sector)
                        if lapB_selector != '<select>':
                            gg_diagram += RUN_OBJECTS_DICT[run_selector].laps[int(lapB_selector)].gg_diagram(sector=sector)
                        st.altair_chart(gg_diagram, use_container_width=True)

        with microsectors:
            microsector = st.radio(
                'Select microsector',
                options = ['All microsectors'] + RUN_OBJECTS_DICT[run_selector].df['microsector'].unique().tolist(), 
                index = 0,
                format_func = lambda x: f"Microsector {x}" if x != 'All microsectors' else x,
                horizontal = True
            )

            if microsector == 'All microsectors':
                if lapA_selector == '<select>':
                    st.altair_chart(
                        circuit.track_chart(microsectors=True),
                    )
                elif lapB_selector == '<select>':
                    microsectors_delta = compute_sectors_deltas(
                        info=RUN_OBJECTS_DICT[run_selector].info,
                        filename=RUN_OBJECTS_DICT[run_selector].laps[int(lapA_selector)].filename,
                        lap=lapA_selector,
                        microsectors=True
                        )
                    st.altair_chart(
                        circuit.colored_sectors_chart(microsectors_delta, microsectors=True),
                    )
                else:
                    microsectors_comparison = compute_sectors_comparison(
                        info=RUN_OBJECTS_DICT[run_selector].info,
                        filenameA=RUN_OBJECTS_DICT[run_selector].laps[int(lapA_selector)].filename,
                        lapA=lapA_selector,
                        filenameB=RUN_OBJECTS_DICT[run_selector].laps[int(lapB_selector)].filename,
                        lapB=lapB_selector,
                        microsectors=True
                        )
                    st.altair_chart(
                        circuit.colored_sectors_chart(microsectors_comparison, microsectors=True),
                    )

            else:
                microsector_idx = microsector - 1
                
                microsector_racing_line, microsector_gg_diagram = st.columns([1,1])
                with microsector_racing_line:
                    if lapA_selector == '<select>':
                        st.altair_chart(
                            circuit.chart(sector=microsector_idx, microsectors=True),
                        )
                    else:
                        racing_line_df = RUN_OBJECTS_DICT[run_selector].laps[int(lapA_selector)].racing_line_df(curve_name='lapA', sector=microsector, microsectors=True)
                        if lapB_selector != '<select>':
                            racing_line_df = pd.concat([racing_line_df, RUN_OBJECTS_DICT[run_selector].laps[int(lapB_selector)].racing_line_df(curve_name='lapB', sector=microsector, microsectors=True)])
                        st.altair_chart(
                            circuit.chart(middle_curve_df=racing_line_df, sector=microsector_idx, microsectors=True),
                        )
                
                with microsector_gg_diagram:
                    if lapA_selector != '<select>':
                        gg_diagram = RUN_OBJECTS_DICT[run_selector].laps[int(lapA_selector)].gg_diagram(sector=microsector, microsectors=True)
                        if lapB_selector != '<select>':
                            gg_diagram += RUN_OBJECTS_DICT[run_selector].laps[int(lapB_selector)].gg_diagram(sector=microsector, microsectors=True)
                        st.altair_chart(gg_diagram, use_container_width=True)

        with turns:
            if turns_json is None:
                st.write('No turns data available, please build the turns data for this run first.')
            else:
                st.altair_chart(
                    circuit.turns_chart(turns_json=turns_json)
                )
