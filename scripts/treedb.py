# treedb.py - load languoids/tree/**/md.ini into sqlite3

from __future__ import unicode_literals

import re
import datetime
import warnings

from treedb_backend import iteritems

import sqlalchemy as sa
import sqlalchemy.orm
import sqlalchemy.ext.associationproxy  # TODO: consider orderinglist

import treedb_files as _files
import treedb_backend as _backend
import treedb_values as _values

LEVEL = ('family', 'language', 'dialect')

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
                'code': cfg.get('iso_retirement', 'code'),
                'name': cfg.get('iso_retirement', 'name'),
                'change_request': cfg.get('iso_retirement', 'change_request', fallback=None),
                'effective': getdate(cfg, 'iso_retirement', 'effective'),
                'reason': cfg.get('iso_retirement', 'reason'),
                'change_to': getlines(cfg, 'iso_retirement', 'change_to'),
                'remedy': cfg.get('iso_retirement', 'remedy', fallback=None),
                'comment': cfg.get('iso_retirement', 'comment', fallback=None),
            }
        yield item


class Languoid(_backend.Model):

    __tablename__ = 'languoid'

    id = sa.Column(sa.String(8), sa.CheckConstraint('length(id) = 8'), primary_key=True)
    level = sa.Column(sa.Enum(*LEVEL), nullable=False)
    name = sa.Column(sa.String, sa.CheckConstraint("name != ''"), nullable=False, unique=True)
    parent_id = sa.Column(sa.ForeignKey('languoid.id'), index=True)
    hid = sa.Column(sa.Text, sa.CheckConstraint('length(hid) >= 3'), unique=True)
    iso639_3 = sa.Column(sa.String(3), sa.CheckConstraint('length(iso639_3) = 3'), unique=True)
    latitude = sa.Column(sa.Float, sa.CheckConstraint('latitude BETWEEN -90 AND 90'))
    longitude = sa.Column(sa.Float, sa.CheckConstraint('longitude BETWEEN -180 AND 180'))

    __table_args__ = (
        sa.CheckConstraint('(latitude IS NULL) = (longitude IS NULL)'),
    )

    def __repr__(self):
        hid_iso = ['%s=%r' % (n, getattr(self, n)) for n in ('hid', 'iso639_3') if getattr(self, n)]
        return '<%s id=%r level=%r name=%r%s>' % (self.__class__.__name__,
            self.id, self.level, self.name, ' ' + ' '.join(hid_iso) if hid_iso else '')

    parent = sa.orm.relationship('Languoid', remote_side=[id])
    children = sa.orm.relationship('Languoid', remote_side=[parent_id], order_by=id)

    macroareas = sa.orm.relationship('Macroarea', secondary='languoid_macroarea', order_by='Macroarea.name',
                                      back_populates='languoids')
    macroarea_names = sa.ext.associationproxy.association_proxy('macroareas', 'name')
    countries = sa.orm.relationship('Country', secondary='languoid_country', order_by='Country.id',
                                    back_populates='languoids')

    sources = sa.orm.relationship('Source', back_populates='languoid', order_by='[Source.provider, Source.ord]')
    altnames = sa.orm.relationship('Altname', back_populates='languoid', order_by='[Altname.provider, Altname.ord]')
    triggers = sa.orm.relationship('Trigger', back_populates='languoid', order_by='[Trigger.field, Trigger.ord]')
    identifiers = sa.orm.relationship('Identifier', back_populates='languoid', order_by='Identifier.site')

    subclassificationcomment = sa.orm.relationship('ClassificationComment', uselist=False,
                                                   primaryjoin="and_(ClassificationComment.languoid_id == Languoid.id, ClassificationComment.kind == 'sub')")
    subclassificationrefs = sa.orm.relationship('ClassificationRef', order_by='ClassificationRef.ord',
                                                   primaryjoin="and_(ClassificationRef.languoid_id == Languoid.id, ClassificationRef.kind == 'sub')")
    familyclassificationcomment = sa.orm.relationship('ClassificationComment', uselist=False,
                                                   primaryjoin="and_(ClassificationComment.languoid_id == Languoid.id, ClassificationComment.kind == 'family')")
    familyclassificationrefs = sa.orm.relationship('ClassificationRef', order_by='ClassificationRef.ord',
                                                   primaryjoin="and_(ClassificationRef.languoid_id == Languoid.id, ClassificationRef.kind == 'family')")

    endangerment = sa.orm.relationship('Endangerment', uselist=False, back_populates='languoid')
    ethnologue_comment = sa.orm.relationship('EthnologueComment', uselist=False, back_populates='languoid')
    iso_retirement = sa.orm.relationship('IsoRetirement', uselist=False, back_populates='languoid')

    @classmethod  # TODO: with_self (reflexive)
    def tree(cls, with_terminal=False):
        child = sa.orm.aliased(cls, name='child')
        cols = [child.id.label('child_id'),
                sa.literal(1).label('steps'),
                child.parent_id.label('parent_id')]

        if with_terminal:
            cols.append(sa.literal(False).label('terminal'))

        tree_1 = sa.select(cols)\
            .where(child.parent_id != None)\
            .cte(recursive=True).alias('tree')

        parent = sa.orm.aliased(cls, name='parent')
        fromclause = tree_1.join(parent, parent.id == tree_1.c.parent_id)
        cols = [tree_1.c.child_id, tree_1.c.steps + 1, parent.parent_id]

        if with_terminal:
            gparent = sa.orm.aliased(Languoid, name='grandparent')
            fromclause = fromclause.outerjoin(gparent, gparent.id == parent.parent_id)
            cols.append(gparent.parent_id == None)

        tree_2 = sa.select(cols).select_from(fromclause)\
            .where(parent.parent_id != None)

        return tree_1.union_all(tree_2)


