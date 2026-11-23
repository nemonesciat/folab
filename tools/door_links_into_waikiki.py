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
import navedit, arrivalcheck  # noqa: E402
NEAR, GAP, WIDE = 60.0, 48.0, 24.0     # (GAP: 32 stood within a body of the hotel's front)
FRONT = ['+047E98']                # (the Royal Hawaiian's city door: linked already, 92 from the street's edge)
FRONT_CELL = 'Waikiki.esp:000DC6'
Wd = arrivalcheck.World(gd, pr)
fronts = []
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
        linked.append((ck, d, found[d], round(N._tri_distance(p, V[t[0]], V[t[1]], V[t[2]]))))
    nd = [d for d in e['data'].get('no_door', []) if d not in found]
    e['data'] = dict(e['data'], no_door=nd)
    if not nd:
        e['data'].pop('no_door')

def door_half(base):
    """Half a door's width, from its record's bounds."""
    try:
        if base.startswith('+'):
            b = [int(f['value']) for f in next(x for x in pr.records[base]['subs'] if x['tag'] == 'OBND')['fields'] if 'name' in f]
        else:
            import struct
            b = struct.unpack('<6h', gd.fields(gd.from_key(base))['OBND'][:12])
        return (b[3] - b[0]) / 2.0
    except Exception:
        return 80.0


def front(ck, mi, d, p):
    # a door whose triangle is further than NEAR from it (the Workshop: people walk to the triangle and go through from
    # there): its triangle's free edge facing the door carried on to GAP in front of the door, two triangles joined to it,
    # if nothing solid stands there at body height; the door linked to the nearer of them
    m = sess.entry(ck, mi)['m']               # (read only until the strip is known clear: mine() marks it changed)
    ti = next(x[1] for x in m['doors'] if x[0] == d)
    V = m['verts']
    t = m['tris'][ti]
    if N._tri_distance(p, V[t[0]], V[t[1]], V[t[2]]) <= NEAR:
        return
    best = None
    for i in range(3):
        if t[3 + i] != N.NONE or (t[6] >> i & 1):
            continue
        a_, b_ = V[t[i]], V[t[(i + 1) % 3]]
        ex, ey = b_[0] - a_[0], b_[1] - a_[1]
        ln = math.hypot(ex, ey)
        nx, ny = ey / ln, -ex / ln                     # (anticlockwise corners: the edge's outside is to its right)
        dist = (p[0] - a_[0]) * nx + (p[1] - a_[1]) * ny
        if dist > 0 and (best is None or dist < best[0]):
            best = (dist, i, nx, ny)
    if best is None:
        fronts.append((ck, d, 'no free edge of its triangle faces the door'))
        return
    dist, i, nx, ny = best
    step = dist - GAP
    ia, ib = t[i], t[(i + 1) % 3]
    a_, b_ = V[ia], V[ib]
    # (a trapezoid: the whole edge on the triangle's side, the door's width and WIDE more either side at the door's)
    ex, ey = b_[0] - a_[0], b_[1] - a_[1]
    ln = math.hypot(ex, ey)
    ux, uy = ex / ln, ey / ln
    sd = (p[0] - a_[0]) * ux + (p[1] - a_[1]) * uy
    half = door_half(where[d][1]['base']) + WIDE
    s0, s1 = max(0.0, sd - half), min(ln, sd + half)
    if s1 - s0 < 2 * WIDE:
        fronts.append((ck, d, 'the edge facing it does not run across its front'))
        return
    na_ = (a_[0] + ux * s0 + nx * step, a_[1] + uy * s0 + ny * step, a_[2])
    nb_ = (a_[0] + ux * s1 + nx * step, a_[1] + uy * s1 + ny * step, a_[2])
    spots = [(a_[0] + ux * (s0 + (s1 - s0) * u) + nx * step * w, a_[1] + uy * (s0 + (s1 - s0) * u) + ny * step * w)
             for u in (0.0, 0.25, 0.5, 0.75, 1.0) for w in (0.3, 0.65, 1.0)]
    g_ = Wd.group(ck)
    blocked = [b for b in (Wd.judge(g_, x_, y_, a_[2] + 0.0, Wd.outside(g_))[0] for x_, y_ in spots) if b]
    if blocked:
        fronts.append((ck, d, 'something stands in front of it: %s' % sorted(set(blocked))))
        return
    m = sess.mine(ck, mi)['m']
    t1 = sess.add(ck, mi, [ib, ia, list(na_)])
    nai = len(m['verts']) - 1                   # (the corner add just made)
    t2 = sess.add(ck, mi, [ib, nai, list(nb_)])
    # the door to the nearer new triangle, off the old one
    m['doors'] = [x for x in m['doors'] if x[0] != d]
    if not any(x[1] == ti for x in m['doors']):
        m['tris'][ti] = m['tris'][ti][:6] + (m['tris'][ti][6] & ~N.F_DOOR,) + m['tris'][ti][7:]
    got, _miss = N.link_doors(m, [(d, p)])
    V = m['verts']
    nt = m['tris'][got[d]]
    fronts.append((ck, d, 'linked to new triangle %d, %d from the door (was triangle %d, %d)'
                   % (got[d], round(N._tri_distance(p, V[nt[0]], V[nt[1]], V[nt[2]])), ti, round(dist))))
    linked[:] = [x for x in linked if x[1] != d] + [(ck, d, got[d], round(N._tri_distance(p, V[nt[0]], V[nt[1]], V[nt[2]])))]


