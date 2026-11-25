"""Terminals in the court district (officeterminals.py) in a small mod of its own: a game room standing in for an office with a
locked wall safe and a locked drug locker, then the terminals as one Undo from a plan, written and read back: the
locked things named and persistent, the terminal at the lock's difficulty, its items' scripts unlocking them, standing
clear of doors and seats. Nothing near the real game."""
import math
import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import browse  # noqa: E402
import espwrite  # noqa: E402
import gamedata  # noqa: E402
import health  # noqa: E402
import officeterminals as OT  # noqa: E402
import project  # noqa: E402
import robots  # noqa: E402
import server  # noqa: E402
import tes4  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


G = server.GD = gamedata.GameData()
server.BR = browse.Browse(G, lambda: server.PR)
pr = server.PR = project.Project.create('Office Test')
key = lambda e, tag: G.key(next(f for f, (i, r) in G.forms.items() if r.tag == tag and G.edid(f) == e))
place = key('CrimsonCaravanBarracks01', 'CELL')      # (a game room with its navmesh stands in for an office)
check('kinds by name', OT.kind_of('Kuakini Medical Center') == 'clinic' and OT.kind_of('Offices') == 'office'
      and OT.kind_of('Center for Security Studies') == 'security')
made = server.edit('locked things', [
    {'op': 'add', 'cell': place, 'base': key('LootSafeWallEmpty', 'CONT'), 'p': [1900.0, 2400.0, 8137.0, 0, 0, 0], 's': 1.0,
     'extra': {'props': {'lock': {'level': 75}}}},
    {'op': 'add', 'cell': place, 'base': key('Footlocker01Drugs', 'CONT'), 'p': [2200.0, 2400.0, 8137.0, 0, 0, 0], 's': 1.0,
     'extra': {'props': {'lock': {'level': 50}}}}])['made']
spot = OT._spot(G, pr, place, [1900.0, 2400.0, 8137.0])
check('a spot near the safe, on the navmesh', spot is not None and OT.NEAR[0] <= math.dist(spot[:2], (1900, 2400)) <= OT.NEAR[1], spot)
row = {'cell': place, 'place': 'FOLabWaikikiOffices99', 'full': 'Medical Arts Building', 'kind': 'clinic',
       'targets': [(made[0], 'LootSafeWallEmpty', 75), (made[1], 'Footlocker01Drugs', 50)], 'spot': spot, 'lock': 'average', 'way_in': (0, 0)}
undo0 = len(pr.undo_stack)
o, rep = OT.ops(G, pr, ([row], []))
pr.apply(OT.LABEL, o)
check('one Undo, one terminal, Science 50', len(pr.undo_stack) == undo0 + 1 and len(rep['terminals']) == 1 and rep['terminals'][0]['science'] == 50, rep)
check('the locked things named and persistent', [pr.cells[place]['refs'][k].get('edid') for k in made] == ['FOLabTermLockOffices991REF', 'FOLabTermLockOffices992REF']
      and all(pr.cells[place]['refs'][k].get('persistent') for k in made))
try:
    OT.ops(G, pr, ([row], []))
    check('a second go refused', False)
except ValueError:
    check('a second go refused', True)
os.makedirs(project.BUILD_DIR, exist_ok=True)
out = os.path.join(project.BUILD_DIR, 'Office Test.esp')
espwrite.write(G, pr, out)
g = gamedata.GameData(plugins=list(gamedata.OFFICIAL) + [out])
i = len(g.plugins) - 1
mine = {tes4.zstr(g.fields(f).get('EDID', b'')): f for f, (n, r) in g.forms.items() if n == i}
sd = list(tes4.iter_subrecords(g.plugins[i].data(g.forms[mine['FOLabTermOffices99']][1])))
d = dict(sd)
refs = {}
for f, (n, r) in g.cell_refs[g.from_key(place)].items():
    e = tes4.zstr(dict(tes4.iter_subrecords(g.plugins[n].data(r))).get('EDID', b''))
    if e and n == i:
        refs[e] = r.formid
src = [v for k, v in sd if k == 'SCTX']
scro = sorted(struct.unpack('<I', v)[0] for k, v in sd if k == 'SCRO')
check('the terminal: average, locked, three items', d['DNAM'][:2] == bytes([2, 0]) and sum(1 for k, _ in sd if k == 'ITXT') == 3)
check('its scripts unlock the safe and the locker by name', src == [b'FOLabTermLockOffices991REF.Unlock', b'FOLabTermLockOffices992REF.Unlock']
      and scro == sorted(refs[e] for e in ('FOLabTermLockOffices991REF', 'FOLabTermLockOffices992REF')), src)
check('the clinic\'s welcome', b'PATIENT RECORDS' in d['DESC'])
s = health.check_file(g, out)['summary']
check('the plugin passes health with no errors', s.get('error', 0) == 0, s)
