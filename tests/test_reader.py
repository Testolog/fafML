from unittest import TestCase, main

from faf_ml.bp.block import BlockBuilder


class BPBuildersTestCases(TestCase):

    def test_correct_parse_value(self):
        bb = BlockBuilder()
        expect = {"A": {"a": "b"}}
        tmp = """A {
        a='b'
        }"""
        for index, line in enumerate(tmp.splitlines()):
            bb.append_line(index, line).try_to_close_block()
        real = bb.process()[0]
        self.assertEqual(expect, real.parsed, msg="test_correct_parse_block")

    def test_correct_parse_block(self):
        bb = BlockBuilder()
        expect = {"A": {"a": ["b"]}}
        tmp = """A {
        a={
        'b',
        },
        }"""
        for index, line in enumerate(tmp.splitlines()):
            bb.append_line(index, line).try_to_close_block()
        real = bb.process()[0]
        self.assertEqual(expect, real.parsed, msg="test_correct_parse_block")

    def test_correct_parse_object(self):
        bb = BlockBuilder()
        expect = {"A": {"object_0": ["b"], "object_1": ["b"]}}
        tmp = """A {
        {
        'b',
        },
        {
        'b',
        },
        }"""
        for index, line in enumerate(tmp.splitlines()):
            bb.append_line(index, line).try_to_close_block()
        real = bb.process()[0]
        self.assertEqual(expect, real.parsed, msg="test_correct_parse_block")


if __name__ == '__main__':
    main()
