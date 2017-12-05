from __future__ import unicode_literals

import six

import pytest
import mock

from clldutils.path import copytree

from pyglottolog import commands


def _args(api, *args):
    return mock.Mock(repos=api, args=list(args), log=mock.Mock())


def test_show(capsys, sapi):
    commands.show(_args(sapi, '**a:key**'))
    assert (b'@misc' if six.PY2 else '@misc') in capsys.readouterr()[0]

    commands.show(_args(sapi, 'a:key'))
    assert (b'@misc' if six.PY2 else '@misc') in capsys.readouterr()[0]

    commands.show(_args(sapi, 'abcd1236'))
    assert (b'Classification' if six.PY2 else 'Classificat') in capsys.readouterr()[0]


def test_edit(mocker, sapi):
    mocker.patch('pyglottolog.commands.subprocess')
    commands.edit(_args(sapi, 'abcd1236'))


def test_create(capsys, api):
    commands.create(_args(api, 'abcd1234', 'new name', 'language'))
    assert 'Info written' in capsys.readouterr()[0]
    assert 'new name' in [c.name for c in api.languoid('abcd1234').children]


def test_fts(capsys, api):
    from pyglottolog.commands import refindex, refsearch, langindex, langsearch

    with pytest.raises(ValueError):
        commands.refsearch(_args(api, 'Harzani year:1334'))

    commands.refindex(_args(api))
    commands.refsearch(_args(api, 'Harzani year:1334'))
    assert "'Abd-al-'Ali Karang" in capsys.readouterr()[0]

    commands.langindex(_args(api))
    commands.langsearch(_args(api, 'id:abcd*'))
    assert "abcd1234" in capsys.readouterr()[0]

    commands.langsearch(_args(api, 'classification'))
    assert "abcd1234" in capsys.readouterr()[0]


def test_metadata(capsys, api):
    commands.metadata(_args(api))
    assert "longitude" in capsys.readouterr()[0]


def test_lff(capsys, api):
    commands.tree2lff(_args(api))
    with api.build_path('dff.txt').open(encoding='utf8') as fp:
        dfftxt = fp.read().replace('dialect', 'Dialect Name')
    with api.build_path('dff.txt').open('w', encoding='utf8') as fp:
        fp.write(dfftxt)
    commands.lff2tree(_args(api))
    assert 'git status' in capsys.readouterr()[0]
    assert api.languoid('abcd1236').name == 'Dialect Name'
    commands.tree2lff(_args(api))
    with api.build_path('dff.txt').open(encoding='utf8') as fp:
        assert dfftxt == fp.read()


def test_index(api):
    commands.index(_args(api))
    assert len(list(api.repos.joinpath('languoids').glob('*.md'))) == 7


def test_tree(capsys, api):
    with pytest.raises(commands.ParserError):
        commands.tree(_args(api))

    with pytest.raises(commands.ParserError):
        commands.tree(_args(api, 'xyz'))

    commands.tree(_args(api, 'abc', 'language'))
    out, _ = capsys.readouterr()
    if not isinstance(out, six.text_type):
        out = out.decode('utf-8')
    assert 'language' in out
    assert 'dialect' not in out


def test_newick(capsys, api):
    commands.newick(_args(api, 'abcd1235'))
    assert 'language' in capsys.readouterr()[0]


def test_check(capsys, api):
    commands.check(_args(api, 'refs'))

    args = _args(api)
    commands.check(args)
    assert 'family' in capsys.readouterr()[0]
    for call in args.log.error.call_args_list:
        assert 'unregistered glottocode' in call[0][0]
    assert args.log.error.call_count == 4

    copytree(
        api.tree.joinpath('abcd1234', 'abcd1235'),
        api.tree.joinpath('abcd1235'))

    args = _args(api)
    commands.check(args)
    assert 'duplicate glottocode' in \
            ''.join(c[0][0] for c in args.log.error.call_args_list)
    assert args.log.error.call_count == 6


@pytest.mark.skipif(six.PY3, reason='PY2 only')
def test_monster(capsys, api):
    commands.bib(_args(api))
    assert capsys.readouterr()[0]
