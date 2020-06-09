import json
import os

from faf_ml.bp.block import BlockBuilder
from faf_ml.bp.constant import BP_EXTENSIONS


def read_files(file_path):
    result_block = {}
    files = [os.path.join(root, _file) for root, dirs, files in os.walk(file_path) for _file in files if
             BP_EXTENSIONS in _file]
    for path in files:
        result_block[os.path.basename(path)] = read_file(path)
    return result_block


def read_file(file_path):
    crr_block = BlockBuilder()
    with open(file_path, "r") as f:
        for index, line in enumerate(f):
            crr_block.append_line(index + 1, line).try_to_close_block()
    return crr_block.process()


if __name__ == '__main__':
    flow_data = read_file("../../data/test/XSL0105_unit.bp")
    json.dump(flow_data[0].parsed, open("../../data/test/XSL0105_unit.json", "w+"), indent=2)
