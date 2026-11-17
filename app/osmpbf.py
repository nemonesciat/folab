"""OpenStreetMap's .osm.pbf, read with the standard library for one thing only: the coastline.

A region's whole file (Geofabrik's, say) is easy to download where a query to a busy server isn't, and its coastline is
the real one well past the area a city's map covers. lodbeyond.py shapes the sea past a world's edge by it.

The format: blocks one after another, each a 4-byte big-endian length, a header (protocol buffer: its type and the
block's size) and the block (zlib-packed). OSMData blocks hold a string table and groups of nodes (dense: ids,
latitudes and longitudes as running differences) and ways (tags as string-table numbers, node ids as running
differences). Two passes: first the coastline ways and the nodes they need, then those nodes' places.

`coast(path, bbox)` returns something like an osm.Data: `bounds` (min lat, min lon, max lat, max lon) and `coast`, each
way as its (lat, lon) points, the land on its left, as OSM draws it."""
import struct
import zlib


COAST_PAD = 0.05            # (degrees: coastline this far past a cut's box is kept, so no stretch of it ends inside the world)


class Coast:
    def __init__(self):
        self.bounds = None
        self.coast = []


def _varint(b, i):
    v = s = 0
    while True:
        c = b[i]
        i += 1
        v |= (c & 0x7f) << s
        if c < 0x80:
            return v, i
        s += 7


def _fields(b):
    """(field number, wire type, value) for each field of a message: value is an int or a bytes slice."""
    i, n = 0, len(b)
    while i < n:
        key, i = _varint(b, i)
        f, t = key >> 3, key & 7
        if t == 0:
            v, i = _varint(b, i)
        elif t == 2:
            ln, i = _varint(b, i)
            v = b[i:i + ln]
            i += ln
        elif t == 1:
            v = b[i:i + 8]
            i += 8
        elif t == 5:
            v = b[i:i + 4]
            i += 4
        else:
            raise ValueError('not an .osm.pbf file (wire type %d)' % t)
        yield f, t, v


def _packed(b):
    out, i, n = [], 0, len(b)
    while i < n:
        v, i = _varint(b, i)
        out.append(v)
    return out


def _zig(v):
    return (v >> 1) ^ -(v & 1)


def _deltas(b):
    out, run = [], 0
    for v in _packed(b):
        run += _zig(v)
        out.append(run)
    return out


def _blocks(path):
    """Each OSMData block's bytes, unpacked."""
    with open(path, 'rb') as f:
        while True:
            head = f.read(4)
            if len(head) < 4:
                return
            hdr = f.read(struct.unpack('>I', head)[0])
            kind, size = b'', 0
            for fn, _t, v in _fields(hdr):
                if fn == 1:
                    kind = bytes(v)
                elif fn == 3:
                    size = v
            blob = f.read(size)
            if kind != b'OSMData':
                continue
            raw = packed = None
            for fn, _t, v in _fields(blob):
                if fn == 1:
                    raw = bytes(v)
                elif fn == 3:
                    packed = v
            if raw is not None:
                yield raw
            elif packed is not None:
                yield zlib.decompress(packed)
            else:
                raise ValueError('a block of this .osm.pbf is packed in a way the standard library can\'t open (not zlib)')


def _block(data):
    strings, groups, gran, lat0, lon0 = [], [], 100, 0, 0
    for fn, _t, v in _fields(data):
        if fn == 1:
            strings = [bytes(s) for f2, _t2, s in _fields(v) if f2 == 1]
        elif fn == 2:
            groups.append(v)
        elif fn == 17:
            gran = v
        elif fn == 19:
            lat0 = v - (1 << 64) if v >= 1 << 63 else v       # (int64: a negative one is ten bytes of two's complement)
        elif fn == 20:
            lon0 = v - (1 << 64) if v >= 1 << 63 else v
    return strings, groups, gran, lat0, lon0


def _tags(keys, vals, strings):
    return [(strings[k].decode('utf-8', 'replace'), strings[v].decode('utf-8', 'replace')) for k, v in zip(keys, vals)]


