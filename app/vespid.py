"""Waikiki's Vespid (the user, 23 Nov 2026; docs/waikiki-pacing-plan.md section 6): the island's mutant yellowjacket, in the
cazador's place, on the game's cazador as the game has it:

  skeleton   creatures\\NVCazadores\\Skeleton.nif, its animations and ragdoll: kept (the Vespid moves as a cazador)
  body       NVCazadores.NIF: shape 1 the body (7,212 corners, cazadores_D.dds 1024 square, DXT1, + _N), shape 2 the four
             wings (cazadores_wing_D.dds 512, DXT3: the tattered edges are its alpha), two gore caps
  poison     EITM CazadorPoison (SPEL): the game's Antivenom (NVAntivenom, its effect's script) dispels it by name

So a Vespid is a copy of the game's full cazador record (VCrTier4CazadorMedNR: no template) with its own body: the
cazador's body file with its two pictures changed (nifwrite) and a glow picture put in its body's texture set (nifglow,
as the game's Glowing One: slot 2, the material's emissive colour green), in the cazador's own folder because the
creature's model list (NIFZ) names bodies beside the skeleton. Its poison is the cazador's own SPEL, so the game's
Antivenom cures it, and antidotes are easy to come by where it lives (`antidote_ops`).

The pictures are painted over the cazador's by where each texel lies on the body (`texel_map`: every triangle of the
body drawn into the picture with its corners' positions in the bind pose, so a texel knows its place in 3D; `part_of`
names the part): a western yellowjacket's colours (Vespula pensylvanica, which really is invasive in Hawai'i), yellow
and black bands round the abdomen (`bands`), a yellow face, a black thorax with yellow marks, yellow legs from black
hips, black antennae, smoky wings; the cazador's own light and shade kept (each texel's brightness over its part's
middle). Its glow (`glow_picture`): the eyes, and a faint seam where each band meets the next. The queen (`QUEEN`) is
bigger, her glow brighter and her bands' seams lit along the back.

    pictures(gd)              {name: PIL image}: body, wing, glow for each kind (numpy, PIL: a build step, as birds)
    files(gd, slug)           {path under Data: bytes}
    creature(gd, kind, ...)   the kind's CREA
"""
import json
import math

CAZADOR = 'VCrTier4CazadorMedNR'          # (a full record: no template; NR, not the respawning one)
CAZ_BODY = 'meshes\\creatures\\nvcazadores\\nvcazadores.nif'
CAZ_TEX = 'textures\\creatures\\cazadores\\cazadores_D.dds'
CAZ_WING = 'textures\\creatures\\cazadores\\cazadores_wing_D.dds'
BODY = 'meshes\\creatures\\nvcazadores\\folab%s_%s.nif'     # (mod, kind: beside the skeleton, as the creature's NIFZ wants)
TEX = 'textures\\folab\\%s\\vespid\\%s.dds'                 # (mod, picture)
SIZE, WING_SIZE = 1024, 512

# kind: (editor ID, shown name, base scale, health, level, glow strength, emissive multiplier)
KINDS = {
    'vespid': ('FOLabVespid', 'Vespid', 0.85, 200, 18, 1.0, 1.0),
    'queen': ('FOLabVespidQueen', 'Vespid Queen', 1.7, 900, 30, 2.2, 2.0),
}
QUEEN = 'queen'
GLOW_COLOUR = (0.45, 1.0, 0.35)         # (the material's emissive: the glow picture's light is this colour; the Glowing One's
                                        # is 0.63, 0.78, 0.42)
HUANG_WORD = ('huángfēng', 'wasps')      # (what the Huáng call them: on screen "huangfeng (wasps)" in the game's letters)

# western yellowjacket colours
YELLOW = (236, 196, 32)
YELLOW_PALE = (242, 214, 92)
BLACK = (22, 20, 16)
BROWN = (70, 44, 22)
EYE = (34, 38, 26)
WING = (150, 128, 92)                   # (smoky amber membrane)
VEIN = (48, 34, 20)


