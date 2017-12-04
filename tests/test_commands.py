from __future__ import unicode_literals

import pytest
import mock

from six import text_type, PY2

from clldutils.testing import capture  # FIXME
from clldutils.path import copytree


def _args(api, *args):
    return mock.Mock(repos=api, args=list(args), log=mock.Mock())


def test_show(api):
    from pyglottolog.commands import show

    with capture(show, _args(api, '**a:key**')) as out:
        assert (b'@misc' if PY2 else '@misc') in out

    with capture(show, _args(api, 'a:key')) as out:
        assert (b'@misc' if PY2 else '@misc') in out

    with capture(show, _args(api, 'abcd1236')) as out:
        assert (b'Classification' if PY2 else 'Classificat') in out


def test_edit(mocker, api):
    from pyglottolog.commands import edit

    with mocker.patch('pyglottolog.commands.subprocess'):
        edit(_args(api, 'abcd1236'))


def test_create(api):
    from pyglottolog.commands import create

    with capture(create, _args(api, 'abcd1234', 'new name', 'language')) as out:
        assert 'Info written' in out
        assert 'new name' in [c.name for c in api.languoid('abcd1234').children]


def test_fts(api):
    from pyglottolog.commands import refindex, refsearch, langindex, langsearch

    with pytest.raises(ValueError):
        refsearch(_args(api, 'Harzani year:1334'))

    refindex(_args(api))
    with capture(refsearch, _args(api, 'Harzani year:1334')) as out:
        assert "'Abd-al-'Ali Karang" in out

    langindex(_args(api))
    with capture(langsearch, _args(api, 'id:abcd*')) as out:
        assert "abcd1234" in out

    with capture(langsearch, _args(api, 'classification')) as out:
        assert "abcd1234" in out


def test_metadata(api):
    from pyglottolog.commands import metadata

    with capture(metadata, _args(api)) as out:
        assert "longitude" in out


def test_lff(api):
    from pyglottolog.commands import tree2lff, lff2tree

    tree2lff(_args(api))
    with api.build_path('dff.txt').open(encoding='utf8') as fp:
        dfftxt = fp.read().replace('dialect', 'Dialect Name')
    with api.build_path('dff.txt').open('w', encoding='utf8') as fp:
        fp.write(dfftxt)
    with capture(lff2tree, _args(api)) as out:
        assert 'git status' in out
    assert api.languoid('abcd1236').name == 'Dialect Name'
    tree2lff(_args(api))
    with api.build_path('dff.txt').open(encoding='utf8') as fp:
        assert dfftxt == fp.read()


def test_index(api):
    from pyglottolog.commands import index

    index(_args(api))
    assert len(list(api.repos.joinpath('languoids').glob('*.md'))) == 7


def test_tree(api):
    from pyglottolog.commands import tree, ParserError

    with pytest.raises(ParserError):
        tree(_args(api))

    with pytest.raises(ParserError):
        tree(_args(api, 'xyz'))

    with capture(tree, _args(api, 'abc', 'language')) as out:
        if not isinstance(out, text_type):
            out = out.decode('utf8')
        assert 'language' in out
        assert 'dialect' not in out


def test_newick(api):
    from pyglottolog.commands import newick

    with capture(newick, _args(api, 'abcd1235')) as out:
        assert 'language' in out


def test_check(api):
    from pyglottolog.commands import check

    with capture(check, _args(api, 'refs')):
        pass

    args = _args(api)
    with capture(check, args) as out:
        assert 'family' in out
    for call in args.log.error.call_args_list:
        assert 'unregistered glottocode' in call[0][0]
    assert args.log.error.call_count == 4

    copytree(
        api.tree.joinpath('abcd1234', 'abcd1235'),
        api.tree.joinpath('abcd1235'))

    args = _args(api)
    with capture(check, args):
        assert 'duplicate glottocode' in \
            ''.join(c[0][0] for c in args.log.error.call_args_list)
        assert args.log.error.call_count == 6


def test_monster(api):
    from pyglottolog.commands import bib

    if not PY2:  # pragma: no cover
        return

    with capture(bib, _args(api)) as out:
        assert out
