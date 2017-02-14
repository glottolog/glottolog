# coding: utf8
from __future__ import unicode_literals
import os
import re
from collections import defaultdict, OrderedDict

from six import text_type
from clldutils.misc import slug, UnicodeMixin
from clldutils import jsonlib
from clldutils.path import Path
from clldutils.inifile import INI
import attr
import pycountry

from pyglottolog.util import languoids_path, IdNameDescription

INFO_FILENAME = 'md.ini'
TREE = languoids_path('tree')

"""
Ok so 800 hh-comments (phew) are in.

    There's the comment field which is freetext with markdown (emph, |-| tables and http:// urls). It may have cr:s that fuck up reading the .ini structure -- I am unsure about all that but at least I see no signs of parsing errors when readin the ini:s via pyglottolog.api

    There's the comment_type field which is either
    -"spurious" meaning the comment is to explain why the languoid in question is spurious and in which Ethnologue (as below) that is/was
    -"missing" meaning the comment is to explain why the languoid in question is missing (as a language entry) and in which Ethnologue (as below) that is/was

    There's the "ethnologue_versions" field which says which Ethnologue version(s) from E16-E19 the comment pertains to, joined by /:s. E.g. E16/E17. In the case of comment_type=spurious, E16/E17 in the version field means that the code was spurious in E16/E17 but no longer spurious in E18/E19. In the case of comment_type=missing, E16/E17 would mean that the code was missing from E16/E17, but present in E18/E19. If the comment concerns a language where versions would be the empty string, instead the string ISO 639-3 appears.

    There's the isohid field which says which iso/hid the comment concerns.
"""



@attr.s
class LevelItem(IdNameDescription):
    pass


class Level(object):
    """
    Glottolog distinguishes three levels of languoids:
    - family: any sub-grouping of languoids above the language level
    - language: defined as per\
    http://glottolog.org/glottolog/glottologinformation#inclusionexclusionoflanguages
    - dialect: any variety which is not a language

    The Glottolog classification imposes the following rules on the nesting of languoids:
    1. Dialects must not be top-level nodes of the classification.
    2. Dialects must not have a family as parent.
    3. Languages must either be isolates (i.e. top-level nodes) or have a family as
       parent.
    4. The levels of the languoids in a tree branch must be monotonically descending.
    """
    family = LevelItem(1, 'family', 'sub-grouping of languoids above the language level')
    language = LevelItem(2, 'language', 'defined by mutual non-intellegibility')
    dialect = LevelItem(3, 'dialect', 'any variety which is not a language')

    @classmethod
    def get(cls, item):
        if isinstance(item, LevelItem):
            return item
        for li in cls():
            if li.id == item or li.name == item:
                return li
        raise ValueError(item)

    def __iter__(self):
        return iter([self.family, self.language, self.dialect])


@attr.s
class Country(UnicodeMixin):
    """
    Glottolog languoids can be related to the countries they are spoken in. These
    countries are identified by ISO 3166 Alpha-2 codes.

    .. see also:: https://en.wikipedia.org/wiki/ISO_3166-1
    """
    id = attr.ib()
    name = attr.ib()

    def __unicode__(self):
        return '{0.name} ({0.id})'.format(self)

    @classmethod
    def from_name(cls, name):
        try:
            res = pycountry.countries.get(name=name)
            return cls(id=res.alpha_2, name=res.name)
        except KeyError:
            pass

    @classmethod
    def from_id(cls, id_):
        try:
            res = pycountry.countries.get(alpha_2=id_)
            return cls(id=res.alpha_2, name=res.name)
        except KeyError:
            pass

    @classmethod
    def from_text(cls, text):
        match = re.search('\(?(?P<code>[A-Z]{2})\)?', text)
        if match:
            return cls.from_id(match.group('code'))
        return cls.from_name(text)


@attr.s
class Macroarea(IdNameDescription):
    """
    Glottolog languoids can be related to a macroarea.
    """
    @classmethod
    def from_name(cls, name):
        for ma in MACROAREAS:
            if ma.name == name:
                return ma


