from __future__ import unicode_literals


def test_HHTypes(sapi):
    hht = sapi.hhtypes
    assert hht['grammar'].rank == 17
    assert 'grammar' in hht

    prev = None
    for t in hht:
        if prev:
            assert prev > t
        prev = t

    assert len(hht) == 2
    assert 'rank' in repr(hht[0])
    assert hht.parse('grammar') == ['grammar']



