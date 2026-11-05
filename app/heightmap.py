"""Height maps: an area of a worldspace's ground as a 16-bit greyscale PNG, to work on in other tools (GIMP, Krita,
World Machine, Gaea), and back.

One pixel per land point: a cell is 32 pixels across, and the cells' shared edge points are one pixel, so an area
w x h cells is (32w + 1) x (32h + 1) pixels, north at the top. Black is the area's lowest point, white its highest.
The file carries where it came from and its height range in a text chunk ('FOLab': world key, corner cell, lowest,
highest), so it goes back to the same place at the same heights. A picture without one is laid on the area asked
for, black to white over the range asked for.

Coming back, the area's outer edge keeps the heights it has (the cells round it share those points, so the ground
still meets them); the writer keeps every point in the 8-unit steps the game stores."""
import json
import struct
import zlib

SIDE = 33


# ---------- PNG ----------

def write_png16(width, height, values, text=None):
    """A 16-bit greyscale PNG; values row by row from the top, 0-65535."""
    raw = bytearray()
    for r in range(height):
        raw.append(0)
        raw += struct.pack('>%dH' % width, *values[r * width:(r + 1) * width])

    def chunk(tag, data):
        return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', zlib.crc32(tag + data) & 0xFFFFFFFF)
    out = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 16, 0, 0, 0, 0))
    if text:
        out += chunk(b'tEXt', b'FOLab\0' + json.dumps(text).encode())
    return out + chunk(b'IDAT', zlib.compress(bytes(raw), 6)) + chunk(b'IEND', b'')


