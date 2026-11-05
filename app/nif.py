"""Reads New Vegas / Fallout 3 meshes (NIF 20.2.0.7, user version 11, Bethesda version 34) for the 3D view.

Unlike Morrowind's 4.0.0.2 files, these list every block's type and size in the header, so each block is
parsed on its own and every parse that understands a block is checked to end exactly at the block's size."""
import struct

VERSION = 0x14020007
NODE_TYPES = {'NiNode', 'BSFadeNode', 'BSMultiBoundNode', 'BSOrderedNode', 'BSValueNode', 'BSBlastNode',
              'BSDamageStage', 'BSDebrisNode', 'BSMasterParticleSystem', 'NiBillboardNode', 'NiSwitchNode',
              'NiLODNode', 'BSTreeNode', 'NiBSAnimationNode', 'NiBSParticleNode'}
GEOM_TYPES = {'NiTriShape', 'NiTriStrips'}
DATA_TYPES = {'NiTriShapeData', 'NiTriStripsData'}
APP_CULLED = 0x1


class NifError(ValueError):
    pass


class Reader:
    __slots__ = ('d', 'p')

    def __init__(self, d, p=0):
        self.d, self.p = d, p

    def u8(self):
        v = self.d[self.p]
        self.p += 1
        return v

    def u16(self):
        v = struct.unpack_from('<H', self.d, self.p)[0]
        self.p += 2
        return v

    def u32(self):
        v = struct.unpack_from('<I', self.d, self.p)[0]
        self.p += 4
        return v

    def i32(self):
        v = struct.unpack_from('<i', self.d, self.p)[0]
        self.p += 4
        return v

    def f32(self):
        v = struct.unpack_from('<f', self.d, self.p)[0]
        self.p += 4
        return v

    def many(self, fmt, n):
        size = struct.calcsize('<%d%s' % (n, fmt))
        v = struct.unpack_from('<%d%s' % (n, fmt), self.d, self.p)
        self.p += size
        return v

    def sized(self):
        n = self.u32()
        s = self.d[self.p:self.p + n].decode('cp1252', 'replace')
        self.p += n
        return s

    def short(self):
        n = self.u8()
        s = self.d[self.p:self.p + n].rstrip(b'\0').decode('cp1252', 'replace')
        self.p += n
        return s


class Nif:
    """Header, block table and raw block bytes; parse() turns the blocks we understand into dicts."""

    def __init__(self, data):
        self.data = data
        nl = data.find(b'\n')
        if nl < 0 or not data.startswith(b'Gamebryo File Format'):
            raise NifError('not a Gamebryo file')
        r = Reader(data, nl + 1)
        self.version = r.u32()
        if self.version != VERSION:
            raise NifError('version %08X, expected 20.2.0.7' % self.version)
        r.u8()                                  # endian: little
        self.user = r.u32()
        n = r.u32()
        self.bsver = r.u32()
        r.short(); r.short(); r.short()         # author, process script, export script
        types = [r.sized() for _ in range(r.u16())]
        self.types = [types[t & 0x7FFF] for t in r.many('H', n)]
        sizes = r.many('I', n)
        nstr = r.u32()
        r.u32()                                 # longest string
        self.strings = [r.sized() for _ in range(nstr)]
        r.many('I', r.u32())                    # groups
        self.offsets = []
        p = r.p
        for s in sizes:
            self.offsets.append(p)
            p += s
        self.sizes = sizes
        if p > len(data):
            raise NifError('blocks run past the end of the file')
        self.blocks = [None] * n

    def string(self, i):
        return self.strings[i] if 0 <= i < len(self.strings) else ''

    def block(self, i):
        """The parsed block, or None when its type is not one we read (or i is not a block)."""
        if not 0 <= i < len(self.blocks):
            return None
        if self.blocks[i] is None:
            t = self.types[i]
            fn = _PARSERS.get(t)
            if fn is None:
                self.blocks[i] = False
            else:
                r = Reader(self.data, self.offsets[i])
                b = fn(self, r, t)
                end = self.offsets[i] + self.sizes[i]
                if r.p != end:
                    raise NifError('%s block %d read %d bytes of %d' % (t, i, r.p - self.offsets[i], self.sizes[i]))
                b['type'] = t
                self.blocks[i] = b
        return self.blocks[i] or None


def _object_net(nif, r, b):
    b['name'] = nif.string(r.i32())
    b['extra'] = r.many('i', r.u32())
    b['controller'] = r.i32()


