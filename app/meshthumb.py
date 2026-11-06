"""Small pictures: a mesh drawn from three-quarters above by a plain software renderer, and PNG files to hold them.

Browsers can't show a DDS and a grid of hundreds of meshes won't fit in graphics contexts, so the Library's thumbnails
are made here. Each triangle is one flat colour, taken from a small copy of its texture at the triangle's middle and
lit by how it faces: enough to know a chair from a crate at a glance."""
import math
import struct
import zlib

CHUNK = lambda tag, data: struct.pack('>I', len(data)) + tag + data + struct.pack('>I', zlib.crc32(tag + data) & 0xFFFFFFFF)


def png_rgba(w, h, rgba):
    """A PNG from RGBA bytes, rows from the top."""
    raw = b''.join(b'\0' + rgba[y * w * 4:(y + 1) * w * 4] for y in range(h))
    return (b'\x89PNG\r\n\x1a\n' + CHUNK(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 6, 0, 0, 0)) +
            CHUNK(b'IDAT', zlib.compress(raw, 6)) + CHUNK(b'IEND', b''))


def read_png(data):
    """(w, h, RGBA bytes) from a PNG: 8 or 16 bits, grey, grey + alpha, RGB, RGBA or palette, not interlaced."""
    if data[:8] != b'\x89PNG\r\n\x1a\n':
        raise ValueError('not a PNG')
    p, idat, pal, trns = 8, bytearray(), None, None
    w = h = depth = ctype = 0
    while p < len(data):
        n, tag = struct.unpack_from('>I4s', data, p)
        d = data[p + 8:p + 8 + n]
        if tag == b'IHDR':
            w, h, depth, ctype, _c, _f, inter = struct.unpack('>IIBBBBB', d)
            if inter:
                raise ValueError('an interlaced PNG: save it without interlacing')
        elif tag == b'PLTE':
            pal = d
        elif tag == b'tRNS':
            trns = d
        elif tag == b'IDAT':
            idat += d
        p += 12 + n
    chans = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[ctype]
    bpp = max(1, chans * depth // 8)
    stride = (w * chans * depth + 7) // 8
    raw = zlib.decompress(bytes(idat))
    prev = bytearray(stride)
    out = bytearray(w * h * 4)
    for y in range(h):
        f = raw[y * (stride + 1)]
        row = bytearray(raw[y * (stride + 1) + 1:(y + 1) * (stride + 1)])
        for i in range(stride):
            a = row[i - bpp] if i >= bpp else 0
            b = prev[i]
            c = prev[i - bpp] if i >= bpp else 0
            if f == 1:
                row[i] = (row[i] + a) & 255
            elif f == 2:
                row[i] = (row[i] + b) & 255
            elif f == 3:
                row[i] = (row[i] + (a + b) // 2) & 255
            elif f == 4:
                pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2 * c)
                row[i] = (row[i] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        prev = row
        for x in range(w):
            q = (y * w + x) * 4
            if depth == 16:
                v = [row[(x * chans + k) * 2] for k in range(chans)]
            elif depth == 8:
                v = row[x * chans:(x + 1) * chans]
            else:                                       # (1, 2 or 4 bits a pixel: grey or palette)
                bit = x * depth
                v = [(row[bit // 8] >> (8 - depth - bit % 8)) & ((1 << depth) - 1)]
                if ctype == 0:
                    v = [v[0] * 255 // ((1 << depth) - 1)]
            if ctype == 0:
                out[q:q + 4] = bytes((v[0], v[0], v[0], 255))
            elif ctype == 2:
                out[q:q + 4] = bytes((v[0], v[1], v[2], 255))
            elif ctype == 3:
                i = v[0]
                out[q:q + 4] = bytes((pal[i * 3], pal[i * 3 + 1], pal[i * 3 + 2], trns[i] if trns and i < len(trns) else 255))
            elif ctype == 4:
                out[q:q + 4] = bytes((v[0], v[0], v[0], v[1]))
            else:
                out[q:q + 4] = bytes(v)
    return w, h, bytes(out)


def read_tga(data):
    """(w, h, RGBA bytes) from a TGA: 24 or 32 bits, plain or run-length packed."""
    idl, _map, kind = data[0], data[1], data[2]
    w, h, bits, desc = struct.unpack_from('<HHBB', data, 12)
    if kind not in (2, 10) or bits not in (24, 32):
        raise ValueError('only 24- and 32-bit colour TGA pictures can be brought in')
    n, p = bits // 8, 18 + idl
    px = bytearray()
    if kind == 2:
        px = data[p:p + w * h * n]
    else:
        while len(px) < w * h * n:
            c = data[p]
            p += 1
            if c & 0x80:
                px += data[p:p + n] * ((c & 0x7F) + 1)
                p += n
            else:
                px += data[p:p + n * (c + 1)]
                p += n * (c + 1)
    out = bytearray(w * h * 4)
    top = desc & 0x20
    for y in range(h):
        row = y if top else h - 1 - y
        for x in range(w):
            s = (row * w + x) * n
            q = (y * w + x) * 4
            out[q:q + 4] = bytes((px[s + 2], px[s + 1], px[s], px[s + 3] if n == 4 else 255))
    return w, h, bytes(out)


def read_bmp(data):
    """(w, h, RGBA bytes) from an uncompressed 24- or 32-bit BMP."""
    off, _hs, w, h, _pl, bits, comp = struct.unpack_from('<IIiiHHI', data, 10)
    if bits not in (24, 32) or comp not in (0, 3):
        raise ValueError('only uncompressed 24- and 32-bit BMP pictures can be brought in')
    n, stride = bits // 8, (w * bits // 8 + 3) & ~3
    top = h < 0
    h = abs(h)
    out = bytearray(w * h * 4)
    for y in range(h):
        row = off + (y if top else h - 1 - y) * stride
        for x in range(w):
            s = row + x * n
            q = (y * w + x) * 4
            out[q:q + 4] = bytes((data[s + 2], data[s + 1], data[s], data[s + 3] if n == 4 and comp == 3 else 255))
    return w, h, bytes(out)


# the view: from a quarter round and above
_YAW, _PITCH = math.radians(-35), math.radians(28)
_CY, _SY, _CP, _SP = math.cos(_YAW), math.sin(_YAW), math.cos(_PITCH), math.sin(_PITCH)
_LIGHT = (0.45, -0.55, 0.70)


def draw(shapes, tex_of, size=128, max_tris=40000):
    """A picture of a mesh's shapes (nif.mesh_from_nif's). tex_of(path) gives a small copy of a texture as (w, h, RGBA)
    or None. Returns (w, h, RGBA bytes), or None when there's nothing to draw. Drawn at twice the size, then halved."""
    total = sum(len(s['i']) // 3 for s in shapes)
    solid = [s for s in shapes if s['alpha'] != 'blend'] or shapes
    if not total:
        return None
    # the corners, turned to the view: x across, y up the picture, z towards the viewer
    tx = []
    lo = [1e30, 1e30]
    hi = [-1e30, -1e30]
    for s in solid:
        p = s['p']
        pts = []
        for k in range(0, len(p), 3):
            x, y, z = p[k], p[k + 1], p[k + 2]
            if x != x or y != y or z != z:              # (a few of the game's meshes hold not-a-number corners)
                x = y = z = 0.0
            rx = x * _CY - y * _SY
            ry = x * _SY + y * _CY
            sy = z * _CP + ry * _SP
            sz = ry * _CP - z * _SP
            pts.append((rx, sy, sz, x, y, z))
            lo[0] = min(lo[0], rx); hi[0] = max(hi[0], rx)
            lo[1] = min(lo[1], sy); hi[1] = max(hi[1], sy)
        tx.append(pts)
    n = size * 2
    span = max(hi[0] - lo[0], hi[1] - lo[1], 1e-3)
    scale = (n - 8) / span
    ox, oy = (n - (hi[0] - lo[0]) * scale) / 2 - lo[0] * scale, (n - (hi[1] - lo[1]) * scale) / 2 - lo[1] * scale
    zbuf = [1e30] * (n * n)
    col = [None] * (n * n)
    stride = max(1, total // max_tris)
    for s, pts in zip(solid, tx):
        tex = tex_of(s['tex']) if s['tex'] else None
        uv, idx = s['uv'], s['i']
        has_uv = len(uv) == len(s['p']) // 3 * 2
        for t in range(0, len(idx) - 2, 3 * stride):
            ia, ib, ic = idx[t], idx[t + 1], idx[t + 2]
            a, b, c = pts[ia], pts[ib], pts[ic]
            ux, uy, uz = b[3] - a[3], b[4] - a[4], b[5] - a[5]
            vx, vy, vz = c[3] - a[3], c[4] - a[4], c[5] - a[5]
            nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
            ln = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
            light = 0.6 + 0.55 * abs(nx * _LIGHT[0] + ny * _LIGHT[1] + nz * _LIGHT[2]) / ln
            r, g, bl = 176, 164, 140
            if tex and has_uv:
                w, h, px = tex
                u = (uv[ia * 2] + uv[ib * 2] + uv[ic * 2]) / 3
                v = (uv[ia * 2 + 1] + uv[ib * 2 + 1] + uv[ic * 2 + 1]) / 3
                q = (int((v - math.floor(v)) * h) % h * w + int((u - math.floor(u)) * w) % w) * 4
                if px[q + 3] < 90 and s['alpha'] == 'test':
                    continue
                r, g, bl = px[q], px[q + 1], px[q + 2]
            shade = (min(255, int(r * light)), min(255, int(g * light)), min(255, int(bl * light)))
            ax, ay = a[0] * scale + ox, n - (a[1] * scale + oy)
            bx, by = b[0] * scale + ox, n - (b[1] * scale + oy)
            cx, cy = c[0] * scale + ox, n - (c[1] * scale + oy)
            x0, x1 = int(max(0, min(ax, bx, cx))), int(min(n - 1, max(ax, bx, cx) + 1))
            y0, y1 = int(max(0, min(ay, by, cy))), int(min(n - 1, max(ay, by, cy) + 1))
            den = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
            if abs(den) < 1e-6:
                continue
            az, bz, cz = a[2], b[2], c[2]
            d1x, d1y = (by - cy) / den, (cx - bx) / den
            d2x, d2y = (cy - ay) / den, (ax - cx) / den
            for y in range(y0, y1 + 1):
                row = y * n
                py = y + 0.5 - cy
                w1 = d1x * (x0 + 0.5 - cx) + d1y * py
                w2 = d2x * (x0 + 0.5 - cx) + d2y * py
                for x in range(x0, x1 + 1):
                    w3 = 1 - w1 - w2
                    if w1 >= -0.01 and w2 >= -0.01 and w3 >= -0.01:
                        d = w1 * az + w2 * bz + w3 * cz
                        if d < zbuf[row + x]:
                            zbuf[row + x] = d
                            col[row + x] = shade
                    w1 += d1x
                    w2 += d2x
    out = bytearray(size * size * 4)
    for y in range(size):
        for x in range(size):
            r = g = bl = k = 0
            for off in (0, 1, n, n + 1):
                c = col[y * 2 * n + x * 2 + off]
                if c:
                    r += c[0]; g += c[1]; bl += c[2]; k += 1
            if k:
                q = (y * size + x) * 4
                out[q], out[q + 1], out[q + 2], out[q + 3] = r // k, g // k, bl // k, k * 255 // 4
    return size, size, bytes(out)
