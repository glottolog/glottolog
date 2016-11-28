# coding: utf8
from __future__ import unicode_literals, print_function, division

from six import text_type, PY2
from mock import Mock
from clldutils.testing import capture

from pyglottolog.tests.util import WithRepos
from pyglottolog.languoids import Level


class Tests(WithRepos):
    def test_tree2lff(self):
        from pyglottolog.cli import tree2lff

        tree2lff(
            Mock(repos=self.repos),
            out_paths={
                Level.language: self.tmp_path('lff.txt'),
                Level.dialect: self.tmp_path('dff.txt'),
            })

    def test_tree(self):
        from pyglottolog.cli import tree

        with capture(tree, Mock(repos=self.repos, args=['abcd1234', 'language'])) as out:
            if not isinstance(out, text_type):
                out = out.decode('utf8')
            self.assertIn('<l>', out)
            self.assertNotIn('<d>', out)

    def test_check(self):
        from pyglottolog.cli import check_tree

        check_tree(Mock(args=[], repos=self.repos))

    def test_monster(self):
        from pyglottolog.cli import monster

        if not PY2:  # pragma: no cover
            return

        with capture(monster, Mock(repos=self.repos)) as out:
            assert out
