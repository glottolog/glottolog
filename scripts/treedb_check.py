# treedb_check.py - check glottolog-specific invariants

from __future__ import unicode_literals

import itertools

import sqlalchemy as sa

import treedb_backend as _backend
from treedb import LEVEL, Languoid

FAMILY, LANGUAGE, DIALECT = LEVEL

BOOKKEEPING = 'Bookkeeping'

SPECIAL_FAMILIES = (
    'Unattested',
    'Unclassifiable',
    'Pidgin',
    'Mixed Language',
    'Artificial Language',
    'Speech Register',
    'Sign Language',
)

CHECKS = []


def main(make_session=_backend.Session):
    for func in CHECKS:
        session = make_session()
        ns = {'invalid_query': staticmethod(func), '__doc__': func.__doc__}
        check_cls = type(str('%sCheck' % func.__name__), (Check,), ns)
        check = check_cls(session)
        try:
            check.validate()
        finally:
            session.close()


def check(func):
    CHECKS.append(func)
    return func


class Check(object):

    detail = True

    def __init__(self, session):
        self.session = session
        self.query = self.invalid_query(session)

    def invalid_query(self, session):
        raise NotImplementedError

    def validate(self):
        self.invalid_count = self.query.count()
        print(self)
        if self.invalid_count:
            if self.detail:
                self.invalid = self.query.all()
                self.show_detail(self.invalid, self.invalid_count)
            return False
        else:
            self.invalid = []
            return True

    def __str__(self):
        if self.invalid_count:
            msg = '%d invalid\n    (violating %s)' % (self.invalid_count, self.__doc__)
        else:
            msg = 'OK'
        return '%s: %s' % (self.__class__.__name__, msg)

    @staticmethod
    def show_detail(invalid, invalid_count, number=25):
        ids = (i.id for i in itertools.islice(invalid, number))
        cont = ', ...' if number < invalid_count else ''
        print('    %s%s' % (', '.join(ids), cont))


@check
def dialect_parent(session):
    """Parent of a dialect is a language or dialect."""
    return session.query(Languoid).filter_by(level=DIALECT).order_by('id')\
        .join(Languoid.parent, aliased=True)\
        .filter(Languoid.level.notin_([LANGUAGE, DIALECT]))


@check
def family_children(session):
    """Family has at least one subfamily or language."""
    return session.query(Languoid).filter_by(level=FAMILY).order_by('id')\
        .filter(~Languoid.children.any(
            Languoid.level.in_([FAMILY, LANGUAGE])))


@check
def family_languages(session):
    """Family has at least two languages."""
    family, child = (sa.orm.aliased(Languoid) for _ in range(2))
    tree = Languoid.tree(include_self=True, with_terminal=True)
    return session.query(Languoid).filter_by(level=FAMILY).order_by('id')\
        .filter(~session.query(family).filter_by(level=FAMILY)
            .filter(family.name.in_(SPECIAL_FAMILIES))
            .join(tree, tree.c.parent_id == family.id)
            .filter_by(terminal=True, child_id=Languoid.id)
            .exists())\
        .filter(session.query(sa.func.count())
            .select_from(child).filter_by(level=LANGUAGE)
            .join(tree, tree.c.child_id == child.id)
            .filter_by(parent_id=Languoid.id).as_scalar() < 2)


@check
def bookkeeping_no_children(session):
    """Bookkeeping languoids lack children."""
    return session.query(Languoid).order_by('id')\
        .filter(Languoid.parent.has(name=BOOKKEEPING))\
        .filter(Languoid.children.any())


if __name__ == '__main__':
    main()
