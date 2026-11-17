"""Buildings put up on a real map's plots: the game's own stand-alone buildings, each fitted to an OpenStreetMap outline and facing the street.

osmplace.py levels each building's plot (a pad) and keeps its outline in the marker layer; this stands buildings on those pads.

The catalogue is measured from the game, once per game files (buildings.json beside the kit index):

  which      a STAT under an architecture folder (or a mobile home, DWELLING) that the game places outdoors on its own: in most of its placements no other
             building-sized piece overlaps it (Westside's wall runs and the Strip's façades are parts of something bigger, so they're
             left out), whose editor ID says what kind of building it is (FAMILY_WORDS). City-block kit pieces (BLD03...), signs,
             walls, roads, rubble, low-detail copies and far-off stand-ins are left out by name.
  footprint  the mesh's own box, in its frame.
  doors      the load doors the game set on it, in its frame (from the placement with the most): its front is where they are.
  shut       what the game puts in its other doorways, the ones nobody goes through: a door-shaped static, boards over it, a
             door that leads nowhere ('door': it is placed locked). Without them a building stands with holes for doors.
  ground     how the game's ground stands against it: at its middle (where it's set on a pad) and the lowest and highest at its
             corners over every placement (how far a corner may lie off level before ground shows through a floor or under a wall).
  family     what it is, by its editor ID's words (house, shop, apartments, civic, industrial), matched to OSM's building=*.

Fitting, for each plot that has a pad: the outline's smallest enclosing rectangle; its street side is the side nearest a road the
mod has laid (a long side when there are none); buildings stand in a row along it, fronts to the street, the best for the plot's
depth and width and its kind first, as many as fill it; a deep plot gets a second row facing the other way. Nothing may overlap a
road piece or another building; small things the mod placed on the plot (scatter, plants) are taken away. Doors go where the
game had them on that building, locked 'needs a key' until something lies behind them.

    cat = townbuild.load(gd, folder)                   the catalogue
    ops, report = townbuild.plan(gd, pr, world, rows, cat, seed)   rows: the marker layer's buildings (osmplace.lay_pads)

Angles: the game turns a thing clockwise from above (rz); a point (lx, ly) in its frame is at
(lx cos rz + ly sin rz, -lx sin rz + ly cos rz) from its origin."""
import collections
import json
import math
import os
import random
import re
import struct

import kitindex
import landshape
import navbuild
import navmesh
import nif
import recordio
import roadgen

FORMAT = 10              # (buildings.json's layout: a file with another number is made again)
MIN_SIDE, MAX_SIDE = 300, 3600
DWELLING = re.compile(r'\\mobilehome[^\\]*\.nif$')   # (homes the game keeps with its vehicles, narrower than a building: trailer lots are full of them)
MIN_HIGH, MAX_HIGH = 220, 1700
ALONE = 0.6                # (in this share of its placements at least, nothing building-sized overlaps it)
OVERLAP_PART = 0.25        # (another big piece over this share of the smaller one's footprint makes them parts of one thing)
SETBACK = 32.0             # (a building's front stands this far inside the plot's street side)
GAP = 48.0                 # (between buildings in a row)
DEPTH_OVER = 1.3           # (a building may be this much deeper than its plot, plus SLACK: compressed plots are small)
WIDTH_OVER = 1.25
SLACK = 128.0
ROW_MIN = 300.0            # (a row stops when less frontage than this is left)
GROUND_OFF = 48.0          # (a corner's ground may lie this much further off level than the game ever had it)
GENERIC_USES = 3           # (a building the game places this many times or more is generic: it fills ordinary plots)
POI_AREA = 3000.0 * 3000.0 # (a plot this big stands out even unnamed)
KIND_PULL = 1.0            # (and one whose editor ID names what the file says it is: KIND_WORD)
LANDMARK_PULL = 0.6       # (how much a plot that stands out prefers a landmark that fits)
VARIETY = 0.45            # (each building costs this much more for every time it's up already, by the square root)
MAX_INSIDE_REFS = 900      # (a real place with more than this in it is too much to copy behind a building)
CLEAR_BELOW = 400.0      # (the mod's own things smaller than this across are taken off a plot a building stands on)
FLOAT_MOST = 48.0        # (however far the game once let the ground fall away under one, a trailer on a cliff's edge: the model's own underside no further over the ground than this, or it floats)
DRY = 8.0                # (ground lower than this is looked at for water over it)
DOOR_LOCK = {'props': {'lock': {'level': 255, 'key': '', 'leveled': False}}}
INSIDE_SHARE = 0.6         # (of ordinary buildings that have a real place behind them in the game, how many get one; plots that stand out always)
MAX_INSIDES = 300          # (places made in one go: each needs a navmesh, a few seconds)
INITIALLY_OFF = 0x800      # (a ref's record flag: off until something switches it on)
NOT_INSIDE = {'NPC_', 'CREA', 'LVLN', 'LVLC', 'KEYM', 'NOTE', 'TACT', 'TERM'}
PLACE_NAME = {'house': 'House', 'shop': 'Shop', 'apartments': 'Offices', 'civic': 'Hall', 'industrial': 'Works'}

# (words in an editor ID that say it isn't a building: signs, walls, roads, ruins in heaps, far-off stand-ins, parts)
NOT_A_BUILDING = re.compile(r'imposter|lod|_?wl$|rubble|crater|wall|sign|neon|highway|overpass|rail|pylon|tower|marquee|debris|pile|'
                            r'top|roof|platform|dock|bridge|fence|ramp|column|stair|coaster|curve|entrance|dino|sidewalk|decal|parking|'
                            r'int$|interior|tent|addon|wing|section|pillar|road|^rw|rwcorner|bld\d|duct|powerstation|truss|opt$|low$|dest\d|cabin\d|barrier')
# (what a building is, by its editor ID's words, first match; a STAT with none of these isn't taken)
FAMILY_WORDS = (('civic', ('police', 'school', 'townhall', 'town-hall', 'church', 'firehouse', 'trainstation', 'rangerstation', 'terminal', 'inspection')),
                ('industrial', ('warehouse', 'hangar', 'factory', 'garage', 'shed', 'barn', 'transmission', 'transmbldg', 'substation', 'barracks',
                                'quonset', 'greenhouse')),
                ('house', ('house', 'home', 'bungalow', 'shack', 'craftsman', 'usonian', 'trailer', 'fuselag')),
                ('shop', ('store', 'shop', 'liquor', 'pawn', 'gasstation', 'saloon', 'diner', 'bldgcorner', 'oldwest', 'market', 'wrangler', 'kiosk')),
                ('apartments', ('apartment', 'motel', 'hotel', 'casino', 'office')))
# (OSM's building=* to a family; anything else goes by size)
OSM_FAMILY = {'house': 'house', 'detached': 'house', 'semidetached_house': 'house', 'terrace': 'house', 'bungalow': 'house', 'cabin': 'house',
              'farm': 'house', 'hut': 'house', 'static_caravan': 'house', 'residential': 'apartments', 'apartments': 'apartments',
              'dormitory': 'apartments', 'hotel': 'apartments', 'commercial': 'shop', 'retail': 'shop', 'kiosk': 'shop', 'supermarket': 'shop',
              'office': 'apartments', 'industrial': 'industrial', 'warehouse': 'industrial', 'garage': 'industrial', 'garages': 'industrial',
              'shed': 'industrial', 'barn': 'industrial', 'farm_auxiliary': 'industrial', 'service': 'industrial', 'hangar': 'industrial',
              'church': 'civic', 'chapel': 'civic', 'school': 'civic', 'public': 'civic', 'civic': 'civic', 'government': 'civic',
              'hospital': 'civic', 'train_station': 'civic', 'fire_station': 'civic', 'university': 'civic', 'college': 'civic'}


# (OSM's building=* to a word in the editor ID of the game's building for it, within its family)
KIND_WORD = {'church': 'church', 'chapel': 'church', 'cathedral': 'church', 'school': 'school', 'police': 'police', 'fire_station': 'fire',
             'train_station': 'train', 'hotel': 'hotel', 'motel': 'motel', 'apartments': 'apartment', 'office': 'office', 'shed': 'shack',
             'hut': 'shack', 'cabin': 'shack', 'barn': 'barracks', 'warehouse': 'quonset', 'hangar': 'quonset', 'kiosk': 'kiosk',
             'retail': 'store', 'supermarket': 'store', 'garage': 'gasstation', 'service': 'gasstation', 'bungalow': 'bungalow', 'farm': 'ranch'}


def family_of(edid):
    e = edid.lower()
    for fam, words in FAMILY_WORDS:
        if any(w in e for w in words):
            return fam
    return 'any'