sess = sess or (navedit.Session(gd, pr, FRONT_CELL) if FRONT else None)
linked_in = {}
for ck, m0 in pr.navmesh.items():
    for mi, mm in enumerate([m0] + list(m0.get('others', []))):
        for x in mm.get('doors', []):
            linked_in.setdefault(x[0], (ck, mi))
for ck, d, ti, dist in linked:
    linked_in[d] = (ck, 0)
for d in sorted({x[1] for x in linked} | set(FRONT)):
    if d not in where or d not in linked_in:
        fronts.append(('?', d, 'not linked to any navmesh, or not in the mod'))
        continue
    front(linked_in[d][0], linked_in[d][1], d, tuple(where[d][1]['p'][:3]))
if sess is not None and (linked or sess.touched):
    ops = sess.finish()          # (each changed mesh checked by navmesh.validate: EditError stops here, nothing written)
for ck, d, ti, dist in linked:
    say('  linked %s in %s to triangle %d (%d from the door)' % (d, ck, ti, dist))
for ck, d, what in fronts:
    say('  in front of %s: %s' % (d, what))
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
ops = ops or [{'cell': 'Waikiki.esp:000DC6'}]
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
rh_dist = None
for e_ in check.A.meshes('Waikiki.esp:000DC6'):
    for x in e_['m']['doors']:
        if x[0] == '+047E98':
            V_, t_ = e_['m']['verts'], e_['m']['tris'][x[1]]
            rh_dist = round(N._tri_distance(tuple(where['+047E98'][1]['p'][:3]), V_[t_[0]], V_[t_[1]], V_[t_[2]]), 1)
            seen_ = {x[1]}
            todo_ = [x[1]]
            T_ = e_['m']['tris']
            while todo_:
                tt = T_[todo_.pop()]
                for i in range(3):
                    if not (tt[6] >> i & 1) and tt[3 + i] != N.NONE and tt[3 + i] not in seen_:
                        seen_.add(tt[3 + i])
                        todo_.append(tt[3 + i])
            say('  its triangle %d: %s from the door; in a piece of %d of the %d triangles of its mesh' % (x[1], rh_dist, len(seen_), len(T_)))
say('the Royal Hawaiian city door +047E98 linked:', rh, '| its triangle within %d of it:' % NEAR, rh_dist is not None and rh_dist <= NEAR)
say('faults', faults)
say('CHECKS: ' + ('all good' if not missing and not faults and rh and rh_dist is not None and rh_dist <= NEAR else 'PROBLEMS'))
