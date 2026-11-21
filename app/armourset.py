"""Waikiki's armour and dress (the user, 21 Nov 2026: "love the armor ideas", then "Build and put them in";
`docs/waikiki-armour-ideas.md`): each is a game armour with pictures of FOLab's own on its meshes (nifwrite: only the
texture paths change), an ARMO copied from it with those models, and the Kahuna's guard's crested helmet (the mahiole)
a model of FOLab's own made as hats.py makes hats.

How a picture is painted (`paint`): each pixel of the game's picture is labelled where it lands on the body (`part_of`,
from the middle of every triangle of every model drawn with it: cape, chest, arm, skirt, shin, feet, head) and what it
is made of (`stuff`, from its colour: metal, red cloth, leather, cloth); a recipe names a pattern for (part, stuff),
(part, '*'), ('*', stuff) or ('*', '*'), laid on with the picture's own light (garmentprint.shading: folds, seams and
edges kept, the old pattern out) and its alpha (the Legion's fringes are cut-outs). The fighter's plates get shark teeth
along their edges (`teeth`).

Who wears what is the user's groups as named (`WHO`): only pirates are people of the mod's own so far (peopledress), so
the boarding armour goes in their body list; the Kahuna's guard, the fighters, the captains and the Huáng have no people
yet, so their armour is made and waits (`ops` reports it as unworn).

Records drop the base's script, enchantment and alternate textures (a Legion piece's script, the duster's and Marked
Men's enchantments): numbers, slots and repair list are the base's.

Needs numpy, PIL and scipy (as garmentprint): a build step from the developer's Python."""
import math
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

import dds
import garmentprint
import hats
import library
import nif
import nifmake
import recordio

B = chr(92)
GOLD = (200, 160, 60)
SCRAP = (120, 116, 108)
PLATE_MIN = 3000            # (pixels on a 1024 picture: a piece this big is a plate, smaller ones are straps and buckles)
LAUHALA = hats.LAUHALA


# ---------- where on the body, what it's made of ----------

def part_of(tex, x, y, z):
    if 'cloak' in tex.lower():
        return 'cape'
    if z < 22:
        return 'feet'
    if z < 44:
        return 'shin'
    if z < 72:
        return 'skirt'
    if z > 108:
        return 'head'
    if abs(x) > 17:
        return 'arm'
    return 'chest'


def _picture(gd, path):
    w, h, px = dds.decode(gd.read_file(path), want=4096)[:3]
    return Image.frombytes('RGBA', (w, h), bytes(px))


def labels(gd, meshes, tex, size):
    """{part: bool mask} over the picture tex (size x size), from every model's triangles drawn with it."""
    ims = {}
    for m in meshes:
        for s in nif.mesh_from_nif(gd.read_file(m), placed=False):
            if s['tex'].lower() != tex.lower():
                continue
            uv, idx, P = s['uv'], s['i'], s['p']
            for t in range(0, len(idx), 3):
                ks = [idx[t + k] for k in range(3)]
                c = [sum(P[3 * k + a] for k in ks) / 3 for a in range(3)]
                part = part_of(tex, *c)
                if part not in ims:
                    ims[part] = Image.new('L', (size, size), 0)
                ImageDraw.Draw(ims[part]).polygon([((uv[2 * k] % 1) * size, (uv[2 * k + 1] % 1) * size) for k in ks], fill=255)
    return {p: np.asarray(im.filter(ImageFilter.MaxFilter(3))) > 0 for p, im in ims.items()}


def stuff(rgb):
    """per pixel: 'metal', 'red', 'leather' or 'cloth', from the picture's colour."""
    a = rgb.astype(np.float32) / 255
    mx, mn = a.max(-1), a.min(-1)
    s = (mx - mn) / np.maximum(mx, 1e-3)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    red = (r > g * 1.45) & (r > b * 1.3) & (mx > 0.18)
    out = np.full(a.shape[:2], 'cloth', dtype=object)
    out[(s < 0.22) & (mx > 0.30)] = 'metal'
    out[(s >= 0.22) & (mx <= 0.30) & ~red] = 'leather'
    out[red] = 'red'
    return out