MACROAREAS = [
    Macroarea(*args) for args in [
        ('northamerica',
         'North America',
         'North and Middle America up to Panama. Includes Greenland.'),
        ('southamerica',
         'South America',
         'Everything South of Darién'),
        ('africa',
         'Africa',
         'The continent'),
        ('australia',
         'Australia',
         'The continent'),
        ('eurasia',
         'Eurasia',
         'The Eurasian landmass North of Sinai. Includes Japan and islands to the North'
         'of it. Does not include Insular South East Asia.'),
        ('pacific',
         'Papunesia',
         'All islands between Sumatra and the Americas, excluding islands off Australia'
         'and excluding Japan and islands to the North of it.'),
    ]]


old_ref_pattern = re.compile('[^\[]+\[(?P<pages>[^\]]*)\]\s*\([0-9]+\s+(?P<key>[^\)]+)\)')
new_ref_pattern = re.compile('(\*\*)?(?P<key>hh:[a-zA-Z\-_0-9:]+)(\*\*(:(?P<pages>[0-9\-]+))?)?')


@attr.s
class ClassificationComment(object):
    sub = attr.ib(default=None)
    subrefs = attr.ib(default=attr.Factory(list))
    family = attr.ib(default=None)
    familyrefs = attr.ib(default=attr.Factory(list))

    def check(self, lang, keys):
        def from_match(m):
            assert m
            r = '**{0}**'.format(m.group('key'))
            if m.group('pages'):
                r += ':{0}'.format(m.group('pages'))
            return r

        refs = []
        for ref in self.subrefs:
            match = new_ref_pattern.match(ref)
            assert match
            if match.group('key') not in keys:
                print(lang, ref)
            continue
            #parts = ref.split()
            #if len(parts) > 1:
            #    match = old_ref_pattern.match(ref)
            #    if match:
            #        refs.append(from_match(match))
            #    else:
            #        for part in parts:
            #            refs.append(from_match(new_ref_pattern.match(part)))
            #else:
            #    refs.append(from_match(new_ref_pattern.match(ref)))
        #if refs:
        #    lang.cfg.set('classification', 'subrefs', refs)
        #    return True
        return False


@attr.s
class ISORetirement(object):
    code = attr.ib()
    comment = attr.ib()
    name = attr.ib()
    effective = attr.ib()
    reason = attr.ib(default=None)
    remedy = attr.ib(default=None)
    change_request = attr.ib(default=None)

    def asdict(self):
        return attr.asdict(self)


@attr.s
class StatusItem(IdNameDescription):
    pass


class EndangermentStatus(object):
    """
    http://www.unesco.org/new/en/culture/themes/endangered-languages/atlas-of-languages-in-danger/
    """
    safe = StatusItem(
        1,
        'safe',
        'language is spoken by all generations; '
        'intergenerational transmission is uninterrupted.')
    vulnerable = StatusItem(
        2,
        'vulnerable',
        'most children speak the language, but it may be restricted to certain domains'
        '(e.g., home).')
    definite = StatusItem(
        3,
        'definitely endangered',
        'children no longer learn the language as mother tongue in the home.')
    severe = StatusItem(
        4,
        'severely endangered',
        'language is spoken by grandparents and older generations; while the parent '
        'generation may understand it, they do not speak it to children or among '
        'themselves')
    critical = StatusItem(
        5,
        'critically endangered',
        'the youngest speakers are grandparents and older, and they speak the language '
        'partially and infrequently')
    extinct = StatusItem(
        6,
        'extinct',
        'there are no speakers left since the 1950s')

    @classmethod
    def from_name(cls, value):
        value = value if isinstance(value, int) else value.lower().split()[0]
        for status in cls():
            if status.id == value or status.name.startswith(value):
                return status

    def __iter__(self):
        return iter([
            self.safe,
            self.vulnerable,
            self.definite,
            self.severe,
            self.critical,
            self.extinct])


class Glottocodes(object):
    """
    Registry keeping track of glottocodes that have been dealt out.
    """
    def __init__(self, fname):
        self._fname = fname
        self._store = jsonlib.load(self._fname)

    def __contains__(self, item):
        alpha, num = Glottocode(item).split()
        return alpha in self._store and num <= self._store[alpha]

    def new(self, name, dry_run=False):
        alpha = slug(text_type(name))[:4]
        assert alpha
        while len(alpha) < 4:
            alpha += alpha[-1]
        num = self._store.get(alpha, 1233) + 1
        if not dry_run:
            self._store[alpha] = num
            # Store the updated dictionary of glottocodes back.
            ordered = OrderedDict()
            for k in sorted(self._store.keys()):
                ordered[k] = self._store[k]
            jsonlib.dump(ordered, self._fname, indent=4)
        return Glottocode('%s%s' % (alpha, num))


