# coding: utf8
from __future__ import unicode_literals
from unittest import TestCase
from contextlib import contextmanager

from pyglottolog.lff import read_lff


@contextmanager
def lff(text):
    yield text.split('\n')


class Tests(TestCase):
    def test_read_lff(self):
        _lff = lff("""
Name [abcd1234], Name2 [abcd1235]
   Lang [abcd1236][abc]
""")
        res = list(read_lff('language', fp=_lff))
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].name, 'Lang')
        self.assertEqual(len(res[0].lineage), 2)
        self.assertEqual(res[0].lineage[0], ('Name', 'abcd1234', 'family'))

    def test_read_lff_error(self):
        _lff = lff("""
Name [acd1234], Name2 [abcd1235]
   Lang [abcd1236][abc]
""")
        with self.assertRaises(ValueError):
            list(read_lff('language', fp=_lff))
