# coding: utf8
from __future__ import unicode_literals, print_function, division

from pyglottolog.tests.util import WithRepos


class Tests(WithRepos):
    def test_HHTypes(self):
        from pyglottolog.references import HHTypes

        hht = HHTypes(repos=self.repos)
        self.assertEqual(hht['grammar'].rank, 17)

        prev = None
        for t in hht:
            if prev:
                self.assertGreater(prev, t)
            prev = t

        self.assertEqual(len(hht), 2)
        self.assertIn('rank', repr(hht[0]))
        self.assertEqual(HHTypes.parse('grammar'), ['grammar'])