"""Two of the game's worn outfits made one: the top of one, the bottom of another (the user, 21 Nov 2026: "hawaiian
shirt+shorts (like khaki or jean)"; no game outfit is a collared shirt over shorts).

A worn outfit (NIF 20.2.0.7) is the skeleton's bones as NiNodes under the root, and shapes skinned to them: each an
NiTriShape with its properties, its NiTriShapeData (where the corners are in the bind pose, and the triangles), a
BSDismemberSkinInstance naming its bones, NiSkinData (each bone's weights) and NiSkinPartition (what the game draws: the
triangles again, in pieces of a few bones each, by the piece's own corner numbers). Every outfit of the game names the
same bones, so a shape from one can hang on another's bones by name.

    join(top, bottom, cut, take, top_keep=None, bottom_keep=None)   bytes

`top` is kept whole but for its triangles under `cut` (their middle's height in the bind pose) in the shapes `top_keep`
names (None: every shape). The shapes of `bottom` named in `take` are added, each without its triangles at or over
`cut` (or `bottom_cut`, a little higher, so the two overlap and no gap shows) unless `bottom_keep` leaves it whole. A triangle left out becomes three of one corner (it draws nothing) in the
shape's data (no corner or weight changes) and is left out of its partitions, which are written again as plain
triangle lists (the Powder Gang's are strips). Blocks added keep their bytes but for their
links (to blocks: the new numbers; to bones: the top's node of that name) and their names (the string table merged).

    py -3 app/outfitjoin.py     the Hawaiian shirt over the Powder Gang's shorts, barefoot (garmentprint.shirt_and_shorts),
                                what each shape draws"""
import struct

import nif

GEOM = ('NiTriShape',)
SKIN = ('BSDismemberSkinInstance', 'NiSkinInstance')


class JoinError(ValueError):
    pass


def _i(d, p):
    return struct.unpack_from('<i', d, p)[0]


def _u(d, p):
    return struct.unpack_from('<I', d, p)[0]


def _net(d, p, strs, refs):
    """An NiObjectNET at p: its name is a string, its extra data and controller links. Returns past it."""
    strs.append(p)
    p += 4
    n = _u(d, p)
    refs += [p + 4 + 4 * k for k in range(n)]
    p += 4 + 4 * n
    refs.append(p)
    return p + 4


def _av(d, p, strs, refs):
    p = _net(d, p, strs, refs)
    p += 4 + 12 + 36 + 4                    # flags (u32 past bsver 26), translation, rotation, scale
    n = _u(d, p)
    refs += [p + 4 + 4 * k for k in range(n)]
    p += 4 + 4 * n
    refs.append(p)                          # collision
    return p + 4


def _data_spots(d, o):
    """(where the triangle count is, where the triangles start, where 'additional data' is) of an NiTriShapeData."""
    p = o + 4
    n = struct.unpack_from('<H', d, p)[0]
    p += 2 + 2
    has = d[p]; p += 1
    if has:
        p += 12 * n
    vflags = struct.unpack_from('<H', d, p)[0]; p += 2
    hasn = d[p]; p += 1
    if hasn:
        p += 12 * n
        if vflags & 0x1000:
            p += 24 * n
    p += 16
    hasc = d[p]; p += 1
    if hasc:
        p += 16 * n
    p += 8 * n * (vflags & 1)
    p += 2                                  # consistency
    extra = p
    p += 4
    count = p
    p += 2 + 4
    if not d[p]:
        raise JoinError('a shape keeps no triangles')
    return count, p + 1, extra, n


def links(n, i):
    """(string index spots, link spots) of block i: positions in the file."""
    d, o, t = n.data, n.offsets[i], n.types[i]
    strs, refs = [], []
    if t in GEOM:
        p = _av(d, o, strs, refs)
        refs += [p, p + 4]                  # data, skin instance
        nm = _u(d, p + 8)
        strs += [p + 12 + 4 * k for k in range(nm)]
    elif t in ('NiMaterialProperty', 'NiAlphaProperty', 'NiFloatExtraData', 'NiStringExtraData'):
        p = _net(d, o, strs, refs) if t in ('NiMaterialProperty', 'NiAlphaProperty') else None
        if t in ('NiFloatExtraData', 'NiStringExtraData'):
            strs.append(o)
            if t == 'NiStringExtraData':
                strs.append(o + 4)
    elif t == 'BSShaderPPLightingProperty':
        p = _net(d, o, strs, refs)
        refs.append(p + 2 + 4 + 4 + 4 + 4 + 4)  # flags, type, flags, flags 2, environment scale, clamp: the texture set
    elif t == 'NiTriShapeData':
        refs.append(_data_spots(d, o)[2])
    elif t in SKIN:
        refs += [o, o + 4, o + 8]           # skin data, partition, skeleton root
        nb = _u(d, o + 12)
        refs += [o + 16 + 4 * k for k in range(nb)]
    elif t in ('BSShaderTextureSet', 'NiSkinData', 'NiSkinPartition'):
        pass
    else:
        raise JoinError('a block of a kind this does not join: %s' % t)
    return strs, refs


