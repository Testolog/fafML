import enum
import re
from itertools import takewhile
from typing import List, Callable, Optional, Tuple

from faf_ml.bp.constant import *


# todo
# 1. improve parser
# 2. counter for objects blocks
class BlockType(enum.Enum):
    OBJECT = enum.auto()
    BLOCK = enum.auto()
    FIELD = enum.auto()
    ARRAY = enum.auto()
    VALUE = enum.auto()
    DELIMITER = enum.auto()
    NOT_PROCESSED = enum.auto()
    COMMENT = enum.auto()

    def __str__(self):
        return self.name


class BlockBuilder(object):

    def __init__(self):
        self.current_block: Optional[Block] = None
        self.valued_line = ""
        self.list_blocks: List[Block] = []
        self.run_time: List[Block] = []

    def append_line(self, line_number, raw_line):
        _line = re.sub(r"\s+", "", raw_line)
        new_block = create_block(line_number, _line)
        if not self.current_block:
            self.current_block = new_block
        else:
            if not self.current_block.is_complete():
                self.current_block.append_block(new_block)
            else:
                self.run_time.append(self.current_block)
                self.current_block = new_block
        return self

    def try_to_close_block(self):
        if self.current_block and self.current_block.is_complete():
            self.run_time.append(self.current_block)
            self.current_block = None
        return self

    # todo flat tree of bloks
    def process(self):
        return [_.process() for _ in self.run_time]


class Block(object):

    def __init__(self, name, block_type, start_line: int):
        self.structure_name = name
        self.block_type = block_type
        self.content: List[Tuple[int, str]] = []
        self.start: int = start_line
        self.end: int = start_line
        self.parsed = {}
        self.level = 0
        self.level_block: List[Block] = []
        self.value_block: List[Block] = []
        self.not_processed: List[Block] = []
        self.number_objects = 0

    def open_block(self):
        self.level += 1

    def close_block(self):
        self.level -= 1

    def is_complete(self):
        return self.level == 0 and self.structure_name and len(self.content) != 0

    def append_line(self, line_number, row):
        if START_BLOCK_CHART in row:
            self.open_block()
        elif END_BLOCK_CHART in row:
            self.close_block()
        self.end = line_number
        self.content.append((line_number, row))

    def append_block(self, block):
        active_block = get_first_not_complete_block(self.level_block, self)
        self + block
        self.cascade_append(block)
        if block.block_type is BlockType.BLOCK:
            active_block.level_block.append(block)
        elif block.block_type is BlockType.OBJECT:
            block.structure_name = "object_{}".format(self.number_objects)
            self.number_objects += 1
            active_block.level_block.append(block)
        elif block.block_type is not BlockType.DELIMITER and block.block_type is not BlockType.NOT_PROCESSED:
            active_block.value_block.append(block)
        else:
            active_block.not_processed.append(block)

    def process(self):
        for vle_b in self.value_block:
            if vle_b.block_type is BlockType.VALUE:
                self.block_type = BlockType.ARRAY
                if self.structure_name in self.parsed:
                    self.parsed[self.structure_name].append(process(vle_b))
                else:
                    self.parsed[self.structure_name] = [process(vle_b)]
            else:
                if self.structure_name in self.parsed:
                    self.parsed[self.structure_name].update(process(vle_b))
                else:
                    self.parsed[self.structure_name] = process(vle_b)
        for lvl_b in self.level_block:
            lvl_b.process()
            if self.structure_name in self.parsed:
                self.parsed[self.structure_name].update(lvl_b.parsed)
            else:
                self.parsed[self.structure_name] = lvl_b.parsed
        return self

    def __str__(self):
        return "point:{}, type:{}, range:[{}, {}], ".format(self.structure_name, self.block_type, self.start, self.end)

    def __add__(self, other: 'Block'):
        for numb, line in other.content:
            self.append_line(numb, line)

    def cascade_append(self, other: 'Block'):
        for lvl_block in self.level_block:
            if not lvl_block.is_complete():
                lvl_block + other
                lvl_block.cascade_append(other)


def process(block: Block) -> Block:
    return get_process(block)(block)


def clean_string(raw_line: str):
    return re.sub(r"[,{}'\s]+", "", raw_line)


def get_first_not_complete_block(blocks: List[Block], default: Optional[Block] = None) -> Block:
    if len(blocks) == 0:
        return default
    else:
        block = blocks[0]
        if not block.is_complete():
            if len(block.level_block) > 0:
                return get_first_not_complete_block(block.level_block, block)
            else:
                return block
        else:
            return get_first_not_complete_block(blocks[1:], default)


