import enum
import re
from typing import List, Callable, Optional

from bp.constant import *


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
        self.list_blocks: List[Block] = []
        self.run_time = []

    def append_line(self, index, line):
        self.valued_line = line
        if not self.current_block:
            self.current_block = create_block(index, self.valued_line)
        else:
            if self.current_block.block_type is BlockType.BLOCK or self.current_block.block_type is BlockType.OBJECT:
                if not self.current_block.is_complete():
                    self.current_block.append_line(index, self.valued_line)
                else:
                    self.current_block.end = index - 1
                    self.run_time.append(process(self.current_block))
                    self.current_block = create_block(index, self.valued_line)
            else:
                self.run_time.append(process(self.current_block))
                self.current_block = create_block(index, self.valued_line)
        return self

    def try_to_close_block(self, index):
        if self.current_block and self.current_block.is_complete():
            self.current_block.end = index
            self.run_time.append(process(self.current_block))
            self.current_block = None
        return self

    # todo flat tree of bloks
    def process(self):
        return self.run_time


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

    def __str__(self):
        return "point:{}, type:{}, range:[{}, {}], ".format(self.structure_name, self.block_type, self.start, self.end)


def process(block: Block) -> Block:
    return get_process(block)(block)


def clean_string(line: str):
    return re.sub(r"[,{}'\s]+", "", line)


def field_processor(block: Block) -> Block:
    single_line = block.content[0][1]
    key, value = clean_string(str(single_line)).split(KEY_VALUE_DELIMITER)
    block.parsed[key.strip()] = value
    return block


def object_processor(block: Block) -> Block:
    return block_processor(block)


def block_processor(block: Block) -> Block:
    nested_builder = BlockBuilder()
    for index, potential_block in block.content[1:-1]:
        nested_builder \
            .append_line(index, potential_block) \
            .try_to_close_block(index)
    block.nested_blocks = nested_builder.process()
    return block


def value_processor(block: Block) -> Block:
    single_line = block.content[0][1]
    block.parsed[block.structure_name] = clean_string(str(single_line))
    return block


def get_process(block: Block) -> Callable[[Block], Block]:
    switcher = {
        BlockType.OBJECT: object_processor,
        BlockType.BLOCK: block_processor,
        BlockType.VALUE: value_processor,
        BlockType.FIELD: field_processor
    }
    return switcher.get(block.block_type, lambda x: block)


def is_block(line):
    return True if re.match(r"[\w\s]+=[\w\s]*?\{", line) else False


def is_global(line):
    return True if re.match(r"[\w\s]+\{", line) else False


def is_object(line):
    return True if re.match(r"\s*\{\s*", line) else False


def is_field(line):
    return KEY_VALUE_DELIMITER in line


def is_value(line):
    return True if re.match(r"[\S\D]+,", line) else False


def create_block(index, line) -> Block:
    if is_global(line):
        key = clean_string(line)
        inst = Block(key.strip(), BlockType.BLOCK, index)
        inst.append_line(index, line)
        return inst
    if is_block(line):
        key, value = clean_string(line).split(KEY_VALUE_DELIMITER)
        inst = Block(key.strip(), BlockType.BLOCK, index)
        inst.append_line(index, line)
        return inst
    elif is_object(line):
        inst = Block(BlockType.OBJECT.name, BlockType.OBJECT, index)
        inst.append_line(index, line)
        return inst
    elif is_field(line):
        key, value = clean_string(line).split(KEY_VALUE_DELIMITER)
        inst = Block(key, BlockType.FIELD, index)
        inst.append_line(index, line)
        return inst
    elif is_value(line):
        inst = Block(BlockType.VALUE.name, BlockType.VALUE, index)
        inst.append_line(index, line)
        return inst
    else:
        inst = Block(BlockType.NOT_PROCESSED, BlockType.NOT_PROCESSED, index)
        inst.append_line(index, line)
        return inst
