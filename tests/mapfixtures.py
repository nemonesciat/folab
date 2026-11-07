"""Small map files for the tests to read, written here from the file formats' own rules (not named test_, so run.py leaves it)."""
import struct
import zlib


def lzw_encode(data):
    """TIFF's LZW, high bit first, the code size growing one code early, a clear code to start."""
    out = bytearray()
    acc = nacc = 0

    def put(code, width):
        nonlocal acc, nacc
        acc = (acc << width) | code
        nacc += width
        while nacc >= 8:
            nacc -= 8
            out.append((acc >> nacc) & 255)
            acc &= (1 << nacc) - 1
    table = {bytes((i,)): i for i in range(256)}
    nxt, width = 258, 9
    put(256, width)
    w = b''
    for b in data:
        wb = w + bytes((b,))
        if wb in table:
            w = wb
            continue
        put(table[w], width)
        table[wb] = nxt
        nxt += 1
        if nxt == 4094:
            put(256, width)
            table = {bytes((i,)): i for i in range(256)}
            nxt, width = 258, 9
        elif nxt >= 2048:
            width = 12
        elif nxt >= 1024:
            width = 11
        elif nxt >= 512:
            width = 10
        w = bytes((b,))
    if w:
        put(table[w], width)
        nxt += 1
        if nxt >= 2048:
            width = 12
        elif nxt >= 1024:
            width = 11
        elif nxt >= 512:
            width = 10
    put(257, width)
    if nacc:
        out.append((acc << (8 - nacc)) & 255)
    return bytes(out)


def tiff(w, h, values, kind='h', comp=1, order='<', tiled=None, rows=None, pred=1, scale=None, tie=None, matrix=None, geokeys=None, nodata=None, spp=1):
    """A TIFF of values (row by row from the top), as signed 16-bit ('h'), unsigned ('H') or 32-bit float ('f'). tiled: (tw, th);
    rows: rows to a strip; comp 1, 5 (LZW) or 8 (Deflate); pred 1, 2 or 3. spp: samples a pixel (the first is values, the rest 7)."""
    fmt_code = {'h': 2, 'H': 1, 'f': 3}[kind]
    bits = {'h': 16, 'H': 16, 'f': 32}[kind]
    width = bits // 8

    def chunk(rect_values, cw, ch):
        vals = []
        for v in rect_values:
            vals.append(v)
            vals += [7] * (spp - 1)
        per = cw * spp
        if pred == 2:
            mask = (1 << bits) - 1
            diff = []
            for r in range(ch):
                row = vals[r * per:(r + 1) * per]
                for k in range(per):
                    d = (row[k] - (row[k - spp] if k >= spp else 0)) & mask
                    diff.append(d)
            raw = struct.pack(order + '%d%s' % (len(diff), 'H'), *diff)
        elif pred == 3:
            big = struct.pack('>%d%s' % (len(vals), kind), *vals)
            raw = bytearray()
            for r in range(ch):
                row = big[r * per * width:(r + 1) * per * width]
                planes = bytearray()
                for b in range(width):
                    planes += row[b::width]
                d = bytearray(planes)
                for k in range(len(d) - 1, spp - 1, -1):
                    d[k] = (d[k] - d[k - spp]) & 255
                raw += d
            raw = bytes(raw)
        else:
            raw = struct.pack(order + '%d%s' % (len(vals), kind), *vals)
        if comp == 5:
            return lzw_encode(raw)
        if comp == 8:
            return zlib.compress(raw)
        return raw

    chunks = []
    if tiled:
        tw, th = tiled
        for ty in range(0, h, th):
            for tx in range(0, w, tw):
                part = []
                for r in range(ty, ty + th):
                    for c in range(tx, tx + tw):
                        part.append(values[r * w + c] if r < h and c < w else 0)
                chunks.append(chunk(part, tw, th))
    else:
        per = rows or h
        for r0 in range(0, h, per):
            n = min(per, h - r0)
            chunks.append(chunk(values[r0 * w:(r0 + n) * w], w, n))
    body = b''.join(chunks)
    offs, at = [], 8
    for c in chunks:
        offs.append(at)
        at += len(c)
    entries = []

    def add(tag, typ, vals):
        entries.append((tag, typ, vals))
    add(256, 4, [w])
    add(257, 4, [h])
    add(258, 3, [bits] * spp)
    add(259, 3, [comp])
    add(262, 3, [1])
    add(277, 3, [spp])
    add(284, 3, [1])
    if pred != 1:
        add(317, 3, [pred])
    add(339, 3, [fmt_code] * spp)
    if tiled:
        add(322, 4, [tiled[0]])
        add(323, 4, [tiled[1]])
        add(324, 4, offs)
        add(325, 4, [len(c) for c in chunks])
    else:
        add(273, 4, offs)
        add(278, 4, [rows or h])
        add(279, 4, [len(c) for c in chunks])
    if scale:
        add(33550, 12, list(scale))
    if tie:
        add(33922, 12, list(tie))
    if matrix:
        add(34264, 12, list(matrix))
    if geokeys:
        flat = [1, 1, 0, len(geokeys)]
        for k, v in sorted(geokeys.items()):
            flat += [k, 0, 1, v]
        add(34735, 3, flat)
    if nodata is not None:
        add(42113, 2, str(nodata))
    entries.sort(key=lambda e: e[0])
    sz = {3: 2, 4: 4, 12: 8, 2: 1}
    ifd_at = at + (at & 1)
    extra_at = ifd_at + 2 + 12 * len(entries) + 4
    ifd, extra = bytearray(struct.pack(order + 'H', len(entries))), bytearray()
    for tag, typ, vals in entries:
        if typ == 2:
            raw = vals.encode() + b'\0'
            n = len(raw)
        else:
            raw = struct.pack(order + '%d%s' % (len(vals), {3: 'H', 4: 'I', 12: 'd'}[typ]), *vals)
            n = len(vals)
        ifd += struct.pack(order + 'HHI', tag, typ, n)
        _ = sz
        if len(raw) <= 4:
            ifd += raw + bytes(4 - len(raw))
        else:
            ifd += struct.pack(order + 'I', extra_at + len(extra))
            extra += raw + (b'\0' if len(raw) & 1 else b'')
    ifd += bytes(4)
    head = (b'II' if order == '<' else b'MM') + struct.pack(order + 'HI', 42, ifd_at)
    return head + body + (b'\0' if at & 1 else b'') + bytes(ifd) + bytes(extra)


