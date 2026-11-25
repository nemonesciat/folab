"""Parley on the road (parley.py) in a small mod of its own: two roadside pirates (stand-ins), the standing step first, then
parley as one Undo: the leader swapped to a record of its own with its hailing script, the crew to the parley faction
(allied to the Fiends, neutral to you), the five choices' lines with their checks and costs, the standing script made
again counting them. Written and read back. Nothing near the real game."""
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
from kuliouquest import _person  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


G = server.GD = gamedata.GameData()
server.BR = browse.Browse(G, lambda: server.PR)
pr = server.PR = project.Project.create('Parley Test')
world = next(w for c, w in G.ext_cells.items() if G.edid(w) == 'WastelandNV')
grid = G.grid(world)
x0, y0 = -18 * 4096.0 + 2000, 2000.0
cell = G.key(grid[(int(x0 // 4096), int(y0 // 4096))])
base = server.edit('a roadside pirate', [{'op': 'record_new', 'record': _person(G, pr, PL.ROADSIDE, 'Pirate', 'NVProspectorMale')}])['made'][0]
made = server.edit('four of them', [{'op': 'add', 'cell': cell, 'base': base, 'p': [x0 + dx, y0, 9000.0, 0, 0, 0], 's': 1.0}
                                    for dx in (0, 300, 5000, 5300)])['made']
RS.apply(pr, G)
# (plan() reads the concept map over Waikiki: here a plan is given, one pair kept, one new group, one pair taken out)
P = {'world': G.key(world), 'skipped': [], 'rows': [
        {'leader': (cell, made[0]), 'crew': [(cell, made[1])], 'p': [x0, y0, 9000]},
        {'new': [(x0 + 900.0, y0 + 900.0, 9004.0, 0.0), (x0 + 1100.0, y0 + 900.0, 9004.0, 0.0)], 'p': [x0 + 1000, y0 + 900, 9000]}],
     'remove': [{'refs': [(cell, made[2]), (cell, made[3])], 'p': [x0 + 5000, y0, 9000], 'holder': 'court'}]}
undo0 = len(pr.undo_stack)
rep = PL.apply(pr, G, P)
check('one Undo', len(pr.undo_stack) == undo0 + 1)
check('14 lines a leader, two leaders', rep['lines'] == 28 and rep['leaders'] == 2, rep['lines'])
check('the pair in the court land taken out, one new group', rep['removed'] == 2 and rep['new_groups'] == 1, rep)
check('the removed refs are gone', all(made[k] not in pr.cells[cell]['refs'] for k in (2, 3)))
os.makedirs(project.BUILD_DIR, exist_ok=True)
out = os.path.join(project.BUILD_DIR, 'Parley Test.esp')
espwrite.write(G, pr, out)
g = gamedata.GameData(plugins=list(gamedata.OFFICIAL) + [out])
i = len(g.plugins) - 1
mine = {tes4.zstr(g.fields(f).get('EDID', b'')): f for f, (n, r) in g.forms.items() if n == i}
fid = lambda e: g.forms[mine[e]][1].formid
lead = dict(tes4.iter_subrecords(g.plugins[i].data(g.forms[mine['FOLabParleyLeader01']][1])))
check('the leader has its hailing script and the parley faction', struct.unpack('<I', lead['SCRI'])[0] == fid('FOLabParleyLeader01Script')
      and struct.unpack('<I', lead['SNAM'][:4])[0] == fid('FOLabParleyPirates'))
ls = dict(tes4.iter_subrecords(g.plugins[i].data(g.forms[mine['FOLabParleyLeader01Script']][1])))['SCTX']
check('it stops you within 600, once a day', b'GetDistance player < 600' in ls and b'StartConversation player FOLabParleyHold' in ls)
fac = dict(tes4.iter_subrecords(g.plugins[i].data(g.forms[mine['FOLabParleyPirates']][1])))
check('the faction: allied to the Fiends', struct.unpack_from('<I', fac['XNAM'], 8)[0] == 2)
srcs = []
for f, (n, r) in g.forms.items():
    if n == i and r.tag == 'INFO':
        sd = list(tes4.iter_subrecords(g.plugins[n].data(r)))
        if struct.unpack('<I', dict(sd)['QSTI'])[0] == fid(PL.QUEST):
            srcs.append(b''.join(v for t, v in sd if t == 'SCTX'))
check('fights, fear and soft touch in the scripts', sum(b'StartCombat player' in s for s in srcs) == 10
      and sum(b'pirates + 5' in s for s in srcs) == 4 and sum(b'pirates - 5' in s for s in srcs) == 4 and sum(b'pirates - 8' in s for s in srcs) == 2)
st = dict(tes4.iter_subrecords(g.plugins[i].data(g.forms[mine[RS.SCRIPT]][1])))['SCTX']
check('the standing script counts the parley pirates\' dead', b'GetDeadCount FOLabParleyLeader01' in st and b'GetDeadCount FOLabPirateRoadsideParley' in st)
s = health.check_file(g, out)['summary']
check('the plugin passes health with no errors', s.get('error', 0) == 0, s)
