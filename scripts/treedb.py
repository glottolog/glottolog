# treedb.py - load languoids/tree/**/md.ini into sqlite3

from __future__ import unicode_literals

import re
import time
import itertools
import datetime

import sqlalchemy as sa
import sqlalchemy.orm

import treedb_backend as _backend
from treedb_backend import iteritems

REBUILD = False

MACROAREA = {
    'North America', 'South America',
    'Eurasia',
    'Africa',
    'Australia', 'Papunesia',
}

TRIGGER_FIELD = {'lgcode', 'inlg'}

IDENTIFIER_SITE = {
    'multitree', 'endangeredlanguages',
    'wals', 'languagelandscape',
}

ENDANGERMENT_STATUS = (
    'not endangered',
    'threatened', 'shifting',
    'moribund', 'nearly extinct',
    'extinct',
)

ENDANGERMENT_SOURCE = {'E20', 'ElCat', 'UNESCO', 'Glottolog'}


def iterlanguoids(root=_backend.ROOT):
    def getlines(cfg, section, option):
        if not cfg.has_option(section, option):
            return []
        return cfg.get(section, option).strip().splitlines()

    def getdatetime(cfg, section, option, format_='%Y-%m-%dT%H:%M:%S'):
        return datetime.datetime.strptime(cfg.get(section, option), format_)

    def splitcountry(name, _match=re.compile(r'(.+) \(([^)]+)\)$').match):
        return _match(name).groups()

    def splitsource(s, pattern=re.compile(
        "\*\*(?P<bibfile>[a-z0-9\-_]+):(?P<bibkey>[a-zA-Z.?\-;*'/()\[\]!_:0-9\u2014]+?)\*\*"
        "(:(?P<pages>[0-9\-f]+))?"
        '(<trigger "(?P<trigger>[^\"]+)">)?')):
        return pattern.match(s).groupdict()

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
            'macroareas': getlines(cfg, 'core', 'macroareas'),
            'countries': [splitcountry(c) for c in getlines(cfg, 'core', 'countries')],
        }
        if cfg.has_section('sources'):
            item['sources'] = {provider: list(map(splitsource, getlines(cfg, 'sources', provider)))
                               for provider in cfg.options('sources')}
        if cfg.has_section('altnames'):
            item['altnames'] = {provider: getlines(cfg, 'altnames', provider)
                                for provider in cfg.options('altnames')}
        if cfg.has_section('triggers'):
            item['triggers'] = {field: getlines(cfg, 'triggers', field)
                                for field in cfg.options('triggers')}
        if cfg.has_section('identifier'):
            # FIXME: semicolon-separated (wals)?
            item['identifier'] = dict(cfg.items('identifier'))
        if cfg.has_section('endangerment'):
            item['endangerment'] = {
                'status': cfg.get('endangerment', 'status'),
                'source': cfg.get('endangerment', 'source'),
                'date': getdatetime(cfg, 'endangerment', 'date'),
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


languoid_macroarea = sa.Table('languoid_macroarea', _backend.Model.metadata,
    sa.Column('languoid_id', sa.ForeignKey('languoid.id'), primary_key=True),
    sa.Column('macroarea', sa.Enum(*sorted(MACROAREA)), primary_key=True))


class Country(_backend.Model):

    __tablename__ = 'country'

    id = sa.Column(sa.String(2), primary_key=True)
    name = sa.Column(sa.Text, unique=True)


languoid_country = sa.Table('languoid_country', _backend.Model.metadata,
    sa.Column('languoid_id', sa.ForeignKey('languoid.id'), primary_key=True),
    sa.Column('country_id', sa.ForeignKey('country.id'), primary_key=True))


class Source(_backend.Model):

    __tablename__ = 'source'

    languoid_id = sa.Column(sa.ForeignKey('languoid.id'), primary_key=True)
    bibfile = sa.Column(sa.Text, primary_key=True)
    bibkey = sa.Column(sa.Text, primary_key=True)
    # FIXME: clean up duplicates (ord: primary key-> unique(languoid_id, ord))
    ord = sa.Column(sa.Integer, primary_key=True)
    pages = sa.Column(sa.Text)
    trigger = sa.Column(sa.Text)


class Altname(_backend.Model):

    __tablename__ = 'altname'

    languoid_id = sa.Column(sa.ForeignKey('languoid.id'), primary_key=True)
    provider = sa.Column(sa.Text, primary_key=True)
    ord = sa.Column(sa.Integer, primary_key=True)
    name = sa.Column(sa.Text, nullable=False)


languoid_trigger = sa.Table('languoid_trigger', _backend.Model.metadata,
    sa.Column('languoid_id', sa.ForeignKey('languoid.id'), primary_key=True),
    sa.Column('field', sa.Enum(*sorted(TRIGGER_FIELD)), primary_key=True),
    sa.Column('ord', sa.Integer, primary_key=True),
    sa.Column('trigger', sa.Text, nullable=False))


languoid_identifier = sa.Table('languoid_identifier', _backend.Model.metadata,
    sa.Column('languoid_id', sa.ForeignKey('languoid.id'), primary_key=True),
    sa.Column('site', sa.Enum(*sorted(IDENTIFIER_SITE)), primary_key=True),
    sa.Column('identifier', sa.Text, nullable=False))


class Endangerment(_backend.Model):

    __tablename__ = 'endangerment'

    languoid_id = sa.Column(sa.ForeignKey('languoid.id'), primary_key=True)
    status = sa.Column(sa.Enum(*ENDANGERMENT_STATUS), nullable=False)
    source = sa.Column(sa.Enum(*sorted(ENDANGERMENT_SOURCE)), nullable=False)
    date = sa.Column(sa.DateTime, nullable=False)
    comment = sa.Column(sa.Text, nullable=False)


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
    insert_lang = sa.insert(Languoid, bind=conn).execute

    insert_ma = languoid_macroarea.insert(bind=conn).execute

    has_country = sa.select([sa.exists()
        .where(Country.id == sa.bindparam('id'))], bind=conn).scalar
    insert_country = sa.insert(Country, bind=conn).execute
    lang_country = languoid_country.insert(bind=conn).execute

    insert_source = sa.insert(Source, bind=conn).execute
    insert_altname = sa.insert(Altname, bind=conn).execute
    insert_trigger = languoid_trigger.insert(bind=conn).execute
    insert_ident = languoid_identifier.insert(bind=conn).execute
    insert_enda = sa.insert(Endangerment, bind=conn).execute

    insert_ord = itertools.count()

    for l in iterlanguoids():
        lid = l['id']

        macroareas = l.pop('macroareas')
        countries = l.pop('countries')

        sources = l.pop('sources', None)
        altnames = l.pop('altnames', None)
        triggers = l.pop('triggers', None)
        identifier = l.pop('identifier', None)
        endangerment = l.pop('endangerment', None)

        insert_lang(l)
        for ma in macroareas:
            insert_ma(languoid_id=lid, macroarea=ma)
        for name, cc in countries:
            if not has_country(id=cc):
                insert_country(id=cc, name=name)
            lang_country(languoid_id=lid, country_id=cc)
        if sources is not None:
            for provider, data in iteritems(sources):
                for s in data:
                    insert_source(languoid_id=lid, provider=provider, ord=next(insert_ord), **s)
        if altnames is not None:
            for provider, names in iteritems(altnames):
                for i, n in enumerate(names, 1):
                    insert_altname(languoid_id=lid, provider=provider, ord=i, name=n)
        if triggers is not None:
            for field, triggers in iteritems(triggers):
                for i, t in enumerate(triggers, 1):
                    insert_trigger(languoid_id=lid, field=field, ord=i, trigger=t)
        if identifier is not None:
            for site, i in iteritems(identifier):
                insert_ident(languoid_id=lid, site=site, identifier=i)
        if endangerment is not None:
            insert_enda(languoid_id=lid, **endangerment)


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
        [sa.select([sa.func.group_concat(languoid_macroarea.c.macroarea, ', ')])
            .where(languoid_macroarea.c.languoid_id == Languoid.id)
            .order_by(languoid_macroarea)
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


other = sa.orm.aliased(Source)
query = sa.select([
    Source.bibfile, Source.bibkey,
    sa.func.group_concat(Source.pages).label('pages'),
    sa.func.group_concat(Source.trigger).label('trigger'),
    sa.func.group_concat(Source.languoid_id).label('languoid_id'),
    ], bind=_backend.engine)\
    .where(sa.exists()
        .where(other.languoid_id == Source.languoid_id)
        .where(other.bibfile == Source.bibfile)
        .where(other.bibkey == Source.bibkey)
        .where(other.ord != Source.ord))\
    .group_by(Source.bibfile, Source.bibkey)\
    .order_by(Source.bibfile, Source.bibkey)
_backend.print_rows(query, '{bibfile:8} {bibkey:24} {pages!s:8} {trigger!s:12} {languoid_id}')
