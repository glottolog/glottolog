from __future__ import unicode_literals


def test_unique():
    from pyglottolog.util import unique

    assert list(unique([1, 2, 1, 2, 3])) == [1, 2, 3]


def test_wrap():
    from pyglottolog.util import wrap

    text = """\
This is going to be a long line which must be split.
The next line is going to be interpreted as second paragraph upon first pass.
"""
    wrapped = wrap(text, width=20, line_as_paragraph=True)

    # Now a second pass should be idempotent:
    assert wrapped == wrap(wrapped, width=20)


def test_group_first():
    from pyglottolog.util import group_first

    key, items = next(group_first([(1, 2), (1, 3)]))
    assert key, list(items) == (1, [(1, 2), (1, 3)])


def test_Trigger():
    from pyglottolog.util import Trigger

    t1 = Trigger('hhtype', 'grammar', 'phonologie AND NOT morphologie')
    t2 = Trigger('hhtype', 'phonology', 'phonologie')
    t3 = Trigger('hhtype', 'grammar', 'grammar')

    assert t1 != t3 and t1 == t1
    allkeys = range(5)
    keys_by_word = dict(grammar=[1, 2], phonologie=[2, 3], morphologie=[3, 4])
    assert t1(allkeys, keys_by_word) == {2}
    assert t2(allkeys, keys_by_word) == {2, 3}
    assert t3(allkeys, keys_by_word) == {1, 2}
    assert 'not morphologie and phonologie' in Trigger.format('a', t1)

    for t in sorted([t1, t2, t3]):
        assert t.type in Trigger.format(t.type, t)
