import enum
import os
import re
from typing import List, Optional

KEY_VALUE_DELIMITER = "="
VALUE_DELIMITER = ","
START_BLOCK_CHART = "{"
END_BLOCK_CHART = "},"


class BlockType(enum.Enum):
    OBJECT = enum.auto()
    BLOCK = enum.auto()
    FIELD = enum.auto()
    ARRAY = enum.auto()
    VALUE = enum.auto()
    NOT_PROCESSED = enum.auto()

    def __str__(self):
        return self.name


class BlockBuilder(object):

    def __init__(self):
        self.current_block: Optional[Block] = None
        self.valued_line = None
        self.list_blocks = []

    def append_line(self, index, line):
        #todo process line with
        self.valued_line = line
        if not self.current_block:
            self.current_block = BlockBuilder._new_block(index, self.valued_line)
        else:
            if self.current_block.block_type is BlockType.BLOCK or self.current_block.block_type is BlockType.OBJECT:
                if not self.current_block.is_complete():
                    self.current_block.append_line(index, self.valued_line)
                else:
                    self.current_block.end = index - 1
                    self.list_blocks.append(self.current_block)
                    self.current_block = self._new_block(index, self.valued_line)
            else:
                self.list_blocks.append(self.current_block)
                self.current_block = self._new_block(index, self.valued_line)
        return self

    @staticmethod
    def _new_block(index, line):
        if Block.is_block(line):
            key, value = Block.clean_string(line).split(KEY_VALUE_DELIMITER)
            inst = Block(key.strip(), BlockType.BLOCK, index)
            inst.append_line(index, line)
            return inst
        elif Block.is_object(line):
            inst = Block(BlockType.OBJECT.value, BlockType.OBJECT, index)
            inst.append_line(index, line)
            return inst
        elif Block.is_field(line):
            key, value = Block.clean_string(line).split(KEY_VALUE_DELIMITER)
            inst = Block(key, BlockType.FIELD, index)
            inst.append_line(index, line)
            return inst
        elif Block.is_value(line):
            inst = Block(BlockType.VALUE.name, BlockType.VALUE, index)
            inst.append_line(index, line)
            return inst
        else:
            inst = Block(BlockType.NOT_PROCESSED, BlockType.NOT_PROCESSED, index)
            inst.append_line(index, line)
            return inst

    def try_to_close_block(self, index):
        if self.current_block and self.current_block.is_complete():
            self.current_block.end = index
            self.list_blocks.append(self.current_block)
            self.current_block = None
        return self

    def process(self):
        for block in self.list_blocks:
            if block.block_type is not BlockType.NOT_PROCESSED:
                block.parse_block()
            else:
                print("error: {} range_lines:[{}, {}]".format("\n".join([l for _, l in block.content]), block.start,
                                                              block.end))
        return self.list_blocks


class Block(object):

    def __init__(self, name, block_type, start_line: int):
        self.structure_name = name
        self.block_type = block_type
        self.content = []
        self.start: int = start_line
        self.end: int = start_line
        self.parsed = {}
        self.nested_blocks: List[Block] = []
        self.level = 0

    def open_block(self):
        self.level += 1

    def close_block(self):
        self.level -= 1

    def is_complete(self):
        return self.level == 0 and self.structure_name and len(self.content) != 0

    def append_line(self, index, line):
        if START_BLOCK_CHART in line:
            self.open_block()
        elif END_BLOCK_CHART in line:
            self.close_block()
        self.content.append((index, line.strip()))

    def parse_block(self):
        if self.block_type is BlockType.FIELD:
            single_line = self.content[0]
            key, value = self.clean_string(str(single_line)).split(KEY_VALUE_DELIMITER)
            self.parsed[key.strip()] = value
        elif self.block_type is BlockType.VALUE:
            single_line = self.content[0]
            self.parsed[self.structure_name] = self.clean_string(str(single_line))
        elif self.block_type is BlockType.BLOCK:
            nested_builder = BlockBuilder()
            for index, potential_block in self.content[1:-1]:
                nested_builder \
                    .append_line(index, potential_block) \
                    .try_to_close_block(index)
            self.nested_blocks = nested_builder.process()
        elif self.block_type is BlockType.OBJECT:
            nested_builder = BlockBuilder()
            for index, potential_block in self.content[1:-1]:
                nested_builder \
                    .append_line(index, potential_block) \
                    .try_to_close_block(index)
            self.nested_blocks = nested_builder.process()

    def flat_att(self):
        for block in self.nested_blocks:
            block.parse_block()
            if len(block.nested_blocks) == 0:
                self.parsed[block.structure_name] = block.parsed

    @staticmethod
    def clean_string(line: str):
        return re.sub(r"[,{}'\s]+", "", line)

    @staticmethod
    def is_block(line):
        return True if re.match(r"[\w\s=]+{", line) else False

    @staticmethod
    def is_object(line):
        return True if re.match(r"\s*\{\s*", line) else False

    @staticmethod
    def is_field(line):
        return KEY_VALUE_DELIMITER in line

    @staticmethod
    def is_value(line):
        return True if re.match(r"[\S\D]+,", line) else False

    def __str__(self):
        return "point:{}, type:{}, range:[{}, {}], ".format(self.structure_name, self.block_type, self.start, self.end)


class BPReader(object):
    BP_EXTENSIONS = ".bp"
    GLOBAL_NAME_STRUCTURE = re.compile(r"^\w+\s*{", re.MULTILINE | re.IGNORECASE)

    def __init__(self, file_path):
        self.raw_unit = []
        self.paths_bp = [os.path.join(root, _file) for root, dirs, files in os.walk(file_path) for _file in files if
                         self.BP_EXTENSIONS in _file][:1]

    def parse(self):
        for path in self.paths_bp:
            is_global_structure: bool = False
            crr_block = BlockBuilder()
            high_content = []
            with open(path, "r") as f:
                for index, line in enumerate(f):
                    if not is_global_structure or self.GLOBAL_NAME_STRUCTURE.search(line):
                        is_global_structure = True
                    else:
                        crr_block \
                            .append_line(index + 1, line) \
                            .try_to_close_block(index + 1)
            high_content = crr_block.process()
            self.raw_unit.append(high_content)


if __name__ == '__main__':
    reader = BPReader("/tmp/bp")
    reader.paths_bp = ["../XSL0105_unit.bp"]
    reader.parse()
