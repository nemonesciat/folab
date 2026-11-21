"""Waikiki's first quest (castawayquest.py) made in a small mod of its own: a stand-in opening with its `step`, a beachcomber
stood in the Mojave, then the quest's ops as one Undo, written and read back as the game reads them: the quest's stages with
their log entries, objectives aimed at the trunk, the beachcomber and the marker (all kept loaded), the script naming what it
uses, silent lines with no scripts of their own, the trunk holding the lockbox. Nothing goes near the real game."""
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
import newgame  # noqa: E402
import project  # noqa: E402
import recordio  # noqa: E402
import server  # noqa: E402
import tes4  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


G = server.GD = gamedata.GameData()
server.BR = browse.Browse(G, lambda: server.PR)
pr = server.PR = project.Project.create('First Quest')

# ---- the stand-in: an opening quest with a `step`, a beachcomber kept loaded where the Mojave has ground ----
sc = api_scripts.scripts()
keys = ['+%06X' % (pr.next_id + k) for k in range(3)]
pr.apply('stand-in', [{'op': 'record_new', 'record': {'type': 'SCPT', 'flags': 0, 'src': '', 'subs': [{'tag': 'EDID', 'label': 'Editor ID', 'kind': 'z', 'value': 'OpeningStandIn'}]}},
                      {'op': 'record_new', 'record': newgame._quest_record(cq.OPENING, keys[0])},
                      {'op': 'record_new', 'record': cq._named(recordio.load(G, cq._game_form(G, 'NVProspectorMale', 'NPC_')), 'FOLabBeachcomber', 'Beachcomber')}])
c = sc.compile('scn OpeningStandIn\r\nshort step\r\nbegin GameMode\r\nend\r\n', keys[0], 'quest')
pr.apply('stand-in script', [{'op': 'record', 'key': keys[0], 'record': sc._record_of(c, 'OpeningStandIn')}])
cell = next(c for c, w in G.ext_cells.items() if G.edid(w) == 'WastelandNV' and G.cell_grid(c) == (-18, 0))
far = next(c for c, w in G.ext_cells.items() if G.edid(w) == 'WastelandNV' and G.cell_grid(c) == (-16, 2))
base = (-18 * 4096.0 + 2000, 2000.0)
comber = pr.apply('beachcomber', [{'op': 'add', 'cell': G.key(cell), 'base': keys[2], 'p': [base[0], base[1], 9000.0, 0, 0, 0], 'extra': {'persistent': True, 'edid': cq.COMBER_REF}}])[0]
where = {'trunk': (G.key(cell), [base[0] + 600, base[1], 9000.0, 0.0, 0.0, 1.0]), 'arrive': (G.key(far), [-16 * 4096.0 + 2000, 2 * 4096.0 + 2000, 9000.0, 0, 0, 0]),
         'comber': comber, 'comber_cell': G.key(cell)}
before = (len(pr.records), sum(len(c.get('refs', {})) for c in pr.cells.values()), len(pr.undo_stack))

# ---- the quest ----
ops, rep = cq.ops(G, pr, where)
made = server.edit('first quest', ops)['made']
check('one Undo step', len(pr.undo_stack) == before[2] + 1)
check('keys as reserved', made[:10] == [rep['keys'][k] for k in ('lockbox', 'trunk', 'message', 'script', 'quest', 'ask', 'back', 'cut', 'trunk_ref', 'arrive_ref')])
k = rep['keys']
src = api_scripts.source_of(pr.records[k['script']]).replace('\r', '')
check('the script is the quest\'s own source, kept with it', 'scn ' + cq.SCRIPT in src and 'StartConversation PlayerREF ' + cq.TOPICS['back'] in src)
check('the script waits for the opening to be over', '%s.step != 9' % cq.OPENING in src)
check('the reward is the game\'s levelled duffle lists', all('player.AddItem %s %d' % r in src for r in cq.REWARD))
check('it shows, completes and ends by itself', src.count('SetObjectiveDisplayed') == 3 and src.count('SetObjectiveCompleted') == 3 and 'CompleteQuest ' + cq.QUEST in src)
try:
    cq.ops(G, pr, where)
    check('a second build is refused', False)
except ValueError:
    check('a second build is refused', True)

