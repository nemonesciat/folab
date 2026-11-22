"""ways_in_into_waikiki.py [real] [--home H] [--app A] [--before DIR]: a way in from the real city for the places that had
theirs only through copies in the hotels' small worlds (the user, 22 Nov 2026: "do the ready to make things").

- A: the places whose way out the view-door step (doorswap.view_copies_ops, 22 Nov 07:54) pointed at a city door that leads
  into another place, so nothing leads into them now (49 on Waikiki of 08:26).
- B: the places whose way out still leads to a copy in a hotel's small world whose city door is gone (13).

For each: the nearest city door that leads nowhere (no link, nothing leading to it, not a hotel's or a lift) within REACH of
where its old copy stood, unlocked and linked both ways. Arriving inside: where the old copy's link arrived (the place's own
spot in front of its door). Arriving outside: a step in front of the city door on the side that is on the city's navmesh
(else the side away from the building it is on), facing out. The B copies are locked and their links taken off, as
viewworld.stage_ops makes them. One Undo. Written by the doors session for the story session.

Runs with the main checkout's app by default (--app). --before: the backup taken just before the view-door step (to know which
copy each A place came through). Dry run without `real`; backup; refuses while the game runs (not on a FOLabScratch home); run
once (nothing left to do)."""
import json, math, os, shutil, subprocess, sys, time

ARGS = sys.argv[1:]
REAL = 'real' in ARGS


def opt(name, default):
    return ARGS[ARGS.index(name) + 1] if name in ARGS else default


HOME = opt('--home', r'C:\Users\AMD RYZEN\Claude Code Projects\FOLab\packaging\out\FOLab')
APP = opt('--app', r'C:\Users\AMD RYZEN\Claude Code Projects\FOLab\app')
BEFORE = opt('--before', os.path.join(HOME, 'backups', 'Waikiki before view doors 1122-0754'))
REACH = 6000.0     # (about a block and a half: no spare doorway stands nearer for most of them)
STEP = 110.0
os.environ['FOLAB_HOME'] = HOME
os.environ['FOLAB_NO_GAME_WRITES'] = '1'
sys.path.insert(0, APP)
sys.stdout.reconfigure(encoding='utf-8')
t0 = time.time()
say = lambda *a: print('%5.0fs' % (time.time() - t0), *a, flush=True)
SCRATCH = 'FOLabScratch' in HOME
if REAL and not SCRATCH:
    running = subprocess.run(['tasklist'], capture_output=True, text=True).stdout.lower()
    busy = [n for n in ('falloutnv.exe', 'nv-rs.exe', 'nvrs.exe', 'folab.exe', 'modorganizer.exe', 'nvse_loader.exe', 'play.exe', 'geck.exe')
            if n in running]
    if busy:
        sys.exit('not while these run: ' + ', '.join(busy))

import gamedata, project, server, doorswap, doorset, hotelinside, recordio  # noqa: E402
src = os.path.join(project.PROJECTS_DIR, 'Waikiki.json')
was = project.modified(src)
say('mod', src, time.strftime('%d %b %H:%M', time.localtime(was)), '| app', APP)
server.not_while_playing = lambda: None
server.GD = gamedata.GameData(); server.BR = None
pr = project.Project.open('Waikiki'); server.load_game(pr); server.PR = pr
gd = server.GD
name = doorswap.Names(gd, pr)
worlds = {gd.edid(w): w for w in gd.worlds()}
city_w = worlds[doorset.CITY]
city = {gd.key(c) for c in gd.grid(city_w).values()}
views = {}
for hotel, v in hotelinside.VIEWS.items():
    for c in gd.grid(worlds[v['world']]).values():
        views[gd.key(c)] = hotel
outside = city | set(views)
refs = {rk: (ck, r) for ck, c in pr.cells.items() for rk, r in (c.get('refs') or {}).items() if not r.get('removed')}
leads = {}
for rk, (ck, r) in refs.items():
    if (r.get('tel') or {}).get('door'):
        leads.setdefault(r['tel']['door'], []).append(rk)

# --- the places to give a way in ---
def place_doors():
    """[(place door ref, its cell, where its way out leads)] for doors in places (not outside cells) that lead outside."""
    out = []
    for rk, (ck, r) in refs.items():
        t = r.get('tel') or {}
        if ck in outside or not t.get('door') or t['door'] not in refs:
            continue
        if refs[t['door']][0] in outside:
            out.append((rk, ck, t['door']))
    return out

