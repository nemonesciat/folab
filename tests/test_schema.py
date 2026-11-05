import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import sys, time
import gamedata, schema
gd = gamedata.GameData()
t = time.time()
records, stats = schema.checkall(gd)
print('checked in %.0fs' % (time.time() - t))
for rtype in schema.TYPES:
    st = stats[rtype]
    described = {k: v for k, v in st.items() if schema.layout(rtype, k)}
    bad = {k: v for k, v in described.items() if v[1]}
    raw = sorted(k for k in st if not schema.layout(rtype, k))
    print(('FAIL ' if bad else 'PASS ') + '%s: %d records, layouts wrong: %s' % (rtype, records[rtype], ', '.join('%s %d/%d' % (k, v[1], v[0] + v[1]) for k, v in bad.items()) or 'none'))
