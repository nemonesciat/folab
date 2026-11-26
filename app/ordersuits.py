"""The Order's suits in the Missouri's colours (the user, 25 Nov 2026: the Captain's Guard a hereditary order in power armour
"passed down from the original crew of the ship"; the Workshop: "the game's T-45d, retextured with the Missouri's marks; a
painted hull number"). After missouriguns (its eight FOLabOrderSuit<Family> suits and helmets).

- **The look:** polished knight's armour (the user: "even lighter ... the illusion of polished knight's armor ... some kind of
  trim"): the game's T-45d pictures in a pale Navy grey, each pixel's own light kept but evened (`SMOOTH`: light wear), the
  plates' ridges lit from the normal map (`ridges_of`), a gold edging `TRIM` wide inside every plate's border (`plates_of`: the
  model's own triangles laid on the picture; `trim_of`), the normal map's alpha (the game's shine) raised (`SHINE`); the ship's hull number **63** in navy edged gold on the breastplate as **BB-63** (MISSOURI under it was cut by the plate's edge and seam), a gold anchor on the
  shoulder plates (symmetric: the picture serves both shoulders). The helmet in the same grey.
- **Where on the picture:** the breastplate and shoulders were found from the model's own triangles (facing forward, +y, at chest
  height; facing out above the arm): `BACK` (the breastplate: named before the game's +y front was seen), `SHOULDER`, at 1024.
- **Files:** the pictures and the retextured models (nifwrite: only the texture paths change) among the mod's own files;
  `ops` points every suit and helmet record of the Order at them.

Needs numpy and PIL: a build step from the developer's Python (DEV_ONLY in packaging, as armourset).

    files(gd, pr)    {tag: model path} for the suit and the helmet, written among the mod's files
    ops(gd, pr)      (ops, report): the records' models changed, one Undo
    pictures(gd)     (body before, body after, helmet after) as PIL images, for a look first
"""
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

import dds
import library
import recordio

B = chr(92)
BODY_TEX = 'textures' + B + 'armor' + B + 'powerarmor' + B + 'PowerArmorBody.dds'
HELMET_TEX = 'textures' + B + 'armor' + B + 'headgear' + B + 'PowerArmorHelmet.dds'
SUIT, HELMET = 'ArmorPowerT45d', 'ArmorPowerT45dHelmet'
HAZE = np.array([150.0, 166.0, 190.0])      # (a pale Navy grey tending to polished steel)
WHITE, GOLD, SHADOW = (236, 234, 226), (240, 196, 72), (24, 24, 26)
BACK = (198, 428, 132)                      # (the breastplate's flat upper plate: its middle and the width BB-63 fills, at 1024)
SHOULDER = (695, 314, 104)                   # (the shoulder plate's outer face: the anchor's middle and size)
MODEL_TAGS = ('MODL', 'MOD2', 'MOD3', 'MOD4')
TRIM = 7                                    # (the gold edging's width inside each plate's border, at 1024)
# The plates that are edged, each by a point inside its piece of the body picture (at 1024): only the great plates, as on
# parade armour (every piece edged, seams and straps too, read as a gold cage). Read off the picture's pieces by eye.
PLATES = {'breastplate': (114, 432), 'pauldron': (694, 262), 'upper arm': (870, 245), 'back plate': (805, 523),
          'greaves': (205, 939), 'knee': (751, 751), 'boot': (63, 745)}
NAVY = (26, 40, 78)
SHINE, TRIM_SHINE = 165, 235                # (the normal map's alpha: how much the plates and the trim shine)
SMOOTH = 0.45                               # (how much of the old paint's grime and scratches is kept)


def _picture(gd, path):
    w, h, px = dds.decode(gd.read_file(path), want=4096)[:3]
    return Image.frombytes('RGBA', (w, h), bytes(px))


