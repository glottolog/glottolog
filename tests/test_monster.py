from __future__ import unicode_literals

from six import PY2

from pyglottolog import monster


def test_main(capsys, api):
    if not PY2:  # pragma: no cover
        return

    monster.compile(api)
    out, _ = capsys.readouterr()
    assert len(out.splitlines()) == 43
    assert '2 splitted' in out
    assert '2 merged' in out
