"""The four secrets (secretcaches.py) in a small mod of its own, from given plans: the Alewa site (a hard terminal
whose item unlocks a salvage cache that only its script can open) and the Heights site (a terminal whose plan's script
reveals a hidden map marker at the Vault's back door). Written and read back. Nothing near the real game."""
import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import browse  # noqa: E402
import espwrite  # noqa: E402
import gamedata  # noqa: E402
import health  # noqa: E402
import project  # noqa: E402
import secretcaches as SC  # noqa: E402
import server  # noqa: E402
import tes4  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


G = server.GD = gamedata.GameData()
server.BR = browse.Browse(G, lambda: server.PR)
pr = server.PR = project.Project.create('Secrets Test')
world = next(w for c, w in G.ext_cells.items() if G.edid(w) == 'WastelandNV')
W = G.key(world)
grid = G.grid(world)
x0, y0 = -18 * 4096.0 + 2000, 2000.0
cell = G.key(grid[(int(x0 // 4096), int(y0 // 4096))])
P = {'site': 'alewa', 'skipped': [], 'rows': [{'what': 'terminal', 'world': W, 'p': (x0, y0, 9000.0, 0.0), 'near': {}},
                                              {'what': 'cache', 'world': W, 'p': (x0 + 400, y0, 9000.0, 0.0), 'near': {}}]}
o, rep = SC.ops(G, pr, P)
pr.apply(SC.SITES['alewa']['label'], o)
check('alewa: a hard terminal and the cache', rep['terminals'][0]['science'] == 75 and rep['cache']['items'] == ['Ammo556mm', 'Stimpak'], rep)
Q = {'site': 'heights', 'skipped': [], 'rows': [{'what': 'terminal', 'world': W, 'p': (x0, y0 + 600, 9000.0, 0.0), 'near': {}},
                                                {'what': 'marker', 'cell': cell, 'p': (x0 + 900, y0 + 900, 9000.0), 'type': 4}]}
o2, rep2 = SC.ops(G, pr, Q)
pr.apply(SC.SITES['heights']['label'], o2)
check('heights: the terminal and the hidden marker', rep2['made'] == ['FOLabVaultServiceDoorMarker', 'FOLabHeightsEstate'], rep2['made'])
try:
    SC.ops(G, pr, P)
    check('a second go at a site refused', False)
except ValueError:
    check('a second go at a site refused', True)
os.makedirs(project.BUILD_DIR, exist_ok=True)
out = os.path.join(project.BUILD_DIR, 'Secrets Test.esp')
espwrite.write(G, pr, out)
g = gamedata.GameData(plugins=list(gamedata.OFFICIAL) + [out])
i = len(g.plugins) - 1
mine = {tes4.zstr(g.fields(f).get('EDID', b'')): f for f, (n, r) in g.forms.items() if n == i}
refs = {}
for c, rr in g.cell_refs.items():
    for f, (n, r) in rr.items():
        if n == i:
            d = dict(tes4.iter_subrecords(g.plugins[n].data(r)))
            if 'EDID' in d:
                refs[tes4.zstr(d['EDID'])] = (r, d)
r, d = refs['FOLabAlewaSalvageCacheREF']
check('the cache: persistent, needs a key', r.flags & tes4.PERSISTENT and d['XLOC'][0] == 255)
t = list(tes4.iter_subrecords(g.plugins[i].data(g.forms[mine['FOLabAlewaWallWatch']][1])))
check('the wall watch unlocks the cache by its script', [v for k, v in t if k == 'SCTX'] == [b'FOLabAlewaSalvageCacheREF.Unlock']
      and struct.unpack('<I', next(v for k, v in t if k == 'SCRO'))[0] == r.formid)
mr, md = refs['FOLabVaultServiceDoorMarker']
h = list(tes4.iter_subrecords(g.plugins[i].data(g.forms[mine['FOLabHeightsEstate']][1])))
check('the estate plan reveals the marker (ShowMap), a map marker', [v for k, v in h if k == 'SCTX'] == [b'ShowMap FOLabVaultServiceDoorMarker']
      and struct.unpack('<I', next(v for k, v in h if k == 'SCRO'))[0] == mr.formid and 'XMRK' in md)
s = health.check_file(g, out)['summary']
check('the plugin passes health with no errors', s.get('error', 0) == 0, s)
