from __future__ import unicode_literals

import pytest

from clldutils.path import read_text, write_text

from pyglottolog.references import BibFiles, BibFile, Entry


def test_BibFiles_getitem(bibfiles):
    bf = bibfiles[0]
    assert len(list(bf.iterentries())) == 3 and bf.size and bf.mtime


def test_BibFiles_roundtrip(capsys, bibfiles_copy):
    bibfiles_copy.roundtrip_all()
    assert 'a.bib' in capsys.readouterr()[0]


def test_BibFile(tmpdir, bibfiles):
    bf = bibfiles['a.bib']
    assert bf['a:key'].type == 'misc'
    assert bf['s:Andalusi:Turk'].key == 's:Andalusi:Turk'

    for entry in bf.iterentries():
        if entry.key == 'key':
            assert len(list(entry.languoids({'abc': 1})[0])) == 1

    with pytest.raises(KeyError):
        bf['xyz']

    assert len(list(bf.iterentries())) == 3

    lines = [line for line in read_text(bf.fname).split('\n')
             if not line.strip().startswith('glottolog_ref_id')]
    write_text(str(tmpdir / 'a.bib'), '\n'.join(lines))

    entries = bf.load()  # FIXME
    bf.fname = str(tmpdir / ' newa.bib')
    bf.save(entries)

    bf.update(str(tmpdir / 'a.bib'))
    assert len(list(bf.iterentries())) == 3

    bf.update(bibfiles['b.bib'].fname)
    assert len(list(bf.iterentries())) == 1

    def visitor(entry):
        entry.fields['new_field'] = 'a'

    bf.visit(visitor=visitor)
    for entry in bf.iterentries():
        assert 'new_field' in entry.fields

    bf.visit(visitor=lambda e: True)
    assert len(bf.keys()) == 0


def test_BibFile_show_characters(capsys, bibfiles):
    bibfiles['b.bib'].show_characters()
    assert 'CJK UNIFIED IDEOGRAPH' in capsys.readouterr()[0]


def test_Entry_lgcodes():
    assert Entry.lgcodes(None) == []


@pytest.fixture
def entry():
    return Entry('x', 'misc', {'hhtype': 'grammar (computerized assignment from "xyz")'}, None)


def test_Entry(entry):
    assert entry.doctypes({'grammar': 1}) == ([1], 'xyz')
