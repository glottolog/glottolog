from __future__ import unicode_literals

import pytest

from clldutils import path

import pyglottolog

TESTS_DIR = path.Path(__file__).parent


@pytest.fixture(scope='session')
def repos_path():
    return TESTS_DIR / 'repos'


@pytest.fixture(scope='session')
def references_path(repos_path):
    return repos_path / 'references'


@pytest.fixture(scope='session')
def bibfiles(references_path):
    return pyglottolog.references.BibFiles.from_path(str(references_path))


@pytest.fixture
def bibfiles_copy(tmpdir, references_path):
    references_copy = tmpdir / 'references'
    path.copytree(str(references_path), str(references_copy))
    return pyglottolog.references.BibFiles.from_path(str(references_copy))


@pytest.fixture(scope='session')
def hhtypes(references_path):
    return pyglottolog.references.HHTypes(str(references_path / 'hhtype.ini'))


@pytest.fixture(scope='session')
def api(repos_path):
    """Glottolog instance from shared directory for read-only tests."""
    return pyglottolog.Glottolog(str(repos_path))


@pytest.fixture
def api_copy(tmpdir, repos_path):
    """Glottolog instance from isolated directory copy."""
    repos_copy = str(tmpdir / 'repos')
    path.copytree(str(repos_path), repos_copy)
    return pyglottolog.Glottolog(repos_copy)