def haze(im, strength=0.9, smooth=SMOOTH, ridges=None):
    """The picture in pale Navy grey, each pixel's own light kept but evened (its spread against the picture's mean cut to
    `smooth`: polished, light wear), and the plates' ridges lit (`ridges`, 0..1 a pixel)."""
    a = np.asarray(im.convert('RGBA')).astype(np.float32)
    rgb, alpha = a[..., :3], a[..., 3:]
    lum = rgb @ np.array([0.299, 0.587, 0.114])
    rel = np.clip(lum / max(1.0, float(lum.mean())), 0, 4)
    rel = 1 + (rel - 1) * smooth
    grey = np.power(np.clip(rel, 0.05, 4), 0.8)[..., None] * HAZE[None, None, :]
    if ridges is not None:
        grey = grey + ridges[..., None] * np.array([48.0, 50.0, 54.0])[None, None, :]
    out = rgb * (1 - strength) + grey * strength
    return Image.fromarray(np.concatenate([np.clip(out, 0, 255), alpha], -1).astype(np.uint8), 'RGBA')


def _normal(gd, path):
    w, h, px = dds.decode(gd.read_file(path[:-4] + '_n.dds'), want=4096)[:3]
    return np.frombuffer(bytes(px), np.uint8).reshape(h, w, 4).copy()


def ridges_of(nrm):
    """Where the plates bend (the normal map leaning away from flat), 0..1, softened: highlights along ridges and bevels."""
    from scipy import ndimage
    n = nrm[..., :3].astype(np.float32) / 127.5 - 1
    lean = np.sqrt(n[..., 0] ** 2 + n[..., 1] ** 2)
    r = np.clip((lean - 0.12) / 0.4, 0, 1)
    return ndimage.gaussian_filter(r, 1.2)


def plates_of(gd, model, tex, size):
    """The model's pieces on the picture (size x size): every triangle of `model` drawn with `tex`, laid out in its picture."""
    import math
    import nif
    mask = Image.new('L', (size, size), 0)
    d = ImageDraw.Draw(mask)
    for sh in nif.mesh_from_nif(gd.read_file(model), placed=False):
        if sh['tex'].lower() != tex.lower():
            continue
        uv, idx = sh['uv'], sh['i']
        for t in range(0, len(idx), 3):
            us = [uv[2 * k] for k in idx[t:t + 3]]
            vs = [uv[2 * k + 1] for k in idx[t:t + 3]]
            if max(us) - min(us) > 0.5 or max(vs) - min(vs) > 0.5:
                continue
            fu, fv = math.floor(min(us)), math.floor(min(vs))
            d.polygon([((u - fu) * size, (v - fv) * size) for u, v in zip(us, vs)], fill=255)
    return np.asarray(mask) > 0


def trim_of(pieces, size, seeds):
    """The gold edging, 0..1 a pixel: a band `TRIM` wide inside the border of each piece holding one of `seeds` (points at
    1024; None: the biggest piece)."""
    from scipy import ndimage
    k = size / 1024.0
    lab, n = ndimage.label(pieces)
    if seeds is None:
        areas = ndimage.sum(pieces, lab, range(1, n + 1))
        chosen = [1 + int(np.argmax(areas))]
    else:
        chosen = [int(lab[int(y * k), int(x * k)]) for x, y in seeds]
        chosen = [c for c in chosen if c]
    plates = np.isin(lab, chosen)
    inner = ndimage.binary_erosion(plates, iterations=max(2, int(round(TRIM * k))))
    return ndimage.gaussian_filter((plates & ~inner).astype(np.float32), 0.7 * max(1.0, k))


def gild(im, trim):
    """The edging laid on: brass gold with the plate's own light, a dark line on its inner side."""
    from scipy import ndimage
    a = np.asarray(im).astype(np.float32)
    lum = a[..., :3] @ np.array([0.299, 0.587, 0.114])
    rel = np.clip(lum / max(1.0, float(lum.mean())), 0.6, 1.4)
    gold = np.array(GOLD, np.float32)[None, None, :] * rel[..., None]
    line = np.clip(ndimage.binary_dilation(trim > 0.5, iterations=2).astype(np.float32) - (trim > 0.3), 0, 1) * 0.45
    a[..., :3] = a[..., :3] * (1 - line[..., None]) + np.array(SHADOW, np.float32) * line[..., None]
    a[..., :3] = a[..., :3] * (1 - trim[..., None]) + gold * trim[..., None]
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGBA')


