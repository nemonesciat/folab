"""Repainting one of the game's creatures as another (the Vespid's way, vespid.py, made general for Waikiki's island animals,
sharklurk.py and islandbeasts.py): the game's body file is copied with its pictures changed (nifwrite), the creature's
skeleton, moves and ragdoll kept, so it moves exactly as the game's does.

A new picture is painted texel by texel over the game's own: `texel_map` draws every triangle of the body that uses the
picture into it with its corners' bind-pose places and the triangle's facing, so each texel knows where it lies on the body
and which way it looks; a painter names the part and colour from that (`Paint.put`), and `Paint.picture` keeps the game's
own light and shade (each texel's brightness over its part's middle), so folds, scales and muscle still read.

    texel_map(gd, body, picture)   (place (n, n, 3), facing (n, n, 3), covered (n, n))
    game_picture(gd, path, size)   the game's picture as float RGBA (size, size, 4)
    Paint(gd, body, picture)       .part / .colour arrays to fill, .picture() -> PIL RGB

Needs numpy and PIL: a build step, as the Vespid's (DEV_ONLY in packaging).
"""
import math


def size_of(gd, path):
    """(width, height) of a picture the game has."""
    import struct
    d = gd.read_file(path)
    h, w = struct.unpack_from('<II', d, 12)
    return w, h


def game_picture(gd, path, size=None):
    """The picture as float32 RGBA (h, w, 4), at `size` (its own when None)."""
    import numpy as np
    import dds
    size = size or size_of(gd, path)[0]
    w, h, px = dds.decode(gd.read_file(path), want=size)[:3]
    if (w, h) != (size, size):
        raise ValueError('%s came as %dx%d, not %d' % (path, w, h, size))
    return np.frombuffer(bytes(px), np.uint8).reshape(h, w, 4).astype(np.float32)


def shapes_on(gd, body, picture, which=None):
    """The body's shapes drawn with `picture` (any case), bind pose (which: only these of them, by order)."""
    import nif
    want = picture.lower()
    got = [s for s in nif.mesh_from_nif(gd.read_file(body), placed=False) if (s.get('tex') or '').lower() == want]
    return [got[k] for k in which] if which is not None else got


def texel_map(gd, body, picture, size=None, which=None):
    """(place (size, size, 3), facing (size, size, 3), covered (size, size) bool) for each texel of `picture` from the
    triangles of `body` that use it (the first triangle to cover a texel wins; a pixel's slack round each, the edge texels
    the game filters into)."""
    import numpy as np
    size = size or size_of(gd, picture)[0]
    pos = np.zeros((size, size, 3), np.float32)
    face = np.zeros((size, size, 3), np.float32)
    have = np.zeros((size, size), bool)
    for s in shapes_on(gd, body, picture, which):
        P = np.array(s['p'], np.float64).reshape(-1, 3)
        UV = np.array(s['uv'], np.float64).reshape(-1, 2) % 1.0 * size
        I = np.array(s['i']).reshape(-1, 3)
        N = np.cross(P[I[:, 1]] - P[I[:, 0]], P[I[:, 2]] - P[I[:, 0]])
        N /= np.maximum(np.linalg.norm(N, axis=1), 1e-9)[:, None]
        for (a, b, c), nrm in zip(I, N):
            xs, ys = UV[[a, b, c], 0], UV[[a, b, c], 1]
            x0, x1 = int(max(0, math.floor(xs.min()) - 1)), int(min(size - 1, math.ceil(xs.max()) + 1))
            y0, y1 = int(max(0, math.floor(ys.min()) - 1)), int(min(size - 1, math.ceil(ys.max()) + 1))
            d = (ys[1] - ys[2]) * (xs[0] - xs[2]) + (xs[2] - xs[1]) * (ys[0] - ys[2])
            if abs(d) < 1e-9:
                continue
            gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
            w0 = ((ys[1] - ys[2]) * (gx - xs[2]) + (xs[2] - xs[1]) * (gy - ys[2])) / d
            w1 = ((ys[2] - ys[0]) * (gx - xs[2]) + (xs[0] - xs[2]) * (gy - ys[2])) / d
            w2 = 1 - w0 - w1
            slack = -0.6 / max(1.0, abs(d) ** 0.5)
            m = (w0 >= slack) & (w1 >= slack) & (w2 >= slack)
            if not m.any():
                continue
            q = w0[..., None] * P[a] + w1[..., None] * P[b] + w2[..., None] * P[c]
            sub, sf, sh = pos[y0:y1 + 1, x0:x1 + 1], face[y0:y1 + 1, x0:x1 + 1], have[y0:y1 + 1, x0:x1 + 1]
            fresh = m & ~sh
            sub[fresh] = q[fresh]
            sf[fresh] = nrm
            sh[fresh] = True
    return pos, face, have


