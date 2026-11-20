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


def _clear_rim_cols(px, w, h, x0, x1, n):
    """_clear_rim for one strip of a sheet: columns x0 to x1 (and their top and bottom rows) clear n deep at its edges."""
    out = bytearray(px)
    for y in range(h):
        edge_row = y < n or y >= h - n
        for x in range(x0, min(x1, w)):
            if edge_row or x < x0 + n or x >= x1 - n:
                out[(y * w + x) * 4 + 3] = 0
    return bytes(out)


def _keep_cover_cols(px, w, h, x0, x1, cut, share):
    """_keep_cover for one strip of a sheet (columns x0 to x1)."""
    idx = [(y * w + x) * 4 + 3 for y in range(h) for x in range(x0, min(x1, w))]
    al = [px[i] for i in idx]
    n = len(al) or 1
    lo, hi = 0.0, 8.0
    for _ in range(16):
        mid = (lo + hi) / 2
        if sum(1 for a in al if a * mid > cut) / n < share:
            lo = mid
        else:
            hi = mid
    s = (lo + hi) / 2
    out = bytearray(px)
    for i, a in zip(idx, al):
        out[i] = min(255, int(a * s + 0.5))
    return bytes(out)


def encode(w, h, rgba, cut=None, rim=False, strips=None):
    """A plain 32-bit DDS with its full chain of smaller copies, from RGBA bytes (rows from the top): what a picture
    from elsewhere becomes for the game. Bigger than a compressed one, and exactly the picture.

    cut: for a cut-out (drawn where alpha is at least cut, 0-255: leaves, a fence): each smaller copy's colour is the
    mean of what shows (weighted by alpha, so the clear parts' colour never darkens it), and its alpha is lifted or
    lowered until as much of it is at the cut or over as of the picture itself. Plain halving makes a bush blobbier and
    darker the further off it is (FOLab's leaves: a fifth darker and half as dense again at 1/32 size)."""
    chain = []
    cur, cw, ch = rgba, w, h
    share = None
    if cut is not None:
        share = sum(1 for a in rgba[3::4] if a > cut) / float(w * h)
    shares = None
    if strips:
        # (a sheet of several pictures side by side, each its own strip: strips [(x0, x1, plain, rim)], in the full
        # picture's columns; each keeps its own share over the cut, or, plain (a stem), is halved plainly)
        shares = [None if plain else sum(1 for y in range(h) for x in range(x0, x1) if rgba[(y * w + x) * 4 + 3] > cut) / float((x1 - x0) * h)
                  for x0, x1, plain, _r in strips]
    while True:
        if rim and cut is not None and cw > 2 and ch > 2 and not strips:
            cur = _clear_rim(cur, cw, ch, 2 if cur is rgba else 1)
        if strips and cw > 2 and ch > 2:
            f = cw / float(w)
            for x0, x1, _plain, r in strips:
                if r:
                    cur = _clear_rim_cols(cur, cw, ch, int(x0 * f), int(x1 * f), 2 if cur is rgba else 1)
        bgra = bytearray(cur)
        bgra[0::4], bgra[2::4] = cur[2::4], cur[0::4]
        chain.append(bytes(bgra))
        if cw == 1 and ch == 1:
            break
        if cut is None:
            cur, cw, ch = _half(cur, cw, ch)
        elif strips:
            cur, cw, ch = _half_cutout(cur, cw, ch)
            f = cw / float(w)
            for (x0, x1, plain, _r), sh in zip(strips, shares):
                a, b = int(x0 * f), max(int(x0 * f) + 1, int(x1 * f))
                if plain or b - a < 1:
                    # (the stem's strip: its alpha as the most of what each pixel covers, so it stays solid)
                    continue
                cur = _keep_cover_cols(cur, cw, ch, a, b, cut, sh)
        else:
            cur, cw, ch = _half_cutout(cur, cw, ch)
            cur = _keep_cover(cur, cut, share)
    # flags: caps, height, width, pitch, pixel format, mipmap count; RGB + alpha masks in the pixel format
    head = b'DDS ' + struct.pack('<7I', 124, 0x2100F, h, w, w * 4, 0, len(chain)) + b'\0' * 44
    head += struct.pack('<2I4s5I', 32, 0x41, b'\0\0\0\0', 32, 0xFF0000, 0xFF00, 0xFF, 0xFF000000)
    head += struct.pack('<5I', 0x401008, 0, 0, 0, 0)
    return head + b''.join(chain)


