from __future__ import unicode_literals

import pytest

from clldutils import path

import pyglottolog

REPOS = path.Path(__file__).parent / 'repos'


@pytest.fixture(scope='session')
def repos():
    return REPOS


@pytest.fixture(scope='session')
def sapi(repos):
    """Glottolog instance from shared directory for read-only tests."""
    return pyglottolog.Glottolog(str(repos))


@pytest.fixture
def api(tmpdir, repos):
    """Glottolog instance from isolated directory copy."""
    repos_copy = str(tmpdir / 'repos')
    path.copytree(str(repos), repos_copy)
    return pyglottolog.Glottolog(repos_copy)
