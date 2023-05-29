import numpy as np
import pandas as pd

def compute_sectors_deltas(info: dict, filename: str, lap: int, microsectors: bool = False) -> list:
    """
    Compute sector deltas: This function returns a list with different values for each sector of the lap.
    The value of a sector will be 'Best overall' if it is the best time for that sector, 'Personal best' if it is
    the best time for that sector for the driver, and 'Other times' if it is not the best time for that sector for the driver.
    """
    # return [np.random.choice(['Best overall', 'Personal best', 'Other times']) for _ in range((30 if microsectors else 3))]
    segments = 'microsectors' if microsectors else 'sectors'

    driver = info[filename]['driver']
    best_times = info['best_times']['global'][segments]
    personal_best_times = info['best_times'][driver][segments]
    lap_times = info[filename]['laps'][str(lap)][segments]

    return [
        'Best overall' if t == bt else 'Personal best' if t == pbt else 'Other times'
        for t, bt, pbt in zip(lap_times, best_times, personal_best_times)
    ]

def compute_sectors_comparison(info: dict, filenameA: str, global_lapA: int, lapA: int, filenameB: str, global_lapB: int, lapB: int, microsectors: bool = False) -> list:
    """
    Compute sector deltas: This function returns a list with different values for each sector of the lap.
    The value of a sector will be 'lapA' if lap A has the best time for that sector and 'lapB' if it is
    lap B the one with the best time for that sector.
    """
    # return [np.random.choice(['lapA', 'lapB', 'other']) for _ in range((30 if microsectors else 3))]
    segments = 'microsectors' if microsectors else 'sectors'

    lapA_times = info[filenameA]['laps'][str(lapA)][segments]
    lapB_times = info[filenameB]['laps'][str(lapB)][segments]

    return [
        -1 if tA == tB else (global_lapA if tA < tB else global_lapB)
        for tA, tB in zip(lapA_times, lapB_times)
    ]

def color_laps_df_rows(row: pd.Series, info: dict, lapA: int = None, lapB: int = None) -> list:
    """
    Returns a colormap for the rows of the laps dataframe.
    """
    if lapA is not None and int(row['Lap'].split(' ')[1]) == lapA:
        row_colors = ['background-color: rgba(78, 121, 167, 0.5);'] * 2
    elif lapB is not None and int(row['Lap'].split(' ')[1]) == lapB:
        row_colors = ['background-color: rgba(242, 142, 43, 0.5);'] * 2
    else:
        row_colors = ['background-color: white;'] * 2

    if row['Laptime'] == info['best_times']['global']['laptime']:
        row_colors += ['background-color: rgba(128, 0, 128, 0.5);']
    elif row['Laptime'] == info['best_times'][row['Driver']]['laptime']:
        row_colors += ['background-color: rgba(44, 160, 44, 0.5);']
    else:
        row_colors += ['background-color: white;']
    
    return row_colors

def laps_df(laps: list, info: dict, lapA: int = None, lapB: int = None) -> pd.DataFrame:
    """
    Create a colored dataframe with the laps information.
    """
    assert lapB is None or lapA is not None, 'lapA must be specified if lapB is specified'
    laps_df = pd.DataFrame(
        [
            {
                'Lap': f'Lap {lap.number}',
                'Driver': lap.driver,
                'Laptime': lap.laptime,
            }
            for lap in laps
        ]
    )

    return laps_df.style.apply(
        lambda row: color_laps_df_rows(row, info, lapA, lapB),
        axis=1
    ).format('{:.3f}', subset=['Laptime'])
