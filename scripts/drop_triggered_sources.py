import pyglottolog

g = pyglottolog.Glottolog()

files = dropped = 0

for l in g.languoids():
    old = l.sources
    new = [s for s in old if s.trigger is None]
    diff = len(old) - len(new)
    if diff:
        print('%s: dropped %d' % (l.glottocode, diff))
        files += 1
        dropped += diff
        l.sources = new
        l.write_info()

print('%d total: %d' % (files, dropped))
