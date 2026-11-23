"""Footings: closed bases of FOLab's own set under a building's walls where daylight still shows after the land was raised
(floatfit.fix): a road along the wall (its ground stays), a lower neighbour against it, a corner between land points, water.

A footing is a solid block THICK deep, LENGTHS long and HEIGHTS tall, its outer face flush with the wall's face, its top TUCK
above the building's foot (hidden under the wall's bottom), going down past the lowest land along it by SINK. Concrete under
the game's buildings, black lava stone under FOLab's own. The blocks are pieces of their own (meshes\\folab\\footing), made
here with modelmake; `pieces()` is their descriptions, `plan()` where they go, `ops()` both as the mod's changes.

In a footing's own frame: x along the wall, its outer face at y 0 facing -y, the building on +y, its top at z 0."""
import math

import floatfit

THICK = 48.0
LENGTHS = (1024.0, 512.0, 256.0, 128.0)
HEIGHTS = (64.0, 128.0, 256.0, 512.0)
TUCK = 8.0                     # (its top this far over the foot: hidden by the wall's bottom, no seam)
SINK = 24.0                    # (its bottom this far under the lowest land along it)
SAMPLE = 32.0
LOOKS = {'concrete': ('concrete', 96), 'stone': ('hotel/lava', 300)}
FOLDER = 'footing'


def edid_of(look, length, height):
    return 'FOLabFooting%s%dx%d' % (look.title(), length, height)


def model_of(look, length, height):
    return 'folab\\%s\\%s_%d_%d.nif' % (FOLDER, look, length, height)


def describe(look, length, height):
    import modelsets
    tex, tile = LOOKS[look]
    return {'name': edid_of(look, length, height), 'ground': False, 'bevel': 0,
            'looks': {'f': modelsets.look(tex, tile=tile)},
            'parts': [{'shape': 'box', 'size': [length, THICK, height], 'at': [0, THICK / 2, -height], 'look': 'f', 'solid': True,
                       'material': 'stone' if look == 'stone' else 'concrete'}]}


def side_frames(b):
    """Each wall of a building's box: (name, start (lx, ly), along (ux, uy), length, turn of a footing on it), in the building's
    frame, scaled. A footing on it turns by the building's turn plus that, so its +y points into the building."""
    o, s = b['ob'], b['s']
    x0, y0, x1, y1 = o[0] * s, o[1] * s, o[3] * s, o[4] * s
    return [('south', (x0, y0), (1.0, 0.0), x1 - x0, 0.0),
            ('north', (x1, y1), (-1.0, 0.0), x1 - x0, math.pi),
            ('west', (x0, y1), (0.0, -1.0), y1 - y0, math.pi / 2),
            ('east', (x1, y0), (0.0, 1.0), y1 - y0, -math.pi / 2)]


def _out_of(along):
    """The outward normal of a wall walked anticlockwise round the box: its right."""
    return along[1], -along[0]


def plan(L, b, foot, gap_over=floatfit.DONE / 2):
    """[{look-free block: 'p' (x, y, z, 0, 0, rz), 'length', 'height'}] for one building: blocks wherever the land OUT past a wall
    lies more than gap_over under its foot."""
    p = b['p']
    out = []
    for _name, (sx, sy), (ux, uy), length, turn in side_frames(b):
        if length < 64:
            continue
        nx, ny = _out_of((ux, uy))
        n = max(2, int(length // SAMPLE) + 1)
        low = []
        for i in range(n):
            t = length * i / (n - 1)
            lx, ly = sx + ux * t, sy + uy * t
            gs = []
            for d in (0.0, floatfit.OUT):
                g = L.at(*floatfit._world(p, lx + nx * d, ly + ny * d))
                if g is not None:
                    gs.append(g)
            low.append((t, min(gs) if gs else None))
        # stretches of the wall over low land, widened a little either way
        runs, cur = [], None
        for t, g in low:
            bad = g is not None and foot - g > gap_over
            if bad and cur is None:
                cur = [t, t]
            elif bad:
                cur[1] = t
            elif cur is not None:
                runs.append(cur)
                cur = None
        if cur is not None:
            runs.append(cur)
        for a, z in runs:
            a, z = max(0.0, a - 96.0), min(length, z + 96.0)
            t = a
            while t < z - 1.0:
                left = z - t
                size = next((l for l in LENGTHS if l <= left + 64.0), LENGTHS[-1])
                if t + size > length:
                    t = max(0.0, length - size)
                mid = t + size / 2
                lows = [g for tt, g in low if t - 1 <= tt <= t + size + 1 and g is not None]
                if not lows:
                    t += size
                    continue
                top = foot + TUCK
                need = top - (min(lows) - SINK)
                height = next((h for h in HEIGHTS if h >= need), HEIGHTS[-1])
                lx, ly = sx + ux * mid, sy + uy * mid
                wx, wy = floatfit._world(p, lx, ly)
                rz = (p[5] + turn) % (2 * math.pi)
                out.append({'p': [round(wx, 2), round(wy, 2), round(top, 2), 0.0, 0.0, round(rz, 4)], 'length': size, 'height': height})
                if need > HEIGHTS[-1]:       # (deeper than the tallest: another under it)
                    out.append({'p': [round(wx, 2), round(wy, 2), round(top - HEIGHTS[-1], 2), 0.0, 0.0, round(rz, 4)], 'length': size,
                                'height': next((h for h in HEIGHTS if h >= need - HEIGHTS[-1]), HEIGHTS[-1])})
                t += size
    return out


def look_for(b):
    """Lava stone under FOLab's own buildings, concrete under the game's."""
    return 'stone' if b.get('folder') else 'concrete'
