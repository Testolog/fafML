import json

import faf_ml.bp.reader as reader

flow_data = reader.read("../data/test/XSL0105_unit.bp")
json.dump(flow_data, open("../data/test/XSL0105_unit.json", "w+"), indent=2)
