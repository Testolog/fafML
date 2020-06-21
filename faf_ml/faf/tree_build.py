import json
from itertools import product
from typing import Dict, List

from pandas import DataFrame, MultiIndex, Series, concat
from tabulate import tabulate

PROCESS_COLUMN = ["Economy", 'Categories', 'Defense', 'General', 'Intel', 'Wreckage', 'Weapon', 'Veteran', 'Transport',
                  'Buffs']


def build_multiple_lvl_df(raw_data: Dict, index=None, select_column: List = None) -> DataFrame:
    series = []

    def dict_to_tuple(work_dict: Dict, t_key=None):
        res = []
        for key, value in work_dict.items():
            if select_column:
                if not t_key and key not in select_column:
                    continue
            if isinstance(value, dict):
                res += [(t_key, *_) for _ in dict_to_tuple(value, key)] if t_key else dict_to_tuple(value, key)
            elif isinstance(value, list):
                series.append(Series([value], index=[index]))
                res.append((t_key, key, "value") if t_key else (key, "value"))
            else:
                series.append(Series(value, index=[index]))
                res.append((t_key, key) if t_key else (key,))
        return res

    to_tuple = dict_to_tuple(raw_data)
    output_df: DataFrame = concat(series, axis=1)
    output_df.columns = MultiIndex.from_tuples(to_tuple)
    return output_df


def zip_units_dfs(units: List[DataFrame]) -> DataFrame:
    index_df = concat([_.columns.to_frame() for _ in units], axis=0).drop_duplicates()
    global_columns = MultiIndex.from_frame(index_df)
    common_df = concat([_.reindex(columns=global_columns) for _ in units], axis=0)
    common_df.columns = global_columns
    return common_df

