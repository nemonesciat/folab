"""Is a spot somewhere a person can stand and walk off from? For a start point (New Game, Play here) on a world the mod
has filled: a spot inside a building's box, or hemmed in by them, is no place to begin.

Goes by each placed thing's bounds (OBND, turned and sized as placed): what's under knee height (a road piece, a decal)
doesn't count. It can't see inside a model, so a courtyard reads as its building: that errs toward moving the start."""
import math
import struct

LOW = 60.0              # (a thing no taller than this is walked over)
WALK = 900.0            # (how far a person should be able to walk in a straight line from where they start)
WAYS = 8
BODY = 48.0


class Standing:
    """Every thing the mod has placed in a world, to ask spots against."""

    def __init__(self, gd, pr, world):
        self.by = {}
        self.all = []
        boxes = {}
        for cell in gd.grid(world).values():
            c = pr.cells.get(gd.key(cell))
            for rk, r in (c['refs'].items() if c else ()):
                p, key = r.get('p'), r.get('base')
                if not p or not key or r.get('removed'):
                    continue
                if key not in boxes:
                    boxes[key] = None
                    try:
                        fid = gd.from_key(key)
                        o = gd.fields(fid).get('OBND') if fid in gd.forms else None
                        if o and len(o) >= 12:
                            b = struct.unpack_from('<6h', o)
                            if b[5] - b[2] > LOW and b[3] > b[0] and b[4] > b[1] and 'marker' not in gd.edid(fid).lower():      # (markers aren't there in the game)
                                boxes[key] = (b, gd.edid(fid))
                    except (ValueError, KeyError):
                        pass
                if not boxes[key]:
                    continue
                b, edid = boxes[key]
                s = float(r.get('s') or 1.0)
                n = len(self.all)
                self.all.append((p[0], p[1], math.cos(p[5]), math.sin(p[5]), b[0] * s, b[1] * s, b[3] * s, b[4] * s, edid))
                rad = math.hypot(max(abs(b[0]), abs(b[3])), max(abs(b[1]), abs(b[4]))) * s + BODY
                for i in range(int((p[0] - rad) // 1024), int((p[0] + rad) // 1024) + 1):
                    for j in range(int((p[1] - rad) // 1024), int((p[1] + rad) // 1024) + 1):
                        self.by.setdefault((i, j), []).append(n)

    def inside(self, x, y, margin=BODY):
        """The editor ID of something whose box this spot is in, or None."""
        for n in self.by.get((int(x // 1024), int(y // 1024)), ()):
            ox, oy, c, s, x0, y0, x1, y1, edid = self.all[n]
            dx, dy = x - ox, y - oy
            lx, ly = dx * c - dy * s, dx * s + dy * c
            if x0 - margin <= lx <= x1 + margin and y0 - margin <= ly <= y1 + margin:
                return edid
        return None

    def ways(self, x, y, far=WALK):
        """How many of eight straight lines from here run `far` without meeting anything."""
        n = 0
        for k in range(WAYS):
            a = k * math.tau / WAYS
            if not any(self.inside(x + math.sin(a) * d, y + math.cos(a) * d) for d in range(64, int(far) + 1, 64)):
                n += 1
        return n

    def clear(self, x, y):
        """(ok, why not). A start wants nothing over it and most ways open."""
        hit = self.inside(x, y)
        if hit:
            return False, 'inside ' + hit
        w = self.ways(x, y)
        if w < WAYS - 2:
            return False, 'hemmed in: only %d of %d ways are open' % (w, WAYS)
        return True, ''