def turn(lx, ly, rz):
    """A point in a thing's frame (game turn rz, clockwise) in the world's, from its origin."""
    c, s = math.cos(rz), math.sin(rz)
    return lx * c + ly * s, -lx * s + ly * c


def corners(cx, cy, ux, uy, hu, hv):
    """A rectangle's corners: middle, its first axis (unit), half sizes along it and across."""
    vx, vy = -uy, ux
    return [(cx + ux * a * hu + vx * b * hv, cy + uy * a * hu + vy * b * hv) for a, b in ((-1, -1), (1, -1), (1, 1), (-1, 1))]


def overlap(a, b):
    """Two convex outlines (lists of points) overlap: no line between them (separating axes)."""
    for poly in (a, b):
        for i in range(len(poly)):
            x0, y0 = poly[i]
            x1, y1 = poly[(i + 1) % len(poly)]
            nx, ny = y0 - y1, x1 - x0
            pa = [nx * x + ny * y for x, y in a]
            pb = [nx * x + ny * y for x, y in b]
            if max(pa) <= min(pb) or max(pb) <= min(pa):
                return False
    return True


def hull(pts):
    pts = sorted(set((round(p[0], 2), round(p[1], 2)) for p in pts))
    if len(pts) < 3:
        return pts

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, up = [], []
    for p in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(up) >= 2 and cross(up[-2], up[-1], p) <= 0:
            up.pop()
        up.append(p)
    return lo[:-1] + up[:-1]


def rect_of(ring):
    """The outline's smallest enclosing rectangle: (middle x, y, angle of its first axis (radians, anticlockwise from east), length along it, across)."""
    h = hull(ring)
    best = None
    for i in range(len(h)):
        x0, y0 = h[i]
        x1, y1 = h[(i + 1) % len(h)]
        a = math.atan2(y1 - y0, x1 - x0)
        ux, uy = math.cos(a), math.sin(a)
        us = [x * ux + y * uy for x, y in h]
        vs = [-x * uy + y * ux for x, y in h]
        area = (max(us) - min(us)) * (max(vs) - min(vs))
        if best is None or area < best[0]:
            mu, mv = (max(us) + min(us)) / 2, (max(vs) + min(vs)) / 2
            best = (area, mu * ux - mv * uy, mu * uy + mv * ux, a, max(us) - min(us), max(vs) - min(vs))
    if best is None:
        xs, ys = [p[0] for p in ring], [p[1] for p in ring]
        return ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, 0.0, max(xs) - min(xs), max(ys) - min(ys))
    return best[1:]


# ---------- the catalogue, measured from the game ----------

def _foot(box, rz, pos):
    """A placed box's footprint corners in the world."""
    return [(pos[0] + wx, pos[1] + wy) for wx, wy in (turn(x, y, rz) for x, y in ((box[0], box[1]), (box[3], box[1]), (box[3], box[4]), (box[0], box[4])))]


def _area(poly):
    return abs(sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(poly, poly[1:] + poly[:1]))) / 2


def _clip(subject, clip):
    """The part of convex outline subject inside convex outline clip (both anticlockwise or both clockwise)."""
    def side(p, a, b):
        return (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])
    sign = 1 if sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(clip, clip[1:] + clip[:1])) > 0 else -1
    out = list(subject)
    for i in range(len(clip)):
        a, b = clip[i], clip[(i + 1) % len(clip)]
        inp, out = out, []
        for j in range(len(inp)):
            p, q = inp[j], inp[(j + 1) % len(inp)]
            pin, qin = side(p, a, b) * sign >= 0, side(q, a, b) * sign >= 0
            if pin:
                out.append(p)
            if pin != qin:
                dp, dq = side(p, a, b), side(q, a, b)
                t = dp / (dp - dq)
                out.append((p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t))
        if not out:
            return []
    return out


def _tel(gd, rfid):
    """A door's link: (the door it leads to, where you arrive: x, y, z, rx, ry, rz), or None."""
    try:
        x = gd.fields(rfid).get('XTEL')
    except KeyError:
        return None
    if not x or len(x) < 28:
        return None
    i = gd.forms[rfid][0]
    return gd.to_global(i, struct.unpack_from('<I', x)[0]), list(struct.unpack_from('<6f', x, 4))


def _inside_of(gd, d, b):
    """The real place an outside door d on building b leads into, as a building may take a copy of it: {'cell', 'exit' (the door
    inside that leads back), 'arrive_in' (where you arrive inside), 'arrive_out' (outside, in the building's frame)}, or None."""
    t = _tel(gd, d['ref'])
    if not t:
        return None
    dest, arrive_in = t
    cell = gd.ref_cell.get(dest)
    if cell is None or cell not in gd.interiors:
        return None
    back = _tel(gd, dest)
    if not back or back[0] != d['ref']:
        return None
    n = len(gd.cell_refs.get(cell, {}))
    if n > MAX_INSIDE_REFS:
        return None
    p = back[1]
    lx, ly = turn(p[0] - b['pos'][0], p[1] - b['pos'][1], -b['rot'][2])
    return {'cell': gd.key(cell), 'exit': gd.key(dest), 'things': n, 'arrive_in': [round(v, 4) for v in arrive_in],
            'arrive_out': [round(lx, 1), round(ly, 1), round(p[2] - b['pos'][2], 1), round(p[3], 4), round(p[4], 4), round((p[5] - b['rot'][2]) % math.tau, 4)]}


