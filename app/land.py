"""The ground of one exterior cell, from its LAND record: heights, colours and painted textures.

A cell is 4096 units square with 33 x 33 points 128 units apart. Heights (VHGT) are kept as a starting value and then
one small step per point: each row starts one step from the row before's start, and each point is one step from the
point before it, all times 8. Colours (VCLR) are one RGB per point. The cell is painted in four quarters
(0 south-west, 1 south-east, 2 north-west, 3 north-east), 17 x 17 points each: a base texture (BTXT) and layers over it
(ATXT), each followed by how strongly it shows at some of the quarter's points (VTXT: point number, strength).
Textures name an LTEX, whose TNAM is a texture set (TXST) whose TX00 is the picture."""
import struct

import tes4

SIDE = 33
QSIDE = 17
STEP = 128.0
DEFAULT_TEXTURE = 'textures\\landscape\\dirt02.dds'


def texture_of(gd, i, ltex_id, cache):
    """An LTEX's picture (path under Data), for an LTEX form ID as plugin i wrote it."""
    if not ltex_id:
        return None
    return texture_of_fid(gd, gd.to_global(i, ltex_id), cache)


def texture_of_fid(gd, fid, cache):
    if fid in cache:
        return cache[fid]
    path = None
    try:
        f = gd.fields(fid)
        if 'TNAM' in f:
            j = gd.forms[fid][0]
            tx = gd.fields(gd.to_global(j, struct.unpack_from('<I', f['TNAM'])[0])).get('TX00')
            if tx:
                path = tes4.zstr(tx)
        if not path and 'ICON' in f:
            path = tes4.zstr(f['ICON'])
    except (KeyError, struct.error):
        path = None
    if path and not path.lower().startswith('textures\\'):
        path = 'textures\\' + path
    cache[fid] = path
    return path