def _clear_rim(px, w, h, n):
    """A cut-out's outermost n rows and columns made clear. The game repeats a picture across its edges, so a card's top
    edge samples the picture's bottom row: FOLab's grass had 169 solid pixels along it and every card of every plant
    carried a dark bar along its top in nv-rs, 20 Nov 2026."""
    out = bytearray(px)
    for y in range(h):
        edge_row = y < n or y >= h - n
        for x in range(w):
            if edge_row or x < n or x >= w - n:
                out[(y * w + x) * 4 + 3] = 0
    return bytes(out)


def _half_cutout(px, w, h):
    """_half for a cut-out: alpha the plain mean, colour the alpha-weighted mean (the plain mean where all is clear)."""
    nw, nh = max(1, w // 2), max(1, h // 2)
    fx, fy = w // nw, h // nh
    out = bytearray(nw * nh * 4)
    for y in range(nh):
        for x in range(nw):
            t = [0, 0, 0, 0]
            plain = [0, 0, 0]
            for dy in range(fy):
                row = (y * fy + dy) * w
                for dx in range(fx):
                    o = (row + x * fx + dx) * 4
                    a = px[o + 3]
                    for c in range(3):
                        t[c] += px[o + c] * a
                        plain[c] += px[o + c]
                    t[3] += a
            n = fx * fy
            q = (y * nw + x) * 4
            for c in range(3):
                out[q + c] = (t[c] + t[3] // 2) // t[3] if t[3] else plain[c] // n
            out[q + 3] = t[3] // n
    return bytes(out), nw, nh


def _keep_cover(px, cut, share):
    """A copy's alpha scaled so that `share` of it is over `cut` (Castano's coverage: a bisection on the scale). Over, not at:
    the game draws only alpha greater than its threshold (NiAlphaProperty test GREATER, nv-rs's too), and a picture of only
    clear and solid (a stem) was scaled to exactly the cut in every smaller copy, so none of it drew past a couple of
    metres (20 Nov 2026)."""
    al = px[3::4]
    n = len(al)
    lo, hi = 0.0, 8.0
    for _ in range(16):
        mid = (lo + hi) / 2
        got = sum(1 for a in al if a * mid > cut) / n
        if got < share:
            lo = mid
        else:
            hi = mid
    s = (lo + hi) / 2
    out = bytearray(px)
    out[3::4] = bytes(min(255, int(a * s + 0.5)) for a in al)
    return bytes(out)


def _half(px, w, h):
    """A picture at half the size, each pixel the mean of those it covers."""
    nw, nh = max(1, w // 2), max(1, h // 2)
    fx, fy = w // nw, h // nh
    out = bytearray(nw * nh * 4)
    if fx == 2 and fy == 2 and w == 2 * nw and h == 2 * nh:
        # the usual case, a colour at a time over whole rows (a drawn 512 texture took seconds the slow way)
        for y in range(nh):
            a, b = px[2 * y * w * 4:(2 * y + 1) * w * 4], px[(2 * y + 1) * w * 4:(2 * y + 2) * w * 4]
            for c in range(4):
                out[y * nw * 4 + c:(y + 1) * nw * 4:4] = bytes((p + q + r + s) >> 2 for p, q, r, s in zip(a[c::8], a[c + 4::8], b[c::8], b[c + 4::8]))
        return bytes(out), nw, nh
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


# --- compressed, as the game keeps its own ---
# FOLab wrote its own pictures plain (32 bits a pixel), 4 to 8 times what the game's compressed ones take: a city of
# them (348 MB on Waikiki) ran the 32-bit game out of texture memory, so its own buildings and ships lost their pictures
# far off and then near too. A picture with no transparency becomes DXT1 (8 bytes a 4 x 4 block), one with any (a
# normal map keeps its shine there, glass and leaves their cut-outs) DXT5 (16 bytes).

def _colour_block(px, four):
    """Sixteen (r, g, b, a) as DXT colour: the corners of their colour box as the two ends, each pixel the nearest step
    along the line between them. four: always the four-colour order (c0 > c1), which DXT1 needs and DXT5 ignores."""
    r0 = max(p[0] for p in px); g0 = max(p[1] for p in px); b0 = max(p[2] for p in px)
    r1 = min(p[0] for p in px); g1 = min(p[1] for p in px); b1 = min(p[2] for p in px)
    c0 = (r0 >> 3) << 11 | (g0 >> 2) << 5 | b0 >> 3
    c1 = (r1 >> 3) << 11 | (g1 >> 2) << 5 | b1 >> 3
    if c0 == c1:
        return struct.pack('<HHI', c0, c1, 0)
    if c0 < c1:
        c0, c1 = c1, c0
        r0, g0, b0, r1, g1, b1 = r1, g1, b1, r0, g0, b0
    dr, dg, db = r0 - r1, g0 - g1, b0 - b1
    n = dr * dr + dg * dg + db * db
    bits = 0
    order = (1, 3, 2, 0)                        # (step 0 is the far end c1, step 3 the near end c0)
    for k, p in enumerate(px):
        t = ((p[0] - r1) * dr + (p[1] - g1) * dg + (p[2] - b1) * db) * 3 / n if n else 0
        s = 0 if t < 0.5 else 1 if t < 1.5 else 2 if t < 2.5 else 3
        bits |= order[s] << (2 * k)
    return struct.pack('<HHI', c0, c1, bits)


def _alpha_block(px):
    """Sixteen alphas as DXT5's 8 bytes: the highest and lowest, and 3 bits a pixel among the eight steps between."""
    a0 = max(p[3] for p in px)
    a1 = min(p[3] for p in px)
    if a0 == a1:
        return struct.pack('<BB', a0, a1) + b'\0' * 6
    bits = 0
    for k, p in enumerate(px):
        step = int(round((p[3] - a1) * 7.0 / (a0 - a1)))   # 0 at a1 .. 7 at a0
        idx = 0 if step == 7 else 1 if step == 0 else 8 - step
        bits |= idx << (3 * k)
    return struct.pack('<BB', a0, a1) + bits.to_bytes(6, 'little')


def _levels_plain(data):
    """A plain 32-bit DDS's pictures, largest first: [(w, h, rgba bytes)]."""
    h, w = struct.unpack_from('<2I', data, 12)
    mips = max(1, struct.unpack_from('<I', data, 28)[0])
    bits = struct.unpack_from('<I', data, 88)[0]
    masks = struct.unpack_from('<4I', data, 92)
    if bits != 32:
        return None
    sh = [_shift(m) for m in masks]
    out, off = [], 128
    for m in range(mips):
        mw, mh = max(1, w >> m), max(1, h >> m)
        n = mw * mh * 4
        raw = data[off:off + n]
        off += n
        if len(raw) < n:
            break
        if masks == (0xFF0000, 0xFF00, 0xFF, 0xFF000000):
            rgba = bytearray(raw)
            rgba[0::4], rgba[2::4] = raw[2::4], raw[0::4]
        else:
            vals = struct.unpack('<%dI' % (mw * mh), raw)
            rgba = bytearray()
            for v in vals:
                rgba += bytes(((v & masks[i]) >> sh[i][0] if masks[i] else 255) & 255 for i in range(4))
        out.append((mw, mh, bytes(rgba)))
    return out


def compress(data):
    """A plain 32-bit DDS (as encode() writes) made DXT1, or DXT5 if any pixel isn't fully opaque, every mipmap kept as it
    was. Anything else comes back as it was."""
    if data[:4] != b'DDS ' or struct.unpack_from('<I', data, 80)[0] & 4:
        return data
    levels = _levels_plain(data)
    if not levels:
        return data
    alpha = any(a != 255 for a in levels[0][2][3::4])
    out = []
    for w, h, px in levels:
        for by in range(0, max(4, h), 4):
            for bx in range(0, max(4, w), 4):
                blk = []
                for y in range(4):
                    yy = min(by + y, h - 1)
                    for x in range(4):
                        o = (yy * w + min(bx + x, w - 1)) * 4
                        blk.append(px[o:o + 4])
                if alpha:
                    out.append(_alpha_block(blk))
                out.append(_colour_block(blk, True))
    h0, w0 = levels[0][1], levels[0][0]
    size = max(1, w0 // 4) * max(1, h0 // 4) * (16 if alpha else 8)
    head = b'DDS ' + struct.pack('<7I', 124, 0xA1007, h0, w0, size, 0, len(levels)) + b'\0' * 44
    head += struct.pack('<2I4s5I', 32, 4, b'DXT5' if alpha else b'DXT1', 0, 0, 0, 0, 0)
    head += struct.pack('<5I', 0x401008, 0, 0, 0, 0)
    return head + b''.join(out)
