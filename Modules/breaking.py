import pandas as pd


def get_breaking_stats(turns_json: list, lap_numbers: list, run_df: pd.DataFrame) -> tuple[list]:
    axis_names = []
    axis_idxs = []
    lines = []
    mean_v = []
    out_v = []
    distance_before_breaking = []

    for turn in turns_json:
        for lap_number in lap_numbers:
            df = run_df.loc[(turn['first_ms'] <= run_df['microsector']) & (run_df['microsector'] <= turn['last_ms']) & (run_df['laps'] == lap_number)]

            pre_break_dist = 0
            has_breaked = df[['BPE', 'TimeStamp']].sort_values(by = 'TimeStamp', ascending = True).values[0][0] >= 0.2
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
            distance_before_breaking.append(pre_break_dist)

    return axis_names, axis_idxs, lines, mean_v, out_v, distance_before_breaking
