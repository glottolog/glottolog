from __future__ import unicode_literals

import pytest

from pyglottolog.references import Isbns, Isbn


def test_Isbns():
    assert Isbns.from_field('9783866801929, 3866801920') == \
           [Isbn('9783866801929')]

    assert Isbns.from_field('978-3-86680-192-9 3-86680-192-0') == \
           [Isbn('9783866801929')]

    with pytest.raises(ValueError, match=r'pattern'):
        Isbns.from_field('9783866801929 spam, 3866801920')

    with pytest.raises(ValueError, match=r'delimiter'):
        Isbns.from_field('9783866801929: 3866801920')

    assert Isbns.from_field('9780199593569, 9780191739385').to_string() == \
           '9780199593569, 9780191739385'


def test_Isbn():
    with pytest.raises(ValueError, match='length'):
        Isbn('978-3-86680-192-9')

    with pytest.raises(ValueError, match=r'length'):
        Isbn('03-86680-192-0')

    with pytest.raises(ValueError, match=r'0 instead of 9'):
        Isbn('9783866801920')

    with pytest.raises(ValueError, match=r'9 instead of 0'):
        Isbn('3866801929')

    assert Isbn('9783866801929').digits == '9783866801929'
    assert Isbn('3866801920').digits == '9783866801929'

    l, r = twins = Isbn('9783866801929'), Isbn('9783866801929')
    assert l == r and not l != r
    assert len(set(twins)) == 1

    assert repr(Isbn('9783866801929')) in \
           ["Isbn(u'9783866801929')", "Isbn('9783866801929')"]