class Macroarea(_backend.Model):

    __tablename__ = 'macroarea'

    name = sa.Column(sa.Enum(*sorted(MACROAREA)), primary_key=True)

    def __repr__(self):
        return '<%s %r>' % (self.__class__.__name__, self.name)

    languoids = sa.orm.relationship('Languoid', secondary='languoid_macroarea', order_by='Languoid.id',
                                    back_populates='macroareas')


languoid_macroarea = sa.Table('languoid_macroarea', _backend.Model.metadata,
    sa.Column('languoid_id', sa.ForeignKey('languoid.id'), primary_key=True),
    sa.Column('macroarea_name', sa.ForeignKey('macroarea.name'), primary_key=True))


class Country(_backend.Model):

    __tablename__ = 'country'

    id = sa.Column(sa.String(2), sa.CheckConstraint('length(id) = 2'), primary_key=True)
    name = sa.Column(sa.Text, sa.CheckConstraint("name != ''"), nullable=False, unique=True)

    def __repr__(self):
        return '<%s id=%r name=%r>' % (self.__class__.__name__, self.id, self.name)

    languoids = sa.orm.relationship('Languoid', secondary='languoid_country', order_by='Languoid.id',
                                    back_populates='countries')


languoid_country = sa.Table('languoid_country', _backend.Model.metadata,
    sa.Column('languoid_id', sa.ForeignKey('languoid.id'), primary_key=True),
    sa.Column('country_id', sa.ForeignKey('country.id'), primary_key=True))


