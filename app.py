import streamlit as st
import pandas as pd
import altair as alt
import numpy as np
import json
from os import listdir
from os.path import dirname, abspath, join, isfile
import vegafusion as vf
vf.enable()

from Modules import Run, compute_sectors_deltas, compute_sectors_comparison, laps_df
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
            new_run_object = Run(join(dirname(abspath(__file__)), 'data', run, f), info=INFO[run], filename=f)
            run_object = new_run_object if run_object is None else run_object + new_run_object

    RUN_OBJECTS_DICT[run] = run_object

# ---------- APP SETUP ----------
st.set_page_config(
    page_title="DPA Visualization Tool",
    page_icon=":checkered_flag:",
    # page_icon="🏎",
    layout="wide",
    initial_sidebar_state="expanded",
)
header_panel = st.container()
run_panel = st.container()
lap_panel = st.container()

# ---------- HEADER ----------
with header_panel:
    st.title('DPA Visualization Tool')

# ---------- SELECTORS ----------
with st.sidebar:
    st.header('Select run and lap')
    run_selector = st.selectbox(
        'Select run',
        RUNS,
        index=0
    )
    
    lapA_selector = st.selectbox(
        label = 'Select lap A',
        options = ['<select>'] + list(range(len(RUN_OBJECTS_DICT[run_selector].laps))),
        format_func = lambda x: f"Lap {x} [{RUN_OBJECTS_DICT[run_selector].laps[x].driver}]" if x != '<select>' else x,
        index=0
    )
    
    lapB_options = set(range(len(RUN_OBJECTS_DICT[run_selector].laps))) - (set([int(lapA_selector)]) if lapA_selector != '<select>' else set())
    lapB_options = ['<select>'] + list(lapB_options)
    lapB_selector = st.selectbox(
        'Select lap B',
        options = lapB_options,
        format_func = lambda x: f"Lap {x} [{RUN_OBJECTS_DICT[run_selector].laps[x].driver}]" if x != '<select>' else x,
        index=0,
        disabled = True if lapA_selector == '<select>' else False
    )
    
    if lapA_selector != '<select>':
        laps_data_frame = laps_df(RUN_OBJECTS_DICT[run_selector].laps, RUN_OBJECTS_DICT[run_selector].info, lapA_selector)
    else:
        laps_data_frame = laps_df(RUN_OBJECTS_DICT[run_selector].laps, RUN_OBJECTS_DICT[run_selector].info)
    st.dataframe(laps_data_frame)

# ---------- RUN PANEL ----------
try:
    with open(join(dirname(abspath(__file__)), 'data', run_selector, 'turns.json'), 'r') as f:
        turns_json = json.load(f)
except FileNotFoundError:
    turns_json = None

with run_panel:
    st.divider()
    st.header('Run overview')
    radars_panel, harshness_panel = st.columns([2,1])
    with radars_panel:
        if lapA_selector == '<select>':
            mean_v_chart, out_v_chart, braking_point_chart = RUN_OBJECTS_DICT[run_selector].braking_charts(turns_json)
        else:
            lap_numbers = [int(lapA_selector) - 1, int(lapB_selector) - 1] if lapB_selector != '<select>' else [int(lapA_selector) - 1]
            mean_v_chart, out_v_chart, braking_point_chart = RUN_OBJECTS_DICT[run_selector].braking_charts(turns_json, laps=lap_numbers)
        
        columns = st.columns(2)
        with columns[0]:
            st.altair_chart(mean_v_chart)
        
        with columns[1]:
            st.altair_chart(out_v_chart)

        st.altair_chart(braking_point_chart)

        with st.expander('Circuit Turns', expanded=False):
            if turns_json is None:
                st.write('No turns data available, please build the turns data for this run first.')
            else:
                st.write('The following chart shows the circuit turns. These turns have been manually defined with microsectors, hovering the mouse over the chart you can see the turn number and the microsector number.')
                circuit = CircuitChart(seed=int(run_selector.split(':')[1]), random_orientation=False)
                st.altair_chart(
                    circuit.turns_chart(turns_json=turns_json)
                )
                st.markdown('In order to change each turn microsectors modify the `turns.json` file in the run folder.')


    with harshness_panel:
        if lapA_selector == '<select>':
            throttle_harshness_chart = RUN_OBJECTS_DICT[run_selector].throttle_harshness_chart()
            steering_harshness_chart = RUN_OBJECTS_DICT[run_selector].steering_harshness_chart()
        else:
            lap_numbers = [lapA_selector, lapB_selector] if lapB_selector != '<select>' else [int(lapA_selector)]
            throttle_harshness_chart = RUN_OBJECTS_DICT[run_selector].throttle_harshness_chart(laps=lap_numbers)
            steering_harshness_chart = RUN_OBJECTS_DICT[run_selector].steering_harshness_chart(laps=lap_numbers)

        st.altair_chart(throttle_harshness_chart.properties(height=300), use_container_width=True)
        st.altair_chart(steering_harshness_chart.properties(height=300), use_container_width=True)

