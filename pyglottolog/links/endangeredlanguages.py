# coding: utf8
from __future__ import unicode_literals, print_function, division
import re
from collections import OrderedDict

import requests
from bs4 import BeautifulSoup as bs

from clldutils.misc import nfilter
from clldutils import jsonlib

BASE_URL = "http://www.endangeredlanguages.com"
STORE = 'endangeredlanguages.json'


def read_store(fname):
    return jsonlib.load(fname) if fname.exists() else {}


def store(details_, fname):
    db = read_store(fname)
    if not details_:
        return db
    db[details_['id']] = details_
    ordered = OrderedDict()
    for k in sorted(list(db.keys()), key=lambda lid: int(lid)):
        v = OrderedDict()
        for key in sorted(list(db[k].keys())):
            if key != 'id':
                v[key] = db[k][key]
        ordered[k] = v
    jsonlib.dump(ordered, fname, indent=4)
    return db


def get_soup(path):
    return bs(requests.get(BASE_URL + path).content, "html5lib")


def details(path):
    soup = get_soup(path)
    if not soup.find('h2'):
        return
    res = dict(id=path.split('/')[-1], name=soup.find('h2').get_text())
    data = OrderedDict()
    for tr in soup.find_all('tr'):
        tds = list(tr.find_all('td'))
        if len(tds) == 3:
            data[tds[0].get_text().strip()] = tds[2].get_text().strip()

    names = data.get('ALSO KNOWN AS')
    if names:
        res['alternative_names'] = nfilter([n.strip() for n in names.split(',')])
    if data.get('CODE AUTHORITY') == 'ISO 639-3':
        res['iso-639-3'] = data.get('LANGUAGE CODE')
    return res


def scrape(api, update=False):
    store_path = api.repos.joinpath('links', STORE)
    db = read_store(store_path)
    lang_url = re.compile('/lang/(?P<id>[0-9]+)$')
    done = set()
    for a in get_soup('/lang/region').find_all('a', href=True):
        if a['href'].startswith('/lang/country/') and a['href'] not in done:
            for a in get_soup(a['href']).find_all('a', href=True):
                match = lang_url.match(a['href'])
                if match:
                    lid = match.group('id')
                    if lid not in db or update:
                        db = store(details(a['href']), store_path)
            done.add(a['href'])
