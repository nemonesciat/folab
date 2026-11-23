"""The city's navmesh taken out of the closed hotels (the user, 22 Nov 2026, after seven people were found standing in the
closed Royal Hawaiian's lobby: "remove the navmesh triangles inside ... so nobody can path in there"). Inside each closed
hotel's walls the city navmesh is sealed islands, nothing joined to the street: the Royal Hawaiian 20 triangles (four
islands, two cells, each pair joined only to its partner across the cell border), the Moana 10 (one island), the Kilauea
none. Every island wholly inside is deleted through navedit (its links renumbered, the meshes round it retargeted, each mesh
checked by navmesh.validate); an island with any triangle outside the walls is left and reported.

Run with the main checkout's app (it reads the change journal, projects/Waikiki.changes).
py -3 shell_navmesh_out.py rehearse   a copy of Waikiki (json, journal, source) in D:\\FOLabScratch\\hotel-install\\shellnav_home
py -3 shell_navmesh_out.py real       Waikiki itself: game, FOLab, MO2, GECK closed; backup first; one Undo
                                       ("No navmesh inside the closed hotels"). Then the usual build and install.
"""
import math
import os
import shutil
import subprocess
import sys
import time

MODE = sys.argv[1] if len(sys.argv) > 1 else 'rehearse'
REAL_HOME = 'C:/Users/AMD RYZEN/Claude Code Projects/FOLab/packaging/out/FOLab'
SCRATCH = 'D:/FOLabScratch/hotel-install/shellnav_home'
APP = 'C:/Users/AMD RYZEN/Claude Code Projects/FOLab/app'          # (the main checkout: journal-aware project.py)
LABEL = 'No navmesh inside the closed hotels'
sys.stdout.reconfigure(encoding='utf-8')
if MODE == 'real':
    tl = subprocess.run(['tasklist'], capture_output=True, text=True).stdout.lower()
    for exe in ('falloutnv.exe', 'folab.exe', 'play.exe', 'modorganizer.exe', 'geck.exe'):
        if exe in tl:
            sys.exit('close ' + exe + ' first')
    HOME = REAL_HOME
else:
    HOME = SCRATCH
    src = REAL_HOME + '/projects'
    if os.path.isdir(SCRATCH):
        shutil.rmtree(SCRATCH)
    os.makedirs(SCRATCH + '/projects')
    for n in os.listdir(src):
        if n.startswith('Waikiki.') and os.path.isfile(os.path.join(src, n)):
            shutil.copy2(os.path.join(src, n), os.path.join(SCRATCH, 'projects', n))
    shutil.copytree(src + '/Waikiki source', SCRATCH + '/projects/Waikiki source')
    print('copied Waikiki (json and journal) into', SCRATCH, flush=True)
os.environ['FOLAB_HOME'] = HOME
os.environ['FOLAB_NO_GAME_WRITES'] = '1'
sys.path.insert(0, APP)
mod = HOME + '/projects/Waikiki.json'
if MODE == 'real':
    back = HOME + '/backups/Waikiki before shell navmesh out ' + time.strftime('%m%d-%H%M')
    os.makedirs(back)
    for n in os.listdir(HOME + '/projects'):
        if n.startswith('Waikiki.') and os.path.isfile(os.path.join(HOME, 'projects', n)):
            shutil.copy2(os.path.join(HOME, 'projects', n), os.path.join(back, n))
    print('backup', back, flush=True)

import gamedata, navedit, navmesh as N, project, server, stormsched   # noqa: E402
server.GD = gamedata.GameData()
server.BR = None
seen = os.path.getmtime(mod)
pr = project.Project.open('Waikiki')
server.load_game(pr)
server.PR = pr
gd = server.GD
city = stormsched._world(gd, 'FOLabWaikiki')
HOTELS = {
    'royal_hawaiian': ((-94422.0, -24124.0, 26.0, 0.0), lambda lx, ly: abs(lx) < 2000 - 20 and abs(ly) < 400 - 20),
    'moana': ((-88066.0, -25696.0, 26.0, 0.7854), lambda lx, ly: abs(lx) < 900 - 20 and abs(ly) < 450 - 20),
    'kilauea': ((-105593.0, -16889.0, 27.2, 3.1416), lambda lx, ly: math.hypot(lx, ly) < 2900 * 0.8 - 20),
}
grid = {gd.key(c): xy for xy, c in gd.grid(city).items()}
# (23 Nov 2026, item 4: the Royal Hawaiian's city door +047E98 lost its link. Its triangle was in the lobby's island;
# navedit re-links a door whose triangle goes to the nearest one left, but navbuild._ref_position had no place for a
# door the mod added, so it went into `no_door`. The app is fixed on claude/zealous-rosalind-5e1645; until the main
# checkout has it, the same here. And a door with no triangle left within DOOR_KEEP keeps its own.)
import navbuild  # noqa: E402
DOOR_KEEP = 600.0
if 'project' not in navbuild._ref_position.__code__.co_varnames:
    _game_position = navbuild._ref_position

    def _ref_position(gd_, key, project=None):
        for c in (project or pr).cells.values():
            r = (c.get('refs') or {}).get(key)
            if r is not None:
                return None if r.get('removed') or not r.get('p') else tuple(r['p'][:3])
        return _game_position(gd_, key)
    navbuild._ref_position = _ref_position


