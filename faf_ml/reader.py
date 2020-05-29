import os
import re
from typing import List

KEY_VALUE_DELIMITER = "="
BLOCK_DELIMITER = ","
START_BLOCK_CHART = "{"
END_BLOCK_CHART = "},"


class BlockType(object):

    @staticmethod
    def get_instances(line):
        if "}" not in line:
            key, value = line.split(KEY_VALUE_DELIMITER)
            inst = BlockType(key.strip())
            inst.append_line(line)
            return inst
        else:
            return None

    def __init__(self, name):
        self.structure_name = name
        self.content = []
        self.parsed = {}
        self.nested_blocks: List[BlockType] = []
        self.level = 0

    def open_block(self):
        self.level += 1

    def close_block(self):
        self.level -= 1

    def is_complete(self):
        return self.level == 0 and self.structure_name and len(self.content) != 0

    def append_line(self, line):
        if START_BLOCK_CHART in line:
            self.open_block()
        elif END_BLOCK_CHART in line:
            self.close_block()
        self.content.append(line.strip())

    # todo rewrite to tree
    def parse_block(self):
        # for constant
        if len(self.content) == 1:
            single_line = self.content[0][:-1]
            if KEY_VALUE_DELIMITER in single_line:
                key, value = str(single_line).split(KEY_VALUE_DELIMITER)
                self.parsed[key.strip()] = value.replace(",", "").replace("'", "").strip()
            else:
                self.parsed['value'] = single_line.replace(",", "").replace("'", "").strip()
        else:
            block_inst = None
            for potential_block in self.content[1:-1]:
                if block_inst:
                    if not block_inst.is_complete():
                        block_inst.append_line(potential_block)
                    else:
                        block_inst = None
                if not block_inst:
                    if BlockType.is_block(potential_block):
                        block_inst = BlockType.get_instances(potential_block)
                        self.nested_blocks.append(block_inst)
                    elif BlockType.is_field(potential_block):
                        key, value = str(potential_block).split(KEY_VALUE_DELIMITER)
                        self.parsed[key.strip()] = value.replace(",", "").replace("'", "").strip()
                    elif BlockType.is_value(potential_block):
                        if "value" not in self.parsed:
                            self.parsed["value"] = [potential_block.replace(",", "").replace("'", "").strip()]
                        else:
                            self.parsed["value"].append(potential_block.replace(",", "").replace("'", "").strip())

    def flat_att(self):
        for block in self.nested_blocks:
            block.parse_block()
            block.flat_att()
            if len(block.nested_blocks) == 0:
                self.parsed[block.structure_name] = block.parsed


    @staticmethod
    def is_block(line):
        return True if re.match(r"[\w\s=]+{", line) else False

    @staticmethod
    def is_field(line):
        return KEY_VALUE_DELIMITER in line

    @staticmethod
    def is_value(line):
        return True if re.match(r"['\w]+,", line) else False


def __str__(self):
    return "{}:{}".format(self.structure_name, len(self.content))


class BPReader(object):
    BP_EXTENSIONS = ".bp"
    GLOBAL_NAME_STRUCTURE = re.compile(r"^\w+\s*{", re.MULTILINE | re.IGNORECASE)

    def __init__(self, file_path):
        self._raw_unit = []
        self._paths_bp = [os.path.join(root, _file) for root, dirs, files in os.walk(file_path) for _file in files if
                          self.BP_EXTENSIONS in _file][:1]

    def parse(self):
        for path in self._paths_bp:
            is_global_structure: bool = False
            crr_block = None
            high_content = []
            with open(path, "r") as f:
                for line in f:
                    if not is_global_structure or self.GLOBAL_NAME_STRUCTURE.search(line):
                        is_global_structure = True
                    else:
                        if crr_block:
                            if crr_block.is_complete():
                                print(crr_block.structure_name)
                                crr_block.parse_block()
                                crr_block.flat_att()
                                high_content.append(crr_block)
                                crr_block = BlockType.get_instances(line)
                            else:
                                crr_block.append_line(line)
                        else:
                            crr_block = BlockType.get_instances(line)

            self._raw_unit.append(high_content)


if __name__ == '__main__':
    reader = BPReader("/tmp/bp")
    reader.parse()