say('reading the mod as it was before the view-door step:', BEFORE)
before = project.Project(os.path.join(BEFORE, 'Waikiki.json'))
old = {rk: (ck, r) for ck, c in before.cells.items() for rk, r in (c.get('refs') or {}).items() if not r.get('removed')}
jobs = []          # (kind, place door, its cell, old copy ref, inside arrival, spot to search from)
HOTEL_OWN = ('FOLabLift', 'FOLabDoorRoyalHawaiian', 'FOLabDoorMoana', 'FOLabDoorKilauea', 'OffDoorHotelSmL01', 'HotelElevatorDoor')
reached = {ck for rk, (ck, r) in refs.items() for t in [r.get('tel') or {}] if t.get('door') in refs and refs[t['door']][0] != ck}
reached = {refs[r['tel']['door']][0] for rk, (ck, r) in refs.items() if (r.get('tel') or {}).get('door') in refs and refs[r['tel']['door']][0] != ck}
seen_a = set()
for rk, ck, to in sorted(place_doors()):
    tck = refs[to][0]
    if tck in city:
        if ck in reached or ck in seen_a:
            continue                                # (something leads into the place already, or it has its job)
        o = old.get(rk)
        oto = ((o[1].get('tel') or {}).get('door')) if o else None
        if not oto or old.get(oto, (None,))[0] not in views:
            continue
        copy = old[oto][1]
        inside = (copy.get('tel') or {}).get('p') if (copy.get('tel') or {}).get('door') == rk else None
        seen_a.add(ck)
        jobs.append(('A', rk, ck, oto, inside, copy['p']))
    elif tck in views:
        e = name(refs[to][1].get('base') or '')[0] or ''
        if any(e.startswith(h) for h in HOTEL_OWN):
            continue                                # (a hotel's own lift or lookout: rightly in its small world)
        copy = refs[to][1]
        inside = (copy.get('tel') or {}).get('p') if (copy.get('tel') or {}).get('door') == rk else None
        jobs.append(('B', rk, ck, to, inside, copy['p']))
say('places: A (nothing leads in since the view-door step)', sum(1 for j in jobs if j[0] == 'A'),
    '| B (way out to a hotel world copy)', sum(1 for j in jobs if j[0] == 'B'))

# --- free city doors ---
special = {k for (pc, t), k in doorswap.records_of(pr).items() if pc in doorset.HOTELS or pc.startswith('lift')}
free = []
for rk, (ck, r) in refs.items():
    if ck not in city or not r.get('p') or r['p'][2] < -20000 or r.get('tel') or leads.get(rk):
        continue
    e, t = name(r.get('base') or '')
    if t != 'DOOR' or r['base'] in special or e in doorset.LIFTS:
        continue
    if (r.get('props') or {}).get('parent'):
        continue                                    # (enabled by something: may be off)
    free.append((rk, ck, r))
say('city doors leading nowhere', len(free))
import health
UNREACHED_BEFORE = next((g['count'] for g in health.check_mod(server)['groups'] if g['title'] == 'Places nothing leads to'), 0)
say('health before: places nothing leads to', UNREACHED_BEFORE)


def obnd(base):
    try:
        if base.startswith('+'):
            s = next(x for x in pr.records[base]['subs'] if x['tag'] == 'OBND')
            return [int(f['value']) for f in s['fields'] if 'name' in f]
        import struct
        return list(struct.unpack('<6h', gd.fields(gd.from_key(base))['OBND'][:12]))
    except Exception:
        return [-60, -10, 0, 60, 10, 200]


# (doorways the game shuts with a door's static twin: the twin swapped for the real door, same mesh, same frame)
door_of = {}
for f, (_i, rec) in gd.forms.items():
    if rec.tag == 'DOOR':
        door_of.setdefault(gd.edid(f).lower(), gd.key(f))
shut = []
for rk, (ck, r) in refs.items():
    if ck not in city or not r.get('p') or r['p'][2] < -20000 or (r.get('props') or {}).get('parent'):
        continue
    e, t = name(r.get('base') or '')
    if t != 'STAT' or not e or not e.lower().endswith('static'):
        continue
    real = door_of.get(e.lower()[:-6])
    if real and max(abs(a - b) for a, b in zip(obnd(real), obnd(r['base']))) <= 10:
        shut.append((rk, ck, r, real))           # (only where the real door's bounds are the twin's within 10: it fills the doorway as the twin did)
say('shut doorways with a real door to swap in', len(shut))


def on_navmesh(ck, x, y, z):
    m = pr.navmesh.get(ck)
    if not m:
        return None
    vs = m['verts']
    for t in m['tris']:
        a, b, c = (vs[i] for i in t[:3])
        if abs((a[2] + b[2] + c[2]) / 3.0 - z) > 120:
            continue
        def s(p, q, r_): return (p[0] - r_[0]) * (q[1] - r_[1]) - (q[0] - r_[0]) * (p[1] - r_[1])
        d = (s((x, y), a, b), s((x, y), b, c), s((x, y), c, a))
        if not (min(d) < 0 < max(d)):
            return True
    return False


