from __future__ import print_function

from pyglottolog import Glottolog
from treemaker import TreeMaker
from newick import loads


def make_tree(repos, *taxa):
    # We create a dict to lookup Glottolog languoids by name, ISO- or Glottocode.
    langs = {}
    for lang in Glottolog(repos).languoids():
        if lang.iso:
            langs[lang.iso] = lang
        langs[lang.name] = lang
        langs[lang.id] = lang

    t = TreeMaker()
    for taxon in taxa:
        if taxon not in langs:
            print('unknown taxon: {0}'.format(taxon))
            continue
        t.add(taxon, ', '.join(l[1] for l in langs[taxon].lineage))
    return t


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('--format', help='output format [nexus|newick|ascii]', default='ascii')
    parser.add_argument('--repos', default=None)
    parser.add_argument('taxa', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    tree = make_tree(args.repos, *args.taxa)
    if args.format == 'ascii':
        print(loads(tree.write())[0].ascii_art())
    else:
        print(tree.write(args.format))
