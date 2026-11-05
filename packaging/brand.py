"""FOLab's logo and icon, drawn from one set of shapes (the user's sketch): a pipe wrench whose jaws make the F, a gear
for the O, LAB underneath. Writes

    app/web/vendor/folab-mark.svg   the F-wrench and the gear (colour: currentColor, so the page's theme colours it)
    app/web/vendor/folab-icon.svg   the icon: the wrench before the gear on a dark rounded square
    app/web/vendor/folab-icon.png   the icon at 64 pixels (the page's tab and window icon)
    app/web/vendor/folab.ico        the icon at 16 to 256 pixels (FOLab.exe, the taskbar)

Run:  py -3 packaging/brand.py   (standard library only: the shapes are rasterised here, four samples a pixel)"""
import math
import os
import struct
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
VENDOR = os.path.join(HERE, '..', 'app', 'web', 'vendor')


# ---------- the shapes (y down) ----------

def wrench(ox=0, oy=0, s=1.0):
    """The F: the wrench's top jaw (F's top arm, teeth under it), its lower jaw (the middle arm, teeth on top), the
    spine down the back, the adjusting nut, and the handle."""
    P = lambda pts: [(ox + x * s, oy + y * s) for x, y in pts]
    top = [(0, 0), (104, 0), (104, 34)]
    for i in range(7):                                      # (teeth along the jaw's underside, right to left)
        x = 104 - i * 10
        top += [(x, 34), (x - 5, 42), (x - 10, 34)]
    top += [(30, 34), (30, 66), (0, 66)]
    lower = [(34, 56)]
    for i in range(6):
        x = 34 + i * 10
        lower += [(x, 56), (x + 5, 48), (x + 10, 56)]
    lower += [(96, 56), (96, 78), (34, 78)]
    nut = [(2, 74), (30, 74), (30, 128), (2, 128)]
    handle = [(40, 78), (72, 78), (76, 196), (36, 196)]
    return [P(top), P(lower), P(nut), P(handle)]


def gear(cx, cy, r_out, r_root, teeth=12, r_hole=0.0, steps=6):
    """A gear's outline (and its hole, wound the other way)."""
    pts = []
    for t in range(teeth):
        a0 = 2 * math.pi * t / teeth
        da = 2 * math.pi / teeth
        for frac, r in ((0.0, r_root), (0.12, r_out), (0.5, r_out), (0.62, r_root)):
            a = a0 + frac * da
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
        for k in range(1, steps):                          # (the root between teeth, round)
            a = a0 + (0.62 + 0.38 * k / steps) * da
            pts.append((cx + r_root * math.cos(a), cy + r_root * math.sin(a)))
    out = [pts]
    if r_hole:
        out.append([(cx + r_hole * math.cos(-2 * math.pi * k / 40), cy + r_hole * math.sin(-2 * math.pi * k / 40)) for k in range(40)])
    return out


def path_d(polys):
    return ' '.join('M' + ' L'.join('%.1f %.1f' % p for p in poly) + ' Z' for poly in polys)


# ---------- SVG ----------

def mark_svg():
    """The F-wrench before the gear, 230 x 210, in currentColor: the gear an outline, big and fat-toothed, tucked
    behind the wrench (a rim of the header's colour round the wrench keeps them apart)."""
    g = gear(150, 104, 88, 70, 10, 30)
    x0, y0, x1, y1 = _mark_box()
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="%.0f %.0f %.0f %.0f">' % (x0 - 2, y0 - 2, x1 - x0 + 4, y1 - y0 + 4) +
            '<path fill="none" stroke="currentColor" stroke-width="11" stroke-linejoin="round" d="%s"/>'
            '<path fill="currentColor" fill-rule="evenodd" stroke="var(--bg3,#1d1914)" stroke-width="9" paint-order="stroke" '
            'stroke-linejoin="round" d="%s"/>'
            '<g stroke="rgba(0,0,0,0.35)" stroke-width="2.5">%s</g></svg>') % (
        path_d(g), path_d(wrench(8, 4)),
        ''.join('<line x1="12" y1="%d" x2="36" y2="%d"/>' % (y, y) for y in range(88, 130, 8)))   # (the nut's knurls)


ICON_BG, ICON_RIM, ICON_GEAR, ICON_WRENCH = (7, 15, 9), (31, 74, 44), (61, 242, 122), (138, 255, 172)   # (the Pip-Boy theme's greens)


ICON_GOLD, ICON_LIGHT = (52, 214, 108), (138, 255, 172)
MARK_SCALE = 0.92                  # (the mark in the 256 x 256 icon, centred on its own extent...)
MARK_NUDGE = (0, 3)                # (...then moved toward where its weight is: the solid wrench outweighs the gear's outline)


def _mark_box():
    """The mark's extent (the wrench, and the gear with its outline), in its own units."""
    pts = [p for poly in wrench(8, 4) + gear(150, 104, 88, 70, 10, 30) for p in poly]
    pad = 13 / 2
    return (min(x for x, _y in pts) - pad, min(y for _x, y in pts) - pad,
            max(x for x, _y in pts) + pad, max(y for _x, y in pts) + pad)


def _fit(polys):
    x0, y0, x1, y1 = _mark_box()
    s = MARK_SCALE
    ox, oy = 128 - (x0 + x1) / 2 * s + MARK_NUDGE[0], 128 - (y0 + y1) / 2 * s + MARK_NUDGE[1]
    return [[(ox + x * s, oy + y * s) for x, y in poly] for poly in polys]


