"""Waikiki's second quest (kuliouquest.py) made in a small mod of its own: a stand-in for the first quest, a camp marker named
as Kuliouou's with game road pieces near it, then the quest's ops as one Undo, written and read back as the game reads them:
seven people of the mod's own placed off and kept loaded, two travel packages to the quest's markers, the script naming what
it uses, stages with log entries, objectives aimed at the father and the woman, four silent lines with no scripts, the woman's
one answer. Nothing goes near the real game."""
import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import api_scripts  # noqa: E402
import browse  # noqa: E402
import castawayquest as cq  # noqa: E402
import espwrite  # noqa: E402
import gamedata  # noqa: E402
import health  # noqa: E402
import kuliouquest as kq  # noqa: E402
import newgame  # noqa: E402
import project  # noqa: E402
import server  # noqa: E402
import tes4  # noqa: E402
import worldrec  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


G = server.GD = gamedata.GameData()
server.BR = browse.Browse(G, lambda: server.PR)
pr = server.PR = project.Project.create('Second Quest')

# ---- the stand-in: the first quest (a stage 30 to wait for), Kuliouou's marker, road pieces round it ----
sc = api_scripts.scripts()
keys = ['+%06X' % (pr.next_id + k) for k in range(2)]
pr.apply('stand-in', [{'op': 'record_new', 'record': {'type': 'SCPT', 'flags': 0, 'src': '', 'subs': [{'tag': 'EDID', 'label': 'Editor ID', 'kind': 'z', 'value': 'FirstStandIn'}]}},
                      {'op': 'record_new', 'record': newgame._quest_record(kq.BEFORE, keys[0])}])
c = sc.compile('scn FirstStandIn\r\nshort state\r\nbegin GameMode\r\nend\r\n', keys[0], 'quest')
pr.apply('stand-in script', [{'op': 'record', 'key': keys[0], 'record': sc._record_of(c, 'FirstStandIn')}])
world = next(w for c, w in G.ext_cells.items() if G.edid(w) == 'WastelandNV')
cx, cy = -18 * 4096.0 + 2000, 2000.0
road = G.key(cq._game_form(G, 'WastelandRoadStraightLong', 'STAT'))
cell = next(c for c, w in G.ext_cells.items() if w == world and G.cell_grid(c) == (-18, 0))
stand = [worldrec.marker_op(G, world, [cx, cy, 9000.0], kq.KULIOUOU, 11)]
stand += [{'op': 'add', 'cell': G.key(cell), 'base': road, 'p': [cx - 1200, cy + d, 9000.0, 0, 0, 0], 's': 1.0} for d in (-1000, 0, 1000, 1900)]
pr.apply('camp', stand)
before = (len(pr.records), sum(len(c.get('refs', {})) for c in pr.cells.values()), len(pr.undo_stack))

# ---- the quest ----
where = kq.spots(G, pr)
check('the catchers stand on a road piece, the woman by the camp', abs(where['catcher'][1][0] - (cx - 1200)) < 1 and
      abs(where['woman'][1][0] - cx) < 200 and abs(where['woman'][1][1] - cy) < 200, (where['catcher'], where['woman']))
ops, rep = kq.ops(G, pr, where)
made = server.edit('second quest', ops)['made']
check('one Undo step', len(pr.undo_stack) == before[2] + 1)
check('keys as reserved', made[:len(kq.KEY_ORDER)] == [rep['keys'][k] for k in kq.KEY_ORDER])
k = rep['keys']
src = api_scripts.source_of(pr.records[k['script']]).replace('\r', '')
check('the script waits for the first quest to send you here', 'GetStage %s < %d' % (kq.BEFORE, kq.BEFORE_STAGE) in src)
check('it switches the people on, starts all three talks and ends by itself',
      src.count('.Enable') == len(kq.PEOPLE) + 1 and src.count('StartConversation') == 3 and 'CompleteQuest ' + kq.QUEST in src)
check('those led away walk, then go', src.count('AddScriptPackage') == 5 and src.count('.Disable') == 5)
try:
    kq.ops(G, pr, where)
    check('a second build is refused', False)
except ValueError:
    check('a second build is refused', True)

