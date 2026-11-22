"""cut_doorways_into_waikiki.py [real] [--home H] [--app A] [--before DIR]: run after ways_in_into_waikiki.py. The places it
left with no way in from the city (no spare door within its reach: 22 on Waikiki of 08:26) get a doorway of their own on a
building of their kind near where their old copy stood (the user, 22 Nov 2026: "New doorways nearby").

A doorway is one the building really has: a spot in townbuild's catalogue (where the game stands its doors and shuts its other
doorways), on a game building or on a FOLab building made in its frame (restyleset.REPLACES), with no door in it now. What
shuts it (a door's static twin) is swapped for a real door of the same bounds; an empty one gets the catalogue's door. Kind:
a House place a house or apartments, a Shop a shop, Works industrial. Linked both ways (inside: where the old copy's link
arrived; outside: a step in front of the door on the side on the city's navmesh, facing out); the touched cells' navmeshes
made again (navbuild.generate_area) and each outside arrival checked on the new navmesh. One Undo. Written by the doors
session for the story session. Dry run without `real`; backup; refuses while the game runs (not on a FOLabScratch home)."""
import collections, json, math, os, shutil, struct, subprocess, sys, time

ARGS = sys.argv[1:]
REAL = 'real' in ARGS


def opt(name, default):
    return ARGS[ARGS.index(name) + 1] if name in ARGS else default


HOME = opt('--home', r'C:\Users\AMD RYZEN\Claude Code Projects\FOLab\packaging\out\FOLab')
APP = opt('--app', r'C:\Users\AMD RYZEN\Claude Code Projects\FOLab\app')
BEFORE = opt('--before', os.path.join(HOME, 'backups', 'Waikiki before view doors 1122-0754'))
REACH = 3000.0
STEP = 110.0
HERE = os.path.dirname(os.path.abspath(__file__))
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

import gamedata, project, server, doorswap, doorset, hotelinside, recordio, townbuild, restyleset, modelsets, navbuild, health  # noqa: E402
sys.path.insert(0, HERE)
import doorout  # noqa: E402
src = os.path.join(project.PROJECTS_DIR, 'Waikiki.json')
was = project.modified(src)
say('mod', src, time.strftime('%d %b %H:%M', time.localtime(was)), '| app', APP)
server.not_while_playing = lambda: None
server.GD = gamedata.GameData(); server.BR = None
pr = project.Project.open('Waikiki'); server.load_game(pr); server.PR = pr
gd = server.GD
modelsets._all_sets()
name = doorswap.Names(gd, pr)
worlds = {gd.edid(w): w for w in gd.worlds()}
city_w = worlds[doorset.CITY]
cgrid = gd.grid(city_w)
city = {gd.key(c) for c in cgrid.values()}
views = set()
for hotel, v in hotelinside.VIEWS.items():
    views |= {gd.key(c) for c in gd.grid(worlds[v['world']]).values()}
outside = city | views


def load_refs():
    return {rk: (ck, r) for ck, c in pr.cells.items() for rk, r in (c.get('refs') or {}).items() if not r.get('removed')}


refs = load_refs()