def icon_layers():
    """The icon, 256 x 256, in the logo's style: the outline gear tucked behind the wrench-F, gold on a dark square.
    [(kind, colour, polygons, width)] painted in order: 'fill', or 'stroke' (a band width wide along the outlines)."""
    corner = 40
    sq = []
    for cxx, cyy, a0 in ((256 - corner, corner, -90), (256 - corner, 256 - corner, 0), (corner, 256 - corner, 90), (corner, corner, 180)):
        for k in range(9):
            a = math.radians(a0 + 90 * k / 8)
            sq.append((cxx + corner * math.cos(a), cyy + corner * math.sin(a)))
    inner = [((x - 128) * 0.95 + 128, (y - 128) * 0.95 + 128) for x, y in sq]
    sc = MARK_SCALE
    g, w = _fit(gear(150, 104, 88, 70, 10, 30)), _fit(wrench(8, 4))
    return [('fill', ICON_RIM, [sq], 0), ('fill', ICON_BG, [inner], 0),
            ('stroke', ICON_GOLD, g, 13 * sc),
            ('stroke', ICON_BG, w, 11 * sc), ('fill', ICON_LIGHT, w, 0)]


def icon_svg():
    out = []
    for kind, c, polys, width in icon_layers():
        rgb = 'rgb(%d,%d,%d)' % c
        if kind == 'fill':
            out.append('<path fill="%s" fill-rule="evenodd" d="%s"/>' % (rgb, path_d(polys)))
        else:
            out.append('<path fill="none" stroke="%s" stroke-width="%.1f" stroke-linejoin="round" d="%s"/>' % (rgb, width, path_d(polys)))
    return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256">%s</svg>' % ''.join(out)


# ---------- pixels ----------

def inside(x, y, polys):
    """Even-odd: inside the outline and not in a hole."""
    n = False
    for poly in polys:
        j = len(poly) - 1
        for i in range(len(poly)):
            (xi, yi), (xj, yj) = poly[i], poly[j]
            if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
                n = not n
            j = i
    return n


def near_edge(x, y, segs, half):
    for ax, ay, bx, by, L2 in segs:
        if (x < min(ax, bx) - half or x > max(ax, bx) + half or y < min(ay, by) - half or y > max(ay, by) + half):
            continue
        t = 0.0 if not L2 else max(0.0, min(1.0, ((x - ax) * (bx - ax) + (y - ay) * (by - ay)) / L2))
        dx, dy = x - ax - t * (bx - ax), y - ay - t * (by - ay)
        if dx * dx + dy * dy <= half * half:
            return True
    return False


def render(size):
    layers = []
    for kind, c, polys, width in icon_layers():
        segs = [(a[0], a[1], b[0], b[1], (b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2)
                for poly in polys for a, b in zip(poly, poly[1:] + poly[:1])]
        box = (min(x for p in polys for x, _y in p) - width, min(y for p in polys for _x, y in p) - width,
               max(x for p in polys for x, _y in p) + width, max(y for p in polys for _x, y in p) + width)
        layers.append((kind, c, polys, width / 2, segs, box))
    k = 256.0 / size
    ss = 4 if size <= 64 else 2
    px = bytearray(size * size * 4)
    for y in range(size):
        for x in range(size):
            r = g = b = a = 0.0
            for sy in range(ss):
                for sx in range(ss):
                    X, Y = (x + (sx + 0.5) / ss) * k, (y + (sy + 0.5) / ss) * k
                    col = None
                    for kind, c, polys, half, segs, box in layers:
                        if not (box[0] <= X <= box[2] and box[1] <= Y <= box[3]):
                            continue
                        if (inside(X, Y, polys) if kind == 'fill' else near_edge(X, Y, segs, half)):
                            col = c
                    if col:
                        r += col[0]; g += col[1]; b += col[2]; a += 1
            if a:
                px[(y * size + x) * 4:(y * size + x + 1) * 4] = bytes((int(r / a), int(g / a), int(b / a), int(255 * a / ss / ss)))
    return px


def png(size, px):
    raw = b''.join(b'\0' + bytes(px[y * size * 4:(y + 1) * size * 4]) for y in range(size))

    def chunk(t, d):
        return struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', size, size, 8, 6, 0, 0, 0)) +
            chunk(b'IDAT', zlib.compress(raw, 9)) + chunk(b'IEND', b''))


def ico(images):
    head = struct.pack('<HHH', 0, 1, len(images))
    offset = 6 + 16 * len(images)
    entries = b''
    for s, img in images:
        entries += struct.pack('<BBBBHHII', s % 256, s % 256, 0, 0, 1, 32, len(img), offset)
        offset += len(img)
    return head + entries + b''.join(img for _s, img in images)


def main():
    os.makedirs(VENDOR, exist_ok=True)
    with open(os.path.join(VENDOR, 'folab-mark.svg'), 'w', encoding='utf-8') as f:
        f.write(mark_svg())
    with open(os.path.join(VENDOR, 'folab-icon.svg'), 'w', encoding='utf-8') as f:
        f.write(icon_svg())
    images = [(s, png(s, render(s))) for s in (16, 24, 32, 48, 64, 256)]
    with open(os.path.join(VENDOR, 'folab-icon.png'), 'wb') as f:
        f.write(dict(images)[64])
    with open(os.path.join(VENDOR, 'folab.ico'), 'wb') as f:
        f.write(ico(images))
    print('logo and icon written to', os.path.normpath(VENDOR))


if __name__ == '__main__':
    main()
