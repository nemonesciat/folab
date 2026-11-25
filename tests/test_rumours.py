"""Rumours (rumours.py) in a small mod of its own: two tellers (stand-ins), map markers named as Waikiki's, then the step
as one Undo: each rumour a line said by any teller (GetIsID OR'd), only until told, its Speech, its end script setting
it told and showing its marker on the map; the markers named; the fallback line. Written and read back."""
import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import browse  # noqa: E402
import espwrite  # noqa: E402
import gamedata  # noqa: E402
import health  # noqa: E402
import project  # noqa: E402
import rumours as RU  # noqa: E402
import server  # noqa: E402
import tes4  # noqa: E402
from kuliouquest import _person  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


G = server.GD = gamedata.GameData()
server.BR = browse.Browse(G, lambda: server.PR)
pr = server.PR = project.Project.create('Rumour Test')
world = next(w for c, w in G.ext_cells.items() if G.edid(w) == 'WastelandNV')
grid = G.grid(world)
x0, y0 = -18 * 4096.0 + 2000, 2000.0
cell = G.key(grid[(int(x0 // 4096), int(y0 // 4096))])
server.edit('tellers', [{'op': 'record_new', 'record': _person(G, pr, e, 'Waikiki Local', 'NVProspectorMale')} for e in RU.TELLERS[:2]])
server.edit('markers', [{'op': 'add', 'cell': cell, 'base': 'FalloutNV.esm:000010', 'p': [x0 + 500 * n, y0, 9000.0, 0, 0, 0], 's': 1.0,
                         'extra': {'persistent': True, 'marker': {'name': name, 'type': 0, 'flags': 2}}}
                        for n, (name, _s, _w) in enumerate(RU.RUMOURS[:3])])
P = RU.plan(G, pr)
check('three rumours with markers, two tellers', len(P['rows']) == 3 and len(P['tellers']) == 2, P['skipped'])
undo0 = len(pr.undo_stack)
rep = RU.apply(pr, G, P)
check('one Undo, four lines', len(pr.undo_stack) == undo0 + 1 and rep['lines'] == 4, rep)
os.makedirs(project.BUILD_DIR, exist_ok=True)
out = os.path.join(project.BUILD_DIR, 'Rumour Test.esp')
espwrite.write(G, pr, out)
g = gamedata.GameData(plugins=list(gamedata.OFFICIAL) + [out])
i = len(g.plugins) - 1
mine = {tes4.zstr(g.fields(f).get('EDID', b'')): f for f, (n, r) in g.forms.items() if n == i}
fid = lambda e: g.forms[mine[e]][1].formid
infos = []
for f, (n, r) in g.forms.items():
    if n == i and r.tag == 'INFO':
        sd = list(tes4.iter_subrecords(g.plugins[n].data(r)))
        if struct.unpack('<I', dict(sd)['QSTI'])[0] == fid(RU.QUEST):
            infos.append((b''.join(v for t, v in sd if t == 'SCTX'), [c for t, c in sd if t == 'CTDA']))
check('each rumour shows its marker once told', sum(b'ShowMap FOLabMarker' in s for s, _c in infos) == 3)
check('any teller says it (two GetIsID, the first OR\'d)', all(sum(1 for c in cs if struct.unpack_from('<H', c, 8)[0] == 72) == 2
                                                               and cs[0][0] & 1 for _s, cs in infos))
s = health.check_file(g, out)['summary']
check('the plugin passes health with no errors', s.get('error', 0) == 0, s)