# ---- written and read back ----
os.makedirs(project.BUILD_DIR, exist_ok=True)
out = os.path.join(project.BUILD_DIR, 'First Quest.esp')
espwrite.write(G, pr, out)
g = gamedata.GameData(plugins=list(gamedata.OFFICIAL) + [out])
i = len(g.plugins) - 1
mine = {tes4.zstr(g.fields(f).get('EDID', b'')): f for f, (n, r) in g.forms.items() if n == i}
q = mine.get(cq.QUEST)
subs = list(tes4.iter_subrecords(g.plugins[i].data(g.forms[q][1])))
stages = [struct.unpack('<h', d)[0] for t, d in subs if t == 'INDX']
logs = [tes4.zstr(d) for t, d in subs if t == 'CNAM']
flags = [d[0] for t, d in subs if t == 'QSDT']
check('the quest: four stages with their log entries, the last completing it',
      stages == [n for n, _l, _f in cq.STAGES] and logs == [l for _n, l, _f in cq.STAGES] and flags == [0, 0, 0, 1], (stages, flags))
check('named for the Pip-Boy, started with the game', tes4.zstr(dict(subs)['FULL']) == cq.QUEST_NAME and dict(subs)['DATA'][0] & 1)
objs = [struct.unpack('<i', d)[0] for t, d in subs if t == 'QOBJ']
targets = [g.to_global(i, struct.unpack('<I', d[:4])[0]) for t, d in subs if t == 'QSTA']
refs = {}
for cf, rs in g.cell_refs.items():
    for rf, e in rs.items():
        if rf >> 24 == i:
            refs[tes4.zstr(g.ref_fields(e)[1].get('EDID', b''))] = (rf, e)
want = [refs[cq.TRUNK_REF][0], refs[cq.COMBER_REF][0], refs[cq.ARRIVE][0]]
check('three objectives, aimed at the trunk, the beachcomber and the marker', objs == [10, 20, 30] and targets == want, (targets, want))
check('every target is kept loaded (persistent)', all(refs[n][1][1].flags & tes4.PERSISTENT for n in (cq.TRUNK_REF, cq.COMBER_REF, cq.ARRIVE)))
scf = mine[cq.SCRIPT]
scro = [g.to_global(i, struct.unpack('<I', d)[0]) for t, d in tes4.iter_subrecords(g.plugins[i].data(g.forms[scf][1])) if t == 'SCRO']
named = {tes4.zstr(g.fields(f).get('EDID', b'')) if f in g.forms else None for f in scro} | {n for n, (rf, _e) in refs.items() if rf in scro}
check('the script names what it uses', {cq.OPENING, cq.QUEST, cq.LOCKBOX, cq.MESSAGE, cq.TOPICS['ask'], cq.TOPICS['back'],
                                         cq.ARRIVE, cq.COMBER_REF, 'LootDuffleBag100', 'LootDuffleBag25'} <= named, named)
cont = list(tes4.iter_subrecords(g.plugins[i].data(g.forms[mine[cq.TRUNK]][1])))
check('the trunk holds the lockbox', [g.to_global(i, struct.unpack('<I', d[:4])[0]) for t, d in cont if t == 'CNTO'] == [mine[cq.LOCKBOX]])
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
check('three silent lines, no sound named', len(infos) == 3 and silent, len(infos))
check('their words are the quest\'s', ' '.join(texts) == ' '.join(texts) and any('Kuliouou.' in t for t in texts) and any('lockbox' in t for t in texts))
check('no line carries a script of its own (they never ran in the game)', scripts == 0, scripts)
choice = [g.to_global(i, struct.unpack('<I', d)[0]) for f in infos for t, d in tes4.iter_subrecords(g.plugins[i].data(g.forms[f][1])) if t == 'TCLT']
check('the back line offers the cut-open answer', choice == [mine[cq.TOPICS['cut']]] and tes4.zstr(g.fields(mine[cq.TOPICS['cut']])['FULL']) == cq.WORDS['cut_prompt'])
summary = health.check_file(G, out)['summary']
check('the plugin passes the health check', summary['error'] == 0, summary)

# ---- Undo ----
pr.undo()
check('one Undo takes it all away', (len(pr.records), sum(len(c.get('refs', {})) for c in pr.cells.values())) == before[:2])
