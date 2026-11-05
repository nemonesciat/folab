import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import os, struct, sys
import gamedata, project, espwrite, tes4
gd = gamedata.GameData()
pr = project.Project.create('Roundtrip Test')
pr.cells, pr.next_id = {}, project.FIRST_ID
v21 = next(c for c in gd.interiors if gd.edid(c) == '2EOVault21')
dm = next(c for c in gd.interiors if gd.edid(c) == 'NVDLC01Vault')
refs = [r for r in gd.refs(v21) if r['type'] == 'REFR' and r['base'] in gd.forms and gd.describe(r['base'])[0] == 'FURN']
mv, rm = refs[0], refs[1]
dmr = next(r for r in gd.refs(dm) if r['base'] in gd.forms and gd.describe(r['base'])[0] == 'STAT')
chair = gd.key(refs[2]['base'])
ck, dk = gd.key(v21), gd.key(dm)
newp = [mv['pos'][0] + 64, mv['pos'][1], mv['pos'][2], 0, 0, 1.0]
made = pr.apply('test', [
    {'op': 'add', 'cell': ck, 'base': chair, 'p': [100, 200, 7968, 0, 0, 0.5], 's': 1.25},
    {'op': 'move', 'cell': ck, 'ref': gd.key(mv['ref']), 'p': newp},
    {'op': 'remove', 'cell': ck, 'ref': gd.key(rm['ref'])},
    {'op': 'move', 'cell': dk, 'ref': gd.key(dmr['ref']), 'p': list(dmr['pos'][:2]) + [dmr['pos'][2] + 10] + list(dmr['rot'])},
])
path = pr.plugin_path()
n = espwrite.write(gd, pr, path)
print('wrote', path, n, 'bytes; new ref', made)
p = tes4.PluginFile(path)
print('header', p.header)
gd2 = gamedata.GameData(plugins=list(gamedata.OFFICIAL) + [path])
me = len(gd2.plugins) - 1
def check(what, ok):
    print(('PASS ' if ok else 'FAIL ') + what)
r2 = {r['ref']: r for r in gd2.refs(v21)}
allr = {fid: e for fid, e in gd2.cell_refs[v21].items()}
newfid = (me << 24) | int(made[0][1:], 16)
check('new ref present with base/scale/pos', newfid in r2 and r2[newfid]['base'] == refs[2]['base'] and abs(r2[newfid]['scale'] - 1.25) < 1e-6 and r2[newfid]['pos'][2] == 7968)
check('moved ref has new position', [round(v, 3) for v in r2[mv['ref']]['pos'] + r2[mv['ref']]['rot']] == [round(v, 3) for v in newp])
check('moved ref keeps its base', r2[mv['ref']]['base'] == mv['base'])
e = allr[rm['ref']]
check('removed ref is initially disabled and sunk', e[0] == me and e[1].flags & 0x800 and r2[rm['ref']]['pos'][2] == -30000)
check('override records come from our plugin', allr[mv['ref']][0] == me)
d2 = {r['ref']: r for r in gd2.refs(dm)}
check('DLC ref moved, base still resolves', abs(d2[dmr['ref']]['pos'][2] - dmr['pos'][2] - 10) < 1e-3 and d2[dmr['ref']]['base'] == dmr['base'] and d2[dmr['ref']]['base'] in gd2.forms)
# copied CELL fields resolve to the same forms as the original
def cellforms(g, cell, plugin_i):
    i, rec = (plugin_i, None)
    out = {}
    for pi, pl in enumerate(g.plugins):
        for r, path_ in pl.walk():
            pass
    return out
for cell in (v21, dm):
    i0, rec0 = gd.source(cell); i1, rec1 = gd2.source(cell)
    f0 = dict(tes4.iter_subrecords(gd.plugins[i0].data(rec0))); f1 = dict(tes4.iter_subrecords(gd2.plugins[i1].data(rec1)))
    same = True
    for tag, where in espwrite.FORMID_FIELDS['CELL'].items():
        if tag in f0:
            offs = range(0, len(f0[tag]) - 3, 4) if where == 'all' else where
            for o in offs:
                a = struct.unpack_from('<I', f0[tag], o)[0]; b = struct.unpack_from('<I', f1[tag], o)[0]
                if a and gd.to_global(i0, a) != gd2.to_global(i1, b): same = False; print('  differs', tag, hex(a), hex(b))
    check('%s CELL copy from our plugin, form fields point at the same forms' % gd.edid(cell), i1 == me and same and set(f0) == set(f1))
check('untouched refs unchanged', sum(1 for fid, r in r2.items() if fid not in (mv['ref'], rm['ref'], newfid)) == len(gd.refs(v21)) - 2)
