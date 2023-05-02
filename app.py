import streamlit as st
import pandas as pd
import altair as alt
import numpy as np
import json
from os import listdir
from os.path import dirname, abspath, join, isfile

from Modules import Run
from Modules.radarchart import RadarChart
alt.data_transformers.disable_max_rows()


# ---------- DATA LOADING ----------
RUNS = ['proves_pilots']
with open(join(dirname(abspath(__file__)), 'data', 'drivers.json'), 'r') as f:
    DRIVERS = json.load(f)
RUN_OBJECTS_DICT = {}

for run in RUNS:
    run_object = None
    for f in listdir(join(dirname(abspath(__file__)), 'data', run)):
        if isfile(join(dirname(abspath(__file__)), 'data', run, f)) and f.endswith('.csv'):
            driver = DRIVERS[run][f]
            new_run_object = Run(join(dirname(abspath(__file__)), 'data', run, f), driver)
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
st.header('DPA Visualization Tool Header')

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
            options = range(len(RUN_OBJECTS_DICT[run_selector].laps)),
            format_func = lambda x: f"Lap {x} [{RUN_OBJECTS_DICT[run_selector].laps[x].driver}]",
            index=0
        )
    
    with columns[2]:
        lapB_selector = st.selectbox(
            'Select lap B',
            options = range(len(RUN_OBJECTS_DICT[run_selector].laps)),
            format_func = lambda x: f"Lap {x} [{RUN_OBJECTS_DICT[run_selector].laps[x].driver}]",
            index=1
        )
    
# ---------- RUN PANEL ----------
with run_panel:
    radars_panel, smoothness_panel = st.columns([5,2])
    with radars_panel:
        columns = st.columns(3)
        with columns[0]:
            st.write('Braking Distance to the apex')
            df_dict = []
            for lap in range(2):
                for turn in range(7): # 7 turns
                    meters = max(5, (np.random.uniform(0, ((turn%4)+1)*20)+np.random.randint(10)))
                    df_dict.append({'axis_name': f'Turn {turn+1}', 'axis': turn, 'line': lap, 'metric': meters})
            df = pd.DataFrame(df_dict)

            radar = RadarChart(df, 4)
            st.altair_chart(radar.chart.properties(height = 300), use_container_width=True)
        
        with columns[1]:
            st.write('Average Speed per turn')
            df_dict = []
            for lap in range(2):
                for turn in range(7): # 7 turns
                    meters = max(5, (np.random.uniform(0, ((turn%4)+1)*20)+np.random.randint(10)))
                    df_dict.append({'axis_name': f'Turn {turn+1}', 'axis': turn, 'line': lap, 'metric': meters})
            df = pd.DataFrame(df_dict)

            radar = RadarChart(df, 4)
            st.altair_chart(radar.chart.properties(height = 300), use_container_width=True)

        with columns[2]:
            st.write('Speed at the end of the turn')
            df_dict = []
            for lap in range(2):
                for turn in range(7): # 7 turns
                    meters = max(5, (np.random.uniform(0, ((turn%4)+1)*20)+np.random.randint(10)))
                    df_dict.append({'axis_name': f'Turn {turn+1}', 'axis': turn, 'line': lap, 'metric': meters})
            df = pd.DataFrame(df_dict)

            radar = RadarChart(df, 4)
            st.altair_chart(radar.chart.properties(height = 400), use_container_width=True)

    with smoothness_panel:
        throttle_smoothness_chart = RUN_OBJECTS_DICT[run_selector].throttle_smoothness_chart()
        steering_smoothness_chart = RUN_OBJECTS_DICT[run_selector].steering_smoothness_chart()

        st.altair_chart(throttle_smoothness_chart.properties(height=250), use_container_width=True)
        st.altair_chart(steering_smoothness_chart.properties(height=250), use_container_width=True)

# ---------- LAP PANEL ----------
with lap_panel:
    video, track = st.columns([1,3])
    with video:
        st.image("img/livegap.png", use_column_width=True)

    with track:
        sectors, microsectors = st.tabs(['Sectors', 'Microsectors'])

        with sectors:
            sector = st.radio(
                'Select sector',
                options = ['All sectors', 'Sector 1', 'Sector 2', 'Sector 3'], # TODO: get from run
                index = 0,
                horizontal = True
            )

            if sector == 'All sectors':
                st.image("img/sectors.png", use_column_width=True)

            else:
                sector_idx = int(sector[-1])
                
                sector_racing_line, sector_gg_diagram = st.columns([1,1])
                with sector_racing_line:
                    st.image("img/turn.png", use_column_width=True)
                
                with sector_gg_diagram:
                    gg_diagram = RUN_OBJECTS_DICT[run_selector].laps[lapA_selector].gg_diagram() + RUN_OBJECTS_DICT[run_selector].laps[lapB_selector].gg_diagram()
                    st.altair_chart(gg_diagram, use_container_width=True)

        with microsectors:
            microsector = st.radio(
                'Select microsector',
                options = ['All microsectors', 'Microsector 1', 'Microsector 2', 'Microsector 3', 'Microsector 4', 'Microsector 5'], # TODO: get from run
                index = 0,
                horizontal = True
            )

            if microsector == 'All microsectors':
                st.image("img/microsectors.png", use_column_width=True)

            else:
                microsector_idx = int(microsector[-1])
                
                microsector_racing_line, microsector_gg_diagram = st.columns([1,1])
                with microsector_racing_line:
                    st.image("img/turn.png", use_column_width=True)
                
                with microsector_gg_diagram:
                    gg_diagram = RUN_OBJECTS_DICT[run_selector].laps[lapA_selector].gg_diagram() + RUN_OBJECTS_DICT[run_selector].laps[lapB_selector].gg_diagram()
                    st.altair_chart(gg_diagram, use_container_width=True)

# ---------- FOOTER ----------
st.markdown('<style>h1{color: red;}</style>',
            unsafe_allow_html=True)

st.title('DPA Visualization Tool')
st.dataframe(RUN_OBJECTS_DICT[run_selector].df)