# ---------- patterns: each a function () -> RGB float array, tiled over the picture ----------

def tiled(tile, shape):
    th, tw = tile.shape[:2]
    return np.tile(tile, (shape[0] // th + 1, shape[1] // tw + 1, 1))[:shape[0], :shape[1]]


def solid(c):
    return lambda: np.array(c, np.float32).reshape(1, 1, 3)


def feathers(ground, band=None, size=56, seed=3):
    """overlapping rounded feather tips in rows, as a cloak's netting is tied; yellow crescents of `band` if given."""
    def make():
        rnd = random.Random(seed)
        n = 8
        im = Image.new('RGB', (size * n, size * n), tuple(int(v * 0.6) for v in ground))
        d = ImageDraw.Draw(im)
        for row in range(n * 2 + 2):
            for col in range(n + 1):
                cx = col * size + (size // 2 if row % 2 else 0)
                cy = row * size // 2 - size // 2
                k = rnd.uniform(0.85, 1.1)
                d.ellipse((cx - size * 0.55, cy - size * 0.2, cx + size * 0.55, cy + size * 0.75),
                          fill=tuple(min(255, int(v * k)) for v in ground), outline=tuple(int(v * 0.55) for v in ground))
                d.line((cx, cy, cx, cy + size * 0.6), fill=tuple(int(v * 0.75) for v in ground), width=2)
        a = np.asarray(im, np.float32)
        if band:
            yy, xx = np.mgrid[0:a.shape[0], 0:a.shape[1]] / a.shape[0]
            m = np.zeros(a.shape[:2], bool)
            for cx, cy in ((0.25, 0.3), (0.75, 0.8)):
                for ox in (-1, 0, 1):
                    for oy in (-1, 0, 1):
                        m |= (np.hypot(xx - cx - ox, yy - cy - oy) < 0.2) & (np.hypot(xx - cx - ox, yy - cy - oy + 0.07) > 0.2)
            a[m] = a[m] / np.maximum(np.asarray(ground, np.float32), 1) * np.asarray(band, np.float32)
        return a
    return make


def lamellae(iron=(118, 114, 108), lace=(170, 40, 34), w=40, h=56):
    """rows of small rounded plates, overlapping, laced in red: scales cut from the ship's hull."""
    def make():
        im = Image.new('RGB', (w * 8, h * 4), (40, 36, 34))
        d = ImageDraw.Draw(im)
        for row in range(6):
            for col in range(10):
                x = col * w + (w // 2 if row % 2 else 0) - w // 2
                y = row * h - h
                d.rounded_rectangle((x + 1, y, x + w - 2, y + h * 1.25), radius=w // 2, fill=iron, outline=(60, 58, 55))
                d.rectangle((x + w // 2 - 2, y + h * 0.15, x + w // 2 + 2, y + h * 0.35), fill=lace)
            d.line((0, row * h - h + h * 0.08, w * 8, row * h - h + h * 0.08), fill=lace, width=3)
        return np.asarray(im, np.float32)
    return make


def plait(colours, size=128):
    def make():
        c = hats.plait(colours, size=size)
        return np.asarray(c.rgb, np.float32).reshape(c.h, c.w, 3)
    return make


def coir(base=(120, 82, 48)):
    """coconut fibre: rough brown strands."""
    def make():
        rnd = random.Random(9)
        im = Image.new('RGB', (128, 128), tuple(int(v * 0.7) for v in base))
        d = ImageDraw.Draw(im)
        for _ in range(700):
            x, y = rnd.uniform(-10, 138), rnd.uniform(-20, 128)
            k = rnd.uniform(0.6, 1.35)
            d.line((x, y, x + rnd.uniform(-6, 6), y + rnd.uniform(10, 26)), fill=tuple(min(255, int(v * k)) for v in base), width=1)
        return np.asarray(im, np.float32)
    return make


def tapa(ground=(214, 196, 160), ink=(60, 38, 26), cell=48):
    """bark cloth printed in bands of triangles and lines."""
    def make():
        im = Image.new('RGB', (cell * 4, cell * 4), ground)
        d = ImageDraw.Draw(im)
        for r in range(4):
            y = r * cell
            if r % 2 == 0:
                for c in range(8):
                    x = c * cell // 2
                    d.polygon([(x, y + cell * 0.8), (x + cell // 4, y + cell * 0.2), (x + cell // 2, y + cell * 0.8)], fill=ink)
            else:
                for k in range(4):
                    d.line((0, y + cell * (0.2 + 0.2 * k), cell * 4, y + cell * (0.2 + 0.2 * k)), fill=ink, width=3 if k % 2 else 1)
        return np.asarray(im, np.float32)
    return make


def canvas(base=(196, 186, 160)):
    """sailcloth: a plain heavy weave."""
    def make():
        rnd = np.random.default_rng(4)
        a = np.ones((64, 64, 3), np.float32) * np.asarray(base, np.float32)
        a *= (0.93 + 0.07 * ((np.arange(64)[None, :] % 3) == 0))[..., None]
        a *= (0.95 + 0.05 * ((np.arange(64)[:, None] % 3) == 0))[..., None]
        return a * (0.95 + 0.1 * rnd.random((64, 64, 1)))
    return make


def rubber():
    """tyre rubber: black with tread."""
    def make():
        im = Image.new('RGB', (96, 96), (34, 34, 36))
        d = ImageDraw.Draw(im)
        for k in range(7):
            d.polygon([(0, k * 16), (40, k * 16 + 8), (0, k * 16 + 12)], fill=(58, 58, 60))
            d.polygon([(96, k * 16 + 8), (56, k * 16), (96, k * 16 - 4)], fill=(58, 58, 60))
        return np.asarray(im, np.float32)
    return make


def brocade(ground, figure, size=200, seed=5):
    """silk with peonies and cloud scrolls in the figure colour."""
    def make():
        rnd = random.Random(seed)
        im = Image.new('RGB', (size * 3, size * 3), tuple(ground))
        d = ImageDraw.Draw(im)
        for _ in range(7):
            x0, y0, peony = rnd.uniform(0, size), rnd.uniform(0, size), rnd.random() < 0.5
            for ox in (0, size, 2 * size):
                for oy in (0, size, 2 * size):
                    x, y = x0 + ox, y0 + oy
                    if peony:
                        for k, r in enumerate((26, 18, 10)):
                            c = tuple(int(g + (f - g) * (0.55 + 0.2 * k)) for g, f in zip(ground, figure))
                            for j in range(8):
                                a = j * math.tau / 8 + k * 0.4
                                d.ellipse((x + math.cos(a) * r * 0.6 - r * 0.5, y + math.sin(a) * r * 0.6 - r * 0.5,
                                           x + math.cos(a) * r * 0.6 + r * 0.5, y + math.sin(a) * r * 0.6 + r * 0.5), fill=c)
                    else:
                        for j in range(3):
                            d.arc((x + j * 16 - 14, y - 12, x + j * 16 + 14, y + 12), 180, 360, fill=tuple(figure), width=3)
                            d.arc((x + j * 16 - 7, y - 4, x + j * 16 + 7, y + 8), 0, 270, fill=tuple(figure), width=2)
        return np.asarray(im.crop((size, size, 2 * size, 2 * size)), np.float32)
    return make


def teeth(rgb, sel, colour=(238, 232, 212), every=None, size=None):
    """shark teeth along the edges of sel (a bool mask): small pale triangles standing on its edge, pointing in."""
    import scipy.ndimage as nd
    if not sel.any():
        return rgb
    k = sel.shape[0] / 1024.0
    size = size or 20 * k                               # (a tooth about a finger's width on the plate)
    every = every or int(round(18 * k))
    edge = sel & ~nd.binary_erosion(sel, iterations=2)
    soft = nd.gaussian_filter(sel.astype(np.float32), 3)
    gy, gx = np.gradient(soft)
    im = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(im)
    ys, xs = np.nonzero(edge)
    seen = set()
    for y, x in zip(ys, xs):
        cell = (y // every, x // every)
        if cell in seen:
            continue
        seen.add(cell)
        nx, ny = gx[y, x], gy[y, x]                     # (inward: outside the piece is picture nothing is drawn with)
        ln = math.hypot(nx, ny)
        if ln < 1e-4:
            continue
        nx, ny = nx / ln, ny / ln
        tx, ty = -ny, nx
        base = [(x + tx * size * 0.5, y + ty * size * 0.5), (x - tx * size * 0.5, y - ty * size * 0.5)]
        d.polygon(base + [(x + nx * size, y + ny * size)], fill=colour, outline=(150, 140, 120))
    return np.asarray(im, np.float32)


def paint(gd, meshes, tex, recipe, extra=None):
    """The picture tex with each (part, stuff) the recipe names painted, its light and alpha kept: a PIL RGBA image."""
    src = _picture(gd, tex)
    size = src.size[0]
    if src.size[1] != size:
        src = src.resize((size, size))
    base = src.convert('RGB')
    labs = labels(gd, meshes, tex, size)
    rgb = np.asarray(base, np.int16)
    st = stuff(rgb)
    out = np.asarray(base, np.float32).copy()
    shade = garmentprint.shading(base, Image.fromarray(np.full(rgb.shape[:2], 255, np.uint8)))[..., None]
    made = {}
    for part, m in labs.items():
        for kind in ('metal', 'red', 'leather', 'cloth'):
            pat = None
            for key in ((part, kind), (part, '*'), ('*', kind), ('*', '*')):
                if key in recipe:
                    pat = recipe[key]
                    break
            sel = m & (st == kind)
            if pat is None or not sel.any():
                continue
            if id(pat) not in made:
                p = pat()
                made[id(pat)] = tiled(p, rgb.shape) if p.shape[0] > 1 else np.broadcast_to(p, rgb.shape).astype(np.float32)
            out[sel] = (made[id(pat)] * shade)[sel]
    if extra:
        out = extra(out, labs, st)
    rgba = np.dstack([np.clip(out, 0, 255).astype(np.uint8), np.asarray(src)[..., 3]])
    return Image.fromarray(rgba, 'RGBA')


def _fighter_teeth(out, labs, st):
    """teeth round the scrap plates on the shoulders (the pieces over the collar bone: `part_of` calls them head), each a
    piece of its own in the picture, so its edge there is the plate's edge."""
    import scipy.ndimage as nd
    if 'head' not in labs:
        return out
    sel = nd.binary_opening(labs['head'], iterations=2)
    lab, n = nd.label(sel)
    if not n:
        return out
    sizes = nd.sum(sel, lab, range(1, n + 1))
    big = [k + 1 for k, v in enumerate(sizes) if v > PLATE_MIN * (st.shape[0] / 1024.0) ** 2]
    return teeth(out, np.isin(lab, big))


# ---------- the armours ----------
# key -> (base ARMO, editor ID, name in game, who, recipe, extra)
ARMOURS = {
    'feathercloak': ('ArmorNVCLPraetorian', 'FOLabAhuula', "Ali'i Feather Cloak", 'the Kahuna\'s guard', {
        ('cape', '*'): feathers((160, 26, 22), band=(220, 176, 46)),
        ('chest', 'metal'): plait(LAUHALA), ('chest', 'leather'): plait(LAUHALA), ('chest', 'red'): feathers((236, 190, 40)),
        ('arm', '*'): coir(), ('chest', 'cloth'): coir(),
        ('skirt', '*'): tapa(), ('shin', '*'): coir((100, 70, 40)), ('feet', '*'): coir((90, 62, 36)),
    }, None),
    'fighter': ('NVDLC04ArmorMarkedMenTribal', 'FOLabKoaArmor', 'Koa Fighting Armor', 'the fighters', {
        ('head', '*'): solid(SCRAP), ('chest', '*'): plait(LAUHALA), ('arm', '*'): coir(), ('skirt', '*'): coir(),
        ('shin', '*'): coir((100, 70, 40)), ('feet', '*'): coir((90, 62, 36)),
    }, _fighter_teeth),
    'boarding': ('ArmorNVCLCenturion', 'FOLabSalvageArmor', 'Salvaged Boarding Armor', 'pirates', {
        ('chest', 'metal'): solid((214, 120, 30)), ('arm', 'metal'): solid((90, 84, 76)),
        ('*', 'red'): canvas(), ('*', 'leather'): rubber(), ('skirt', '*'): canvas((150, 140, 116)),
        ('cape', '*'): canvas((170, 160, 132)), ('shin', 'metal'): solid((90, 84, 76)),
    }, None),
    'officercoat': ('BountyHunterDuster', 'FOLabOfficersCoat', "Officer's Coat", 'pirate captains', {
        ('chest', '*'): solid((22, 26, 48)), ('arm', '*'): solid((22, 26, 48)), ('skirt', 'cloth'): solid((22, 26, 48)),
        ('skirt', 'leather'): solid((22, 26, 48)), ('skirt', 'metal'): solid((22, 26, 48)), ('shin', '*'): solid((30, 26, 24)),
        ('feet', '*'): solid((30, 26, 24)),
    }, None),
    'lamellar': ('ArmorNVCLVeteran', 'FOLabHuangLamellar', 'Lamellar Armor', 'the Huáng\'s guards', {
        ('*', 'metal'): lamellae(), ('chest', 'leather'): lamellae(), ('skirt', 'leather'): lamellae(),
        ('*', 'red'): solid((160, 36, 30)), ('skirt', 'cloth'): lamellae(), ('arm', 'leather'): solid((150, 34, 28)),
        ('shin', '*'): solid((40, 34, 30)), ('feet', '*'): solid((34, 28, 24)),
    }, None),
    'changshan': ('OutfitVeronicaRobes', 'FOLabChangshan', 'Changshan', 'the Huáng', {
        ('chest', '*'): solid((34, 42, 64)), ('arm', '*'): solid((34, 42, 64)), ('skirt', '*'): solid((34, 42, 64)),
        ('shin', '*'): solid((30, 30, 32)), ('feet', '*'): solid((26, 24, 22)), ('head', '*'): solid((34, 42, 64)),
    }, None),
    'silkgown': ('OutfitVeronicaRobes', 'FOLabSilkGown', 'Silk Gown', 'the Huáng', {
        ('chest', '*'): brocade((150, 24, 26), (214, 170, 70)), ('arm', '*'): brocade((150, 24, 26), (214, 170, 70)),
        ('skirt', '*'): brocade((150, 24, 26), (214, 170, 70)), ('head', '*'): brocade((150, 24, 26), (214, 170, 70)),
        ('shin', '*'): solid((30, 30, 32)), ('feet', '*'): solid((26, 24, 22)),
    }, None),
    'officialrobe': ('OutfitElderMcNamara', 'FOLabOfficialsRobe', "Official's Robe", 'the Huáng\'s leaders', {
        ('*', 'red'): brocade((18, 22, 40), (96, 80, 40), size=320), ('*', 'cloth'): solid((18, 22, 40)),
        ('*', 'leather'): solid((26, 22, 20)), ('*', 'metal'): solid(GOLD),
    }, None),
}
MODEL_TAGS = ('MODL', 'MOD2', 'MOD3', 'MOD4')
DROP = ('MODT', 'MO2T', 'MO3T', 'MO4T', 'MODS', 'MO2S', 'MO3S', 'MO4S', 'MODD', 'MOSD', 'SCRI', 'EITM')
# the groups as people of the mod's own: who wears each armour now; the rest have no people yet
WHO = {'boarding': ('FOLabPirateBodyList', 2)}     # (list, entries added: pirates' body list holds ~25)


def _base(gd, edid):
    return next(f for f, (_i, r) in gd.forms.items() if r.tag == 'ARMO' and gd.edid(f) == edid)


def _models(gd, edid):
    rec = recordio.load(gd, _base(gd, edid))
    return {t: 'meshes' + B + recordio.field(rec, t) for t in MODEL_TAGS if recordio.field(rec, t)}


def files(gd, pr, key):
    """Paints the armour's pictures and writes them and its models among the mod's own files: {tag: model path}."""
    import nifwrite
    edid, _e, _n, _who, recipe, extra = ARMOURS[key]
    models = _models(gd, edid)
    worn = [models[t] for t in ('MODL', 'MOD3') if t in models]
    root = library.assets_dir(pr)
    slug = library.slug(pr.name)
    texs = set()
    for m in worn:
        for s in nif.mesh_from_nif(gd.read_file(m), placed=False):
            t = s['tex']
            if t and 'characters' not in t.lower() and 'gore' not in t.lower() and t.lower().endswith('.dds'):
                texs.add(t)
    changes = {}
    for t in sorted(texs):
        pic = 'textures\\folab\\%s\\armour\\%s_%s' % (slug, key, t.split(B)[-1].lower())
        im = paint(gd, worn, t, recipe, extra)
        cut = 128 if any(a < 255 for a in im.getchannel('A').getdata()) else None
        library._put(root, pic, dds.compress(dds.encode(im.size[0], im.size[1], im.tobytes(), cut=cut)))
        changes[t] = pic
    out = {}
    for tag, m in models.items():
        data = gd.read_file(m)
        new = nifwrite.retexture(data, changes)
        wrong = nifwrite.prove(data, changes)
        if wrong:
            raise ValueError('%s %s: %s' % (key, tag, '; '.join(wrong)))
        rel = 'meshes\\folab\\%s\\armour\\%s_%s.nif' % (slug, key, tag.lower())
        library._put(root, rel, new)
        out[tag] = rel
    return out


def armour_record(gd, key, models):
    base, edid, name, _who, _r, _x = ARMOURS[key]
    fid = _base(gd, base)
    rec = recordio.load(gd, fid)
    rec['src'] = ''
    rec['copied_from'] = gd.key(fid)
    for s in rec['subs']:
        if s['tag'] in models:
            s['value'] = models[s['tag']][7:]               # (models are named from meshes\)
    rec['subs'] = [s for s in rec['subs'] if s['tag'] not in DROP]
    recordio.set_field(rec, 'EDID', edid)
    recordio.set_field(rec, 'FULL', name)
    return rec


# ---------- the mahiole: the Kahuna's guard's crested helmet ----------
MAHIOLE = {'top': 7.6, 'thick': 0.4, 'crest': 4.2, 'crest_w': 0.95}


def mahiole_textures():
    """(red feathers, yellow feathers): each (diffuse DDS, flat normal map DDS)."""
    out = []
    for ground in ((160, 26, 22), (226, 182, 48)):
        a = feathers(ground, size=24)()
        im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).resize((256, 256))
        diffuse = garmentprint.dds_of(im)
        normal = garmentprint.dds_of(Image.new('RGB', (64, 64), (128, 128, 255)))
        out.append((diffuse, normal))
    return out


def mahiole_shapes():
    """A close cap (the lauhala's crown, no brim) and a crest from brow to nape, in the hat's frame (hats.py)."""
    top, thick = MAHIOLE['top'], MAHIOLE['thick']
    crown = hats._dome
    cap = hats.Profile('mahiole_red')
    dome = [(crown(h), h) for h in (top, top - 0.15, top - 0.6, top - 1.4, top - 2.4, top - 3.4, 2.8, 2.0, 1.0, 0.0)]
    dome[0] = (0.0, top)
    cap.strip(dome[:3], uv='plan')
    lip = crown(0.0)
    cap.strip(dome[2:], u_turns=5.0, v_per=0.12)
    cap.strip([(lip, 0.0), (lip - thick, -0.05)], u_turns=5.0)
    inner = [(max(0.0, crown(h) - thick), h - thick) for h in (0.0, 1.0, 2.0, 2.8, top - 3.4, top - 2.4, top - 1.4, top - 0.6, top - 0.15)]
    inner = [(lip - thick, -0.05)] + inner[1:]
    cap.strip(inner, u_turns=5.0, v_per=0.12)
    cap.strip([inner[-1], (0.0, top - thick)], uv='plan')
    # the crest: stations over the head from the brow (front, +y) to the nape, each a ring standing on the cap
    crest = hats.Profile('mahiole_yellow')
    ry, rz = hats.BAND_R * hats.BAND_E, top
    rows = []
    N, M = 28, 12
    for k in range(N + 1):
        f = k / N
        phi = math.radians(28 + 130 * f)                   # from the brow up over the top and down the back
        by, bz = ry * math.cos(phi), rz * math.sin(phi) - 0.3
        ny, nz = math.cos(phi) / ry, math.sin(phi) / rz      # (the dome's outward normal in the y-z plane)
        ln = math.hypot(ny, nz)
        ny, nz = ny / ln, nz / ln
        h = 0.4 + MAHIOLE['crest'] * math.sin(math.pi * f) ** 0.6
        w = MAHIOLE['crest_w'] * (0.35 + 0.65 * math.sin(math.pi * f) ** 0.4)
        ring = []
        for j in range(M + 1):
            a = math.tau * j / M
            cx, cn = w * math.cos(a), h / 2 * (1 + math.sin(a))
            p = (cx, by + ny * cn, bz + nz * cn)
            n = (math.cos(a) / max(w, 1e-3), ny * math.sin(a) / max(h, 1e-3), nz * math.sin(a) / max(h, 1e-3))
            ring.append(crest.corner(p, n, (j / M, f * 4.0)))
        rows.append(ring)
    for k in range(N):
        for j in range(M):
            a, b, c, d = rows[k][j], rows[k][j + 1], rows[k + 1][j], rows[k + 1][j + 1]
            crest.tri(a, c, b)
            crest.tri(b, c, d)
    for k, sign in ((0, -1), (N, 1)):                        # (the two ends closed)
        f = k / N
        phi = math.radians(28 + 130 * f)
        mid = crest.corner((0.0, ry * math.cos(phi), rz * math.sin(phi)), (0.0, -math.sin(phi) * sign, math.cos(phi) * sign), (0.5, f * 4.0))
        for j in range(M):
            crest.tri(mid, rows[k][j], rows[k][j + 1])
    return [cap.shape(), crest.shape()]


def mahiole_inside(z):
    """How far out the cap's inside is at height z over the band; it ends at the band, as the sun hat's crown does."""
    if z > MAHIOLE['top'] - MAHIOLE['thick']:
        return None
    return hats._dome(z + MAHIOLE['thick']) - MAHIOLE['thick']


def mahiole_clearance(head):
    """The least room between the game's head and the cap's inside (as hats.clearance)."""
    c, s = math.cos(hats.TILT), math.sin(hats.TILT)
    least = None
    for x, y, z in head:
        x, y, z = x - hats.FIT[0], y - hats.FIT[1], z - hats.FIT[2]
        y, z = y * c - z * s, y * s + z * c
        if z < 0:
            continue
        r_in = mahiole_inside(z)
        r = math.hypot(x, y / hats.BAND_E)
        room = (r_in - r) if r_in is not None else -1.0
        least = room if least is None else min(least, room)
    return least


def mahiole_files(mod):
    shapes = mahiole_shapes()
    worn = hats._moved(shapes, hats.TILT, hats.FIT)
    low = min(sh['p'][k] for sh in shapes for k in range(2, len(sh['p']), 3))
    go = hats._moved(shapes, 0.0, (0.0, 0.0, -low))
    worn_path, go_path = hats.MESH % (mod, 'mahiole'), hats.MESH % (mod, 'mahiole_go')
    out = {worn_path: nifmake.build_worn('FOLabMahiole', worn),
           go_path: nifmake.build_dropped('FOLabMahioleGO', go, mass=0.8, material='cloth')}
    for (diffuse, normal), key in zip(mahiole_textures(), ('mahiole_red', 'mahiole_yellow')):
        out[hats.TEX % key], out[hats.NORMAL % key] = diffuse, normal
    pts = [(sh['p'][k], sh['p'][k + 1], sh['p'][k + 2]) for sh in go for k in range(0, len(sh['p']), 3)]
    box = [int(math.floor(min(q[k] for q in pts))) for k in range(3)] + [int(math.ceil(max(q[k] for q in pts))) for k in range(3)]
    return {'files': out, 'worn_path': worn_path, 'go_path': go_path, 'box': box, 'shapes': worn, 'go_shapes': go}


def mahiole_record(gd, made):
    rec = hats.hat_record(gd, 'boater', made)                # (a copy of the Rattan Cowboy Hat, FOLab's models)
    recordio.set_field(rec, 'EDID', 'FOLabMahiole')
    recordio.set_field(rec, 'FULL', 'Mahiole')
    rec['subs'] = [s for s in rec['subs'] if s['tag'] != 'EITM']
    return rec


# ---------- into a mod ----------

def ops(gd, pr, keys=None):
    """(ops, report): every armour (or `keys`) and the mahiole, their files among the mod's own; each armour WHO names
    put in that list (copies of its first entry). Refused if the mod has any of them already."""
    import json
    import peopledress
    keys = list(keys or ARMOURS)
    have = {(recordio.field(r, 'EDID') or '').lower(): k for k, r in pr.records.items()}
    for k in keys:
        if ARMOURS[k][1].lower() in have:
            raise ValueError('The mod already has %s (Undo the armour first to make it again).' % ARMOURS[k][1])
    if 'folabmahiole' in have:
        raise ValueError('The mod already has FOLabMahiole.')
    root = library.assets_dir(pr)
    slug = library.slug(pr.name)
    made_keys = peopledress._Keys(pr)
    rep = {'armour': {}, 'worn_by': {}, 'unworn': []}
    for k in keys:
        models = files(gd, pr, k)
        rk = made_keys.add(armour_record(gd, k, models))
        rep['armour'][k] = {'key': rk, 'edid': ARMOURS[k][1], 'name': ARMOURS[k][2], 'for': ARMOURS[k][3], 'models': models}
    m = mahiole_files(slug)
    for path, data in m['files'].items():
        library._put(root, path, data)
    rep['armour']['mahiole'] = {'key': made_keys.add(mahiole_record(gd, m)), 'edid': 'FOLabMahiole', 'name': 'Mahiole',
                                'for': 'the Kahuna\'s guard', 'models': {'MODL': m['worn_path'], 'MOD2': m['go_path']}}
    out = list(made_keys.ops)
    for k, info in rep['armour'].items():
        if k not in WHO:
            rep['unworn'].append('%s (%s: no people of the mod\'s own yet)' % (info['name'], info['for']))
            continue
        list_edid, n = WHO[k]
        lk = have.get(list_edid.lower())
        if not lk:
            rep['unworn'].append('%s (%s: the mod has no %s)' % (info['name'], info['for'], list_edid))
            continue
        lst = json.loads(json.dumps(pr.records[lk]))
        rows = [s for s in lst['subs'] if s['tag'] == 'LVLO']
        at = lst['subs'].index(rows[-1]) + 1
        for _ in range(n):
            s = json.loads(json.dumps(rows[0]))
            for f in s['fields']:
                if f.get('code') == 'F':
                    f['value'] = info['key']
            lst['subs'].insert(at, s)
        out.append({'op': 'record', 'key': lk, 'record': lst})
        rep['worn_by'][info['name']] = {'list': list_edid, 'entries': n, 'of': len(rows) + n}
    return out, rep


def apply(server, keys=None):
    """ops as one Undo; checks the keys."""
    pr = server.PR
    first = pr.next_id
    o, rep = ops(server.GD, pr, keys)
    out = server.edit('Armour and dress for Waikiki\'s people', o)
    made = list(out.get('made') or []) if isinstance(out, dict) else []
    want = ['+%06X' % (first + n) for n in range(sum(1 for x in o if x['op'] == 'record_new'))]
    if made[:len(want)] != want:
        raise RuntimeError('the armour got other keys than planned (%s vs %s): undo this step' % (made[:2], want[:2]))
    return rep