class Source(_backend.Model):

    __tablename__ = 'source'

    languoid_id = sa.Column(sa.ForeignKey('languoid.id'), primary_key=True)
    provider = sa.Column(sa.Text, sa.CheckConstraint("provider != ''"), primary_key=True)
    bibfile = sa.Column(sa.Text, sa.CheckConstraint("bibfile != ''"), primary_key=True)
    bibkey = sa.Column(sa.Text, sa.CheckConstraint("bibkey != ''"), primary_key=True)
    ord = sa.Column(sa.Integer, sa.CheckConstraint('ord >= 1'), nullable=False)
    pages = sa.Column(sa.Text, sa.CheckConstraint("pages != ''"))
    trigger = sa.Column(sa.Text, sa.CheckConstraint("trigger != ''"))

    __table_args__ = (
        sa.UniqueConstraint(languoid_id, provider, ord),
    )

    def __repr__(self):
        return '<%s languoid_id=%r povider=%r bibfile=%r bibkey=%r>' % (self.__class__.__name__,
            self.languoid_id, self.provider, self.bibfile, self.bibkey)

    languoid = sa.orm.relationship('Languoid', innerjoin=True, back_populates='sources')

    @classmethod
    def printf(cls):
        return sa.case([
            (sa.and_(cls.pages != None, cls.trigger != None),
                 sa.func.printf('**%s:%s**:%s<trigger "%s">', cls.bibfile, cls.bibkey, cls.pages, cls.trigger)),
            (cls.pages != None,
                 sa.func.printf('**s:%s**:%s', cls.bibfile, cls.bibkey, cls.pages)),
            (cls.trigger != None,
                 sa.func.printf('**%s:%s**<trigger "%s">', cls.bibfile, cls.bibkey, cls.trigger)),
            ], else_=sa.func.printf('**%s:%s**', cls.bibfile, cls.bibkey))


class Altname(_backend.Model):

    __tablename__ = 'altname'

    languoid_id = sa.Column(sa.ForeignKey('languoid.id'), primary_key=True)
    provider = sa.Column(sa.Text, sa.CheckConstraint("provider != ''"), primary_key=True)
    name = sa.Column(sa.Text, sa.CheckConstraint("name != ''"), primary_key=True)
    ord = sa.Column(sa.Integer, sa.CheckConstraint('ord >= 1'), nullable=False)

    __table_args__ = (
        sa.UniqueConstraint(languoid_id, provider, ord),
    )

    def __repr__(self):
        return '<%s languoid_id=%r povider=%r name=%r>' % (self.__class__.__name__,
            self.languoid_id, self.provider, self.name)

    languoid = sa.orm.relationship('Languoid', innerjoin=True, back_populates='altnames')


class Trigger(_backend.Model):

    __tablename__ = 'trigger'

    languoid_id = sa.Column(sa.ForeignKey('languoid.id'), primary_key=True)
    field = sa.Column(sa.Enum(*sorted(TRIGGER_FIELD)), primary_key=True)
    trigger = sa.Column(sa.Text, sa.CheckConstraint("trigger != ''"), primary_key=True)
    ord = sa.Column(sa.Integer, sa.CheckConstraint('ord >= 1'), nullable=False)

    __table_args__ = (
        sa.UniqueConstraint(languoid_id, field, ord),
    )

    def __repr__(self):
        return '<%s languoid_id=%r field=%r trigger=%r>' % (self.__class__.__name__,
            self.languoid_id, self.field, self.trigger)

    languoid = sa.orm.relationship('Languoid', innerjoin=True, back_populates='triggers')


class Identifier(_backend.Model):

    __tablename__ = 'identifier'

    languoid_id = sa.Column(sa.ForeignKey('languoid.id'), primary_key=True)
    site= sa.Column(sa.Enum(*sorted(IDENTIFIER_SITE)), primary_key=True)
    identifier = sa.Column(sa.Text, sa.CheckConstraint("identifier != ''"), nullable=False)

    def __repr__(self):
        return '<%s languoid_id=%r site=%r identifier=%r>' % (self.__class__.__name__,
            self.languoid_id, self.site, self.identifier)

    languoid = sa.orm.relationship('Languoid', innerjoin=True, back_populates='identifiers')


