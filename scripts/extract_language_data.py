# extract_language_data.py - https://github.com/clld/glottolog/issues/144

from __future__ import unicode_literals

import pathlib
import configparser

import sqlalchemy as sa

SKIP = (
    'iwai1245', 'Iwaidjic', 'name_comment',
    'Ethnologue calls the family "Yiwaidjic", but the name of the language is "Iwaidja", so we use "Iwaidjic".'
)

REPLACE = {
    ('jeri1242', 'name_comment'): (
        'Ethnologue\'s name follows **181522**, but Glottolog adopts the name "Jeli" from **141802**.',
        'Ethnologue\'s name follows **181522**, but Glottolog adopts the name "Jeli" from **141802**.',
        'Ethnologue\'s name follows **hh:w:Kastenholz:Jeri-Kuo**, but Glottolog adopts the name "Jeli" from **hh:g:Trobs:Jeli**.'),
    ('kryt1240', 'name_comment'): (
        'The name form "Kryz" corresponds best to Russian "\u043a\u0440\u044b\u0437\u0441\u043a\u0438\u0439 \u044f\u0437\u044b\u043a", and is used by **30850**.',
        'The name form "Kryz" corresponds best to Russian "\u043a\u0440\u044b\u0437\u0441\u043a\u0438\u0439 \u044f\u0437\u044b\u043a", and is used by Authier (2000).',
        'The name form "Kryz" corresponds best to Russian "\u043a\u0440\u044b\u0437\u0441\u043a\u0438\u0439 \u044f\u0437\u044b\u043a", and is used by **hh:g:Authier:Kryz**.'),
    ('yong1270', 'speakers'): (
        '40000 (estimated) (Lidz 2010: 3, based on Yang 2009)',
        '40,000 (estimated) (Lidz 2010: 3, based on Yang 2009)',
        '40000 (estimated) (**hh:gtd:Lidz:Yongning-Na**: 3, based on **hh:s:Zhenhong:Mosuo**)'),
}

engine = sa.create_engine('postgresql://postgres@/glottolog2.7', echo=True)

l = sa.table('language', *map(sa.column, ['pk', 'id', 'name']))
ld = sa.table('language_data', *map(sa.column, ['object_pk', 'active', 'key', 'value']))

query = sa.select([l.c.id, l.c.name, ld.c.key, ld.c.value], bind=engine)\
    .where(ld.c.object_pk == l.c.pk)\
    .where(ld.c.key.op('!~')('^_'))\
    .order_by(l.c.id, ld.c.key)

tree = pathlib.Path('../languoids/tree')

for gcode, name, key, value in query.execute():
    found = list(tree.rglob('%s/md.ini' % gcode))
    if len(found) != 1:
        assert (gcode, name, key, value) == SKIP
        continue
    ini, = found
    cfg = configparser.ConfigParser()
    with ini.open(encoding='utf-8') as f:
        cfg.read_file(f)
    core = cfg['core']
    if (gcode, key) in REPLACE:
        infile, indb, new = REPLACE[gcode, key]
        assert core[key] == infile
        assert value == indb
        value = new
    elif key in core:
        assert core[key] == value
        continue
    core[key] = value
    with ini.open('w', encoding='utf-8') as f:
        f.write('# -*- coding: utf-8 -*-\n')
        cfg.write(f)
