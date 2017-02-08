# coding: utf8
from __future__ import unicode_literals, print_function, division

from pyglottolog.tests.util import WithApi


class Tests(WithApi):
    def test_HHTypes(self):
        hht = self.api.hhtypes
        self.assertEqual(hht['grammar'].rank, 17)

        prev = None
        for t in hht:
            if prev:
                self.assertGreater(prev, t)
            prev = t

        self.assertEqual(len(hht), 2)
        self.assertIn('rank', repr(hht[0]))
        self.assertEqual(hht.parse('grammar'), ['grammar'])
