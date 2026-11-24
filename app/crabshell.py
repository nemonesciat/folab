"""The coconut crab made a crab (the user, 23 Nov 2026: "give the crab a proper shell and remove the tail"): on the game's
radscorpion, whose skeleton, moves and ragdoll stay (islandbeasts.py paints it).

  the tail      its six narrow segments, the wide one behind the body and the pelvis's rear (bones Bip01 Tail, Tail1-Tail6,
                Bip01 Pelvis past RUMP_END: the user erased that hind section and the rump, 23 Nov 2026) left out of the body: each triangle with a corner those
                bones carry most is drawn as three of one corner and taken out of its skin partition (outfitjoin's way,
                as the shirt and shorts); the body ends at its pelvis, under the shell's back edge
  the cap       closes the stump, under the shell's back edge, which comes down round over it (BACK_DROP): a low dome over the hole's rim, skinned wholly to Bip01 Pelvis (nifmake.build_bound)
  the shell     a coconut crab's carapace over the front body, skinned wholly to Bip01 Spine: an oval dome a little wider
                than the body, its middle raised, a lip turned down at the edge, never under the body's own top
                (`shell_shapes` lifts it clear of every corner Bip01 Spine carries), its own picture (`shell_picture`)

The radscorpion's sting attack still plays with its tail out of sight: the crab lunges with nothing striking; its claws'
attacks are its own. Body files: islandbeasts' body (tail out), the shell and the cap, all in the crab's NIFZ.

    body(gd)                 the radscorpion body with the tail out (bytes)
    shell_shapes(gd, mod)    the carapace in the body's space; cap_shapes(gd, mod) the stump's cap
    files(gd, slug)          {path under Data: bytes}: shell, cap and their pictures
"""
import math

BODY_GAME = 'meshes\\creatures\\radscorpion\\radscorpion.nif'
TAIL_GONE = ('Bip01 Tail', 'Bip01 Tail1', 'Bip01 Tail2', 'Bip01 Tail3', 'Bip01 Tail4', 'Bip01 Tail5', 'Bip01 Tail6')
TAIL_KEPT = 'Bip01 Pelvis'      # (the stump's bone: the cap rides it)
RUMP_END = 28.0            # (the user: "remove the rest of that rump": the pelvis's corners past this (raw y) go too)
BACK_DROP = 20.0           # (the shell's rim comes this much lower at the back: rounded down over where the rump was)
SHELL_BONE = 'Bip01 Spine'
SHELL = 'meshes\\creatures\\radscorpion\\folab%s_crabshell.nif'
CAP = 'meshes\\creatures\\radscorpion\\folab%s_crabcap.nif'
TEX = 'textures\\folab\\%s\\beasts\\%s.dds'

# The carapace (the radscorpion's bind pose: claws to -y, the body's top ~z 74): an oval over x +-HALF_X, y FRONT..BACK,
# its edge at EDGE_Z, its top RISE over the edge, a lip LIP down at the rim, CLEAR over the body wherever it lies.
HALF_X, FRONT, BACK = 47.0, -70.0, 56.0
EDGE_Z, RISE, LIP, CLEAR, THICK = 38.0, 37.0, 7.0, 2.5, 2.0
RINGS, AROUND = 14, 48


def tail_out(data):
    """The body's bytes with every triangle the six tail segments carry left out (drawn as nothing, out of its skin
    partition). Returns (bytes, triangles left, boundary edges round the hole [(a, b)] as corner numbers)."""
    import struct
    import nif
    import outfitjoin
    import creaturepaint as cp
    sk = cp.skin_of(data)
    who = cp.main_bone(sk)
    gone_bones = {j for j, nm in enumerate(sk['names']) if nm in TAIL_GONE}
    kept_tail = sk['names'].index(TAIL_KEPT) if TAIL_KEPT in sk['names'] else -1
    V = sk['verts']
    gone_v = {v for v, j in enumerate(who) if j in gone_bones or (j == kept_tail and V[3 * v + 1] > RUMP_END)}
    n = nif.Nif(data)
    buf = bytearray(data)
    parts = {}
    left = outfitjoin._hide(buf, n, sk['shape'], None, parts, drop=lambda t: any(c in gone_v for c in t))
    blocks = [parts.get(i) or bytes(buf[n.offsets[i]:n.offsets[i] + n.sizes[i]]) for i in range(len(n.types))]
    out = outfitjoin.compact(outfitjoin._write(n, list(n.types), blocks, list(n.strings)))
    # the hole's rim: edges of kept triangles that a dropped triangle also had
    tris = n.block(n.block(sk['shape'])['data'])['tris']
    count = {}
    kept_edges = set()
    for k in range(0, len(tris), 3):
        t = tris[k:k + 3]
        dropped = any(c in gone_v for c in t)
        for a, b in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])):
            e = (min(a, b), max(a, b))
            if dropped:
                count[e] = count.get(e, 0) + 1
            else:
                kept_edges.add(e)
    rim = [e for e in kept_edges if e in count]
    return out, left, rim


