"""Skill-milestone perks (milestones.py): 52 perks, every skill three milestones with a choice of two at 100; entry-point perks
laid out as the game's (PRKE 2, DATA point/function/tabs, PRKC + CTDA filters, EPFT, EPFD, PRKF), ability perks naming their
SPEL; the milestone quest's script compiles; a small mod with it all written, read back, passing health."""
import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import browse  # noqa: E402
import espwrite  # noqa: E402
import gamedata  # noqa: E402
import health  # noqa: E402
import milestones as M  # noqa: E402
import project  # noqa: E402
import server  # noqa: E402
import tes4  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


check('thirteen skills, each 50, 75 and two at 100', len(M.PERKS) == 13 and all(sorted(p[0] for p in ps) == [50, 75, 100, 100] for ps in M.PERKS.values()))
names = [p[2] for ps in M.PERKS.values() for p in ps]
check('every perk its own name', len(set(names)) == len(names) == 52)
M.ISLAND = 'WastelandNV'                     # (the test's stand-in for the island's world)
G = server.GD = gamedata.GameData()
server.BR = browse.Browse(G, lambda: server.PR)
pr = server.PR = project.Project.create('Milestone Test')
P = M.plan(G, pr)
rep = M.apply(pr, G, P)
check('one change, every perk made', rep['perks'] == 52 and len(pr.undo_stack) == 1, (rep['perks'], rep['kinds']))
check('most perks do something now (entry points, abilities, a script)', rep['kinds'].get('ep', 0) + rep['kinds'].get('ab', 0) >= 24, rep['kinds'])
os.makedirs(project.BUILD_DIR, exist_ok=True)
out = os.path.join(project.BUILD_DIR, 'Milestone Test.esp')
espwrite.write(G, pr, out)
g = gamedata.GameData(plugins=list(gamedata.OFFICIAL) + [out])
i = len(g.plugins) - 1
perks = {}
for f, (n, r) in g.forms.items():
    if n == i and r.tag == 'PERK':
        perks[g.edid(f)] = list(tes4.iter_subrecords(g.plugins[n].data(r)))
check('52 perks in the plugin', len(perks) == 52, len(perks))
md = perks.get('FOLabPerkMarketDay', [])
seq = [t for t, _v in md]
data = [v for t, v in md if t == 'DATA']
check('Market Day: Calculate Buy Price (17), multiply, 2 tabs, 0.85, only on the island',
      data[-1:] == [bytes((17, 3, 2))] and any(t == 'EPFD' and abs(struct.unpack('<f', v)[0] - 0.85) < 1e-6 for t, v in md)
      and 'PRKC' in seq and seq[-1] == 'PRKF', [(t, v.hex()) for t, v in md if t not in ('EDID', 'FULL', 'DESC', 'ICON')])
pd = [v for t, v in md if t == 'DATA'][0]
check('not playable (given, not picked), shown', pd[3] == 0 and pd[4] == 0, pd.hex())
sl = perks.get('FOLabPerkSeaLegs', [])
ab = [v for t, v in sl if t == 'DATA'][-1:]
spel = g.forms.get((i << 24) | (struct.unpack('<I', ab[0])[0] & 0xFFFFFF)) if ab and len(ab[0]) == 4 else None   # (the file's own form, in load order)
check('Sea Legs: an ability perk naming its SPEL', spel is not None and spel[1].tag == 'SPEL', ab)
q = next((f for f, (n, r) in g.forms.items() if n == i and r.tag == 'QUST' and g.edid(f) == M.QUEST), None)
check('the milestone quest is in', q is not None)
h = health.check_file(g, out)
bad = [(x['kind'], x['count'], [r['text'] for r in x['rows']][:2]) for x in h['groups'] if x['sev'] == 'error']
check('the plugin passes health', not bad, bad)
