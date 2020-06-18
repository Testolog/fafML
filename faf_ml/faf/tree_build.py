import json
from itertools import product

from pandas import DataFrame, MultiIndex
from tabulate import tabulate

PROCESS_COLUMN = ["Economy", 'Categories', 'Defense', 'General', 'Intel', 'Wreckage']

with open("../../data/test/XSL0105_unit.json") as f:
    data = json.load(f)
mp_index = MultiIndex.from_tuples(product(["XSL0105"], PROCESS_COLUMN))
df: DataFrame = DataFrame(data, columns=PROCESS_COLUMN, index=["XSL0105"])
print(DataFrame(data, columns=PROCESS_COLUMN, index=mp_index))
e = DataFrame.from_records(df['Economy'], index=["XSL0105"])
print(tabulate(df, headers="keys", tablefmt='psql'))
