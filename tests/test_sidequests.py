"""Waikiki's first side quests (sidequests.py) made in a small mod of its own: a stand-in doctor placed, stand-ins for the
armour and dao the gate guard wears, then each quest's ops as one Undo, written and read back as the game reads them: the
quest's stages and objectives aimed at the right refs, the doctor's ref given its editor ID, the trunk holding the supplies,
the guard carrying his gear, the script naming what it uses, two silent lines with no scripts. (Where things go in Waikiki
was rehearsed on a copy of it.) Nothing goes near the real game."""
import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import api_scripts  # noqa: E402
import browse  # noqa: E402
import espwrite  # noqa: E402
import gamedata  # noqa: E402
import health  # noqa: E402
import project  # noqa: E402
import recordio  # noqa: E402
import server  # noqa: E402
import sidequests as sq  # noqa: E402
import tes4  # noqa: E402
from castawayquest import _game_form  # noqa: E402
from kuliouquest import _person  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


G = server.GD = gamedata.GameData()
server.BR = browse.Browse(G, lambda: server.PR)
pr = server.PR = project.Project.create('Side Quests')

# ---- the stand-ins: the doctor (an NPC_ of the mod's own, placed), the gate guard's armour and dao ----
world = next(w for c, w in G.ext_cells.items() if G.edid(w) == 'WastelandNV')
grid = G.grid(world)
cell = lambda x, y: G.key(grid[(int(x // 4096), int(y // 4096))])
x0, y0 = -18 * 4096.0 + 2000, 2000.0
armour = recordio.load(G, _game_form(G, 'ArmorLegate', 'ARMO'))
recordio.set_field(armour, 'EDID', 'FOLabHuangLamellar', label='Editor ID')
dao = recordio.load(G, _game_form(G, 'WeapNVMachete', 'WEAP'))
recordio.set_field(dao, 'EDID', 'FOLabWeapDao', label='Editor ID')
for r in (armour, dao):
    r['src'] = ''
doctor = _person(G, pr, sq.DOCTOR['giver_npc'], 'Doctor', 'NVProspectorFemale')
made = server.edit('stand-ins', [{'op': 'record_new', 'record': armour}, {'op': 'record_new', 'record': dao},
                                 {'op': 'record_new', 'record': doctor}])['made']
server.edit('the doctor', [{'op': 'add', 'cell': cell(x0, y0), 'base': made[2], 'p': [x0, y0, 9000.0, 0, 0, 0], 's': 1.0, 'extra': {'persistent': True}}])
doc_cell, doc_ref = cell(x0, y0), next(k for k, r in pr.cells[cell(x0, y0)]['refs'].items() if r['base'] == made[2])
before = (len(pr.records), sum(len(c.get('refs', {})) for c in pr.cells.values()), len(pr.undo_stack))

# ---- the two quests, with spots given (spots() needs Waikiki) ----
where = {'doctor': {'giver': (doc_cell, doc_ref), 'box': (cell(x0 + 900, y0), [x0 + 900, y0, 9000.0, 0, 0, 0])},
         'gate': {'guard': (cell(x0, y0 + 900), [x0, y0 + 900, 9000.0, 0, 0, 0]), 'goal': (cell(x0 + 1500, y0 + 1500), [x0 + 1500, y0 + 1500, 9000.0, 0, 0, 0])}}
reps = {}
for name in ('doctor', 'gate'):
    spec = sq.SPECS[name]
    o, rep = sq.ops(G, pr, spec, where[name])
    n0 = len(pr.undo_stack)
    got = server.edit(name, o)['made']
    check('%s: one Undo step, keys as reserved' % name, len(pr.undo_stack) == n0 + 1 and
          got[:len(sq.key_order(spec))] == [rep['keys'][k] for k in sq.key_order(spec)])
    src = api_scripts.source_of(pr.records[rep['keys']['script']]).replace('\r', '')
    check('%s: the script starts both talks, rewards and completes' % name, src.count('StartConversation') == 2 and
          'CompleteQuest ' + spec['quest'] in src and all('AddItem %s %d' % (e, n) in src for e, n in rep['reward']))
    reps[name] = rep
check('the doctor\'s ref is given its editor ID', pr.cells[doc_cell]['refs'][doc_ref].get('edid') == sq.DOCTOR['giver_ref'])
try:
    sq.ops(G, pr, sq.DOCTOR, where['doctor'])
    check('a second build is refused', False)
except ValueError:
    check('a second build is refused', True)

# ---- written and read back ----
os.makedirs(project.BUILD_DIR, exist_ok=True)
out = os.path.join(project.BUILD_DIR, 'Side Quests.esp')
espwrite.write(G, pr, out)
g = gamedata.GameData(plugins=list(gamedata.OFFICIAL) + [out])
i = len(g.plugins) - 1
mine = {tes4.zstr(g.fields(f).get('EDID', b'')): f for f, (n, r) in g.forms.items() if n == i}
refs = {}
for cf, rs in g.cell_refs.items():
    for rf, e in rs.items():
        if rf >> 24 == i:
            refs[tes4.zstr(g.ref_fields(e)[1].get('EDID', b''))] = (rf, e)
for name, want in (('doctor', [sq.DOCTOR['box_ref'], sq.DOCTOR['giver_ref']]), ('gate', [sq.GATE['goal'][1], sq.GATE['giver_ref']])):
    spec = sq.SPECS[name]
    subs = list(tes4.iter_subrecords(g.plugins[i].data(g.forms[mine[spec['quest']]][1])))
    check('%s: three stages, the last completing it' % name, [d[0] for t, d in subs if t == 'QSDT'] == [0, 0, 1])
    targets = [g.to_global(i, struct.unpack('<I', d[:4])[0]) for t, d in subs if t == 'QSTA']
    check('%s: objectives aimed at the right refs' % name, all(n in refs for n in want) and targets == [refs[n][0] for n in want],
          [n for n in want if n not in refs])
    scro = {g.to_global(i, struct.unpack('<I', d)[0]) for t, d in tes4.iter_subrecords(g.plugins[i].data(g.forms[mine[spec['script']]][1])) if t == 'SCRO'}
    check('%s: the script names the giver' % name, refs[spec['giver_ref']][0] in scro)
trunk = g.fields(mine[sq.DOCTOR['box'][0]])
check('the trunk holds the medical supplies', g.to_global(i, struct.unpack('<I', trunk['CNTO'][:4])[0]) == mine[sq.DOCTOR['item'][0]])
guard = [g.to_global(i, struct.unpack('<I', d[:4])[0]) for t, d in tes4.iter_subrecords(g.plugins[i].data(g.forms[mine[sq.GATE['guard'][0]]][1])) if t == 'CNTO']
check('the gate guard carries the lamellar and the dao', {mine['FOLabHuangLamellar'], mine['FOLabWeapDao']} <= set(guard))
infos = [f for f, (n, r) in g.forms.items() if n == i and r.tag == 'INFO']
silent = all(struct.unpack('<I', d[16:20])[0] == 0 for f in infos for t, d in tes4.iter_subrecords(g.plugins[i].data(g.forms[f][1])) if t == 'TRDT')
scripts = sum(1 for f in infos for t, d in tes4.iter_subrecords(g.plugins[i].data(g.forms[f][1])) if t == 'SCDA' and d)
check('four silent lines, no scripts on them', len(infos) == 4 and silent and scripts == 0, (len(infos), scripts))
summary = health.check_file(G, out)['summary']
check('the plugin passes the health check', summary['error'] == 0, summary)

# ---- Undo ----
pr.undo()
pr.undo()
check('two Undos take both away', (len(pr.records), sum(len(c.get('refs', {})) for c in pr.cells.values())) == before[:2] and
      not pr.cells[doc_cell]['refs'][doc_ref].get('edid'))
