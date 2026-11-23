"""door_links_into_waikiki.py [real] [--home H] [--app A]: doors a navmesh edit left with no triangle linked again (the
Workshop's item 4, 23 Nov 2026: the Royal Hawaiian's city door +047E98 had no navmesh link). shell_navmesh_out took the
triangle it was linked to (triangle 80 of cell 000DC6's mesh, in the lobby's sealed island); navedit then looks for the
nearest triangle left, but navbuild._ref_position gave no place for a door the mod added, so the door went into the
mesh's `no_door` list and nothing linked it (fixed in the app, commit on claude/zealous-rosalind-5e1645).

Here: every door in a mesh's `no_door` that stands (not removed) in that mesh's own cell gets the nearest triangle within
REACH (navmesh.link_doors: the triangle flagged as a door's, the door in the mesh's door list, so the build writes its
XNDP and NVDP); a door with none that near stays listed, and is reported. Nothing else of any mesh changes (each checked
by navmesh.validate). One Undo; no backup (the install makes the one); refuses while the game runs (not on a
FOLabScratch home). Dry run without `real`."""
import copy, math, os, subprocess, sys, time

ARGS = sys.argv[1:]
REAL = 'real' in ARGS


def opt(name, default):
    return ARGS[ARGS.index(name) + 1] if name in ARGS else default


HOME = opt('--home', r'C:\Users\AMD RYZEN\Claude Code Projects\FOLab\packaging\out\FOLab')
APP = opt('--app', r'C:\Users\AMD RYZEN\Claude Code Projects\FOLab\app')
REACH = 600.0          # (navmesh.DOOR_REACH is 1,024; the game's are within 546 of their door 99 times in 100)
os.environ['FOLAB_HOME'] = HOME
os.environ['FOLAB_NO_GAME_WRITES'] = '1'
sys.path.insert(0, APP)
sys.stdout.reconfigure(encoding='utf-8')
t0 = time.time()
say = lambda *a: print('%5.0fs' % (time.time() - t0), *a, flush=True)
if REAL and 'FOLabScratch' not in HOME:
    running = subprocess.run(['tasklist'], capture_output=True, text=True).stdout.lower()
    busy = [n for n in ('falloutnv.exe', 'nv-rs.exe', 'nvrs.exe', 'folab.exe', 'modorganizer.exe', 'nvse_loader.exe', 'play.exe', 'geck.exe')
            if n in running]
    if busy:
        sys.exit('not while these run: ' + ', '.join(busy))
import gamedata, project, server, navmesh as N  # noqa: E402
src = os.path.join(project.PROJECTS_DIR, 'Waikiki.json')
was = project.modified(src)
say('mod', src, time.strftime('%d %b %H:%M', time.localtime(was)))
server.not_while_playing = lambda: None
server.GD = gamedata.GameData(); server.BR = None
pr = project.Project.open('Waikiki'); server.load_game(pr); server.PR = pr
gd = server.GD
where = {rk: (ck, r) for ck, c in pr.cells.items() for rk, r in (c.get('refs') or {}).items()}


def listed():
    out = []
    for ck, m in pr.navmesh.items():
        for mi, mm in enumerate([m] + list(m.get('others', []))):
            for d in mm.get('no_door', []) or []:
                out.append((ck, mi, d))
    return out


before = listed()
say('doors listed with no triangle:', len(before))
ops, linked, left = [], [], []
by_mesh = {}
for ck, mi, d in before:
    by_mesh.setdefault((ck, mi), []).append(d)
import navedit  # noqa: E402
sess = None
for (ck, mi), doors in sorted(by_mesh.items()):
    sess = sess or navedit.Session(gd, pr, ck)
    e0 = sess.entry(ck, mi)
    have = {x[0] for x in e0['m']['doors']}
    want = []
    for d in doors:
        dck, r = where.get(d, (None, None))
        if r is None or r.get('removed') or not r.get('p') or r['p'][2] < -20000:
            left.append((ck, d, 'not standing in the mod'))
            continue
        if dck != ck and not r.get('persistent'):
            left.append((ck, d, 'in another cell (%s)' % dck))
            continue
        if d in have:
            continue
        want.append((d, tuple(r['p'][:3])))
    if not want:
        continue
    V, T = e0['m']['verts'], e0['m']['tris']
    near = []
    for d, p in want:
        best = min((N._tri_distance(p, V[t[0]], V[t[1]], V[t[2]]) for t in T), default=None)
        if best is None or best > REACH:
            left.append((ck, d, 'no triangle within %d (nearest %s)' % (REACH, None if best is None else round(best))))
        else:
            near.append((d, p))
    if not near:
        continue
    e = sess.mine(ck, mi)
    found, missed = N.link_doors(e['m'], near)
    V = e['m']['verts']
    for d in found:
        p = dict(near)[d]
        t = e['m']['tris'][found[d]]
        c = [sum(V[t[k]][a] for k in range(3)) / 3.0 for a in range(3)]
        linked.append((ck, d, found[d], round(math.dist(c, p))))
    nd = [d for d in e['data'].get('no_door', []) if d not in found]
    e['data'] = dict(e['data'], no_door=nd)
    if not nd:
        e['data'].pop('no_door')
if sess is not None and linked:
    ops = sess.finish()          # (each changed mesh checked by navmesh.validate: EditError stops here, nothing written)
for ck, d, ti, dist in linked:
    say('  linked %s in %s to triangle %d (its middle %d from the door)' % (d, ck, ti, dist))
for ck, d, why in left:
    say('  left %s in %s: %s' % (d, ck, why))
say('doors linked %d, left %d; meshes changed %d' % (len(linked), len(left), len(ops)))
if not REAL:
    say('dry run: nothing saved')
    sys.exit(0)
if not ops and 'check' not in ARGS:
    sys.exit('nothing to link: run already?')
if project.modified(src) != was:
    sys.exit('Waikiki changed while this ran: stopping')
if ops:
    pr.apply('Doors a navmesh edit left unlinked, linked again', ops)
    say('applied and saved')
else:
    ops = [{'cell': ck} for ck in ('Waikiki.esp:000DC6',)]      # (check only: the cell this step is for)
pr2 = project.Project.open('Waikiki')
linked_now = {(ck, d[0]) for ck, m in pr2.navmesh.items() for mm in [m] + list(m.get('others', [])) for d in mm['doors']}
missing = [(ck, d) for ck, d, ti, dist in linked if (ck, d) not in linked_now]
still = len([x for x in [(ck, mi, d) for ck, m in pr2.navmesh.items() for mi, mm in enumerate([m] + list(m.get('others', []))) for d in mm.get('no_door', []) or []]])
check = navedit.Session(gd, pr2, sorted({o['cell'] for o in ops})[0])
faults = []
for ck in sorted({o['cell'] for o in ops}):
    for e_ in check.A.meshes(ck):
        N.refresh(e_['m'])                   # (its search grid and counts, as the writer makes them)
        if N.validate(e_['m']):
            faults.append((ck, N.validate(e_['m'])[:2]))
say('from the saved mod: linked doors found %d of %d; still listed with no triangle %d; meshes failing their check %d'
    % (len(linked) - len(missing), len(linked), still, len(faults)))
rh = any(d == '+047E98' for ck, d in linked_now)
say('the Royal Hawaiian city door +047E98 linked:', rh)
say('faults', faults)
say('CHECKS: ' + ('all good' if not missing and not faults and rh else 'PROBLEMS'))
