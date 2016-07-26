# coding: utf8
from __future__ import unicode_literals, print_function, division

from clldutils.path import Path, copytree
from clldutils.testing import WithTempDir


class WithRepos(WithTempDir):
    def setUp(self):
        from pyglottolog.languoids import Languoid, Level

        WithTempDir.setUp(self)
        self.repos = self.tmp_path()
        self.languoids = self.tmp_path('languoids')
        self.languoids.mkdir()
        self.tree = self.languoids.joinpath('tree')
        self.tree.mkdir()
        self.tmp_path('build').mkdir()

        f = Languoid.from_name_id_level('family', 'abcd1234', Level.family)
        f.write_info(self.tree.joinpath(f.id))

        l = Languoid.from_name_id_level(
            'language', 'abcd1235', Level.language,
            latitude=0.5, longitude=0.5, macroareas=('a', 'b'), hid='abc')
        l.write_info(self.tree.joinpath(f.id, l.id))

        d = Languoid.from_name_id_level('dialect', 'abcd1236', Level.dialect)
        d.write_info(self.tree.joinpath(f.id, l.id, d.id))

        self.references = self.tmp_path('references')
        copytree(Path(__file__).parent.joinpath('data', 'references'), self.references)