def _pieces(d, o):
    """The pieces of an NiSkinPartition at o: [dict] with their bytes split round the triangles: 'head' (counts, bones,
    corner map, weights), 'tris' [(a, b, c)] (a strip read out as the triangles it draws, as nif.py reads strips),
    'tail' (bone indices), 'vmap'."""
    out = []
    p = o
    count = _u(d, p); p += 4
    for _ in range(count):
        start = p
        nv, nt, nb, ns, nw = struct.unpack_from('<5H', d, p); p += 10
        p += 2 * nb
        vmap = None
        if d[p]:
            vmap = struct.unpack_from('<%dH' % nv, d, p + 1)
            p += 1 + 2 * nv
        else:
            p += 1
        p += 1 + (4 * nv * nw if d[p] else 0)
        head = d[start:p]
        lengths = struct.unpack_from('<%dH' % ns, d, p); p += 2 * ns
        has = d[p]; p += 1
        tris = []
        if has and ns:
            for ln in lengths:
                st = struct.unpack_from('<%dH' % ln, d, p); p += 2 * ln
                for k in range(ln - 2):
                    x, y, z = st[k], st[k + 1], st[k + 2]
                    if x == y or y == z or x == z:
                        continue
                    tris.append((x, y, z) if k % 2 == 0 else (x, z, y))
        elif has:
            tris = [struct.unpack_from('<3H', d, p + 6 * k) for k in range(nt)]
            p += 6 * nt
        tstart = p
        p += 1 + (nv * nw if d[p] else 0)
        out.append({'head': head, 'tris': tris, 'tail': d[tstart:p], 'vmap': vmap, 'nv': nv, 'nb': nb, 'nw': nw})
    return out, p - o


def _pieces_bytes(pieces):
    out = [struct.pack('<I', len(pieces))]
    for pc in pieces:
        h = bytearray(pc['head'])
        struct.pack_into('<HH', h, 2, len(pc['tris']), struct.unpack_from('<H', h, 4)[0])   # triangles, bones
        struct.pack_into('<H', h, 6, 0)                                                     # no strips
        out.append(bytes(h) + b'' + b''.join(struct.pack('<3H', *t) for t in pc['tris']) + pc['tail'])
    return b''.join(out)


def _hide(buf, n, shape, keep, parts):
    """Turns each triangle of the shape whose middle (bind pose) keep(z) refuses into three of one corner in its data, and
    leaves it out of its partition (rewritten as plain triangles into parts[block]). Returns how many went."""
    b = n.block(shape)
    V0 = n.block(b['data'])['verts']
    R, t0, sc = b['R'], b['t'], b['s']          # (the shape's own place under the root: its corners are kept round it)
    V = [0.0] * len(V0)
    for c in range(0, len(V0), 3):
        x, y, z = V0[c], V0[c + 1], V0[c + 2]
        V[c + 2] = t0[2] + sc * (R[2][0] * x + R[2][1] * y + R[2][2] * z)
    d = n.data
    count_at, tri_at, _x, _nv = _data_spots(d, n.offsets[b['data']])
    nt = struct.unpack_from('<H', d, count_at)[0]
    gone = set()
    for k in range(nt):
        t = struct.unpack_from('<3H', d, tri_at + 6 * k)
        if not keep(sum(V[3 * c + 2] for c in t) / 3.0):
            gone.add(tuple(sorted(t)))
            struct.pack_into('<3H', buf, tri_at + 6 * k, t[0], t[0], t[0])
    skin = b['skin']
    if skin >= 0:
        part = _i(d, n.offsets[skin] + 4)
        pieces, size = _pieces(d, n.offsets[part])
        if size != n.sizes[part]:
            raise JoinError('a partition read %d bytes of %d' % (size, n.sizes[part]))
        for pc in pieces:
            vm = pc['vmap']
            pc['tris'] = [t for t in pc['tris'] if tuple(sorted(vm[c] for c in t) if vm else sorted(t)) not in gone]
        parts[part] = _pieces_bytes(pieces)
    return len(gone)


def _reach(n, start):
    """Every block a shape needs, in file order, but bones (NiNodes)."""
    seen, todo = set(), [start]
    while todo:
        i = todo.pop()
        if i in seen or i < 0 or n.types[i] == 'NiNode':
            continue
        seen.add(i)
        _s, refs = links(n, i)
        todo += [_i(n.data, p) for p in refs]
    return sorted(seen)


def _names(n):
    return {n.block(i)['name']: i for i, t in enumerate(n.types) if t == 'NiNode'}


