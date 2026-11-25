"""Maintenance panels for the crazed robots (robotpanels.py) in a small mod of its own: a crazed Mister Handy (robots.py's
record) placed in an empty game room, then the plan finds a panel spot on the navmesh near it, clear of doors and seats,
and one Undo names the robot, makes the messages, the panel and its script (Science 50 to shut it down by KillActor,
75 to reset it, RewardXP), and places the panel. Written and read back."""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import browse  # noqa: E402
import espwrite  # noqa: E402
import factionfolk as ff  # noqa: E402
import gamedata  # noqa: E402
import health  # noqa: E402
import project  # noqa: E402
import robotpanels as RP  # noqa: E402
import robots as R  # noqa: E402
import server  # noqa: E402
import tes4  # noqa: E402
from activity import _new_key  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


G = server.GD = gamedata.GameData()
server.BR = browse.Browse(G, lambda: server.PR)
pr = server.PR = project.Project.create('Panel Test')
server.edit('the court', [{'op': 'record_new', 'record': ff._faction(G, *ff.FACTIONS['court'])}])
check('nothing without the robots', not RP.plan(G, pr)[0])
key = lambda e, tag: G.key(next(f for f, (i, r) in G.forms.items() if r.tag == tag and G.edid(f) == e))
room = key('CrimsonCaravanBarracks01', 'CELL')
got, _why = R.inside_spots(G, pr, room, ('crazed',))
ck = _new_key(pr)
pr.apply('a crazed robot', [{'op': 'record', 'key': ck, 'record': R.robot_record(G, pr, 'crazed')},
                            {'op': 'place', 'cell': room, 'key': _new_key(pr),
                             'ref': {'base': ck, 'p': list(got[0][1][:3]) + [0.0, 0.0, got[0][1][3]], 's': 1.0}}])
rows, skipped = RP.plan(G, pr)
check('one panel planned', len(rows) == 1 and not skipped, skipped)
p, robot = rows[0]['panel'], rows[0]['robot_at']
doors, _actors, seats = R._things(G, pr, room)
check('near its robot', RP.NEAR[0] <= math.dist(p[:3], robot[:3]) <= RP.NEAR[1], rows[0]['apart'])
check('clear of doors and seats', min(math.dist(p[:3], d[:3]) for d in doors) >= R.DOOR_CLEAR
      and min((math.dist(p[:3], s[:3]) for s in seats), default=1e9) >= R.SEAT_CLEAR)
undo0 = len(pr.undo_stack)
ops, rep = RP.ops(G, pr, (rows, skipped))
pr.apply(RP.LABEL, ops)
check('one Undo', len(pr.undo_stack) == undo0 + 1)
refs = pr.cells[room]['refs']
named = [r for r in refs.values() if r.get('edid') == RP.ROBOT_REF % 1]
check('the robot named and persistent', len(named) == 1 and named[0].get('persistent'), named)
check('made again, it refuses', bool(RP.plan(G, pr)[1]) and not RP.plan(G, pr)[0])
os.makedirs(project.BUILD_DIR, exist_ok=True)
out = os.path.join(project.BUILD_DIR, 'Panel Test.esp')
espwrite.write(G, pr, out)
g = gamedata.GameData(plugins=list(gamedata.OFFICIAL) + [out])
i = len(g.plugins) - 1
mine = {tes4.zstr(g.fields(f).get('EDID', b'')): f for f, (n, r) in g.forms.items() if n == i}
src = dict(tes4.iter_subrecords(g.plugins[i].data(g.forms[mine[RP.SCRIPT % 1]][1])))['SCTX']
check('Science 50 shuts it down by KillActor', b'Science < 50' in src and b'FOLabCrazedBot1REF.KillActor' in src)
check('Science 75 resets it, for experience', b'Science >= 75' in src and b'RemoveFromFaction RobotFaction' in src
      and b'SetActorValue Aggression 0' in src and b'RewardXP 25' in src)
menu = list(tes4.iter_subrecords(g.plugins[i].data(g.forms[mine[RP.MENU]][1])))
check('the menu has three buttons', sum(1 for t, _v in menu if t == 'ITXT') == 3)
panel = dict(tes4.iter_subrecords(g.plugins[i].data(g.forms[mine[RP.PANEL % 1]][1])))
check('the panel is a control panel named Maintenance Panel', b'ControlPanel' in panel['MODL'] and panel['FULL'] == b'Maintenance Panel\x00')
placed = [r for c, rr in g.cell_refs.items() for f, (n, r) in rr.items() if n == i
          and tes4.zstr(dict(tes4.iter_subrecords(g.plugins[n].data(r))).get('EDID', b'')) == RP.ROBOT_REF % 1]
check('the robot persistent in the plugin', len(placed) == 1 and placed[0].flags & 0x400)
h = health.check_file(g, out)
bad = [(x['kind'], x['count']) for x in h['groups'] if x['sev'] == 'error']
check('the plugin passes health', not bad, bad)