def survey(gd, progress=None):
    """Every stand-alone outdoor building in the game, measured: a list of dicts (see the module's docstring)."""
    shapes, info = {}, {}

    def base(fid):
        if fid not in info:
            info[fid] = None
            if fid in gd.forms and gd.forms[fid][1].tag == 'STAT':
                _t, edid, _n, model = gd.describe(fid)
                m = (model or '').replace('/', '\\').lower()
                if m.startswith('architecture\\') or '\\architecture\\' in m or DWELLING.search(m):
                    try:
                        sh = kitindex._load_shape(gd, m, shapes)
                    except (FileNotFoundError, OSError):
                        sh = None
                    if sh:
                        info[fid] = (edid, m, sh[1])
        return info[fid]

    def big(box):
        return box[3] - box[0] >= MIN_SIDE * 0.8 and box[4] - box[1] >= MIN_SIDE * 0.8 and box[5] - box[2] >= MIN_HIGH * 0.8

    seen = collections.defaultdict(list)       # base -> [(cell, ref, footprint, others' footprints, doors)]
    cells = list(gd.ext_cells)
    worlds = {}
    for n, cell in enumerate(cells):
        if progress and n % 2000 == 0:
            progress('Looking at the game\'s buildings', n, len(cells))
        refs = gd.refs(cell)
        parts, doors, shuts = [], [], []
        for r in refs:
            if not r['base'] or not r['pos'] or not r['rot']:
                continue
            if r['type'] == 'REFR' and r['leads'] and r['base'] in gd.forms and gd.forms[r['base']][1].tag == 'DOOR':
                doors.append(r)
                continue
            if r['type'] == 'REFR' and r['base'] in gd.forms and _shuts(gd, r['base']):      # (at any size: the game fits a door or boards to the doorway)
                shuts.append(r)
                continue
            b = base(r['base'])
            if not b or abs(r['rot'][0]) > 0.05 or abs(r['rot'][1]) > 0.05 or abs(r['scale'] - 1) > 0.01 or not big(b[2]):
                continue
            parts.append((r, b, _foot(b[2], r['rot'][2], r['pos'])))
        for r, b, fp in parts:
            alone = True
            for r2, b2, fp2 in parts:
                if r2 is r:
                    continue
                inter = _clip(fp, fp2)
                if inter and _area(inter) > OVERLAP_PART * min(_area(fp), _area(fp2)):
                    alone = False
                    break
            mine = []
            for d in doors:
                lx, ly = turn(d['pos'][0] - r['pos'][0], d['pos'][1] - r['pos'][1], -r['rot'][2])
                box = b[2]
                if box[0] - 96 <= lx <= box[3] + 96 and box[1] - 96 <= ly <= box[4] + 96:
                    row = {'base': gd.key(d['base']), 'x': round(lx, 1), 'y': round(ly, 1), 'z': round(d['pos'][2] - r['pos'][2], 1),
                           'rz': round((d['rot'][2] - r['rot'][2]) % math.tau, 4), 'tx': round(d['rot'][0], 4), 'ty': round(d['rot'][1], 4)}
                    inside = _inside_of(gd, d, r)
                    if inside:
                        row['inside'] = inside
                    mine.append(row)
            shut = []
            for d in shuts:
                lx, ly = turn(d['pos'][0] - r['pos'][0], d['pos'][1] - r['pos'][1], -r['rot'][2])
                box = b[2]
                if box[0] - SHUT_REACH <= lx <= box[3] + SHUT_REACH and box[1] - SHUT_REACH <= ly <= box[4] + SHUT_REACH \
                        and box[2] - SHUT_REACH <= d['pos'][2] - r['pos'][2] <= box[5]:
                    row = {'base': gd.key(d['base']), 'x': round(lx, 1), 'y': round(ly, 1), 'z': round(d['pos'][2] - r['pos'][2], 1),
                           'rz': round((d['rot'][2] - r['rot'][2]) % math.tau, 4), 'tx': round(d['rot'][0], 4), 'ty': round(d['rot'][1], 4)}
                    if abs((d['scale'] or 1.0) - 1) > 0.005:
                        row['s'] = round(d['scale'], 3)
                    if _BOARDS.search((gd.edid(d['base']) or '').lower()):
                        row['board'] = 1
                    if gd.forms[d['base']][1].tag == 'DOOR':
                        row['door'] = 1
                    shut.append(row)
            seen[r['base']].append((cell, r, alone, mine, shut))
            worlds[cell] = gd.ext_cells[cell]
    out = []
    grounds = {}
    for fid, uses in seen.items():
        edid, model, box = info[fid]
        w, d, h = box[3] - box[0], box[4] - box[1], box[5] - box[2]
        narrowest = MIN_SIDE * 0.8 if DWELLING.search(model) else MIN_SIDE
        if not (narrowest <= min(w, d) and max(w, d) <= MAX_SIDE and MIN_HIGH <= h <= MAX_HIGH):
            continue
        if NOT_A_BUILDING.search(edid.lower()) or family_of(edid) == 'any':
            continue
        alone = sum(1 for u in uses if u[2]) / len(uses)
        if alone < ALONE:
            continue
        try:
            whole = solid(nif.mesh_from_nif(gd.read_file('meshes\\' + model)))
        except Exception:
            whole = 0.0
        if whole < SOLID:
            continue                            # (a facade or a bare frame: from some side there is nothing to see)
        mid, lo, hi = [], [], []
        for cell, r, _a, _m, _s in uses:
            world = worlds[cell]
            g = grounds.get(world) or grounds.setdefault(world, roadgen.Ground(gd, None, world))
            z0 = g.at(r['pos'][0], r['pos'][1])
            if z0 is None:
                continue
            mid.append(z0 - r['pos'][2])
            cz = [g.at(x, y) for x, y in _foot(box, r['rot'][2], r['pos'])]
            cz = [z - r['pos'][2] for z in cz if z is not None]
            if cz:
                lo.append(min(cz))
                hi.append(max(cz))
        if not mid:
            continue
        mid.sort()
        doors = [{k: v for k, v in d.items() if k != 'inside'} for d in max((u[3] for u in uses), key=len)[:4]]
        # (every real place the game has behind this building, by which of its doors leads there)
        insides, had = [], set()
        for _c, _r, _a, mine, _s in uses:
            for d in mine:
                ins = d.get('inside')
                if not ins or ins['cell'] in had:
                    continue
                k = min(range(len(doors)), key=lambda i: math.hypot(doors[i]['x'] - d['x'], doors[i]['y'] - d['y'])) if doors else None
                if k is None or math.hypot(doors[k]['x'] - d['x'], doors[k]['y'] - d['y']) > 48:
                    continue
                had.add(ins['cell'])
                insides.append(dict(ins, door=k))
        out.append({'key': gd.key(fid), 'edid': edid, 'model': model, 'box': [round(v, 1) for v in box], 'uses': len(uses), 'alone': round(alone, 2),
                    'family': family_of(edid), 'doors': doors, 'shut': _doorways(doors, [u[4] for u in uses if u[2]]) or _doorways(doors, [u[4] for u in uses]), 'mid': round(mid[len(mid) // 2], 1), 'lo': round(min(lo), 1) if lo else 0.0,
                    'hi': round(max(hi), 1) if hi else 0.0, 'insides': insides, 'solid': round(whole, 2)})
    out.sort(key=lambda b: b['edid'].lower())
    return out


SHUT_REACH = 40.0       # (how far outside a building's box something in its doorway may be)
SHUT_SAME = 80.0        # (two things this near are in the same doorway)
SHUT_MOST = 48          # (a motel has a door to every room, on two floors)
_SHUT_WORD = re.compile(r'door|woodplanksgroup')       # (boards nailed over a doorway are the game's WoodPlanksGroup)
_SHUT_NOT = re.compile(r'doorframe|doorway|indoor|outdoor|doorbell|doormat')
_shut_known = {}


def _shuts(gd, base):
    """Is this what the game closes a doorway with: a door that leads nowhere, a static made to look like one, boards over it?"""
    if base not in _shut_known:
        tag = gd.forms[base][1].tag
        e = (gd.edid(base) or '').lower()
        _shut_known[base] = tag == 'DOOR' or (tag in ('STAT', 'ACTI', 'MSTT') and bool(_SHUT_WORD.search(e)) and not _SHUT_NOT.search(e))
    return _shut_known[base]


def _doorways(doors, placements):
    """The doorways the game shuts on a building, from every placement of it (each a list of things in its frame): one
    doorway is whatever lies within SHUT_SAME of one spot; it is filled as the placement with the most there fills it. A
    doorway one of `doors` already stands in is left to that door."""
    ways = []                                   # [x, y, z, {which placement: [rows]}]
    for n, rows in enumerate(placements):
        for r in rows:
            if any(math.hypot(r['x'] - d['x'], r['y'] - d['y']) < SHUT_SAME and abs(r['z'] - d['z']) < SHUT_SAME * 1.5 for d in doors):
                continue
            for w in ways:
                if math.hypot(r['x'] - w[0], r['y'] - w[1]) < SHUT_SAME and abs(r['z'] - w[2]) < SHUT_SAME * 1.5:
                    w[3].setdefault(n, []).append(r)
                    break
            else:
                ways.append([r['x'], r['y'], r['z'], {n: [r]}])
    ways.sort(key=lambda w: -len(w[3]))         # (the doorways most placements shut, first)
    out = []
    for w in ways[:SHUT_MOST]:
        # (as the placement that puts a door there has it, before one that only boards it over)
        out += max(w[3].values(), key=lambda rows: (any(not r.get('board') for r in rows), len(rows)))[:3]
    return out


def load(gd, folder, progress=None):
    """The catalogue for these game files: from folder if it was measured before."""
    path = os.path.join(folder, 'buildings.json')
    try:
        with open(path, encoding='utf-8') as f:
            got = json.load(f)
        if got.get('format') == FORMAT:
            return got['buildings']
    except (OSError, ValueError):
        pass
    cat = survey(gd, progress)
    os.makedirs(folder, exist_ok=True)
    with open(path + '.tmp', 'w', encoding='utf-8') as f:
        json.dump({'format': FORMAT, 'buildings': cat}, f, indent=0)
    os.replace(path + '.tmp', path)
    return cat


# ---------- a real place behind a door ----------

def inside_ops(gd, inside, tag, edid, full):
    """Ops that make a copy of the game's place behind a building as a place of the mod's own, named '$tag', its way out named
    '$tag' + 'x'. What it has that belongs to the game's own story stays out: people and creatures, keys, notes and terminals,
    talking radios, things switched on by quests (an enable parent, or off at the start), anything with a script of its own;
    nothing in it is owned or locked. Doors to anywhere else are locked. Returns (ops, how many things it has, {the game's door key:
    the copy's name}: the game's own navmesh names its doors, copied_navmesh points it at these)."""
    cfid = gd.from_key(inside['cell'])
    rec = recordio.load(gd, cfid)
    rec['subs'] = [s for s in rec['subs'] if s['tag'] not in ('XOWN', 'XRNK')]
    recordio.set_field(rec, 'EDID', edid, label='Editor ID')
    recordio.set_field(rec, 'FULL', full, label='Name')
    ops = [{'op': 'record_new', 'record': rec, 'name': tag}]
    exit_fid = gd.from_key(inside['exit'])
    kept = 0
    doors = {}
    for r in gd.refs(cfid):
        if r['type'] != 'REFR' or not r['base'] or r['base'] not in gd.forms or not r['pos'] or not r['rot']:
            continue
        i, rr = gd.cell_refs[cfid][r['ref']] if r['ref'] in gd.cell_refs.get(cfid, {}) else (None, None)
        if rr is None:
            continue
        btag = gd.forms[r['base']][1].tag
        if btag in NOT_INSIDE or rr.flags & INITIALLY_OFF or 'XESP' in gd.plugins[i].fields(rr):
            continue
        if btag != 'DOOR' and 'SCRI' in gd.fields(r['base']):
            continue                     # (a script of its own may be part of a game quest: a safehouse's bed, a terminal's menu)
        o = {'op': 'add', 'cell': '$' + tag, 'base': gd.key(r['base']), 'p': [round(v, 4) for v in list(r['pos']) + list(r['rot'])], 's': round(r['scale'], 4)}
        if r['ref'] == exit_fid:
            o['name'] = tag + 'x'
        elif btag == 'DOOR':
            o['name'] = '%sd%d' % (tag, len(doors))
            if r['leads']:
                o['extra'] = DOOR_LOCK
        if btag == 'DOOR':
            doors[gd.key(r['ref'])] = o['name']
        ops.append(o)
        kept += 1
    return ops, kept, doors


def copied_navmesh(gd, pr, src, ckey, door_keys):
    """The game's own navmesh of the place a copy was made from, for the copy (whose things stand exactly where the game's do): the
    project's form, its doors pointed at the copy's (door_keys: the game's door key to the copy's), or None when it can't be
    taken as it is (none, more than one, links to other meshes, or not sound) and one has to be made."""
    entries = navbuild.game_entries(gd, src)
    if len(entries) != 1:
        return None
    data = navbuild.game_copy(gd, entries[0])
    if data['ext']:
        return None
    data['doors'] = [[door_keys[d], t] for d, t in data['doors'] if d in door_keys]
    for k in ('copy', 'outline'):
        data.pop(k, None)
    data['form'] = None
    if navmesh.validate(navmesh.refresh(navbuild.as_mesh(data))):
        return None
    data['sig'] = navbuild.signature(navbuild.place_refs(gd, pr, ckey))
    return data


# A hotel on the map is a hotel inside, whatever stands for it outside: a small building's own interior behind the door
# of the Hyatt was a corner shop. So a plot the map calls a hotel (its kind, or its name) gets one of the game's big
# hotel and casino floors behind its door, the ones with a single way out to the street.
# The same for the other places a town has that are big inside or particular: a market, a warehouse, offices, a school,
# a police station, a clinic. Each kind has its own few of the game's interiors and its own share of the places made.
GRAND = {'hotel': ('VikkiAndVance', 'BisonSteve01', 'MonteCarloSuitesInterior', 'FreesideAtomicWrangler', 'JacobstownLodge', '2CCampGolfResort'),
         'market': ('NiptonGeneralStore', 'FreesideRobotShop', 'WestsideLiquorStoreInterior', 'GSGeneralStore', 'WestsidePawnShopInterior', 'FreesideSupplyDropHouse'),
         'works': ('FreesideVanGraffWarehouse', 'NorthVegasHouseTools', '1ENeonSignFactory', '2EOMichaelAngelo', '1EEastPumpStation'),
         'office': ('RepconHQ01', 'AerotechOfficeInterior01', 'AerotechOfficeInterior02', 'SLAlliedTechnologiesOfficesINT', 'QJOffice'),
         'school': ('NellisSchool', 'CampSearchlightSchool', 'GSSchoolHouse'),
         'police': ('CampSearchlightPoliceStation', 'PrimmSheriffStation', 'SLNHPStationINT', '2ENCREmbassy02'),
         'clinic': ('NewVegasMedicalClinicInterior',)}
GRAND_KIND = {'hotel': 'hotel', 'motel': 'hotel', 'hostel': 'hotel', 'guest_house': 'hotel', 'resort': 'hotel',
              'supermarket': 'market', 'mall': 'market', 'department_store': 'market', 'warehouse': 'works', 'industrial': 'works', 'hangar': 'works',
              'manufacture': 'works', 'office': 'office', 'government': 'office', 'bank': 'office', 'school': 'school', 'college': 'school', 'university': 'school',
              'kindergarten': 'school', 'police': 'police', 'fire_station': 'police', 'hospital': 'clinic', 'clinic': 'clinic'}
GRAND_NAMES = (('hotel', re.compile(r'\b(hotel|inn|resort|suites?|motel|lodge|hostel|hyatt|hilton|marriott|sheraton|westin|outrigger)\b', re.I)),
               ('market', re.compile(r'\b(market|supermarket|foodland|safeway|grocery|mart|stores?|shopping)\b', re.I)),
               ('works', re.compile(r'\b(warehouse|depot|factory|cannery|works|storage)\b', re.I)),
               ('police', re.compile(r'\b(police|sheriff|fire station)\b', re.I)),
               ('clinic', re.compile(r'\b(clinic|hospital|medical)\b', re.I)),
               ('school', re.compile(r'\b(school|academy|college|library)\b', re.I)),
               ('office', re.compile(r'\b(bank|offices?|consulate|city hall|courthouse)\b', re.I)))
GRAND_NAME = GRAND_NAMES[0][1]
GRAND_MOST = 10             # (of the places made in one go, how many may be of one of these kinds: the rest stay for ordinary buildings)
POOL_THINGS = 420           # (an interior with more in it than this isn't lent to a building of another kind)
GRAND_OUT = 110.0           # (how far outside the door one arrives)
_grand = {}


def grand_kind(row):
    """What big place a plot calls for ('hotel'), or None."""
    if not row:
        return None
    k = GRAND_KIND.get((row.get('kind') or '').lower())
    if not k:
        name = row.get('name') or ''
        k = next((what for what, pat in GRAND_NAMES if pat.search(name)), None)
    return k


def pools_of(cat):
    """{family: [interiors]}: every place the game has behind a building of that family, for a building of the same family
    that has a door but no place of its own (as the game's own interiors of a family are much alike). Each without its
    arrival outside: that is worked out from the door it goes behind."""
    out = {}
    for b in cat:
        for i in b.get('insides', ()):
            if i.get('things', 0) <= POOL_THINGS:
                out.setdefault(b['family'], {})[i['cell']] = dict({k: v for k, v in i.items() if k != 'arrive_out'}, door=0)
    return {f: list(v.values()) for f, v in out.items()}


_entries = {}
_door_names = {}


def entries_of(gd, b):
    """Which of a building's `shut` rows can be ways in: [(which row, the real door to stand there)]. A door that leads
    nowhere is one already; a static made to look like a door (`...DoorStatic`) is swapped for the door it copies, where
    the game has one of that name."""
    if b['key'] not in _entries:
        got = []
        for n, d in enumerate(b.get('shut', ())):
            if d.get('door'):
                got.append((n, d['base']))
                continue
            e = (gd.edid(gd.from_key(d['base'])) or '').lower()
            if d.get('board') or 'door' not in e:
                continue
            if id(gd) not in _door_names:
                _door_names[id(gd)] = {(gd.edid(f) or '').lower(): f for f, (_i, r) in gd.forms.items() if r.tag == 'DOOR'}
            bare = e.replace('static', '')
            twin = _door_names[id(gd)].get(bare) if bare != e else None
            if twin is None:
                twin = _door_names[id(gd)].get(bare.rstrip('0123456789')) if bare.rstrip('0123456789') != e else None      # (dlc04shackdoor01: dlc04shackdoor)
            if twin is None:
                twin = _door_like(gd, gd.from_key(d['base']))
            if twin is not None:
                got.append((n, gd.key(twin)))
        _entries[b['key']] = got
    return _entries[b['key']]


_like = {}
LIKE_BOX = 12.0             # (two boxes whose six sides differ by no more than this in all are the same door)


def _door_like(gd, static):
    """A real door that looks like a static made to look like one: the same model, else the same box. One with no script
    of its own (a door of some quest would bring its quest with it)."""
    key = (id(gd), static)
    if key not in _like:
        if id(gd) not in _like:
            doors = []
            for f, (_i, r) in gd.forms.items():
                if r.tag == 'DOOR':
                    fl = gd.fields(f)
                    if 'SCRI' in fl:
                        continue
                    m = fl.get('MODL')
                    doors.append((f, (m[:-1].decode('cp1252', 'replace') if m else '').lower().replace('/', '\\'), obnd(gd, gd.key(f))))
            _like[id(gd)] = doors
        m = gd.fields(static).get('MODL')
        model = (m[:-1].decode('cp1252', 'replace') if m else '').lower().replace('/', '\\')
        box = obnd(gd, gd.key(static))
        got = next((f for f, dm, _o in _like[id(gd)] if model and dm == model), None)
        if got is None and box:
            best = min(((sum(abs(u - v) for u, v in zip(box, o)), f) for f, _dm, o in _like[id(gd)] if o), default=None)
            if best and best[0] <= LIKE_BOX:
                got = best[1]
        _like[key] = got
    return _like[key]


def entry_of(gd, b):
    """For a building with no door that leads anywhere: the first of its `entries_of`, or None."""
    got = entries_of(gd, b) if not b['doors'] else []
    return got[0] if got else None


# A motel or a block of flats is a row of doors, each to a room: a few of them open (the game's own motel rooms behind
# them), the rest stay shut.
STRIP = re.compile(r'noso|motel|apartment|rowhouse')
ROOMS = ('NovacPlayersRoom', 'ElReyMotelRoom02', 'ElReyMotelRoom03', 'SLHellsMotel', 'NiptonHotel')
ROOMS_EACH = 3              # (rooms opened in one building)
ROOMS_MOST = 45             # (and in one go)


# A doorway the game only nails boards over shows daylight between them here, where the building is a hollow shell with
# nothing behind: the game's own black sheet (BlackPlane01, a 256 square) is stood just inside, facing out.
BLACK = 'BlackPlane01'
BLACK_ON = False           # (off: stood by the building's box it came out in front of porch walls, 1,100 black squares in a town.
                           # To come back it must go by the boards' own facing, just behind them, no bigger than they are)
BLACK_SIZE = 1.3
BLACK_IN = 14.0
_BOARDS = re.compile(r'woodplanks|barricade')
_black = {}


def boarded_ways(gd, b):
    """The middles (x, y in the building's frame) of the doorways that have boards over them and no door or door static."""
    if b['key'] not in _black:
        ways = []
        for d in b.get('shut', ()):
            e = (gd.edid(gd.from_key(d['base'])) or '').lower()
            for w in ways:
                if math.hypot(d['x'] - w[0], d['y'] - w[1]) < SHUT_SAME:
                    w[2].append(e)
                    break
            else:
                ways.append([d['x'], d['y'], [e]])
        _black[b['key']] = [(w[0], w[1]) for w in ways if all(_BOARDS.search(e) for e in w[2])
                            and not any(math.hypot(w[0] - d['x'], w[1] - d['y']) < SHUT_SAME for d in b['doors'])]
    return _black[b['key']]


def _outward(b, x, y):
    """Which way is out, for a spot in or against a building's wall: a unit step along x or y in its frame."""
    x0, y0, _z0, x1, y1, _z1 = b['box']
    vx, vy = x - (x0 + x1) / 2, y - (y0 + y1) / 2
    if abs(vx) / max(1.0, (x1 - x0) / 2) > abs(vy) / max(1.0, (y1 - y0) / 2):
        return (1.0 if vx > 0 else -1.0), 0.0
    return 0.0, (1.0 if vy > 0 else -1.0)


def _facing(ux, uy):
    """The turn (rx, ry, rz) that stands a flat sheet (lying in its own x-y, face up) upright with its face toward
    (ux, uy) and its edges level. Found by trying: the game turns about z first, so the face is aimed with rx and ry."""
    import navgen
    best = None
    for rx in (math.pi / 2, -math.pi / 2):
        for k in range(360):
            ry = math.tau * k / 360
            for rz in (0.0, math.pi / 2):
                R = navgen._turn(rx, ry, rz)
                score = R[0][2] * ux + R[1][2] * uy - abs(R[2][0]) - abs(R[2][2])
                if best is None or score > best[0]:
                    best = (score, rx, ry, rz)
    return best[1], best[2], best[3]


def grand_inside(gd, edid):
    """One of the game's interiors by editor ID, as a building may take a copy of it (the same form as a building's own
    `insides`, but with no arrival outside: that is worked out from whichever building's door it goes behind), or None."""
    key = (id(gd), edid)
    if key not in _grand:
        got = None
        cell = next((c for c in gd.interiors if (gd.edid(c) or '').lower() == edid.lower()), None)
        for r in (gd.refs(cell) if cell is not None else ()):
            if r['type'] != 'REFR' or not r.get('leads') or r['base'] not in gd.forms or gd.forms[r['base']][1].tag != 'DOOR':
                continue
            t = _tel(gd, r['ref'])
            if not t or gd.ref_cell.get(t[0]) in gd.interiors or gd.ref_cell.get(t[0]) is None:
                continue                        # (the door that leads out to the street, not one to another floor)
            back = _tel(gd, t[0])
            arrive = back[1] if back and back[0] == r['ref'] else list(r['pos']) + list(r['rot'])
            got = {'cell': gd.key(cell), 'exit': gd.key(r['ref']), 'things': len(gd.cell_refs.get(cell, {})), 'arrive_in': [round(v, 4) for v in arrive], 'door': 0, 'grand': edid}
            break
        _grand[key] = got
    return _grand[key]


def _arrive_door(d, ox, oy, z, rz, b, gd=None):
    """Coming out of a room in a row of them: on the walkway just before its own door (which may be upstairs, and well
    inside the building's box), facing away from it."""
    # (which way a door faces is its thin side, turned as it stands; of the two ways through it, out is the one away from
    # the building's middle)
    o = obnd(gd, d['base']) if gd is not None else None
    thin_x = bool(o) and (o[3] - o[0]) < (o[4] - o[1])
    nx, ny = turn(1.0 if thin_x else 0.0, 0.0 if thin_x else 1.0, d['rz'])
    x0, y0, _z0, x1, y1, _z1 = b['box']
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    if math.hypot(d['x'] - nx * ROOM_OUT - cx, d['y'] - ny * ROOM_OUT - cy) > math.hypot(d['x'] + nx * ROOM_OUT - cx, d['y'] + ny * ROOM_OUT - cy):
        nx, ny = -nx, -ny
    ux, uy = nx, ny
    dx, dy = turn(d['x'] + ux * ROOM_OUT, d['y'] + uy * ROOM_OUT, rz)
    return [round(ox + dx, 2), round(oy + dy, 2), round(z + d['z'] + 4.0, 2), 0.0, 0.0, round((rz + math.atan2(ux, uy)) % math.tau, 4)]


ROOM_OUT = 70.0


def _arrive_out(inside, ox, oy, z, rz, b=None, d=None):
    if 'arrive_out' not in inside:
        # (a place that isn't this building's own: out through the door, a step clear of the wall it is in, facing away)
        d = d or b['doors'][inside['door']]
        x0, y0, _z0, x1, y1, _z1 = b['box']
        ux, uy = _outward(b, d['x'], d['y'])
        if ux:
            lx, ly = (x1 if ux > 0 else x0) + ux * GRAND_OUT, d['y']
        else:
            lx, ly = d['x'], (y1 if uy > 0 else y0) + uy * GRAND_OUT
        dx, dy = turn(lx, ly, rz)
        return [round(ox + dx, 2), round(oy + dy, 2), round(z + b['mid'] + 8.0, 2), 0.0, 0.0, round((rz + math.atan2(ux, uy)) % math.tau, 4)]
    p = inside['arrive_out']
    dx, dy = turn(p[0], p[1], rz)
    return [round(ox + dx, 2), round(oy + dy, 2), round(z + p[2], 2), p[3], p[4], round((rz + p[5]) % math.tau, 4)]


# ---------- standing them on plots ----------

class Fit:
    """One catalogue building as it would stand: its front's direction in its frame, its width along a street and depth back from it."""

    def __init__(self, b):
        self.b = b
        box = b['box']
        self.cx, self.cy = (box[0] + box[3]) / 2, (box[1] + box[4]) / 2
        hw, hd = (box[3] - box[0]) / 2, (box[4] - box[1]) / 2
        if b['doors']:
            # (its front: the side of its box its doors are nearest, on average)
            sx = sum((d['x'] - self.cx) / hw for d in b['doors']) / len(b['doors'])
            sy = sum((d['y'] - self.cy) / hd for d in b['doors']) / len(b['doors'])
            self.front = (1.0 if sx > 0 else -1.0, 0.0) if abs(sx) >= abs(sy) else (0.0, 1.0 if sy > 0 else -1.0)
        else:
            # (no door: a long side to the street)
            self.front = (0.0, -1.0) if hw >= hd else (-1.0, 0.0)
        along_x = self.front[0] == 0
        self.width = 2 * (hw if along_x else hd)
        self.depth = 2 * (hd if along_x else hw)

    def turn_for(self, fx, fy):
        """The game turn that points its front at (fx, fy)."""
        return (math.atan2(self.front[1], self.front[0]) - math.atan2(fy, fx)) % math.tau

    def placed(self, mx, my, rz):
        """(origin x, y, footprint corners) with its box's middle at (mx, my), turned rz."""
        ox, oy = turn(self.cx, self.cy, rz)
        box = self.b['box']
        x, y = mx - ox, my - oy
        return x, y, _foot(box, rz, (x, y))


def obnd(gd, key):
    """A base form's bounds (OBND: x0, y0, z0, x1, y1, z1), or None."""
    try:
        fid = gd.from_key(key)
        if fid in gd.forms:
            o = gd.fields(fid).get('OBND')
            if o and len(o) >= 12:
                b = struct.unpack_from('<6h', o)
                if b[3] > b[0] or b[4] > b[1]:
                    return list(b)
    except (ValueError, KeyError):
        pass
    return None


class World:
    """What's on the world already: road pieces and other big things in the mod (to keep clear of), small ones (to clear away)."""

    def __init__(self, gd, pr, world, cat):
        self.gd, self.pr = gd, pr
        self.grid = gd.grid(world)
        self.ground = roadgen.Ground(gd, pr, world)
        self.ins = None
        self._black = False
        self.touched = set()                 # (grid squares a building stands over: their navmesh needs making again)
        self.ours = {b['key'] for b in cat}
        self.boxes, self.big, self.small = {}, [], []
        keys = {gd.key(c): xy for xy, c in self.grid.items()}
        self.bucket = collections.defaultdict(list)
        for ck, c in pr.cells.items():
            if ck not in keys:
                continue
            for rk, r in c['refs'].items():
                if r.get('removed') or not r.get('p') or not r.get('base'):
                    continue
                box = self._box(r['base'])
                if box is None:
                    continue
                p = r['p']
                rz = p[5] if len(p) > 5 else 0.0
                s = r.get('s', 1.0)
                fp = _foot([v * s for v in box], rz, p)
                big = max(box[3] - box[0], box[4] - box[1]) * s >= CLEAR_BELOW
                item = (ck, rk, fp, big, r['base'] in self.ours)
                xs, ys = [q[0] for q in fp], [q[1] for q in fp]
                for bx in range(int(min(xs) // 1024), int(max(xs) // 1024) + 1):
                    for by in range(int(min(ys) // 1024), int(max(ys) // 1024) + 1):
                        self.bucket[(bx, by)].append(item)

    def black_key(self):
        """The game's black sheet, or None."""
        if not BLACK_ON:
            return None
        if self._black is False:
            f = next((f for f, (_i, r) in self.gd.forms.items() if r.tag == 'STAT' and self.gd.edid(f) == BLACK), None)
            self._black = self.gd.key(f) if f is not None else None
        return self._black

    def _box(self, key):
        if key not in self.boxes:
            self.boxes[key] = obnd(self.gd, key)
        return self.boxes[key]

    def near(self, fp):
        xs, ys = [q[0] for q in fp], [q[1] for q in fp]
        got, seen = [], set()
        for bx in range(int(min(xs) // 1024), int(max(xs) // 1024) + 1):
            for by in range(int(min(ys) // 1024), int(max(ys) // 1024) + 1):
                for item in self.bucket.get((bx, by), ()):
                    if (item[0], item[1]) not in seen:
                        seen.add((item[0], item[1]))
                        got.append(item)
        return got

    def add(self, fp, ck, rk):
        xs, ys = [q[0] for q in fp], [q[1] for q in fp]
        item = (ck, rk, fp, True, True)
        for bx in range(int(min(xs) // 1024), int(max(xs) // 1024) + 1):
            for by in range(int(min(ys) // 1024), int(max(ys) // 1024) + 1):
                self.bucket[(bx, by)].append(item)

    def wet(self, x, y, g):
        w = self.ground.water(x, y)
        return w is not None and g < w

    def cell_at(self, x, y):
        c = self.grid.get((int(x // 4096), int(y // 4096)))
        return self.gd.key(c) if c is not None else None


def _roads(gd, w):
    """Where the mod's road pieces stand: a list of (x, y)."""
    kit = set()
    try:
        kit = set(roadgen.pieces(gd).values())
    except (roadgen.RoadError, KeyError, ValueError):
        pass
    out = []
    for items in w.bucket.values():
        for ck, rk, fp, big, _o in items:
            r = w.pr.cells[ck]['refs'][rk]
            if r.get('base') in kit:
                out.append((r['p'][0], r['p'][1]))
    return list(set(out))


def _family_for(row, area):
    fam = OSM_FAMILY.get((row.get('kind') or '').lower())
    if fam:
        return fam
    if area < 1200 * 1200:
        return 'house'
    if area < 2600 * 2600:
        return 'shop'
    return 'apartments'


def plan(gd, pr, world, rows, cat, seed=1, progress=None, insides=INSIDE_SHARE, stretch=1.0):
    """(ops as one Undo, a report). rows: the marker layer's buildings. insides: the share of ordinary buildings that get a copy of a
    real place behind their door (0: none); report['made'] lists [(tag, family, the game's place, its doors' names)] for each, '$tag' naming the place in the ops."""
    rng = random.Random(seed)
    fits = [Fit(b) for b in cat]
    w = World(gd, pr, world, cat)
    # In a world squeezed smaller than life the plots shrink and the game's buildings don't: stretch lets a building take
    # that much more room than its plot (it still can't stand on a road or another building), and the plots that stand
    # out, then the biggest, choose first, so fewer buildings go up than the map has, each at its real size.
    stretch = max(1.0, float(stretch))
    if stretch > 1.0:
        def order(row):
            _cx, _cy, _a, L, W = rect_of(row['ring']) if row.get('pad') else (0, 0, 0, 0, 0)
            return (0 if is_poi(row, L * W) else 1, -(L * W))
        rows = sorted(rows, key=order)
    if insides:
        prefix = re.sub(r'[^A-Za-z0-9]', '', gd.edid(world)) or 'Town'
        w.ins = Insides(gd, prefix, insides, seed=seed, taken=[recordio.field(r, 'EDID') for r in pr.records.values()])
        w.ins.pools = pools_of(cat)
    roads = _roads(gd, w)
    road_bucket = collections.defaultdict(list)
    for x, y in roads:
        road_bucket[(int(x // 4096), int(y // 4096))].append((x, y))

    def nearest_road(x, y):
        best = None
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for rx, ry in road_bucket.get((int(x // 4096) + dx, int(y // 4096) + dy), ()):
                    d = math.hypot(rx - x, ry - y)
                    if best is None or d < best:
                        best = d
        return best

    ops, gone = [], set()
    rep = collections.Counter()
    fams = collections.Counter()
    used = collections.Counter()
    counted = set()
    for items in w.bucket.values():                # (what's up already counts, so laying more keeps the mix)
        for ck, rk, _fp, _big, ours in items:
            if ours and (ck, rk) not in counted:
                counted.add((ck, rk))
                used[w.pr.cells[ck]['refs'][rk]['base']] += 1
    for i, row in enumerate(rows):
        if progress and i % 50 == 0:
            progress('Putting up buildings', i, len(rows))
        rep['plots'] += 1
        if not row.get('pad'):
            rep['too_small'] += 1
            continue
        ring = row['ring']
        cx, cy, a, L, W = rect_of(ring)
        if any(item[4] and landshape.inside(((item[2][0][0] + item[2][2][0]) / 2, (item[2][0][1] + item[2][2][1]) / 2), ring) for item in w.near(corners(cx, cy, math.cos(a), math.sin(a), L / 2, W / 2))):
            rep['had_one'] += 1                # (laid before: a building of ours already stands on it)
            continue
        fam = _family_for(row, L * W)
        # (the street side: of the four, the one whose middle is nearest a road; a long side when there are none)
        ux, uy = math.cos(a), math.sin(a)
        sides = []
        for k, (nx, ny, half_along, half_across) in enumerate(((-uy, ux, L / 2, W / 2), (uy, -ux, L / 2, W / 2), (ux, uy, W / 2, L / 2), (-ux, -uy, W / 2, L / 2))):
            mx, my = cx + nx * half_across, cy + ny * half_across
            d = nearest_road(mx, my)
            sides.append((d if d is not None else (1e9 + (0 if k < 2 else 1) + rng.random()), k, nx, ny, half_along * 2, half_across * 2))
        sides.sort()
        _d, k0, fx, fy, front_len, depth = sides[0]
        poi = is_poi(row, L * W)
        rep['poi'] += poi
        rows_done = _fill(fits, w, fam, cx, cy, fx, fy, front_len, depth, rng, ops, gone, rep, fams, used, row, poi, stretch)
        if rows_done == 0:
            # (nothing fits facing the street: side-on, toward whichever of the other two sides is nearer a road, as a trailer on a narrow lot stands)
            _d, _k, fx, fy, front_len, depth = next(s for s in sides if (s[1] < 2) != (k0 < 2))
            rows_done = _fill(fits, w, fam, cx, cy, fx, fy, front_len, depth, rng, ops, gone, rep, fams, used, row, poi, stretch)
            rep['side_on'] += rows_done > 0
        if rows_done == 0:
            rep['nothing_fits'] += 1
        else:
            rep['built'] += 1
    report = {'plots': rep['plots'], 'built': rep['built'], 'buildings': rep['buildings'], 'doors': rep['doors'], 'shut': rep.get('shut', 0), 'opened': rep.get('opened', 0), 'rooms': rep.get('rooms', 0), 'unboarded': rep.get('unboarded', 0), 'backed': rep.get('backed', 0), 'too_small': rep['too_small'],
              'nothing_fits': rep['nothing_fits'], 'blocked': rep['blocked'], 'steep': rep['steep'], 'had_one': rep['had_one'],
              'cleared': len(gone), 'families': dict(fams), 'catalogue': len(cat), 'roads_seen': len(roads), 'poi': rep['poi'], 'landmarks': rep['landmarks'],
              'insides': len(w.ins.tags) if w.ins else 0, 'inside_things': w.ins.things if w.ins else 0, 'made': list(w.ins.tags) if w.ins else [],
              'insides_capped': bool(w.ins and w.ins.left <= 0), 'side_on': rep['side_on'],
              'cell_xy': [list(xy) for xy in sorted(w.touched)]}
    return ops, report


SOLID = 0.45               # (a building shows at least this much wall to someone standing on each of its four sides)
SOLID_GRID = 20


def solid(shapes):
    """How much of a model a person sees as wall from its worst side: for each of the four sides, the share of the model's
    outline, seen level from there, that outward-facing triangles fill (the game doesn't draw a wall from behind). A whole
    building is near 1; a facade made to stand against others, or a ruin's bare frame, is near 0: from somewhere, it is
    only lines, or nothing."""
    lo, hi = [1e18] * 3, [-1e18] * 3
    for sh in shapes:
        p = sh['p']
        for k in range(0, len(p), 3):
            for a in range(3):
                lo[a] = min(lo[a], p[k + a])
                hi[a] = max(hi[a], p[k + a])
    if hi[0] <= lo[0] or hi[1] <= lo[1] or hi[2] <= lo[2]:
        return 0.0
    G = SOLID_GRID
    worst = 1.0
    for axis, sign in ((0, 1), (0, -1), (1, 1), (1, -1)):
        other = 1 - axis
        seen = bytearray(G * G)
        for sh in shapes:
            if sh.get('alpha') == 'blend':
                continue
            p, idx, both = sh['p'], sh['i'], sh.get('double')
            for k in range(0, len(idx) - 2, 3):
                a, b, c = (p[3 * idx[k]:3 * idx[k] + 3], p[3 * idx[k + 1]:3 * idx[k + 1] + 3], p[3 * idx[k + 2]:3 * idx[k + 2] + 3])
                u = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
                v = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
                n = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2])[axis]
                if not both and n * sign <= 0:
                    continue                    # (its back is to the viewer on this side)
                # its three corners on the side's grid; every square its box covers that its middle or a corner lies in
                pts = [((q[other] - lo[other]) / (hi[other] - lo[other]) * G, (q[2] - lo[2]) / (hi[2] - lo[2]) * G) for q in (a, b, c)]
                x0, x1 = max(0, int(min(q[0] for q in pts))), min(G - 1, int(max(q[0] for q in pts)))
                y0, y1 = max(0, int(min(q[1] for q in pts))), min(G - 1, int(max(q[1] for q in pts)))
                d = (pts[1][1] - pts[2][1]) * (pts[0][0] - pts[2][0]) + (pts[2][0] - pts[1][0]) * (pts[0][1] - pts[2][1])
                if abs(d) < 1e-9:
                    continue
                for gy in range(y0, y1 + 1):
                    for gx in range(x0, x1 + 1):
                        if seen[gy * G + gx]:
                            continue
                        px, py = gx + 0.5, gy + 0.5
                        w0 = ((pts[1][1] - pts[2][1]) * (px - pts[2][0]) + (pts[2][0] - pts[1][0]) * (py - pts[2][1])) / d
                        w1 = ((pts[2][1] - pts[0][1]) * (px - pts[2][0]) + (pts[0][0] - pts[2][0]) * (py - pts[2][1])) / d
                        if w0 >= -0.02 and w1 >= -0.02 and w0 + w1 <= 1.02:
                            seen[gy * G + gx] = 1
        # (the top fifth is left out: a pitched roof leaves the corners of its side empty and is no less a building)
        rows = int(G * 0.8)
        worst = min(worst, sum(seen[:rows * G]) / float(rows * G))
    return worst


def landmark(b):
    """One of the game's one-offs (the Prospector Saloon, Nipton's town hall): it places it fewer than GENERIC_USES times."""
    return b['uses'] < GENERIC_USES


def is_poi(row, area):
    """A plot that stands out: named in the file, a hall's kind (church, school, police...), or very big. Only these may take a landmark."""
    return bool((row.get('name') or '').strip()) or OSM_FAMILY.get((row.get('kind') or '').lower()) == 'civic' or area >= POI_AREA


def _cost(f, fam, want_w, want_d, last, used, rng, poi=False, word=None):
    c = abs(math.log(f.depth / max(want_d, 64.0))) * 0.8
    if poi and landmark(f.b):
        c -= LANDMARK_PULL                                             # (a place worth finding gets one if one fits)
    if word and word in f.b['edid'].lower():
        c -= KIND_PULL                                                 # (a church, if the game has one that fits)
    c += max(0.0, math.log(f.width / max(want_w, 64.0))) * 1.5      # (too wide for what's left costs more than too narrow)
    c += 0.0 if f.b['family'] == fam else 0.9
    c -= math.log(f.b['uses'] + 1) * 0.04
    c += 0.35 if last is f else 0.0
    c += VARIETY * math.sqrt(used[f.b['key']])                        # (a street of one house is no town)
    return c + rng.uniform(0, 0.35)


def _fill(fits, w, fam, cx, cy, fx, fy, front_len, depth, rng, ops, gone, rep, fams, used, row, poi=False, stretch=1.0):
    """Rows of buildings along the street side (fx, fy outward) of a plot, a second facing back if it's deep. Returns how many rows got any."""
    ax, ay = fy, -fx                          # (along the street)
    level = row['level']
    rows_got = 0
    plot_depth = depth                        # (the row's front stays at the plot's own street side, however far back it may reach)
    front_len, depth = front_len * stretch, depth * stretch
    spare = depth
    for facing in (1, -1):
        if spare < ROW_MIN:
            break
        sfx, sfy = fx * facing, fy * facing
        edge = plot_depth / 2 - SETBACK       # (the row's front, from the plot's middle, toward its street)
        max_d = spare * DEPTH_OVER + SLACK if facing == 1 else spare - GAP
        picked, left, last = [], front_len * WIDTH_OVER + SLACK, None
        while left >= ROW_MIN:
            # (generic buildings anywhere; a landmark only on a plot that stands out, once in the world, one to a plot)
            may_mark = poi and facing == 1 and not picked and not rows_got
            choices = [f for f in fits if f.width <= left and f.depth <= max_d and (not landmark(f.b) or may_mark and not used[f.b['key']])]
            if not choices:
                break
            word = KIND_WORD.get((row.get('kind') or '').lower())
            best = min(choices, key=lambda f: _cost(f, fam, min(left, front_len), min(spare, max_d), last, used, rng, poi, word))
            picked.append(best)
            left -= best.width + GAP
            last = best
            if landmark(best.b):
                break                         # (a landmark keeps its plot to itself: the rest is its yard)
            if len(picked) == 1 and best.width >= front_len * 0.6 and front_len < 2 * ROW_MIN + best.width:
                break
        if not picked:
            break
        total = sum(f.width for f in picked) + GAP * (len(picked) - 1)
        s = -total / 2
        row_depth = 0.0
        got = 0
        for f in picked:
            along = s + f.width / 2
            s += f.width + GAP
            back = edge - f.depth / 2
            mx = cx + ax * along + sfx * back
            my = cy + ay * along + sfy * back
            rz = f.turn_for(sfx, sfy)
            ox, oy, fp = f.placed(mx, my, rz)
            if _put(f, w, ox, oy, rz, fp, level, ops, gone, rep, row, poi):
                got += 1
                used[f.b['key']] += 1
                rep['landmarks'] += landmark(f.b)
                fams[f.b['family']] += 1
                row_depth = max(row_depth, f.depth)
        if got:
            rows_got += 1
        spare = depth - SETBACK * 2 - row_depth - GAP
        if facing == 1 and spare < ROW_MIN:
            break
    return rows_got


def _put(f, w, ox, oy, rz, fp, level, ops, gone, rep, row=None, poi=False):
    """Stand one building, its doors and clear what's small under it, if nothing big is in its way and the ground lies right."""
    clear = []
    for ck, rk, ofp, big, _ours in w.near(fp):
        if (ck, rk) in gone or not overlap(fp, ofp):
            continue
        if big or not rk.startswith('+'):
            rep['blocked'] += 1
            return False
        clear.append((ck, rk))
    b = f.b
    z = level - b['mid']
    for x, y in fp + [(ox, oy)]:
        g = w.ground.at(x, y)
        if g is None or not (max(b['lo'] - GROUND_OFF, b['box'][2] - FLOAT_MOST) <= g - z <= b['hi'] + GROUND_OFF) or (g < DRY and w.wet(x, y, g)):
            rep['steep'] += 1                   # (or a corner of it in the water)
            return False
    ck = w.cell_at(ox, oy)
    if ck is None:
        rep['blocked'] += 1
        return False
    for c, r in clear:
        if (c, r) not in gone:
            gone.add((c, r))
            ops.append({'op': 'remove', 'cell': c, 'ref': r})
    ops.append({'op': 'add', 'cell': ck, 'base': b['key'], 'p': [round(ox, 2), round(oy, 2), round(z, 2), 0.0, 0.0, round(rz, 4)], 's': 1})
    # (each by a name of its own: near() passes over a name it has seen, and with one name for all only the first new
    # building in a cell was ever looked at, so the rest stood in each other: 5,844 pairs over Koko Head)
    w.add(fp, ck, '(new %d)' % rep['buildings'])
    for x, y in fp + [(ox, oy)]:
        if (int(x // 4096), int(y // 4096)) in w.grid:
            w.touched.add((int(x // 4096), int(y // 4096)))
    rep['buildings'] += 1
    strip = bool(STRIP.search(b['edid'].lower()))
    # (a motel or a row of flats: its doors open into rooms, the game's motel rooms, never a shop or an office borrowed
    # from another building however the plot is named)
    entry = entry_of(w.gd, b) if not strip else None
    inside = w.ins.pick(b, poi, row, entry is not None) if w.ins and not (strip and not b['doors']) else None
    rooms = {}
    if w.ins and strip:
        # (spread along the row, not the first three doors side by side)
        ways = entries_of(w.gd, b)
        for e in ways[::max(1, len(ways) // ROOMS_EACH)][:ROOMS_EACH]:
            rooms[e[0]] = e[1]
    shut = b.get('shut', ())
    doorlike = [(d['x'], d['y'], d['z']) for d in b['doors']] + [(d['x'], d['y'], d['z']) for d in shut if not d.get('board')]
    for k, d in enumerate(b['doors']):
        dx, dy = turn(d['x'], d['y'], rz)
        dck = w.cell_at(ox + dx, oy + dy) or ck
        o = {'op': 'add', 'cell': dck, 'base': d['base'], 'p': [round(ox + dx, 2), round(oy + dy, 2), round(z + d['z'], 2), d['tx'], d['ty'], round((rz + d['rz']) % math.tau, 4)], 's': 1}
        rep['doors'] += 1
        if inside and k == inside['door']:
            ops.extend(w.ins.make(inside, b, row, o, dck, _arrive_out(inside, ox, oy, z, rz, b)))
        else:
            o['extra'] = DOOR_LOCK
            ops.append(o)
    for n, d in enumerate(shut):
        if d.get('board') and any(math.hypot(d['x'] - x, d['y'] - y) < SHUT_SAME and abs(d['z'] - z_) < SHUT_SAME * 2 for x, y, z_ in doorlike):
            rep['unboarded'] = rep.get('unboarded', 0) + 1
            continue                            # (boards nailed across a door stood through it: a door is enough)
        dx, dy = turn(d['x'], d['y'], rz)
        dck = w.cell_at(ox + dx, oy + dy) or ck
        o = {'op': 'add', 'cell': dck, 'base': d['base'],
             'p': [round(ox + dx, 2), round(oy + dy, 2), round(z + d['z'], 2), d['tx'], d['ty'], round((rz + d['rz']) % math.tau, 4)], 's': d.get('s', 1)}
        if entry is not None and n == entry[0] and inside:
            # (the way in: the real door in place of what only looked like one, a place behind it)
            o['base'] = entry[1]
            ops.extend(w.ins.make(inside, b, row, o, dck, _arrive_out(inside, ox, oy, z, rz, b, d)))
            rep['doors'] += 1
            rep['opened'] = rep.get('opened', 0) + 1
            continue
        room = w.ins.room() if n in rooms else None
        if room:
            o['base'] = rooms[n]
            ops.extend(w.ins.make(room, b, row, o, dck, _arrive_door(d, ox, oy, z, rz, b, w.gd)))
            rep['doors'] += 1
            rep['rooms'] = rep.get('rooms', 0) + 1
            continue
        if d.get('door'):
            o['extra'] = DOOR_LOCK
        ops.append(o)
        rep['shut'] = rep.get('shut', 0) + 1
    black = w.black_key()
    for bx, by in (boarded_ways(w.gd, b) if black else ()):
        ux, uy = _outward(b, bx, by)
        dx, dy = turn(bx - ux * BLACK_IN, by - uy * BLACK_IN, rz)
        wx, wy = turn(ux, uy, rz)
        rx, ry, rz2 = _facing(wx, wy)
        ops.append({'op': 'add', 'cell': w.cell_at(ox + dx, oy + dy) or ck, 'base': black,
                    'p': [round(ox + dx, 2), round(oy + dy, 2), round(z + b['mid'] + 128.0 * BLACK_SIZE - 12.0, 2), round(rx, 4), round(ry, 4), round(rz2, 4)], 's': BLACK_SIZE})
        rep['backed'] = rep.get('backed', 0) + 1
    return True


class Insides:
    """Which buildings get a copy of a real place behind their door, and the ops for it (inside_ops)."""

    def __init__(self, gd, prefix, share=INSIDE_SHARE, most=MAX_INSIDES, seed=1, taken=()):
        self.gd, self.prefix, self.share, self.left = gd, prefix, share, most
        self.rng = random.Random(seed * 7919 + 1)
        self.used = collections.Counter()
        self.kinds = collections.Counter()       # (how many of each big kind were made: GRAND_MOST)
        self.pools = {}                          # (pools_of(cat), set by plan)
        self.tags = []                           # (what was made: [(tag, family)])
        self.taken = {e.lower() for e in taken}
        self.n = collections.Counter()
        self.things = 0

    def pick(self, b, poi, row=None, entry=False):
        """One of the places the game has behind this building, or None: always on a plot that stands out, else by share.
        A plot that calls for a big or particular place (a hotel, a market, a school) gets one of those, whatever the
        building. A building with a door (or, entry, something that can be made one) but no place of its own in the game
        borrows one from the others of its family."""
        if self.left <= 0 or not (b['doors'] or entry):
            return None
        what = grand_kind(row)
        if what and self.kinds[what] < GRAND_MOST:
            big = [g for g in (grand_inside(self.gd, e) for e in GRAND[what]) if g]
            if big:
                self.kinds[what] += 1
                least = min(self.used[i['cell']] for i in big)
                return self.rng.choice([i for i in big if self.used[i['cell']] == least])
        own = b.get('insides') if b['doors'] else None
        cands = own or self.pools.get(b['family']) or ()
        if not cands or (not poi and self.rng.random() >= self.share):
            return None
        least = min(self.used[i['cell']] for i in cands)
        return self.rng.choice([i for i in cands if self.used[i['cell']] == least])

    def room(self):
        """A motel room for one door of a row of them, or None when enough have been made."""
        if self.left <= 0 or self.kinds['room'] >= ROOMS_MOST:
            return None
        got = [g for g in (grand_inside(self.gd, e) for e in ROOMS) if g]
        if not got:
            return None
        self.kinds['room'] += 1
        least = min(self.used[i['cell']] for i in got)
        return self.rng.choice([i for i in got if self.used[i['cell']] == least])

    def make(self, inside, b, row, door_op, dck, arrive_out):
        self.left -= 1
        self.used[inside['cell']] += 1
        tag = 'in%d' % len(self.tags)
        fam = b['family']
        word = PLACE_NAME.get(fam, 'Building')
        while True:
            self.n[word] += 1
            edid = '%s%s%02d' % (self.prefix, word, self.n[word])
            if edid.lower() not in self.taken:
                break
        self.taken.add(edid.lower())
        full = (row.get('name') or '').strip() or word
        ops, kept, doors = inside_ops(self.gd, inside, tag, edid, full)
        self.things += kept
        self.tags.append((tag, fam, inside['cell'], doors))
        door = dict(door_op, name=tag + 'o')
        return ops + [door,
                      {'op': 'tel', 'cell': dck, 'ref': '$' + tag + 'o', 'tel': {'door': '$' + tag + 'x', 'p': inside['arrive_in']}},
                      {'op': 'tel', 'cell': '$' + tag, 'ref': '$' + tag + 'x', 'tel': {'door': '$' + tag + 'o', 'p': arrive_out}}]
