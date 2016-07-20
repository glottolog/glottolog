# coding: utf8
from __future__ import unicode_literals, print_function, division

from unittest import TestCase


class Tests(TestCase):
    def test_intersectall(self):
        from pyglottolog.util import intersectall

        self.assertEqual(intersectall([{1, 2}, {2, 3}, {3, 4}]), set())
        self.assertEqual(intersectall([{1, 2}, {2, 3}, {2, 4}]), {2})

    def test_unique(self):
        from pyglottolog.util import unique

        l = [1, 2, 3, 4, 5, 1, 2, 3, 4, 5, 6]
        self.assertEqual(len(set(l)), len(list(unique(l))))

    def test_group_first(self):
        from pyglottolog.util import group_first

        for key, items in group_first([(1, 2), (1, 3)]):
            self.assertEqual(key, 1)
            self.assertEqual(len(list(items)), 2)
            break
