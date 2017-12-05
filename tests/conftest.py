from __future__ import unicode_literals

import pytest

from clldutils import path

import pyglottolog

REPOS = path.Path(__file__).parent / 'repos'


@pytest.fixture(scope='session')
def sapi():
    """Glottolog instance from shared directory for read-only tests."""
    return pyglottolog.Glottolog(str(REPOS))


@pytest.fixture
def api(tmpdir):
    """Glottolog instance from isolated directory copy."""
    repos = str(tmpdir / 'repos')
    path.copytree(str(REPOS), repos)
    return pyglottolog.Glottolog(repos)
