"""A DDS texture's average colour, for drawing the ground on the flat map.

DDS: a 128-byte header (height at 12, width at 16, mipmap count at 28, the compression's four letters at 84), then
the picture at full size and each smaller copy after it. DXT1 keeps each 4 x 4 block of pixels as two colours (5-6-5
bits of red, green, blue) and a 2-bit choice per pixel among those two and two mixes of them; DXT3 and DXT5 put 8
bytes of transparency before the same colour block. The average is taken over a small copy (16 x 16), which the
texture keeps already shrunk."""
import struct


def _565(v):
    return ((v >> 11) & 31) * 255 // 31, ((v >> 5) & 63) * 255 // 63, (v & 31) * 255 // 31


def _block(b, off):
    c0, c1, bits = struct.unpack_from('<HHI', b, off)
    a, z = _565(c0), _565(c1)
    if c0 > c1:
        pal = [a, z, tuple((2 * x + y) // 3 for x, y in zip(a, z)), tuple((x + 2 * y) // 3 for x, y in zip(a, z))]
    else:
        pal = [a, z, tuple((x + y) // 2 for x, y in zip(a, z)), (0, 0, 0)]
    return [pal[(bits >> (2 * i)) & 3] for i in range(16)]


def info(data):
    """{'format', 'w', 'h', 'mips'} of a DDS file's bytes, or None."""
    if len(data) < 128 or data[:4] != b'DDS ':
        return None
    h, w = struct.unpack_from('<II', data, 12)
    mips = max(1, struct.unpack_from('<I', data, 28)[0])
    pf, four, bits = struct.unpack_from('<I4sI', data, 80)
    fmt = four.decode('ascii', 'replace').strip('\0') if pf & 4 else '%d-bit' % bits
    return {'format': fmt, 'w': w, 'h': h, 'mips': mips}


def _shift(mask):
    """How far right a colour mask's bits sit, and the most they can hold."""
    s = 0
    while mask and not mask >> s & 1:
        s += 1
    return s, (mask >> s) or 1


def decode(data, want=128):
    """The smallest stored copy of the picture at least want across, as (w, h, RGBA bytes, rows from the top); None
    for a picture this can't read. DXT1/3/5 and the plain formats the game uses."""
    if len(data) < 128 or data[:4] != b'DDS ':
        return None
    h, w = struct.unpack_from('<II', data, 12)
    mips = max(1, struct.unpack_from('<I', data, 28)[0])
    pf, four, bits, rm, gm, bm, am = struct.unpack_from('<I4sIIIII', data, 80)
    step = {b'DXT1': 8, b'DXT3': 16, b'DXT5': 16}.get(four) if pf & 4 else None
    if pf & 4 and not step:
        return None
    if not pf & 4 and bits not in (8, 16, 24, 32):
        return None
    size = lambda a, b: (max(1, (a + 3) // 4) * max(1, (b + 3) // 4) * step) if step else a * b * bits // 8
    off = 128
    for _ in range(mips - 1):
        nw, nh = max(1, w // 2), max(1, h // 2)
        if max(nw, nh) < want:
            break
        off += size(w, h)
        w, h = nw, nh
    if off + size(w, h) > len(data) or not w or not h:
        return None
    out = bytearray(w * h * 4)
    if not step:
        n = bits // 8
        rs, gs, bs, a_s = _shift(rm), _shift(gm), _shift(bm), _shift(am)
        lum = pf & 0x20000 or (pf & 2 and not rm)      # (grey, or alpha only)
        for i in range(w * h):
            v = int.from_bytes(data[off + i * n:off + (i + 1) * n], 'little')
            r, g, b = ((v >> rs[0]) & rs[1]) * 255 // rs[1], ((v >> gs[0]) & gs[1]) * 255 // gs[1], ((v >> bs[0]) & bs[1]) * 255 // bs[1]
            if lum:
                r = g = b = v & 0xFF if pf & 0x20000 else 255
            a = ((v >> a_s[0]) & a_s[1]) * 255 // a_s[1] if am else 255
            out[i * 4:i * 4 + 4] = bytes((r, g, b, a))
        return w, h, bytes(out)
    for by in range((h + 3) // 4):
        for bx in range((w + 3) // 4):
            o = off + (by * ((w + 3) // 4) + bx) * step
            pix = _block(data, o + step - 8)
            if four == b'DXT1':
                c0, c1 = struct.unpack_from('<HH', data, o)
                bits_ = struct.unpack_from('<I', data, o + 4)[0]
                alpha = [0 if c0 <= c1 and (bits_ >> (2 * i)) & 3 == 3 else 255 for i in range(16)]
            elif four == b'DXT3':
                v = int.from_bytes(data[o:o + 8], 'little')
                alpha = [((v >> (4 * i)) & 15) * 17 for i in range(16)]
            else:
                a0, a1 = data[o], data[o + 1]
                pal = [a0, a1] + ([((7 - k) * a0 + k * a1) // 7 for k in range(1, 7)] if a0 > a1
                                  else [((5 - k) * a0 + k * a1) // 5 for k in range(1, 5)] + [0, 255])
                v = int.from_bytes(data[o + 2:o + 8], 'little')
                alpha = [pal[(v >> (3 * i)) & 7] for i in range(16)]
            for i in range(16):
                x, y = bx * 4 + i % 4, by * 4 + i // 4
                if x < w and y < h:
                    q = (y * w + x) * 4
                    out[q], out[q + 1], out[q + 2] = pix[i]
                    out[q + 3] = alpha[i]
    return w, h, bytes(out)


def encode(w, h, rgba):
    """A plain 32-bit DDS with its full chain of smaller copies, from RGBA bytes (rows from the top): what a picture
    from elsewhere becomes for the game. Bigger than a compressed one, and exactly the picture."""
    chain = []
    cur, cw, ch = rgba, w, h
    while True:
        bgra = bytearray(cur)
        bgra[0::4], bgra[2::4] = cur[2::4], cur[0::4]
        chain.append(bytes(bgra))
        if cw == 1 and ch == 1:
            break
        cur, cw, ch = _half(cur, cw, ch)
    # flags: caps, height, width, pitch, pixel format, mipmap count; RGB + alpha masks in the pixel format
    head = b'DDS ' + struct.pack('<7I', 124, 0x2100F, h, w, w * 4, 0, len(chain)) + b'\0' * 44
    head += struct.pack('<2I4s5I', 32, 0x41, b'\0\0\0\0', 32, 0xFF0000, 0xFF00, 0xFF, 0xFF000000)
    head += struct.pack('<5I', 0x401008, 0, 0, 0, 0)
    return head + b''.join(chain)


def _half(px, w, h):
    """A picture at half the size, each pixel the mean of those it covers."""
    nw, nh = max(1, w // 2), max(1, h // 2)
    fx, fy = w // nw, h // nh
    out = bytearray(nw * nh * 4)
    for y in range(nh):
        for x in range(nw):
            for c in range(4):
                t = 0
                for dy in range(fy):
                    row = (y * fy + dy) * w
                    for dx in range(fx):
                        t += px[(row + x * fx + dx) * 4 + c]
                out[(y * nw + x) * 4 + c] = t // (fx * fy)
    return bytes(out), nw, nh


def average_colour(data, want=16):
    """(r, g, b) 0-255, or None for a picture this can't read."""
    if len(data) < 128 or data[:4] != b'DDS ':
        return None
    h, w = struct.unpack_from('<II', data, 12)
    mips = max(1, struct.unpack_from('<I', data, 28)[0])
    four = data[84:88]
    step = {b'DXT1': 8, b'DXT3': 16, b'DXT5': 16}.get(four)
    if not step:
        return None
    off = 128
    for _ in range(mips - 1):
        if w <= want and h <= want:
            break
        off += max(1, (w + 3) // 4) * max(1, (h + 3) // 4) * step
        w, h = max(1, w // 2), max(1, h // 2)
    n = max(1, (w + 3) // 4) * max(1, (h + 3) // 4)
    tot, k = [0, 0, 0], 0
    for i in range(n):
        o = off + i * step + (step - 8)
        if o + 8 > len(data):
            break
        for px in _block(data, o):
            tot[0] += px[0]; tot[1] += px[1]; tot[2] += px[2]
            k += 1
    return tuple(v // k for v in tot) if k else None