def _esc(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')


def cut(path, bbox, out, progress=None):
    """Write the part of a region's .osm.pbf inside bbox (min lat, min lon, max lat, max lon) as .osm XML, as the
    OpenStreetMap site's export would: every node inside, every way with a node inside (whole, its nodes outside too),
    every relation with a member kept. osm.read reads the result like any map file. Returns counts."""
    s, w, n, e = bbox
    inside = set()
    near = set()                                        # (nodes just outside: coastline through them is kept too)
    nodes = {}                                        # {id: (lat, lon, tags)}
    ways = {}                                           # {id: (refs, tags)}
    rels = {}                                           # {id: ([(type, ref, role)], tags)}
    # pass 1: nodes inside, all ways and relations (Hawaii's are few enough to hold)
    for data in _blocks(path):
        strings, groups, gran, lat0, lon0 = _block(data)
        for grp in groups:
            for fn, _t, msg in _fields(grp):
                if fn == 2:
                    ids = lats = lons = kv = None
                    for f2, _t2, v in _fields(msg):
                        if f2 == 1:
                            ids = _deltas(v)
                        elif f2 == 8:
                            lats = _deltas(v)
                        elif f2 == 9:
                            lons = _deltas(v)
                        elif f2 == 10:
                            kv = _packed(v)
                    if not ids:
                        continue
                    at = 0
                    for k, nid in enumerate(ids):
                        tags = []
                        if kv:
                            while at < len(kv) and kv[at] != 0:
                                tags.append((strings[kv[at]].decode('utf-8', 'replace'), strings[kv[at + 1]].decode('utf-8', 'replace')))
                                at += 2
                            at += 1
                        la, lo = 1e-9 * (lat0 + gran * lats[k]), 1e-9 * (lon0 + gran * lons[k])
                        if s <= la <= n and w <= lo <= e:
                            inside.add(nid)
                            nodes[nid] = (la, lo, tags)
                        elif s - COAST_PAD <= la <= n + COAST_PAD and w - COAST_PAD <= lo <= e + COAST_PAD:
                            near.add(nid)
                elif fn == 3:
                    wid, keys, vals, refs = 0, [], [], []
                    for f2, _t2, v in _fields(msg):
                        if f2 == 1:
                            wid = v
                        elif f2 == 2:
                            keys = _packed(v)
                        elif f2 == 3:
                            vals = _packed(v)
                        elif f2 == 8:
                            refs = _deltas(v)
                    ways[wid] = (refs, _tags(keys, vals, strings))
                elif fn == 4:
                    rid, keys, vals, roles, mems, types = 0, [], [], [], [], []
                    for f2, _t2, v in _fields(msg):
                        if f2 == 1:
                            rid = v
                        elif f2 == 2:
                            keys = _packed(v)
                        elif f2 == 3:
                            vals = _packed(v)
                        elif f2 == 8:
                            roles = _packed(v)
                        elif f2 == 9:
                            mems = _deltas(v)
                        elif f2 == 10:
                            types = _packed(v)
                    members = [(('node', 'way', 'relation')[types[k]], mems[k], strings[roles[k]].decode('utf-8', 'replace'))
                               for k in range(len(mems))]
                    rels[rid] = (members, _tags(keys, vals, strings))
        if progress:
            progress('read', len(nodes))
    kept_ways = {wid: v for wid, v in ways.items() if any(r in inside for r in v[0]) or (
        ('natural', 'coastline') in v[1] and any(r in near for r in v[0]))}
    need = set(r for refs, _t in kept_ways.values() for r in refs) - set(nodes)
    kept_rels = {rid: v for rid, v in rels.items()
                 if any((t == 'way' and m in kept_ways) or (t == 'node' and m in inside) for t, m, _r in v[0])}
    # pass 2: the places of nodes outside the box that kept ways run through
    if need:
        for data in _blocks(path):
            _s, groups, gran, lat0, lon0 = _block(data)
            for grp in groups:
                for fn, _t, msg in _fields(grp):
                    if fn != 2:
                        continue
                    ids = lats = lons = None
                    for f2, _t2, v in _fields(msg):
                        if f2 == 1:
                            ids = _deltas(v)
                        elif f2 == 8:
                            lats = _deltas(v)
                        elif f2 == 9:
                            lons = _deltas(v)
                    for k, nid in enumerate(ids or ()):
                        if nid in need:
                            nodes[nid] = (1e-9 * (lat0 + gran * lats[k]), 1e-9 * (lon0 + gran * lons[k]), [])
    with open(out, 'w', encoding='utf-8') as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n<osm version="0.6" generator="FOLab osmpbf">\n')
        f.write(' <bounds minlat="%.7f" minlon="%.7f" maxlat="%.7f" maxlon="%.7f"/>\n' % (s, w, n, e))
        for nid in sorted(nodes):
            la, lo, tags = nodes[nid]
            if tags:
                f.write(' <node id="%d" lat="%.7f" lon="%.7f">\n' % (nid, la, lo))
                for k, v in tags:
                    f.write('  <tag k="%s" v="%s"/>\n' % (_esc(k), _esc(v)))
                f.write(' </node>\n')
            else:
                f.write(' <node id="%d" lat="%.7f" lon="%.7f"/>\n' % (nid, la, lo))
        for wid in sorted(kept_ways):
            refs, tags = kept_ways[wid]
            f.write(' <way id="%d">\n' % wid)
            for r in refs:
                if r in nodes:
                    f.write('  <nd ref="%d"/>\n' % r)
            for k, v in tags:
                f.write('  <tag k="%s" v="%s"/>\n' % (_esc(k), _esc(v)))
            f.write(' </way>\n')
        for rid in sorted(kept_rels):
            members, tags = kept_rels[rid]
            f.write(' <relation id="%d">\n' % rid)
            for t, m, role in members:
                f.write('  <member type="%s" ref="%d" role="%s"/>\n' % (t, m, _esc(role)))
            for k, v in tags:
                f.write('  <tag k="%s" v="%s"/>\n' % (_esc(k), _esc(v)))
            f.write(' </relation>\n')
        f.write('</osm>\n')
    return {'nodes': len(nodes), 'ways': len(kept_ways), 'relations': len(kept_rels)}


def coast(path, bbox=None):
    """The coastline ways with any point inside bbox (min lat, min lon, max lat, max lon), each whole; every one if
    bbox is None."""
    want_ways = []                                      # [(refs)]
    for data in _blocks(path):
        strings, groups, _g, _a, _o = _block(data)
        try:
            k_nat, v_coast = strings.index(b'natural'), strings.index(b'coastline')
        except ValueError:
            continue
        for grp in groups:
            for fn, _t, way in _fields(grp):
                if fn != 3:
                    continue
                keys = vals = refs = None
                for f2, _t2, v in _fields(way):
                    if f2 == 2:
                        keys = _packed(v)
                    elif f2 == 3:
                        vals = _packed(v)
                    elif f2 == 8:
                        refs = v
                if keys and vals and any(k == k_nat and vals[n] == v_coast for n, k in enumerate(keys)) and refs:
                    want_ways.append(_deltas(refs))
    need = set(r for w in want_ways for r in w)
    where = {}
    for data in _blocks(path):
        _s, groups, gran, lat0, lon0 = _block(data)
        for grp in groups:
            for fn, _t, dense in _fields(grp):
                if fn == 2:
                    ids = lats = lons = None
                    for f2, _t2, v in _fields(dense):
                        if f2 == 1:
                            ids = _deltas(v)
                        elif f2 == 8:
                            lats = _deltas(v)
                        elif f2 == 9:
                            lons = _deltas(v)
                    if not ids:
                        continue
                    for n, nid in enumerate(ids):
                        if nid in need:
                            where[nid] = (1e-9 * (lat0 + gran * lats[n]), 1e-9 * (lon0 + gran * lons[n]))
                elif fn == 1:                           # (a plain node: id 1, lat 8, lon 9, zigzag)
                    nid = la = lo = None
                    for f2, _t2, v in _fields(dense):
                        if f2 == 1:
                            nid = _zig(v)
                        elif f2 == 8:
                            la = _zig(v)
                        elif f2 == 9:
                            lo = _zig(v)
                    if nid in need:
                        where[nid] = (1e-9 * (lat0 + gran * la), 1e-9 * (lon0 + gran * lo))
    out = Coast()
    for refs in want_ways:
        line = [where[r] for r in refs if r in where]
        if len(line) < 2:
            continue
        if bbox and not any(bbox[0] <= la <= bbox[2] and bbox[1] <= lo <= bbox[3] for la, lo in line):
            continue
        out.coast.append(line)
    out.bounds = tuple(bbox) if bbox else None
    return out
