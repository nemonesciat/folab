"""Distant land: what the game shows of a world beyond the cells it has loaded. Worked out from the game's own files, and
checked by rebuilding them (tests/test_lodgen.py): this writes the terrain part. Objects and trees are not done here.

What New Vegas reads for a world, by the world's editor ID:
  lodsettings\\<id>.dlodsettings   24 bytes: lowest level (4), highest, four times the highest, south-west cell (x, y as shorts),
                                  north-east cell, and 4 again. Chunks are counted from the south-west cell.
  meshes\\landscape\\lod\\<id>\\<id>.level<L>.x<X>.y<Y>.nif     the ground of L x L cells, L = 4, 8, 16...: see terrain_nif
  textures\\landscape\\lod\\<id>\\diffuse\\<id>.n.level<L>.x<X>.y<Y>.dds  its colours, DXT1, 256 x 256 with all its mipmaps
  textures\\landscape\\lod\\<id>\\normals\\<id>.n.level<L>.x<X>.y<Y>.dds  its slopes, the same
  meshes\\landscape\\lod\\<id>\\blocks\\... and textures\\...\\blocks\\<id>.buildings.dds  distant buildings (NOT made here)
  Distant trees are made from billboards listed elsewhere (NOT made here).

A world with no settings file shows no distant land at all; a game world's own files are overridden by loose files of the
same name, so a mod that reshapes land can replace just the chunks it touches."""
import json
import math
import os
import shutil
import struct

import land
import maptiles
import project
import roadgen

SKIRT_Z = -14098.0      # how far down the game's chunks hang their edges, so no gap shows between levels
TEXTURE = 256
HEADER_LINE = b'Gamebryo File Format, Version 20.2.0.7\n'
NIF_TYPES = ['BSMultiBoundNode', 'NiTriShape', 'BSShaderPPLightingProperty', 'BSShaderTextureSet', 'NiTriShapeData',
             'NiAdditionalGeometryData', 'BSMultiBound', 'BSMultiBoundAABB']
# The fixed parts of a chunk's blocks, as every chunk in the game has them
_NODE_TAIL = struct.pack('<9f', 1, 0, 0, 0, 1, 0, 0, 0, 1) + struct.pack('<f', 1.0) + struct.pack('<I', 0) + b'\xff\xff\xff\xff' + struct.pack('<II', 1, 1) + struct.pack('<I', 0) + struct.pack('<I', 6)
_NODE_HEAD = b'\xff\xff\xff\xff' + struct.pack('<I', 0) + b'\xff\xff\xff\xff' + struct.pack('<H', 0x080E) + struct.pack('<H', 8)
_SHAPE = bytes.fromhex('ffffffff00000000ffffffff0e0008000000000000000000000000000000803f0000000000000000000000000000803f0000000000000000000000000000803f0000803f0100000002000000ffffffff04000000ffffffff000000000000000000')
_LIGHTING = bytes.fromhex('ffffffff00000000ffffffff01000100000000300000020000000000803f00000000030000000000000000000000000000410000803f')


class LodError(ValueError):
    """Why not, in words for the person asking."""


# --- the chunk's mesh ---

