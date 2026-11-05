import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import os, struct, sys, hashlib
import gamedata, project, espwrite, recordio, adopt, plugintree, tes4
import shutil
src = os.path.join(os.environ['FOLAB_HOME'], 'DMTest.esm')     # (Dead Money's master, copied as if it were a mod)
shutil.copyfile(os.path.join(gamedata.find_data_dir(), 'DeadMoney.esm'), src)
def check(what, ok): print(('PASS ' if ok else 'FAIL ') + what)
gd = gamedata.GameData()
name = adopt.adopt(gd, src)
pr = project.Project.open(name)
gd2 = gamedata.GameData(plugins=list(gamedata.OFFICIAL) + [pr.source_path()])
me = len(gd2.plugins) - 1
out = pr.plugin_path()
espwrite.write(gd2, pr, out)
a, b = open(src, 'rb').read(), open(out, 'rb').read()
check('opened and saved untouched: the same file (%d bytes)' % len(a), a == b)
if a != b:
    i = next(i for i in range(min(len(a), len(b))) if a[i] != b[i]); print('  first difference at', i, len(a), len(b))
# edits
own = lambda tag: next(fid for fid, (i, r) in gd2.forms.items() if i == me and r.tag == tag and fid >> 24 == me)
w = own('WEAP')
rec = recordio.load(gd2, w)
d = next(s for s in rec['subs'] if s['tag'] == 'DATA'); next(f for f in d['fields'] if f['name'] == 'Value')['value'] = 777
cell = next(c for c in gd2.interiors if c >> 24 == me and len([r for r in gd2.refs(c) if r['ref'] >> 24 == me]) > 5)
refs = [r for r in gd2.refs(cell) if r['ref'] >> 24 == me and r['type'] == 'REFR' and r['pos']]
mv, rm = refs[0], refs[1]
base = gd2.key(refs[2]['base'])
ck = gd2.key(cell)
made = pr.apply('edits', [{'op': 'record', 'key': gd2.key(w), 'record': rec},
                          {'op': 'move', 'cell': ck, 'ref': gd2.key(mv['ref']), 'p': [mv['pos'][0] + 50] + list(mv['pos'][1:]) + list(mv['rot'])},
                          {'op': 'remove', 'cell': ck, 'ref': gd2.key(rm['ref'])},
                          {'op': 'add', 'cell': ck, 'base': base, 'p': [1, 2, 3, 0, 0, 0]}])
espwrite.write(gd2, pr, out)
t0, t1 = plugintree.Plugin.read(src), plugintree.Plugin.read(out)
r0 = {r.formid: r.bytes() for r, _p, _x in t0.records()}; r1 = {r.formid: r.bytes() for r, _p, _x in t1.records()}
own_index = len(tes4.PluginFile(src).header['masters'])
loc = lambda fid: (own_index << 24) | (fid & 0xFFFFFF)
changed = {f for f in r0 if f in r1 and r0[f] != r1[f]}; gone = set(r0) - set(r1); new = set(r1) - set(r0)
check('only the weapon and the moved ref changed', changed == {loc(w), loc(mv['ref'])}); print('  changed', sorted(hex(x) for x in changed), 'expected', hex(loc(w)), hex(loc(mv['ref'])))
check('the removed ref (its own) is gone', gone == {loc(rm['ref'])})
check('one new ref, with the next free ID', len(new) == 1 and (list(new)[0] & 0xFFFFFF) == int(made[0][1:], 16)); print('  new', [hex(x) for x in new], made, 'next_id', hex(pr.next_id))
gd3 = gamedata.GameData(plugins=list(gamedata.OFFICIAL) + [out])
w3 = (len(gd3.plugins) - 1 << 24) | (w & 0xFFFFFF)
i3, rec3 = gd3.source(w3)
check('weapon value is 777 in the saved file', struct.unpack_from('<i', dict(tes4.iter_subrecords(gd3.plugins[i3].data(rec3)))['DATA'])[0] == 777)
check('group structure otherwise intact (same number of groups + 1 at most)', abs(t1.count() - t0.count()) <= 2)
[q.close() for q in gd3.plugins]; pr.esm = True; espwrite.write(gd2, pr, out)
check('save as master sets the ESM flag', tes4.PluginFile(out).header['flags'] & 1 == 1)