def _av_object(nif, r, b):
    _object_net(nif, r, b)
    b['flags'] = r.u32() if nif.bsver > 26 else r.u16()
    b['t'] = r.many('f', 3)
    m = r.many('f', 9)
    b['R'] = (m[0:3], m[3:6], m[6:9])
    b['s'] = r.f32()
    b['props'] = r.many('i', r.u32())
    b['collision'] = r.i32()


def _node(nif, r, t):
    b = {}
    _av_object(nif, r, b)
    b['children'] = r.many('i', r.u32())
    b['effects'] = r.many('i', r.u32())
    if t == 'BSMultiBoundNode':
        b['multibound'] = r.i32()
        if nif.bsver >= 83:
            r.u32()
    elif t == 'BSOrderedNode':
        r.many('f', 4)
        r.u8()
    elif t == 'BSValueNode':
        r.i32()
        r.u8()
    elif t in ('BSBlastNode', 'BSDamageStage'):
        r.many('B', 3)                          # range: min, max, current
    elif t == 'NiBillboardNode':
        r.u16()
    elif t == 'NiSwitchNode':
        r.u16(); r.i32()
    elif t == 'NiLODNode':
        r.u16(); r.i32()
        r.i32()                                 # LOD level data
    elif t == 'BSTreeNode':
        r.many('i', r.u32())
        r.many('i', r.u32())
    return b


def _geometry(nif, r, t):
    b = {}
    _av_object(nif, r, b)
    b['data'] = r.i32()
    b['skin'] = r.i32()
    nm = r.u32()
    r.many('i', nm)                             # material names
    r.many('i', nm)                             # material extra data
    r.i32()                                     # active material
    r.u8()                                      # material needs update
    return b


def _geometry_data(nif, r, t):
    b = {}
    r.i32()                                     # group ID
    n = r.u16()
    r.u8(); r.u8()                              # keep / compress flags
    b['verts'] = r.many('f', 3 * n) if r.u8() else ()
    vflags = r.u16()
    b['normals'] = r.many('f', 3 * n) if r.u8() else ()
    if b['normals'] and vflags & 0x1000:
        r.p += 24 * n                           # tangents, bitangents
    r.many('f', 4)                              # bounding sphere
    b['colors'] = r.many('f', 4 * n) if r.u8() else ()
    nuv = vflags & 1 if nif.user >= 11 else vflags & 63
    uvs = r.many('f', 2 * n * nuv)
    b['uv'] = uvs[:2 * n]
    r.u16()                                     # consistency
    r.i32()                                     # additional data
    ntri = r.u16()
    if t == 'NiTriShapeData':
        r.u32()                                 # triangle points
        b['tris'] = r.many('H', 3 * ntri) if r.u8() else ()
        for _ in range(r.u16()):                # match groups
            r.many('H', r.u16())
    else:
        lengths = r.many('H', r.u16())
        tris = []
        if r.u8():
            for ln in lengths:
                s = r.many('H', ln)
                for k in range(ln - 2):
                    a, c, d = s[k], s[k + 1], s[k + 2]
                    if a == c or c == d or a == d:
                        continue
                    tris += (a, c, d) if k % 2 == 0 else (a, d, c)
        b['tris'] = tris
    return b


def _shader_base(nif, r, b):
    _object_net(nif, r, b)
    r.u16()                                     # flags
    b['shader_type'] = r.u32()
    b['shader_flags'] = r.u32()
    r.u32()                                     # shader flags 2
    r.f32()                                     # environment map scale


def _pplighting(nif, r, t):
    b = {}
    _shader_base(nif, r, b)
    r.u32()                                     # texture clamp mode
    b['texset'] = r.i32()
    if nif.bsver > 14:
        r.f32(); r.i32()                        # refraction strength, fire period
    if nif.bsver > 24:
        r.f32(); r.f32()                        # parallax passes, scale
    if nif.bsver > 34:
        r.many('f', 4)
    return b


def _nolighting(nif, r, t):
    b = {}
    _shader_base(nif, r, b)
    r.u32()                                     # texture clamp mode
    b['file'] = r.sized()
    if nif.bsver > 26:
        r.many('f', 4)                          # falloff
    return b


def _texset(nif, r, t):
    return {'textures': [r.sized() for _ in range(r.i32())]}


def _alpha(nif, r, t):
    b = {}
    _object_net(nif, r, b)
    b['flags'] = r.u16()
    b['threshold'] = r.u8()
    return b


def _stencil(nif, r, t):
    b = {}
    _object_net(nif, r, b)
    b['flags'] = r.u16()
    r.u32()                                     # stencil ref
    r.u32()                                     # stencil mask
    return b


