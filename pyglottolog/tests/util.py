# coding: utf8
from __future__ import unicode_literals, print_function, division

from clldutils.path import Path, copytree
from clldutils.testing import WithTempDir


class WithRepos(WithTempDir):
    def setUp(self):
        WithTempDir.setUp(self)
        self.repos = self.tmp_path()

        self.languoids = self.tmp_path('languoids')
        copytree(Path(__file__).parent.joinpath('data', 'languoids'), self.languoids)
        self.tree = self.languoids.joinpath('tree')

        self.references = self.tmp_path('references')
        copytree(Path(__file__).parent.joinpath('data', 'references'), self.references)

        self.tmp_path('build').mkdir()
