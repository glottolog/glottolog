# coding: utf8
from __future__ import unicode_literals

import pytest

from clldutils import jsonlib

from pyglottolog.languoids import (Languoid, EndangermentStatus,
    Glottocodes, Glottocode, Level, Country, Reference, Macroarea,
    ClassificationComment, EthnologueComment)


def test_Glottocodes(tmpdir, api):
    gcjson = str(tmpdir / 'glottocodes.json')
    jsonlib.dump({}, gcjson)

    glottocodes = Glottocodes(gcjson)
    gc = glottocodes.new('a', dry_run=True)
    assert gc.startswith('aaaa')
    assert gc not in glottocodes
    gc = glottocodes.new('a')
    assert gc in glottocodes
    # make sure it's also written to file:
    assert gc in Glottocodes(gcjson)
    assert len(list(Glottocodes(gcjson))) == 1


def test_es():
    assert EndangermentStatus.critical == EndangermentStatus.get('nearly extinct')


def test_EndangermentStatus():
    c = EndangermentStatus.critical
    assert EndangermentStatus.get(c) == c

    with pytest.raises(ValueError):
        EndangermentStatus.get(123)


def test_pattern():
    pattern = Glottocode.pattern
    for valid in [
        'abcd1234',
        'a12d3456',
    ]:
        assert pattern.match(valid) is not None

    for invalid in [
        'abcd123',
        '12d3456',
        'aNOCODE',
        'NOCODE_abd',
        'nocode',
    ]:
        assert pattern.match(invalid) is None


def test_Country():
    assert Country.from_text('Germany').id == 'DE'
    assert Country.from_name('abcdefg') is None
    assert Country.from_id('abcdefg') is None


def test_Glottocode():
    with pytest.raises(ValueError):
        Glottocode('a2')


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
        EthnologueComment('abc', 'missing', 'E16', 'äöü'.encode('utf8'))

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


def test_factory(tmpdir, api):
    f = Languoid.from_dir(api.tree / 'abcd1234')
    assert f.category == 'Family'
    l = Languoid.from_dir(api.tree / f.id / 'abcd1235')
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

    l.countries = api.countries[:2]
    assert len(l.countries) == 2

    assert l.parent == f
    assert f.children[0] == l
    assert l.children[0].family == f
    l.write_info(str(tmpdir))
    assert (tmpdir / 'abcd1235').exists()
    assert isinstance(api.languoid('abcd1235').iso_retirement.asdict(), dict)
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
