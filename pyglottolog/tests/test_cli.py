# coding: utf8
from __future__ import unicode_literals, print_function, division

from mock import Mock

from pyglottolog.tests.util import WithRepos


class Tests(WithRepos):
    def test_check(self):
        from pyglottolog.cli import check_tree

        check_tree(Mock(repos=self.tmp_path().as_posix()))
