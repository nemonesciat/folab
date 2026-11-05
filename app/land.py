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
    fid = gd.to_global(i, ltex_id)
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
    out = {'h': None, 'c': None, 'q': [{'base': None, 'layers': []} for _ in range(4)]}
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
            layer = None
        elif tag == 'ATXT' and len(d) >= 5:
            tex, quarter = struct.unpack_from('<IB', d)
            layer = None
            if quarter < 4:
                layer = {'tex': texture_of(gd, i, tex, tex_cache), 'a': [0.0] * (QSIDE * QSIDE)}
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
