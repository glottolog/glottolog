# coding: utf8
from __future__ import unicode_literals, print_function, division

from clldutils.path import read_text, write_text

from pyglottolog.tests.util import WithApi


class Tests(WithApi):
    def test_HHTypes(self):
        hht = self.api.hhtypes
        self.assertEqual(hht['grammar'].rank, 17)

        prev = None
        for t in hht:
            if prev:
                self.assertGreater(prev, t)
            prev = t

        self.assertEqual(len(hht), 2)
        self.assertIn('rank', repr(hht[0]))
        self.assertEqual(hht.parse('grammar'), ['grammar'])

    def test_BibFile(self):
        bibfile = self.api.bibfiles['a.bib']
        self.assertTrue(bibfile['a:key'].startswith('@misc'))
        self.assertTrue(bibfile['s:Andalusi:Turk'].startswith('@'))

        with self.assertRaises(KeyError):
            _ = bibfile['xyz']

        self.assertEqual(len(list(bibfile.iterentries())), 3)

        lines = [line for line in read_text(bibfile.fname).split('\n')
                 if not line.strip().startswith('glottolog_ref_id')]
        write_text(self.tmp_path('a.bib'), '\n'.join(lines))
        bibfile.update(self.tmp_path('a.bib'))
        self.assertEqual(len(list(bibfile.iterentries())), 3)

        bibfile.update(self.api.bibfiles['b.bib'].fname)
        self.assertEqual(len(list(bibfile.iterentries())), 1)
