import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import struct, sys
import gamedata, project, espwrite, tes4
gd = gamedata.GameData()
pr = project.Project.create('Roundtrip Two'); pr.cells, pr.next_id = {}, project.FIRST_ID
ops = []
picked = {}
for plug in ('DeadMoney.esm', 'HonestHearts.esm', 'OldWorldBlues.esm'):
    pi = gd.names.index(plug.lower())
    for c in sorted(gd.interiors):
        if c >> 24 != pi: continue
        rs = [r for r in gd.refs(c) if r['ref'] >> 24 == pi and gd.cell_refs[c][r['ref']][1].tag == 'REFR'
              and any(t in tes4.subrecord_dict(gd.plugins[pi].data(gd.cell_refs[c][r['ref']][1])) for t in ('XOWN', 'XTEL', 'XLKR', 'XESP', 'XEMI', 'XNDP'))]
        if rs:
            r = rs[0]; picked[plug] = (c, r)
            ops.append({'op': 'move', 'cell': gd.key(c), 'ref': gd.key(r['ref']), 'p': list(r['pos']) + list(r['rot'])}); break
pr.apply('dlc', ops)
path = pr.plugin_path(); espwrite.write(gd, pr, path)
print('masters', tes4.PluginFile(path).header['masters'])
gd2 = gamedata.GameData(plugins=list(gamedata.OFFICIAL) + [path]); me = len(gd2.plugins) - 1
for plug, (c, r) in picked.items():
    i0, rec0 = gd.cell_refs[c][r['ref']]; i1, rec1 = gd2.cell_refs[c][r['ref']]
    f0 = list(tes4.iter_subrecords(gd.plugins[i0].data(rec0))); f1 = list(tes4.iter_subrecords(gd2.plugins[i1].data(rec1)))
    ok = i1 == me and [t for t, _ in f0] == [t for t, _ in f1]
    n = 0
    for (t, a), (_, b) in zip(f0, f1):
        where = espwrite.FORMID_FIELDS['REFR'].get(t)
        if not where: ok &= (a == b) or t in ('DATA', 'XSCL'); continue
        offs = range(0, len(a) - 3, 4) if where == 'all' else [o for o in where if o + 4 <= len(a)]
        for o in offs:
            x = struct.unpack_from('<I', a, o)[0]; y = struct.unpack_from('<I', b, o)[0]
            if x:
                n += 1; ok &= gd.to_global(i0, x) == gd2.to_global(i1, y)
    print('PASS' if ok else 'FAIL', plug, gd.edid(c), '%d form IDs re-pointed and resolving to the same forms' % n)
# undo / redo
before = pr.count(); pr.apply('extra', [{'op': 'remove', 'cell': ops[0]['cell'], 'ref': ops[0]['ref']}])
u = pr.undo(); a = pr.count(); r = pr.redo(); b = pr.count()
print('PASS' if (u == 'extra' and r == 'extra' and pr.cells[ops[0]['cell']]['refs'][ops[0]['ref']] == {'removed': True}) else 'FAIL', 'undo/redo')
pr2 = project.Project.open('Roundtrip Two'); print('PASS' if pr2.cells == pr.cells else 'FAIL', 'project reloads from disk')
