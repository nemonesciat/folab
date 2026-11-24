"""Waikiki's Sharklurk (the user, 23 Nov 2026; docs/waikiki-pacing-plan.md section 6, the south shore's danger): the game's
lakelurk (it swims and walks: it comes out of the surf after you), repainted as a shark and given a dorsal fin.

  skeleton   creatures\\MirelurkKing\\Skeleton.nif, its animations and ragdoll: kept (it moves as a lakelurk)
  body       lakelurk.NIF: shapes 0, 1, 6 on lakekurk.dds (1024, DXT1, + _n, + _g 512: the lakelurk's red glow of eye,
             hood stripes and spine spots), four gore caps
  fin        sharkfin.nif, a second body file in the creature's model list (NIFZ): one shape skinned wholly to
             'Bip01 Spine2' as the body binds it (`spine_bind`, read from the body's own skin data), so it rides the
             back as the spine moves, as the game's worn hats ride the head (nifmake.build_bound)

It is bite only (the user: "no beam, just bite"): the lakelurk's sonic weapon (LakelurkSonic2HL) and its ammo are not in
its inventory, its combat style is the Mirelurk King's close fighting kind (`STYLE`). It drops shark meat (an ALCH copied
from the lakelurk's meat) and sometimes a shark tooth (a MISC); `death_list` is their levelled list.

Its look (`body_picture`): a shark's countershading, slate grey over white (the line by each texel's facing: back, tops
and outsides grey; chest, belly and the insides of the limbs white), five gill slits each side of the neck, old pale
scars, the lakelurk's spines grey with worn pale tips, its eye black with a dull green shine. The lakelurk's glow is
taken out but for a faint eye shine (`glow_picture`).

    pictures(gd)              {name: PIL image}
    fin_shapes(gd)            the fin in the body's space (bind pose)
    files(gd, slug)           {path under Data: bytes}
    records(gd, slug, keys)   the CREA, meat ALCH, tooth MISC, death LVLI
"""
import json
import math

LURK = 'NVCrLakelurk'                           # (the full record the levelled lakelurks are templated on)
BODY_GAME = 'meshes\\creatures\\mirelurkking\\lakelurk.nif'
PIC = 'textures\\creatures\\lakelurks\\lakekurk.dds'
GLOW = 'textures\\creatures\\lakelurks\\lakekurk_g.dds'
NORMAL = 'textures\\creatures\\lakelurks\\lakekurk_n.dds'
BODY = 'meshes\\creatures\\mirelurkking\\folab%s_sharklurk.nif'       # (mod: beside the skeleton, as NIFZ wants)
FIN = 'meshes\\creatures\\mirelurkking\\folab%s_sharkfin.nif'
TEX = 'textures\\folab\\%s\\sharklurk\\%s.dds'                         # (mod, picture)
SONIC = ('LakelurkSonic2HL', 'AmmoLakelurk')    # (its beam: left out of the inventory)
STYLE = 'CSNVLakelurk'                          # (replaced below when the game has a close-fighting one: `_style`)
SPINE = 'Bip01 Spine2'

EDID, NAME = 'FOLabSharklurk', 'Sharklurk'
SCALE, HEALTH, LEVEL, DAMAGE = 1.05, 220, 16, 60     # (the lakelurk: 1.0, 150, 13, 55; the bite is all it has)

# shark colours
SLATE = (82, 92, 102)
SLATE_DARK = (56, 64, 74)
WHITE = (214, 216, 210)
SCAR = (176, 168, 166)
GILL = (34, 36, 42)
EYE = (12, 14, 14)
TIP = (200, 198, 188)


# ---------- the body ----------