def hgt(n, fn):
    """An SRTM square: fn(row from the north, col from the west) -> metres (None: no data)."""
    vals = []
    for r in range(n):
        for c in range(n):
            v = fn(r, c)
            vals.append(-32768 if v is None else int(v))
    return struct.pack('>%dh' % len(vals), *vals)


def osm(nodes, ways, relations=(), bounds=None):
    """OSM XML. nodes: {id: (lat, lon)} or (lat, lon, tags); ways: [(id, [node ids], tags)]; relations: [(id, [(type, ref, role)], tags)]."""
    x = ['<?xml version="1.0" encoding="UTF-8"?>', '<osm version="0.6" generator="folab tests">']
    if bounds:
        x.append('<bounds minlat="%s" minlon="%s" maxlat="%s" maxlon="%s"/>' % tuple(bounds))
    for i, n in nodes.items():
        tags = n[2] if len(n) > 2 else {}
        inner = ''.join('<tag k="%s" v="%s"/>' % kv for kv in tags.items())
        x.append('<node id="%d" lat="%.7f" lon="%.7f">%s</node>' % (i, n[0], n[1], inner))
    for i, refs, tags in ways:
        x.append('<way id="%d">%s%s</way>' % (i, ''.join('<nd ref="%d"/>' % r for r in refs), ''.join('<tag k="%s" v="%s"/>' % kv for kv in tags.items())))
    for i, members, tags in relations:
        x.append('<relation id="%d">%s%s</relation>' % (i, ''.join('<member type="%s" ref="%d" role="%s"/>' % m for m in members),
                                                         ''.join('<tag k="%s" v="%s"/>' % kv for kv in tags.items())))
    x.append('</osm>')
    return '\n'.join(x).encode()
