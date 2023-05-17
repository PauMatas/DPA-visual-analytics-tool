import pandas as pd


def get_braking_stats(turns_json: list, laps: list, run_df: pd.DataFrame, lap_map: list, lap_idxs: list = []) -> tuple[list]:
    if lap_idxs:
        laps = [laps[i] for i in lap_idxs]
        lap_map = [lap_map[i] for i in lap_idxs]
    axis_names = []
    axis_idxs = []
    lines = []
    mean_v = []
    out_v = []
    distance_before_braking = []

    for turn in turns_json:
        for lap_number, lap_diff in zip(laps, lap_map):
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
                lines.append(lap_number)
                mean_v.append(df['Velocity'].mean())
                out_v.append(df['Velocity'].values[-1])
                distance_before_braking.append(pre_break_dist)

    return axis_names, axis_idxs, lines, mean_v, out_v, distance_before_braking