def countershade(pos, face, seed=7):
    """0 (white underside) .. 1 (slate back) for each texel: by which way it faces (back -y, up +z, out to the sides),
    the line wavy as a real shark's."""
    import numpy as np
    import creaturepaint as cp
    x, z = pos[..., 0], pos[..., 2]
    fy, fz = face[..., 1], face[..., 2]
    fx_out = face[..., 0] * np.sign(x + 1e-6)
    limb = (np.abs(x) > 19) | (z < 64)          # (arms and legs: grey but where they face in or down)
    trunk = -0.95 * fy + 0.45 * fz + 0.25 * fx_out + 0.2
    lim = 0.35 - 1.1 * np.maximum(0, -fx_out) - 0.6 * np.maximum(0, -fz) - 0.25 * fy
    d = np.where(limb, lim, trunk)
    head = z > 118
    d = np.where(head, -0.8 * fy + 0.7 * fz + 0.3 * fx_out, d)
    wave = cp.space_noise(pos, 9.0, seed) - 0.5
    t = np.clip((d + 0.05 + 0.35 * wave) / 0.18 + 0.5, 0, 1)
    return t


def gills(pos, face):
    """Texels on the gill slits: five curved slits each side of the neck, behind the hood's lower edge."""
    import numpy as np
    x, y, z = pos[..., 0], pos[..., 1], pos[..., 2]
    side = np.abs(face[..., 0]) > 0.35
    out = np.zeros(x.shape, bool)
    for k in range(5):
        yc = 9.0 - 3.2 * k                      # (front to back)
        bend = 0.04 * (z - 115.0) ** 2
        out |= side & (np.abs(y - (yc + bend * 0.2)) < 0.55) & (z > 104) & (z < 121) & (np.abs(x) > 6) & (np.abs(x) < 16)
    return out


def scars(pos, seed=11):
    """Texels on old scars: a few pale streaks over the back and shoulders (as a shark's from other sharks' teeth)."""
    import numpy as np
    rng = np.random.default_rng(seed)
    out = np.zeros(pos.shape[:-1], bool)
    for _ in range(9):
        a = np.array([rng.uniform(-26, 26), rng.uniform(-18, -4), rng.uniform(70, 125)])
        d = rng.normal(size=3)
        d[1] *= 0.3
        d /= np.linalg.norm(d)
        b = a + d * rng.uniform(8, 18)
        ab = b - a
        t = np.clip(((pos - a) @ ab) / float(ab @ ab), 0, 1)
        q = a + t[..., None] * ab
        out |= np.linalg.norm(pos - q, axis=-1) < rng.uniform(0.35, 0.7)
    return out


def _spines(game):
    """The lakelurk's orange-tipped spines and claws (by the picture's own orange)."""
    r, g, b = game[..., 0], game[..., 1], game[..., 2]
    return (r > 90) & (r > g * 1.35) & (g > b * 1.2)


def _eye(game):
    r, g, b = game[..., 0], game[..., 1], game[..., 2]
    return (r > 120) & (r > 2.2 * g) & (r > 2.2 * b)


def body_picture(gd, paint=None):
    """The body's picture (PIL RGB)."""
    import numpy as np
    import creaturepaint as cp
    p = paint or cp.Paint(gd, BODY_GAME, PIC)
    p.teeth = teeth_texels(gd, p.size)
    t = countershade(p.pos, p.face)
    grain = cp.space_noise(p.pos, 3.5, 21)[..., None]
    slate = np.array(SLATE, np.float32) * (0.9 + 0.2 * grain)
    slate = slate * (1 - 0.35 * cp.space_noise(p.pos, 14.0, 22)[..., None]) + np.array(SLATE_DARK, np.float32) * 0.35 * cp.space_noise(p.pos, 14.0, 22)[..., None]
    white = np.array(WHITE, np.float32) * (0.96 + 0.06 * grain)
    col = white * (1 - t[..., None]) + slate * t[..., None]
    p.part[p.have] = 'skin'
    p.put(p.have, col)
    sp = p.have & _spines(p.game)
    p.part[sp] = 'spine'
    tipness = np.clip((p.game[..., 0] - 90) / 90.0, 0, 1)
    p.put(sp, np.array(SLATE, np.float32) * (1 - tipness[..., None]) + np.array(TIP, np.float32) * tipness[..., None])
    sc = p.have & scars(p.pos) & (t > 0.5)
    p.mix(sc, SCAR, 0.8)
    gl = p.have & gills(p.pos, p.face)
    p.put(gl, GILL)
    p.part[gl] = 'gill'
    eye = p.have & _eye(p.game)
    p.part[eye] = 'eye'
    p.put(eye, EYE)
    face_paint(p)
    return p.picture(keep=0.7, sheen=0.08, keep_of={'face': 0.3, 'mouth': 0.2, 'eye': 0.1}), p


