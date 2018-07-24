from __future__ import unicode_literals

import pytest

from clldutils.path import walk

from pyglottolog.lff import read_lff, rmtree, lff2tree, tree2lff
from pyglottolog.languoids import Level


def test_rmtree(tmpdir):
    d = tmpdir
    for _ in range(80):  # https://bugs.python.org/issue18199
        d /= 'a'
        d.mkdir()
        (d / 'a.ini').write_text('a', encoding='utf-8')
    root = tmpdir / 'a'
    assert root.exists()
    rmtree(str(root))
    assert not root.exists()


def _set_lff(api_copy, name, content):
    api_copy.build_path(name).write_text(content, encoding='utf-8')
    return content


def test_lff2tree(api_copy):
    lfftext = _set_lff(api_copy, 'lff.txt', """# -*- coding: utf-8 -*-
Abkhaz-Adyge [abkh1242] aaa
    Ubykh [ubyk1235]uby
Abkhaz-Adyge [abkh1242] aaa; Abkhaz-Abaza [abkh1243]
    Abaza [abaz1241]abq
    Abkhazian [abkh1244]abk
Abkhaz-Adyge [abkh1242] aaa; Circassian [circ1239]
    Adyghe [adyg1241]ady
    Kabardian [kaba1278]kbd
""")

    _set_lff(api_copy, 'dff.txt', """# -*- coding: utf-8 -*-
Abaza [abaz1241] abq
    Ashkaraua [ashk1247]
    Bezshagh [bezs1238]
    Tapanta [tapa1256]
Abkhazian [abkh1244] abk
    Abzhui [abzh1238]
    Bzyb [bzyb1238]
    Samurzakan [samu1242]
""")

    lff2tree(api_copy)
    assert api_copy.languoid('abkh1242').iso == 'aaa'
    assert api_copy.languoid('ashk1247').level == Level.dialect
    assert api_copy.languoid('abaz1241').level == Level.language
    assert api_copy.languoid('abaz1241').hid == 'abq'

    _set_lff(api_copy, 'lff.txt', lfftext.replace('Abkhaz-Abaza', 'Abkhaz-Abazzza'))
    lff2tree(api_copy)
    glottocodes = [d.name for d in walk(api_copy.tree, mode='dirs')]
    assert len(glottocodes) == len(set(glottocodes))

    abkh1243 = api_copy.languoid('abkh1243')
    # Make sure the new name is picked up ...
    assert abkh1243.name == 'Abkhaz-Abazzza'
    # ... and the old one retained as alternative name:
    assert 'Abkhaz-Abaza' in abkh1243.names['glottolog']

    lfftext = _set_lff(api_copy, 'lff.txt', """# -*- coding: utf-8 -*-
Abkhaz-Adyge [abkh1242]
    Ubykh [ubyk1235]
Abkhaz-Adyge [abkh1242]; Abkhaz-Abaza [abkh1243]; Abaza [abaz1241]
    Ashkaraua [ashk1247]xyz
    Abkhazian [abkh1244]
Abkhaz-Adyge [abkh1242]; Circassian [circ1239]
    Adyghe [adyg1241]ady
    Kabardian [kaba1278]
Abkhaz-Adyge [abkh1242]; Circassian [circ1239]; New Group []
    New name []NOCODE_New-name
    Another one []
""")

    _set_lff(api_copy, 'dff.txt', """# -*- coding: utf-8 -*-
Ashkaraua [ashk1247]xyz
    Bezshagh [bezs1238]
    Tapanta [tapa1256]
Abkhazian [abkh1244]
    Abzhui [abzh1238]
    Bzyb [bzyb1238]
    Samurzakan [samu1242]
Kabardian [kaba1278]
    Dia []aaa
""")

    lff2tree(api_copy)
    assert api_copy.languoid('abaz1241').level == Level.family
    # Now we test two things:
    # - aaa has been removed as ISO code from abkh1242
    # - aaa has been attached as ISO code to a newly created language
    assert api_copy.languoid('aaa').name == 'Dia'
    langs = list(api_copy.languoids())
    assert 'newg1234' in api_copy.glottocodes
    assert sum(1 for l in langs if l.name == 'New Group') == 1
    assert sum(1 for l in langs if l.hid == 'NOCODE_New-name') == 1

    # Test ISO code removal:
    _set_lff(api_copy, 'dff.txt', """# -*- coding: utf-8 -*-
Kabardian [kaba1278]
    Dia []
""")
    lff2tree(api_copy)
    assert api_copy.languoid('aaa') is None

    tree2lff(api_copy)

    # Test hid adding
    _set_lff(api_copy, 'dff.txt', """# -*- coding: utf-8 -*-
Ashkaraua [ashk1247]xyz
    Ashkarauax [bezs1238]NOCODE_abc
""")
    lff2tree(api_copy)
    assert api_copy.languoid('bezs1238').hid == 'NOCODE_abc'

    #
    # Nodes must have unique names!
    #
    _set_lff(api_copy, 'dff.txt', """# -*- coding: utf-8 -*-
Ashkaraua [ashk1247]xyz
    Ashkaraua [bezs1238]
""")
    with pytest.raises(ValueError, match=r'duplicate'):
        lff2tree(api_copy)

    #
    # Nodes must have consistent names!
    #
    _set_lff(api_copy, 'dff.txt', """# -*- coding: utf-8 -*-
Ashkxxxaraua [ashk1247]xyz
    Bezshagh [bezs1238]
""")
    with pytest.raises(ValueError, match=r'inconsistent'):
        lff2tree(api_copy)

    #
    # Top-level nodes in dff must be languages:
    #
    _set_lff(api_copy, 'dff.txt', """# -*- coding: utf-8 -*-
Abaza [abaz1241]
    Bezshagh [bezs1238]
""")
    with pytest.raises(ValueError, match=r'inconsistent'):
        lff2tree(api_copy)

    #
    # Top-level nodes in dff must be languages in lff:
    #
    _set_lff(api_copy, 'dff.txt', """# -*- coding: utf-8 -*-
None [xyzz1234]
    Dia []
""")
    with pytest.raises(ValueError, match=r'invalid'):
        lff2tree(api_copy)

    #
    # Isolates must not have multiple ancestors:
    #
    _set_lff(api_copy, 'dff.txt', """# -*- coding: utf-8 -*-
None [xyzz1234]; Other [-isolate-]
    Dia []
""")
    with pytest.raises(ValueError, match=r'isolate'):
        lff2tree(api_copy)

    #
    # Languages must appear after a classification line:
    #
    _set_lff(api_copy, 'dff.txt', """# -*- coding: utf-8 -*-
    Dia []
""")
    with pytest.raises(ValueError, match=r'classification'):
        lff2tree(api_copy)


def test_read_lff_error(tmpdir, mocker):
    lff = tmpdir / 'lff.txt'
    lff.write_text("""
Name [ac1234]; Name2 [abcd1235]
    Lang [abcd1236]abc
""", encoding='utf-8')

    with pytest.raises(ValueError):
        list(read_lff(None, mocker.Mock(), {}, Level.language, str(lff)))