def body(gd):
    return tail_out(gd.read_file(BODY_GAME))[0]


def _points(gd):
    """(every corner (n, 3), [main bone name per corner]) of the body at rest."""
    import numpy as np
    import creaturepaint as cp
    sk = cp.skin_of(gd.read_file(BODY_GAME))
    who = cp.main_bone(sk)
    P = np.array(sk['verts'], np.float64).reshape(-1, 3)
    return P, [sk['names'][j] if j >= 0 else '' for j in who], sk


def shell_shapes(gd, mod='test'):
    """The carapace as nifmake shapes in the body's space: the dome's top (rings from the middle out), a lip turned down,
    an underside a little inside it (so it is solid from below and at the rim)."""
    import numpy as np
    P, names, _sk = _points(gd)
    body_pts = P[[i for i, nm in enumerate(names) if nm in (SHELL_BONE, 'Bip01 Pelvis', 'Bip01 SpineL', 'Bip01 SpineR', 'Bip01 L Clavicle', 'Bip01 R Clavicle')]]
    cy = (FRONT + BACK) / 2
    hy = (BACK - FRONT) / 2

    def top_of(x, y):
        """The body's highest corner near (x, y), or None."""
        m = (np.abs(body_pts[:, 0] - x) < 6) & (np.abs(body_pts[:, 1] - y) < 6)
        return float(body_pts[m, 2].max()) if m.any() else None

    def dome(r):
        return EDGE_Z + RISE * math.sqrt(max(0.0, 1 - r * r)) ** 0.8

    rows = []
    for i in range(RINGS + 1):
        r = i / RINGS
        ring = []
        for k in range(AROUND):
            a = math.tau * k / AROUND
            x, y = HALF_X * r * math.cos(a), cy + hy * r * math.sin(a)
            z = dome(r) - (2.5 * math.cos(2 * a) * r * r)           # (a little flatter across, longer fore and aft)
            z -= BACK_DROP * r ** 3 * max(0.0, math.sin(a)) ** 2       # (rounded down at the back, a crab's)
            t = top_of(x, y)
            if t is not None:
                z = max(z, t + CLEAR)
            ring.append((x, y, z))
        rows.append(ring)
    # (smooth the lift a ring each way, so no bump shows where the body pushed it up)
    rows = [[tuple(np.mean([rows[max(0, i - 1)][k], rows[i][k], rows[min(RINGS, i + 1)][k]], axis=0)) if 0 < i < RINGS else rows[i][k]
             for k in range(AROUND)] for i in range(RINGS + 1)]
    P2, UV, I = [], [], []

    def add(x, y, z, u, v):
        P2.append((x, y, z))
        UV.append((u, v))
        return len(P2) - 1

    top = [[add(x, y, z, 0.5 + x / (2 * HALF_X) * 0.96, 0.5 + (y - cy) / (2 * hy) * 0.96) for (x, y, z) in ring] for ring in rows]
    # (the middle as one corner)
    mid = add(0.0, cy, rows[0][0][2], 0.5, 0.5)
    for k in range(AROUND):
        I += [mid, top[1][k], top[1][(k + 1) % AROUND]]
    for i in range(1, RINGS):
        for k in range(AROUND):
            a, b = top[i][k], top[i][(k + 1) % AROUND]
            c, d = top[i + 1][k], top[i + 1][(k + 1) % AROUND]
            I += [a, c, d, a, d, b]
    # the lip: down from the rim
    lip = [add(x * 1.02, cy + (y - cy) * 1.02, z - LIP, 0.5 + x / (2 * HALF_X) * 0.99, 0.5 + (y - cy) / (2 * hy) * 0.99) for (x, y, z) in rows[RINGS]]
    for k in range(AROUND):
        a, b = top[RINGS][k], top[RINGS][(k + 1) % AROUND]
        c, d = lip[k], lip[(k + 1) % AROUND]
        I += [a, c, d, a, d, b]
    # the underside: back in from the lip's foot to under the rim, so the edge has a thickness
    under = [add(x * 0.94, cy + (y - cy) * 0.94, z - LIP + THICK, 0.5 + x / (2 * HALF_X) * 0.9, 0.5 + (y - cy) / (2 * hy) * 0.9) for (x, y, z) in rows[RINGS]]
    for k in range(AROUND):
        a, b = lip[k], lip[(k + 1) % AROUND]
        c, d = under[k], under[(k + 1) % AROUND]
        I += [a, c, d, a, d, b]
    return [_shape(P2, UV, I, TEX % (mod, 'crab_shell'))]