def terrain_nif(world_name, level, x, y, verts, uvs, tris, centre=None):
    """A terrain chunk's NIF. world_name as the texture paths spell it; verts [(x, y, z)] from the chunk's corner; uvs [(u, v)];
    tris [(a, b, c)]. Its texture paths, placing and bounds follow from the rest."""
    size = level * 4096.0
    nv = len(verts)
    lox, hix = min(v[0] for v in verts), max(v[0] for v in verts)
    loy, hiy = min(v[1] for v in verts), max(v[1] for v in verts)
    zs = [v[2] for v in verts]
    real = [z for z in zs if z != SKIRT_Z] or zs
    if centre is None:
        cz = (min(zs) + max(zs)) / 2
        cx, cy = (lox + hix) / 2, (loy + hiy) / 2
        rad = max(math.sqrt((v[0] - cx) ** 2 + (v[1] - cy) ** 2 + (v[2] - cz) ** 2) for v in verts)
    else:
        cx, cy, cz, rad = centre
    px, py = x * 4096.0, y * 4096.0
    node = _NODE_HEAD + struct.pack('<3f', px, py, 0.0) + _NODE_TAIL
    paths = ['Data\\Textures\\Landscape\\LOD\\%s\\%s\\%s.n.Level%d.X%d.Y%d.dds' % (world_name, k, world_name, level, x, y) for k in ('Diffuse', 'Normals')] + [''] * 4
    texset = struct.pack('<I', 6) + b''.join(struct.pack('<I', len(p)) + p.encode('cp1252') for p in paths)
    data = [struct.pack('<iHBBB', 0, nv, 0, 0, 1), b''.join(struct.pack('<3f', *v) for v in verts),
            struct.pack('<HB', 1, 0), struct.pack('<4f', cx, cy, cz, rad), b'\0',
            b''.join(struct.pack('<2f', *t) for t in uvs),
            struct.pack('<Hi', 0, 5), struct.pack('<HIB', len(tris), 3 * len(tris), 1),
            b''.join(struct.pack('<3H', *t) for t in tris), struct.pack('<H', 0)]
    morph = b''.join(struct.pack('<f', v[2]) for v in verts)
    extra = struct.pack('<HI', nv, 1) + struct.pack('<6IB', 1, 4, 4 * nv, 4, 0, 0, 2) + struct.pack('<I', 1) + \
        struct.pack('<BIIIII', 1, 4 * nv, 1, 0, 1, 4) + morph
    # the bounds: world coordinates, height the real ground's and not the skirts'
    mid, half = (min(real) + max(real)) / 2, (max(real) - min(real)) / 2
    aabb = struct.pack('<6f', px + size / 2, py + size / 2, mid, size / 2, size / 2, half)
    blocks = [node, _SHAPE, _LIGHTING, texset, b''.join(data), extra, struct.pack('<I', 7), aabb]
    head = [HEADER_LINE, struct.pack('<IBI', 0x14020007, 1, 11), struct.pack('<I', len(blocks)), struct.pack('<I', 34), bytes((1, 0)) * 3,
            struct.pack('<H', len(NIF_TYPES))]
    head += [struct.pack('<I', len(t)) + t.encode() for t in NIF_TYPES]
    head.append(struct.pack('<%dH' % len(blocks), *range(len(blocks))))
    head.append(struct.pack('<%dI' % len(blocks), *[len(b) for b in blocks]))
    head.append(struct.pack('<III', 0, 0, 0))
    return b''.join(head) + b''.join(blocks) + struct.pack('<II', 1, 0)


def read_terrain_nif(d):
    """(verts, uvs, tris, (centre x, y, z, radius)) of a chunk."""
    s = d.find(b'\n') + 1
    nb = struct.unpack_from('<I', d, s + 9)[0]
    p = s + 17 + 6
    nt = struct.unpack_from('<H', d, p)[0]
    p += 2
    for _ in range(nt):
        p += 4 + struct.unpack_from('<I', d, p)[0]
    types = struct.unpack_from('<%dH' % nb, d, p)
    p += 2 * nb
    sizes = struct.unpack_from('<%dI' % nb, d, p)
    p += 4 * nb + 12
    for k in range(nb):
        if k == 4:
            b = d[p:p + sizes[k]]
            nv = struct.unpack_from('<H', b, 4)[0]
            q = 9
            verts = list(struct.iter_unpack('<3f', b[q:q + 12 * nv]))
            q += 12 * nv + 3
            centre = struct.unpack_from('<4f', b, q)
            q += 17
            uvs = list(struct.iter_unpack('<2f', b[q:q + 8 * nv]))
            q += 8 * nv + 6
            n = struct.unpack_from('<H', b, q)[0]
            q += 7
            tris = list(struct.iter_unpack('<3H', b[q:q + 6 * n]))
            return verts, uvs, tris, centre
        p += sizes[k]
    raise LodError('Not a terrain chunk.')


# --- DXT1 ---