def shine(nrm, trim):
    """The normal map with its alpha (the game's shine) raised: polished plates, the trim brightest."""
    out = nrm.copy()
    al = np.maximum(out[..., 3].astype(np.float32), SHINE)
    out[..., 3] = np.clip(al * (1 - trim) + TRIM_SHINE * trim, 0, 255).astype(np.uint8)
    return out


def _fit(a, size):
    if a.shape[0] == size:
        return a
    return np.asarray(Image.fromarray((a * 255).astype(np.uint8)).resize((size, size), Image.BILINEAR)).astype(np.float32) / 255


def _trim(gd, edid, tex, size):
    seeds = list(PLATES.values()) if edid == SUIT else None          # (the helmet: its shell's rim)
    return trim_of(plates_of(gd, _models(gd, edid)['MODL'], tex, size), size, seeds)


def normals(gd):
    """(body, helmet) normal maps with the polished shine, as RGBA arrays."""
    out = []
    for edid, tex in ((SUIT, BODY_TEX), (HELMET, HELMET_TEX)):
        nrm = _normal(gd, tex)
        out.append(shine(nrm, _trim(gd, edid, tex, nrm.shape[0])))
    return out


def _font(size):
    for name in ('impact.ttf', 'arialbd.ttf', 'arial.ttf'):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _stamp(base, draw_fn, scale):
    """A mark drawn on a layer of its own, worn with the plate: its alpha roughened and the plate's light laid over it."""
    w, h = base.size
    layer = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    draw_fn(ImageDraw.Draw(layer))
    rng = np.random.default_rng(63)
    a = np.asarray(layer).astype(np.float32)
    wear = rng.random((h, w)) * 255
    wear = np.asarray(Image.fromarray(wear.astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.2))).astype(np.float32)
    a[..., 3] *= np.clip((wear - 40) / 120, 0.55, 1.0)          # (paint worn thin in places)
    b = np.asarray(base).astype(np.float32)
    lum = (b[..., :3] @ np.array([0.299, 0.587, 0.114])) / max(1.0, float((b[..., :3] @ np.array([0.299, 0.587, 0.114])).mean()))
    a[..., :3] *= np.clip(lum, 0.8, 1.15)[..., None]             # (the plate's shading through the paint, gently)
    al = a[..., 3:] / 255
    b[..., :3] = b[..., :3] * (1 - al) + a[..., :3] * al
    return Image.fromarray(np.clip(b, 0, 255).astype(np.uint8), 'RGBA')


def body(gd):
    im = _picture(gd, BODY_TEX)
    s = im.size[0] / 1024.0
    out = haze(im, ridges=_fit(ridges_of(_normal(gd, BODY_TEX)), im.size[0]))
    out = gild(out, _trim(gd, SUIT, BODY_TEX, im.size[0]))
    x, y, hgt = (v * s for v in BACK)

    def number(d):
        # BB-63 alone, sized to the flat plate's width (MISSOURI under it ran onto the ribbed plate and over the seam)
        size = int(hgt)
        while size > 8:
            f = _font(size)
            l, t, r, b = d.textbbox((0, 0), 'BB-63', font=f)
            if r - l <= hgt:
                break
            size -= 2
        d.text((x, y), 'BB-63', font=f, fill=NAVY + (255,), anchor='mm',          # (navy, edged in gold: reads on pale steel)
               stroke_width=max(2, int(3 * s)), stroke_fill=GOLD + (255,))
    out = _stamp(out, number, s)
    ax, ay, size = (v * s for v in SHOULDER)

    def anchor(d):
        r = size / 2
        for col, lw in ((SHADOW + (255,), max(3, int(size * 0.17))), (GOLD + (255,), max(2, int(size * 0.11)))):
            d.ellipse([ax - r * 0.2, ay - r, ax + r * 0.2, ay - r * 0.62], outline=col, width=lw)        # (the ring)
            d.line([ax, ay - r * 0.62, ax, ay + r * 0.9], fill=col, width=lw)                            # (the shank)
            d.line([ax - r * 0.5, ay - r * 0.42, ax + r * 0.5, ay - r * 0.42], fill=col, width=lw)       # (the stock)
            d.arc([ax - r * 0.85, ay - r * 0.1, ax + r * 0.85, ay + r * 0.95], 20, 160, fill=col, width=lw)   # (the arms)
            g = 1.25 if col[0] == SHADOW[0] else 1.0
            for sx in (-1, 1):
                d.polygon([(ax + sx * r * 0.88 * g, ay + r * 0.38), (ax + sx * r * 0.6, ay + r * 0.52), (ax + sx * r * 0.97 * g, ay + r * 0.66)], fill=col)
    return _stamp(out, anchor, s)


