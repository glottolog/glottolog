from __future__ import unicode_literals

from six import PY2

from clldutils.testing import capture


def test_main(api):
    from pyglottolog.monster import compile

    if not PY2:  # pragma: no cover
        return

    with capture(compile, api) as out:
        assert len(out.splitlines()) == 43
        assert '2 splitted' in out
        assert '2 merged' in out
