# coding: utf8
from __future__ import unicode_literals, print_function, division

from clldutils.path import Path, copytree
from clldutils.testing import WithTempDir

from pyglottolog.api import Glottolog


class WithApi(WithTempDir):
    def setUp(self):
        WithTempDir.setUp(self)
        self.repos = self.tmp_path('repos')
        copytree(Path(__file__).parent.joinpath('data'), self.repos)
        self.api = Glottolog(self.repos)