# The face (bind pose): the hood's front, |x| under 10, z 118-146, facing forward (+y). Measured from the lakelurk's own
# picture: brow and eye sockets at z ~139, x +-5; nose ~135; its open lips ~126-132; chin ~120.
FACE = (10.0, 118.0, 147.0)                 # (half width, bottom, top)
EYE_AT, EYE_R = (6.2, 139.0), 1.5           # (a shark's: small, round, black, set out to the sides)
LIPS = (4.6, 131.4, 135.8)                  # (the lakelurk's own mouth, front: half width, bottom, top; its teeth in it)
GUM, GAPE, TOOTH_WHITE = (150, 96, 102), (40, 26, 30), (232, 230, 220)
# the snout (the user, 23 Nov 2026: "point the nose out a little more"): the face's own corners above the mouth moved
# forward, most on the middle line at nose height, none at the mouth or on the hood's top and sides
SNOUT, SNOUT_Z = 7.0, (134.6, 138.5, 147.0)   # (how far, at its most; from, fullest, to: heights)
SNOUT_HALF = 10.0                           # (half width: nothing moves past it)


def _face(p):
    x, z = p.pos[..., 0], p.pos[..., 2]
    import numpy as np
    return p.have & (p.face[..., 1] > 0.25) & (np.abs(x) < FACE[0]) & (z > FACE[1]) & (z < FACE[2])


SPINES_FROM = 85.0          # (the row of spikes down the middle of the back, the crown to here: out)


def back_spines(data):
    """{shape block: {triangle (sorted corners)}}: the spikes down the middle of the back from the crown to SPINES_FROM
    (each its own small patch of the picture, 18-38 triangles, on the middle line behind the body), left out (the user,
    23 Nov 2026: "get rid of the neck spines"); the shoulders' are kept."""
    import numpy as np
    import nif
    n = nif.Nif(data)
    out = {}
    for i, t in enumerate(n.types):
        if t != 'NiTriShape':
            continue
        b = n.block(i)
        if b['skin'] < 0:
            continue
        bd = n.block(b['data'])
        V = np.array(bd['verts'], np.float64).reshape(-1, 3)
        P = V @ np.array(b['R']).T * b['s'] + np.array(b['t'])
        T = np.array(bd['tris']).reshape(-1, 3)
        par = list(range(len(V)))

        def root(a):
            while par[a] != a:
                par[a] = par[par[a]]
                a = par[a]
            return a
        for a, b2, c in T:
            for x, y in ((a, b2), (b2, c)):
                ra, rb = root(x), root(y)
                if ra != rb:
                    par[ra] = rb
        patches = {}
        for k, tri in enumerate(T):
            patches.setdefault(root(int(tri[0])), []).append(k)
        for ks in patches.values():
            c = P[T[ks]].mean(axis=(0, 1))
            if len(ks) <= 60 and abs(c[0]) < 1.0 and c[1] < -4.0 and c[2] > SPINES_FROM:
                out.setdefault(i, set()).update(tuple(sorted(int(v) for v in T[k])) for k in ks)
    return out


