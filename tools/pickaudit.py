"""pickaudit.py: after the door-pick rehearsal (D:\\FOLabScratch\\pick2), against its backup: the moved doors' arrivals on the
navmesh before and after, and which doors dropped out of the count."""
import json, os, sys
HOME = r'D:\FOLabScratch\pick2'
APP = r'C:\Users\AMD RYZEN\Claude Code Projects\FOLab\app'
HERE = os.path.dirname(os.path.abspath(__file__))
os.environ['FOLAB_HOME'] = HOME
os.environ['FOLAB_NO_GAME_WRITES'] = '1'
sys.path.insert(0, APP)
import gamedata, project, server, doorswap  # noqa: E402
server.not_while_playing = lambda: None
server.GD = gamedata.GameData(); server.BR = None
pr = project.Project.open('Waikiki'); server.load_game(pr)
gd = server.GD
name = doorswap.Names(gd, pr)
back = [d for d in os.listdir(os.path.join(HOME, 'backups')) if d.startswith('Waikiki before door pick')][0]
old = project.Project(os.path.join(HOME, 'backups', back, 'Waikiki.json'))
rep = json.load(open(os.path.join(HERE, 'door_pick_report.json')))


def refs_of(p):
    return {rk: (ck, r) for ck, c in p.cells.items() for rk, r in (c.get('refs') or {}).items() if not r.get('removed')}


def on_mesh(p, ck, x, y, z):
    m = p.navmesh.get(ck)
    if not m:
        return None
    vs = m['verts']
    for t in m['tris']:
        a, b, c = (vs[i] for i in t[:3])
        if abs((a[2] + b[2] + c[2]) / 3.0 - z) > 120:
            continue
        def s_(p1, q1, r1): return (p1[0] - r1[0]) * (q1[1] - r1[1]) - (q1[0] - r1[0]) * (p1[1] - r1[1])
        d = (s_((x, y), a, b), s_((x, y), b, c), s_((x, y), c, a))
        if not (min(d) < 0 < max(d)):
            return True
    return False


def cell_at(ck, x, y):
    try:
        w = gd.ext_cells.get(gd.from_key(ck))
    except Exception:
        w = None
    if w is None:
        return ck
    c = gd.grid(w).get((int(x // 4096), int(y // 4096)))
    return gd.key(c) if c is not None else ck


now, was = refs_of(pr), refs_of(old)
rows = {'both on': 0, 'off before too': 0, 'on before, off now': [], 'no mesh there': 0}
for m in rep['moved']:
    if not m.get('out'):
        continue
    rk = m['door']
    for k, (c, x) in now.items():
        if (x.get('tel') or {}).get('door') != rk:
            continue
        a_now = x['tel']['p']
        a_was = ((was.get(k) or (None, {}))[1].get('tel') or {}).get('p') or a_now
        ck = now[rk][0]
        b = on_mesh(old, cell_at(ck, a_was[0], a_was[1]), a_was[0], a_was[1], a_was[2] - 8)
        n = on_mesh(pr, cell_at(ck, a_now[0], a_now[1]), a_now[0], a_now[1], a_now[2] - 8)
        if b is None or n is None:
            rows['no mesh there'] += 1
        elif n:
            rows['both on'] += 1
        elif not b:
            rows['off before too'] += 1
        else:
            rows['on before, off now'].append((rk, m['is'], k, a_was == a_now))
print(json.dumps({k: (v if not isinstance(v, list) else (len(v), v[:12])) for k, v in rows.items()}, indent=1))
# doors that dropped out of the count: in the before list, not in the after
gone = [k for k in rep['before'] if k not in rep['after']]
print('dropped out of the count', [(k, name((was.get(k) or (None, {}))[1].get('base') or '')[0], k in now) for k in gone])
