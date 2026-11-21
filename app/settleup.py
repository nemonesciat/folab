"""Things in the air put back on what is under them, by real collision.

The roof camps (rooftops: sandbags, chairs, bedding, fires, crates, boxes to find, lean-tos), the junk yards and the
shanties were stood on what was there when they were made. Steps after (groundfit's fit and close_gaps letting buildings
down, buildings taken out or swapped) moved what was under them and left them where they were: a tester saw sandbags and a
lean-to in mid-air over Waikiki's roofs again and again (18-19 Nov 2026). Earlier checks missed them: they took a
building's bounding box for its roof (a box reaches over chimneys and water tanks, so anything at its top looked held),
and they could not read the size of the mod's own pieces, so they skipped those.

`settle(gd, pr, world)` looks at each such thing the mod added: under five spots of its footprint, the highest solid
surface of everything round it (the game's collision of every placed thing, the mod's own models' collision, the land)
that is not above its underside. The thing rests on the highest of these. One whose underside is more than `GAP` over
that is let down onto it; one sunk into a roof (a building lifted under it) is lifted onto the roof floor (rooftops.roof_of)
when that is within `LIFT`. A roof camp's thing that would fall more than `FELL` onto anything but a building of the catalogue
(the open ground, a car, a wall) is taken out: its roof is gone, and a mattress in the street is no better than one in the air. Returns (ops, report)."""
import math
import re

import navbuild
import navgen
import recordio
import roadgen
import rooftops
import townbuild

GAP = 12.0          # an underside this far over what holds it is resting on it
LIFT = 400.0        # a thing this far under a roof floor, inside the building, is lifted onto it
FELL = 150.0        # a roof camp's thing that would fall further than this to the open ground is taken out
SQ = 256.0          # triangles are filed by squares this size
NEAR = 1          # cells round a thing whose things may hold it

CAMP_EDIDS = ({rooftops.SANDBAG} | {e for e, _c in rooftops.CAMP} | set(rooftops.LOOT) | set(rooftops.CHAIRS)
              | set(rooftops.JUNK) | {e for e, _n in rooftops.YARD})
ROOF_PIECE = re.compile(r'^FOLabCityLeanTo', re.I)       # (the mod's own pieces that stand on roofs)
GROUND_PIECE = re.compile(r'^FOLabCity(Shanty|Lookout)', re.I)
RAMP_PIECE = re.compile(r'^FOLabCityRamp', re.I)          # (a way up: its top must still meet a roof)
RAMP_REACH = 1500.0     # a ramp tower's roof stands within this of it
RAMP_OVER = (-400.0, 60.0)  # and its floor between these of the tower's top (the top reaches over the wall and its parapet)


def _edid(gd, pr, key):
    if key.startswith('+'):
        rec = pr.records.get(key) or {}
        return recordio.field(rec, 'EDID') or rec.get('edid') or ''
    try:
        return gd.edid(gd.from_key(key)) or ''
    except (ValueError, KeyError):
        return ''