class ClassificationComment(_backend.Model):

    __tablename__ = 'classificationcomment'

    languoid_id = sa.Column(sa.ForeignKey('languoid.id'), primary_key=True)
    kind = sa.Column(sa.Enum(*sorted(CLASSIFICATION_KIND)), primary_key=True)
    comment = sa.Column(sa.Text, sa.CheckConstraint("comment != ''"), nullable=False)

    def __repr__(self):
        return '<%s languoid_id=%r kind=%r comment=%r>' % (self.__class__.__name__,
            self.languoid_id, self.kind, self.comment)

    languoid = sa.orm.relationship('Languoid', innerjoin=True)


class ClassificationRef(_backend.Model):

    __tablename__ = 'classificationref'
    languoid_id = sa.Column(sa.ForeignKey('languoid.id'), primary_key=True)
    kind = sa.Column(sa.Enum(*sorted(CLASSIFICATION_KIND)), primary_key=True)
    bibfile = sa.Column(sa.Text, sa.CheckConstraint("bibfile != ''"),primary_key=True)
    bibkey = sa.Column(sa.Text, sa.CheckConstraint("bibkey != ''"), primary_key=True)
    ord = sa.Column(sa.Integer, sa.CheckConstraint('ord >= 1'), nullable=False)
    pages = sa.Column(sa.Text, sa.CheckConstraint("pages != ''"))

    __table_args__ = (
        sa.UniqueConstraint(languoid_id, kind, ord),
    )

    def __repr__(self):
        return '<%s languoid_id=%r kind=%r bibfile=%r bibkey=%r>' % (self.__class__.__name__,
            self.languoid_id, self.kind, self.bibfile, self.bibkey)

    languoid = sa.orm.relationship('Languoid', innerjoin=True)

    @classmethod
    def printf(cls):
        format_ = sa.case([(cls.pages != None, '**s:%s**:%s')], else_='**%s:%s**')
        return sa.func.printf(format_, cls.bibfile, cls.bibkey, cls.pages)


class Endangerment(_backend.Model):

    __tablename__ = 'endangerment'

    languoid_id = sa.Column(sa.ForeignKey('languoid.id'), primary_key=True)
    status = sa.Column(sa.Enum(*ENDANGERMENT_STATUS), nullable=False)
    source = sa.Column(sa.Enum(*sorted(ENDANGERMENT_SOURCE)), nullable=False)
    date = sa.Column(sa.DateTime, nullable=False)
    comment = sa.Column(sa.Text, sa.CheckConstraint("comment != ''"), nullable=False)

    def __repr__(self):
        return '<%s languoid_id=%r status=%r source=%r date=%r>' % (self.__class__.__name__,
            self.languoid_id, self.status, self.source, self.date)

    languoid = sa.orm.relationship('Languoid', innerjoin=True, back_populates='endangerment')


class EthnologueComment(_backend.Model):

    __tablename__ = 'ethnologuecomment'

    languoid_id = sa.Column(sa.ForeignKey('languoid.id'), primary_key=True)
    isohid = sa.Column(sa.Text, sa.CheckConstraint('length(isohid) >= 3'), nullable=False)
    comment_type = sa.Column(sa.Enum(*sorted(EL_COMMENT_TYPE)), nullable=False)
    ethnologue_versions = sa.Column(sa.Text, sa.CheckConstraint('length(ethnologue_versions) >= 3'), nullable=False)
    comment = sa.Column(sa.Text, sa.CheckConstraint("comment != ''"), nullable=False)

    def __repr__(self):
        return '<%s languoid_id=%r isohid=%r comment_type=%r ethnologue_versions=%r>' % (self.__class__.__name__,
            self.languoid_id, self.isohid, self.comment_type, self.ethnologue_versions)

    languoid = sa.orm.relationship('Languoid', innerjoin=True, back_populates='ethnologue_comment')