def spines_out(data):
    """The body with `back_spines` left out (drawn as nothing, out of their skin partitions)."""
    import nif
    import outfitjoin
    gone = back_spines(data)
    n = nif.Nif(data)
    buf = bytearray(data)
    parts = {}
    for i, tris in gone.items():
        outfitjoin._hide(buf, n, i, None, parts, drop=lambda t, tris=tris: tuple(sorted(t)) in tris)
    blocks = [parts.get(i) or bytes(buf[n.offsets[i]:n.offsets[i] + n.sizes[i]]) for i in range(len(n.types))]
    return outfitjoin.compact(outfitjoin._write(n, list(n.types), blocks, list(n.strings)))


def teeth_texels(gd, size):
    """Texels of the lakelurk's teeth (its shape objTEETH, the first on the picture)."""
    import creaturepaint as cp
    return cp.texel_map(gd, BODY_GAME, PIC, size, which=[0])[2]


def snout(P):
    """Placed points (n, 3) -> with the snout pulled forward (+y)."""
    import numpy as np
    P = np.array(P, np.float64)
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    z0, zm, z1 = SNOUT_Z
    wz = np.where(z < zm, np.clip((z - z0) / (zm - z0), 0, 1), np.clip((z1 - z) / (z1 - zm), 0, 1))
    wz = wz * wz * (3 - 2 * wz)
    wx = np.clip(1 - (x / SNOUT_HALF) ** 2, 0, 1) ** 2
    wy = np.clip(y / 10.0, 0, 1)
    P[:, 1] = y + SNOUT * wz * wx * wy
    return P


def face_paint(p):
    """A great white's face over the lakelurk's (the user's pictures, 23 Nov 2026): grey down to just under the eyes, white
    below on a ragged line; small round black eyes set out to the sides with a pale glint; a wide mouth curved up at its
    corners, pink gums, a dark gape, a row of white triangular teeth along each jaw. The human brow, nose and lips are
    painted over (and flattened in the normal map, `normal_picture`), so the face reads as a snout."""
    import numpy as np
    import creaturepaint as cp
    face = _face(p)
    x, z = p.pos[..., 0], p.pos[..., 2]
    p.part[face] = 'face'
    # (grey over white: the line just under the eyes, ragged, dipping toward the mouth's corners)
    line = EYE_AT[1] - 2.8 - 0.06 * x ** 2 + 1.6 * (cp.space_noise(p.pos, 2.2, 71) - 0.5)
    grey = np.array(SLATE, np.float32) * (0.95 + 0.1 * cp.space_noise(p.pos, 1.5, 72)[..., None])
    white = np.array(WHITE, np.float32)
    p.put(face & (z >= line), grey)
    p.put(face & (z < line), white)
    # (the mouth: the lakelurk's own lips dark gum, its own teeth white; no line along the cheeks (the user: too much))
    hw, lo, hi = LIPS
    lips = face & (np.abs(x) < hw) & (z > lo) & (z < hi)
    p.put(lips, GUM)
    teeth = getattr(p, 'teeth', None)
    if teeth is not None:
        p.put(teeth, TOOTH_WHITE)
        p.part[teeth] = 'teeth'
    p.part[lips] = 'mouth'
    # (the eyes: round, black, a little glint; a ball round each eye's spot on the skin, so the paint doesn't run back
    # along the side of the head)
    y = p.pos[..., 1]
    for side in (1, -1):
        near = face & (np.hypot(x - side * EYE_AT[0], z - EYE_AT[1]) < 1.0)
        ey = float(np.median(y[near])) if near.any() else 12.0
        d = np.sqrt((x - side * EYE_AT[0]) ** 2 + (z - EYE_AT[1]) ** 2 + (y - ey) ** 2)
        eye = p.have & (d < EYE_R)
        p.put(eye, EYE)
        p.part[eye] = 'eye'
        glint = eye & (np.sqrt((x - side * (EYE_AT[0] - 0.5)) ** 2 + (z - EYE_AT[1] - 0.6) ** 2 + (y - ey) ** 2) < 0.45)
        p.put(glint, (150, 160, 165))
    # (the lakelurk's own red eye on the picture: black)
    return face


