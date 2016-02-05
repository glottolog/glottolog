# coding: utf8
from __future__ import unicode_literals
from unittest import TestCase
import re


class Tests(TestCase):
    def test_ID_REGEX(self):
        from pyglottolog.languoids import ID_REGEX

        pattern = re.compile(ID_REGEX + '$')
        for valid in [
            'abcd1234',
            'a12d3456',
            'NOCODE',
            'NOCODE_abd',
            'NOCODE_1',
        ]:
            self.assertIsNotNone(pattern.match(valid))

        for invalid in [
            'abcd123',
            '12d3456',
            'aNOCODE',
            'NOCODE.abd',
            'nocode',
        ]:
            self.assertIsNone(pattern.match(invalid))