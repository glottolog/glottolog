# coding: utf8
from __future__ import unicode_literals, print_function, division
from collections import OrderedDict
import re

from six import text_type
import attr
import markdown
import pycountry
from clldutils.misc import slug, UnicodeMixin
from clldutils.source import Source
from clldutils import jsonlib

from pyglottolog.util import message, IdNameDescription


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


@attr.s
class Reference(UnicodeMixin):
    key = attr.ib()
    pages = attr.ib(default=None)
    pattern = re.compile(
        "\*\*(?P<key>[a-z0-9\-_]+:[a-zA-Z.?\-;*'/()\[\]!_:0-9\u2014]+?)\*\*"
        "(:(?P<pages>[0-9\-f]+))?")
    old_pattern = re.compile('[^\[]+\[(?P<pages>[^\]]*)\]\s*\([0-9]+\s+(?P<key>[^\)]+)\)')

    def __unicode__(self):
        res = '**{0.key}**'.format(self)
        if self.pages:
            res += ':{0.pages}'.format(self)
        return res

    def get_source(self, api):
        return Source.from_bibtex(
            api.bibfiles[self.bibname][self.bibkey], _check_id=False)

    @property
    def provider(self):
        return self.key.split(':')[0]

    @property
    def bibname(self):
        return '{0}.bib'.format(self.provider)

    @property
    def bibkey(self):
        return self.key.split(':', 1)[1]

    @classmethod
    def from_match(cls, match):
        assert match
        return cls(**match.groupdict())

    @classmethod
    def from_string(cls, string, pattern=None):
        return cls.from_match((pattern or cls.pattern).match(string.strip()))

    @classmethod
    def from_list(cls, l, pattern=None):
        res = []
        for s in l:
            if s.strip():
                try:
                    res.append(cls.from_string(s, pattern=pattern))
                except AssertionError:
                    raise ValueError('invalid ref: {0}'.format(s))
        return res


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


@attr.s
class ClassificationComment(object):
    sub = attr.ib(default=None)
    subrefs = attr.ib(default=attr.Factory(list), convert=Reference.from_list)
    family = attr.ib(default=None)
    familyrefs = attr.ib(default=attr.Factory(list), convert=Reference.from_list)

    def check(self, lang, keys, log):
        for attr in ['sub', 'family']:
            comment = getattr(self, attr)
            if comment:
                for m in Reference.pattern.finditer(getattr(self, attr)):
                    if m.group('key') not in keys:
                        log.error(message(
                            lang,
                            'classification {0}: invalid bibkey: {1}'.format(
                                attr, m.group('key'))))
        return False


@attr.s
class ISORetirement(object):
    code = attr.ib()
    comment = attr.ib(convert=lambda s: s.replace('\n.', '\n'))
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


def valid_ethnologue_versions(inst, attr, value):
    if not all(x in ['E16', 'E17', 'E18', 'E19', 'ISO 639-3'] for x in value):
        raise ValueError('invalid ethnologue_versions: {0}'.format('/'.join(value)))


def valid_comment_type(inst, attr, value):
    if value not in ['spurious', 'missing']:
        raise ValueError('invalid comment type: {0}'.format(value))


@attr.s
class EthnologueComment(UnicodeMixin):
    # There's the isohid field which says which iso/hid the comment concerns.
    isohid = attr.ib()

    # There's the comment_type field which is either
    # - "spurious" meaning the comment is to explain why the languoid in question is
    #   spurious and in which Ethnologue (as below) that is/was
    # - "missing" meaning the comment is to explain why the languoid in question is
    #   missing (as a language entry) and in which Ethnologue (as below) that is/was
    comment_type = attr.ib(validator=valid_comment_type, convert=lambda s: s.lower())

    # There's the "ethnologue_versions" field which says which Ethnologue version(s)
    # from E16-E19 the comment pertains to, joined by /:s. E.g. E16/E17. In the case of
    # comment_type=spurious, E16/E17 in the version field means that the code was spurious
    # in E16/E17 but no longer spurious in E18/E19. In the case of comment_type=missing,
    # E16/E17 would mean that the code was missing from E16/E17, but present in E18/E19.
    # If the comment concerns a language where versions would be the empty string,
    # instead the string ISO 639-3 appears.
    ethnologue_versions = attr.ib(
        default=attr.Factory(list),
        validator=valid_ethnologue_versions,
        convert=lambda s: s.replace('693', '639').split('/'))
    comment = attr.ib(default=None)

    def check(self, lang, keys, log):
        try:
            markdown.markdown(self.comment)
        except Exception as e:
            log.error(message(lang, 'ethnologue comment: invalid markup: {0}'.format(e)))
        for m in Reference.pattern.finditer(self.comment):
            if m.group('key') not in keys:
                log.error(message(lang, 'ethnologue comment: invalid bibkey: {0}'.format(
                    m.group('key'))))
        return False
