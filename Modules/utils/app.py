import numpy as np

def compute_sectors_deltas(info: dict, filename: str, lap: int, microsectors: bool = False) -> list:
    """
    Compute sector deltas: This function returns a list with different values for each sector of the lap.
    The value of a sector will be 'best' if it is the best time for that sector, 'personal_best' if it is
    the best time for that sector for the driver, and 'other' if it is not the best time for that sector for the driver.
    """
    # return [np.random.choice(['best', 'personal_best', 'other']) for _ in range((30 if microsectors else 3))]
    segments = 'microsectors' if microsectors else 'sectors'

    driver = info[filename]['driver']
    best_times = info['best_times']['global'][segments]
    personal_best_times = info['best_times'][driver][segments]
    lap_times = info[filename]['laps'][str(lap)][segments]

    return [
        'best' if t == bt else 'personal_best' if t == pbt else 'other'
        for t, bt, pbt in zip(lap_times, best_times, personal_best_times)
    ]

def compute_sectors_comparison(info: dict, filenameA: str, lapA: int, filenameB: str, lapB: int, microsectors: bool = False) -> list:
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
        'other' if tA == tB else ('lapA' if tA > tB else 'lapB')
        for tA, tB in zip(lapA_times, lapB_times)
    ]