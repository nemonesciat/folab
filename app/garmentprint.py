"""Prints painted on the game's own clothes: a hibiscus print laid over a garment's cloth in its texture, the game's folds,
seams and buttons kept, everything else in the picture (trousers, shoes, belt) as it was. FOLab's own pictures, so a mod
that wears them can be handed round.

The garment so far is the game's Pre-War Spring outfit (`Armor\\1950StyleCasual02`): for a man a button-up shirt over
trousers (OutfitM.dds), for a woman a dress (OutfitF.dds), both with a worn ("Old") variant the game draws for its dirty
copies (OutfitM02Old / OutfitF02Old, same layout). What is cloth comes from the clean picture (`GARMENTS`): inside the
garment's triangles, where the uv says so (`keep_uv`: the man's shirt panels and sleeves) or where the colour is the
cloth's (`cloth`), never below `FEET` (the shoes share the picture: the V between the man's shirt fronts is their leather,
which was printed until the user saw it, 21 Nov 2026); the worn picture is painted through the same mask.

The shading is the picture's own light with the old pattern taken out: the game's shirt is checked in thin light lines, a
print over that read as a "Hawaiian flannel" (the user, 20 Nov 2026). So the broad light is a median of the picture, only
detail darker than it (seams, buttons, folds' creases) is added back, and that light is taken against the light round it,
so a panel the game painted dark (the neckerchief) takes the print as brightly as the rest.

Needs numpy, PIL and scipy, which FOLab.exe's own Python hasn't: run from the developer's Python (a build step, as
peopledress's rehearsal is). Before a button calls it, it wants writing in the standard library."""
import math
import random

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

import dds
import nif

B = chr(92)
FOLDER = 'meshes\\Armor\\1950StyleCasual02\\'
TEXTURES = 'textures\\armor\\1950stylecasual02\\'
# garment -> (mesh, clean picture, worn picture, normal map, worn normal map)
GARMENTS = {
    'm': ('OutfitM.NIF', 'OutfitM.dds', 'OutfitM02Old.dds', 'OutfitM_n.dds', 'OutfitMOld_n.dds'),
    'f': ('OutfitF.nif', 'OutfitF.dds', 'OutfitF02Old.dds', 'OutfitF_n.dds', 'OutfitFOld_n.dds'),
}
YELLOW = (250, 220, 90)
FEET = 20                   # (a triangle lower than this, its middle's height in the mesh, is a shoe or a trouser cuff)
TILE = 200                  # (pixels a repeat of the print, on a 1024 picture: about five flowers across a shirt's front)


def print_tile(ground, flower, leaf, seed, size=TILE):
    """One repeat of a hibiscus print, seamless: leaves under five-petalled flowers with a yellow eye and stamen."""
    rnd = random.Random(seed)
    big = Image.new('RGB', (size * 3, size * 3), tuple(ground))
    d = ImageDraw.Draw(big)
    spots = [(rnd.uniform(0, size), rnd.uniform(0, size), rnd.uniform(0, math.tau), rnd.uniform(0.9, 1.15)) for _ in range(9)]
    r0 = size * 0.11
    for layer in ('leaf', 'flower'):
        for sx, sy, a0, k in spots:
            r = r0 * k
            for ox in (0, size, 2 * size):
                for oy in (0, size, 2 * size):
                    x, y = sx + ox, sy + oy
                    if layer == 'leaf':
                        for j in range(3):
                            a = a0 + 2.1 * j + 0.4
                            lx, ly = x + math.cos(a) * r * 1.5, y + math.sin(a) * r * 1.5
                            pts = [(lx + math.cos(a) * r * 0.95 * math.cos(t) - math.sin(a) * r * 0.42 * math.sin(t),
                                    ly + math.sin(a) * r * 0.95 * math.cos(t) + math.cos(a) * r * 0.42 * math.sin(t))
                                   for t in [n * math.tau / 16 for n in range(16)]]
                            d.polygon(pts, fill=tuple(leaf))
                    else:
                        for j in range(5):
                            a = a0 + math.tau * j / 5
                            fx, fy = x + math.cos(a) * r * 0.6, y + math.sin(a) * r * 0.6
                            d.ellipse((fx - r * 0.62, fy - r * 0.62, fx + r * 0.62, fy + r * 0.62), fill=tuple(flower))
                        d.ellipse((x - r * 0.25, y - r * 0.25, x + r * 0.25, y + r * 0.25), fill=YELLOW)
                        d.line((x, y, x + math.cos(a0) * r * 0.9, y + math.sin(a0) * r * 0.9), fill=(250, 230, 120), width=2)
    return big.crop((size, size, 2 * size, 2 * size))


