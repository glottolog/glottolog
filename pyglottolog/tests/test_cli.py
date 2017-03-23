# coding: utf8
from __future__ import unicode_literals, print_function, division

from six import text_type, PY2
from mock import Mock, patch
from clldutils.testing import capture
from clldutils.path import copytree

from pyglottolog.tests.util import WithApi


class Tests(WithApi):
    def _args(self, *args):
        self.log = Mock()
        return Mock(repos=self.api, args=list(args), log=self.log)

    def test_show(self):
        from pyglottolog.commands import show

        with capture(show, self._args('**a:key**')) as out:
            self.assertIn('@misc'.encode('utf8') if PY2 else '@misc', out)

        with capture(show, self._args('a:key')) as out:
            self.assertIn('@misc'.encode('utf8') if PY2 else '@misc', out)

        with capture(show, self._args('abcd1236')) as out:
            self.assertIn('Classification'.encode('utf8') if PY2 else 'Classificat', out)

    def test_edit(self):
        from pyglottolog.commands import edit

        with patch('pyglottolog.commands.subprocess', Mock()):
            edit(self._args('abcd1236'))

    def test_create(self):
        from pyglottolog.commands import create

        with capture(create, self._args('abcd1234', 'new name', 'language')) as out:
            self.assertIn('Info written', out)
            self.assertIn(
                'new name', [c.name for c in self.api.languoid('abcd1234').children])

    def test_fts(self):
        from pyglottolog.commands import refindex, refsearch, langindex, langsearch

        with self.assertRaises(ValueError):
            refsearch(self._args('Harzani year:1334'))

        refindex(self._args())
        with capture(refsearch, self._args('Harzani year:1334')) as out:
            self.assertIn("'Abd-al-'Ali Karang", out)

        langindex(self._args())
        with capture(langsearch, self._args('id:abcd*')) as out:
            self.assertIn("abcd1234", out)

        with capture(langsearch, self._args('classification')) as out:
            self.assertIn("abcd1234", out)

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
        from pyglottolog.commands import tree, ParserError

        with self.assertRaises(ParserError):
            tree(self._args())

        with self.assertRaises(ParserError):
            tree(self._args('xyz'))

        with capture(tree, self._args('abc', 'language')) as out:
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

        with capture(check, self._args('refs')):
            pass

        with capture(check, self._args()) as out:
            self.assertIn('family', out)
        for call in self.log.error.call_args_list:
            self.assertIn('unregistered glottocode', call[0][0])
        self.assertEqual(self.log.error.call_count, 4)

        copytree(
            self.api.tree.joinpath('abcd1234', 'abcd1235'),
            self.api.tree.joinpath('abcd1235'))

        with capture(check, self._args()):
            self.assertIn(
                'duplicate glottocode',
                ''.join(c[0][0] for c in self.log.error.call_args_list))
            self.assertEqual(self.log.error.call_count, 6)

    def test_monster(self):
        from pyglottolog.commands import bib

        if not PY2:  # pragma: no cover
            return

        with capture(bib, self._args()) as out:
            assert out