class Glottocode(text_type):
    regex = '[a-z0-9]{4}[0-9]{4}'
    pattern = re.compile(regex + '$')

    def __new__(cls, content):
        if not cls.pattern.match(content):
            raise ValueError(content)
        return text_type.__new__(cls, content)

    def split(self):
        return self[:4], int(self[4:])


class Languoid(UnicodeMixin):
    """
    Info on languoids is encoded in the ini files and in the directory hierarchy.
    This class provides access to all of it.
    """
    section_core = 'core'

    def __init__(self, cfg, lineage=None, id_=None, directory=None):
        """

        :param cfg:
        :param lineage: list of ancestors, given as (id, name) pairs.
        """
        assert id_ or directory
        if id_ is None:
            id_ = Glottocode(directory.name)
        lineage = lineage or []
        assert all([
            Glottocode.pattern.match(id)
            and Level.get(level) for name, id, level in lineage])
        self.lineage = [(name, id, Level.get(level)) for name, id, level in lineage]
        self.cfg = cfg
        self.dir = directory or TREE.joinpath(*[id for name, id, _ in self.lineage])
        self._id = id_

    @classmethod
    def from_dir(cls, directory, nodes=None, **kw):
        if nodes is None:
            nodes = {}
        cfg = INI.from_file(directory.joinpath(INFO_FILENAME), interpolation=None)

        lineage = []
        for parent in directory.parents:
            id_ = parent.name
            assert id_ != directory.name
            if not Glottocode.pattern.match(id_):
                # we ignore leading non-languoid-dir path components.
                break

            if id_ not in nodes:
                l = Languoid.from_dir(parent, nodes=nodes)
                nodes[id_] = (l.name, l.id, l.level)
            lineage.append(nodes[id_])

        res = cls(cfg, list(reversed(lineage)), directory=directory)
        nodes[res.id] = (res.name, res.id, res.level)
        return res

    @classmethod
    def from_name_id_level(cls, name, id, level, **kw):
        cfg = INI(interpolation=None)
        cfg.read_dict(dict(core=dict(name=name)))
        res = cls(cfg, kw.pop('lineage', []), id_=Glottocode(id))
        res.level = Level.get(level)
        for k, v in kw.items():
            setattr(res, k, v)
        return res

    def __eq__(self, other):
        return self.id == other.id

    def __repr__(self):
        return '<%s %s>' % (self.level.name.capitalize(), self.id)

    def __unicode__(self):
        return '%s [%s]' % (self.name, self.id)

    def _set(self, key, value):
        if value is None and key in self.cfg[self.section_core]:
            del self.cfg[self.section_core][key]
        else:
            self.cfg.set(self.section_core, key, value)

    def _get(self, key, type_=None):
        res = self.cfg.get(self.section_core, key, fallback=None)
        if type_ and res:
            return type_(res)
        return res

    def write_info(self, outdir=None):
        outdir = outdir or self.id
        if not isinstance(outdir, Path):
            outdir = Path(outdir)
        if outdir.name != self.id:
            outdir = outdir.joinpath(self.id)
        if not outdir.exists():
            outdir.mkdir()
        fname = outdir.joinpath(INFO_FILENAME)
        self.cfg.write(fname)
        if os.linesep == '\n':
            with fname.open(encoding='utf8') as fp:
                text = fp.read()
            with fname.open('w', encoding='utf8') as fp:
                fp.write(text.replace('\n', '\r\n'))
        return fname

    # -------------------------------------------------------------------------
    # Accessing info of a languoid
    # -------------------------------------------------------------------------
    @property
    def glottocode(self):
        return self._id

    @property
    def id(self):
        return self._id

    @property
    def category(self):
        fid = self.lineage[0][1] if self.lineage else None
        category_map = defaultdict(
            lambda: 'Spoken L1 Language',
            **{
                'book1242': 'Bookkeeping',
                'unat1236': 'Unattested',
                'uncl1493': 'Unclassifiable',
                'sign1238': 'Sign Language',
                'arti1236': 'Artificial Language',
                'spee1234': 'Speech Register',
                'pidg1258': 'Pidgin',
                'mixe1287': 'Mixed Language',
            })
        if self.level == Level.language:
            return category_map[fid]
        cat = self.level.name.capitalize()
        if self.level == Level.family:
            if self.id.startswith('unun9') or \
                    self.id in category_map or fid in category_map:
                cat = 'Pseudo ' + cat
        return cat

    @property
    def isolate(self):
        return self.level == Level.language and not self.lineage

    def children_from_nodemap(self, nodes):
        # A faster alternative to `children` when the relevant languoids have already been
        # read from disc.
        return [nodes[d.name] for d in self.dir.iterdir() if d.is_dir()]

    @property
    def children(self):
        return [Languoid.from_dir(d) for d in self.dir.iterdir() if d.is_dir()]

    def ancestors_from_nodemap(self, nodes):
        # A faster alternative to `ancestors` when the relevant languoids have already
        # been read from disc.
        return [nodes[l[1]] for l in self.lineage]

    @property
    def ancestors(self):
        res = []
        for parent in self.dir.parents:
            id_ = parent.name
            if Glottocode.pattern.match(id_):
                res.append(Languoid.from_dir(parent))
            else:
                # we ignore leading non-languoid-dir path components.
                break
        return list(reversed(res))

    @property
    def parent(self):
        ancestors = self.ancestors
        return ancestors[-1] if ancestors else None

    @property
    def family(self):
        ancestors = self.ancestors
        return ancestors[0] if ancestors else None

    @property
    def names(self):
        if 'altnames' in self.cfg:
            return {k: self.cfg.getlist('altnames', k) for k in self.cfg['altnames']}
        return {}

    @property
    def identifier(self):
        if 'identifier' in self.cfg:
            return self.cfg['identifier']
        return {}

    @property
    def endangerment(self):
        if 'status' in self.cfg[self.section_core]:
            res = self.cfg.get(self.section_core, 'status')
            if res:
                return EndangermentStatus.from_name(res)

    @endangerment.setter
    def endangerment(self, value):
        self._set('status', EndangermentStatus.from_name(value).name)

    @property
    def classification_comment(self):
        cfg = self.cfg['classification'] if 'classification' in self.cfg else {}
        return ClassificationComment(
            family=cfg.get('family'),
            familyrefs=self.cfg.getlist('classification', 'familyrefs'),
            sub=cfg.get('sub'),
            subrefs=self.cfg.getlist('classification', 'subrefs'))

    @property
    def macroareas(self):
        return [Macroarea.from_name(n)
                for n in self.cfg.getlist(self.section_core, 'macroareas')]

    @macroareas.setter
    def macroareas(self, value):
        assert isinstance(value, (list, tuple)) \
            and all(isinstance(o, Macroarea) for o in value)
        self._set('macroareas', ['{0}'.format(ma) for ma in value])

    @property
    def countries(self):
        return [Country.from_text(n)
                for n in self.cfg.getlist(self.section_core, 'countries')]

    @countries.setter
    def countries(self, value):
        assert isinstance(value, (list, tuple)) \
               and all(isinstance(o, Country) for o in value)
        self._set('countries', ['{0}'.format(c) for c in value])

    @property
    def name(self):
        return self._get('name')

    @name.setter
    def name(self, value):
        self._set('name', value)

    @property
    def latitude(self):
        return self._get('latitude', float)

    @latitude.setter
    def latitude(self, value):
        self._set('latitude', float(value))

    @property
    def longitude(self):
        return self._get('longitude', float)

    @longitude.setter
    def longitude(self, value):
        self._set('longitude', float(value))

    @property
    def hid(self):
        return self._get('hid')

    @hid.setter
    def hid(self, value):
        self._set('hid', value)

    @property
    def level(self):
        return self._get('level', Level.get)

    @level.setter
    def level(self, value):
        self._set('level', Level.get(value).name)

    @property
    def iso(self):
        return self._get('iso639-3')

    @iso.setter
    def iso(self, value):
        self._set('iso639-3', value)

    @property
    def iso_code(self):
        return self._get('iso639-3')

    @iso_code.setter
    def iso_code(self, value):
        self._set('iso639-3', value)

    @property
    def iso_retirement(self):
        if 'iso_retirement' in self.cfg:
            return ISORetirement(**self.cfg['iso_retirement'])

    @property
    def fname(self):
        return self.dir.joinpath(INFO_FILENAME)