# ---------- where each texel lies on the body ----------

def _in(p, c, r, k):
    return (((p[..., 0] - c[0]) / r[0]) ** 2 + ((p[..., 1] - c[1]) / r[1]) ** 2 + ((p[..., 2] - c[2]) / r[2]) ** 2) <= k * k


# The cazador in its bind pose: x across (left -x), y along (head +y), z up; it stands on z 0.
# abdomen: an egg from the waist (y -12) back and down to the sting (y -68, z 16); thorax y -5..32; head y 32..50;
# antennae and the front feelers past y 48.
ABDOMEN = ((0.0, -38.0, 44.0), (19.0, 30.0, 25.0), 1.12)
HEAD = ((0.0, 41.0, 34.0), (21.0, 11.0, 19.0), 1.15)
THORAX = ((0.0, 15.0, 50.0), (24.0, 21.0, 28.0), 1.1)
WAIST_TO_TIP = ((0.0, -10.0, 54.0), (0.0, -67.0, 17.0))
SEGMENTS = 6


def part_of(p):
    """Names (array of str) for points p (..., 3) of the bind pose."""
    import numpy as np
    out = np.full(p.shape[:-1], 'leg', dtype=object)
    th = _in(p, *THORAX)
    he = _in(p, *HEAD)
    ab = _in(p, *ABDOMEN)
    front = p[..., 1] > 48
    waist = (p[..., 1] > -16) & (p[..., 1] < -2) & (np.abs(p[..., 0]) < 9) & (p[..., 2] > 30)
    out[waist] = 'waist'
    out[th] = 'thorax'
    out[he] = 'head'
    out[front & ((p[..., 2] > 36) | (np.abs(p[..., 0]) < 3))] = 'antenna'
    out[front & ~((p[..., 2] > 36) | (np.abs(p[..., 0]) < 3))] = 'feeler'
    out[ab] = 'abdomen'
    sting = (p[..., 1] < -58) & (np.abs(p[..., 0]) < 9) & (p[..., 2] < 26)
    out[sting] = 'sting'
    return out


def texel_map(gd, size=SIZE):
    """(positions (size, size, 3) of each texel in the bind pose, covered (size, size) bool), from the body's triangles
    drawn into its picture."""
    import numpy as np
    import nif
    s = nif.mesh_from_nif(gd.read_file(CAZ_BODY), placed=False)[0]
    P = np.array(s['p'], np.float64).reshape(-1, 3)
    UV = np.array(s['uv'], np.float64).reshape(-1, 2) % 1.0 * size
    I = np.array(s['i']).reshape(-1, 3)
    pos = np.zeros((size, size, 3), np.float32)
    have = np.zeros((size, size), bool)
    for a, b, c in I:
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
        # (a pixel's width of slack round each triangle: the edge texels the game filters into)
        m = (w0 >= -0.6 / max(1.0, abs(d) ** 0.5)) & (w1 >= -0.6 / max(1.0, abs(d) ** 0.5)) & (w2 >= -0.6 / max(1.0, abs(d) ** 0.5))
        if not m.any():
            continue
        q = w0[..., None] * P[a] + w1[..., None] * P[b] + w2[..., None] * P[c]
        sub, sh = pos[y0:y1 + 1, x0:x1 + 1], have[y0:y1 + 1, x0:x1 + 1]
        fresh = m & ~sh
        sub[fresh] = q[fresh]
        sh[fresh] = True
    return pos, have


