from __future__ import unicode_literals

import pytest

from pyglottolog.languoids import (Languoid, EndangermentStatus,
    Glottocodes, Glottocode, Level, Country, Reference, Macroarea,
    ClassificationComment, EthnologueComment)


def test_legacy_imports():
    from pyglottolog import objects
    assert objects.Glottocode is Glottocode
    assert objects.Macroarea is Macroarea
    assert objects.Level is Level
    assert objects.Reference is Reference


def test_Glottocodes(tmpdir):
    json = tmpdir / 'glottocodes.json'
    json.write_text('{}', encoding='ascii')

    glottocodes = Glottocodes(str(json))
    gc = glottocodes.new('a', dry_run=True)
    assert gc.startswith('aaaa')
    assert gc not in glottocodes
    gc = glottocodes.new('a')
    assert gc in glottocodes
    # make sure it's also written to file:
    assert gc in Glottocodes(str(json))
    assert len(list(Glottocodes(str(json)))) == 1


def test_es():
    assert EndangermentStatus.get('nearly extinct') == EndangermentStatus.critical


def test_EndangermentStatus():
    c = EndangermentStatus.critical
    assert EndangermentStatus.get(c) == c

    with pytest.raises(ValueError):
        EndangermentStatus.get(123)


@pytest.mark.parametrize('input_, valid', [
    ('abcd1234', True),
    ('a12d3456', True),
    ('abcd123', False),
    ('12d3456', False),
    ('aNOCODE', False),
    ('NOCODE_abd', False),
    ('nocode', False),
])
def test_pattern(input_, valid, _match=Glottocode.pattern.match):
    assert (_match(input_) is not None) == valid


def test_Country():
    assert Country.from_text('Germany').id == 'DE'
    assert Country.from_name('abcdefg') is None
    assert Country.from_id('abcdefg') is None


def test_Glottocode_validation():
    with pytest.raises(ValueError):
        Glottocode('a2')


def test_Glottocode_ordering():
    assert sorted([Glottocode('abcd1235'), Glottocode('abcd1234')])[0] == Glottocode('abcd1234')
    assert Glottocode('zzzz9999') > Glottocode('abcd1234')
    assert Glottocode('abcd1234') <= Glottocode('abcd1234')


def test_Reference():
    ref = Reference('bib:key', '12-34', 'German')
    assert '{0}'.format(ref) == '**bib:key**:12-34<trigger "German">'
    Reference.from_list(['{0}'.format(ref)])

    with pytest.raises(ValueError):
        Reference.from_list(['abc'])


def test_ClassificationComment(mocker):
    cc = ClassificationComment(family='**bib:key**')
    log = mocker.Mock()
    cc.check(mocker.Mock(), [], log)
    assert log.error.called
    log = mocker.Mock()
    cc.check(mocker.Mock(), ['bib:key'], log)
    assert not log.error.called


def test_EthnologueComment(mocker):
    with pytest.raises(ValueError):
        EthnologueComment('abc', 't')

    with pytest.raises(ValueError):
        EthnologueComment('abc', 'missing', 'E15')

    with pytest.raises(ValueError):
        EthnologueComment('abc', 'missing', 'E16')

    with pytest.raises(ValueError):
        EthnologueComment('abc', 'missing', 'E16', '\u00e4\u00f6\u00fc'.encode('utf-8'))

    log = mocker.Mock()
    ec = EthnologueComment('abc', 'missing', 'E16', 'abc')
    ec.check(mocker.Mock(), [], log)
    assert not log.error.called

    log = mocker.Mock()
    ec = EthnologueComment('abc', 'missing', 'E16', '**bib:key**')
    ec.check(mocker.Mock(), [], log)
    assert log.error.called


def test_Level(api):
    assert Level.dialect > Level.language
    assert Level.language == api.languoid('abcd1235').level
    with pytest.raises(ValueError):
        Level.get('abcde')


def test_Languoid_sorting(api):
    assert api.languoid('abcd1235') < api.languoid('abcd1236')
    assert api.languoid('abcd1236') >= api.languoid('abcd1235')


def test_factory(tmpdir, api_copy):
    f = Languoid.from_dir(api_copy.tree / 'abcd1234')
    assert f.category == 'Family'
    l = Languoid.from_dir(api_copy.tree / f.id / 'abcd1235')
    assert l.name == 'language'
    assert 'abcd1235' in repr(l)
    assert 'language' in '%s' % l
    assert l.level == Level.language
    assert l.latitude == pytest.approx(0.5)
    assert l.longitude == pytest.approx(0.5)
    l.latitude, l.longitude = 1.0, 1.0
    assert l.latitude == pytest.approx(1.0)
    assert l.longitude == pytest.approx(1.0)
    assert l.iso_code == 'abc'
    l.iso_code = 'cde'
    assert l.iso == 'cde'
    assert l.hid == 'abc'
    l.hid = 'abo'
    assert l.hid == 'abo'
    assert l.id == 'abcd1235'

    assert len(l.macroareas) == 2
    l.macroareas = [Macroarea.africa]
    assert l.macroareas == [Macroarea.africa]

    l.countries = api_copy.countries[:2]
    assert len(l.countries) == 2

    assert l.parent == f
    assert f.children[0] == l
    assert l.children[0].family == f
    l.write_info(str(tmpdir))
    assert (tmpdir / 'abcd1235').exists()
    assert isinstance(api_copy.languoid('abcd1235').iso_retirement.asdict(), dict)
    assert l.classification_comment is None
    l.endangerment = 'nearly extinct'
    assert l.endangerment == EndangermentStatus.critical
    assert l.names == {}
    l.cfg['altnames'] = {'glottolog': 'xyz'}
    assert 'glottolog' in l.names
    assert l.identifier == {}
    l.cfg['identifier'] = {'multitree': 'xyz'}
    assert 'multitree' in l.identifier


def test_isolate(api):
    l = Languoid.from_dir(api.tree / 'isol1234')
    assert l.isolate
    assert l.parent is None
    assert l.family is None


def test_attrs(api):
    l = Languoid.from_name_id_level(
        api.tree, 'name', 'abcd1235', Level.language, hid='NOCODE')
    l.name = 'other'
    assert l.name == 'other'
    with pytest.raises(AttributeError):
        l.glottocode = 'x'
    with pytest.raises(AttributeError):
        l.id = 'x'
    assert l.id == l.glottocode
    assert l.hid == 'NOCODE'
