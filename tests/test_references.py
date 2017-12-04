from __future__ import unicode_literals

import pytest

from clldutils.path import read_text, write_text


def test_Entry(api):
    from pyglottolog.references import Entry

    assert Entry.lgcodes(None) == []
    e = Entry(
        'x', 'misc', {'hhtype': 'grammar (computerized assignment from "xyz")'}, None)
    assert e.doctypes({'grammar': 1}) == ([1], 'xyz')


def test_HHTypes(api):
    hht = api.hhtypes
    assert hht['grammar'].rank == 17
    assert 'grammar' in hht

    prev = None
    for t in hht:
        if prev:
            assert prev > t
        prev = t

    assert len(hht) == 2
    assert 'rank' in repr(hht[0])
    assert hht.parse('grammar') == ['grammar']


def test_BibFile(tmpdir, api):
    bibfile = api.bibfiles['a.bib']
    assert bibfile['a:key'].type == 'misc'
    assert bibfile['s:Andalusi:Turk'].key == 's:Andalusi:Turk'

    for entry in bibfile.iterentries():
        if entry.key == 'key':
            assert len(list(entry.languoids({'abc': 1})[0])) == 1

    with pytest.raises(KeyError):
        bibfile['xyz']

    assert len(list(bibfile.iterentries())) == 3

    lines = [line for line in read_text(bibfile.fname).split('\n')
             if not line.strip().startswith('glottolog_ref_id')]
    write_text(str(tmpdir /'a.bib'), '\n'.join(lines))
    bibfile.update(str(tmpdir / 'a.bib'))
    assert len(list(bibfile.iterentries())) == 3

    bibfile.update(api.bibfiles['b.bib'].fname)
    assert len(list(bibfile.iterentries())) == 1

    def visitor(entry):
        entry.fields['new_field'] = 'a'

    bibfile.visit(visitor=visitor)
    for entry in bibfile.iterentries():
        assert 'new_field' in entry.fields

    bibfile.visit(visitor=lambda e: True)
    assert len(bibfile.keys()) == 0


def test_Isbns(api):
    from pyglottolog.references import Isbns, Isbn

    assert Isbns.from_field('9783866801929, 3866801920') == \
           [Isbn('9783866801929')]

    assert Isbns.from_field('978-3-86680-192-9 3-86680-192-0') == \
           [Isbn('9783866801929')]

    with pytest.raises(ValueError, match=r'pattern'):
        Isbns.from_field('9783866801929 spam, 3866801920')

    with pytest.raises(ValueError, match=r'delimiter'):
        Isbns.from_field('9783866801929: 3866801920')

    assert Isbns.from_field('9780199593569, 9780191739385').to_string() == \
           '9780199593569, 9780191739385'


def test_Isbn(api):
    from pyglottolog.references import Isbn

    with pytest.raises(ValueError, match='length'):
        Isbn('978-3-86680-192-9')

    with pytest.raises(ValueError, match=r'length'):
        Isbn('03-86680-192-0')

    with pytest.raises(ValueError, match=r'0 instead of 9'):
        Isbn('9783866801920')

    with pytest.raises(ValueError, match=r'9 instead of 0'):
        Isbn('3866801929')

    assert Isbn('9783866801929').digits == '9783866801929'
    assert Isbn('3866801920').digits == '9783866801929'

    twins = Isbn('9783866801929'), Isbn('9783866801929')
    assert twins[0] == twins[1]
    assert len(set(twins)) == 1
    assert not twins[0] != twins[1]

    assert repr(Isbn('9783866801929')) in \
           ["Isbn(u'9783866801929')", "Isbn('9783866801929')"]