# ---- written and read back ----
os.makedirs(project.BUILD_DIR, exist_ok=True)
out = os.path.join(project.BUILD_DIR, 'Second Quest.esp')
espwrite.write(G, pr, out)
g = gamedata.GameData(plugins=list(gamedata.OFFICIAL) + [out])
i = len(g.plugins) - 1
mine = {tes4.zstr(g.fields(f).get('EDID', b'')): f for f, (n, r) in g.forms.items() if n == i}
q = mine.get(kq.QUEST)
subs = list(tes4.iter_subrecords(g.plugins[i].data(g.forms[q][1])))
check('the quest: four stages with log entries, the last completing it',
      [struct.unpack('<h', d)[0] for t, d in subs if t == 'INDX'] == [n for n, _l, _f in kq.STAGES] and
      [d[0] for t, d in subs if t == 'QSDT'] == [0, 0, 0, 1])
check('named for the Pip-Boy, started with the game', tes4.zstr(dict(subs)['FULL']) == kq.QUEST_NAME and dict(subs)['DATA'][0] & 1)
refs = {}
for cf, rs in g.cell_refs.items():
    for rf, e in rs.items():
        if rf >> 24 == i:
            refs[tes4.zstr(g.ref_fields(e)[1].get('EDID', b''))] = (rf, e)
targets = [g.to_global(i, struct.unpack('<I', d[:4])[0]) for t, d in subs if t == 'QSTA']
check('two objectives, aimed at the father and the woman', [struct.unpack('<i', d)[0] for t, d in subs if t == 'QOBJ'] == [10, 20] and
      targets == [refs[kq.REF['father']][0], refs[kq.REF['woman']][0]])
people = [kq.REF[p] for p, _e, _n, _t in kq.PEOPLE] + [kq.BOAT_REF]
check('everyone and the boat are placed off and kept loaded',
      all(n in refs and refs[n][1][1].flags & tes4.PERSISTENT and refs[n][1][1].flags & 0x800 for n in people),
      [n for n in people if n not in refs])
check('the people are characters (ACHR) of the mod\'s own', all(refs[kq.REF[p]][1][1].tag == 'ACHR' for p, _e, _n, _t in kq.PEOPLE))
check('the two markers they walk to are on', all(n in refs and not refs[n][1][1].flags & 0x800 for n in (kq.TAKEN_TO, kq.BOAT_TO)))
for name, to in (('take', kq.TAKEN_TO), ('boat', kq.BOAT_TO)):
    pl = g.fields(mine[kq.PACKS[name]])['PLDT']
    check('the %s package travels to its marker' % name, struct.unpack('<i', pl[:4])[0] == 0 and
          g.to_global(i, struct.unpack('<I', pl[4:8])[0]) == refs[to][0] and 'CTDA' not in g.fields(mine[kq.PACKS[name]]))
scro = [g.to_global(i, struct.unpack('<I', d)[0]) for t, d in tes4.iter_subrecords(g.plugins[i].data(g.forms[mine[kq.SCRIPT]][1])) if t == 'SCRO']
named = {tes4.zstr(g.fields(f).get('EDID', b'')) if f in g.forms else None for f in scro} | {n for n, (rf, _e) in refs.items() if rf in scro}
want = {kq.BEFORE, kq.QUEST, kq.BOAT_REF, kq.TOPICS['catch'], kq.TOPICS['sale'], kq.TOPICS['pip']} | set(kq.PACKS.values()) | set(kq.REF.values())
check('the script names what it uses', want <= named, want - named)
infos = [f for f, (n, r) in g.forms.items() if n == i and r.tag == 'INFO']
silent, texts, scripts = True, [], 0
for f in infos:
    for t, d in tes4.iter_subrecords(g.plugins[i].data(g.forms[f][1])):
        if t == 'TRDT' and struct.unpack('<I', d[16:20])[0] != 0:
            silent = False
        elif t == 'NAM1':
            texts.append(tes4.zstr(d))
        elif t == 'SCDA' and d:
            scripts += 1
check('four silent lines', len(infos) == 4 and silent, len(infos))
check('their words are the quest\'s', any('Tribute day' in t for t in texts) and any('Waikiki' in t for t in texts))
check('no line carries a script of its own', scripts == 0, scripts)
choice = [g.to_global(i, struct.unpack('<I', d)[0]) for f in infos for t, d in tes4.iter_subrecords(g.plugins[i].data(g.forms[f][1])) if t == 'TCLT']
check('the woman offers the one answer', choice == [mine[kq.TOPICS['given']]] and
      tes4.zstr(g.fields(mine[kq.TOPICS['given']])['FULL']) == kq.WORDS['given_prompt'])
summary = health.check_file(G, out)['summary']
check('the plugin passes the health check', summary['error'] == 0, summary)

# ---- Undo ----
pr.undo()
check('one Undo takes it all away', (len(pr.records), sum(len(c.get('refs', {})) for c in pr.cells.values())) == before[:2])
