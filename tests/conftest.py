from __future__ import unicode_literals

import pytest

from clldutils import path

import pyglottolog

REPOS = path.Path(__file__).parent / 'repos'


@pytest.fixture(scope='session')
def api_ro():
    return pyglottolog.Glottolog(str(REPOS))


@pytest.fixture
def api(tmpdir):
    repos = str(tmpdir / 'repos')
    path.copytree(str(REPOS), repos)
    return pyglottolog.Glottolog(repos)