def decode(gd, entry, tex_cache):
    """{'h': [33*33 heights, row by row from the south], 'c': hex colours or None, 'q': [4 quarters of
    {'base': texture, 'layers': [{'tex', 'a': [17*17 strengths]}]}]}"""
    i, rec = entry
    subs = list(tes4.iter_subrecords(gd.plugins[i].data(rec)))
    out = {'h': None, 'c': None, 'q': [{'base': None, 'bkey': None, 'layers': []} for _ in range(4)]}
    key = lambda v: gd.key(gd.to_global(i, v)) if v else None
    layer = None
    for tag, d in subs:
        if tag == 'VHGT' and len(d) >= 4 + SIDE * SIDE:
            start = struct.unpack_from('<f', d)[0]
            steps = struct.unpack_from('<%db' % (SIDE * SIDE), d, 4)
            h, row = [], start
            for r in range(SIDE):
                row += steps[r * SIDE]
                v = row
                h.append(v * 8)
                for c in range(1, SIDE):
                    v += steps[r * SIDE + c]
                    h.append(v * 8)
            out['h'] = h
        elif tag == 'VCLR' and len(d) >= SIDE * SIDE * 3:
            out['c'] = d[:SIDE * SIDE * 3].hex()
        elif tag == 'BTXT' and len(d) >= 5:
            tex, quarter = struct.unpack_from('<IB', d)
            if quarter < 4:
                out['q'][quarter]['base'] = texture_of(gd, i, tex, tex_cache)
                out['q'][quarter]['bkey'] = key(tex)
            layer = None
        elif tag == 'ATXT' and len(d) >= 5:
            tex, quarter = struct.unpack_from('<IB', d)
            layer = None
            if quarter < 4:
                layer = {'tex': texture_of(gd, i, tex, tex_cache), 'key': key(tex), 'a': [0.0] * (QSIDE * QSIDE)}
                out['q'][quarter]['layers'].append(layer)
        elif tag == 'VTXT' and layer is not None:
            for k in range(len(d) // 8):
                pos, _pad, strength = struct.unpack_from('<HHf', d, k * 8)
                if pos < QSIDE * QSIDE:
                    layer['a'][pos] = round(strength, 3)
    for q in out['q']:
        q['layers'] = [l for l in q['layers'] if l['tex'] and any(l['a'])]
        if not q['base']:
            q['base'] = DEFAULT_TEXTURE
    return out


# --- writing ---------------------------------------------------------------------------------------------------------

MAX_LAYERS = 6          # (painted layers a quarter can have; the game's own land never has more)


def encode_heights(h):
    """VHGT for 33 x 33 heights: a starting value, then whole steps (each between -128 and 127, times 8). Heights
    a step can't reach are brought as near as the steps allow."""
    v = [x / 8.0 for x in h]
    start = v[0]
    steps = []
    row_start = start
    for r in range(SIDE):
        d = max(-128, min(127, round(v[r * SIDE] - row_start)))
        row_start += d
        steps.append(d)
        cur = row_start
        for c in range(1, SIDE):
            d = max(-128, min(127, round(v[r * SIDE + c] - cur)))
            cur += d
            steps.append(d)
    return struct.pack('<f', start) + struct.pack('<%db' % len(steps), *steps) + bytes(3)


def heights_of(vhgt):
    """The heights a VHGT gives (to check what was written, or to see where a stroke really left the ground)."""
    start = struct.unpack_from('<f', vhgt)[0]
    steps = struct.unpack_from('<%db' % (SIDE * SIDE), vhgt, 4)
    out, row = [], start
    for r in range(SIDE):
        row += steps[r * SIDE]
        v = row
        out.append(v * 8)
        for c in range(1, SIDE):
            v += steps[r * SIDE + c]
            out.append(v * 8)
    return out


def encode_normals(h, beyond=None):
    """VNML: each point's slope as a direction, x y z as signed bytes, from the heights either side of it (as the
    game's own are). beyond(r, c) gives a height past the cell's edge (row or column -1 or 33, from the cell next
    door), or None; without it the edge looks only inward."""
    out = bytearray()
    inside = lambda r, c: h[min(SIDE - 1, max(0, r)) * SIDE + min(SIDE - 1, max(0, c))]

    def at(r, c):
        if 0 <= r < SIDE and 0 <= c < SIDE:
            return h[r * SIDE + c], True
        v = beyond(r, c) if beyond else None
        return (v, True) if v is not None else (inside(r, c), False)
    for r in range(SIDE):
        for c in range(SIDE):
            (xa, ka), (xb, kb) = at(r, c + 1), at(r, c - 1)
            (ya, la), (yb, lb) = at(r + 1, c), at(r - 1, c)
            dx = (xa - xb) / (STEP * (int(ka) + int(kb)))
            dy = (ya - yb) / (STEP * (int(la) + int(lb)))
            n = (-dx, -dy, 1.0)
            k = (n[0] ** 2 + n[1] ** 2 + n[2] ** 2) ** 0.5
            out += struct.pack('<3b', *[max(-127, min(127, round(x / k * 127))) for x in n])
    return bytes(out)


def encode(entry, original, link, beyond=None):
    """A LAND record's subrecords for land as a mod keeps it ({'h', 'c', 'q'}, as decode gives, textures by key),
    over the game's own (its DATA and anything else kept). link(key) -> form ID as written."""
    keep = [(t, d) for t, d in original if t not in ('VNML', 'VHGT', 'VCLR', 'BTXT', 'ATXT', 'VTXT')]
    data = [(t, d) for t, d in keep if t == 'DATA']
    rest = [(t, d) for t, d in keep if t != 'DATA']
    subs = data or [('DATA', struct.pack('<I', 0x1F))]
    subs += [('VNML', encode_normals(entry['h'], beyond)), ('VHGT', encode_heights(entry['h']))]
    if entry.get('c'):
        subs.append(('VCLR', bytes.fromhex(entry['c'])))
    for q, quarter in enumerate(entry['q']):
        if quarter.get('bkey'):
            subs.append(('BTXT', struct.pack('<IBBh', link(quarter['bkey']), q, 8, -1)))
        n = 0
        for l in quarter['layers']:
            pts = [(k, a) for k, a in enumerate(l['a']) if a > 0.0005]
            if not pts or not l.get('key') or n >= MAX_LAYERS:
                continue
            subs.append(('ATXT', struct.pack('<IBBH', link(l['key']), q, 9, n)))
            n += 1
            subs.append(('VTXT', b''.join(struct.pack('<HHf', k, 0, min(1.0, a)) for k, a in pts)))
    return subs + rest