def helmet(gd):
    im = _picture(gd, HELMET_TEX)
    out = haze(im, ridges=_fit(ridges_of(_normal(gd, HELMET_TEX)), im.size[0]))
    return gild(out, _trim(gd, HELMET, HELMET_TEX, im.size[0]))


def pictures(gd):
    return _picture(gd, BODY_TEX), body(gd), helmet(gd)


def _models(gd, edid):
    f = next(f for f, (_i, r) in gd.forms.items() if r.tag == 'ARMO' and gd.edid(f) == edid)
    rec = recordio.load(gd, f)
    return {t: 'meshes' + B + recordio.field(rec, t) for t in MODEL_TAGS if recordio.field(rec, t)}


def files(gd, pr):
    """The two pictures and the retextured models among the mod's own files: {'suit': {tag: path}, 'helmet': {tag: path}}."""
    import nifwrite
    root = library.assets_dir(pr)
    slug = library.slug(pr.name)
    pics = {}
    for key, im, src in (('body', body(gd), BODY_TEX), ('helmet', helmet(gd), HELMET_TEX)):
        rel = 'textures' + B + 'folab' + B + slug + B + 'order' + B + 'missouri_%s.dds' % key
        library._put(root, rel, dds.compress(dds.encode(im.size[0], im.size[1], im.convert('RGBA').tobytes(), cut=None)))
        pics[src] = rel
    for key, nrm, src in zip(('body', 'helmet'), normals(gd), (BODY_TEX, HELMET_TEX)):
        rel = 'textures' + B + 'folab' + B + slug + B + 'order' + B + 'missouri_%s_n.dds' % key
        library._put(root, rel, dds.compress(dds.encode(nrm.shape[1], nrm.shape[0], nrm.tobytes(), cut=None)))
        pics[src[:-4] + '_n.dds'] = rel
    out = {}
    for which, edid in (('suit', SUIT), ('helmet', HELMET)):
        out[which] = {}
        for tag, m in _models(gd, edid).items():
            data = gd.read_file(m)
            changes = {k: v for k, v in pics.items()}
            new = nifwrite.retexture(data, changes)
            wrong = nifwrite.prove(data, changes)
            if wrong:
                raise ValueError('%s %s: %s' % (which, tag, '; '.join(wrong)))
            rel = 'meshes' + B + 'folab' + B + slug + B + 'order' + B + 'missouri_%s_%s.nif' % (which, tag.lower())
            library._put(root, rel, new)
            out[which][tag] = rel
    return out


def ops(gd, pr, P=None):
    """(ops, report): every suit and helmet of the Order (FOLabOrderSuit*) pointed at the Missouri's models."""
    import copy
    recs = {k: r for k, r in pr.records.items() if r.get('type') == 'ARMO' and (recordio.field(r, 'EDID') or '').startswith('FOLabOrderSuit')}
    if not recs:
        raise ValueError("the Order's suits (missouriguns) first")
    made = files(gd, pr)
    out = []
    for k, r in sorted(recs.items()):
        which = 'helmet' if recordio.field(r, 'EDID').endswith('Helmet') else 'suit'
        new = copy.deepcopy(r)
        for s in new['subs']:
            if s['tag'] in made[which]:
                s['value'] = made[which][s['tag']][7:]          # (models are named from meshes\)
        out.append({'op': 'record', 'key': k, 'record': new})
    return out, {'made': sorted(recordio.field(r, 'EDID') for r in recs.values()), 'models': made}


LABEL = "The Order's suits in the Missouri's colours"


def plan(gd, pr):
    n = sum(1 for r in pr.records.values() if r.get('type') == 'ARMO' and (recordio.field(r, 'EDID') or '').startswith('FOLabOrderSuit'))
    return {'rows': [{'suits and helmets': n}], 'skipped': [] if n else ["the Order's suits not in the mod"]}
