# coding: utf8
from __future__ import unicode_literals, print_function, division

import attr
from whoosh import index
from whoosh.fields import Schema, TEXT, KEYWORD, ID
from whoosh.analysis import StemmingAnalyzer
from whoosh.qparser import QueryParser

from clldutils.path import rmtree
from clldutils.misc import slug


@attr.s
class Document(object):
    id = attr.ib()
    provider = attr.ib()
    title = attr.ib()
    author = attr.ib()
    authoryear = attr.ib()
    year = attr.ib()
    doctype = attr.ib()
    lgcode = attr.ib()


def get_index(api, recreate=False):
    index_dir = api.ftsindex
    if index_dir.exists() and recreate:
        rmtree(index_dir)  # pragma: no cover
    if not index_dir.exists():
        index_dir.mkdir()
        schema = Schema(
            id=ID(stored=True),
            provider=KEYWORD(stored=True),
            authoryear=TEXT(stored=True),
            title=TEXT(analyzer=StemmingAnalyzer(), stored=True),
            author=TEXT(stored=True),
            year=TEXT(stored=True),
            doctype=TEXT(stored=True),
            lgcode=TEXT(stored=True),
            body=TEXT(),
            tags=KEYWORD)
        return index.create_in(index_dir.as_posix(), schema)
    return index.open_dir(index_dir.as_posix())


def search(repos, q, limit=1000, **kw):
    index_ = get_index(repos)
    qp = QueryParser("body", schema=index_.schema)
    q = '{0} {1}'.format(q, ' '.join('{0}:"{1}"'.format(k, v) for k, v in kw.items()))

    with index_.searcher() as searcher:
        results = searcher.search(qp.parse(q), limit=limit)
        return len(results), [Document(**res) for res in results]


def build_index(api, log):
    writer = get_index(api, recreate=True).writer()
    for bibfile in api.bibfiles:
        log.info('indexing {0}'.format(bibfile))
        for id_, (type_, fields) in bibfile.iterentries():
            author = fields.get('author', '')
            if author:
                author = slug(author.split()[0])
            writer.add_document(
                id='{0}:{1}'.format(bibfile.fname.stem, id_),
                provider='%s' % bibfile.fname.stem,
                title=fields.get('title', fields.get('booktitle', '')),
                author=fields.get('author', fields.get('editor', '')),
                year=fields.get('year', ''),
                doctype=fields.get('hhtype', ''),
                lgcode=fields.get('lgcode', ''),
                body='%s' % fields,
                authoryear='{0}{1}'.format(author, fields.get('year', '')).lower())
    writer.commit()