class _Solids:
    """The world's solid triangles round a spot, as the mod leaves it, read a cell at a time and kept."""

    def __init__(self, gd, pr, skip):
        self.gd, self.pr, self.skip = gd, pr, skip
        self.cells, self.cache, self.report = {}, {}, {'collision': 0, 'drawn': 0, 'unread': 0, 'placed': 0}
        self.grid = {}

    def _cell(self, ck):
        if ck in self.cells:
            return
        self.cells[ck] = True
        try:
            refs = navbuild.place_refs(self.gd, self.pr, ck)
        except Exception:
            return
        for r in refs:
            if r['ref'] in self.skip or r['type'] != 'REFR' or r.get('pos') is None:
                continue
            if r['base'] is None:
                solid = navgen._solid_of_file(self.gd, r['model'], self.cache, self.report) if r.get('model') else []
            else:
                solid = navgen._solid_of(self.gd, r['base'], self.cache, self.report)
            if not solid:
                continue
            (r00, r01, r02), (r10, r11, r12), (r20, r21, r22) = navgen._turn(*r['rot'])
            tx, ty, tz = r['pos']
            s = r['scale']
            for flat, idx, _soup in solid:
                pts = []
                for k in range(0, len(flat) - 2, 3):
                    x, y, z = flat[k], flat[k + 1], flat[k + 2]
                    pts.append((tx + s * (r00 * x + r01 * y + r02 * z), ty + s * (r10 * x + r11 * y + r12 * z),
                                tz + s * (r20 * x + r21 * y + r22 * z)))
                for k in range(0, len(idx) - 2, 3):
                    tri = (pts[idx[k]], pts[idx[k + 1]], pts[idx[k + 2]], r['ref'])
                    x0 = min(p[0] for p in tri[:3]); x1 = max(p[0] for p in tri[:3])
                    y0 = min(p[1] for p in tri[:3]); y1 = max(p[1] for p in tri[:3])
                    for gx in range(int(x0 // SQ), int(x1 // SQ) + 1):
                        for gy in range(int(y0 // SQ), int(y1 // SQ) + 1):
                            self.grid.setdefault((gx, gy), []).append(tri)

    def load_round(self, ckeys):
        for ck in ckeys:
            self._cell(ck)

    def tops(self, x, y):
        """Every solid surface's height straight under or over (x, y): [(z, ref)]."""
        out = []
        for a, b, c, ref in self.grid.get((int(x // SQ), int(y // SQ)), ()):
            d = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
            if abs(d) < 1e-9:
                continue
            l1 = ((b[1] - c[1]) * (x - c[0]) + (c[0] - b[0]) * (y - c[1])) / d
            l2 = ((c[1] - a[1]) * (x - c[0]) + (a[0] - c[0]) * (y - c[1])) / d
            l3 = 1 - l1 - l2
            if l1 >= -1e-6 and l2 >= -1e-6 and l3 >= -1e-6:
                out.append((l1 * a[2] + l2 * b[2] + l3 * c[2], ref))
        return out


def _bounds(gd, pr, key, solids):
    """(x0, y0, z0, x1, y1, z1) of a base: its OBND, else (one of the mod's own models) its collision's."""
    o = townbuild.obnd(gd, key)
    if o:
        return o
    rec = pr.records.get(key) if key.startswith('+') else None
    model = recordio.field(rec, 'MODL') if rec else None
    if not model:
        return None
    sol = navgen._solid_of_file(gd, 'meshes\\' + model.replace('/', '\\').lstrip('\\'), solids.cache, solids.report)
    xs = [f[k] for f, _i, _s in sol for k in range(0, len(f), 3)]
    ys = [f[k + 1] for f, _i, _s in sol for k in range(0, len(f), 3)]
    zs = [f[k + 2] for f, _i, _s in sol for k in range(0, len(f), 3)]
    return [min(xs), min(ys), min(zs), max(xs), max(ys), max(zs)] if xs else None


# (everything=True, the Big jobs' "Things floating or sunk": every small thing the mod placed, not only the roof camps;
# never buildings of the catalogue, road pieces, pavement, doors, lights, plants; and never one with something taller right
# beside it, which may hold it: a sign on a wall, boards over a doorway, a lamp on a post)
LOOSE_TYPES = {'STAT', 'MSTT', 'CONT', 'MISC', 'FURN', 'ACTI', 'SCOL', 'WEAP', 'ARMO', 'AMMO', 'ALCH', 'BOOK', 'KEYM', 'NOTE'}
NOT_LOOSE = re.compile(r'(door|light|lamp|lantern|sign|wire|cable|vine|board|plank|window|billboard|pole|bridge|road|'
                       r'pavement|sidewalk|curb|kerb|fence|wall|rail|pipe|plant|tree|bush|grass|fern|palm|shrub|marker|fx)', re.I)
BESIDE = 24.0       # how far round a loose thing to look for something taller that may hold it


def _type(gd, pr, key):
    if key.startswith('+'):
        return (pr.records.get(key) or {}).get('type', '')
    try:
        f = gd.from_key(key)
        got = gd.forms.get(f)
        return got[1].tag if got else ''
    except (ValueError, KeyError, AttributeError, TypeError):
        return ''


def settle(gd, pr, world, cat=None, cells=None, progress=None, everything=False):
    grid = gd.grid(world)
    by_xy = {xy: gd.key(c) for xy, c in grid.items()}
    G = roadgen.Ground(gd, pr, world)
    by_key = {b['key']: b for b in (cat or [])}
    kinds, todo = {}, []
    not_loose = set()
    if everything:
        import roadbed
        not_loose = set(roadbed._flat_bases(gd, pr)) | set(roadbed._slab_bases(gd))
    for xy, cell in grid.items():
        ck = gd.key(cell)
        if cells is not None and ck not in cells:
            continue
        c = pr.cells.get(ck)
        for rk, r in (c['refs'].items() if c else ()):
            p, b = r.get('p'), r.get('base')
            if not rk.startswith('+') or r.get('removed') or not p or not b or abs(p[3]) > 0.05 or abs(p[4]) > 0.05:
                continue
            if b not in kinds:
                e = _edid(gd, pr, b)
                kinds[b] = ('camp' if (e in CAMP_EDIDS or ROOF_PIECE.match(e)) else 'ground' if GROUND_PIECE.match(e)
                            else 'ramp' if RAMP_PIECE.match(e) else None)
                if kinds[b] is None and everything and b not in by_key and b not in not_loose                         and _type(gd, pr, b) in LOOSE_TYPES and not NOT_LOOSE.search(e or ''):
                    kinds[b] = 'loose'
            if kinds[b]:
                todo.append((xy, ck, rk, r, kinds[b]))
    solids = _Solids(gd, pr, {rk for _xy, _ck, rk, _r, _k in todo})
    buildings = {}                                  # (ref: (its place, its size, its catalogue entry))
    for c in pr.cells.values():
        for rk, r in c.get('refs', {}).items():
            if r.get('base') in by_key and r.get('p') and not r.get('removed'):
                buildings[rk] = (r['p'], float(r.get('s') or 1.0), by_key[r['base']])
    ops, report = [], {'looked_at': len(todo), 'resting': 0, 'let_down': 0, 'lifted': 0, 'taken_out': 0, 'most_fall': 0,
                       'ramps': 0, 'ramps_to_nowhere': 0, 'held': 0}
    todo.sort(key=lambda t: t[0])
    for n, (xy, ck, rk, r, kind) in enumerate(todo):
        if progress and n % 200 == 0:
            progress('Settling things in the air', n, len(todo))
        solids.load_round([by_xy[(xy[0] + dx, xy[1] + dy)] for dx in range(-NEAR, NEAR + 1) for dy in range(-NEAR, NEAR + 1)
                           if (xy[0] + dx, xy[1] + dy) in by_xy])
        p = list(r['p'])
        s = float(r.get('s') or 1.0)
        o = _bounds(gd, pr, r['base'], solids)
        if not o:
            continue
        under = p[2] + o[2] * s
        if kind == 'ramp':
            report['ramps'] += 1
            top = p[2] + o[5] * s
            meets = False
            for bp, bs, bcat in buildings.values():
                if abs(bp[0] - p[0]) > RAMP_REACH or abs(bp[1] - p[1]) > RAMP_REACH:
                    continue
                roof = rooftops.roof_of(gd, bcat['model'], bcat['box'])
                if roof and RAMP_OVER[0] <= bp[2] + roof['z'] * bs - top <= RAMP_OVER[1]:
                    meets = True
                    break
            if not meets:
                ops.append({'op': 'remove', 'cell': ck, 'ref': rk})
                report['ramps_to_nowhere'] += 1
            continue
        c, sn = math.cos(p[5]), math.sin(p[5])
        rest, on_land, lift_to, rest_ref = None, True, None, None
        for fx, fy in ((0.5, 0.5), (0.2, 0.2), (0.8, 0.2), (0.2, 0.8), (0.8, 0.8)):
            lx, ly = (o[0] + (o[3] - o[0]) * fx) * s, (o[1] + (o[4] - o[1]) * fy) * s
            x, y = p[0] + lx * c + ly * sn, p[1] - lx * sn + ly * c
            g = G.at(x, y)
            best, land, bref = (g, True, None) if g is not None and g <= under + GAP else (None, True, None)
            for z, ref in solids.tops(x, y):
                if z <= under + GAP and (best is None or z > best):
                    best, land, bref = z, False, ref
            if best is not None and (rest is None or best > rest):
                rest, on_land, rest_ref = best, land, bref
        if rest is None:
            continue
        gap = under - rest
        if gap <= GAP:
            # inside a building that was lifted? a catalogue building's roof floor a little over it
            lift_to = _roof_over(gd, buildings, solids, p, under)
            if lift_to is None:
                report['resting'] += 1
                continue
            p[2] += lift_to - under
            ops.append({'op': 'move', 'cell': ck, 'ref': rk, 'p': [round(v, 2) for v in p]})
            report['lifted'] += 1
            continue
        if kind == 'loose':
            w = max(o[3] - o[0], o[4] - o[1]) * s / 2 + BESIDE
            if any(under + GAP < z for dx, dy in ((w, 0), (-w, 0), (0, w), (0, -w), (w, w), (-w, w), (w, -w), (-w, -w))
                   for z, _ref in solids.tops(p[0] + dx, p[1] + dy)):
                report['held'] += 1         # (something taller right beside it may hold it: left)
                continue
        on_roof = False
        if rest_ref in buildings:
            bp, bs, bcat = buildings[rest_ref]
            roof = rooftops.roof_of(gd, bcat['model'], bcat['box'])
            on_roof = bool(roof) and abs(bp[2] + roof['z'] * bs - rest) <= GAP * 2
        if kind == 'camp' and gap > FELL and not on_roof:
            ops.append({'op': 'remove', 'cell': ck, 'ref': rk})
            report['taken_out'] += 1
            continue
        p[2] -= gap
        ops.append({'op': 'move', 'cell': ck, 'ref': rk, 'p': [round(v, 2) for v in p]})
        report['let_down'] += 1
        report['most_fall'] = max(report['most_fall'], round(gap))
    report['collision_read'] = solids.report
    return ops, report


def _roof_over(gd, buildings, solids, p, under):
    """The roof floor (world height) of a catalogue building standing round (p), over `under` by no more than LIFT, else None."""
    best = None
    for z, ref in solids.tops(p[0], p[1]):
        if not (under + GAP < z <= under + LIFT) or ref not in buildings:
            continue
        bp, bs, bcat = buildings[ref]
        roof = rooftops.roof_of(gd, bcat['model'], bcat['box'])
        if roof and abs(bp[2] + roof['z'] * bs - z) <= GAP * 2:
            best = z if best is None else min(best, z)
    return best
