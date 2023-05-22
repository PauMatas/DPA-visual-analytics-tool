import pandas as pd


def get_braking_stats(turns_json: list, laps: list, run_df: pd.DataFrame, lap_map: list, drivers: list, lap_idxs: list = [], groupby: bool = False) -> tuple[list]:
    if lap_idxs:
        laps = [laps[i] for i in lap_idxs]
        lap_map = [lap_map[i] for i in lap_idxs]
        drivers = [drivers[i] for i in lap_idxs]
    drivers_map = {driver: i for i, driver in enumerate(drivers)}
    axis_names = []
    axis_idxs = []
    lines = []
    drivers_names = []
    mean_v = []
    out_v = []
    distance_before_braking = []

    for turn in turns_json:
        for lap_number, lap_diff, lap_driver in zip(laps, lap_map, drivers):
            df = run_df.loc[(turn['first_ms'] <= run_df['microsector']) & (run_df['microsector'] <= turn['last_ms']) & (run_df['laps'] == lap_number - lap_diff)]

            pre_break_dist = 0
            if len((first_braking := df[['BPE', 'TimeStamp']].sort_values(by = 'TimeStamp', ascending = True).values)) > 0:
                has_breaked = first_braking[0][0] >= 0.2
                for bpe, dist, _ in df[['BPE', 'dist1', 'TimeStamp']].sort_values(by = 'TimeStamp', ascending = True).values:
                    if not has_breaked and bpe < 0.2:
                        pre_break_dist += dist
                    else:
                        has_breaked = True

                axis_names.append(turn['name'])
                axis_idxs.append(int(turn['name'].split(' ')[1]) - 1)
                drivers_names.append(lap_driver)
                lines.append(lap_number)
                mean_v.append(df['Velocity'].mean())
                out_v.append(df['Velocity'].values[-1])
                distance_before_braking.append(pre_break_dist)

    if groupby:
        # build a dataframe with the data, get the average mean_v, out_v and distance_before_braking of each driver and return the columns splited
        df = pd.DataFrame({'axis_names': axis_names, 'axis_idxs': axis_idxs, 'lines': drivers_names, 'mean_v': mean_v, 'out_v': out_v, 'distance_before_braking': distance_before_braking})
        df = df.groupby(['axis_names', 'axis_idxs', 'lines']).mean().reset_index()
        axis_names = df['axis_names'].values.tolist()
        axis_idxs = df['axis_idxs'].values.tolist()
        drivers_names = df['lines'].values.tolist()
        lines = [drivers_map[driver] for driver in drivers_names]
        mean_v = df['mean_v'].values.tolist()
        out_v = df['out_v'].values.tolist()
        distance_before_braking = df['distance_before_braking'].values.tolist()

    return axis_names, axis_idxs, lines, drivers_names, mean_v, out_v, distance_before_braking