def _encode_block(px):
    """Sixteen (r, g, b) as 8 bytes of DXT1: the two colours furthest apart, each pixel the nearest of the four they make."""
    best, a, b = -1, px[0], px[0]
    for p in (px[0], px[5], px[10], px[15], px[3], px[12]):
        for q in px:
            d = (p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 + (p[2] - q[2]) ** 2
            if d > best:
                best, a, b = d, p, q
    c0 = (a[0] >> 3) << 11 | (a[1] >> 2) << 5 | a[2] >> 3
    c1 = (b[0] >> 3) << 11 | (b[1] >> 2) << 5 | b[2] >> 3
    if c0 == c1:
        return struct.pack('<HHI', c0, c1, 0)
    if c0 < c1:
        c0, c1, a, b = c1, c0, b, a
    ra = (a[0] >> 3) * 255 // 31, (a[1] >> 2) * 255 // 63, (a[2] >> 3) * 255 // 31
    rb = (b[0] >> 3) * 255 // 31, (b[1] >> 2) * 255 // 63, (b[2] >> 3) * 255 // 31
    pal = (ra, rb, tuple((2 * x + y) // 3 for x, y in zip(ra, rb)), tuple((x + 2 * y) // 3 for x, y in zip(ra, rb)))
    bits = 0
    for k, p in enumerate(px):
        bd, bi = 1 << 30, 0
        for i, c in enumerate(pal):
            d = (p[0] - c[0]) ** 2 + (p[1] - c[1]) ** 2 + (p[2] - c[2]) ** 2
            if d < bd:
                bd, bi = d, i
        bits |= bi << (2 * k)
    return struct.pack('<HHI', c0, c1, bits)


def decode_dxt1(d):
    """A DXT1 DDS's top picture: (width, height, [(r, g, b)], row by row from the file's first)."""
    h, w = struct.unpack_from('<2I', d, 12)
    out = [(0, 0, 0)] * (w * h)
    p = 128
    for by in range(0, h, 4):
        for bx in range(0, w, 4):
            c0, c1, bits = struct.unpack_from('<HHI', d, p)
            p += 8
            exp = lambda c: ((c >> 11) * 255 // 31, ((c >> 5) & 63) * 255 // 63, (c & 31) * 255 // 31)
            a, b = exp(c0), exp(c1)
            if c0 > c1:
                pal = (a, b, tuple((2 * x + y) // 3 for x, y in zip(a, b)), tuple((x + 2 * y) // 3 for x, y in zip(a, b)))
            else:
                pal = (a, b, tuple((x + y) // 2 for x, y in zip(a, b)), (0, 0, 0))
            for k in range(16):
                y2, x2 = by + k // 4, bx + k % 4
                if y2 < h and x2 < w:
                    out[y2 * w + x2] = pal[bits >> (2 * k) & 3]
    return w, h, out


def dds_dxt1(pixels, size):
    """A DXT1 DDS with its mipmaps from size x size (r, g, b) rows, the way the game's are stored."""
    levels = []
    cur, n = pixels, size
    while True:
        levels.append((cur, n))
        if n == 1:
            break
        m = n // 2
        nxt = [None] * (m * m)
        for y in range(m):
            for x in range(m):
                a, b, c, d = cur[2 * y * n + 2 * x], cur[2 * y * n + 2 * x + 1], cur[(2 * y + 1) * n + 2 * x], cur[(2 * y + 1) * n + 2 * x + 1]
                nxt[y * m + x] = ((a[0] + b[0] + c[0] + d[0]) // 4, (a[1] + b[1] + c[1] + d[1]) // 4, (a[2] + b[2] + c[2] + d[2]) // 4)
        cur, n = nxt, m
    head = b'DDS ' + struct.pack('<7I', 124, 0xA1007, size, size, size * size // 2, 0, len(levels)) + b'\0' * 44 + \
        struct.pack('<2I4s5I', 32, 4, b'DXT1', 0, 0, 0, 0, 0) + struct.pack('<5I', 0x401008, 0, 0, 0, 0)
    out = [head]
    for px, n in levels:
        for by in range(0, n, 4):
            for bx in range(0, n, 4):
                blk = [px[min(n - 1, by + j) * n + min(n - 1, bx + i)] for j in range(4) for i in range(4)]
                out.append(_encode_block(blk))
    return b''.join(out)


# --- a world's chunks ---

def world_box(gd, world):
    grid = gd.grid(world)
    if not grid:
        raise LodError('This world has no cells.')
    xs, ys = [k[0] for k in grid], [k[1] for k in grid]
    return min(xs), min(ys), max(xs), max(ys)


def settings_bytes(box):
    """A world's .dlodsettings for a box of cells, as the game's are sized: the top level a quarter of the world's width, rounded
    up to a power of two, four at the least."""
    x0, y0, x1, y1 = box
    width = max(x1 - x0, y1 - y0)
    top = 4
    while top * 4 < width:
        top *= 2
    return struct.pack('<3I4hI', 4, top, top * 4, x0, y0, x1, y1, 4)


def levels_of(top):
    out, L = [], 4
    while L <= top:
        out.append(L)
        L *= 2
    return out


def chunks_for(box, top, only=None):
    """[(level, x, y)] over the box, each level counted from the south-west cell; only: cells that matter, or None for all."""
    x0, y0, x1, y1 = box
    out = []
    for L in levels_of(top):
        for y in range(y0, y1 + 1, L):
            for x in range(x0, x1 + 1, L):
                if only is None or any(x <= cx < x + L and y <= cy < y + L for cx, cy in only):
                    out.append((L, x, y))
    return out


class Sampler:
    """The land of a world as the mod has it, by point, with its colours."""

    def __init__(self, gd, pr, world, painter):
        self.gd, self.pr, self.world, self.p = gd, pr, world, painter
        self.g = roadgen.Ground(gd, pr, world)
        d = gd.fields(world).get('DNAM')
        self.default = struct.unpack_from('<f', d)[0] if d and len(d) >= 4 else 0.0
        self.colours = {}

    def height(self, x, y):
        z = self.g.at(x, y)
        return self.default if z is None else z

    def colour_cell(self, k):
        """The colours of a cell: 16 x 16 (r, g, b), from the south-west, as the flat map paints it but without its map shading."""
        if k not in self.colours:
            c = self.g.grid.get(k)
            L = self.pr.land.get(self.gd.key(c)) if c is not None and self.pr else None
            if L is None:
                e = self.gd.land_at(self.world, *k)
                L = land.decode(self.gd, e, self.p.tex) if e else None
            if L is None or not L.get('h'):
                self.colours[k] = None
            else:
                img = bytearray(16 * 16 * 4)
                sh = maptiles.LIGHT
                maptiles.LIGHT = (0.0, 0.0, 1.0)    # (flat light: the normals map does the shading)
                try:
                    self.p._cell(img, 16, 0, 0, L, None)
                finally:
                    maptiles.LIGHT = sh
                # (that paints north-up, top row first, shaded by 0.55 + 0.75: back to plain)
                rows = []
                for r in range(16):
                    for col in range(16):
                        o = ((15 - r) * 16 + col) * 4
                        rows.append(tuple(min(255, int(v / 1.3)) for v in img[o:o + 3]))
                self.colours[k] = rows
        return self.colours[k]

    def colour(self, x, y):
        k = (int(x // 4096), int(y // 4096))
        rows = self.colour_cell(k)
        if not rows:
            return (128, 116, 96)
        c, r = min(15, int((x - k[0] * 4096) / 256)), min(15, int((y - k[1] * 4096) / 256))
        return rows[r * 16 + c]


def chunk_mesh(S, level, cx, cy):
    """A regular grid over a chunk with its skirt: (verts, uvs, tris) wound as the game's are."""
    n = 64 if level == 4 else 32
    size = level * 4096.0
    step = size / n
    px, py = cx * 4096.0, cy * 4096.0
    verts, uvs, tris = [], [], []
    for j in range(n + 1):
        for i in range(n + 1):
            x, y = i * step, j * step
            verts.append((x, y, float(round(S.height(px + x, py + y) / 8) * 8)))
            uvs.append((1.0 - x / size, y / size))
    at = lambda i, j: j * (n + 1) + i
    for j in range(n):
        for i in range(n):
            tris += [(at(i, j), at(i + 1, j), at(i + 1, j + 1)), (at(i, j), at(i + 1, j + 1), at(i, j + 1))]
    # the skirt: a copy of each edge point at the bottom, a wall down from the edge
    ring = [at(i, 0) for i in range(n)] + [at(n, j) for j in range(n)] + [at(i, n) for i in range(n, 0, -1)] + [at(0, j) for j in range(n, 0, -1)]
    base = len(verts)
    for v in ring:
        verts.append((verts[v][0], verts[v][1], SKIRT_Z))
        uvs.append(uvs[v])
    for k in range(len(ring)):
        a, b = ring[k], ring[(k + 1) % len(ring)]
        d, c = base + k, base + (k + 1) % len(ring)
        tris += [(a, d, c), (a, c, b)]
    return verts, uvs, tris


def chunk_textures(S, level, cx, cy):
    """(diffuse, normals) DDS bytes for a chunk. Each picture runs as its UVs say: its first row at the south, its first column at
    the east. Normals: red and green each way across the map (x, y) as (n + 1) / 2, blue up."""
    px, py = cx * 4096.0, cy * 4096.0
    size = level * 4096.0
    t = TEXTURE
    step = size / t
    diffuse, normal = [None] * (t * t), [None] * (t * t)
    near = max(128.0, step)
    for r in range(t):
        y = py + (r + 0.5) * step
        for c in range(t):
            x = px + size - (c + 0.5) * step
            diffuse[r * t + c] = S.colour(x, y)
            dx = (S.height(x + near, y) - S.height(x - near, y)) / (2 * near)
            dy = (S.height(x, y + near) - S.height(x, y - near)) / (2 * near)
            ln = math.sqrt(dx * dx + dy * dy + 1)
            normal[r * t + c] = (int((-dx / ln + 1) * 127.5), int((-dy / ln + 1) * 127.5), int((1 / ln + 1) * 127.5))
    return dds_dxt1(diffuse, t), dds_dxt1(normal, t)


def out_folder(pr):
    return os.path.join(project.BUILD_DIR, os.path.splitext(pr.plugin)[0] + ' distant land')


def report_for(gd, pr, world):
    """How far this goes for a world, in words the page shows: what exists and what would be made."""
    edid = gd.edid(world)
    low = edid.lower()
    have_terrain = sum(1 for a in gd.archives() for n in a.files if n.startswith('meshes\\landscape\\lod\\' + low + '\\') and n.endswith('.nif') and '\\blocks\\' not in n)
    have_blocks = sum(1 for a in gd.archives() for n in a.files if n.startswith('meshes\\landscape\\lod\\' + low + '\\blocks\\'))
    settings = gd.find_file('lodsettings\\' + low + '.dlodsettings')
    box = world_box(gd, world)
    top = struct.unpack_from('<I', settings_bytes(box), 4)[0]
    grid = gd.grid(world)
    back = {c: xy for xy, c in grid.items()}
    changed = sorted({back[gd.from_key(k)] for k in set(pr.land) if not k.startswith('+') and gd.from_key(k) in back}) if pr else []
    every = chunks_for(box, top)
    own = bool(pr and pr.source and gd.names[world >> 24] == pr.plugin.lower())
    return {'world': edid, 'box': list(box), 'levels': levels_of(top), 'game_terrain': have_terrain, 'game_objects': have_blocks, 'settings': bool(settings), 'own_world': own,
            'changed_cells': len(changed), 'all_chunks': len(every), 'changed_chunks': len(chunks_for(box, top, changed)) if changed else 0,
            'folder': out_folder(pr) if pr else ''}


def generate(gd, pr, world, out, only_changed=None, progress=None):
    """Write a world's terrain into a folder laid out as Data is. only_changed: chunks only over the cells the mod's land changes
    (for a game world with its own files), the default when the world has files of the game's already. Returns a report."""
    edid = gd.edid(world)
    low = edid.lower()
    box = world_box(gd, world)
    settings = settings_bytes(box)
    top = struct.unpack_from('<I', settings, 4)[0]
    exists = bool(gd.find_file('lodsettings\\' + low + '.dlodsettings'))
    if only_changed is None:
        only_changed = exists
    only = None
    if only_changed:
        back = {c: xy for xy, c in gd.grid(world).items()}
        only = {back[gd.from_key(k)] for k in pr.land if not k.startswith('+') and gd.from_key(k) in back}
        if exists:
            # (a game world's chunks are counted from its own south-west corner)
            have = gd.read_file('lodsettings\\' + low + '.dlodsettings')
            _a, top, _c, xa, ya, xb, yb, _d = struct.unpack('<3I4hI', have[:24])
            box = (xa, ya, xb, yb)
        if not only:
            return {'chunks': 0, 'files': 0, 'note': 'Your mod hasn\'t changed the land in this world.'}
    painter = maptiles.Painter(gd)
    S = Sampler(gd, pr, world, painter)
    work = chunks_for(box, top, only)
    files = []

    def put(rel, data):
        path = os.path.join(out, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'wb') as f:
            f.write(data)
        files.append(rel)
    if not exists:
        put(os.path.join('lodsettings', edid + '.dlodsettings'), settings)
    base = os.path.join('meshes', 'landscape', 'lod', edid)
    tex = os.path.join('textures', 'landscape', 'lod', edid)
    for n, (L, x, y) in enumerate(work):
        if progress:
            progress(n, len(work))
        v, u, t = chunk_mesh(S, L, x, y)
        put(os.path.join(base, '%s.level%d.x%d.y%d.nif' % (edid, L, x, y)), terrain_nif(edid, L, x, y, v, u, t))
        d, m = chunk_textures(S, L, x, y)
        put(os.path.join(tex, 'diffuse', '%s.n.level%d.x%d.y%d.dds' % (edid, L, x, y)), d)
        put(os.path.join(tex, 'normals', '%s.n.level%d.x%d.y%d.dds' % (edid, L, x, y)), m)
    return {'chunks': len(work), 'files': len(files), 'levels': levels_of(top), 'folder': out, 'settings_written': not exists, 'partial': bool(only)}


# --- into the game and out, at the person's choice ---

def manifest_path(pr):
    return os.path.join(project.BUILD_DIR, os.path.splitext(pr.plugin)[0] + ' distant land.json')


def install(pr, data_dir, out=None):
    """Copy the made files into Data, noting what went in. Any file already there is kept in backups first."""
    out = out or out_folder(pr)
    if not os.path.isdir(out):
        raise LodError('Make the distant land first.')
    done = []
    backups = os.path.join(project.HOME, 'backups', os.path.splitext(pr.plugin)[0] + ' distant land')
    for d, _dirs, names in os.walk(out):
        for name in names:
            src = os.path.join(d, name)
            rel = os.path.relpath(src, out)
            dest = os.path.join(data_dir, rel)
            if os.path.exists(dest):
                keep = os.path.join(backups, rel)
                os.makedirs(os.path.dirname(keep), exist_ok=True)
                shutil.copy2(dest, keep)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copy2(src, dest)
            done.append(rel)
    os.makedirs(project.BUILD_DIR, exist_ok=True)
    with open(manifest_path(pr), 'w', encoding='utf-8') as f:
        json.dump({'files': done, 'backups': backups}, f)
    return len(done)


def uninstall(pr, data_dir):
    """Take out exactly what install put in, putting back what it replaced."""
    try:
        with open(manifest_path(pr), encoding='utf-8') as f:
            m = json.load(f)
    except OSError:
        raise LodError('FOLab hasn\'t put this mod\'s distant land in the game.')
    n = 0
    for rel in m['files']:
        dest = os.path.join(data_dir, rel)
        keep = os.path.join(m['backups'], rel)
        if os.path.exists(keep):
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copy2(keep, dest)
        elif os.path.exists(dest):
            os.remove(dest)
        n += 1
    os.remove(manifest_path(pr))
    return n