class IsoRetirement(_backend.Model):

    __tablename__ = 'isoretirement'

    languoid_id = sa.Column(sa.ForeignKey('languoid.id'), primary_key=True)
    code = sa.Column(sa.String(3), sa.CheckConstraint('length(code) = 3'), nullable=False)
    name = sa.Column(sa.Text, sa.CheckConstraint("name != ''"), nullable=False)
    changerequest_id = sa.Column(sa.ForeignKey('changerequest.id'), nullable=False)

    def __repr__(self):
        return '<%s languoid_id=%r code=%r name=%r>' % (self.__class__.__name__,
            self.languoid_id, self.code, self.name)

    languoid = sa.orm.relationship('Languoid', innerjoin=True, back_populates='iso_retirement')
    change_request = sa.orm.relationship('ChangeRequest', innerjoin=True, back_populates='iso_retirements')


class ChangeRequest(_backend.Model):

    __tablename__ = 'changerequest'

    id = sa.Column(sa.Integer, primary_key=True)
    name = sa.Column(sa.String(8), sa.CheckConstraint("name LIKE '____-___' "))
    effective = sa.Column(sa.Date, nullable=False)
    reason = sa.Column(sa.Enum(*sorted(ISORETIREMENT_REASON)), nullable=False)
    remedy = sa.Column(sa.Text, sa.CheckConstraint("remedy != ''"))
    comment = sa.Column(sa.Text, sa.CheckConstraint("comment != ''"))

    __table_args__ = (
        sa.Index('changerequest_key', sa.func.coalesce(name, effective), unique=True),
        sa.CheckConstraint("remedy IS NOT NULL OR reason = 'non-existent'"),
    )

    def __repr__(self):
        return '<%s name=%r effective=%r reason=%r remedy=%r>' % (self.__class__.__name__,
            self.name, self.effective, self.reason, self.remedy)

    iso_retirements = sa.orm.relationship('IsoRetirement', order_by='IsoRetirement.languoid_id',
                                          back_populates='change_request')
    change_to = sa.orm.relationship('ChangeRequestChangeTo', order_by='ChangeRequestChangeTo.ord',
                                    back_populates='change_request')
    change_to_codes = sa.ext.associationproxy.association_proxy('change_to', 'code')


class ChangeRequestChangeTo(_backend.Model):

    __tablename__ = 'changerequest_changeto'

    changerequest_id = sa.Column(sa.ForeignKey('changerequest.id'), primary_key=True)
    code = sa.Column(sa.String(3), sa.CheckConstraint('length(code) = 3'), primary_key=True)
    ord = sa.Column(sa.Integer, sa.CheckConstraint('ord >= 1'), nullable=False)

    __table_args__ = (
        sa.UniqueConstraint('changerequest_id', 'ord'),
    )

    def __repr__(self):
        return '<%s changerequest_id=%r code=%r>' % (self.__class__.__name__,
            self.changerequest_id, self.code)

    change_request = sa.orm.relationship('ChangeRequest', innerjoin=True, back_populates='change_to')


def load(root=_files.ROOT, with_values=True, rebuild=False):
    _backend.load(make_loader(root, with_values), rebuild=rebuild)


def make_loader(root, with_values):

    def load_func(conn):
        if with_values:
            import treedb_values
            treedb_values.make_loader(root=root)(conn)
        _load(conn, root)

    return load_func


