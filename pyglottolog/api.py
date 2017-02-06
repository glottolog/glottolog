# coding=utf8
from __future__ import unicode_literals
import re

import attr
from clldutils.path import walk, Path
import pycountry

from pyglottolog import util
from pyglottolog import languoids


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


class Glottolog(object):
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

    def languoid(self, id_):
        if ISO_CODE_PATTERN.match(id_):
            for l in languoids.walk_tree(tree=self.tree):
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

    def add_languoid(self):
        pass
