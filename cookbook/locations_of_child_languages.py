from clldutils.dsv import UnicodeWriter
from pyglottolog import Glottolog
from pyglottolog.languoids import Level


def locations(glottolog, fid, outpath):
    with UnicodeWriter(outpath) as writer:
        writer.writerow(['name', 'glottocode', 'latitude', 'longitude'])
        for lang in glottolog.languoids():
            if lang.level == Level.language and lang.latitude is not None:
                if fid in [l[1] for l in lang.lineage]:
                    writer.writerow([lang.name, lang.id, lang.latitude, lang.longitude])


if __name__ == '__main__':
    import sys

    locations(Glottolog(sys.argv[1]), sys.argv[2], sys.argv[3])