def _load(conn, root):
    insert_lang = sa.insert(Languoid, bind=conn).execute

    sa.insert(Macroarea, bind=conn).execute([{'name': n} for n in sorted(MACROAREA)])
    lang_ma = languoid_macroarea.insert(bind=conn).execute

    has_country = sa.select([sa.exists()
        .where(Country.id == sa.bindparam('id'))], bind=conn).scalar
    insert_country = sa.insert(Country, bind=conn).execute
    lang_country = languoid_country.insert(bind=conn).execute

    insert_source = sa.insert(Source, bind=conn).execute
    insert_altname = sa.insert(Altname, bind=conn).execute
    insert_trigger = sa.insert(Trigger, bind=conn).execute
    insert_ident = sa.insert(Identifier, bind=conn).execute
    insert_comment = sa.insert(ClassificationComment, bind=conn).execute
    insert_ref = sa.insert(ClassificationRef, bind=conn).execute
    insert_enda = sa.insert(Endangerment, bind=conn).execute
    insert_el = sa.insert(EthnologueComment, bind=conn).execute

    cr_where = sa.func.coalesce(ChangeRequest.name, ChangeRequest.effective) == \
               sa.func.coalesce(sa.bindparam('name'), sa.bindparam('effective'))
    select_crid = sa.select([ChangeRequest.id], bind=conn).where(cr_where).scalar
    insert_cr = sa.insert(ChangeRequest, bind=conn).execute
    insert_ir = sa.insert(IsoRetirement, bind=conn).execute
    insert_crct = sa.insert(ChangeRequestChangeTo, bind=conn).execute

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
            lang_ma(languoid_id=lid, macroarea_name=ma)
        for name, cc in countries:
            if not has_country(id=cc):
                insert_country(id=cc, name=name)
            lang_country(languoid_id=lid, country_id=cc)
        if sources is not None:
            for provider, data in iteritems(sources):
                for i, s in enumerate(data, 1):
                    insert_source(languoid_id=lid, provider=provider, ord=i, **s)
        if altnames is not None:
            for provider, names in iteritems(altnames):
                for i, n in enumerate(names, 1):
                    insert_altname(languoid_id=lid, provider=provider, ord=i, name=n)
        if triggers is not None:
            for field, triggers in iteritems(triggers):
                for i, t in enumerate(triggers, 1):
                    insert_trigger(languoid_id=lid, field=field, trigger=t, ord=i)
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
            crkey = {c: iso_retirement.pop(i) for c, i in [('name', 'change_request'), ('effective', 'effective')]}
            crparams = {i: iso_retirement.pop(i) for i in ('reason', 'change_to', 'remedy', 'comment')}
            crid = select_crid(**crkey)
            if crid is None:
                crparams.update(crkey)
                change_to = crparams.pop('change_to')
                crid, = insert_cr(**crparams).inserted_primary_key
                for i, c in enumerate(change_to, 1):
                    insert_crct(changerequest_id=crid, code=c, ord=i)
            else:
                # TODO: fix disagreement
                indb = dict(sa.select([ChangeRequest.reason, ChangeRequest.remedy, ChangeRequest.comment], bind=conn)\
                    .where(ChangeRequest.id == crid).execute().first())
                indb['change_to'] = [c for c, in sa.select([ChangeRequestChangeTo.code], bind=conn)\
                    .where(ChangeRequestChangeTo.changerequest_id == crid)\
                    .order_by(ChangeRequestChangeTo.ord).execute()]
                disagreement = [(k, indb[k], crparams[k]) for k in indb if indb[k] != crparams[k]]
                if disagreement:
                    for f, db, ini in disagreement:
                        warnings.warn('%s %s:\n\t%r\n\t%r' % (crid, f, db, ini))
            insert_ir(languoid_id=lid, changerequest_id=crid, **iso_retirement)