def _shape(P, UV, I, tex):
    """A nifmake shape with normals worked out from its triangles (outward, as they're wound)."""
    import numpy as np
    A = np.array(P, np.float64)
    T = np.array(I).reshape(-1, 3)
    fn = np.cross(A[T[:, 1]] - A[T[:, 0]], A[T[:, 2]] - A[T[:, 0]])
    N = np.zeros_like(A)
    for k in range(3):
        np.add.at(N, T[:, k], fn)
    N /= np.maximum(np.linalg.norm(N, axis=1), 1e-9)[:, None]
    return {'p': [round(float(v), 4) for v in A.ravel()], 'n': [round(float(v), 4) for v in N.ravel()],
            'uv': [round(float(v), 4) for uv in UV for v in uv], 'i': [int(v) for v in T.ravel()],
            'tex': tex, 'normal': tex[:-4] + '_n.dds', 'gloss': 30}


def cap_shapes(gd, mod='test'):
    """The stump's cap: a low dome over the hole's rim (a fan from a middle pushed out of the hole, the rim grown a little
    so the segment's bend never opens a crack)."""
    import numpy as np
    data = gd.read_file(BODY_GAME)
    _out, _left, rim = tail_out(data)
    P, _names, _sk = _points(gd)
    loop = sorted({v for e in rim for v in e})
    R = P[loop]
    mid = R.mean(axis=0)
    # (the way out of the hole: from the body's rear segment through the rim's middle)
    seg = P[[i for i, nm in enumerate(_names) if nm == TAIL_KEPT]].mean(axis=0)
    out = mid - seg
    out /= np.linalg.norm(out) or 1
    # (round the rim in order about its middle)
    u = np.cross(out, [0, 0, 1.0])
    if np.linalg.norm(u) < 1e-6:
        u = np.cross(out, [1.0, 0, 0])
    u /= np.linalg.norm(u)
    w = np.cross(out, u)
    ang = np.arctan2((R - mid) @ w, (R - mid) @ u)
    order = np.argsort(ang)
    ring = mid + (R[order] - mid) * 1.12 + out * 0.5
    span = float(np.linalg.norm(R - mid, axis=1).mean())
    top = mid + out * 0.45 * span
    pts = [tuple(top)] + [tuple(q) for q in ring]
    m = len(ring)
    I = []
    for k in range(m):
        I += [0, 1 + k, 1 + (k + 1) % m]
    # (wound to face out of the hole)
    A = np.array(pts)
    fn = np.cross(A[I[1]] - A[I[0]], A[I[2]] - A[I[0]])
    if fn @ out < 0:
        I = [I[k + j] for k in range(0, len(I), 3) for j in (0, 2, 1)]
    UV = [(0.5, 0.5)] + [(0.5 + 0.45 * math.cos(a), 0.5 + 0.45 * math.sin(a)) for a in np.sort(ang)]
    return [_shape(pts, UV, I, TEX % (mod, 'crab_shell'))], len(loop)


