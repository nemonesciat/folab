"""The An questline's stage 4 (anpalace.py) in a small mod: the standing step, stages 1-3 (anquest), then stage 4 with
given spots, one Undo. Checked from the written plugin: the quest, its endings, the palace's faction on the Ship-King and
his guards, the betrayal turning them, the ways through (Speech, Barter, Science, Explosives checks; the receipt; the
seal), Mandarin subtitles, health. Nothing near the real game."""
import collections
import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import anpalace as AP  # noqa: E402
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
pr = server.PR = project.Project.create('An Four Test')
world = next(w for c, w in G.ext_cells.items() if G.edid(w) == 'WastelandNV')
x0, y0 = -18 * 4096.0 + 2000, 2000.0
RS.apply(pr, G)
fiend = next(f for f, (i, r) in G.forms.items() if r.tag == 'NPC_' and 'fiend' in (G.edid(f) or '').lower())


def npc(edid, full=None):
    rec = recordio.load(G, fiend)
    rec['src'] = ''
    recordio.set_field(rec, 'EDID', edid, label='Editor ID')
    if full:
        recordio.set_field(rec, 'FULL', full)
    k = '+%06X' % pr.next_id
    pr.next_id += 1
    pr.apply(edid, [{'op': 'record', 'key': k, 'record': rec}])
    return k


import factionfolk as FF  # noqa: E402
pr.apply('the Huang', [{'op': 'record', 'key': '+%06X' % pr.next_id, 'record': FF._faction(G, 'FOLabHuangFaction', 'Huang')}])
pr.next_id += 1
npc('FOLabPirateTest')
npc(AQ.LIU_WEI)
elder = npc(AP.ELDER, 'Zhanglao')
names = ['fang', 'tan', 'tan_chest', 'tenant', 'handover', 'buyer', 'gao', 'steward', 'distiller', 'gtenant', 'pickup',
         'wei', 'xu', 'he', 'compact_chest', 'store', 'camp'] + ['raider%d' % n for n in range(AQ.RAIDERS)] + ['pirate%d' % n for n in range(AQ.BUYERS)]
S = {n: (x0 + 180.0 * (k % 8), y0 + 180.0 * (k // 8), 9000.0) for k, n in enumerate(names)}
AQ.apply(pr, G, {'rows': [], 'skipped': [], 'spots': S, 'world': G.key(world)})
S4 = {n: (x0 + 200.0 * k, y0 + 1500.0, 9000.0) for k, n in enumerate(('king', 'guard0', 'guard1', 'duke', 'eng', 'box'))}
undo0 = len(pr.undo_stack)
rep = AP.apply(pr, G, {'rows': [], 'skipped': [], 'spots': S4, 'world': G.key(world)})
check('one Undo', len(pr.undo_stack) == undo0 + 1)
check('five people: the Ship-King, two guards, the Duke, his engineer', rep['people'] == 5, rep['people'])
check('lines for every way through', rep['lines'] >= 25, rep['lines'])
try:
    AP.apply(pr, G, {'rows': [], 'skipped': [], 'spots': S4, 'world': G.key(world)})
    check('a second run is refused', False)
except ValueError:
    check('a second run is refused', True)
twice = [e for e, n in collections.Counter(recordio.field(r, 'EDID') for r in pr.records.values() if recordio.field(r, 'EDID')).items() if n > 1]
check('no editor ID made twice', not twice, twice)

os.makedirs(project.BUILD_DIR, exist_ok=True)
out = os.path.join(project.BUILD_DIR, 'An Four Test.esp')
espwrite.write(G, pr, out)
g = gamedata.GameData(plugins=list(gamedata.OFFICIAL) + [out])
i = len(g.plugins) - 1
mine = {tes4.zstr(g.fields(f).get('EDID', b'')): f for f, (n, r) in g.forms.items() if n == i}
fid = lambda e: g.forms[mine[e]][1].formid
allsubs = lambda e: list(tes4.iter_subrecords(g.plugins[i].data(g.forms[mine[e]][1])))
sctx = lambda e: b' '.join(d for t, d in allsubs(e) if t == 'SCTX')
stages = [struct.unpack('<h', d[:2])[0] for t, d in allsubs(AP.Q4) if t == 'INDX']
check('By Order of the Palace: summoned, ordered, sealed, the Duke in line or dead, the betrayal, accepted', stages == [5, 10, 20, 30, 32, 34, 100], stages)
q = sctx(AP.Q4)
check('accepted: the Huang take you in, fame and face', b'AddToFaction FOLabHuangFaction' in q and b'huang + 15' in q)
check('the betrayal: infamy, pirate fame, the houses pay', b'huang - 15' in q and b'betrayed to 1' in q)
s = sctx('FOLabAnByOrderScript')
check('the betrayal turns the palace on you; the Duke dead is an ending', b'SetEnemy FOLabAnPalaceFaction PlayerFaction' in s and b'SetStage FOLabAnByOrder 32' in s)
pf = fid('FOLabAnPalaceFaction')
king = [r for k, r in pr.records.items() if r.get('type') == 'NPC_' and recordio.field(r, 'FULL') == 'The Ship-King']
fac_of = lambda r: [f['value'] for s_ in r['subs'] if s_['tag'] == 'SNAM' for f in s_.get('fields', ()) if 'faction' in f.get('name', '').lower()]
check('the Ship-King is of the palace', king and any(AP.AQ._mod_key(pr, 'FOLabAnPalaceFaction', 'FACT') == v for v in fac_of(king[0])))
skills = collections.Counter()
texts, has_receipt = [], False
for f, (n, r) in g.forms.items():
    if n == i and r.tag == 'INFO':
        sd = list(tes4.iter_subrecords(g.plugins[n].data(r)))
        d = dict(sd)
        if 'KNAM' in d:
            skills[g.edid(struct.unpack('<I', d['KNAM'])[0])] += 1
        texts += [tes4.zstr(v) for t, v in sd if t == 'NAM1']
        if b'RemoveItem FOLabAnVaultReceipt' in b''.join(v for t, v in sd if t == 'SCTX'):
            has_receipt = True
check('the Duke: Speech, Barter, Science, Explosives checks', {'AVSpeech', 'AVBarter', 'AVScience', 'AVExplosives'} <= set(skills), dict(skills))
check('the Vault-Tec receipt shames him', has_receipt)
check('the elder seals the order', any('Shizu de yin' in t for t in texts))
check('Mandarin subtitles, none over 150', all(len(t) <= 150 for t in texts) and sum(t in AP.ZH for t in texts) >= 15)
sm = health.check_file(g, out)['summary']
check('the plugin passes health with no errors', sm.get('error', 0) == 0, sm)
