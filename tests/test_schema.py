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

# a DLC weapon's newly laid-out DNAM: its projectile link is a real key, and re-pointing it for another plugin lands right
import recordio, struct, tes4
dlc = next((fid for fid, (i, r) in gd.forms.items() if r.tag == 'WEAP' and i > 0 and gd.names[i] == 'gunrunnersarsenal.esm'
            and any(t == 'DNAM' and struct.unpack_from('<I', d, 36)[0] for t, d in tes4.iter_subrecords(gd.plugins[i].data(r)))), None)
i, rec = gd.source(dlc)
raw = dict(tes4.iter_subrecords(gd.plugins[i].data(rec)))['DNAM']
want = gd.to_global(i, struct.unpack_from('<I', raw, 36)[0])
r = recordio.load(gd, dlc)
dnam = next(s for s in r['subs'] if s['tag'] == 'DNAM')
print('PASS' if dnam['kind'] == 'struct' else 'FAIL', 'DLC weapon DNAM is read as named fields, not raw')
proj = next(f for f in dnam['fields'] if f.get('name') == 'Projectile')
print('PASS' if proj['value'] == gd.key(want) else 'FAIL', 'its projectile is the right form key (%s)' % proj['value'])
out = dict(recordio.to_bytes(r, lambda k: (0x7F << 24) | (gd.from_key(k) & 0xFFFFFF)))['DNAM']
print('PASS' if struct.unpack_from('<I', out, 36)[0] == (0x7F << 24) | (want & 0xFFFFFF) and out[:36] == raw[:36] and out[40:] == raw[40:] else 'FAIL',
      're-pointed to another plugin: only the projectile link changes')