def normal_picture(gd, paint):
    """The lakelurk's normal map with the face flattened (its brow, nose and lips gone: a smooth snout); its alpha (the
    shine) kept. PIL RGB, and the RGBA array whose alpha the DDS keeps."""
    import numpy as np
    from PIL import Image, ImageFilter
    import creaturepaint as cp
    nm = cp.game_picture(gd, NORMAL, paint.size)
    face = _face(paint)
    soft = np.asarray(Image.fromarray((face * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(3))).astype(np.float32)[..., None] / 255.0
    flat = np.array([128.0, 128.0, 255.0], np.float32)
    rgb = nm[..., :3] * (1 - 0.85 * soft) + flat * 0.85 * soft
    return Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), 'RGB'), nm


def glow_picture(gd, paint):
    """The glow (PIL RGB, 512 as the lakelurk's): nothing but a faint green-gold shine in the eye."""
    import numpy as np
    from PIL import Image, ImageFilter
    eye = paint.have & (paint.part == 'eye')
    g = np.zeros(eye.shape + (3,), np.float32)
    g[eye] = (20, 34, 22)
    img = Image.fromarray(g.astype(np.uint8), 'RGB').filter(ImageFilter.GaussianBlur(1.0))
    return img.resize((512, 512), Image.LANCZOS)


# ---------- the fin ----------

def spine_bind(gd):
    """(R, T, partition (flags, body part)): how the body binds 'Bip01 Spine2' (body to bone: v_bone = R v + T), read
    from the main shape's own skin data, and its torso partition."""
    import creaturepaint as cp
    return cp.bone_bind(gd.read_file(BODY_GAME), SPINE)


def back_line(gd):
    """[(y, z)] where the body's surface crosses its middle line (x 0) on the back (y under 5): the plane cut through every
    triangle of the body."""
    import creaturepaint as cp
    out = []
    for sh in cp.shapes_on(gd, BODY_GAME, PIC):
        P = sh['p']
        I = sh['i']
        for k in range(0, len(I), 3):
            t = I[k:k + 3]
            for a, b in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])):
                xa, xb = P[3 * a], P[3 * b]
                if (xa <= 0 < xb) or (xb <= 0 < xa):
                    f = xa / (xa - xb)
                    y = P[3 * a + 1] + (P[3 * b + 1] - P[3 * a + 1]) * f
                    z = P[3 * a + 2] + (P[3 * b + 2] - P[3 * a + 2]) * f
                    if y < 5:
                        out.append((y, z))
    return out


def _back_at(gd, z0, z1=None, line=None):
    """How far back the skin reaches at its shallowest between heights z0 and z1 (z0 alone: within 2 of it): the back's
    middle line goes in and out by 6, so a fin rooted at the shallowest is inside the skin all along its base."""
    line = line if line is not None else back_line(gd)
    z1 = z0 if z1 is None else z1
    best = None
    for zz in range(int(z0), int(z1) + 1):
        ys = [y for y, z in line if abs(z - zz) < 1.0]
        if ys:
            deepest = min(ys)               # (the skin at this height)
            best = deepest if best is None else max(best, deepest)
    return best


# A shark's dorsal fin: (z from the base's top, how far out behind the back) along its leading edge, then the trailing edge
# hooked under; in the body's space at rest, the base run up the spine. Thick at the base, thin to the tip. Its base sits
# FIN_SINK inside the shallowest skin along it, its root BURIED further out than that, so no light shows under it from
# any side.
# (the user's drawing, 23 Nov 2026: the back of the head running down into it, the leading edge sweeping out and down to a
# tip that points toward the tail, a hollow trailing edge back to the body)
FIN_LEAD = ((0.0, 0.0), (-2.5, 5.0), (-5.5, 10.5), (-9.0, 15.5), (-12.5, 20.0), (-16.0, 23.5))   # (dz, out)
FIN_TRAIL = ((-17.0, 19.0), (-18.0, 13.5), (-19.5, 8.5), (-21.5, 4.5), (-24.0, 1.5), (-26.0, 0.0))
FIN_TOP, FIN_THICK = 121.0, 4.2           # (high: rooted just under the neck, as the user drew it, 23 Nov 2026)
FIN_MID = (-12.0, 6.0)      # (the faces are fans from here: every edge of the outline is seen from it)
# (a great white's: a broad triangle, its front edge nearly straight and raked back toward the tail, a pointed tip, a
# short trailing edge with a slight notch; the user: no "half a crescent moon")
FIN_SINK = 2.5
BURIED = 6.0                # (the skin goes 6 deeper in places along the base: the fin reaches out that much more)