def bands(p):
    """(t along the abdomen 0 at the waist to 1 at the sting, black (bool)) for points p (..., 3): each segment black at
    its front, yellow behind, the black reaching back in a point along the top (the yellowjacket's anchors) and in a
    spot on each side; the first segment's front and the sting black."""
    import numpy as np
    (w, t_) = WAIST_TO_TIP
    w, t_ = np.array(w), np.array(t_)
    ax = t_ - w
    t = ((p - w) @ ax) / float(ax @ ax)
    # (where round the abdomen: up is the back, the dorsal line)
    off = p - (w + t[..., None] * ax)
    n_up = np.array([0.0, ax[2], -ax[1]])
    n_up = n_up / np.linalg.norm(n_up) * (1 if n_up[2] > 0 else -1)
    side = np.abs(p[..., 0])
    up = off @ n_up
    r = np.linalg.norm(off, axis=-1) + 1e-6
    dorsal = np.clip(up / r, -1, 1)                     # 1 on the top line, -1 underneath
    s = np.clip(t, 0, 1) * SEGMENTS
    f = s - np.floor(s)
    black_part = 0.38 + 0.36 * np.clip((dorsal - 0.55) / 0.45, 0, 1) * np.clip(1 - side / 7.0, 0, 1)   # (the anchor)
    spot = (np.abs(f - 0.62) < 0.1) & (np.abs(dorsal - 0.15) < 0.22) & (np.floor(s) >= 1) & (np.floor(s) <= 4)
    black = (f < black_part) | spot | (t < 0.07) | (t > 0.94)
    black &= ~((dorsal < -0.35) & (f > 0.25))           # (underneath mostly yellow)
    return t, black, f


def paint_of(p, part, base_lum):
    """RGB (..., 3) float for each texel by its place and part."""
    import numpy as np
    out = np.zeros(p.shape[:-1] + (3,), np.float32)

    def put(mask, col):
        out[mask] = col
    x, y, z = p[..., 0], p[..., 1], p[..., 2]
    # legs: black hips and thighs near the body, yellow below
    leg = part == 'leg'
    near = (np.abs(x) < 26) & (z > 30)
    put(leg, YELLOW_PALE)
    put(leg & near, BLACK)
    put(leg & (z < 6), BROWN)                           # (the feet)
    put(part == 'waist', BLACK)
    put(part == 'sting', BROWN)
    put(part == 'antenna', BLACK)
    put(part == 'feeler', YELLOW)
    # thorax: black, a yellow collar at its front, two yellow marks on its back, a yellow stroke under each wing
    th = part == 'thorax'
    put(th, BLACK)
    collar = th & (y > 29) & (y < 33) & (z > 46)
    put(collar, YELLOW)
    marks = th & (np.abs(np.abs(x) - 6.0) < 3.2) & (np.abs(y - 2.0) < 4.0) & (z > 58)
    put(marks, YELLOW)
    stroke = th & (np.abs(x) > 15) & (np.abs(z - 50) < 4) & (np.abs(y - 14) < 9)
    put(stroke, YELLOW)
    # head: a yellow face, black crown and a black mark down the middle of the face
    he = part == 'head'
    put(he, YELLOW)
    put(he & (z > 44), BLACK)
    put(he & (np.abs(x) < 2.2) & (z > 32), BLACK)
    # abdomen bands
    ab = part == 'abdomen'
    _t, black, _f = bands(p)
    put(ab, YELLOW)
    put(ab & black, BLACK)
    return out


def _eyes(caz):
    """Where the cazador's eye is on its picture: the red, many-sided patch."""
    import numpy as np
    r, g, b = caz[..., 0], caz[..., 1], caz[..., 2]
    return (r > 70) & (r > 1.7 * g) & (r > 1.7 * b)


def _caz(gd, path, size):
    import numpy as np
    import dds
    w, h, px = dds.decode(gd.read_file(path), want=size)[:3]
    assert (w, h) == (size, size), (path, w, h)
    return np.frombuffer(bytes(px), np.uint8).reshape(h, w, 4).astype(np.float32)