def local(spot, x, y):
    cx, cy, _z, rz = spot
    dx, dy = x - cx, y - cy
    c, s = math.cos(rz), math.sin(rz)
    return dx * c - dy * s, dx * s + dy * c


def inside_of(m):
    """Triangle numbers of mesh m standing inside any closed hotel (middle inside its walls, on its ground floor)."""
    out = set()
    V, T = m['verts'], m['tris']
    for ti, t in enumerate(T):
        pts = [V[t[k]] for k in range(3)]
        mx, my, mz = (sum(p[k] for p in pts) / 3 for k in range(3))
        for spot, inside in HOTELS.values():
            lx, ly = local(spot, mx, my)
            if inside(lx, ly) and mz < spot[2] + 400:
                out.add(ti)
    return out


def islands(m):
    T = m['tris']
    parent = list(range(len(T)))

    def f(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    for ti, t in enumerate(T):
        for i in range(3):
            nb = t[3 + i]
            if not (t[6] >> i & 1) and nb != N.NONE and 0 <= nb < len(T):
                parent[f(ti)] = f(nb)
    out = {}
    for ti in range(len(T)):
        out.setdefault(f(ti), []).append(ti)
    return list(out.values())


def survey():
    found = []
    for ck in grid:
        for c in HOTELS.values():
            pass
        nm = pr.navmesh.get(ck)
        if not nm:
            continue
        for mi, d in enumerate([nm] + nm.get('others', [])):
            ins = inside_of(d)
            if not ins:
                continue
            for isl in islands(d):
                n_in = sum(1 for ti in isl if ti in ins)
                if n_in:
                    found.append((ck, grid[ck], mi, sorted(isl), n_in))
    return found


before = survey()
print('before:', [(xy, mi, len(isl), n_in) for _ck, xy, mi, isl, n_in in before], flush=True)
sess = navedit.Session(gd, pr, before[0][0]) if before else None
cut, left, gone = 0, [], {}
for ck, xy, mi, isl, n_in in before:
    if n_in != len(isl):
        left.append((xy, mi, len(isl), n_in))
        continue
    gone.setdefault((ck, mi), []).extend(isl)
# (every mesh as the session holds it before any change: the same triangles, numbered as in pr.navmesh)
for ck, mi in gone:
    e = sess.entry(ck, mi)
    if len(e['m']['tris']) != len(pr.navmesh[ck]['tris'] if mi == 0 else pr.navmesh[ck]['others'][mi - 1]['tris']):
        sys.exit('%s: the session sees a different mesh than the project: stopping' % (grid[ck],))
# a door linked to a triangle that goes: it is linked again to the nearest one left (navedit), if one is within DOOR_KEEP;
# else its own triangle stays
kept_doors, relinked = [], []
for (ck, mi), tris in gone.items():
    m = sess.entry(ck, mi)['m']
    out_ = set(tris)
    V = m['verts']
    for d in m['doors']:
        if d[1] not in out_:
            continue
        p = navbuild._ref_position(gd, d[0], pr)
        near = p and min((N._tri_distance(p, V[t[0]], V[t[1]], V[t[2]]) for ti, t in enumerate(m['tris']) if ti not in out_),
                         default=None)
        if near is not None and near <= DOOR_KEEP:
            relinked.append((d[0], round(near)))
        else:
            out_.discard(d[1])
            kept_doors.append(d[0])
    gone[(ck, mi)] = sorted(out_)
print('doors whose triangle goes: linked again to the nearest left %s; kept their own %s' % (relinked, kept_doors), flush=True)
for (ck, mi), tris in gone.items():          # (one call a mesh: a deletion renumbers what's left)
    cut += sess.delete(ck, mi, tris)
missed_now = [d for row in sess.A.cells.values() for e in row if e['form'] in sess.touched for d in e['data'].get('no_door', [])
              if d in {x for x, _n in relinked}]
if missed_now:
    sys.exit('doors left unlinked by the cut: %s: nothing written' % missed_now)
if left:
    print('islands reaching outside the walls, left as they are:', left, flush=True)
if not cut:
    sys.exit('no navmesh inside the closed hotels: nothing to do (run once only)')
ops = sess.finish()          # (each changed mesh checked by navmesh.validate: EditError stops here, nothing written)
if os.path.getmtime(mod) != seen:
    sys.exit('Waikiki.json changed while loading: nothing written')
pr.apply(LABEL, ops)
pr.save()
after = survey()
bad = [N.validate(e['m']) for row in sess.A.cells.values() for e in row if e['form'] in sess.touched]
print('took out %d triangles; meshes changed: %s' % (cut, sorted({o['cell'] for o in ops})), flush=True)
print('after: inside the closed hotels %d triangles; mesh faults %s' % (sum(n for *_x, n in after), [b for b in bad if b]))
print('CHECKS: all good' if not after and not any(bad) else 'CHECKS FAILED', '; one Undo: "%s"' % LABEL)