def field_processor(block: Block) -> dict:
    single_line = block.content[0][1]
    key, value = clean_string(remove_comment(str(single_line))).split(KEY_VALUE_DELIMITER)
    return {key: value}


def value_processor(block: Block) -> str:
    return clean_string(str(block.content[0][1]))


def get_process(block: Block) -> Callable[[Block], Block]:
    switcher = {
        BlockType.VALUE: value_processor,
        BlockType.FIELD: field_processor
    }
    return switcher.get(block.block_type, lambda x: x)


def is_block(raw_line):
    return True if re.match(r"\w+=\w*?\{", raw_line, re.IGNORECASE | re.MULTILINE) else False


def is_global(raw_line):
    return True if re.match(r"\w+\{", raw_line, re.IGNORECASE | re.MULTILINE) else False


def is_object(raw_line):
    return True if re.match(r"{", raw_line, re.IGNORECASE | re.MULTILINE) else False


def is_field(raw_line):
    return KEY_VALUE_DELIMITER in raw_line


def is_value(raw_line):
    return True if re.match(r"[\w'<>_\-\.\(\)\*]+,", raw_line, re.IGNORECASE | re.MULTILINE) else False


def is_comment(raw_line):
    return True if re.match(r"(#.+|--.+)", raw_line, re.IGNORECASE | re.MULTILINE) else False


def remove_comment(raw_line):
    return re.sub(r"((?<=\-\-)|(?<=\#)).+", "", raw_line).replace("#", "").replace("--", "")


def is_delimiter(raw_line):
    return True if re.match(r"[},]+", raw_line, re.IGNORECASE | re.MULTILINE) else False


def get_key_from_line(raw_line):
    return "".join(takewhile(lambda x: x is not KEY_VALUE_DELIMITER, raw_line))


def create_block(line_number, raw_line) -> Block:
    get_actual_block = (
        (is_global, Block(clean_string(raw_line), BlockType.BLOCK, line_number)),
        (is_block, Block(get_key_from_line(clean_string(raw_line)), BlockType.BLOCK, line_number)),
        (is_comment, Block(BlockType.COMMENT.name, BlockType.NOT_PROCESSED, line_number)),
        (is_object, Block(BlockType.OBJECT.name, BlockType.OBJECT, line_number)),
        (is_field, Block(get_key_from_line(clean_string(remove_comment(raw_line))), BlockType.FIELD, line_number)),
        (is_value, Block(BlockType.VALUE.name, BlockType.VALUE, line_number)),
        (is_delimiter, Block(BlockType.DELIMITER.name, BlockType.DELIMITER, line_number))
    )
    inst = next((_inst for checker, _inst in get_actual_block if checker(raw_line)),
                Block(BlockType.NOT_PROCESSED, BlockType.NOT_PROCESSED, line_number))
    inst.append_line(line_number, raw_line)
    return inst


if __name__ == '__main__':
    t = """General = {
        BuildBones = {
            AimBone = 'Turret_Muzzle',
            BuildEffectBones = {
                'Turret_Muzzle',
            },
            PitchBone = 'Arm_Pitch',
            YawBone = 'Arm_Yaw',
        },
        Category = 'Construction',
        Classification = 'RULEUC_Engineer',
        CommandCaps = {
            RULEUCC_Attack = false,
            RULEUCC_CallTransport = true,
            RULEUCC_Capture = true,
            RULEUCC_Guard = true,
            RULEUCC_Move = true,
            RULEUCC_Nuke = false,
            RULEUCC_Patrol = true,
            RULEUCC_Pause = true,
            RULEUCC_Reclaim = true,
            RULEUCC_Repair = true,
            RULEUCC_RetaliateToggle = false,
            RULEUCC_Stop = true,
            RULEUCC_Transport = false,
        },
        ConstructionBar = true,
        FactionName = 'Seraphim',
        Icon = 'amph',
        SelectionPriority = 3,
        TechLevel = 'RULEUTL_Basic',
        UnitName = '<LOC xsl0105_name>Iya-istle',
        UnitWeight = 1,
    }"""
    bb = BlockBuilder()
    for index, line in enumerate(t.splitlines()):
        bb.append_line(index + 1, line).try_to_close_block()
    p = bb.process()
    print(p)