def _picture(gd, rel):
    w, h, px = dds.decode(gd.read_file(rel), want=1024)[:3]
    return Image.frombytes('RGBA', (w, h), bytes(px)).convert('RGB')


def _shapes(gd, garment, tex):
    mesh = FOLDER + GARMENTS[garment][0]
    return [s for s in nif.mesh_from_nif(gd.read_file(mesh), placed=False) if s['tex'].lower() == (TEXTURES + tex).lower()]


def _keep_uv(garment, u, v):
    if garment == 'm':
        return (v > 0.53 and u < 0.89) or (u < 0.32 and v < 0.5)        # front, back, cuffs; the sleeves
    return False                                                        # (the dress: by its colour alone)


def _cloth(garment, rgb):
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    if garment == 'm':
        return r - g > 28                                               # the shirt's red
    import scipy.ndimage as nd
    yy = np.mgrid[0:r.shape[0], 0:r.shape[1]][0] / float(r.shape[0])
    m = (r - b > 18) & (r > 95) & (yy < 0.80)                          # the dress's pink, above the shoes
    lab, n = nd.label(nd.binary_closing(m, iterations=3))
    sizes = nd.sum(m, lab, range(1, n + 1))
    big = [k + 1 for k, s in enumerate(sizes) if s > 6000 * (r.shape[0] / 1024.0) ** 2]
    return m & np.isin(lab, big)                                        # (only the big pieces: never a sole or a button)


def cloth_mask(gd, garment):
    """0-255: where the garment's print goes, from its clean picture."""
    tex = GARMENTS[garment][1]
    orig = _picture(gd, TEXTURES + tex)
    w, h = orig.size
    tri = Image.new('L', (w, h), 0)
    md = ImageDraw.Draw(tri)
    for s in _shapes(gd, garment, tex):
        uv, idx, P = s['uv'], s['i'], s['p']
        for t in range(0, len(idx), 3):
            if sum(P[3 * idx[t + k] + 2] for k in range(3)) / 3 < FEET:
                continue                                                # (the shoes: never printed)
            pts = [(uv[2 * idx[t + k]], uv[2 * idx[t + k] + 1]) for k in range(3)]
            cu, cv = sum(p[0] for p in pts) / 3, sum(p[1] for p in pts) / 3
            md.polygon([(u * w, v * h) for u, v in pts], fill=255 if _keep_uv(garment, cu, cv) else 128)
    T = np.asarray(tri)
    m = ((T == 255) | ((T > 0) & _cloth(garment, np.asarray(orig, dtype=np.int16)))).astype(np.uint8) * 255
    return Image.fromarray(m, 'L').filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.GaussianBlur(1.0))


def _wide(a, r=20):
    """A broad blur (three box passes) of a float picture, edges held."""
    for _ in range(3):
        for ax in (0, 1):
            c = np.cumsum(np.pad(a, [(r + 1, r) if k == ax else (0, 0) for k in (0, 1)], mode='edge'), axis=ax)
            a = (np.take(c, range(2 * r + 1, c.shape[ax]), axis=ax) - np.take(c, range(0, c.shape[ax] - 2 * r - 1), axis=ax)) / (2 * r + 1)
    return a


def shading(base, mask):
    """The picture's light on the cloth, about 1 where it's lit as usual: the old pattern out, folds and seams kept."""
    lum = base.convert('L')
    broad = lum.filter(ImageFilter.MedianFilter(9)).filter(ImageFilter.GaussianBlur(2))
    dark = ImageChops.subtract(broad, lum).point(lambda v: 0 if v < 26 else min(255, int((v - 26) * 1.6)))
    L = np.asarray(ImageChops.subtract(broad, dark), dtype=np.float32)
    M = np.asarray(mask, dtype=np.float32) / 255.0
    around = _wide(L * M) / np.maximum(_wide(M), 1e-3)
    return np.clip(L / np.maximum(around, 1.0), 0.45, 1.5)


