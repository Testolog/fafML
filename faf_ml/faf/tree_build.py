import json

from pandas import DataFrame
from tabulate import tabulate

with open("../../data/test/XSL0105_unit.json") as f:
    data = json.load(f)
df: DataFrame = DataFrame(data)
print(df.info())
print(tabulate(df, headers="keys", tablefmt='psql'))
