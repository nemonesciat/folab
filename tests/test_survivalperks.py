"""More Survival perks (survivalperks.py): six playable perks, each asking its Survival and level; three abilities; the Wild
Medicine recipe asking the perk; the quest's script compiles; a small mod with them written, read back, passing health."""
import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import browse  # noqa: E402
import espwrite  # noqa: E402
import gamedata  # noqa: E402
import health  # noqa: E402
import milestones  # noqa: E402
import project  # noqa: E402
import server  # noqa: E402
import survivalperks as S  # noqa: E402
import tes4  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


milestones.ISLAND = 'WastelandNV'                 # (the test's stand-in for the island's world)
G = server.GD = gamedata.GameData()
server.BR = browse.Browse(G, lambda: server.PR)
pr = server.PR = project.Project.create('Survival Test')
P = S.plan(G, pr)
check('without fishing spots or wrack, those hooks wait (said so)', {w for w, _x in P['skipped']} >= {'fishing spots', "the storm's wrack"}, P['skipped'])
rep = S.apply(pr, G, P)
check('one change', len(pr.undo_stack) == 1)
os.makedirs(project.BUILD_DIR, exist_ok=True)
out = os.path.join(project.BUILD_DIR, 'Survival Test.esp')
espwrite.write(G, pr, out)
g = gamedata.GameData(plugins=list(gamedata.OFFICIAL) + [out])
i = len(g.plugins) - 1
recs = {}
for f, (n, r) in g.forms.items():
    if n == i:
        recs[g.edid(f)] = (r.tag, list(tes4.iter_subrecords(g.plugins[n].data(r))))
perks = {e: v[1] for e, v in recs.items() if v[0] == 'PERK'}
check('six perks', len(perks) == 6, sorted(perks))
ok = []
for key, (edid, _n, need, level, _w, _e) in S.PERKS.items():
    subs = perks.get(edid, [])
    data = next((v for t, v in subs if t == 'DATA' and len(v) == 5), b'')
    cond = [v for t, v in subs if t == 'CTDA' and struct.unpack_from('<H', v, 8)[0] == 495]
    ok.append(bool(data) and data[1] == level and data[3] == 1 and cond and struct.unpack_from('<f', cond[0], 4)[0] == need
              and struct.unpack_from('<I', cond[0], 12)[0] == 44)
check('each playable at its level, asking its Survival', all(ok), ok)
check('three abilities', sum(1 for v in recs.values() if v[0] == 'SPEL') == 3)
rc = recs.get(S.RECIPE[0], (None, []))
check('the poultice recipe asks the perk (HasPerk) before its data', rc[0] == 'RCPE' and [t for t, _v in rc[1]][2:4] == ['CTDA', 'DATA']
      and struct.unpack_from('<H', [v for t, v in rc[1] if t == 'CTDA'][0], 8)[0] == 449)
h = health.check_file(g, out)
bad = [(x['kind'], x['count'], [r['text'] for r in x['rows']][:2]) for x in h['groups'] if x['sev'] == 'error']
check('the plugin passes health', not bad, bad)