def join(top, bottom, cut, take, top_keep=None, bottom_keep=(), bottom_cut=None):
    a, b = nif.Nif(top), nif.Nif(bottom)
    if a.version != b.version or a.bsver != b.bsver or a.user != b.user:
        raise JoinError('the two outfits are not of one format')
    A = bytearray(top)
    pa, pb = {}, {}
    for i, t in enumerate(a.types):
        if t in GEOM and (top_keep is None or a.block(i)['name'] in top_keep):
            _hide(A, a, i, lambda z: z >= cut, pa)
    B = bytearray(bottom)
    shapes = {b.block(i)['name']: i for i, t in enumerate(b.types) if t in GEOM}
    missing = [s for s in take if s not in shapes]
    if missing:
        raise JoinError('the bottom outfit has no %s' % ', '.join(missing))
    for name in take:
        if name not in bottom_keep:
            _hide(B, b, shapes[name], lambda z: z < (cut if bottom_cut is None else bottom_cut), pb)
    blocks = [pa.get(i) or bytes(A[a.offsets[i]:a.offsets[i] + a.sizes[i]]) for i in range(len(a.types))]
    types = list(a.types)
    strings = list(a.strings)
    bones = _names(a)
    adding = sorted(set(k for name in take for k in _reach(b, shapes[name])))
    new = {old: len(blocks) + k for k, old in enumerate(adding)}
    b_root = 0
    for old in adding:
        o = b.offsets[old]
        blk = bytearray(B[o:o + b.sizes[old]])
        strs, refs = links(b, old)
        for p in strs:
            s = _i(B, p)
            if s >= 0:
                text = b.string(s)
                if text not in strings:
                    strings.append(text)
                struct.pack_into('<i', blk, p - o, strings.index(text))
        for p in refs:
            r = _i(B, p)
            if r < 0:
                continue
            if r in new:
                v = new[r]
            elif b.types[r] == 'NiNode':
                nm = b.block(r)['name']
                if r == b_root:
                    v = 0
                elif nm in bones:
                    v = bones[nm]
                else:
                    raise JoinError('the top outfit has no bone %s' % nm)
            else:
                raise JoinError('block %d links to %d (%s), not joined' % (old, r, b.types[r]))
            struct.pack_into('<i', blk, p - o, v)
        blocks.append(pb.get(old) or bytes(blk))
        types.append(b.types[old])
    root = blocks[0]
    strs, refs = links_node(a)
    kids_at, kids = refs
    blocks[0] = root[:kids_at] + struct.pack('<I', len(kids) + len(take)) + b''.join(struct.pack('<i', k) for k in kids) + \
        b''.join(struct.pack('<i', new[shapes[name]]) for name in take) + root[kids_at + 4 + 4 * len(kids):]
    return _write(a, types, blocks, strings)


def links_node(n):
    """(None, (position in the root block of its child count, [children])) of the root NiNode."""
    d = n.data
    o = n.offsets[0]
    p = _av(d, o, [], [])
    k = _u(d, p)
    return None, (p - o, list(struct.unpack_from('<%di' % k, d, p + 4)))


def _sized(s):
    b = s.encode('cp1252') if isinstance(s, str) else s
    return struct.pack('<I', len(b)) + b


def _write(a, types, blocks, strings):
    d = a.data
    r = nif.Reader(d, d.find(b'\n') + 1)
    r.u32(); r.u8(); r.u32(); r.u32(); r.u32()
    start = r.p
    r.short(); r.short(); r.short()
    export = d[start:r.p]
    order = []
    for t in types:
        if t not in order:
            order.append(t)
    head = d[:d.find(b'\n') + 1] + struct.pack('<IBIII', a.version, 1, a.user, len(blocks), a.bsver) + export
    head += struct.pack('<H', len(order)) + b''.join(_sized(t) for t in order)
    head += struct.pack('<%dH' % len(blocks), *(order.index(t) for t in types))
    head += struct.pack('<%dI' % len(blocks), *(len(x) for x in blocks))
    head += struct.pack('<II', len(strings), max(len(s) for s in strings)) + b''.join(_sized(s) for s in strings)
    head += struct.pack('<I', 0)
    # (the footer: the roots, as the top had them)
    tail = d[a.offsets[-1] + a.sizes[-1]:]
    return head + b''.join(blocks) + tail


def drawn(data):
    """[(shape name, triangles that draw)] from the partitions: what the game will show."""
    n = nif.Nif(data)
    out = []
    for i, t in enumerate(n.types):
        if t not in GEOM:
            continue
        b = n.block(i)
        k = 0
        if b['skin'] >= 0:
            part = _i(n.data, n.offsets[b['skin']] + 4)
            pieces, size = _pieces(n.data, n.offsets[part])
            if size != n.sizes[part]:
                raise JoinError('%s: its partition read %d bytes of %d' % (b['name'], size, n.sizes[part]))
            k = sum(len(pc['tris']) for pc in pieces)
        out.append((b['name'], k))
    return out


if __name__ == '__main__':
    import gamedata
    import garmentprint as gp
    gd = gamedata.GameData()
    top = gd.read_file(gp.FOLDER + gp.GARMENTS['m'][0])
    out = gp.shirt_and_shorts(gd)
    print(len(top), '->', len(out))
    print(drawn(top))
    print(drawn(out))
    print(len(nif.mesh_from_nif(out, placed=False)), 'shapes read back')
