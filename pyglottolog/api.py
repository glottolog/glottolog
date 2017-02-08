# coding=utf8
from __future__ import unicode_literals
import re

import attr
from clldutils.path import walk, Path
from clldutils.misc import UnicodeMixin, cached_property
from clldutils.inifile import INI
import pycountry
from termcolor import colored
from newick import Node

from pyglottolog import util
from pyglottolog import languoids
from pyglottolog import references

ISO_CODE_PATTERN = re.compile('[a-z]{3}$')


@attr.s
class Country(object):
    id = attr.ib()
    name = attr.ib()


@attr.s
class Macroarea(object):
    id = attr.ib()
    name = attr.ib()
    description = attr.ib()


class Glottolog(UnicodeMixin):
    countries = [Country(c.alpha_2, c.name) for c in pycountry.countries]
    macroareas = [Macroarea(*args) for args in [
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
         'The Eurasian landmass North of Sinai. Includes Japan and islands to the North of it. Does not include Insular South East Asia.'),
        ('pacific', 
         'Papunesia', 
         'All islands between Sumatra and the Americas, excluding islands off Australia and excluding Japan and islands to the North of it.'),
    ]]

    def __init__(self, repos=None):
        self.repos = Path(repos) if repos else util.DATA_DIR
        self.tree = util.languoids_path('tree', data_dir=self.repos)

    def __unicode__(self):
        return '<Glottolog repos at %s>' % self.repos

    def build_path(self, *comps):
        return util.build_path(*comps, **{'repos': self.repos})

    def references_path(self, *comps):
        return util.references_path(*comps, **{'repos': self.repos})

    def languoids_path(self, *comps):
        return util.languoids_path(*comps, **{'repos': self.repos})

    @property
    def glottocodes(self):
        return languoids.Glottocodes(self.languoids_path('glottocodes.json'))

    @property
    def ftsindex(self):
        return self.build_path('whoosh')

    def languoid(self, id_):
        if isinstance(id_, languoids.Languoid):
            return id_

        if ISO_CODE_PATTERN.match(id_):
            for d in walk(self.tree, mode='dirs'):
                l = languoids.Languoid.from_dir(d)
                if l.iso_code == id_:
                    return l
        else:
            for d in walk(self.tree, mode='dirs'):
                if d.name == id_:
                    return languoids.Languoid.from_dir(d)

    def languoids(self, ids=None):
        nodes = {}
        for d in walk(self.tree, mode='dirs'):
            if ids is None or d.name in ids:
                yield languoids.Languoid.from_dir(d, nodes=nodes)

    def ascii_tree(self, start, maxlevel=None):
        _ascii_node(self.languoid(start), 0, True, maxlevel, '')

    def newick_tree(self, start):
        return _newick_node(self.languoid(start)).newick

    @cached_property()
    def bibfiles(self):
        return references.BibFiles(
            self, INI.from_file(self.references_path('BIBFILES.ini'), interpolation=None))

    @cached_property()
    def hhtypes(self):
        return references.HHTypes(
            INI.from_file(self.references_path('hhtype.ini'), interpolation=None))

    @cached_property()
    def triggers(self):
        res = {'inlg': [], 'lgcode': []}
        for lang in self.languoids():
            for type_ in res:
                if lang.cfg.has_option('triggers', type_):
                    label = '%s [%s]' % (lang.name, lang.hid or lang.id)
                    res[type_].extend([util.Trigger(type_, label, text)
                                       for text in lang.cfg.getlist('triggers', type_)])
        return res

    @cached_property()
    def macroarea_map(self):
        res = {}
        for lang in self.languoids():
            ma = lang.macroareas[0] if lang.macroareas else ''
            res[lang.id] = ma
            if lang.iso:
                res[lang.iso] = ma
            if lang.hid:
                res[lang.hid] = ma
        return res


def _newick_node(l):
    n = Node(name="'{0} [{1}]'".format(l.name, l.id))
    for nn in sorted(l.children, key=lambda nn: nn.name):
        n.add_descendant(_newick_node(nn))
    return n


def _ascii_node(n, level, last, maxlevel, prefix):
    if maxlevel:
        if (isinstance(maxlevel, languoids.Level) and n.level > maxlevel) or \
                (not isinstance(maxlevel, languoids.Level) and level > maxlevel):
            return
    s = '\u2514' if last else '\u251c'
    s += '\u2500 '

    if not level:
        for i, node in enumerate(n.ancestors):
            print('{0}{1}{2} [{3}]'.format(
                prefix, s if i else '', node.name, node.id).encode('utf8'))
            prefix = '   ' + prefix

    nprefix = prefix + ('   ' if last else '\u2502  ')

    color = 'red' if not level else (
        'green' if n.level == languoids.Level.language else (
            'blue' if n.level == languoids.Level.dialect else None))

    print('{0}{1}{2} [{3}]'.format(
        prefix,
        s if level else (s if n.ancestors else ''),
        colored(n.name, color) if color else n.name,
        colored(n.id, color) if color else n.id,
    ).encode('utf8'))
    for i, c in enumerate(sorted(n.children, key=lambda nn: nn.name)):
        _ascii_node(c, level + 1, i == len(n.children) - 1, maxlevel, nprefix)
