# treedb.py - load languoids/tree/**/md.ini into sqlite3

from __future__ import unicode_literals

import re
import time
import datetime
import itertools

from treedb_files import iteritems

import sqlalchemy as sa
import sqlalchemy.orm

import treedb_files as _files
import treedb_backend as _backend

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

CLASSIFICATION = {
    'sub': (False, 'sub'), 'subrefs': (True, 'sub'),
    'family': (False, 'family'), 'familyrefs': (True, 'family')
}

CLASSIFICATION_KIND = {c for _, c in CLASSIFICATION.values()}

EL_COMMENT_TYPE = {'Missing', 'Spurious'}

ENDANGERMENT_SOURCE = {'E20', 'ElCat', 'UNESCO', 'Glottolog'}

ISORETIREMENT_REASON = {'split', 'merge', 'duplicate', 'non-existent', 'change'}


def iterlanguoids(root=_files.ROOT):
    def getlines(cfg, section, option):
        if not cfg.has_option(section, option):
            return []
        return cfg.get(section, option).strip().splitlines()

    def getdate(cfg, section, option, format_='%Y-%m-%d', **kwargs):
        value = cfg.get(section, option, **kwargs)
        if value is None:
            return None
        return datetime.datetime.strptime(value, format_).date()

    def getdatetime(cfg, section, option, format_='%Y-%m-%dT%H:%M:%S'):
        return datetime.datetime.strptime(cfg.get(section, option), format_)

    def splitcountry(name, _match=re.compile(r'(.+) \(([^)]+)\)$').match):
        return _match(name).groups()

    def splitsource(s, pattern=re.compile(
        "\*\*(?P<bibfile>[a-z0-9\-_]+):(?P<bibkey>[a-zA-Z.?\-;*'/()\[\]!_:0-9\u2014]+?)\*\*"
        "(:(?P<pages>[0-9\-f]+))?"
        '(<trigger "(?P<trigger>[^\"]+)">)?')):
        return pattern.match(s).groupdict()

    for path_tuple, cfg in _files.iterconfig(root):
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
            item['sources'] = {provider: [splitsource(p) for p in getlines(cfg, 'sources', provider)]
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
        if cfg.has_section('classification'):
            item['classification'] = {
                c: list(map(splitsource, getlines(cfg, 'classification', c)))
                   if CLASSIFICATION[c][0] else
                   cfg.get('classification', c)
                for c in cfg.options('classification')}
            assert item['classification']
        if cfg.has_section('endangerment'):
            item['endangerment'] = {
                'status': cfg.get('endangerment', 'status'),
                'source': cfg.get('endangerment', 'source'),
                'date': getdatetime(cfg, 'endangerment', 'date'),
                'comment': cfg.get('endangerment', 'comment'),
            }
        if cfg.has_section('hh_ethnologue_comment'):
            item['hh_ethnologue_comment'] = {
                'isohid': cfg.get('hh_ethnologue_comment', 'isohid'),
                'comment_type': cfg.get('hh_ethnologue_comment', 'comment_type'),
                'ethnologue_versions': cfg.get('hh_ethnologue_comment', 'ethnologue_versions'),
                'comment': cfg.get('hh_ethnologue_comment', 'comment'),
            }
        if cfg.has_section('iso_retirement'):
            item['iso_retirement'] = {
                'change_request': cfg.get('iso_retirement', 'change_request', fallback=None),
                'effective': getdate(cfg, 'iso_retirement', 'effective', fallback=None),
                'supersedes': getlines(cfg, 'iso_retirement', 'supersedes'),
                'code': cfg.get('iso_retirement', 'code', fallback=None),
                'name': cfg.get('iso_retirement', 'name', fallback=None),
                'remedy': cfg.get('iso_retirement', 'remedy', fallback=None),
                'comment': cfg.get('iso_retirement', 'comment', fallback=None),
                'reason': cfg.get('iso_retirement', 'reason', fallback=None),
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
    # FIXME: this should be set-like, right?
    sa.Column('ord', sa.Integer, primary_key=True),
    sa.Column('trigger', sa.Text, primary_key=True))


languoid_identifier = sa.Table('languoid_identifier', _backend.Model.metadata,
    sa.Column('languoid_id', sa.ForeignKey('languoid.id'), primary_key=True),
    sa.Column('site', sa.Enum(*sorted(IDENTIFIER_SITE)), primary_key=True),
    sa.Column('identifier', sa.Text, nullable=False))


class ClassificationComment(_backend.Model):

    __tablename__ = 'classificationcomment'

    languoid_id = sa.Column(sa.ForeignKey('languoid.id'), primary_key=True)
    kind = sa.Column(sa.Enum(*sorted(CLASSIFICATION_KIND)), primary_key=True)
    comment = sa.Column(sa.Text, nullable=False)


class ClassificationRef(_backend.Model):

    __tablename__ = 'classificationref'
    languoid_id = sa.Column(sa.ForeignKey('languoid.id'), primary_key=True)
    kind = sa.Column(sa.Enum(*sorted(CLASSIFICATION_KIND)), primary_key=True)
    bibfile = sa.Column(sa.Text, primary_key=True)
    bibkey = sa.Column(sa.Text, primary_key=True)
    # FIXME: check for duplicates
    ord = sa.Column(sa.Integer, primary_key=True)
    pages = sa.Column(sa.Text)


class Endangerment(_backend.Model):

    __tablename__ = 'endangerment'

    languoid_id = sa.Column(sa.ForeignKey('languoid.id'), primary_key=True)
    status = sa.Column(sa.Enum(*ENDANGERMENT_STATUS), nullable=False)
    source = sa.Column(sa.Enum(*sorted(ENDANGERMENT_SOURCE)), nullable=False)
    date = sa.Column(sa.DateTime, nullable=False)
    comment = sa.Column(sa.Text, nullable=False)


class EthnologueComment(_backend.Model):

    __tablename__ = 'ethnologuecomment'

    languoid_id = sa.Column(sa.ForeignKey('languoid.id'), primary_key=True)
    isohid = sa.Column(sa.Text, nullable=False)
    comment_type = sa.Column(sa.Enum(*sorted(EL_COMMENT_TYPE)), nullable=False)
    ethnologue_versions = sa.Column(sa.Text, nullable=False)
    comment = sa.Column(sa.Text, nullable=False)


class IsoRetirement(_backend.Model):

    __tablename__ = 'isoretirement'

    languoid_id = sa.Column(sa.ForeignKey('languoid.id'), primary_key=True)
    # FIXME: all nullable?, m:n?
    change_request = sa.Column(sa.String(8))
    effective = sa.Column(sa.Date)
    code = sa.Column(sa.String(3))
    name = sa.Column(sa.Text)
    reason = sa.Column(sa.Enum(*sorted(ISORETIREMENT_REASON)))
    remedy = sa.Column(sa.Text)
    comment = sa.Column(sa.Text)


isoretirement_supersedes = sa.Table('isoretirement_supersedes', _backend.Model.metadata,
    sa.Column('isoretirement_languoid_id', sa.ForeignKey('isoretirement.languoid_id'), primary_key=True),
    sa.Column('supersedes', sa.String(3), primary_key=True))


def load(rebuild=False, root=_files.ROOT):
    if _backend.DBFILE.exists():
        if rebuild:
            _backend.DBFILE.unlink()
        else:
            return

    _backend.create_tables(_backend.engine)

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
    insert_comment = sa.insert(ClassificationComment, bind=conn).execute
    insert_ref = sa.insert(ClassificationRef, bind=conn).execute
    insert_enda = sa.insert(Endangerment, bind=conn).execute
    insert_el = sa.insert(EthnologueComment, bind=conn).execute
    insert_ir = sa.insert(IsoRetirement, bind=conn).execute
    insert_irsu = isoretirement_supersedes.insert(bind=conn).execute

    insert_ord = itertools.count()

    for l in iterlanguoids(root):
        lid = l['id']

        macroareas = l.pop('macroareas')
        countries = l.pop('countries')

        sources = l.pop('sources', None)
        altnames = l.pop('altnames', None)
        triggers = l.pop('triggers', None)
        identifier = l.pop('identifier', None)
        classification = l.pop('classification', None)
        endangerment = l.pop('endangerment', None)
        hh_ethnologue_comment = l.pop('hh_ethnologue_comment', None)
        iso_retirement = l.pop('iso_retirement', None)

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
        if classification is not None:
            for c, value in iteritems(classification):
                isref, kind = CLASSIFICATION[c]
                if isref:
                    for i, r in enumerate(value, 1):
                        insert_ref(languoid_id=lid, kind=kind, ord=i, **r)
                else:
                    insert_comment(languoid_id=lid, kind=kind, comment=value)
        if endangerment is not None:
            insert_enda(languoid_id=lid, **endangerment)
        if hh_ethnologue_comment is not None:
            insert_el(languoid_id=lid, **hh_ethnologue_comment)
        if iso_retirement is not None:
            supersedes = iso_retirement.pop('supersedes')
            insert_ir(languoid_id=lid, **iso_retirement)
            for s in supersedes:
                insert_irsu(isoretirement_languoid_id=lid, supersedes=s)


load(rebuild=REBUILD)


print(sa.select([Languoid], bind=_backend.engine).limit(5).execute().fetchall())


def tree_cte(with_terminal=False):
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


tree = tree_cte(with_terminal=True)
query = sa.select([tree], bind=_backend.engine).where(tree.c.child_id == 'ostr1239')
print(query.execute().fetchall())

tree = tree_cte()  # FIXME: order_by
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
             .label('countries')
    ]).select_from(sa.outerjoin(Languoid, Endangerment))\
    .order_by(Languoid.id)