def read_png(data):
    """(width, height, [values 0-1 row by row from the top], FOLab text or None). Greyscale, grey+alpha, RGB or RGBA,
    8 or 16 bits (colour: its brightness); not palette pictures or interlaced ones."""
    if data[:8] != b'\x89PNG\r\n\x1a\n':
        raise ValueError('not a PNG picture')
    pos, idat, text, head = 8, bytearray(), None, None
    while pos + 8 <= len(data):
        n, tag = struct.unpack('>I4s', data[pos:pos + 8])
        body = data[pos + 8:pos + 8 + n]
        if tag == b'IHDR':
            head = struct.unpack('>IIBBBBB', body)
        elif tag == b'IDAT':
            idat += body
        elif tag == b'tEXt' and body.startswith(b'FOLab\0'):
            try:
                text = json.loads(body[6:].decode())
            except ValueError:
                text = None
        elif tag == b'IEND':
            break
        pos += 12 + n
    if not head:
        raise ValueError('the PNG has no header')
    w, h, depth, ctype, _c, _f, interlace = head
    if interlace or ctype == 3 or depth not in (8, 16):
        raise ValueError('save it as plain greyscale or RGB, 8 or 16 bits, not interlaced')
    chans = {0: 1, 2: 3, 4: 2, 6: 4}[ctype]
    bpp = chans * depth // 8
    stride = w * bpp
    raw = zlib.decompress(bytes(idat))
    rows, prev, k = [], bytearray(stride), 0
    for _ in range(h):
        ft, line = raw[k], bytearray(raw[k + 1:k + 1 + stride])
        k += 1 + stride
        for i in range(stride):
            a = line[i - bpp] if i >= bpp else 0
            b = prev[i]
            c = prev[i - bpp] if i >= bpp else 0
            if ft == 1:
                line[i] = (line[i] + a) & 255
            elif ft == 2:
                line[i] = (line[i] + b) & 255
            elif ft == 3:
                line[i] = (line[i] + (a + b) // 2) & 255
            elif ft == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                line[i] = (line[i] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        rows.append(line)
        prev = line
    top = 65535.0 if depth == 16 else 255.0
    vals = []
    for line in rows:
        if depth == 16:
            px = struct.unpack('>%dH' % (w * chans), bytes(line))
        else:
            px = line
        for x in range(w):
            s = px[x * chans:(x + 1) * chans]
            v = s[0] if chans <= 2 else 0.299 * s[0] + 0.587 * s[1] + 0.114 * s[2]
            vals.append(v / top)
    return w, h, vals, text


# ---------- the ground ----------

def export(heights_at, world_key, x0, y0, w, h):
    """PNG bytes for cells x0..x0+w-1, y0..y0+h-1. heights_at(cx, cy) -> 33*33 heights or None."""
    W, H = w * 32 + 1, h * 32 + 1
    grid = [None] * (W * H)
    for j in range(h):
        for i in range(w):
            hs = heights_at(x0 + i, y0 + j)
            if not hs:
                continue
            for r in range(SIDE):
                for c in range(SIDE):
                    grid[(H - 1 - (j * 32 + r)) * W + i * 32 + c] = hs[r * SIDE + c]
    have = [v for v in grid if v is not None]
    lo, hi = (min(have), max(have)) if have else (0.0, 1.0)
    if hi - lo < 8:
        hi = lo + 8
    vals = [0 if v is None else int(round((v - lo) / (hi - lo) * 65535)) for v in grid]
    return write_png16(W, H, vals, {'world': world_key, 'x': x0, 'y': y0, 'w': w, 'h': h, 'low': lo, 'high': hi})


def apply(png, heights_at, x0=None, y0=None, w=None, h=None, low=None, high=None):
    """New heights from a height map: {(cx, cy): 33*33 heights} for each cell it covers that has ground. The area
    and range come from the file's FOLab text, else from the arguments; a picture of another size is stretched over
    the area. The area's outer edge keeps its heights."""
    pw, ph, vals, text = read_png(png)
    t = text or {}
    x0 = t.get('x', x0); y0 = t.get('y', y0); w = t.get('w', w); h = t.get('h', h)
    low = t.get('low', low); high = t.get('high', high)
    if None in (x0, y0, w, h, low, high):
        raise ValueError('this picture says nothing of where it goes: give the area and the heights black and white stand for')
    W, H = w * 32 + 1, h * 32 + 1

    def sample(gx, gy):
        # the picture at land point (gx from the west, gy from the south), stretched over the area
        fx = gx * (pw - 1) / (W - 1) if W > 1 else 0
        fy = (H - 1 - gy) * (ph - 1) / (H - 1) if H > 1 else 0
        x1, y1 = int(fx), int(fy)
        x2, y2 = min(pw - 1, x1 + 1), min(ph - 1, y1 + 1)
        tx, ty = fx - x1, fy - y1
        v = (vals[y1 * pw + x1] * (1 - tx) + vals[y1 * pw + x2] * tx) * (1 - ty) + \
            (vals[y2 * pw + x1] * (1 - tx) + vals[y2 * pw + x2] * tx) * ty
        return low + v * (high - low)
    out = {}
    for j in range(h):
        for i in range(w):
            old = heights_at(x0 + i, y0 + j)
            if not old:
                continue
            new = []
            for r in range(SIDE):
                for c in range(SIDE):
                    gx, gy = i * 32 + c, j * 32 + r
                    edge = gx in (0, W - 1) or gy in (0, H - 1)
                    v = old[r * SIDE + c] if edge else sample(gx, gy)
                    new.append(v if edge else round(v, 2))
            out[(x0 + i, y0 + j)] = new
    return out


def ground(h, lx, ly):
    """The ground's height at (lx, ly) inside a cell (0-4096 from its south-west corner), between its four points."""
    fx, fy = max(0.0, min(4096.0, lx)) / 128, max(0.0, min(4096.0, ly)) / 128
    c0, r0 = min(31, int(fx)), min(31, int(fy))
    tx, ty = fx - c0, fy - r0
    p = lambda r, c: h[r * SIDE + c]
    return (p(r0, c0) * (1 - tx) + p(r0, c0 + 1) * tx) * (1 - ty) + (p(r0 + 1, c0) * (1 - tx) + p(r0 + 1, c0 + 1) * tx) * ty
