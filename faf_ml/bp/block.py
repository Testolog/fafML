import enum
import re
from typing import List, Callable, Optional

from faf_ml.bp.constant import *


# todo
# 1. improve parser
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

    def append_line(self, index, line):
        line = re.sub(r"\s+", "", line)
        new_block = create_block(index, line)
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
        self.content = []
        self.start: int = start_line
        self.end: int = start_line
        self.parsed = {}
        self.level = 0
        self.level_block: List[Block] = []
        self.value_block: List[Block] = []

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
        active_block = get_first_not_closed_block(self.level_block, self)
        if block.block_type is BlockType.BLOCK or block.block_type is BlockType.OBJECT:
            active_block.level_block.append(block)
        else:
            if block.block_type is not BlockType.DELIMITER and block.block_type is not BlockType.NOT_PROCESSED:
                active_block.value_block.append(block)
            elif block.block_type is BlockType.NOT_PROCESSED:
                pass
                # print("error line:[{}, {}] type {} content:{}".format(block.start, block.end, block.block_type.name,
                #                                                       " ".join([_[1] for _ in block.content])))
        self + block
        self * block

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

    def __mul__(self, other: 'Block'):
        block_start_ = [_ for _ in self.level_block if not _.is_complete() and _.start is not other.start]
        for lvl_b in block_start_:
            lvl_b + other
            lvl_b * other


def process(block: Block) -> Block:
    return get_process(block)(block)


def clean_string(line: str):
    return re.sub(r"[,{}'\s]+", "", line)


def get_first_not_closed_block(blocks: List[Block], default: Optional[Block] = None) -> Block:
    last_block = next((b for b in blocks if not b.is_complete()), default)
    if last_block:
        if any([not _.is_complete() for _ in last_block.level_block]):
            last_block = get_first_not_closed_block(last_block.level_block, last_block)
    return last_block


def field_processor(block: Block) -> dict:
    single_line = block.content[0][1]
    key, value = clean_string(remove_comment(str(single_line))).split(KEY_VALUE_DELIMITER)
    return {key: value}


def value_processor(block: Block) -> str:
    return clean_string(str(block.content[0][1]))


def get_process(block: Block) -> Callable[[Block], Block]:
    switcher = {
        # BlockType.OBJECT: object_processor,
        # BlockType.BLOCK: block_processor,
        BlockType.VALUE: value_processor,
        BlockType.FIELD: field_processor
    }
    return switcher.get(block.block_type, lambda x: block)


def is_block(line):
    return True if re.match(r"\w+=\w*?\{", line, re.IGNORECASE | re.MULTILINE) else False


def is_global(line):
    return True if re.match(r"\w+\{", line, re.IGNORECASE | re.MULTILINE) else False


def is_object(line):
    return True if re.match(r"{", line, re.IGNORECASE | re.MULTILINE) else False


def is_field(line):
    return KEY_VALUE_DELIMITER in line


def is_value(line):
    return True if re.match(r"[\w'<>_\-\.\(\)\*]+,", line, re.IGNORECASE | re.MULTILINE) else False


def is_comment(line):
    return True if re.match(r"(#.+|--.+)", line, re.IGNORECASE | re.MULTILINE) else False


def remove_comment(line):
    return re.sub(r"((?<=\-\-)|(?<=\#)).+", "", line).replace("#", "").replace("--", "")


def is_delimiter(line):
    return True if re.match(r"[},]+", line, re.IGNORECASE | re.MULTILINE) else False


def create_block(line_number, line) -> Block:
    if is_global(line):
        key = clean_string(line)
        inst = Block(key.strip(), BlockType.BLOCK, line_number)
        inst.append_line(line_number, line)
        return inst
    elif is_block(line):
        key, value = clean_string(line).split(KEY_VALUE_DELIMITER)
        inst = Block(key.strip(), BlockType.BLOCK, line_number)
        inst.append_line(line_number, line)
        return inst
    elif is_comment(line):
        inst = Block(BlockType.COMMENT.name, BlockType.NOT_PROCESSED, line_number)
        inst.append_line(line_number, line)
        return inst
    elif is_object(line):
        inst = Block("{}_{}".format(BlockType.OBJECT.name, line_number), BlockType.OBJECT, line_number)
        inst.append_line(line_number, line)
        return inst
    elif is_field(line):
        key, value = clean_string(remove_comment(line)).split(KEY_VALUE_DELIMITER)
        inst = Block(key, BlockType.FIELD, line_number)
        inst.append_line(line_number, line)
        return inst
    elif is_value(line):
        inst = Block(BlockType.VALUE.name, BlockType.VALUE, line_number)
        inst.append_line(line_number, line)
        return inst
    elif is_delimiter(line):
        inst = Block(BlockType.DELIMITER.name, BlockType.DELIMITER, line_number)
        inst.append_line(line_number, line)
        return inst
    else:
        inst = Block(BlockType.NOT_PROCESSED, BlockType.NOT_PROCESSED, line_number)
        inst.append_line(line_number, line)
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