df = pd.read_sql_query(query, _backend.engine, index_col='id')
df.info()


self, other = (sa.orm.aliased(Source) for _ in range(2))
query = sa.select([
        self.bibfile, self.bibkey,
        sa.func.group_concat(self.pages).label('pages'),
        sa.func.group_concat(self.trigger).label('trigger'),
        sa.func.group_concat(self.languoid_id).label('languoid_id'),
    ], bind=_backend.engine)\
    .where(sa.exists()
        .where(other.languoid_id == self.languoid_id)
        .where(other.bibfile == self.bibfile)
        .where(other.bibkey == self.bibkey)
        .where(other.ord != self.ord))\
    .group_by(self.bibfile, self.bibkey)\
    .order_by(self.bibfile, self.bibkey)
_backend.print_rows(query, '{bibfile:8} {bibkey:24} {pages!s:8} {trigger!s:12} {languoid_id}')


self, other = (sa.alias(languoid_trigger) for _ in range(2))
query = self.select(bind=_backend.engine)\
    .where(sa.exists()
        .where(other.c.languoid_id == self.c.languoid_id)
        .where(other.c.field == self.c.field)
        .where(other.c.trigger == self.c.trigger)
        .where(other.c.ord != self.c.ord))
_backend.print_rows(query, '{languoid_id} {field} {ord} {trigger}')


query = sa.select([IsoRetirement], bind=_backend.engine)\
    .order_by(IsoRetirement.change_request, IsoRetirement.code == None, IsoRetirement.code, IsoRetirement.name)
_backend.print_rows(query, '{languoid_id} {change_request} {effective} {code:4} {name}')