def fin_shapes(gd, mod='test'):
    """The fin as nifmake shapes in the body's space: two faces (left, right) and a rim, its root inside the back."""
    back = _back_at(gd, FIN_TOP + min(dz for dz, _o in FIN_TRAIL), FIN_TOP)
    if back is None:
        raise ValueError('no back found under the fin')
    outline = [(dz, o + BURIED if o > 0 else o) for dz, o in list(FIN_LEAD) + list(FIN_TRAIL)]
    n = len(outline)
    zs = [FIN_TOP + dz for dz, _o in outline]
    ys = [back + FIN_SINK - o for _dz, o in outline]
    # thickness: flared at the root, 0.18 of it at the tip
    reach = max(o for _dz, o in outline)
    half = [FIN_THICK / 2 * (1.5 if o <= 0 else (1 - 0.82 * (o / reach))) for _dz, o in outline]
    # the fans' middle
    cz, cy = FIN_TOP + FIN_MID[0], back + FIN_SINK - FIN_MID[1] - BURIED
    P, N, UV, I = [], [], [], []
    zmin, zmax, ymin, ymax = min(zs), max(zs), min(ys), max(ys)

    def uv(z, y):
        return ((ymax - y) / (ymax - ymin), (zmax - z) / (zmax - zmin))
    for side in (1, -1):
        base = len(P) // 3
        P += [side * FIN_THICK / 2 * 0.6, cy, cz]
        N += [side, 0.0, 0.0]
        UV += list(uv(cz, cy))
        for k in range(n):
            P += [side * half[k], ys[k], zs[k]]
            N += [side, 0.0, 0.0]
            UV += list(uv(zs[k], ys[k]))
        for k in range(n):
            a, b = base + 1 + k, base + 1 + (k + 1) % n
            I += [base, a, b] if side > 0 else [base, b, a]
    # the rim between the faces
    base = len(P) // 3
    for k in range(n):
        for side in (1, -1):
            P += [side * half[k], ys[k], zs[k]]
            dz = zs[(k + 1) % n] - zs[k - 1]
            dy = ys[(k + 1) % n] - ys[k - 1]
            ln = math.hypot(dz, dy) or 1
            N += [0.0, dz / ln, -dy / ln]
            UV += list(uv(zs[k], ys[k]))
    for k in range(n):
        a, b = base + 2 * k, base + 2 * ((k + 1) % n)
        I += [a, b, a + 1, b, b + 1, a + 1]
    tex = TEX % (mod, 'fin')
    return [{'p': P, 'n': N, 'uv': UV, 'i': I, 'tex': tex, 'normal': tex[:-4] + '_n.dds', 'gloss': 12}]


def fin_picture(size=256, seed=31):
    """The fin's picture (PIL RGB): plain slate with a fine grain, darker to the tip."""
    import numpy as np
    from PIL import Image
    import creaturepaint as cp
    u = np.linspace(0, 1, size)[None, :].repeat(size, 0)        # (0 at the back's far side ... 1 at the tip side)
    v = np.linspace(0, 1, size)[:, None].repeat(size, 1)
    grain = cp.noise((size, size), 6, seed)[..., None]
    col = np.array(SLATE, np.float32) * (0.85 + 0.25 * grain) * (1.05 - 0.25 * u[..., None])
    return Image.fromarray(np.clip(col, 0, 255).astype(np.uint8), 'RGB')