def shell_picture(size=512, seed=81):
    """The carapace (PIL RGB): a coconut crab's, violet-blue mottled with rust, darker grooves (the gastric H and the
    branchial lines), pale fine spots, a rust rim."""
    import numpy as np
    from PIL import Image
    import creaturepaint as cp
    import islandbeasts as IB
    u = (np.arange(size)[None, :] + 0.5) / size * 2 - 1
    v = (np.arange(size)[:, None] + 0.5) / size * 2 - 1
    u, v = u + 0 * v, v + 0 * u
    r = np.hypot(u / 0.96, v / 0.96)
    blot = cp.noise((size, size), size / 10, seed)[..., None]
    col = np.array(IB.CR_SHELL, np.float32) * (1 - 0.5 * blot) + np.array(IB.CR_RUST, np.float32) * 0.5 * blot
    grain = cp.noise((size, size), 4, seed + 1)[..., None]
    col *= 0.88 + 0.24 * grain
    # grooves: faint, wavering (a crab's gastric H and branchial lines, not drawn letters)
    wob = (cp.noise((size, size), size / 16, seed + 4) - 0.5) * 0.06
    groove = (np.abs(np.abs(u + wob) - 0.17) < 0.012) & (np.abs(v + 0.05) < 0.3)
    groove |= (np.abs(v + 0.05 + wob) < 0.011) & (np.abs(u) < 0.17)
    for sd in (1, -1):
        groove |= (np.abs(np.hypot(u - sd * 0.8, v + 0.1) - 0.5 + wob) < 0.01) & (np.abs(v) < 0.45)
    col[groove] *= 0.84
    spots = cp.noise((size, size), 3, seed + 2) > 0.8
    col[spots] = col[spots] * 0.6 + np.array(IB.CR_JOINT, np.float32) * 0.4
    rim = r > 0.88
    col[rim] = col[rim] * 0.5 + np.array(IB.CR_RUST, np.float32) * 0.5
    return Image.fromarray(np.clip(col, 0, 255).astype(np.uint8), 'RGB')


def shell_normal(size=512, seed=81):
    """Its normal map (PIL RGBA, alpha the shine): the grooves pressed in, a little pitting."""
    import numpy as np
    from PIL import Image
    import creaturepaint as cp
    pic = np.asarray(shell_picture(size, seed).convert('L')).astype(np.float32) / 255.0
    h = pic * 0.6 + cp.noise((size, size), 2, seed + 3) * 0.4
    gy, gx = np.gradient(h)
    nx, ny = -gx * 6, -gy * 6
    nz = np.ones_like(nx)
    ln = np.sqrt(nx * nx + ny * ny + nz * nz)
    rgb = np.stack([(nx / ln + 1) * 127.5, (ny / ln + 1) * 127.5, (nz / ln + 1) * 127.5], axis=-1)
    a = np.full((size, size, 1), 110.0)
    return Image.fromarray(np.clip(np.concatenate([rgb, a], axis=-1), 0, 255).astype(np.uint8), 'RGBA')


def files(gd, slug):
    """{path under Data: bytes}: the shell and the cap (each skinned wholly to its bone), their picture and normal map."""
    import nifmake
    import creaturepaint as cp
    data = gd.read_file(BODY_GAME)
    R, T, part = cp.bone_bind(data, SHELL_BONE)
    out = {SHELL % slug: nifmake.build_bound('FOLabCrabShell', shell_shapes(gd, slug), SHELL_BONE, R, T, part)}
    R, T, part = cp.bone_bind(data, TAIL_KEPT)
    caps, _n = cap_shapes(gd, slug)
    out[CAP % slug] = nifmake.build_bound('FOLabCrabCap', caps, TAIL_KEPT, R, T, part)
    pic = TEX % (slug, 'crab_shell')
    out[pic] = cp.dds_of(shell_picture())
    nm = shell_normal()
    import numpy as np
    out[pic[:-4] + '_n.dds'] = cp.dds_of(nm.convert('RGB'), alpha_from=np.asarray(nm).astype(np.float32))
    return out
