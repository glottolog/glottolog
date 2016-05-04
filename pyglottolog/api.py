from __future__ import unicode_literals
import re

from clldutils.path import walk, Path

from pyglottolog import util
from pyglottolog import languoids


ISO_CODE_PATTERN = re.compile('[a-z]{3}$')


class Glottolog(object):
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
        for d in walk(self.tree, mode='dirs'):
            if ids is None or d.name in ids:
                yield languoids.Languoid.from_dir(d)
