from __future__ import unicode_literals

import pytest

from clldutils.path import read_text, write_text

from pyglottolog.references import BibFiles, BibFile, Entry


@pytest.fixture
def bibfiles(repos):
    return BibFiles.from_path(str(repos / 'references'))


def test_BibFile(tmpdir, bibfiles):
    bibfile = bibfiles['a.bib']
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

    entries = bibfile.load()  # FIXME
    bibfile.fname = str(tmpdir / ' newa.bib')
    bibfile.save(entries)

    bibfile.update(str(tmpdir / 'a.bib'))
    assert len(list(bibfile.iterentries())) == 3

    bibfile.update(bibfiles['b.bib'].fname)
    assert len(list(bibfile.iterentries())) == 1

    def visitor(entry):
        entry.fields['new_field'] = 'a'

    bibfile.visit(visitor=visitor)
    for entry in bibfile.iterentries():
        assert 'new_field' in entry.fields

    bibfile.visit(visitor=lambda e: True)
    assert len(bibfile.keys()) == 0


def test_Entry_lgcodes():
    assert Entry.lgcodes(None) == []


@pytest.fixture
def entry(repos):
    return Entry('x', 'misc', {'hhtype': 'grammar (computerized assignment from "xyz")'}, None)


def test_Entry(entry):
    assert entry.doctypes({'grammar': 1}) == ([1], 'xyz')
