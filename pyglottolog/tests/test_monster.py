# coding: utf8
from __future__ import unicode_literals, print_function, division

from clldutils.testing import capture
from pyglottolog.tests.util import WithRepos


class Tests(WithRepos):
    def test_main(self):
        from pyglottolog.monster import main

        with capture(main, repos=self.repos) as out:
            self.assertEqual(len(out.splitlines()), 70)
            self.assertIn('2 splitted', out)
            self.assertIn('2 merged', out)
