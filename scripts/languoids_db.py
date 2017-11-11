# languoids_db.py - load languoids/tree/**/md.ini into sqlite3

import io
import re
import time
import pathlib
import datetime
import contextlib
import configparser

try:
    from os import scandir
except ImportError:
    from scandir import scandir

import sqlalchemy as sa
import sqlalchemy.orm
import sqlalchemy.ext.declarative

ROOT = pathlib.Path('../languoids/tree')
DBFILE = pathlib.Path('languoids.sqlite3')


def iterfiles(top=ROOT, verbose=False):
    """Yield DirEntry objects for all files under top."""
    if isinstance(top, pathlib.Path):
        top = str(top)
    stack = [top]
    while stack:
        root = stack.pop()
        if verbose:
            print(root)
        direntries = scandir(root)
        dirs = []
        for d in direntries:
            if d.is_dir():
                dirs.append(d.path)
            else:
                yield d
        stack.extend(dirs[::-1])


class ConfigParser(configparser.ConfigParser):

    @classmethod
    def from_file(cls, filename, encoding='utf-8', **kwargs):
        inst = cls(**kwargs)
        with io.open(filename, encoding=encoding) as f:
            inst.read_file(f)
        return inst

    def __init__(self, defaults=None, **kwargs):
        super(ConfigParser, self).__init__(defaults=defaults, interpolation=None, **kwargs)

    def getlist(self, section, option):
        if not self.has_option(section, option):
            return []
        return self.get(section, option).strip().splitlines()

    def getdatetime(self, section, option, format_='%Y-%m-%dT%H:%M:%S'):
        return datetime.datetime.strptime(self.get(section, option), format_)


def iterconfig(root=ROOT, assert_name='md.ini', load=ConfigParser.from_file):
    if not isinstance(root, pathlib.Path):
        root = pathlib.Path(root)
    root_len = len(root.parts)
    for d in iterfiles(root):
        assert d.name == assert_name
        path_tuple = pathlib.Path(d.path).parts[root_len:-1]
        yield path_tuple, load(d.path)


def iterlanguoids(root=ROOT):
    def splitcountry(name, _match=re.compile(r'(.+) \(([^)]+)\)$').match):
        return _match(name).groups()

    for path, cfg in iterconfig(root):
        item = {
            'id': path[-1],
            'parent_id': path[-2] if len(path) > 1 else None,
            'level': cfg.get('core', 'level'),
            'name': cfg.get('core', 'name'),
            'hid': cfg.get('core', 'hid', fallback=None),
            'iso639_3': cfg.get('core', 'iso639-3', fallback=None),
            'latitude': cfg.getfloat('core', 'latitude', fallback=None),
            'longitude': cfg.getfloat('core', 'longitude', fallback=None),
            'macroareas': cfg.getlist('core', 'macroareas'),
            'countries': [splitcountry(c) for c in cfg.getlist('core', 'countries')],
        }
        if cfg.has_section('endangerment'):
            item['endangerment'] = {
                'status': cfg.get('endangerment', 'status'),
                'source': cfg.get('endangerment', 'source'),
                'date': cfg.getdatetime('endangerment', 'date'),
                'comment': cfg.get('endangerment', 'comment'),
            }
        yield item


engine = sa.create_engine('sqlite:///%s' % DBFILE)


@sa.event.listens_for(sa.engine.Engine, 'connect')
def set_sqlite_pragma(dbapi_connection, connection_record):
    with contextlib.closing(dbapi_connection.cursor()) as cursor:
        cursor.execute('PRAGMA foreign_keys = ON')


Model = sa.ext.declarative.declarative_base()


class Languoid(Model):

    __tablename__ = 'languoid'

    id = sa.Column(sa.String(8), primary_key=True)
    level = sa.Column(sa.Enum('family', 'language', 'dialect'), nullable=False)
    name = sa.Column(sa.String, nullable=False, unique=True)
    parent_id = sa.Column(sa.ForeignKey('languoid.id'), index=True)
    hid = sa.Column(sa.Text, unique=True)
    iso639_3 = sa.Column(sa.String(3), unique=True)
    latitude = sa.Column(sa.Float, sa.CheckConstraint('latitude BETWEEN -90 AND 90'))
    longitude = sa.Column(sa.Float, sa.CheckConstraint('longitude BETWEEN -180 AND 180'))


class Endangerment(Model):

    __tablename__ = 'endangerment'

    languoid_id = sa.Column(sa.ForeignKey('languoid.id'), primary_key=True)
    status = sa.Column(sa.Enum('not endangered', 'threatened', 'shifting',
                               'moribund', 'nearly extinct', 'extinct'), nullable=False)
    source = sa.Column(sa.Enum('E20', 'ElCat', 'UNESCO', 'Glottolog'), nullable=False)
    date = sa.Column(sa.DateTime, nullable=False)
    comment = sa.Column(sa.Text, nullable=False)


class Macroarea(Model):

    __tablename__ = 'macroarea'

    name = sa.Column(sa.Text, primary_key=True)

    _names = (
        'North America', 'South America',
        'Eurasia',
        'Africa',
        'Australia', 'Papunesia',
    )


languoid_macroarea = sa.Table('languoid_macroarea', Model.metadata,
    sa.Column('languoid_id', sa.ForeignKey('languoid.id'), primary_key=True),
    sa.Column('macroarea_name', sa.ForeignKey('macroarea.name'), primary_key=True))


class Country(Model):

    __tablename__ = 'country'

    id = sa.Column(sa.String(2), primary_key=True)
    name = sa.Column(sa.Text, unique=True)


languoid_country = sa.Table('languoid_country', Model.metadata,
    sa.Column('languoid_id', sa.ForeignKey('languoid.id'), primary_key=True),
    sa.Column('country_id', sa.ForeignKey('country.id'), primary_key=True))


if DBFILE.exists():
    DBFILE.unlink()

Model.metadata.create_all(engine)

start = time.time()

with engine.begin() as conn:
    conn.execute('PRAGMA synchronous = OFF')
    conn.execute('PRAGMA journal_mode = MEMORY')
    conn = conn.execution_options(compiled_cache={})

    insert_lang = sa.insert(Languoid, bind=conn).execute
    insert_enda = sa.insert(Endangerment, bind=conn).execute

    lang_ma = languoid_macroarea.insert(bind=conn)\
        .values(languoid_id=sa.bindparam('lid'), macroarea_name=sa.bindparam('ma')).execute

    has_co = sa.select([sa.exists()
        .where(Country.id == sa.bindparam('cc'))], bind=conn).scalar
    insert_co = sa.insert(Country, bind=conn).execute
    lang_co = languoid_country.insert(bind=conn)\
        .values(languoid_id=sa.bindparam('lang'), country_id=sa.bindparam('cc')).execute

    sa.insert(Macroarea, bind=conn).execute([{'name': n} for n in Macroarea._names])
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
        
print(time.time() - start)

print(sa.select([Languoid], bind=engine).limit(5).execute().fetchall())


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
query = sa.select([tree], bind=engine).where(tree.c.child_id == 'ostr1239')

print(query.execute().fetchall())

tree = get_tree()  # FIXME: order_by
query = sa.select([
        Languoid.id,
        Languoid.parent_id,
        sa.select([sa.func.group_concat(tree.c.parent_id, '/')])
            .where(tree.c.child_id == Languoid.id).label('path'),
    ], bind=engine)

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

df = pd.read_sql_query(query, engine, index_col='id')
df.info()
