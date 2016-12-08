# coding: utf8
from __future__ import unicode_literals, print_function, division

import attr
from whoosh import index
from whoosh.fields import Schema, TEXT, KEYWORD, ID
from whoosh.analysis import StemmingAnalyzer
from whoosh.qparser import QueryParser

from clldutils.path import rmtree
from clldutils.misc import slug

from pyglottolog.util import build_path
from pyglottolog.monsterlib._bibtex import iterentries


@attr.s
class Document(object):
    id = attr.ib()
    title = attr.ib()
    author = attr.ib()
    authoryear = attr.ib()
    year = attr.ib()
    doctype = attr.ib()


def get_index(repos=None, recreate=False):
    index_dir = build_path('whoosh', repos=repos)
    if index_dir.exists() and recreate:
        rmtree(index_dir)
    if not index_dir.exists():
        index_dir.mkdir()
        schema = Schema(
            id=ID(stored=True),
            authoryear=TEXT(stored=True),
            title=TEXT(analyzer=StemmingAnalyzer(), stored=True),
            author=TEXT(stored=True),
            year=TEXT(stored=True),
            doctype=TEXT(stored=True),
            body=TEXT(),
            tags=KEYWORD)
        return index.create_in(index_dir.as_posix(), schema)
    return index.open_dir(index_dir.as_posix())


def search(q, limit=1000, **kw):
    index_ = get_index(repos=kw.pop('repos', None))
    qp = QueryParser("body", schema=index_.schema)
    q = '{0} {1}'.format(q, ' '.join('{0}:"{1}"'.format(k, v) for k, v in kw.items()))

    with index_.searcher() as searcher:
        results = searcher.search(qp.parse(q), limit=limit)
        return len(results), [Document(**res) for res in results]


def build_index(repos, monster):
    writer = get_index(recreate=True, repos=repos).writer()
    no_id = 0
    for id_, (type_, fields) in iterentries(monster):
        if 'glottolog_ref_id' not in fields:
            no_id += 1
            continue
        author = fields.get('author', '')
        if author:
            author = slug(author.split()[0])
        writer.add_document(
            id=fields['glottolog_ref_id'],
            title=fields.get('title', fields.get('booktitle', '')),
            author=fields.get('author', fields.get('editor', '')),
            year=fields.get('year', ''),
            doctype=fields.get('hhtype', ''),
            body='%s' % fields,
            authoryear='{0}{1}'.format(author, fields.get('year', '')).lower())
    writer.commit()
    if no_id:
        print('{0} entries without ref ID'.format(no_id))
