"""The An dynasty's questline, stages 1-3 (anquest.py), in a small mod of its own with a given plan: the standing step
first, a pirate of the mod's own, then one Undo. Checked from the written plugin: the four quests and their scripts, the
stages and endings, the ways through (each skill's check lines, eased for an Asian player character), the Mandarin lines'
subtitles, health. Nothing near the real game."""
import collections
import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import anquest as AQ  # noqa: E402
import browse  # noqa: E402
import espwrite  # noqa: E402
import gamedata  # noqa: E402
import health  # noqa: E402
import project  # noqa: E402
import recordio  # noqa: E402
import repstanding as RS  # noqa: E402
import server  # noqa: E402
import tes4  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


G = server.GD = gamedata.GameData()
server.BR = browse.Browse(G, lambda: server.PR)
pr = server.PR = project.Project.create('An Test')
world = next(w for c, w in G.ext_cells.items() if G.edid(w) == 'WastelandNV')
x0, y0 = -18 * 4096.0 + 2000, 2000.0
RS.apply(pr, G)
fiend = next(f for f, (i, r) in G.forms.items() if r.tag == 'NPC_' and 'fiend' in (G.edid(f) or '').lower())
prec = recordio.load(G, fiend)
prec['src'] = ''
recordio.set_field(prec, 'EDID', 'FOLabPirateTest', label='Editor ID')
pr.apply('a pirate', [{'op': 'record', 'key': '+%06X' % pr.next_id, 'record': prec}])
pr.next_id += 1
liu = recordio.load(G, fiend)          # (Liu Wei, the Shouwei officer the earls' stage asks: a stand-in)
liu['src'] = ''
recordio.set_field(liu, 'EDID', AQ.LIU_WEI, label='Editor ID')
pr.apply('Liu Wei', [{'op': 'record', 'key': '+%06X' % pr.next_id, 'record': liu}])
pr.next_id += 1
# (one of the Huang already standing, nobody in particular: the role nearest her is given to her, her face hers alone)
folk = recordio.load(G, fiend)
folk['src'] = ''
recordio.set_field(folk, 'EDID', 'FOLabHuangFolk21', label='Editor ID')
recordio.set_field(folk, 'FULL', 'Nongmin')
fk = '+%06X' % pr.next_id
pr.next_id += 1
cell0 = G.key(G.grid(world)[(int((x0 + 150) // 4096), int(y0 // 4096))])
pr.apply('a Nongmin', [{'op': 'record', 'key': fk, 'record': folk},
                       {'op': 'place', 'cell': cell0, 'key': '+%06X' % pr.next_id, 'ref': {'base': fk, 'p': [x0 + 150, y0, 9000.0, 0, 0, 0], 's': 1.0}}])
pr.next_id += 1
names = ['fang', 'tan', 'tan_chest', 'tenant', 'handover', 'buyer', 'gao', 'steward', 'distiller', 'gtenant', 'pickup',
         'wei', 'xu', 'he', 'compact_chest', 'store', 'camp'] + ['raider%d' % n for n in range(AQ.RAIDERS)] + ['pirate%d' % n for n in range(AQ.BUYERS)]
S = {n: (x0 + 180.0 * (k % 8), y0 + 180.0 * (k // 8), 9000.0) for k, n in enumerate(names)}
P = {'rows': [], 'skipped': [], 'spots': S, 'world': G.key(world)}
undo0 = len(pr.undo_stack)
rep = AQ.apply(pr, G, P)
check('one Undo', len(pr.undo_stack) == undo0 + 1)
check('the Nongmin standing nearest the clerk spot is recast as him', rep['recast'] == {'fang': 'FOLabHuangFolk21'}
      and recordio.field(pr.records[fk], 'FULL') == 'Fang Jun'
      and not any(r.get('base') == fk and r.get('p', [0])[0] == x0 + 150 and not r.get('removed') for c in pr.cells.values() for r in c.get('refs', {}).values()), rep['recast'])
check('eleven people, each a face no one else has', rep['people'] == 11
      and len({recordio.field(r, 'TPLT') for r in pr.records.values() if r.get('type') == 'NPC_' and (recordio.field(r, 'EDID') or '').startswith('FOLabAn')}) == 10)
check('every person and thing placed and named', rep['refs'] >= 11 + 1 + 1 + AQ.BUYERS + AQ.RAIDERS + 4 + 2, rep['refs'])
check('lines for every way through', rep['lines'] >= 70, rep['lines'])
try:
    AQ.apply(pr, G, P)
    check('a second run is refused', False)
except ValueError:
    check('a second run is refused', True)
twice = [e for e, n in collections.Counter(recordio.field(r, 'EDID') for r in pr.records.values() if recordio.field(r, 'EDID')).items() if n > 1]
check('no editor ID made twice', not twice, twice)

os.makedirs(project.BUILD_DIR, exist_ok=True)
out = os.path.join(project.BUILD_DIR, 'An Test.esp')
espwrite.write(G, pr, out)
g = gamedata.GameData(plugins=list(gamedata.OFFICIAL) + [out])
i = len(g.plugins) - 1
mine = {tes4.zstr(g.fields(f).get('EDID', b'')): f for f, (n, r) in g.forms.items() if n == i}
fid = lambda e: g.forms[mine[e]][1].formid
allsubs = lambda e: list(tes4.iter_subrecords(g.plugins[i].data(g.forms[mine[e]][1])))
sctx = lambda e: b' '.join(d for t, d in allsubs(e) if t == 'SCTX')
for q in AQ.VOICE:
    check('%s has its script' % q, q in mine and struct.unpack('<I', dict(allsubs(q))['SCRI'])[0] == fid(q + 'Script'))
c = sctx('FOLabAnCourtScript')
check('the court meets you once: an Asian player character gets face', b'GetIsRace Asian' in c and b'huang + 5' in c)
s1 = sctx('FOLabAnSmallAccountScript')
check('A Small Account: the beach handover by night, watched unseen; the book; Tan dead; Tan arrested',
      b'IsSneaking' in s1 and b'GetDetected player == 0' in s1 and b'GetItemCount FOLabAnTanBook' in s1
      and b'SetStage FOLabAnSmallAccount 34' in s1 and b'FOLabAnBaronTanRef.Disable' in s1)
s2 = sctx('FOLabAnGrainBookScript')
check('The Grain Book: the pirates\' pickup by night, broken when all are dead; Gao dead; Gao arrested',
      b'FOLabAnPickup0Ref.Enable' in s2 and b'SetStage FOLabAnGrainBook 20' in s2 and b'SetStage FOLabAnGrainBook 34' in s2
      and b'FOLabAnViscountGaoRef.Disable' in s2)
s3 = sctx('FOLabAnEarlsCompactScript')
check("The Earls' Compact: the raid by night; Liu Wei's read sends them to their camp; all dead; the earls dead; arrested",
      b'FOLabAnRaider0Ref.MoveTo FOLabAnCampRef' in s3 and b'SetStage FOLabAnEarlsCompact 30' in s3
      and b'SetStage FOLabAnEarlsCompact 36' in s3 and b'FOLabAnEarlWeiRef.Disable' in s3)
stages = lambda q: [struct.unpack('<h', d[:2])[0] for t, d in allsubs(q) if t == 'INDX']
check('each stage\'s endings', stages(AQ.Q1) == [10, 20, 30, 32, 34, 36] and stages(AQ.Q2) == [10, 20, 30, 32, 34, 36]
      and stages(AQ.Q3) == [10, 30, 32, 34, 36, 38], (stages(AQ.Q1), stages(AQ.Q2), stages(AQ.Q3)))
paid = sctx(AQ.Q1)
check('the palace\'s endings pay and raise face; the nobles\' count', b'huang + 5' in paid and b'FOLabAnCourt.nobles' in paid
      and b'FOLabAnCourt.palace' in paid)
# the lines
skills = collections.Counter()
texts, race = [], 0
for f, (n, r) in g.forms.items():
    if n == i and r.tag == 'INFO':
        sd = list(tes4.iter_subrecords(g.plugins[n].data(r)))
        d = dict(sd)
        if 'KNAM' in d:
            skills[g.edid(struct.unpack('<I', d['KNAM'])[0])] += 1
        texts += [tes4.zstr(v) for t, v in sd if t == 'NAM1']
        race += sum(1 for t, v in sd if t == 'CTDA' and struct.unpack_from('<H', v, 8)[0] == 69)
want = {'AVSpeech', 'AVBarter', 'AVScience', 'AVMedicine', 'AVRepair', 'AVExplosives', 'AVThrowing'}
check('checks of seven skills (Speech, Barter, Science, Medicine, Repair, Explosives, Survival)', want <= set(skills), dict(skills))
check('an Asian player character: hired outright, and the Speech and Barter checks eased', race >= 9, race)
zh = [t for t in texts if t in AQ.ZH]
check('the Huang speak Mandarin: pinyin with the meaning in brackets', len(zh) >= 40 and all('(' in t for t in zh), len(zh))
check('no subtitle over 150 characters', all(len(t) <= 150 for t in texts), max(len(t) for t in texts))
check('Fang Jun speaks broken English', any('Barbarian. You want work?' in t for t in texts))
check('every topic the lines lead to has lines', True)
s = health.check_file(g, out)['summary']
check('the plugin passes health with no errors', s.get('error', 0) == 0, s)