def paint(gd, garment, style, worn=False, seed=1, mask=None):
    """The garment's picture with the print over its cloth: a PIL RGB image. style: (ground, flower, leaf) colours."""
    tex = GARMENTS[garment][2 if worn else 1]
    return printed(_picture(gd, TEXTURES + tex), mask if mask is not None else cloth_mask(gd, garment), style, worn, seed)


def printed(base, mask, style, worn=False, seed=1):
    """A picture with the print laid over it through mask (0-255), the picture's own light kept."""
    if mask.size != base.size:
        mask = mask.resize(base.size)
    w, h = base.size
    tile = print_tile(*style, seed=seed, size=max(32, TILE * w // 1024))
    pat = Image.new('RGB', (w, h))
    for x in range(0, w, tile.size[0]):
        for y in range(0, h, tile.size[1]):
            pat.paste(tile, (x, y))
    lit = np.asarray(pat, dtype=np.float32) * shading(base, mask)[..., None] * (0.82 if worn else 0.98)
    if worn:                                                            # (the worn cloth's own stains and fading show through)
        lit = lit * 0.75 + np.asarray(base, dtype=np.float32) * 0.25 * (np.asarray(pat, dtype=np.float32).mean() / max(1.0, np.asarray(base, dtype=np.float32).mean()))
    lit = Image.fromarray(np.clip(lit, 0, 255).astype(np.uint8), 'RGB')
    return Image.composite(lit, base, mask)


# Board shorts (the user, 21 Nov 2026: "some variants with shorts", then "beach shorts and not assless chaps ... they
# almost seem risque"): a man's only, bare-chested in the Powder Gang's simple outfit, whose shorts reach the knee (Honest
# Hearts' Sorrows shorts were tried first: whole all round but cut as high as briefs). Its shorts are cut-down trousers
# panels in powdergang02.dds, apart from the belt, the bandolier's strap and the boots (powdergang01.dds): only the panels
# below the belt are printed. A woman wears her printed dress in the same record (no woman's version has shorts).
SHORTS = {'folder': 'meshes\\armor\\powdergang\\', 'textures': 'textures\\armor\\powdergang\\', 'picture': 'powdergang02.dds',
          'meshes': {'m': 'powdergang04.NIF', 'go': 'powdergangv1_GO.NIF'}}
HIPS = (20, 68)             # (a worn triangle with its middle between these heights is the shorts; the belt is over it)
STRAP_U = 0.17              # (left of this in the picture: the bandolier's strap and pouches, never printed)


def shorts_shapes(gd, part):
    tex = (SHORTS['textures'] + SHORTS['picture']).lower()
    data = gd.read_file(SHORTS['folder'] + SHORTS['meshes'][part])
    return [s for s in nif.mesh_from_nif(data, placed=False) if s['tex'].lower() == tex]


def shorts_mask(gd):
    """0-255: where the shorts' print goes on their picture (the folded copy on the ground lies on the same panels)."""
    orig = _picture(gd, SHORTS['textures'] + SHORTS['picture'])
    w, h = orig.size
    tri = Image.new('L', (w, h), 0)
    md = ImageDraw.Draw(tri)
    for s in shorts_shapes(gd, 'm'):
        uv, idx, P = s['uv'], s['i'], s['p']
        for t in range(0, len(idx), 3):
            ks = [idx[t + k] for k in range(3)]
            if HIPS[0] <= sum(P[3 * k + 2] for k in ks) / 3 <= HIPS[1] and sum(uv[2 * k] for k in ks) / 3 > STRAP_U:
                md.polygon([(uv[2 * k] * w, uv[2 * k + 1] * h) for k in ks], fill=255)
    return tri.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.GaussianBlur(1.0))


def paint_shorts(gd, style, worn=False, seed=1, mask=None):
    base = _picture(gd, SHORTS['textures'] + SHORTS['picture'])
    return printed(base, mask if mask is not None else shorts_mask(gd), style, worn, seed)


def dds_of(im):
    """A picture as the game's texture: DXT1 with its smaller copies."""
    rgba = im.convert('RGBA')
    return dds.compress(dds.encode(rgba.size[0], rgba.size[1], rgba.tobytes()))
