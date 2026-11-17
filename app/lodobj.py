"""Distant buildings: what the game shows of a world's buildings, roads and big things beyond the cells it has loaded.
The other half of lodgen.py (which makes the distant ground), worked out from the game's own files and proven by
rebuilding them (tests/test_lodobj.py).

What New Vegas reads, by the world's editor ID:
  meshes\\landscape\\lod\\<id>\\blocks\\<id>.level4.x<X>.y<Y>.nif   every far thing in the 4 x 4 cells from cell (X, Y), as one model
  textures\\landscape\\lod\\<id>\\blocks\\<id>.Buildings.dds        one sheet of every texture those models use
  textures\\landscape\\lod\\<id>\\blocks\\<id>.Buildings_n.dds      the same sheet's bumps

Where the far things come from: beside a thing's model the game often ships a plain stand-in for it, the same name with
_lod on the end (1,283 of them). A placed thing whose model has one is shown from afar; one without isn't, here as in the
game's own worlds (small buildings appear as you come near).

A block's model is one shape: BSMultiBoundNode > BSSegmentedTriShape (placed at the block's south-west corner; its corners
are counted from there) > NiTriShapeData with normals, tangents and one set of texture coordinates into the sheet. The
shape's triangles are kept in segments, one for each of the block's 16 cells, numbered x * 4 + y from the south-west: the
game hides a cell's segment once the cell itself is loaded, so each thing's triangles go in the segment of the cell it
stands in (by where it is placed, not where each triangle lies). The list of segments stops after the last one in use.

lodsettings\\<id>.dlodsettings (lodgen.py writes it) must exist, or the world shows nothing far off at all."""
import math
import os
import struct

import dds
import lodgen
import nif

CELL = 4096.0
BLOCK = 4
TYPES = ['BSMultiBoundNode', 'BSSegmentedTriShape', 'BSShaderPPLightingProperty', 'BSShaderTextureSet', 'NiTriShapeData', 'BSMultiBound', 'BSMultiBoundAABB']
# The fixed parts of a block's model, as every block in the game has them
_NODE = bytes.fromhex('ffffffff00000000ffffffff0e0808000000000000000000000000000000803f0000000000000000000000000000803f'
                      '0000000000000000000000000000803f0000803f00000000ffffffff01000000010000000000000005000000')
_SHAPE_HEAD = bytes.fromhex('ffffffff00000000ffffffff0e000800')
_SHAPE_TAIL = bytes.fromhex('0000803f0000000000000000000000000000803f0000000000000000000000000000803f0000803f'
                            '0100000002000000ffffffff04000000ffffffff000000000000000000')
_LIGHTING = bytes.fromhex('ffffffff00000000ffffffff01000100000000200000040000000000803f00000000030000000000000000000000000000410000803f')
MAX_VERTS = 65000           # (a shape's corners are numbered in 16 bits)
TILE = 256                  # each texture's square on the sheet, in pixels (at 128 a ship's hull seen across the bay was a smear)
OWN_BIG = 500.0             # a thing of the mod's own this big with no far model of its own is shown far off as it is
MAX_REPEAT = 4              # a texture a stand-in repeats more than this many times across is shown this many
TREE_WORDS = ('tree', 'palm', 'bush', 'shrub', 'cactus', 'joshua', 'yucca')


class LodError(ValueError):
    """Why not, in words for the person asking."""


