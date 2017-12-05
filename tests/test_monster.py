from __future__ import unicode_literals

import six

import pytest

from pyglottolog import monster


@pytest.mark.skipif(six.PY3, reason='PY2 only')
def test_main(capsys, api):
    monster.compile(api)
    out, _ = capsys.readouterr()
    assert len(out.splitlines()) == 43
    assert '2 splitted' in out
    assert '2 merged' in out