def body_picture(gd, kind='vespid', tm=None, caz=None):
    """The body's picture (PIL RGB): each texel its colour, lit and shaded as the cazador's is there."""
    import numpy as np
    from PIL import Image, ImageFilter
    pos, have = tm or texel_map(gd)
    caz = _caz(gd, CAZ_TEX, SIZE) if caz is None else caz
    lum = caz[..., :3].mean(axis=2)
    part = part_of(pos)
    col = paint_of(pos, part, lum)
    out = caz[..., :3].copy()
    for name in set(part[have].tolist()):
        m = have & (part == name)
        mid = max(8.0, float(np.median(lum[m])))
        shade = np.clip(lum / mid, 0.45, 1.7) ** 0.75
        out[m] = col[m] * shade[m][:, None]
    dark = col.sum(axis=-1) < 120
    out[have & dark] += 0.22 * caz[..., :3][have & dark]       # (black chitin keeps some of the cazador's sheen)
    eye = _eyes(caz)
    out[eye] = np.array(EYE, np.float32)[None, :] * (0.55 + 0.6 * lum[eye] / max(1.0, float(lum[eye].max())))[:, None]
    if kind == QUEEN:
        # (the queen: deeper, older colours)
        out[have] = out[have] * np.array([0.94, 0.86, 0.8], np.float32)
    img = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), 'RGB')
    # (the colours bled a little past each island's edge, so the smaller copies don't fringe)
    grown = img.filter(ImageFilter.MaxFilter(5))
    m = Image.fromarray((have * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(3))
    return Image.composite(img, grown, m)


def glow_picture(gd, kind='vespid', tm=None, caz=None):
    """The body's glow picture (PIL RGB, grey: the material's emissive colour tints it): the eyes, the seams between the
    bands, and for the queen the seams along her back and the sting."""
    import numpy as np
    from PIL import Image, ImageFilter
    pos, have = tm or texel_map(gd)
    caz = _caz(gd, CAZ_TEX, SIZE) if caz is None else caz
    part = part_of(pos)
    strength = KINDS[kind][5]
    g = np.zeros(have.shape, np.float32)
    eye = _eyes(caz)
    lum = caz[..., :3].mean(axis=2)
    g[eye] = 150 + 90 * np.clip(lum[eye] / max(1.0, float(lum[eye].max())), 0, 1)
    ab = have & (part == 'abdomen')
    t, black, f = bands(pos)
    seam = ab & (np.abs(f - 0.02) < 0.035) & (t > 0.1) & (t < 0.92)
    g[seam] = np.maximum(g[seam], 70)
    if kind == QUEEN:
        g[seam] = np.maximum(g[seam], 150)
        back = ab & black & (np.abs(pos[..., 0]) < 2.5)
        g[back] = np.maximum(g[back], 120)
        g[have & (part == 'sting')] = 160
    g = np.clip(g * strength, 0, 255)
    img = Image.fromarray(g.astype(np.uint8), 'L').filter(ImageFilter.GaussianBlur(1.2))
    return Image.merge('RGB', (img, img, img))


def wing_picture(gd, kind='vespid', caz=None):
    """The wings (PIL RGBA): the cazador's veins and tattered edges, its orange membrane made a yellowjacket's smoky
    amber; the strips beside (feeler and leg bits on the same sheet) left as they are."""
    import numpy as np
    from PIL import Image
    w = _caz(gd, CAZ_WING, WING_SIZE) if caz is None else caz
    rgb, a = w[..., :3], w[..., 3:]
    lum = rgb.mean(axis=2)
    warm = (rgb[..., 0] > rgb[..., 2] + 25)             # (the orange of the wing: the strips beside are grey)
    vein = np.clip((70 - lum) / 50.0, 0, 1)[..., None]
    mem = np.array(WING, np.float32)[None, None, :] * (0.75 + 0.5 * np.clip(lum / 170.0, 0, 1))[..., None]
    if kind == QUEEN:
        mem = mem * np.array([0.9, 0.95, 0.75], np.float32)
    new = mem * (1 - vein) + np.array(VEIN, np.float32)[None, None, :] * vein
    out = np.where(warm[..., None], new, rgb)
    return Image.fromarray(np.clip(np.concatenate([out, a], axis=2), 0, 255).astype(np.uint8), 'RGBA')


def pictures(gd):
    """{(kind, 'body'|'glow'|'wing'): PIL image}."""
    tm = texel_map(gd)
    caz = _caz(gd, CAZ_TEX, SIZE)
    wing = _caz(gd, CAZ_WING, WING_SIZE)
    out = {}
    for k in KINDS:
        out[(k, 'body')] = body_picture(gd, k, tm, caz)
        out[(k, 'glow')] = glow_picture(gd, k, tm, caz)
        out[(k, 'wing')] = wing_picture(gd, k, wing)
    return out


def _picture_name(kind, what):
    return '%s_%s' % (kind, what)


def files(gd, slug, made=None):
    """{path under Data: bytes}: each kind's body (the cazador's with its pictures changed and its glow put in) and its
    three pictures (body DXT1, glow DXT1, wings DXT5 with the cazador's alpha)."""
    import dds
    import nifglow
    import nifwrite
    caz = gd.read_file(CAZ_BODY)
    old = {t['path'] for t in nifwrite.textures_in(caz)}
    body_old = next(p for p in old if nifwrite.key(p) == nifwrite.key(CAZ_TEX))
    wing_old = next(p for p in old if nifwrite.key(p) == nifwrite.key(CAZ_WING))
    made = made or pictures(gd)
    out = {}
    for k, row in KINDS.items():
        body_p = TEX % (slug, _picture_name(k, 'body'))
        glow_p = body_p[:-4] + '_g.dds'
        wing_p = TEX % (slug, _picture_name(k, 'wing'))
        data = nifwrite.retexture(caz, {body_old: body_p, wing_old: wing_p})
        data, lit = nifglow.light_up(data, body_p, glow_p, mult=row[6], colour=GLOW_COLOUR)
        if lit != 1:
            raise ValueError('the glow went on %d shapes, not the body alone' % lit)
        out[BODY % (slug, k)] = data
        for path, im, cut in ((body_p, made[(k, 'body')], None), (glow_p, made[(k, 'glow')], None),
                              (wing_p, made[(k, 'wing')], 0)):
            rgba = im.convert('RGBA').tobytes()
            out[path] = dds.compress(dds.encode(im.size[0], im.size[1], rgba, cut=cut or None))
    return out


def put_files(gd, pr):
    """The files among the mod's own (projects/<mod> assets/). Returns their paths."""
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


def creature(gd, kind, slug, death_item=None, script_key=None):
    """The kind's CREA: the cazador's (its skeleton, moves, poison, combat style, sounds), its own body, name, scale,
    health and level; its death item `death_item` when given (else the cazador's)."""
    edid, shown, scale, health, level, _g, _m = KINDS[kind]
    rec = _copy(gd, 'CREA', CAZADOR)
    for s in rec['subs']:
        if s['tag'] == 'EDID':
            s['value'] = edid
        elif s['tag'] == 'FULL':
            s['value'] = shown
        elif s['tag'] == 'NIFZ':
            s['value'] = (BODY % (slug, kind)).rsplit(chr(92), 1)[1] + chr(0)
        elif s['tag'] == 'BNAM':
            s['fields'][0]['value'] = scale
        elif s['tag'] == 'INAM' and death_item:
            s['value'] = death_item
        elif s['tag'] == 'DATA':
            for f in s['fields']:
                if f.get('name') == 'Health':
                    f['value'] = health
        elif s['tag'] == 'ACBS':
            for f in s['fields']:
                if f.get('name') == 'Level':
                    f['value'] = level
    if script_key:
        at = next(i for i, s in enumerate(rec['subs']) if s['tag'] in ('EITM', 'NIFZ'))
        if any(s['tag'] == 'SCRI' for s in rec['subs']):
            for s in rec['subs']:
                if s['tag'] == 'SCRI':
                    s['value'] = script_key
        else:
            rec['subs'].insert(at, {'tag': 'SCRI', 'label': 'Script', 'kind': 'F', 'value': script_key})
    return rec
