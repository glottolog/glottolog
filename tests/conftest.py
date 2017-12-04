from __future__ import unicode_literals

import pytest

from clldutils import path

DATA = path.Path(__file__).parent / 'data'


@pytest.fixture  # FIXME: session scope w/ tmpdir_factory.getbasetemp()?
def api(tmpdir):
    from pyglottolog import Glottolog

    repos = tmpdir / 'repos'
    path.copytree(str(DATA), str(repos))
    return Glottolog(str(repos))
