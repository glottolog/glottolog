from __future__ import unicode_literals

from six.moves import zip

import itertools


def pairwise(iterable):
    a, b = itertools.tee(iterable)
    next(b, None)
    return zip(a, b)


def test_HHTypes(hhtypes):
    assert hhtypes['grammar'].rank == 17
    assert 'grammar' in hhtypes

    for pref, t in pairwise(hhtypes):
        assert pref > t

    assert len(hhtypes) == 2
    assert 'rank' in repr(hhtypes[0])
    assert hhtypes.parse('grammar') == ['grammar']
