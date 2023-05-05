import argparse
import numpy as np
import json
from os import makedirs

from gro.gro4dpa import *


DATA_DIR = './data'
DRIVERS_JSON_PATH = DATA_DIR + '/drivers.json'

def generate_run(gates: Gates, circuit: CircuitChart) -> tuple[list[pd.DataFrame], list[str]]:
    """Generate a run of the circuit."""

    algorithms = {
        'GRO-Online': run_GRO_online,
        # 'GRO': run_GRO,
        # 'MinCurv': run_min_curv,
        # 'MinDist': run_min_dist,
        # # 'MinCurvDist': run_min_curv_dist,
        # 'MidLine': run_midline,
    }
    
    runs_dfs_list = []
    drivers = []

    for driver, algorithm in algorithms.items():
        print('\t' + f'Running {driver}')
        run_df = algorithm(gates, circuit)
        runs_dfs_list.append(run_df)
        drivers.append(driver)

    return runs_dfs_list, drivers


def save_run(seed: int, run_df: list[pd.DataFrame], drivers: list[str]):
    """Save run to disk."""
    
    try:
        with open(DRIVERS_JSON_PATH, 'r') as f:
            drivers_json = json.load(f)
    except FileNotFoundError:
        drivers_json = {}

    RUN_DIR = F'{DATA_DIR}/TILK-E:{seed}'
    makedirs(RUN_DIR, exist_ok=True)
    for i, (df, driver) in enumerate(zip(run_df, drivers)):
        df.to_csv(f'{RUN_DIR}/{seed}_Run{i}.csv', index=False)
        if f'TILK-E:{seed}' not in drivers_json:
            drivers_json[f'TILK-E:{seed}'] = {}
        drivers_json[f'TILK-E:{seed}'][f'{seed}_Run{i}.csv'] = driver
    
    with open(DRIVERS_JSON_PATH, 'w') as f:
        json.dump(drivers_json, f, indent=4, ensure_ascii=False)


def __main__():
    parser = argparse.ArgumentParser(description='Generate data for DPA project using GRO & TILK-E.')
    parser.add_argument('-n', '--n_circuits', dest='n_circuits', default=1, help='Number of circuits to generate.', type=int)
    args = parser.parse_args()

    SEEDS = [420, 1337, 27, 4, 54, 33][:args.n_circuits] # TODO: remove this line
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
        save_run(seed, runs_dfs_list, drivers)

if __name__ == '__main__':
    __main__()
