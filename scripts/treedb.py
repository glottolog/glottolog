# treedb.py - load languoids/tree/**/md.ini into sqlite3

from __future__ import unicode_literals

import re
import time

import sqlalchemy as sa
import sqlalchemy.orm

import treedb_backend as _backend

REBUILD = False


def iterlanguoids(root=_backend.ROOT):
    def splitcountry(name, _match=re.compile(r'(.+) \(([^)]+)\)$').match):
        return _match(name).groups()

    for path_tuple, cfg in _backend.iterconfig(root):
        item = {
            'id': path_tuple[-1],
            'parent_id': path_tuple[-2] if len(path_tuple) > 1 else None,
            'level': cfg.get('core', 'level'),
            'name': cfg.get('core', 'name'),
            'hid': cfg.get('core', 'hid', fallback=None),
            'iso639_3': cfg.get('core', 'iso639-3', fallback=None),
            'latitude': cfg.getfloat('core', 'latitude', fallback=None),
            'longitude': cfg.getfloat('core', 'longitude', fallback=None),
            'macroareas': cfg.getlines('core', 'macroareas'),
            'countries': [splitcountry(c) for c in cfg.getlines('core', 'countries')],
        }
        if cfg.has_section('endangerment'):
            item['endangerment'] = {
                'status': cfg.get('endangerment', 'status'),
                'source': cfg.get('endangerment', 'source'),
                'date': cfg.getdatetime('endangerment', 'date'),
                'comment': cfg.get('endangerment', 'comment'),
            }
        yield item


class Languoid(_backend.Model):

    __tablename__ = 'languoid'

    id = sa.Column(sa.String(8), primary_key=True)
    level = sa.Column(sa.Enum('family', 'language', 'dialect'), nullable=False)
    name = sa.Column(sa.String, nullable=False, unique=True)
    parent_id = sa.Column(sa.ForeignKey('languoid.id'), index=True)
    hid = sa.Column(sa.Text, unique=True)
    iso639_3 = sa.Column(sa.String(3), unique=True)
    latitude = sa.Column(sa.Float, sa.CheckConstraint('latitude BETWEEN -90 AND 90'))
    longitude = sa.Column(sa.Float, sa.CheckConstraint('longitude BETWEEN -180 AND 180'))


class Endangerment(_backend.Model):

    __tablename__ = 'endangerment'

    languoid_id = sa.Column(sa.ForeignKey('languoid.id'), primary_key=True)
    status = sa.Column(sa.Enum('not endangered', 'threatened', 'shifting',
                               'moribund', 'nearly extinct', 'extinct'), nullable=False)
    source = sa.Column(sa.Enum('E20', 'ElCat', 'UNESCO', 'Glottolog'), nullable=False)
    date = sa.Column(sa.DateTime, nullable=False)
    comment = sa.Column(sa.Text, nullable=False)


class Macroarea(_backend.Model):

    __tablename__ = 'macroarea'

    name = sa.Column(sa.Text, primary_key=True)

    _names = (
        'North America', 'South America',
        'Eurasia',
        'Africa',
        'Australia', 'Papunesia',
    )


languoid_macroarea = sa.Table('languoid_macroarea', _backend.Model.metadata,
    sa.Column('languoid_id', sa.ForeignKey('languoid.id'), primary_key=True),
    sa.Column('macroarea_name', sa.ForeignKey('macroarea.name'), primary_key=True))


class Country(_backend.Model):

    __tablename__ = 'country'

    id = sa.Column(sa.String(2), primary_key=True)
    name = sa.Column(sa.Text, unique=True)


languoid_country = sa.Table('languoid_country', _backend.Model.metadata,
    sa.Column('languoid_id', sa.ForeignKey('languoid.id'), primary_key=True),
    sa.Column('country_id', sa.ForeignKey('country.id'), primary_key=True))


def load(root=_backend.ROOT, rebuild=False):
    if not _backend.DBFILE.exists():
        _backend.create_tables(_backend.engine)
    elif rebuild:
        _backend.DBFILE.unlink()
        _backend.create_tables(_backend.engine)
    else:
        return

    start = time.time()
    with _backend.engine.begin() as conn:
        conn.execute('PRAGMA synchronous = OFF')
        conn.execute('PRAGMA journal_mode = MEMORY')
        conn = conn.execution_options(compiled_cache={})
        _backend._load(conn, root)
        _load(conn, root)
    print(time.time() - start)


