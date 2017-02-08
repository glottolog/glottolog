# coding: utf8
from __future__ import unicode_literals, print_function, division

from six import text_type, PY2
from mock import Mock
from clldutils.testing import capture

from pyglottolog.tests.util import WithApi
from pyglottolog.languoids import Level


class Tests(WithApi):
    def _args(self, *args):
        return Mock(repos=self.api, args=list(args))

    def test_fts(self):
        from pyglottolog.commands import ftsindex, ftssearch

        ftsindex(self._args())
        with capture(ftssearch, self._args('Harzani year:1334')) as out:
            self.assertIn("'Abd-al-'Ali Karang", out)

    def test_metadata(self):
        from pyglottolog.commands import metadata

        with capture(metadata, self._args()) as out:
            self.assertIn("longitude", out)

    def test_lff(self):
        from pyglottolog.commands import tree2lff, lff2tree

        tree2lff(self._args())
        with self.api.build_path('dff.txt').open(encoding='utf8') as fp:
            dfftxt = fp.read().replace('dialect', 'Dialect Name')
        with self.api.build_path('dff.txt').open('w', encoding='utf8') as fp:
            fp.write(dfftxt)
        with capture(lff2tree, self._args()) as out:
            self.assertIn('git status', out)
        self.assertEqual(self.api.languoid('abcd1236').name, 'Dialect Name')
        tree2lff(self._args())
        with self.api.build_path('dff.txt').open(encoding='utf8') as fp:
            self.assertEqual(dfftxt, fp.read())

    def test_index(self):
        from pyglottolog.commands import index

        index(self._args())
        self.assertEqual(
            len(list(self.repos.joinpath('languoids').glob('*.md'))), 7)

    def test_tree(self):
        from pyglottolog.commands import tree

        with capture(tree, self._args('abcd1235', 'language')) as out:
            if not isinstance(out, text_type):
                out = out.decode('utf8')
            self.assertIn('language', out)
            self.assertNotIn('dialect', out)

    def test_newick(self):
        from pyglottolog.commands import newick

        with capture(newick, self._args('abcd1235')) as out:
            self.assertIn('language', out)

    def test_check(self):
        from pyglottolog.commands import check

        with capture(check, self._args()) as out:
            self.assertIn('family', out)

    def test_monster(self):
        from pyglottolog.commands import bib

        if not PY2:  # pragma: no cover
            return

        with capture(bib, self._args()) as out:
            assert out
