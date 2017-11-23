# treedb_check.py - check glottolog-specific invariants

from __future__ import unicode_literals

import itertools

import sqlalchemy as sa

import treedb_backend as _backend
from treedb import Languoid

FAMILY, LANGUAGE, DIALECT = 'family', 'language', 'dialect'

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

DUMMY_SESSION = sa.orm.scoped_session(sa.orm.sessionmaker(bind=None))


def main(make_session=_backend.Session):
    for subcls in itersubclasses(Check):
        if 'invalid_query' in subcls.__dict__:
            session = make_session()
            check = subcls(session)
            try:
                check.validate()
            finally:
                session.close()


def itersubclasses(cls):
    """Recursively yield proper subclasses in depth-first order."""
    stack = cls.__subclasses__()[::-1]
    seen = set()
    while stack:
        cls = stack.pop()
        if cls not in seen:
            seen.add(cls)
            yield cls
            stack.extend(cls.__subclasses__()[::-1])


class Check(object):

    detail = True

    def __init__(self, session=DUMMY_SESSION):
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


class DialectParent(Check):
    """Parent of a dialect is a language or dialect."""

    def invalid_query(self, session):
        return session.query(Languoid).filter_by(level=DIALECT).order_by('id')\
            .join(Languoid.parent, aliased=True)\
            .filter(Languoid.level.notin_([LANGUAGE, DIALECT]))


class FamilyChildren(Check):
    """Family has at least one subfamily or language."""

    def invalid_query(self, session):
        return session.query(Languoid).filter_by(level=FAMILY).order_by('id')\
            .filter(~Languoid.children.any(
                Languoid.level.in_([FAMILY, LANGUAGE])))


class FamilyLanguages(Check):
    """Family has at least two languages."""

    def todo_invalid_query(self, session, exclude=SPECIAL_FAMILIES):
        child = sa.orm.aliased(Languoid)
        #return session.query(Languoid).filter_by(level='FAMILY').order_by('id')\
        #    .filter(Languoid.family.has(Languoid.name.notin_(exclude)))\
        #    .join(TreeClosureTable, TreeClosureTable.parent_pk == Languoid.pk)\
        #    .outerjoin(child, and_(
        #        TreeClosureTable.child_pk == child.pk,
        #        TreeClosureTable.depth > 0,
        #        child.level == LanguoidLevel.language))\
        #    .group_by(Language.pk, Languoid.pk)\
        #    .having(func.count(child.pk) < 2)\


class BookkeepingNoChildren(Check):
    """Bookkeeping languoids lack children."""

    def invalid_query(self, session, **kw):
        return session.query(Languoid).order_by('id')\
            .filter(Languoid.parent.has(name='Bookkeeping'))\
            .filter(Languoid.children.any())


if __name__ == '__main__':
    main()
