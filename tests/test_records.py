import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import copy, struct, sys
import gamedata, project, espwrite, recordio, schema, tes4
gd = gamedata.GameData()
pr = project.Project.create('Records Test'); pr.cells, pr.records, pr.next_id = {}, {}, project.FIRST_ID
def check(what, ok): print(('PASS ' if ok else 'FAIL ') + what)
def find(edid):
    for fid, (i, rec) in gd.forms.items():
        if rec.tag in ('WEAP', 'CELL') and tes4.zstr(gd.plugins[i].fields(rec).get('EDID', b'')) == edid: return fid
w = find('Weap10mmPistol'); gra = next(fid for fid, (i, r) in gd.forms.items() if r.tag == 'WEAP' and gd.names[i] == 'gunrunnersarsenal.esm' and fid >> 24 == i)
cell = find('2EOVault21')
def setf(rec, tag, name, v):
    s = next(s for s in rec['subs'] if s['tag'] == tag); f = next(f for f in s['fields'] if f.get('name') == name); f['value'] = v
r1 = recordio.load(gd, w); setf(r1, 'DATA', 'Damage', 99)
r2 = recordio.load(gd, w); recordio.set_field(r2, 'EDID', 'FOLabTestPistol'); recordio.set_field(r2, 'FULL', 'Test Pistol')
r3 = recordio.load(gd, gra); setf(r3, 'DATA', 'Value', 12345)
r4 = recordio.load(gd, cell); recordio.set_field(r4, 'FULL', 'Vault 21 (edited)')
made = pr.apply('records', [{'op': 'record', 'key': gd.key(w), 'record': r1}, {'op': 'record_new', 'record': r2},
                            {'op': 'record', 'key': gd.key(gra), 'record': r3}, {'op': 'record', 'key': gd.key(cell), 'record': r4}])
pr.apply('place', [{'op': 'add', 'cell': gd.key(cell), 'base': made[0], 'p': [0, 0, 7968, 0, 0, 0]}])
path = pr.plugin_path(); espwrite.write(gd, pr, path)
p = tes4.PluginFile(path); print('masters', p.header['masters'], 'top groups', p.top_groups())
gd2 = gamedata.GameData(plugins=list(gamedata.OFFICIAL) + [path]); me = len(gd2.plugins) - 1
def data(g, fid): i, rec = g.source(fid); return i, rec, list(tes4.iter_subrecords(g.plugins[i].data(rec)))
i, rec, subs = data(gd2, w); d = dict(subs)
check('override wins and has new damage', i == me and struct.unpack_from('<h', d['DATA'], 12)[0] == 99)
_, _, orig = data(gd, w)
check('override: every other subrecord byte-identical once links resolve', len(subs) == len(orig))
same = True
for (t1, a), (t2, b) in zip(orig, subs):
    if t1 != t2: same = False; continue
    if t1 == 'DATA': continue
    offs = schema.form_offsets('WEAP', t1, a)
    for o in offs:
        x, y = struct.unpack_from('<I', a, o)[0], struct.unpack_from('<I', b, o)[0]
        if x and gd.to_global(gd.source(w)[0], x) != gd2.to_global(me, y): same = False; print('  link differs', t1)
    am, bm = bytearray(a), bytearray(b)
    for o in offs: am[o:o+4] = bm[o:o+4] = b'\0\0\0\0'
    if am != bm: same = False; print('  bytes differ', t1)
check('  ...and they do', same)
newfid = (me << 24) | int(made[0][1:], 16)
i, rec, subs = data(gd2, newfid); d = dict(subs)
check('new record exists with its own EDID/name', rec.tag == 'WEAP' and tes4.zstr(d['EDID']) == 'FOLabTestPistol' and tes4.zstr(d['FULL']) == 'Test Pistol')
check('new record keeps ammo link', gd2.to_global(me, struct.unpack('<I', d['NAM0'])[0]) == gd.to_global(gd.source(w)[0], struct.unpack('<I', dict(orig)['NAM0'])[0]))
i, rec, subs = data(gd2, gra); d = dict(subs); _, _, og = data(gd, gra); od = dict(og)
links_ok = all(gd.to_global(gd.source(gra)[0], struct.unpack_from('<I', od[t], o)[0]) == gd2.to_global(me, struct.unpack_from('<I', d[t], o)[0])
               for t in od for o in schema.form_offsets('WEAP', t, od[t]) if struct.unpack_from('<I', od[t], o)[0])
check('GRA override: value changed, every known link re-pointed right', struct.unpack_from('<i', d['DATA'])[0] == 12345 and links_ok)
i, rec, subs = data(gd2, cell)
check('CELL record override in the place group', i == me and tes4.zstr(dict(subs)['FULL']) == 'Vault 21 (edited)')
placed = [r for r in gd2.refs(cell) if r['base'] == newfid]
check('the new weapon placed in the cell', len(placed) == 1)
pr.undo(); pr.undo(); check('undo takes records back out', pr.records == {} and pr.cells == {})