def city_cell(x, y):
    c = cgrid.get((int(x // 4096), int(y // 4096)))
    return gd.key(c) if c is not None else None


def obnd(base):
    try:
        if base.startswith('+'):
            s = next(x for x in pr.records[base]['subs'] if x['tag'] == 'OBND')
            return [int(f['value']) for f in s['fields'] if 'name' in f]
        return list(struct.unpack('<6h', gd.fields(gd.from_key(base))['OBND'][:12]))
    except Exception:
        return None


def on_navmesh(ck, x, y, z):
    m = pr.navmesh.get(ck)
    if not m:
        return False
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


# --- the places still with no way in from the city ---
def place_doors():
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
HOTEL_OWN = ('FOLabLift', 'FOLabDoorRoyalHawaiian', 'FOLabDoorMoana', 'FOLabDoorKilauea', 'OffDoorHotelSmL01', 'HotelElevatorDoor')
reached = {refs[r['tel']['door']][0] for rk, (ck, r) in refs.items() if (r.get('tel') or {}).get('door') in refs and refs[r['tel']['door']][0] != ck}
left = []          # (kind, place door, its cell, old copy, inside arrival, spot, place's editor ID)
for rk, ck, to in sorted(place_doors()):
    rec = pr.records.get(ck) or {}
    edid = recordio.field(rec, 'EDID') if rec else ''
    tck = refs[to][0]
    if tck in city:
        if ck in reached or any(x[2] == ck for x in left):
            continue
        o = old.get(rk)
        oto = ((o[1].get('tel') or {}).get('door')) if o else None
        if not oto or old.get(oto, (None,))[0] not in views:
            continue
        copy = old[oto][1]
        inside = (copy.get('tel') or {}).get('p') if (copy.get('tel') or {}).get('door') == rk else None
        left.append(('A', rk, ck, oto, inside, copy['p'], edid))
    elif tck in views:
        e = name(refs[to][1].get('base') or '')[0] or ''
        if any(e.startswith(h) for h in HOTEL_OWN):
            continue                                # (a hotel's own lift or lookout: rightly in its small world)
        copy = refs[to][1]
        inside = (copy.get('tel') or {}).get('p') if (copy.get('tel') or {}).get('door') == rk else None
        left.append(('B', rk, ck, to, inside, copy['p'], edid))
KIND = {'House': ('house', 'apartments'), 'Shop': ('shop',), 'Works': ('industrial',), 'Office': ('civic', 'apartments', 'shop')}     # (the catalogue files office buildings, NVOfficeBldg, as apartments)


def kind_of(edid):
    rest = edid[len('FOLabWaikiki'):] if edid.startswith('FOLabWaikiki') else edid
    return next((k for k in sorted(KIND, key=len, reverse=True) if rest.startswith(k)), None)


say('places still with no way in', len(left), dict(collections.Counter(kind_of(x[6]) for x in left)))

# --- the doorways buildings really have, with no door in them now ---
cat = townbuild.load(gd, server.kits_folder())
bykey = {b['key']: b for b in cat}
byedid = {b['edid']: b for b in cat}
for g, piece in restyleset.REPLACES.items():       # (FOLab's buildings made in a game building's frame: its doorways)
    k = modelsets.record_of(pr, piece)
    if k and g in byedid:
        bykey[k] = byedid[g]
BLD = doorout.Buildings(refs, obnd, name, city, boxes={k: b['box'] for k, b in bykey.items()})
game_doors = [(gd.key(f), gd.edid(f)) for f, (_i, rec) in gd.forms.items() if rec.tag == 'DOOR']
door_by_name = {e.lower(): k for k, e in game_doors}
door_bounds = [(k, obnd(k)) for k, _e in game_doors]
door_bounds = [(k, b) for k, b in door_bounds if b and any(b)]


def real_door(base):
    """A DOOR for what shuts a doorway: itself if a door, its twin by name, else one of the same bounds within 10."""
    e, t = name(base)
    if t == 'DOOR':
        return base
    if t != 'STAT' or not e:
        return None
    if e.lower().endswith('static') and e.lower()[:-6] in door_by_name:
        return door_by_name[e.lower()[:-6]]
    b = obnd(base)
    if not b or not any(b):
        return None
    best = min(((max(abs(x - y) for x, y in zip(b, d)), k) for k, d in door_bounds), default=None)
    return best[1] if best and best[0] <= 10 else None


grid = {}
for rk, (ck, r) in refs.items():
    if ck in city and r.get('p') and r['p'][2] > -20000:
        grid.setdefault((int(r['p'][0] // 512), int(r['p'][1] // 512)), []).append((rk, ck, r))


def near(x, y, reach):
    for gx in range(-1, 2):
        for gy in range(-1, 2):
            for item in grid.get((int(x // 512) + gx, int(y // 512) + gy), ()):
                if math.hypot(item[2]['p'][0] - x, item[2]['p'][1] - y) < reach:
                    yield item


def in_frame(r, s, x, y, z, rz_local):
    rz = r['p'][5]
    c, sn = math.cos(rz), math.sin(rz)
    return [round(r['p'][0] + (x * c + y * sn) * s, 2), round(r['p'][1] + (-x * sn + y * c) * s, 2), round(r['p'][2] + z * s, 2),
            0.0, 0.0, round((rz + rz_local) % math.tau, 4)]


seen_twins = set()
spare = []          # (family, building ref, building edid, door p, door base, the static it replaces (rk, ck, r) or None, scale)
for rk, (ck, r) in refs.items():
    b = bykey.get(r.get('base'))
    if ck not in city or not b or not r.get('p') or r['p'][2] < -20000:
        continue
    s = float(r.get('s') or 1.0)
    for e in b['doors'] + b['shut']:
        if e.get('board'):
            continue
        p = in_frame(r, s, e['x'], e['y'], e['z'], e['rz'])
        here = [it for it in near(p[0], p[1], 60) if it[0] != rk]
        if any(name(it[2].get('base') or '')[1] == 'DOOR' for it in here):
            continue                                     # (a door is in it already)
        twin = next((it for it in here if real_door(it[2].get('base') or '')), None)
        base = real_door(twin[2]['base']) if twin else real_door(e['base'])
        if not base:
            continue
        if twin:
            if twin[0] in seen_twins:
                continue                                 # (two of the catalogue's doorways at one static: one door)
            seen_twins.add(twin[0])
            p, s2 = list(twin[2]['p']), float(twin[2].get('s') or 1.0)
        else:
            s2 = s * float(e.get('s') or 1.0)
        spare.append((b['family'], rk, b['edid'], p, base, twin, s2))
say('spare doorways on the city\'s buildings', len(spare), dict(collections.Counter(x[0] for x in spare)))
bigs = []
for rk, (ck, r) in refs.items():
    if ck in city and r.get('p') and r['p'][2] > -20000 and name(r.get('base') or '')[1] == 'STAT':
        b = obnd(r['base'])
        if b and (b[3] - b[0]) * (b[4] - b[1]) * float(r.get('s') or 1.0) ** 2 > 300 * 300:
            bigs.append(r['p'])


def outside_arrival(door, normal=None):
    """A step in front of the door on its outside, facing out: along `normal` (a hung door's wall), else the side away from
    the middle of the building it stands on (doorout); on the city's navmesh is asked of it after."""
    b = obnd(door['base']) or [-60, -10, 0, 60, 10, 200]
    s = float(door.get('s') or 1.0)
    rz = door['p'][5]
    c, sn = math.cos(rz), math.sin(rz)
    lx, ly = (1.0, 0.0) if (b[3] - b[0]) < (b[4] - b[1]) else (0.0, 1.0)
    nx, ny = lx * c + ly * sn, -lx * sn + ly * c
    foot = door['p'][2] + b[2] * s
    if normal is not None:
        sg = 1 if nx * normal[0] + ny * normal[1] >= 0 else -1
    else:
        sg = BLD.outward(door['p'], (nx, ny))
        if sg is None:
            sg = max((1, -1), key=lambda g: on_navmesh(city_cell(door['p'][0] + g * nx * STEP, door['p'][1] + g * ny * STEP),
                                                        door['p'][0] + g * nx * STEP, door['p'][1] + g * ny * STEP, foot))
    for step in (STEP, 150.0, 200.0, 260.0):           # (the navmesh outside starts a little off the wall)
        x, y = door['p'][0] + sg * nx * step, door['p'][1] + sg * ny * step
        m = on_navmesh(city_cell(x, y), x, y, foot)
        if m:
            break
    else:
        x, y = door['p'][0] + sg * nx * STEP, door['p'][1] + sg * ny * STEP
    return [round(x, 2), round(y, 2), round(foot + 8.0, 2), 0.0, 0.0, round(math.atan2(sg * nx, sg * ny) % math.tau, 4)], m




# --- else a door hung flat on a wall of a building of its kind, as the game hangs most of its own ---
import nif, kitindex
_tris = {}


def tris_of(model):
    if model not in _tris:
        try:
            _tris[model] = kitindex.triangles(nif.mesh_from_nif(gd.read_file('meshes' + chr(92) + model)))
        except Exception:
            _tris[model] = []
    return _tris[model]


def ray_y(tris, u, z, along, sign, start):
    """The first wall a ray meets, cast in the building's frame from `start` (outside) inward along axis `along` (0 x, 1 y)
    in direction -sign, at the other horizontal coordinate u and height z: the coordinate along `along`, or None."""
    best = None
    other = 1 - along
    for a, b, c in tris:
        # (the ray: P = (u on other, z), varying along `along`)
        ax, ay = a[other], a[2]; bx, by = b[other], b[2]; cx, cy = c[other], c[2]
        den = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if abs(den) < 1e-9:
            continue
        w1 = ((by - cy) * (u - cx) + (cx - bx) * (z - cy)) / den
        w2 = ((cy - ay) * (u - cx) + (ax - cx) * (z - cy)) / den
        w3 = 1 - w1 - w2
        if w1 < 0 or w2 < 0 or w3 < 0:
            continue
        v = w1 * a[along] + w2 * b[along] + w3 * c[along]
        if (v - start) * sign > 0:
            continue                             # (behind where the ray starts)
        if best is None or abs(v - start) < abs(best - start):
            best = v
    return best


def flush_spots(brk, r, b):
    """Doorways one may hang a door on: the middle (then a quarter either side) of each side of the building's box that has
    no doorway of the catalogue's, where the wall is one flat face behind a door's width and height and no deeper than
    DEEP in from the box (no porch or overhang in front of it). (door p, base, scale) in the world, nearest first."""
    model = gd.describe(gd.from_key(r['base']))[3] if not r['base'].startswith('+') else None
    if not model:
        rec = pr.records.get(r['base']) or {}
        model = recordio.field(rec, 'MODL') if rec else None
    tris = tris_of(model) if model else []
    if not tris:
        return []
    entries = [e for e in b['doors'] + b['shut'] if not e.get('board')]
    src_e = next((e for e in entries if real_door(e['base'])), None)
    if not src_e:
        return []
    base = real_door(src_e['base'])
    db = obnd(base) or [-60, -10, 0, 60, 10, 200]
    sb = obnd(src_e['base']) or db
    floor = src_e['z'] + sb[2]                          # (the doorway's floor in the building's frame)
    thin_x = (db[3] - db[0]) < (db[4] - db[1])
    width = (db[4] - db[1]) if thin_x else (db[3] - db[0])
    height = db[5] - db[2]
    x0, y0, _z0, x1, y1, _z1 = b['box']
    out = []
    used_sides = set()
    for e in entries:                                   # (sides that have a doorway already)
        dists = {(1, -1): e['y'] - y0, (1, 1): y1 - e['y'], (0, -1): e['x'] - x0, (0, 1): x1 - e['x']}
        used_sides.add(min(dists, key=dists.get))
    for along, sign in ((1, -1), (1, 1), (0, -1), (0, 1)):
        if (along, sign) in used_sides:
            continue
        lo, hi = (x0, x1) if along == 1 else (y0, y1)
        start = (y0 - 50 if sign < 0 else y1 + 50) if along == 1 else (x0 - 50 if sign < 0 else x1 + 50)
        for frac in (0.5, 0.3, 0.7):
            u = lo + (hi - lo) * frac
            if u - width / 2 < lo + 40 or u + width / 2 > hi - 40:
                continue
            hits = []
            for du in (-width / 2 + 6, 0, width / 2 - 6):
                for dz in (12, height / 2, height - 12):
                    hits.append(ray_y(tris, u + du, floor + dz, along, sign, start))
            if any(h is None for h in hits) or max(hits) - min(hits) > 4:
                continue                                 # (not one flat wall behind the whole door)
            wall = sum(hits) / len(hits)
            face = (y0 if sign < 0 else y1) if along == 1 else (x0 if sign < 0 else x1)
            if abs(wall - face) > DEEP:
                continue                                 # (a wall deep inside the box: a porch or overhang stands in front of it)
            # the door: its thin axis along this side's outward normal (rz_local turns local x to -y, y to +x), its back on the wall
            rz_local = 0.0 if (thin_x and along == 0) or (not thin_x and along == 1) else math.pi / 2
            t_lo, t_hi = (db[0], db[3]) if thin_x else (db[1], db[4])
            mid = (t_lo + t_hi) / 2.0
            off = -mid if (along == 1 and thin_x) else mid     # (where the door's thin middle lands from its origin, along the normal)
            centre = wall + sign * ((t_hi - t_lo) / 2.0 + 1.0)
            origin_n = centre - off
            cx, cy = (u, origin_n) if along == 1 else (origin_n, u)
            s = float(r.get('s') or 1.0)
            p = in_frame(r, s, cx, cy, floor - db[2], rz_local)
            fn = (0.0, float(sign)) if along == 1 else (float(sign), 0.0)
            brz = r['p'][5]
            wn = (fn[0] * math.cos(brz) + fn[1] * math.sin(brz), -fn[0] * math.sin(brz) + fn[1] * math.cos(brz))
            out.append((p, base, s, (along, sign, frac), wn))
            break
    return out


DEEP = 60.0


def inside_from_navmesh(rk, ck):
    """Where one arrives in a place by its door when no link says: a step in front of the door, on the side on the place's
    own navmesh, facing in."""
    r = refs[rk][1]
    b = obnd(r['base']) or [-60, -10, 0, 60, 10, 200]
    rz = r['p'][5]
    c, sn = math.cos(rz), math.sin(rz)
    lx, ly = (1.0, 0.0) if (b[3] - b[0]) < (b[4] - b[1]) else (0.0, 1.0)
    nx, ny = lx * c + ly * sn, -lx * sn + ly * c
    foot = r['p'][2] + b[2] * float(r.get('s') or 1.0)
    for sg in (1, -1):
        for step in (96, 140, 70):
            x, y = r['p'][0] + sg * nx * step, r['p'][1] + sg * ny * step
            if on_navmesh(ck, x, y, foot):
                return [round(x, 2), round(y, 2), round(foot + 8.0, 2), 0.0, 0.0, round(math.atan2(sg * nx, sg * ny) % math.tau, 4)]
    return None


left = [(k, rk, ck, cp, inside or inside_from_navmesh(rk, ck), spot, edid) for k, rk, ck, cp, inside, spot, edid in left]
buildings = [(rk, ck, r, bykey[r['base']]) for rk, (ck, r) in refs.items()
             if ck in city and r.get('base') in bykey and r.get('p') and r['p'][2] > -20000]
taken_buildings = set()
ops, used, report, unmatched = [], set(), [], []
cleared = set()
keep = {x[5][0] for x in spare if x[5]}
for kind, rk, ck, copy_rk, inside, spot, edid in sorted(left, key=lambda j: j[6]):
  for REACH in (3000.0, 6000.0, 9000.0):
    fams = KIND.get(kind_of(edid), ())
    best = None
    for d, i in sorted((math.hypot(x[3][0] - spot[0], x[3][1] - spot[1]), i) for i, x in enumerate(spare) if i not in used and x[0] in fams):
        if d >= REACH:
            break
        if outside_arrival({'base': spare[i][4], 'p': spare[i][3], 's': spare[i][6]})[1]:   # (only onto the city's navmesh)
            best = (d, i)
            break
    flush = None
    if best is None and inside:
        for d, brk, bck, br, b in sorted((math.hypot(r['p'][0] - spot[0], r['p'][1] - spot[1]), brk, bck, r, b) for brk, bck, r, b in buildings
                                         if b['family'] in fams):
            if d > REACH:
                break
            for p, base, s, side, wn in flush_spots(brk, br, b):
                if (brk, side[:2]) in taken_buildings:
                    continue                     # (one new door a wall)
                o, on_mesh = outside_arrival({'base': base, 'p': p, 's': s}, wn)
                if on_mesh and not any(name(it[2].get('base') or '')[1] == 'DOOR' for it in near(p[0], p[1], 150)):
                    flush = (d, brk, b, p, base, s, side, wn)
                    break
            if flush:
                break
    if best is not None or flush is not None or not inside:
        break
  if best is None and flush is None or not inside:
      unmatched.append((kind, edid, rk, 'no %s building within %d with a doorway or a wall to hang a door on' % ('/'.join(fams) or '?', REACH) if inside else 'no inside arrival known'))
      continue
  if best is not None:
      d, i = best
      used.add(i)
      fam, brk, bed, p, base, twin, s = spare[i]
  else:
      d, brk, b, p, base, s, side, wn = flush
      taken_buildings.add((brk, side[:2]))
      fam, bed, twin = b['family'], b['edid'] + ' (hung on its wall, side %s)' % (side,), None
  cell = city_cell(p[0], p[1])
  if twin:
      door_ref, door_ck = twin[0], twin[1]
      ops.append({'op': 'swap', 'cell': door_ck, 'ref': door_ref, 'base': base})
  else:
      tag = 'doorway_%d' % len(report)
      ops.append({'op': 'add', 'cell': cell, 'base': base, 'p': p, 's': s, 'name': tag, 'extra': {'persistent': True}})
      door_ref, door_ck = '$' + tag, cell
  out_p, on_mesh = outside_arrival({'base': base, 'p': p, 's': s}, wn if best is None else None)
  ops.append({'op': 'tel', 'cell': ck, 'ref': rk, 'tel': {'door': door_ref, 'p': out_p}})
  ops.append({'op': 'tel', 'cell': door_ck, 'ref': door_ref, 'tel': {'door': rk, 'p': list(inside)}})
  out_v = (out_p[0] - p[0], out_p[1] - p[1])
  ln = math.hypot(*out_v) or 1.0
  gone = doorout.in_front(p, obnd(base) or [-60, -10, 0, 60, 10, 200], s, (out_v[0] / ln, out_v[1] / ln), refs, name, obnd, city, skip=keep)
  for gck, grk, ge in gone:
      if grk not in cleared:
          cleared.add(grk)
          ops.append({'op': 'remove', 'cell': gck, 'ref': grk})
  report.append({'cleared': [g[2] for g in gone], 'kind': kind, 'place': edid, 'place_door': rk, 'building': bed, 'building_ref': brk, 'family': fam, 'door': name(base)[0],
                 'swapped_static': bool(twin), 'from_old_spot': round(d), 'cell': door_ck, 'door_p': p, 'out': out_p,
                 'outside_on_navmesh_before': on_mesh, 'door_ref': door_ref})
for kind, rk, ck, copy_rk, inside, spot, edid in left:            # (B's copies back as stage_ops makes them)
    if kind == 'B' and copy_rk in refs and any(x['place_door'] == rk for x in report):
        cck, cr = refs[copy_rk]
        if cr.get('tel'):
            ops.append({'op': 'tel', 'cell': cck, 'ref': copy_rk, 'tel': None})
        if not ((cr.get('props') or {}).get('lock') or {}).get('level'):
            ops.append({'op': 'props', 'cell': cck, 'ref': copy_rk, 'props': {'lock': {'level': 255, 'key': '', 'leveled': False}}})
ds = sorted(x['from_old_spot'] for x in report)
say('doorways given', len(report), '| a static swapped for its door', sum(x['swapped_static'] for x in report),
    '| a door stood in an empty doorway', sum(not x['swapped_static'] for x in report),
    '| from the old spot: median', ds[len(ds) // 2] if ds else None, 'most', ds[-1] if ds else None, '| ops', len(ops))
for x in report:
    say('  ', x['place'], '->', x['building'], '(%s)' % x['family'], x['door'], 'swapped' if x['swapped_static'] else 'new', x['from_old_spot'])
say('not matched', unmatched)
out_json = os.path.join(HERE, 'cut_doorways_report.json')
json.dump({'linked': report, 'unmatched': unmatched}, open(out_json, 'w'), indent=1, default=str)
if not ops:
    sys.exit('nothing to do: run already?')
if not REAL:
    say('dry run: nothing saved (the list: cut_doorways_report.json)')
    sys.exit(0)
if project.modified(src) != was:
    sys.exit('Waikiki changed while this ran: stopping')
back = os.path.join(HOME, 'backups', 'Waikiki before doorways %s' % time.strftime('%m%d-%H%M'))
os.makedirs(back)
for f in (src, os.path.splitext(src)[0] + '.changes'):
    if os.path.isfile(f):
        shutil.copy2(f, back)
say('backup', back)
label = 'Doorways of their own for places with no way in from the city'
pr.apply(label, ops)
say('applied and saved')
cells = sorted({x['cell'] for x in report})
t1 = time.time()
nops, nrep = navbuild.generate_area(gd, pr, cells)
pr.apply(label, nops, merge=True)
say('navmeshes made again for %d cells in %.0fs' % (len(cells), time.time() - t1), {k: nrep.get(k) for k in ('cells', 'doors', 'doors_missed', 'neighbours', 'empty')})
refs = load_refs()
bad = []
for x in report:
    dref = x['door_ref']
    if dref.startswith('$'):
        dref = next((rk for rk, (ck, r) in refs.items() if (r.get('tel') or {}).get('door') == x['place_door'] and ck in city), None)
        x['door_ref'] = dref
    a = refs[x['place_door']][1].get('tel') or {}
    b = (refs.get(dref) or (None, {}))[1].get('tel') or {}
    if not dref or a.get('door') != dref or b.get('door') != x['place_door']:
        bad.append('%s not linked both ways' % x['place'])
    o = x['out']
    x['outside_on_navmesh'] = on_navmesh(city_cell(o[0], o[1]), o[0], o[1], o[2] - 8)
    if not x['outside_on_navmesh']:
        bad.append('%s: outside arrival off the new navmesh' % x['place'])
same = doorswap.same_arrivals(pr)
if same:
    bad.append('pairs arriving at one spot: %s' % same)
h = health.check_mod(server)
un = next((g['count'] for g in h['groups'] if g['title'] == 'Places nothing leads to'), 0)
say('health: places nothing leads to', un, '| summary', json.dumps(h['summary']))
json.dump({'linked': report, 'unmatched': unmatched, 'health_unreached': un}, open(out_json, 'w'), indent=1, default=str)
say('CHECKS: ' + ('all good' if not bad else 'PROBLEMS: ' + '; '.join(bad)))
