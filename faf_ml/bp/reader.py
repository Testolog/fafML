import json
import os

from bp.block import BlockBuilder
from bp.constant import BP_EXTENSIONS


def read(file_path):
    result_block = {}
    if os.path.isdir(file_path):
        files = [os.path.join(root, _file) for root, dirs, files in os.walk(file_path) for _file in files if
                 BP_EXTENSIONS in _file]
    else:
        if BP_EXTENSIONS in file_path:
            files = [file_path]
        else:
            raise NameError("not correct type")
    for path in files:
        crr_block = BlockBuilder()
        with open(path, "r") as f:
            for index, line in enumerate(f):
                crr_block.append_line(index + 1, line).try_to_close_block()
        result_block[os.path.basename(path)] = [_.parsed for _ in crr_block.process()]
    return result_block


if __name__ == '__main__':
    flow_data = read("../data/test/XSL0105_unit.bp")
    json.dump(flow_data, open("../data/test/XSL0105_unit.json", "w+"), indent=2)
