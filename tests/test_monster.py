from __future__ import unicode_literals

import six

import pytest

from pyglottolog import monster


def test_main(capsys, api_copy):
    monster.compile(api_copy)
    out, _ = capsys.readouterr()
    assert len(out.splitlines()) == 43
    assert '2 splitted' in out
    assert '2 merged' in out
