"""Who holds a spot, read from the agreed concept map (docs/waikiki-territory-1124/who-holds-what-concept.png, the user's
"who holds what"), by its colours, as weaponsplace's wild-ground test reads it. Needs PIL (the developer's Python).

    Map(gd, world).holder(x, y)   'court', 'pirates', 'both', 'holdouts', 'huang', 'heights', 'vault', 'wild', or None
    pirates_misplaced(gd, pr)     every pirate of the mod's standing in another side's land
"""
import math

HOLDERS = ('court', 'pirates', 'both', 'holdouts', 'huang', 'heights', 'vault', 'wild')
# (the concept map's colours as it draws them over its shaded ground, measured inside each area: the creatures step's)
MEASURED = {'court': (200, 167, 97), 'pirates': (155, 75, 72), 'both': (177, 114, 63), 'holdouts': (90, 142, 90),
            'huang': (72, 151, 145), 'heights': (146, 120, 178), 'vault': (112, 122, 156), 'wild': (104, 114, 98)}
GREY = 10.0
HOLE = 7.0          # (pixels left out round the spot itself: the map's place diamonds and dots sit right on places)
NOT_PIRATES = ('court', 'huang', 'heights', 'vault', 'holdouts')     # (land where a pirate standing is misplaced)


def _chroma(c):
    t = float(sum(c)) or 1.0
    return (c[0] / t, c[1] / t, c[2] / t)


class Map:
    def __init__(self, gd, world):
        import weaponsplace
        self.c = weaponsplace._Concept(gd, world)
        self.colours = [MEASURED[h] for h in HOLDERS]
        self.chromas = [_chroma(h) for h in self.colours]

    @property
    def ok(self):
        return self.c.ok

    def holder(self, x, y, reach=14):           # (14 pixels: wide enough that the map's gold place diamonds and labels are outvoted)
        c = self.c
        if not c.ok:
            return None
        u, v = (x - c.x0 * 4096.0) / c.per, ((c.y0 + c.n) * 4096.0 - y) / c.per
        votes = [0] * len(self.colours)
        for j in range(int(v) - reach, int(v) + reach + 1, 2):
            for i in range(int(u) - reach, int(u) + reach + 1, 2):
                if 0 <= i < c.size and 0 <= j < c.size and (i - u) ** 2 + (j - v) ** 2 >= HOLE ** 2:
                    px = c.img.getpixel((i, j))
                    if sum(px) < 120 or max(px) - min(px) < GREY:      # (the sea, a label, the frame: no one's)
                        continue
                    q = _chroma(px)                   # (by hue: the colours lie half-clear over dark ground, so a dark gold is still gold)
                    d = [sum((q[k] - h[k]) ** 2 for k in range(3)) for h in self.chromas]
                    best = min(range(len(d)), key=d.__getitem__)
                    if d[best] < 0.05 ** 2:
                        votes[best] += 1
        return HOLDERS[votes.index(max(votes))] if max(votes) > 0 else None


def pirates_misplaced(gd, pr, world_key=None):
    """[(where it stands, its record, its spot)] of every pirate of the mod's placed outside in land that isn't the
    pirates' (`NOT_PIRATES`), by the concept map. Pirates are records whose editor ID says Pirate (NPC_ or LVLN)."""
    import recordio
    worlds = {}
    out = []
    for ck, c in pr.cells.items():
        if ck.startswith('+'):
            continue
        try:
            w = gd.ext_cells.get(gd.from_key(ck))
        except (KeyError, ValueError):
            w = None
        if w is None or (world_key and gd.key(w) != world_key):
            continue
        for rk, r in (c.get('refs') or {}).items():
            b = r.get('base', '')
            if r.get('removed') or not r.get('p') or not b.startswith('+'):
                continue
            rec = pr.records.get(b) or {}
            e = recordio.field(rec, 'EDID') or '' if rec else ''
            if rec.get('type') not in ('NPC_', 'LVLN') or 'Pirate' not in e:
                continue
            m = worlds.setdefault(w, Map(gd, w))
            h = m.holder(r['p'][0], r['p'][1])
            if h in NOT_PIRATES:
                out.append({'holder': h, 'edid': e, 'cell': ck, 'ref': rk, 'p': [round(v) for v in r['p'][:3]]})
    return out