# ---------- LAP PANEL ----------
if lapA_selector != '<select>':
    laps_data_frame = laps_df(RUN_OBJECTS_DICT[run_selector].laps, RUN_OBJECTS_DICT[run_selector].info, lapA_selector)
else:
    laps_data_frame = laps_df(RUN_OBJECTS_DICT[run_selector].laps, RUN_OBJECTS_DICT[run_selector].info)

with lap_panel:
    st.divider()
    st.header('Lap overview')
    circuit = CircuitChart(seed=int(run_selector.split(':')[1]), random_orientation=False)
    sectors, microsectors = st.tabs(['Sectors', 'Microsectors'])
    
    with sectors:
        sector = st.radio(
            'Select sector',
            options = ['All sectors'] + RUN_OBJECTS_DICT[run_selector].df['sector'].unique().tolist(),
            index = 0,
            format_func = lambda x: f"Sector {x}" if x != 'All sectors' else x,
            horizontal = True
        )

        if sector == 'All sectors':
            track, delta_comparison = st.columns(2)
            with delta_comparison:
                if lapB_selector != '<select>':
                    st.altair_chart(
                        RUN_OBJECTS_DICT[run_selector].laps_delta_comparison_chart(
                            circuit, lapA_selector, lapB_selector),
                        use_container_width=True
                    )
            
            with track:
                if lapA_selector == '<select>':
                    st.altair_chart(
                        circuit.track_chart(),
                    )
                elif lapB_selector == '<select>':
                    racing_line_df = RUN_OBJECTS_DICT[run_selector].laps[int(lapA_selector)].racing_line_df(curve_name='lapA', sector=(1,30))
                    sectors_delta = compute_sectors_deltas(
                        info=RUN_OBJECTS_DICT[run_selector].info,
                        filename=RUN_OBJECTS_DICT[run_selector].laps[int(lapA_selector)].filename,
                        lap=lapA_selector - RUN_OBJECTS_DICT[run_selector].lap_map[lapA_selector]
                    )
                    st.altair_chart(
                        circuit.chart(middle_curve_df=racing_line_df, info=sectors_delta),
                        use_container_width=True
                    )
                else:
                    sectors_comparison = compute_sectors_comparison(
                        info=RUN_OBJECTS_DICT[run_selector].info,
                        filenameA=RUN_OBJECTS_DICT[run_selector].laps[int(lapA_selector)].filename,
                        lapA=lapA_selector - RUN_OBJECTS_DICT[run_selector].lap_map[lapA_selector],
                        filenameB=RUN_OBJECTS_DICT[run_selector].laps[int(lapB_selector)].filename,
                        lapB=lapB_selector - RUN_OBJECTS_DICT[run_selector].lap_map[lapB_selector]
                        )
                    st.altair_chart(
                        circuit.colored_sectors_chart(sectors_comparison),
                        use_container_width=True
                    )

        else:
            sector_idx = sector - 1
            
            if lapB_selector != '<select>':
                sector_racing_line, sector_gg_diagram, delta_comparison = st.columns([3,2,2])
                with delta_comparison:
                    st.altair_chart(
                        RUN_OBJECTS_DICT[run_selector].laps_delta_comparison_chart(
                            circuit, lapA_selector, lapB_selector, sector=sector),
                        use_container_width=True
                    )
            else:
                sector_racing_line, sector_gg_diagram = st.columns(2)

            with sector_racing_line:
                if lapA_selector == '<select>':
                    st.altair_chart(
                        circuit.chart(sector=sector_idx),
                    )
                elif lapB_selector == '<select>':
                    racing_line_df = RUN_OBJECTS_DICT[run_selector].laps[int(lapA_selector)].racing_line_df(curve_name='lapA', sector=sector)
                    sectors_delta = compute_sectors_deltas(
                        info=RUN_OBJECTS_DICT[run_selector].info,
                        filename=RUN_OBJECTS_DICT[run_selector].laps[int(lapA_selector)].filename,
                        lap=lapA_selector - RUN_OBJECTS_DICT[run_selector].lap_map[lapA_selector]
                    )
                    st.altair_chart(
                        circuit.chart(middle_curve_df=racing_line_df, sector=sector_idx, info=[sectors_delta[sector_idx]]),
                    )
                else:
                    racing_line_df = RUN_OBJECTS_DICT[run_selector].laps[int(lapA_selector)].racing_line_df(curve_name='lapA', sector=sector)
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
        microsector = st.select_slider(
            'Select microsector',
            options=RUN_OBJECTS_DICT[run_selector].df['microsector'].unique().tolist(),
            value=(1, 30),
            format_func = lambda x: f"Microsector {x}",
        )
        if microsector == (1, 30):
            microsector = 'All microsectors'

        if microsector == 'All microsectors':
            track, delta_comparison = st.columns(2)
            with delta_comparison:
                if lapB_selector != '<select>':
                    st.altair_chart(
                        RUN_OBJECTS_DICT[run_selector].laps_delta_comparison_chart(
                            circuit, lapA_selector, lapB_selector),
                        use_container_width=True
                    )
            
            with track:
                if lapA_selector == '<select>':
                    st.altair_chart(
                        circuit.track_chart(microsectors=True),
                    )
                elif lapB_selector == '<select>':
                    racing_line_df = RUN_OBJECTS_DICT[run_selector].laps[int(lapA_selector)].racing_line_df(curve_name='lapA', sector=(1,30))
                    microsectors_delta = compute_sectors_deltas(
                        info=RUN_OBJECTS_DICT[run_selector].info,
                        filename=RUN_OBJECTS_DICT[run_selector].laps[int(lapA_selector)].filename,
                        lap=lapA_selector - RUN_OBJECTS_DICT[run_selector].lap_map[lapA_selector],
                        microsectors=True
                        )
                    st.altair_chart(
                        circuit.chart(middle_curve_df=racing_line_df, info=microsectors_delta),
                        use_container_width=True
                    )
                else:
                    microsectors_comparison = compute_sectors_comparison(
                        info=RUN_OBJECTS_DICT[run_selector].info,
                        filenameA=RUN_OBJECTS_DICT[run_selector].laps[int(lapA_selector)].filename,
                        lapA=lapA_selector - RUN_OBJECTS_DICT[run_selector].lap_map[lapA_selector],
                        filenameB=RUN_OBJECTS_DICT[run_selector].laps[int(lapB_selector)].filename,
                        lapB=lapB_selector - RUN_OBJECTS_DICT[run_selector].lap_map[lapB_selector],
                        microsectors=True
                        )
                    st.altair_chart(
                        circuit.colored_sectors_chart(microsectors_comparison, microsectors=True),
                        use_container_width=True
                    )

        else:
            microsector_idx = (microsector[0] - 1, microsector[1] - 1)
            
            if lapB_selector != '<select>':
                microsector_racing_line, microsector_gg_diagram, delta_comparison = st.columns([3,2,2])
                with delta_comparison:
                    st.altair_chart(
                        RUN_OBJECTS_DICT[run_selector].laps_delta_comparison_chart(
                            circuit, lapA_selector, lapB_selector, sector=microsector),
                        use_container_width=True
                    )
            else:
                microsector_racing_line, microsector_gg_diagram = st.columns(2)

            with microsector_racing_line:
                if lapA_selector == '<select>':
                    st.altair_chart(
                        circuit.chart(sector=microsector_idx),
                    )
                else:
                    racing_line_df = RUN_OBJECTS_DICT[run_selector].laps[int(lapA_selector)].racing_line_df(curve_name='lapA', sector=microsector)
                    if lapB_selector != '<select>':
                        racing_line_df = pd.concat([racing_line_df, RUN_OBJECTS_DICT[run_selector].laps[int(lapB_selector)].racing_line_df(curve_name='lapB', sector=microsector)])
                    st.altair_chart(
                        circuit.chart(middle_curve_df=racing_line_df, sector=microsector_idx),
                    )
            
            with microsector_gg_diagram:
                if lapA_selector != '<select>':
                    gg_diagram = RUN_OBJECTS_DICT[run_selector].laps[int(lapA_selector)].gg_diagram(sector=microsector)
                    if lapB_selector != '<select>':
                        gg_diagram += RUN_OBJECTS_DICT[run_selector].laps[int(lapB_selector)].gg_diagram(sector=microsector)
                    st.altair_chart(gg_diagram, use_container_width=True)


# st.dataframe(RUN_OBJECTS_DICT[run_selector].df)
# st.dataframe(RUN_OBJECTS_DICT[run_selector].describe())