def block_nif(world_name, x, y, verts, normals, tangents, uvs, segments, bounds=None, sphere=None, flags=(0x33, 0x1001)):
    """A block's model. x, y: its south-west cell. verts, normals [(x, y, z)], uvs [(u, v)]: one for each corner, verts
    counted from the block's corner; tangents: the raw tangents and bitangents (24 bytes a corner). segments: 16 lists of
    triangles [(a, b, c)], cell x * 4 + y of the block. bounds: (centre x y z, half sizes x y z) in the world, worked out
    when not given; sphere: (centre x y z, radius) of the corners, likewise."""
    nv = len(verts)
    if nv > 0xFFFF:
        raise LodError('A block has too many corners (%d).' % nv)
    px, py = x * CELL, y * CELL
    used = max([k + 1 for k, s in enumerate(segments) if s] or [0])
    tris, seg_bytes, at = [], [], 0
    for s in segments[:used]:
        seg_bytes.append(struct.pack('<BII', 0, at if s else 0, len(s)))
        tris += s
        at += 3 * len(s)
    shape = _SHAPE_HEAD + struct.pack('<3f', px, py, 0.0) + _SHAPE_TAIL + struct.pack('<I', used) + b''.join(seg_bytes)
    names = ['Data\\Textures\\Landscape\\LOD\\%s\\Blocks\\%s.Buildings.dds' % (world_name, world_name),
             'Data\\Textures\\Landscape\\LOD\\%s\\Blocks\\%s.Buildings_n.dds' % (world_name, world_name)] + [''] * 4
    texset = struct.pack('<I', 6) + b''.join(struct.pack('<I', len(p)) + p.encode('cp1252') for p in names)
    xs, ys, zs = [v[0] for v in verts], [v[1] for v in verts], [v[2] for v in verts]
    if sphere is None:
        cx, cy, cz = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, (min(zs) + max(zs)) / 2
        sphere = (cx, cy, cz, max(math.sqrt((v[0] - cx) ** 2 + (v[1] - cy) ** 2 + (v[2] - cz) ** 2) for v in verts))
    if bounds is None:
        bounds = (px + (min(xs) + max(xs)) / 2, py + (min(ys) + max(ys)) / 2, (min(zs) + max(zs)) / 2,
                  (max(xs) - min(xs)) / 2, (max(ys) - min(ys)) / 2, (max(zs) - min(zs)) / 2)
    data = [struct.pack('<iHBBB', 0, nv, flags[0], 0, 1), b''.join(struct.pack('<3f', *v) for v in verts),
            struct.pack('<HB', flags[1], 1), b''.join(struct.pack('<3f', *n) for n in normals), tangents,
            struct.pack('<4f', *sphere), b'\0', b''.join(struct.pack('<2f', *t) for t in uvs),
            struct.pack('<Hi', 0, -1), struct.pack('<HIB', len(tris), 3 * len(tris), 1),
            b''.join(struct.pack('<3H', *t) for t in tris), struct.pack('<H', 0)]
    blocks = [_NODE, shape, _LIGHTING, texset, b''.join(data), struct.pack('<I', 6), struct.pack('<6f', *bounds)]
    head = [lodgen.HEADER_LINE, struct.pack('<IBI', 0x14020007, 1, 11), struct.pack('<I', len(blocks)), struct.pack('<I', 34), bytes((1, 0)) * 3,
            struct.pack('<H', len(TYPES))]
    head += [struct.pack('<I', len(t)) + t.encode() for t in TYPES]
    head.append(struct.pack('<%dH' % len(blocks), *range(len(blocks))))
    head.append(struct.pack('<%dI' % len(blocks), *[len(b) for b in blocks]))
    head.append(struct.pack('<III', 0, 0, 0))
    return b''.join(head) + b''.join(blocks) + struct.pack('<II', 1, 0)


