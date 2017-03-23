# coding: utf8
from __future__ import unicode_literals, print_function, division

from clldutils.path import read_text, write_text

from pyglottolog.tests.util import WithApi


class Tests(WithApi):
    def test_Entry(self):
        from pyglottolog.references import Entry

        self.assertEqual(Entry.lgcodes(None), [])
        e = Entry(
            'x', 'misc', {'hhtype': 'grammar (computerized assignment from "xyz")'}, None)
        self.assertEqual(e.doctypes({'grammar': 1}), ([1], 'xyz'))

    def test_HHTypes(self):
        hht = self.api.hhtypes
        self.assertEqual(hht['grammar'].rank, 17)
        self.assertIn('grammar', hht)

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
        self.assertEqual(bibfile['a:key'].type, 'misc')
        self.assertEqual(bibfile['s:Andalusi:Turk'].key, 's:Andalusi:Turk')

        for entry in bibfile.iterentries():
            if entry.key == 'key':
                self.assertEqual(len(list(entry.languoids({'abc': 1})[0])), 1)

        with self.assertRaises(KeyError):
            bibfile['xyz']

        self.assertEqual(len(list(bibfile.iterentries())), 3)

        lines = [line for line in read_text(bibfile.fname).split('\n')
                 if not line.strip().startswith('glottolog_ref_id')]
        write_text(self.tmp_path('a.bib'), '\n'.join(lines))
        bibfile.update(self.tmp_path('a.bib'))
        self.assertEqual(len(list(bibfile.iterentries())), 3)

        bibfile.update(self.api.bibfiles['b.bib'].fname)
        self.assertEqual(len(list(bibfile.iterentries())), 1)

        def visitor(entry):
            entry.fields['new_field'] = 'a'

        bibfile.visit(visitor=visitor)
        for entry in bibfile.iterentries():
            self.assertIn('new_field', entry.fields)

        bibfile.visit(visitor=lambda e: True)
        self.assertEqual(len(bibfile.keys()), 0)
