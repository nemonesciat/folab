"""Waikiki's robots (robots.py) in a small mod of its own: every kind's record (a copy of the game's robot, its script gone,
the court's robots in the court's faction and unaggressive, the ruins' keeping the game's RobotFaction), spots inside a
game place picked on its navmesh clear of doors, people and seats, hostile ones refused where someone stands, and the ops:
'place' refs with their keys taken first, the bank guards named and persistent, the bank's terminal shutting them down.
Written as a plugin and read back. Nothing goes near the real game."""
import math
import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import browse  # noqa: E402
import espwrite  # noqa: E402
import factionfolk as ff  # noqa: E402
import gamedata  # noqa: E402
import health  # noqa: E402
import project  # noqa: E402
import recordio  # noqa: E402
import robots as R  # noqa: E402
import server  # noqa: E402
import tes4  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


G = server.GD = gamedata.GameData()
server.BR = browse.Browse(G, lambda: server.PR)
pr = server.PR = project.Project.create('Robot Test')
fac = server.edit('the court', [{'op': 'record_new', 'record': ff._faction(G, *ff.FACTIONS['court'])}])['made'][0]
key = lambda e, tag: G.key(next(f for f, (i, r) in G.forms.items() if r.tag == tag and G.edid(f) == e))
robot_faction = key(R.ROBOT_FACTION, 'FACT')

# ---- the records ----
for kind, (src, edid, name, court, aggr, conf, package) in R.KINDS.items():
    rec = R.robot_record(G, pr, kind)
    tags = [s['tag'] for s in rec['subs']]
    facs = [next(f['value'] for f in s['fields'] if f.get('name') == 'Faction') for s in rec['subs'] if s['tag'] == 'SNAM']
    check('%s: %s, named %s, no script or template' % (kind, edid, name), recordio.field(rec, 'EDID') == edid and recordio.field(rec, 'FULL') == name
          and 'SCRI' not in tags and 'TPLT' not in tags)
    check('%s: its side' % kind, facs == [fac if court else robot_faction], facs)
    check('%s: aggression %d, one package' % (kind, aggr), ff._num(rec, 'AIDT', 'Aggression') == aggr and tags.count('PKID') == 1)

# ---- spots inside a game place (its navmesh, its doors) ----
room = key('CrimsonCaravanBarracks01', 'CELL')
got, why = R.inside_spots(G, pr, room, ('butler', 'doorman', 'housekeeper'))
doors, actors, seats = R._things(G, pr, room)
check('three spots in the barracks', len(got) == 3 and not why, why)
check('each clear of doors, seats and each other', all(min(math.dist(p[:3], d[:3]) for d in doors) >= R.DOOR_CLEAR and
      min((math.dist(p[:3], s[:3]) for s in seats), default=1e9) >= R.SEAT_CLEAR for _k, p, _n in got) and
      all(math.dist(a[1][:3], b[1][:3]) >= R.APART for a in got for b in got if a is not b))
check('the doorman stands nearest a door', min(math.dist(got[1][1][:3], d[:3]) for d in doors) <= min(math.dist(got[0][1][:3], d[:3]) for d in doors))
busy = key('GSProspectorSaloonInterior', 'CELL')
got2, why2 = R.inside_spots(G, pr, busy, ('crazed',))
check('a hostile robot is refused where people stand', got2 == [] and 'stand there' in why2, why2)

# ---- the ops, with a plan given (plan() needs Waikiki); another empty game room stands in for the bank ----
bank = key('SharecropperBarracks01', 'CELL')
P = {'spots': [{'kind': k, 'cell': room, 'place': 'x', 'full': 'x', 'p': p, 'near': {}} for k, p, _n in got] +
     [{'kind': 'bank_guard', 'cell': bank, 'place': R.BANK, 'full': 'bank', 'p': p, 'near': {}}
      for _k, p, _n in R.inside_spots(G, pr, bank, ('bank_guard', 'bank_guard'))[0]],
     'skipped': []}
check('the plan has two bank guards', sum(s['kind'] == 'bank_guard' for s in P['spots']) == 2)
undo0 = len(pr.undo_stack)
ops, rep = R.ops(G, pr, P)
pr.apply(R.LABEL, ops)
check('one Undo', len(pr.undo_stack) == undo0 + 1)
check('records for each kind placed', set(rep['records']) == {'butler', 'doorman', 'housekeeper', 'bank_guard'} and rep['placed'] == 5, rep)
check('the terminal stood in the bank, average lock', isinstance(rep.get('terminal'), dict) and rep['terminal']['science'] == 50, rep.get('terminal'))
try:
    R.ops(G, pr, P)
    check('a second go refused', False)
except ValueError:
    check('a second go refused', True)

os.makedirs(project.BUILD_DIR, exist_ok=True)
out = os.path.join(project.BUILD_DIR, 'Robot Test.esp')
espwrite.write(G, pr, out)
g = gamedata.GameData(plugins=list(gamedata.OFFICIAL) + [out])
i = len(g.plugins) - 1
mine = {tes4.zstr(g.fields(f).get('EDID', b'')): f for f, (n, r) in g.forms.items() if n == i}
named = {}
count = 0
for c, refs in g.cell_refs.items():
    for f, (n, r) in refs.items():
        if n == i and r.tag == 'ACRE':
            count += 1
            sd = dict(tes4.iter_subrecords(g.plugins[n].data(r)))
            if 'EDID' in sd:
                named[tes4.zstr(sd['EDID'])] = (r.formid, bool(r.flags & tes4.PERSISTENT))
check('five robots placed in the plugin', count == 5, count)
check('the bank guards named and persistent', set(named) == set(R.GUARD_REFS) and all(p for _f, p in named.values()), named)
t = dict(tes4.iter_subrecords(g.plugins[i].data(g.forms[mine['FOLabBankSecurityTerminal']][1])))
sd = list(tes4.iter_subrecords(g.plugins[i].data(g.forms[mine['FOLabBankSecurityTerminal']][1])))
src = b''.join(v for k, v in sd if k == 'SCTX')
scro = [struct.unpack('<I', v)[0] for k, v in sd if k == 'SCRO']
check('the terminal shuts both guards down, naming their refs', src.count(b'KillActor') == 2 and sorted(scro) == sorted(f for f, _p in named.values()))
s = health.check_file(g, out)['summary']
check('the plugin passes health with no errors', s.get('error', 0) == 0, s)

fix, said = R.bank_fix_ops(G, pr)
check('the bank fix leaves a KillActor terminal alone', fix == [] and said == 'already KillActor', said)
