"""Which side of a city door is outside, told by geometry, not by the navmesh (the city's navmesh covers the floors inside
hollow game buildings too: chosen by navmesh, 14 of 22 arrivals pointed into the building, 22 Nov 2026).

Buildings(refs, obnd, name, city): every big STAT with its footprint in its own frame. outward(door p, normal) -> +1 or -1:
the sign along `normal` that leads away from the middle of the building whose footprint (grown by MARGIN) the door stands
on, the smallest such; None when it stands on none."""
import math

MARGIN = 90.0
BIG = 300 * 300


class Buildings:
    def __init__(self, refs, obnd, name, city, boxes=None):
        """boxes: {base: box} (townbuild's catalogue, its own buildings only, their measured boxes): a porch slab, an awning or
        a neighbour's fence is never taken for the building then."""
        self.items = []
        for rk, (ck, r) in refs.items():
            if ck not in city or not r.get('p') or r['p'][2] < -20000:
                continue
            if boxes is not None:
                if r.get('base') not in boxes:
                    continue
                b = boxes[r['base']]
            elif name(r.get('base') or '')[1] != 'STAT':
                continue
            else:
                b = obnd(r['base'])
            s = float(r.get('s') or 1.0)
            if not b or (b[3] - b[0]) * (b[4] - b[1]) * s * s < BIG:
                continue
            self.items.append((r['p'], b, s))
        self.grid = {}
        for k, (p, b, s) in enumerate(self.items):
            reach = max(abs(v) for v in b[:2] + b[3:5]) * s + MARGIN
            for gx in range(int((p[0] - reach) // 1024), int((p[0] + reach) // 1024) + 1):
                for gy in range(int((p[1] - reach) // 1024), int((p[1] + reach) // 1024) + 1):
                    self.grid.setdefault((gx, gy), []).append(k)

    def under(self, x, y):
        """(area, centre x, y) of the smallest building footprint the point stands on."""
        best = None
        for k in self.grid.get((int(x // 1024), int(y // 1024)), ()):
            p, b, s = self.items[k]
            rz = p[5]
            c, sn = math.cos(rz), math.sin(rz)
            dx, dy = (x - p[0]) / s, (y - p[1]) / s
            lx, ly = dx * c - dy * sn, dx * sn + dy * c          # (the world back into the building's frame)
            if b[0] - MARGIN <= lx <= b[3] + MARGIN and b[1] - MARGIN <= ly <= b[4] + MARGIN:
                area = (b[3] - b[0]) * (b[4] - b[1]) * s * s
                mx, my = (b[0] + b[3]) / 2.0 * s, (b[1] + b[4]) / 2.0 * s
                cx, cy = p[0] + mx * c + my * sn, p[1] - mx * sn + my * c
                if best is None or area < best[0]:
                    best = (area, cx, cy)
        return best

    def outward(self, p, normal):
        u = self.under(p[0], p[1])
        if u is None:
            return None
        d = (p[0] - u[1]) * normal[0] + (p[1] - u[2]) * normal[1]
        return 1 if d >= 0 else -1


CLEAR_DEEP = 160.0       # (how far out in front of a door loose things are taken away)
LOOSE = ('STAT', 'MSTT', 'MISC', 'FURN', 'CONT', 'ALCH', 'WEAP', 'ARMO', 'AMMO', 'BOOK', 'NOTE', 'KEYM', 'IDLM', 'TREE')
SMALL = 260 * 260
# (only things named as clutter: a game model's bounds can be far smaller than it is, and the first clearing took Quonset
# huts, a courtyard wall and sidewalk with the crates)
CLUTTER = ('barrel', 'crate', 'dumpster', 'tire', 'clothesline', 'pineapple', 'duffle', 'duffel', 'plank', 'bush', 'grass',
           'bag', 'box', 'trash', 'cart', 'debris', 'bucket', 'bottle', 'can0', 'chair', 'bench', 'table', 'pallet', 'junk',
           'litter', 'paper', 'fern', 'shrub', 'flower', 'weed', 'rock0', 'rubble', 'lamp', 'cone', 'mattress', 'suitcase')


def in_front(door_p, door_b, s, out, refs, name, obnd, city, skip=()):
    """Loose things standing in front of a door (its width and a little, CLEAR_DEEP out, its height): [(cell, ref, editor
    ID)]. Small and of a loose kind, never a door, a linked or persistent thing, or anything big."""
    nx, ny = out
    tx, ty = -ny, nx
    half = max(door_b[3] - door_b[0], door_b[4] - door_b[1]) * s / 2.0 + 30.0
    foot = door_p[2] + door_b[2] * s
    found = []
    for rk, (ck, r) in refs.items():
        p = r.get('p')
        if rk in skip or ck not in city or not p or abs(p[0] - door_p[0]) > 400 or abs(p[1] - door_p[1]) > 400:
            continue
        e, t = name(r.get('base') or '')
        if t not in LOOSE or r.get('tel') or r.get('persistent') or not e or 'door' in e.lower() or not any(w in e.lower() for w in CLUTTER):
            continue
        b = obnd(r['base'])
        rs = float(r.get('s') or 1.0)
        if not b or (b[3] - b[0]) * (b[4] - b[1]) * rs * rs > SMALL:
            continue
        dx, dy = p[0] - door_p[0], p[1] - door_p[1]
        along, across = dx * nx + dy * ny, dx * tx + dy * ty
        reach = max(abs(v) for v in (b[0], b[1], b[3], b[4])) * rs
        if -20 - reach <= along <= CLEAR_DEEP + reach and abs(across) <= half + reach and p[2] < foot + 220 and p[2] + b[5] * rs > foot - 20:
            found.append((ck, rk, e))
    return found
