# coding: utf8
from __future__ import unicode_literals, print_function, division

from mock import Mock
from clldutils.testing import capture

from pyglottolog.tests.util import WithRepos


class Tests(WithRepos):
    def test_tree2lff(self):
        from pyglottolog.cli import tree2lff

        tree2lff(Mock(repos=self.repos))

    def test_check(self):
        from pyglottolog.cli import check_tree

        check_tree(Mock(repos=self.repos))

    def test_monster(self):
        from pyglottolog.cli import monster

        with capture(monster, Mock(repos=self.repos)) as out:
            assert out