def _load(conn, root):
    sa.insert(Macroarea, bind=conn).execute([{'name': n} for n in Macroarea._names])

    insert_lang = sa.insert(Languoid, bind=conn).execute
    insert_enda = sa.insert(Endangerment, bind=conn).execute

    lang_ma = languoid_macroarea.insert(bind=conn)\
        .values(languoid_id=sa.bindparam('lid'), macroarea_name=sa.bindparam('ma')).execute

    has_co = sa.select([sa.exists()
        .where(Country.id == sa.bindparam('cc'))], bind=conn).scalar
    insert_co = sa.insert(Country, bind=conn).execute
    lang_co = languoid_country.insert(bind=conn)\
        .values(languoid_id=sa.bindparam('lang'), country_id=sa.bindparam('cc')).execute

    for l in iterlanguoids():
        lid = l['id']
        macroareas = l.pop('macroareas')
        countries = l.pop('countries')
        endangerment = l.pop('endangerment', None)
        insert_lang(l)
        if endangerment is not None:
            insert_enda(languoid_id=lid, **endangerment)
        for ma in macroareas:
            lang_ma(lid=lid, ma=ma)
        for name, cc in countries:
            if not has_co(cc=cc):
                insert_co(id=cc, name=name)
            lang_co(lang=lid, cc=cc)


load(rebuild=REBUILD)


print(sa.select([Languoid], bind=_backend.engine).limit(5).execute().fetchall())


def get_tree(with_terminal=False):
    child = sa.orm.aliased(Languoid, name='child')
    cols = [child.id.label('child_id'),
            sa.literal(1).label('steps'),
            child.parent_id.label('parent_id')]

    if with_terminal:
        cols.append(sa.literal(False).label('terminal'))

    tree_1 = sa.select(cols)\
        .where(child.parent_id != None)\
        .cte(recursive=True).alias('tree')

    parent = sa.orm.aliased(Languoid, name='parent')
    fromclause = tree_1.join(parent, parent.id == tree_1.c.parent_id)
    cols = [tree_1.c.child_id, tree_1.c.steps + 1, parent.parent_id]

    if with_terminal:
        gparent = sa.orm.aliased(Languoid, name='grandparent')
        fromclause = fromclause.outerjoin(gparent, gparent.id == parent.parent_id)
        cols.append(gparent.parent_id == None)

    tree_2 = sa.select(cols).select_from(fromclause)\
        .where(parent.parent_id != None)

    return tree_1.union_all(tree_2)


tree = get_tree(with_terminal=True)
query = sa.select([tree], bind=_backend.engine).where(tree.c.child_id == 'ostr1239')
print(query.execute().fetchall())

tree = get_tree()  # FIXME: order_by
query = sa.select([
        Languoid.id,
        Languoid.parent_id,
        sa.select([sa.func.group_concat(tree.c.parent_id, '/')])
            .where(tree.c.child_id == Languoid.id).label('path'),
    ], bind=_backend.engine)
print(query)
print(query.limit(10).execute().fetchall())


import pandas as pd

query = sa.select(
        [c for c in Languoid.__table__.columns] +
        [c.label('endangerment_%s' % c.name) for c in Endangerment.__table__.columns if c.name != 'languoid_id'] +
        [sa.select([sa.func.group_concat(Macroarea.name, ', ')])
            .select_from(languoid_macroarea.join(Macroarea))
            .where(languoid_macroarea.c.languoid_id == Languoid.id)
            .order_by(Macroarea.name)
            .label('macroareas'),
        sa.select([sa.func.group_concat(Country.id, ' ')])
            .select_from(languoid_country.join(Country))
            .where(languoid_country.c.languoid_id == Languoid.id)
            .order_by(Country.id)
            .label('countries')]
    ).select_from(sa.outerjoin(Languoid, Endangerment))\
    .order_by(Languoid.id)

df = pd.read_sql_query(query, _backend.engine, index_col='id')
df.info()
