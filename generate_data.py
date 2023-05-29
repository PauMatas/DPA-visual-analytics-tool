import argparse
import numpy as np
import json
from os import makedirs

from gro.gro4dpa import * # run_GRO_online, run_GRO, ..., run_midline


DATA_DIR = './data'
INFO_JSON_PATH = DATA_DIR + '/info.json'
N_SECTORS = 3
N_MICROSECTORS = 10 * N_SECTORS

def generate_run(gates: Gates, circuit: CircuitChart) -> tuple[list[pd.DataFrame], list[str]]:
    """Generate a run of the circuit."""

    algorithms = {
        # 'GRO-Online': run_GRO_online,
        # 'GRO': run_GRO,
        # 'MinCurv': run_min_curv,
        # 'MinDist': run_min_dist,
        # # 'MinCurvDist': run_min_curv_dist,
        # 'MidLine': run_midline,

        'Alice': run_GRO_online,
        'Bob': run_GRO_online,
        'Charlie': run_GRO_online,
        'Dave': run_GRO_online,
    }
    
    runs_dfs_list = []
    drivers = []

    for driver, algorithm in algorithms.items():
        print('\t' + f'Running {driver}')
        run_df = algorithm(gates, circuit, driver=driver)
        if not run_df.empty:
            runs_dfs_list.append(run_df)
            drivers.append(driver)

    return runs_dfs_list, drivers


def save_run(seed: int, run_df: list[pd.DataFrame], run_info: dict) -> None:
    """Save run to disk."""
    
    # Save run info to info.json
    try:
        with open(INFO_JSON_PATH, 'r') as f:
            info_json = json.load(f)
    except FileNotFoundError:
        info_json = {}

    info_json[f'TILK-E:{seed}'] = run_info

    with open(INFO_JSON_PATH, 'w') as f:
        json.dump(info_json, f, indent=4, ensure_ascii=False)

    # Save run to disk
    RUN_DIR = F'{DATA_DIR}/TILK-E:{seed}'
    makedirs(RUN_DIR, exist_ok=True)
    for i, df in enumerate(run_df):
        df.to_csv(f'{RUN_DIR}/{seed}_Run{i}.csv', index=False)
    

def times_dict(df: pd.DataFrame) -> dict:
    """Calculate times."""

    groupby = ['laps', 'driver'] if 'driver' in df else ['laps']
    laptime = min(df.groupby(groupby)['delta'].sum())
    sectors = [
        min(df[df['sector'] == sector].groupby(groupby)['delta'].sum())
        for sector in range(1, N_SECTORS + 1)
    ]
    microsectors = [
        min(df[df['microsector'] == microsector].groupby(groupby)['delta'].sum())
        for microsector in range(1, N_MICROSECTORS + 1)
    ]

    return {
        'laptime': laptime,
        'sectors': sectors,
        'microsectors': microsectors,
    }

def driver_best_times(df: pd.DataFrame, driver: str) -> dict:
    """Calculate best times."""
    df = df[df['driver'] == driver]
    return times_dict(df)

def run_info_dict(seed: int, runs_dfs_list: list[pd.DataFrame], drivers: list[str]) -> dict:
    """Calculate run info."""
    run_info = {
        f'{seed}_Run{i}.csv': {
            'driver': driver,
            'laps': {lap: times_dict(lap_df) for lap, (_, lap_df) in enumerate(df.groupby('laps'))}
        }
        for i, (df, driver) in enumerate(zip(runs_dfs_list, drivers))
    }

    runs_drivers_dfs_list = []
    for df, driver in zip(runs_dfs_list, drivers):
        df['driver'] = driver
        runs_drivers_dfs_list.append(df)
    global_df = pd.concat(runs_drivers_dfs_list)
    run_info['best_times'] = {
        driver: driver_best_times(global_df, driver)
        for driver in drivers
    }
    run_info['best_times']['global'] = times_dict(global_df)

    return run_info

    

def __main__():
    parser = argparse.ArgumentParser(description='Generate data for DPA project using GRO & TILK-E.')
    parser.add_argument('-n', '--n_circuits', dest='n_circuits', default=1, help='Number of circuits to generate.', type=int)
    args = parser.parse_args()

    SEEDS = [420, 1337, 27, 4, 54, 6811, 3412][:args.n_circuits] # TODO: remove this line
    # SEEDS = list(np.random.randint(0, 2**32, args.n_circuits))

    # Generate circuits
    while SEEDS:
        seed = SEEDS.pop()
        try:
            gates, circuit = create_environment(seed=seed)
        except CircuitNotRulesCompliant:
            print(f'Circuit {seed} not rules compliant, skipping...')
            seed.put(np.random.randint(0, 2**32))
            continue
        print(f'Generating circuit {seed}')
        runs_dfs_list, drivers = generate_run(gates, circuit)
        run_info = run_info_dict(seed, runs_dfs_list, drivers)
        save_run(seed, runs_dfs_list, run_info)

if __name__ == '__main__':
    __main__()