def flat_normal(size=64):
    from PIL import Image
    return Image.new('RGBA', (size, size), (128, 128, 255, 60))


def fin_model(gd, mod='test'):
    """The fin's bytes: skinned wholly to Bip01 Spine2 as the body binds it."""
    import nifmake
    import creaturepaint as cp
    R, T, part = spine_bind(gd)
    # (made as the pictures see the body; the bones bind the raw corners: the lakelurk's shape sits 30 forward of them)
    return nifmake.build_bound('FOLabSharkFin', cp.skin_shapes(fin_shapes(gd, mod), gd.read_file(BODY_GAME)), SPINE, R, T, part)


# ---------- files ----------

def pictures(gd):
    body, paint = body_picture(gd)
    return {'body': body, 'glow': glow_picture(gd, paint), 'fin': fin_picture(), 'normal': normal_picture(gd, paint)}


def files(gd, slug, made=None):
    """{path under Data: bytes}: the body (the lakelurk's with its pictures changed), the fin, their pictures."""
    import creaturepaint as cp
    import nifwrite
    made = made or pictures(gd)
    lurk = gd.read_file(BODY_GAME)
    old = {t['path'] for t in nifwrite.textures_in(lurk)}
    body_old = next(p for p in old if nifwrite.key(p) == nifwrite.key(PIC))
    glow_old = next(p for p in old if nifwrite.key(p) == nifwrite.key(GLOW))
    norm_old = next(p for p in old if nifwrite.key(p) == nifwrite.key(NORMAL))
    body_p, glow_p, fin_p = TEX % (slug, 'body'), TEX % (slug, 'body_g'), TEX % (slug, 'fin')
    norm_p = body_p[:-4] + '_n.dds'
    shaped, _moved = cp.morph(spines_out(nifwrite.retexture(lurk, {body_old: body_p, glow_old: glow_p, norm_old: norm_p})), snout)
    out = {BODY % slug: shaped,
           norm_p: cp.dds_of(made['normal'][0], alpha_from=made['normal'][1]),
           FIN % slug: fin_model(gd, slug),
           body_p: cp.dds_of(made['body']), glow_p: cp.dds_of(made['glow']), fin_p: cp.dds_of(made['fin']),
           fin_p[:-4] + '_n.dds': cp.dds_of(flat_normal(), alpha_from=None)}
    return out


def put_files(gd, pr):
    import library
    root = library.assets_dir(pr)
    made = files(gd, library.slug(pr.name))
    for rel, data in made.items():
        library._put(root, rel, data)
    return sorted(made)


# ---------- records ----------

def _game(gd, tag, edid):
    got = [f for f, (_i, r) in gd.forms.items() if r.tag == tag and gd.edid(f) == edid]
    if not got:
        raise ValueError('the game has no %s %s' % (tag, edid))
    return min(got, key=lambda f: f >> 24)


def _copy(gd, tag, edid):
    import recordio
    rec = json.loads(json.dumps(recordio.load(gd, _game(gd, tag, edid))))
    rec['src'] = ''
    return rec


def _set(rec, tag, value=None, field=None):
    for s in rec['subs']:
        if s['tag'] == tag:
            if field is None:
                s['value'] = value
            else:
                for f in s['fields']:
                    if f.get('name') == field:
                        f['value'] = value
    return rec