bigs = [(r['p'], obnd(r['base']), float(r.get('s') or 1.0)) for rk, (ck, r) in refs.items()
        if ck in city and r.get('p') and r['p'][2] > -20000 and name(r.get('base') or '')[1] == 'STAT']
bigs = [(p, b, s) for p, b, s in bigs if (b[3] - b[0]) * (b[4] - b[1]) * s * s > 300 * 300]


def outside_arrival(ck, r):
    """A step in front of the door on its outside, facing out: the side away from the middle of the building it stands on
    (doorout: the city's navmesh covers the floors inside hollow buildings too); on the navmesh is asked of it after."""
    b = obnd(r['base'])
    s = float(r.get('s') or 1.0)
    rz = r['p'][5]
    c, sn = math.cos(rz), math.sin(rz)
    lx, ly = (1.0, 0.0) if (b[3] - b[0]) < (b[4] - b[1]) else (0.0, 1.0)
    nx, ny = lx * c + ly * sn, -lx * sn + ly * c
    foot = r['p'][2] + b[2] * s

    def cell_at(x, y):
        k = (int(x // 4096), int(y // 4096))
        return gd.key(gd.grid(city_w)[k]) if k in gd.grid(city_w) else ck
    sg = BLD.outward(r['p'], (nx, ny))
    if sg is None:
        sg = max((1, -1), key=lambda g: on_navmesh(cell_at(r['p'][0] + g * nx * STEP, r['p'][1] + g * ny * STEP),
                                                    r['p'][0] + g * nx * STEP, r['p'][1] + g * ny * STEP, foot))
    for step in (STEP, 150.0, 200.0, 260.0):           # (the navmesh outside starts a little off the wall)
        x, y = r['p'][0] + sg * nx * step, r['p'][1] + sg * ny * step
        m = on_navmesh(cell_at(x, y), x, y, foot)
        if m:
            break
    else:
        x, y = r['p'][0] + sg * nx * STEP, r['p'][1] + sg * ny * STEP
    return [round(x, 2), round(y, 2), round(foot + 8.0, 2), 0.0, 0.0, round(math.atan2(sg * nx, sg * ny) % math.tau, 4)], m


sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import doorout  # noqa: E402
import townbuild, restyleset, modelsets  # noqa: E402
modelsets._all_sets()
_cat = townbuild.load(gd, server.kits_folder())
_boxes = {b['key']: b['box'] for b in _cat}
_byedid = {b['edid']: b for b in _cat}
for _g, _piece in restyleset.REPLACES.items():
    _k = modelsets.record_of(pr, _piece)
    if _k and _g in _byedid:
        _boxes[_k] = _byedid[_g]['box']
BLD = doorout.Buildings(refs, obnd, name, city, boxes=_boxes)


ops, used, report, unmatched = [], set(), [], []
cleared = set()
cands = [(frk, fck, fr, None) for frk, fck, fr in free] + list(shut)
keep = {c[0] for c in cands}
for kind, rk, ck, copy_rk, inside, spot in jobs:
    best = None
    for d, frk, fck, fr, real in sorted((math.hypot(fr['p'][0] - spot[0], fr['p'][1] - spot[1]), frk, fck, fr, real) for frk, fck, fr, real in cands
                                        if frk not in used and math.hypot(fr['p'][0] - spot[0], fr['p'][1] - spot[1]) < REACH):
        if outside_arrival(fck, dict(fr, base=real) if real else fr)[1]:     # (only a doorway one comes out of onto the city's navmesh)
            best = (d, frk, fck, fr, real)
            break
    if best is None or not inside:
        unmatched.append((kind, rk, ck, 'no free or shut city door within %d' % REACH if best is None else 'no inside arrival known'))
        continue
    d, frk, fck, fr, real = best
    used.add(frk)
    if real:
        ops.append({'op': 'swap', 'cell': fck, 'ref': frk, 'base': real})
        fr = dict(fr, base=real)
    out_p, on_mesh = outside_arrival(fck, fr)
    ops.append({'op': 'tel', 'cell': ck, 'ref': rk, 'tel': {'door': frk, 'p': out_p}})
    ops.append({'op': 'tel', 'cell': fck, 'ref': frk, 'tel': {'door': rk, 'p': list(inside)}})
    if (fr.get('props') or {}).get('lock'):
        ops.append({'op': 'props', 'cell': fck, 'ref': frk, 'props': {'lock': None}})
    out_v = (out_p[0] - fr['p'][0], out_p[1] - fr['p'][1])
    ln = math.hypot(*out_v) or 1.0
    gone = doorout.in_front(fr['p'], obnd(fr['base']), float(fr.get('s') or 1.0), (out_v[0] / ln, out_v[1] / ln), refs, name, obnd, city, skip=keep)
    for gck, grk, ge in gone:
        if grk not in cleared:
            cleared.add(grk)
            ops.append({'op': 'remove', 'cell': gck, 'ref': grk})
    report.append({'cleared': [g[2] for g in gone], 'kind': kind, 'place': ck, 'place_door': rk, 'city_door': frk, 'city_door_is': name(real or fr['base'])[0],
                   'was_shut': bool(real), 'from_old_spot': round(d), 'outside_on_navmesh': on_mesh})
for kind, rk, ck, copy_rk, inside, spot in jobs:                     # (B's copies back as stage_ops makes them)
    if kind == 'B' and copy_rk in refs:
        cck, cr = refs[copy_rk]
        if cr.get('tel'):
            ops.append({'op': 'tel', 'cell': cck, 'ref': copy_rk, 'tel': None})
        if not ((cr.get('props') or {}).get('lock') or {}).get('level'):
            ops.append({'op': 'props', 'cell': cck, 'ref': copy_rk, 'props': {'lock': {'level': 255, 'key': '', 'leveled': False}}})
ds = sorted(x['from_old_spot'] for x in report)
say('linked', len(report), '| A', sum(1 for x in report if x['kind'] == 'A'), '| B', sum(1 for x in report if x['kind'] == 'B'),
    '| city door from the old spot: median', ds[len(ds) // 2] if ds else None, 'most', ds[-1] if ds else None,
    '| outside arrival on navmesh', sum(1 for x in report if x['outside_on_navmesh']), '| ops', len(ops))
say('not matched', unmatched)
json.dump({'linked': report, 'unmatched': unmatched}, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ways_in_report.json'), 'w'), indent=1)
if not ops:
    sys.exit('nothing to do: run already?')
if len(report) > 80:
    sys.exit('more places than the rehearsal found: stopping')
if not REAL:
    say('dry run: nothing saved (the list: ways_in_report.json)')
    sys.exit(0)
if project.modified(src) != was:
    sys.exit('Waikiki changed while this ran: stopping')
back = os.path.join(HOME, 'backups', 'Waikiki before ways in %s' % time.strftime('%m%d-%H%M'))
os.makedirs(back)
for f in (src, os.path.splitext(src)[0] + '.changes'):
    if os.path.isfile(f):
        shutil.copy2(f, back)
say('backup', back)
cells = {o['cell'] for o in ops}
current = {k: m for k, m in pr.navmesh.items() if k in cells and m.get('sig') == doorswap.sig_of(gd, pr, k)}
label = 'Ways in from the city for places reached only through the hotels\' small worlds'
pr.apply(label, ops)
nav = [{'op': 'navmesh', 'cell': k, 'mesh': dict(m, sig=doorswap.sig_of(gd, pr, k))} for k, m in current.items()]
if nav:
    pr.apply(label, nav, merge=True)
say('applied and saved | navmeshes kept current', len(nav))
# --- checks ---
refs = {rk: (ck, r) for ck, c in pr.cells.items() for rk, r in (c.get('refs') or {}).items() if not r.get('removed')}
bad = []
for x in report:
    if not x['outside_on_navmesh']:
        bad.append('%s: outside arrival off the navmesh' % x['place'])
    a = refs[x['place_door']][1].get('tel') or {}
    b = refs[x['city_door']][1].get('tel') or {}
    if a.get('door') != x['city_door'] or b.get('door') != x['place_door']:
        bad.append('%s not linked both ways' % x['place_door'])
    if (refs[x['city_door']][1].get('props') or {}).get('lock'):
        bad.append('%s still locked' % x['city_door'])
same = doorswap.same_arrivals(pr)
if same:
    bad.append('pairs arriving at one spot: %s' % same)
left = [rk for rk, ck, to in place_doors() if refs[to][0] in views]
say('places whose way out still leads into a hotel world', len(left), left[:10])
import health
h = health.check_mod(server)
un = next((g['count'] for g in h['groups'] if g['title'] == 'Places nothing leads to'), 0)
say('health: places nothing leads to', un, '| summary', json.dumps(h['summary']))
want = UNREACHED_BEFORE - sum(1 for x in report if x['kind'] == 'A')
if un > want:
    bad.append('places nothing leads to: %d (over %d)' % (un, want))
say('CHECKS: ' + ('all good' if not bad else 'PROBLEMS: ' + '; '.join(bad)))