def read_block_nif(d):
    """What block_nif takes, from one of the game's own (or ours): {'x0', 'y0' (the shape's place), 'verts', 'normals',
    'tangents', 'uvs', 'segments', 'bounds', 'sphere', 'flags', 'world'}."""
    f = nif.Nif(d)
    if f.types != TYPES:
        raise LodError('not a block of distant buildings: %s' % f.types)
    raw = d[f.offsets[1]:f.offsets[1] + f.sizes[1]]
    x0, y0 = struct.unpack_from('<2f', raw, 16)
    used = struct.unpack_from('<I', raw, 97)[0]
    segs = [struct.unpack_from('<BII', raw, 101 + 9 * k) for k in range(used)]
    g = d[f.offsets[4]:f.offsets[4] + f.sizes[4]]
    _grp, nv, keep, _comp, _has = struct.unpack_from('<iHBBB', g, 0)
    p = 9
    verts = [struct.unpack_from('<3f', g, p + 12 * k) for k in range(nv)]
    p += 12 * nv
    vflags, _hn = struct.unpack_from('<HB', g, p)
    p += 3
    normals = [struct.unpack_from('<3f', g, p + 12 * k) for k in range(nv)]
    p += 12 * nv
    tangents = g[p:p + 24 * nv] if vflags & 0x1000 else b''
    p += len(tangents)
    sphere = struct.unpack_from('<4f', g, p)
    p += 17
    uvs = [struct.unpack_from('<2f', g, p + 8 * k) for k in range(nv)]
    p += 8 * nv + 6
    ntri = struct.unpack_from('<H', g, p)[0]
    p += 7
    tris = [struct.unpack_from('<3H', g, p + 6 * k) for k in range(ntri)]
    segments = [tris[i // 3:i // 3 + n] if n else [] for _f, i, n in segs] + [[] for _ in range(16 - used)]
    t = d[f.offsets[3]:f.offsets[3] + f.sizes[3]]
    ln = struct.unpack_from('<I', t, 4)[0]
    world = t[8:8 + ln].decode('cp1252').split('\\')[4]
    return {'x0': x0, 'y0': y0, 'verts': verts, 'normals': normals, 'tangents': tangents, 'uvs': uvs, 'segments': segments,
            'bounds': struct.unpack('<6f', d[f.offsets[6]:f.offsets[6] + 24]), 'sphere': sphere, 'flags': (keep, vflags), 'world': world}


# ---------- the stand-in models ----------

class StandIns:
    """A base form's far model, if the game ships one: its shapes in the thing's own frame, read once."""

    def __init__(self, gd, pr=None):
        self.gd = gd
        self.pr = pr                # (a base that is one of the mod's own records comes as its key, '+...')
        self.by_model = {}
        self.models = {}

    def of_model(self, model):
        low = (model or '').lower().replace('/', '\\')
        if low not in self.by_model:
            shapes = None
            if low.endswith('.nif'):
                path = 'meshes\\' + low[:-4] + '_lod.nif'
                try:
                    data = self.gd.read_file(path)
                    shapes = [s for s in nif.mesh_from_nif(data) if s['uv'] and s['i']] if data else None
                except Exception:
                    shapes = None
            self.by_model[low] = shapes or None
        return self.by_model[low]

    def of(self, base_fid):
        if base_fid not in self.models:
            try:
                if isinstance(base_fid, str):
                    import recordio
                    rec = self.pr.records.get(base_fid) if self.pr else None
                    self.models[base_fid] = (recordio.field(rec, 'MODL') or '') if rec else ''
                else:
                    f = self.gd.fields(base_fid)
                    m = f.get('MODL')
                    self.models[base_fid] = m[:-1].decode('cp1252', 'replace') if m else ''
            except Exception:
                self.models[base_fid] = ''
        got = self.of_model(self.models[base_fid])
        if got is None and isinstance(base_fid, str) and self.models[base_fid]:
            got = self.whole(self.models[base_fid])
        return got

    def whole(self, model):
        """A big model of the mod's own (a ship's deck out of another game) as its own far model, where none was made for
        it: without, parts of the ship were missing from across the water. None for anything small."""
        low = 'whole:' + model.lower().replace('/', chr(92))
        if low not in self.by_model:
            shapes = None
            try:
                data = self.gd.read_file('meshes' + chr(92) + low[6:])
                got = [s for s in nif.mesh_from_nif(data) if s['uv'] and s['i'] and s.get('alpha') != 'blend'] if data else []
                # (not what FOLab made itself, which has a far model where it should be seen far off, nor anything of
                # leaves: thousands of big jungle plants filled every block and crowded the buildings out)
                if low[6:].startswith('folab' + chr(92)) or any(s.get('alpha') for s in got):
                    got = []
                xs = [v for s in got for v in s['p'][0::3]]
                ys = [v for s in got for v in s['p'][1::3]]
                zs = [v for s in got for v in s['p'][2::3]]
                if xs and max(max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs)) >= OWN_BIG:
                    shapes = got
            except Exception:
                shapes = None
            self.by_model[low] = shapes
        return self.by_model[low]


# ---------- the sheet ----------

class Sheet:
    """Every texture the far models use, each in a square of one picture. A texture a model repeats across itself gets a
    square with it repeated that many times, since a sheet's squares can't repeat."""

    def __init__(self, gd):
        self.gd = gd
        self.repeat = {}        # texture path -> how many times across
        self.place = {}

    def want(self, tex, repeat):
        r = max(1, min(MAX_REPEAT, int(math.ceil(repeat - 1e-6))))
        self.repeat[tex] = max(self.repeat.get(tex, 1), r)

    def build(self):
        """Lay the squares out. Returns (size in pixels, [(r, g, b)] rows from the top)."""
        names = sorted(self.repeat)
        across = 1
        while across * across < len(names):
            across *= 2
        size = max(256, across * TILE)
        tile = size // across
        px = [(96, 90, 80)] * (size * size)
        for n, tex in enumerate(names):
            tx, ty = n % across, n // across
            self.place[tex] = (tx / across, ty / across, 1.0 / across, self.repeat[tex])
            pic = None
            try:
                data = self.gd.read_file(tex if tex.lower().startswith('textures') else 'textures\\' + tex)
                pic = dds.decode(data, tile) if data else None
            except Exception:
                pic = None
            if not pic:
                continue
            w, h, rgba = pic[0], pic[1], pic[2]
            rep = self.repeat[tex]
            for y in range(tile):
                sy = int(y * rep * h / tile) % h
                row = (ty * tile + y) * size + tx * tile
                for x in range(tile):
                    o = (sy * w + int(x * rep * w / tile) % w) * 4
                    px[row + x] = (rgba[o], rgba[o + 1], rgba[o + 2])
        return size, px

    def uv(self, tex, u, v, u0, v0):
        """Where a model's texture coordinate lands on the sheet. u0, v0: the model's lowest, taken off first so it starts in its square."""
        ox, oy, span, rep = self.place[tex]
        inset = 0.5 / (TILE * 8)        # (kept a hair inside the square, so the next one doesn't bleed in)
        fu = min(1.0, max(0.0, (u - u0) / rep))
        fv = min(1.0, max(0.0, (v - v0) / rep))
        return ox + inset + fu * (span - 2 * inset), oy + inset + fv * (span - 2 * inset)


def _normals(pos, idx):
    """A normal for each corner, from the triangles round it."""
    n = [[0.0, 0.0, 0.0] for _ in range(len(pos) // 3)]
    for k in range(0, len(idx) - 2, 3):
        a, b, c = idx[k], idx[k + 1], idx[k + 2]
        ax, ay, az = pos[3 * a:3 * a + 3]
        ux, uy, uz = pos[3 * b] - ax, pos[3 * b + 1] - ay, pos[3 * b + 2] - az
        vx, vy, vz = pos[3 * c] - ax, pos[3 * c + 1] - ay, pos[3 * c + 2] - az
        cr = (uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx)
        for q in (a, b, c):
            n[q][0] += cr[0]
            n[q][1] += cr[1]
            n[q][2] += cr[2]
    out = []
    for x, y, z in n:
        L = math.sqrt(x * x + y * y + z * z) or 1.0
        out.append((x / L, y / L, z / L))
    return out


def things_of(gd, pr, world):
    """Every placed thing of a world as (base form, x, y, z, turn about z, size): the game's own, less what the mod took out
    or moved, and the mod's."""
    grid = gd.grid(world)
    out = []
    gone = {}
    for ck, c in (pr.cells.items() if pr else ()):
        for rk, r in c['refs'].items():
            if not rk.startswith('+'):
                gone[rk] = r
    cells = set(grid.values())
    keep = gd.world_persistent.get(world)
    if keep is not None:
        cells.add(keep)
    for cell in cells:
        for r in gd.refs(cell):
            ch = gone.get(gd.key(r['ref']))
            if ch is not None and ch.get('removed'):
                continue
            p = (ch.get('p') if ch else None) or (list(r['pos']) + list(r['rot']))
            out.append((r['base'], p[0], p[1], p[2], p[5], float((ch or {}).get('s') or r.get('scale') or 1.0)))
    for ck, c in (pr.cells.items() if pr else ()):
        if ck.startswith('+'):
            continue
        try:
            cell = gd.from_key(ck)
        except Exception:
            continue
        if cell not in cells:
            continue
        for rk, r in c['refs'].items():
            if rk.startswith('+') and r.get('base') and r.get('p') and not r.get('removed'):
                try:
                    # (a thing of the mod's own making, a ship out of another game say, goes by its record's key)
                    base = r['base'] if r['base'].startswith('+') else gd.from_key(r['base'])
                except Exception:
                    continue
                p = r['p']
                out.append((base, p[0], p[1], p[2], p[5] if len(p) > 5 else 0.0, float(r.get('s') or 1.0)))
    return out


def generate(gd, pr, world, out, progress=None, trees=False, like=None):
    """Write a world's distant buildings into a folder laid out as Data is. Returns a report. trees: far plants too (the
    game shows its own trees another way; as plain models they cost a lot for what they add). like: another world whose
    things this one shows far off (as lodgen's like), named for this one."""
    edid = gd.edid(world)
    if like is not None:
        world = like
    stand = StandIns(gd, pr)
    sheet = Sheet(gd)
    blocks = {}
    shown = skipped = 0
    sw_x, sw_y = lodgen.world_box(gd, world)[:2]         # (blocks are counted from the world's south-west cell, as its settings file says)
    kinds = {}
    for base, x, y, z, rz, s in things_of(gd, pr, world):
        shapes = stand.of(base)
        if not shapes:
            skipped += 1
            continue
        if not trees and not isinstance(base, str) and any(w in gd.edid(base).lower() for w in TREE_WORDS):
            skipped += 1
            continue
        cx, cy = int(math.floor(x / CELL)), int(math.floor(y / CELL))
        bx, by = sw_x + ((cx - sw_x) // BLOCK) * BLOCK, sw_y + ((cy - sw_y) // BLOCK) * BLOCK
        blocks.setdefault((bx, by), []).append((shapes, x, y, z, rz, s, (cx - bx) * BLOCK + (cy - by)))
        shown += 1
        kinds[base] = kinds.get(base, 0) + 1
        for sh in shapes:
            uv = sh['uv']
            sheet.want(sh['tex'], max(max(uv[0::2]) - math.floor(min(uv[0::2])), max(uv[1::2]) - math.floor(min(uv[1::2]))))
    if not blocks:
        return {'blocks': 0, 'things': 0, 'skipped': skipped, 'note': 'Nothing in this world has a far model of the game\'s.'}
    files = []

    def put(rel, data):
        path = os.path.join(out, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'wb') as f:
            f.write(data)
        files.append(rel)
    size, px = sheet.build()
    tex_dir = os.path.join('textures', 'landscape', 'lod', edid, 'blocks')
    put(os.path.join(tex_dir, edid + '.Buildings.dds'), lodgen.dds_dxt1(px, size))
    put(os.path.join(tex_dir, edid + '.Buildings_n.dds'), lodgen.dds_dxt1([(128, 128, 255)] * (64 * 64), 64))
    dropped = 0
    for n, ((bx, by), items) in enumerate(sorted(blocks.items())):
        if progress:
            progress(n, len(blocks))
        verts, normals, uvs = [], [], []
        segments = [[] for _ in range(16)]
        ox, oy = bx * CELL, by * CELL
        for shapes, x, y, z, rz, s, seg in items:
            if len(verts) + sum(len(sh['p']) // 3 for sh in shapes) > MAX_VERTS:
                dropped += 1
                continue
            c, sn = math.cos(rz), math.sin(rz)
            for sh in shapes:
                p, uv, idx = sh['p'], sh['uv'], sh['i']
                first = len(verts)
                u0, v0 = math.floor(min(uv[0::2])), math.floor(min(uv[1::2]))
                nn = _normals(p, idx)
                for k in range(len(p) // 3):
                    lx, ly, lz = p[3 * k] * s, p[3 * k + 1] * s, p[3 * k + 2] * s
                    verts.append((x + lx * c + ly * sn - ox, y - lx * sn + ly * c - oy, z + lz))
                    a, b, cz = nn[k]
                    normals.append((a * c + b * sn, -a * sn + b * c, cz))
                    uvs.append(sheet.uv(sh['tex'], uv[2 * k], uv[2 * k + 1], u0, v0))
                segments[seg] += [(first + idx[k], first + idx[k + 1], first + idx[k + 2]) for k in range(0, len(idx) - 2, 3)]
        if not verts:
            continue
        # (tangents the plain way: along the ground, and up; the sheet's bumps are flat, so they change nothing seen)
        tangents = b''.join(struct.pack('<3f', 1.0, 0.0, 0.0) for _ in verts) + b''.join(struct.pack('<3f', 0.0, 1.0, 0.0) for _ in verts)
        put(os.path.join('meshes', 'landscape', 'lod', edid, 'blocks', '%s.level4.x%d.y%d.nif' % (edid, bx, by)),
            block_nif(edid, bx, by, verts, normals, tangents, uvs, segments))
    return {'blocks': len(blocks), 'things': shown, 'skipped': skipped, 'dropped': dropped, 'kinds': len(kinds), 'textures': len(sheet.repeat),
            'sheet': size, 'files': len(files), 'folder': out}


# ---------- far things for the editor's own view ----------

class Far:
    """What stands far off, for FOLab's 3D view to draw past the cells it has in full: by map tile (16 x 16 cells), every
    placed thing the game ships a far model for, with that model's file. The game's own are read once a tile; the mod's
    changes are laid over them each time asked, so an edit shows without anything being worked out again."""
    TILE = 16

    def __init__(self, gd):
        self.gd = gd
        self.st = StandIns(gd)
        self.paths = {}
        self.game = {}

    def path(self, base):
        """The far model's file for a base form, or None."""
        if base not in self.paths:
            got = None
            if base in self.gd.forms and self.st.of(base):
                got = 'meshes\\' + self.st.models[base].lower().replace('/', '\\')[:-4] + '_lod.nif'
            self.paths[base] = got
        return self.paths[base]

    def own(self, pr, key):
        """The far model's file for a record of the mod's own (a hotel FOLab made, a ship out of another game), or None:
        by its model, since the same key is another record in another mod."""
        import recordio
        rec = pr.records.get(key) if pr else None
        model = ((recordio.field(rec, 'MODL') or '') if rec else '').lower().replace('/', chr(92))
        if not model.endswith('.nif'):
            return None
        if model not in self.paths:
            self.paths[model] = 'meshes' + chr(92) + model[:-4] + '_lod.nif' if self.st.of_model(model) else None
        return self.paths[model]

    def _cells(self, world, tx, ty):
        grid = self.gd.grid(world)
        for i in range(self.TILE):
            for j in range(self.TILE):
                c = grid.get((tx * self.TILE + i, ty * self.TILE + j))
                if c is not None:
                    yield c

    def _game(self, world, tx, ty):
        k = (world, tx, ty)
        if k not in self.game:
            out = []
            for cell in self._cells(world, tx, ty):
                for r in self.gd.refs(cell):
                    if not r['base'] or not r['pos'] or not r['rot']:
                        continue
                    p = self.path(r['base'])
                    if p:
                        out.append((self.gd.key(r['ref']), self.gd.key(cell), p, r['pos'][0], r['pos'][1], r['pos'][2], r['rot'][2], float(r.get('scale') or 1.0)))
            if len(self.game) > 400:
                self.game.clear()
            self.game[k] = out
        return self.game[k]

    def tile(self, pr, world, tx, ty):
        """{'models': [file...], 'things': [[which model, x, y, z, turn, size]...]}"""
        models, things = {}, []

        def add(path, x, y, z, rz, s):
            things.append([models.setdefault(path, len(models)), round(x, 1), round(y, 1), round(z, 1), round(rz, 4), round(s, 3)])

        cells = pr.cells if pr else {}
        for rk, ck, path, x, y, z, rz, s in self._game(world, tx, ty):
            ch = (cells.get(ck) or {}).get('refs', {}).get(rk) if cells else None
            if ch:
                if ch.get('removed'):
                    continue
                p = ch.get('p')
                if p:
                    x, y, z, rz = p[0], p[1], p[2], p[5] if len(p) > 5 else rz
                s = float(ch.get('s') or s)
            add(path, x, y, z, rz, s)
        for cell in (self._cells(world, tx, ty) if cells else ()):
            c = cells.get(self.gd.key(cell))
            for rk, r in (c['refs'].items() if c else ()):
                if not rk.startswith('+') or not r.get('base') or not r.get('p') or r.get('removed'):
                    continue
                try:
                    path = self.own(pr, r['base']) if r['base'].startswith('+') else self.path(self.gd.from_key(r['base']))
                except Exception:
                    path = None
                if path:
                    p = r['p']
                    add(path, p[0], p[1], p[2], p[5] if len(p) > 5 else 0.0, float(r.get('s') or 1.0))
        return {'models': list(models), 'things': things}
