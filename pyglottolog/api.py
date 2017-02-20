# coding=utf8
from __future__ import unicode_literals
import re
import os

from clldutils.path import Path, as_posix, walk
from clldutils.misc import UnicodeMixin, cached_property
from clldutils.inifile import INI
from clldutils.declenum import EnumSymbol
import pycountry
from termcolor import colored
from newick import Node

from pyglottolog import util
from pyglottolog import languoids
from pyglottolog import references
from pyglottolog import objects

ISO_CODE_PATTERN = re.compile('[a-z]{3}$')


class Glottolog(UnicodeMixin):
    countries = [objects.Country(c.alpha_2, c.name) for c in pycountry.countries]

    def __init__(self, repos=None):
        self.repos = Path(repos) if repos else util.DATA_DIR
        self.tree = self.repos.joinpath('languoids', 'tree')

    def __unicode__(self):
        return '<Glottolog repos at %s>' % self.repos

    def build_path(self, *comps):
        build_dir = self.repos.joinpath('build')
        if not build_dir.exists():
            build_dir.mkdir()
        return build_dir.joinpath(*comps)

    def references_path(self, *comps):
        return self.repos.joinpath('references', *comps)

    def languoids_path(self, *comps):
        return self.repos.joinpath('languoids', *comps)

    @cached_property()
    def iso(self):
        return util.get_iso(self.build_path())

    @property
    def glottocodes(self):
        return objects.Glottocodes(self.languoids_path('glottocodes.json'))

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

    def languoids(self, ids=None, maxlevel=objects.Level.dialect):
        nodes = {}

        for dirpath, dirnames, filenames in os.walk(as_posix(self.tree)):
            dp = Path(dirpath)
            if dp.name in nodes and nodes[dp.name][2] > maxlevel:
                del dirnames[:]

            for dirname in dirnames:
                if ids is None or dirname in ids:
                    lang = languoids.Languoid.from_dir(dp.joinpath(dirname), nodes=nodes)
                    if lang.level <= maxlevel:
                        yield lang

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
            ma = lang.macroareas[0].value if lang.macroareas else ''
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
        if (isinstance(maxlevel, EnumSymbol) and n.level > maxlevel) or \
                (not isinstance(maxlevel, EnumSymbol) and level > maxlevel):
            return
    s = '\u2514' if last else '\u251c'
    s += '\u2500 '

    if not level:
        for i, node in enumerate(n.ancestors):
            util.sprint('{0}{1}{2} [{3}]', prefix, s if i else '', node.name, node.id)
            prefix = '   ' + prefix

    nprefix = prefix + ('   ' if last else '\u2502  ')

    color = 'red' if not level else (
        'green' if n.level == objects.Level.language else (
            'blue' if n.level == objects.Level.dialect else None))

    util.sprint(
        '{0}{1}{2} [{3}]',
        prefix,
        s if level else (s if n.ancestors else ''),
        colored(n.name, color) if color else n.name,
        colored(n.id, color) if color else n.id)
    for i, c in enumerate(sorted(n.children, key=lambda nn: nn.name)):
        _ascii_node(c, level + 1, i == len(n.children) - 1, maxlevel, nprefix)
