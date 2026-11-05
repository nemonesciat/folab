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
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 204">'
            '<path fill="none" stroke="currentColor" stroke-width="11" stroke-linejoin="round" d="%s"/>'
            '<path fill="currentColor" fill-rule="evenodd" stroke="var(--bg3,#1d1914)" stroke-width="9" paint-order="stroke" '
            'stroke-linejoin="round" d="%s"/>'
            '<g stroke="rgba(0,0,0,0.35)" stroke-width="2.5">%s</g></svg>') % (
        path_d(g), path_d(wrench(8, 4)),
        ''.join('<line x1="12" y1="%d" x2="36" y2="%d"/>' % (y, y) for y in range(88, 130, 8)))   # (the nut's knurls)


ICON_BG, ICON_RIM, ICON_GEAR, ICON_WRENCH = (27, 24, 19), (70, 60, 46), (210, 168, 90), (236, 228, 210)


def icon_layers():
    """The icon, 256 x 256: [(colour, polygons)] painted in order."""
    corner = 44
    sq = []
    for cxx, cyy, a0 in ((256 - corner, corner, -90), (256 - corner, 256 - corner, 0), (corner, 256 - corner, 90), (corner, corner, 180)):
        for k in range(9):
            a = math.radians(a0 + 90 * k / 8)
            sq.append((cxx + corner * math.cos(a), cyy + corner * math.sin(a)))
    inner = [((x - 128) * 0.94 + 128, (y - 128) * 0.94 + 128) for x, y in sq]
    return [(ICON_RIM, [sq]), (ICON_BG, [inner]),
            (ICON_GEAR, gear(150, 118, 92, 74, 12, 32)),
            (ICON_WRENCH, wrench(34, 30, 1.0))]


def icon_svg():
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256">%s</svg>' %
            ''.join('<path fill="rgb(%d,%d,%d)" fill-rule="evenodd" d="%s"/>' % (c + (path_d(p),)) for c, p in icon_layers()))


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


def render(size):
    layers = icon_layers()
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
                    for c, polys in layers:
                        if inside(X, Y, polys):
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