_PARSERS = {t: _node for t in NODE_TYPES}
_PARSERS.update({t: _geometry for t in GEOM_TYPES})
_PARSERS.update({t: _geometry_data for t in DATA_TYPES})
_PARSERS.update({
    'BSShaderPPLightingProperty': _pplighting,
    'Lighting30ShaderProperty': _pplighting,
    'BSShaderNoLightingProperty': _nolighting,
    'BSShaderTextureSet': _texset,
    'NiAlphaProperty': _alpha,
    'NiStencilProperty': _stencil,
})


def _mul(a, b):
    return tuple(tuple(sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)) for i in range(3))


def _apply(R, v):
    return [R[i][0] * v[0] + R[i][1] * v[1] + R[i][2] * v[2] for i in range(3)]


def _det(R):
    return (R[0][0] * (R[1][1] * R[2][2] - R[1][2] * R[2][1]) - R[0][1] * (R[1][0] * R[2][2] - R[1][2] * R[2][0])
            + R[0][2] * (R[1][0] * R[2][1] - R[1][1] * R[2][0]))


def _looks(nif, props):
    """(base texture path, alpha blend, alpha test, double sided) from a shape's properties."""
    tex, blend, test, double = '', False, False, False
    for pi in props:
        p = nif.block(pi)
        if not p:
            continue
        t = p['type']
        if t in ('BSShaderPPLightingProperty', 'Lighting30ShaderProperty'):
            ts = nif.block(p['texset'])
            if ts and ts['textures']:
                tex = ts['textures'][0]
        elif t == 'BSShaderNoLightingProperty' and p['file']:
            tex = p['file']
        elif t == 'NiAlphaProperty':
            blend, test = bool(p['flags'] & 1), bool(p['flags'] & 0x200)
        elif t == 'NiStencilProperty':
            double = (p['flags'] >> 10) & 3 == 3     # draw mode: both
    return tex.replace('/', '\\'), blend, test, double


def mesh_from_nif(data, max_verts=200000):
    """Triangles of a model in its own coordinates, with texture names, for the 3D view. The same shape as
    Morrowind Workshop's: [{'p', 'uv', 'i', 'tex', 'alpha', 'double'}] with positions in game units."""
    nif = Nif(data)
    shapes = []
    total = [0]
    seen = set()
    I3 = ((1, 0, 0), (0, 1, 0), (0, 0, 1))

    def visit(i, R, t, s):
        if i in seen or total[0] > max_verts:
            return
        seen.add(i)
        b = nif.block(i)
        if not b or b['flags'] & APP_CULLED:
            return
        lR, lt, ls = b['R'], b['t'], b['s']
        nR = _mul(R, lR)
        nt = [t[k] + s * v for k, v in enumerate(_apply(R, lt))]
        ns = s * ls
        if 'children' in b:
            for c in b['children']:
                visit(c, nR, nt, ns)
            return
        if b['skin'] >= 0 and 'data' in b:
            pass                                # skinned: drawn in bind pose, good enough for a preview
        d = nif.block(b['data'])
        if not d or not d['verts'] or not d['tris']:
            return
        v = d['verts']
        pos = []
        for k in range(0, len(v), 3):
            w = _apply(nR, v[k:k + 3])
            pos += [round(nt[a] + ns * w[a], 3) for a in range(3)]
        idx = list(d['tris'])
        if _det(nR) < 0:
            idx = [x for k in range(0, len(idx) - 2, 3) for x in (idx[k], idx[k + 2], idx[k + 1])]
        tex, blend, test, double = _looks(nif, b['props'])
        shapes.append({'p': pos, 'uv': [round(u, 4) for u in d['uv']], 'i': idx, 'tex': tex,
                       'alpha': 'blend' if blend else 'test' if test else '', 'double': double})
        total[0] += len(v) // 3

    if nif.blocks:
        visit(0, I3, [0.0, 0.0, 0.0], 1.0)
    return shapes


if __name__ == '__main__':
    import collections
    import sys
    import gamedata
    gd = gamedata.GameData(plugins=['FalloutNV.esm'])
    for path in sys.argv[1:]:
        data = gd.read_file(path)
        nif = Nif(data)
        print(path, 'user', nif.user, 'bsver', nif.bsver, collections.Counter(nif.types).most_common(8))
        for s in mesh_from_nif(data):
            print('  %5d verts %5d tris  %-6s %s' % (len(s['p']) // 3, len(s['i']) // 3, s['alpha'], s['tex']))