def noise(shape, scale, seed):
    """Smooth value noise in 0..1 over a picture's grid (`scale` texels a cell)."""
    import numpy as np
    rng = np.random.default_rng(seed)
    h, w = shape
    gh, gw = int(h / scale) + 2, int(w / scale) + 2
    g = rng.random((gh, gw)).astype(np.float32)
    y = np.arange(h, dtype=np.float32) / scale
    x = np.arange(w, dtype=np.float32) / scale
    y0, x0 = y.astype(int), x.astype(int)
    fy, fx = (y - y0)[:, None], (x - x0)[None, :]
    fy, fx = fy * fy * (3 - 2 * fy), fx * fx * (3 - 2 * fx)
    a = g[y0][:, x0]
    b = g[y0][:, x0 + 1]
    c = g[y0 + 1][:, x0]
    d = g[y0 + 1][:, x0 + 1]
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


def space_noise(p, scale, seed):
    """Smooth noise 0..1 over the body's own space (so a pattern runs on across the picture's seams)."""
    import numpy as np
    rng = np.random.default_rng(seed)
    k = rng.normal(size=(6, 3)).astype(np.float32)
    ph = rng.random(6).astype(np.float32) * 6.283
    q = p / scale
    v = sum(np.sin(q @ k[i] + ph[i]) for i in range(6)) / 6.0
    return np.clip(0.5 + 0.9 * v, 0, 1)