def creature(gd, slug, death_list=None):
    """The Sharklurk's CREA: the lakelurk's (skeleton, moves, water breathing, sounds, body parts) with its own body and
    fin, no beam, more health and a harder bite."""
    rec = _copy(gd, 'CREA', LURK)
    sonic = {gd.key(_game(gd, 'WEAP', SONIC[0])), gd.key(_game(gd, 'AMMO', SONIC[1]))}
    keep = []
    for s in rec['subs']:
        if s['tag'] == 'CNTO' and (s.get('fields') or [{}])[0].get('value') in sonic:
            continue
        keep.append(s)
    rec['subs'] = keep
    names = [(BODY % slug).rsplit('\\', 1)[1], (FIN % slug).rsplit('\\', 1)[1]]
    _set(rec, 'EDID', EDID)
    _set(rec, 'FULL', NAME)
    _set(rec, 'NIFZ', '\0'.join(names) + '\0')
    _set(rec, 'BNAM', SCALE, 'Scale')
    _set(rec, 'DATA', HEALTH, 'Health')
    _set(rec, 'DATA', DAMAGE, 'Damage')
    _set(rec, 'ACBS', LEVEL, 'Level')
    if death_list:
        _set(rec, 'INAM', death_list)
    return rec


MEAT, TOOTH, TEETH, DEATH = 'FOLabSharkMeat', 'FOLabSharkTooth', 'FOLabSharkTeeth40', 'FOLabDeathItemSharklurk'
MEAT_EACH, TOOTH_CHANCE = 2, 40         # (meat each kill; a tooth 40 kills in 100)
TOOTH_MODEL = 'Clutter\\RaiderDressing\\Tooth.NIF'


def meat(gd):
    """Shark Meat: the lakelurk's meat (its healing and the same model), a little dearer."""
    rec = _copy(gd, 'ALCH', 'LakelurkMeat')
    _set(rec, 'EDID', MEAT)
    _set(rec, 'FULL', 'Shark Meat')
    _set(rec, 'ENIT', 15, 'Value')
    return rec


def tooth(gd):
    """Shark Tooth: a MISC on the game's tooth model (raiders' dressing), worth a little, light."""
    rec = _copy(gd, 'MISC', 'GeckoHide')
    rec['subs'] = [s for s in rec['subs'] if s['tag'] not in ('MODT', 'ICON', 'MICO')]
    _set(rec, 'EDID', TOOTH)
    _set(rec, 'FULL', 'Shark Tooth')
    _set(rec, 'MODL', TOOTH_MODEL)
    _set(rec, 'DATA', 8, 'Value')
    _set(rec, 'DATA', 0.1, 'Weight')
    return rec


def teeth_list(gd, tooth_key):
    """A tooth, TOOTH_CHANCE kills in 100 (the list's chance of none the rest)."""
    rec = _copy(gd, 'LVLI', 'LootLakelurkMeat10')
    _set(rec, 'EDID', TEETH)
    _set(rec, 'LVLD', 100 - TOOTH_CHANCE, 'Percent')
    _set(rec, 'LVLO', tooth_key, 'Item')
    _set(rec, 'LVLO', 1, 'Count')
    return rec


def death_list(gd, meat_key, teeth_key):
    """What a Sharklurk leaves: its meat every time, the teeth list once (every entry, as the gecko's death items)."""
    rec = _copy(gd, 'LVLI', 'DeathItemGecko100')
    lvlo = [s for s in rec['subs'] if s['tag'] == 'LVLO']
    first = rec['subs'].index(lvlo[0])
    rows = []
    for key, n in ((meat_key, MEAT_EACH), (teeth_key, 1)):
        row = json.loads(json.dumps(lvlo[0]))
        for f in row['fields']:
            if f.get('name') == 'Item':
                f['value'] = key
            elif f.get('name') == 'Count':
                f['value'] = n
        rows.append(row)
    rec['subs'] = [s for s in rec['subs'] if s['tag'] != 'LVLO']
    rec['subs'][first:first] = rows
    _set(rec, 'EDID', DEATH)
    return rec


def records(gd, slug, keys):
    """[(name, record)] in key order: meat, tooth, teeth list, death list, the Sharklurk. keys: {name: key} reserved."""
    return [('meat', meat(gd)), ('tooth', tooth(gd)), ('teeth', teeth_list(gd, keys['tooth'])),
            ('death', death_list(gd, keys['meat'], keys['teeth'])), ('sharklurk', creature(gd, slug, keys['death']))]
