"""Yield and recruit (yieldrecruit.py) on parley's road bosses, in a small mod of its own: parley first (one kept pair),
then this step as one Undo: the leader's script made again (yield below a quarter of his health, his crew stopped too,
then off the road when sent), the crew named, his follow package first and only while your teammate, the yield's
choices and the parting line. Written and read back. Nothing near the real game."""
import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import browse  # noqa: E402
import espwrite  # noqa: E402
import gamedata  # noqa: E402
import health  # noqa: E402
import parley as PL  # noqa: E402
import project  # noqa: E402
import repstanding as RS  # noqa: E402
import server  # noqa: E402
import tes4  # noqa: E402
import yieldrecruit as YR  # noqa: E402
from kuliouquest import _person  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


G = server.GD = gamedata.GameData()
server.BR = browse.Browse(G, lambda: server.PR)
pr = server.PR = project.Project.create('Yield Test')
world = next(w for c, w in G.ext_cells.items() if G.edid(w) == 'WastelandNV')
grid = G.grid(world)
x0, y0 = -18 * 4096.0 + 2000, 2000.0
cell = G.key(grid[(int(x0 // 4096), int(y0 // 4096))])
base = server.edit('a roadside pirate', [{'op': 'record_new', 'record': _person(G, pr, PL.ROADSIDE, 'Pirate', 'NVProspectorMale')}])['made'][0]
made = server.edit('two', [{'op': 'add', 'cell': cell, 'base': base, 'p': [x0 + dx, y0, 9000.0, 0, 0, 0], 's': 1.0} for dx in (0, 300)])['made']
RS.apply(pr, G)
PL.apply(pr, G, {'world': G.key(world), 'skipped': [], 'remove': [], 'rows': [{'leader': (cell, made[0]), 'crew': [(cell, made[1])], 'p': [x0, y0, 9000]}]})
P = YR.plan(G, pr)
check('one leader with his crew', len(P['rows']) == 1 and len(P['rows'][0]['crew']) == 1, P)
undo0 = len(pr.undo_stack)
rep = YR.apply(pr, G, P)
check('one Undo', len(pr.undo_stack) == undo0 + 1)
check('8 lines for one leader', rep['lines'] == 8, rep['lines'])
check('the crew named', pr.cells[cell]['refs'][made[1]].get('edid') == 'FOLabParleyCrew011REF')
os.makedirs(project.BUILD_DIR, exist_ok=True)
out = os.path.join(project.BUILD_DIR, 'Yield Test.esp')
espwrite.write(G, pr, out)
g = gamedata.GameData(plugins=list(gamedata.OFFICIAL) + [out])
i = len(g.plugins) - 1
mine = {tes4.zstr(g.fields(f).get('EDID', b'')): f for f, (n, r) in g.forms.items() if n == i}
fid = lambda e: g.forms[mine[e]][1].formid
src = dict(tes4.iter_subrecords(g.plugins[i].data(g.forms[mine['FOLabParleyLeader01Script']][1])))['SCTX']
check('he yields below a quarter, his crew stopped, then leaves', b'GetHealthPercentage < 0.25' in src and b'FOLabParleyCrew011REF.StopCombat' in src
      and b'FOLabParleyCrew011REF.Disable' in src and b'StartConversation player FOLabParleyHold' in src)
lead = list(tes4.iter_subrecords(g.plugins[i].data(g.forms[mine['FOLabParleyLeader01']][1])))
pk = [struct.unpack('<I', v)[0] for t, v in lead if t == 'PKID']
check('his follow package first', pk[0] == fid('FOLabParleyFollow'))
fol = [c for t, c in tes4.iter_subrecords(g.plugins[i].data(g.forms[mine['FOLabParleyFollow']][1])) if t == 'CTDA']
check('only while your teammate', len(fol) == 1 and struct.unpack_from('<H', fol[0], 8)[0] == 454)
srcs = []
for f, (n, r) in g.forms.items():
    if n == i and r.tag == 'INFO':
        sd = list(tes4.iter_subrecords(g.plugins[n].data(r)))
        if struct.unpack('<I', dict(sd)['QSTI'])[0] == fid(YR.QUEST):
            srcs.append(b''.join(v for t, v in sd if t == 'SCTX'))
check('recruit, send off, rob, fight, part', sum(b'SetPlayerTeammate 1' in s for s in srcs) == 2 and any(b'SetPlayerTeammate 0' in s for s in srcs)
      and any(b'pirates + 8' in s for s in srcs) and any(b'AddItem LootDuffleBag25 2' in s for s in srcs) and any(b'StartCombat player' in s for s in srcs))
s = health.check_file(g, out)['summary']
check('the plugin passes health with no errors', s.get('error', 0) == 0, s)