class Paint:
    """A picture being painted over the game's: fill `part` (names) and `colour` (RGB 0-255) where `have`."""

    def __init__(self, gd, body, picture, size=None, tm=None):
        import numpy as np
        self.size = size or size_of(gd, picture)[0]
        self.game = game_picture(gd, picture, self.size)
        self.pos, self.face, self.have = tm or texel_map(gd, body, picture, self.size)
        self.lum = self.game[..., :3].mean(axis=2)
        self.part = np.full(self.have.shape, '', dtype=object)
        self.colour = np.zeros(self.have.shape + (3,), np.float32)

    def put(self, mask, colour):
        import numpy as np
        if isinstance(colour, (tuple, list)):
            colour = np.array(colour, np.float32)
        self.colour[mask] = colour if colour.ndim == 1 else colour[mask]

    def mix(self, mask, colour, amount):
        """Blend `colour` in by `amount` (0..1 array or number) where mask."""
        import numpy as np
        a = amount if np.isscalar(amount) else amount[mask][:, None]
        c = np.array(colour, np.float32)
        self.colour[mask] = self.colour[mask] * (1 - a) + c * a

    def picture(self, keep=0.75, floor=0.45, top=1.7, sheen=0.0, bleed=5, keep_of=None):
        """PIL RGB: each covered texel its colour times the game's own brightness there over its part's middle
        (`keep` how much of that shade, `keep_of` by part), the rest of the sheet as the game's; colours bled `bleed` past each island."""
        import numpy as np
        from PIL import Image, ImageFilter
        out = self.game[..., :3].copy()
        names = set(self.part[self.have].tolist())
        for name in names:
            m = self.have & (self.part == name)
            mid = max(8.0, float(np.median(self.lum[m])))
            shade = np.clip(self.lum / mid, floor, top) ** (keep_of or {}).get(name, keep)
            out[m] = self.colour[m] * shade[m][:, None]
        if sheen:
            dark = self.have & (self.colour.sum(axis=-1) < 200)
            out[dark] += sheen * self.game[..., :3][dark]
        img = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), 'RGB')
        if not bleed:
            return img
        grown = img.filter(ImageFilter.MaxFilter(bleed))
        m = Image.fromarray((self.have * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(3))
        return Image.composite(img, grown, m)


def dds_of(img, alpha_from=None, cut=None):
    """A PIL picture as the game's DDS: DXT1 when no alpha, else DXT5 with the alpha of `alpha_from` (float RGBA array)."""
    import numpy as np
    import dds
    from PIL import Image
    if alpha_from is not None:
        rgb = np.asarray(img.convert('RGB')).astype(np.uint8)
        a = np.clip(alpha_from[..., 3], 0, 255).astype(np.uint8)[..., None]
        img = Image.fromarray(np.concatenate([rgb, a], axis=2), 'RGBA')
        return dds.compress(dds.encode(img.size[0], img.size[1], img.tobytes(), cut=cut))
    rgba = img.convert('RGBA').tobytes()
    return dds.compress(dds.encode(img.size[0], img.size[1], rgba))


# ---------- bones ----------

def skin_of(data, shape=None):
    """{'shape': block, 'names': [bone names], 'binds': [(R, T, scale)], 'weights': [[(vertex, weight)]], 'parts':
    [(flags, body part)], 'verts'} of a body's skinned shape (`shape` its block, else the one with the most corners): how
    its own skin data binds each bone (body to bone: v_bone = R v + T)."""
    import struct
    import nif
    n = nif.Nif(data)
    best = None
    for i, t in enumerate(n.types):
        if t not in ('NiTriShape', 'NiTriStrips') or (shape is not None and i != shape):
            continue
        b = n.block(i)
        if b['skin'] < 0:
            continue
        o = n.offsets[b['skin']]
        sd, _part, _root, nb = struct.unpack_from('<iiiI', data, o)
        bones = struct.unpack_from('<%di' % nb, data, o + 16)
        npart = struct.unpack_from('<I', data, o + 16 + 4 * nb)[0]
        parts = [struct.unpack_from('<HH', data, o + 20 + 4 * nb + 4 * k) for k in range(npart)]
        d = n.offsets[sd] + 13 * 4
        nbs, has_w = struct.unpack_from('<IB', data, d)
        d += 5
        binds, weights = [], []
        for _j in range(nbs):
            R = struct.unpack_from('<9f', data, d)
            T = struct.unpack_from('<3f', data, d + 36)
            s = struct.unpack_from('<f', data, d + 48)[0]
            nv = struct.unpack_from('<H', data, d + 68)[0]
            binds.append(((R[0:3], R[3:6], R[6:9]), T, s))
            weights.append([struct.unpack_from('<Hf', data, d + 70 + 6 * k) for k in range(nv)] if has_w else [])
            d += 70 + (6 * nv if has_w else 0)
        verts = n.block(b['data'])['verts']
        got = {'shape': i, 'names': [n.block(q)['name'] for q in bones], 'binds': binds, 'weights': weights,
               'parts': parts, 'verts': verts}
        if best is None or len(verts) > len(best['verts']):
            best = got
    if best is None:
        raise ValueError('no skinned shape')
    return best


def bone_bind(data, bone):
    """(R, T, torso partition) of `bone` as the body's biggest skinned shape binds it."""
    sk = skin_of(data)
    if bone not in sk['names']:
        raise ValueError('the body binds no %s' % bone)
    R, T, s = sk['binds'][sk['names'].index(bone)]
    if abs(s - 1) > 1e-3:
        raise ValueError('%s bound at scale %s' % (bone, s))
    torso = next((p for p in sk['parts'] if p[1] == 0), sk['parts'][0])
    return R, T, torso


def main_bone(sk):
    """[bone index carrying the most of each corner]."""
    who = [-1] * (len(sk['verts']) // 3)
    best = [0.0] * len(who)
    for j, ws in enumerate(sk['weights']):
        for v, w in ws:
            if w > best[v]:
                best[v], who[v] = w, j
    return who


# ---------- the space the bones work in ----------
# A skinned shape keeps a place of its own under the root (the lakelurk's sits at -13.83, +30.37; the radscorpion's is
# turned half round) and its skin data's overall transform undoes it: the game puts every corner by its bones from the
# raw numbers alone (v_bone = R v_raw + T). Our pictures (nif.mesh_from_nif, texel_map) see the body placed; parts we add
# (a fin, a shell) are bound by the same R, T, so they must be built in the raw space: `to_skin` takes points there.

def place_of(data):
    """(R (3x3), t, s) of the body's biggest skinned shape under its root: placed = R raw * s + t."""
    import numpy as np
    import nif
    sk = skin_of(data)
    b = nif.Nif(data).block(sk['shape'])
    return np.array(b['R'], np.float64), np.array(b['t'], np.float64), float(b['s'])


def to_skin(data, P, normals=False):
    """Points (n, 3) as the pictures see the body -> the raw space its bones bind (normals: turn only)."""
    import numpy as np
    R, t, s = place_of(data)
    P = np.asarray(P, np.float64).reshape(-1, 3)
    return P @ R if normals else ((P - t) @ R) / s


def from_skin(data, P, normals=False):
    """Raw points (n, 3) -> as the pictures see the body."""
    import numpy as np
    R, t, s = place_of(data)
    P = np.asarray(P, np.float64).reshape(-1, 3)
    return P @ R.T if normals else P @ R.T * s + t


def skin_shapes(shapes, data):
    """nifmake shapes built as the pictures see the body, moved into its bones' raw space."""
    out = []
    for sh in shapes:
        sh = dict(sh)
        sh['p'] = [round(float(v), 4) for v in to_skin(data, sh['p']).ravel()]
        if sh.get('n'):
            sh['n'] = [round(float(v), 4) for v in to_skin(data, sh['n'], normals=True).ravel()]
        out.append(sh)
    return out


def _verts_at(d, o):
    """(where the corners start, where the normals start or None, corner count, vertex flags) in an NiTriShapeData."""
    import struct
    p = o + 4
    n = struct.unpack_from('<H', d, p)[0]
    p += 4
    has = d[p]
    p += 1
    va = p if has else None
    if has:
        p += 12 * n
    vflags = struct.unpack_from('<H', d, p)[0]
    p += 2
    hasn = d[p]
    p += 1
    return va, (p if hasn else None), n, vflags


def morph(data, move):
    """The body with its corners moved (`move`: placed points (n, 3) -> their new places), in every skinned shape; the
    normals of moved corners worked out again from their triangles (the rest kept as made). Skin weights, partitions and
    triangles are untouched, so each corner rides the same bones."""
    import struct
    import numpy as np
    import nif
    n = nif.Nif(data)
    buf = bytearray(data)
    R, t, s = place_of(data)
    moved_total = 0
    for i, typ in enumerate(n.types):
        if typ != 'NiTriShape':
            continue
        b = n.block(i)
        if b['skin'] < 0:
            continue
        bd = n.block(b['data'])
        o = n.offsets[b['data']]
        va, na, cnt, _vf = _verts_at(data, o)
        if va is None:
            continue
        raw = np.array(bd['verts'], np.float64).reshape(-1, 3)
        Rs, ts, ss = np.array(b['R'], np.float64), np.array(b['t'], np.float64), float(b['s'])
        placed = raw @ Rs.T * ss + ts
        new = np.asarray(move(placed), np.float64)
        d = np.linalg.norm(new - placed, axis=1)
        hit = d > 1e-3
        if not hit.any():
            continue
        moved_total += int(hit.sum())
        nraw = ((new - ts) @ Rs) / ss
        struct.pack_into('<%df' % (3 * cnt), buf, va, *nraw.ravel().tolist())
        if na is not None and bd['tris']:
            T = np.array(bd['tris']).reshape(-1, 3)
            fn = np.cross(nraw[T[:, 1]] - nraw[T[:, 0]], nraw[T[:, 2]] - nraw[T[:, 0]])
            N = np.zeros_like(nraw)
            for k in range(3):
                np.add.at(N, T[:, k], fn)
            N /= np.maximum(np.linalg.norm(N, axis=1), 1e-9)[:, None]
            old = np.array(bd['normals'], np.float64).reshape(-1, 3)
            # (keep the made normal's side: soup winding isn't trusted)
            N *= np.where((N * old).sum(axis=1) < 0, -1.0, 1.0)[:, None]
            out = np.where(hit[:, None], N, old)
            struct.pack_into('<%df' % (3 * cnt), buf, na, *out.ravel().tolist())
    return bytes(buf), moved_total