def get_query():
    def get_cols(model, label='%s', ignore='id'):
        cols = model.__table__.columns
        if ignore:
            ignore_suffix = '_%s' % ignore
            cols = [c for c in cols if c.name != ignore and not c.name.endswith(ignore_suffix)]
        return [c.label(label % c.name) for c in cols]

    idents = [(s, sa.orm.aliased(Identifier)) for s in sorted(IDENTIFIER_SITE)]
    s, i = idents[0]
    fromclause = sa.outerjoin(Languoid, i, sa.and_(i.languoid_id == Languoid.id, i.site == s))
    for s, i in idents[1:]:
        fromclause = fromclause.outerjoin(i, sa.and_(i.languoid_id == Languoid.id, i.site == s))
    ltrig, itrig = (sa.orm.aliased(Trigger) for _ in range(2))
    subc, famc = (sa.orm.aliased(ClassificationComment) for _ in range(2))
    subr, famr = (sa.orm.aliased(ClassificationRef) for _ in range(2))
    return sa.select([
            Languoid,
            sa.select([sa.func.group_concat(languoid_macroarea.c.macroarea_name, ', ')])
                .where(languoid_macroarea.c.languoid_id == Languoid.id)
                .order_by(languoid_macroarea)
                .label('macroareas'),
            sa.select([sa.func.group_concat(Country.id, ' ')])
                .select_from(languoid_country.join(Country))
                .where(languoid_country.c.languoid_id == Languoid.id)
                .order_by(Country.id)
                .label('countries'),
            sa.select([sa.func.group_concat(Source.printf(), ', ')])
                .where(Source.languoid_id == Languoid.id)
                .where(Source.provider == 'glottolog')
                .order_by(Source.ord)
                .label('sources_glottolog'),
            ] + [i.identifier.label('identifier_%s' % s) for s, i in idents] + [
            sa.select([sa.func.group_concat(ltrig.trigger, ', ')])
                .where(ltrig.languoid_id == Languoid.id)
                .where(ltrig.field == 'lgcode')
                .order_by(ltrig.ord)
                .label('triggers_lgcode'),
            sa.select([sa.func.group_concat(itrig.trigger, ', ')])
                .where(itrig.languoid_id == Languoid.id)
                .where(itrig.field == 'inlg')
                .order_by(itrig.ord)
                .label('trigggers_inlg'),
            subc.comment.label('classification_sub'),
            sa.select([sa.func.group_concat(subr.printf(), ', ')])
                .where(subr.languoid_id == Languoid.id)
                .where(subr.kind == 'sub')
                .order_by(subr.ord)
                .label('classification_subrefs'),
            famc.comment.label('classification_family'),
            sa.select([sa.func.group_concat(famr.printf(), ', ')])
                .where(famr.languoid_id == Languoid.id)
                .where(famr.kind == 'family')
                .order_by(famr.ord)
                .label('classification_familyrefs'),
            ] + get_cols(Endangerment, label='endangerment_%s') +
            get_cols(EthnologueComment, label='elcomment_%s') +
            get_cols(IsoRetirement, label='isoretirement_%s') +
            get_cols(ChangeRequest, label='isoretirement_cr_%s')
        ).select_from(fromclause
            .outerjoin(subc, sa.and_(subc.languoid_id == Languoid.id, subc.kind == 'sub'))
            .outerjoin(famc, sa.and_(famc.languoid_id == Languoid.id, famc.kind == 'family'))
            .outerjoin(Endangerment)
            .outerjoin(EthnologueComment)
            .outerjoin(sa.join(IsoRetirement, ChangeRequest)))\
        .order_by(Languoid.id)


load()

_backend.print_rows(sa.select([Languoid]).order_by(Languoid.id).limit(5))

tree = Languoid.tree(with_terminal=True)
_backend.print_rows(sa.select([tree]).where(tree.c.child_id == 'ramo1244'))

tree = Languoid.tree()
squery = sa.select([
        Languoid.id,
        tree.c.steps,
        tree.c.parent_id.label('path_part'),
    ])\
    .select_from(sa.outerjoin(Languoid, tree, Languoid.id == tree.c.child_id))\
    .order_by(Languoid.id, tree.c.steps.desc())
query = sa.select([
        squery.c.id,
        sa.func.group_concat(squery.c.path_part, '/').label('path'),
    ])\
    .group_by(squery.c.id)
_backend.print_rows(query.limit(5))

pf = _backend.pd_read_sql(query, index_col='id')
print(pf)

query = get_query()
df = _backend.pd_read_sql(query, index_col='id')
df.info()
