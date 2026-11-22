"""A vault's number where the game shows one on its gear door: the user chose Vault 50 for Ka'au's Vault (22 Nov 2026).

The game's gear doors take their numbers from one sheet of numbers (textures\\dungeons\\vaultruined\\vault11ruinednumbers.dds,
read 22 Nov 2026): tall hatch strips across the top (108, 11, 87, 92, 01 to 05) and round plates below (11, 3, 112, 87, 92 and
a blank one). Vault 22's gear door (VGearDoorR22, the one vaultgate stands at the crater) shows the plate at u 0.32-0.51,
v 0.76-0.94: the "92". So the crater's door read 92.

`sheet(game, number)` is that sheet with the 92 plate showing `number` instead: its old figures taken off with the blank
plate's face, and the new ones drawn in the game's own stencil figures (the hatch strips' 0 to 9 where the sheet has them,
`DIGITS_AT`) scaled to the plate's figures and coloured from the old figures' own rust. Plain Python (dds.decode/encode).
`ops(game, pr, number, gear_ref)` puts the sheet and a copy of the door's model using it among the mod's own files, a DOOR
of the mod's own on that model, and swaps the crater's gear door to it (its link and lock stay). Not seen in game."""
import json
import os

import dds
import library
import nifwrite
import recordio

BS = chr(92)
SHEET = 'textures' + BS + 'dungeons' + BS + 'vaultruined' + BS + 'vault11ruinednumbers.dds'
GEAR = 'VGearDoorR22'
SIZE = 1024
PLATE = (331, 778, 520, 965)            # (the 92 plate: the door's u 0.323-0.508, v 0.76-0.942)
BLANK_SHIFT = 287                       # (the blank plate, the same distance along as the plates are apart)
# where the sheet has each figure in the hatch strips' stencil (left, top, right, bottom on the 1024 sheet; found by
# `_figures` in each strip's number band): '0','5' from the "05" strip, '1','2','3','4' from "01" ... "04", '8','7' from
# "87", '9' from "92"
STRIPS = {'05': 838, '01': 466, '02': 559, '3': 652, '04': 745, '87': 280, '92': 373, '108': 94}
BAND = (150, 205)                       # (the strips' number band, top and bottom)
STRIP_W = 88


def _px(img, x, y):
    i = (y * SIZE + x) * 4
    return img[i], img[i + 1], img[i + 2], img[i + 3]


def _figure_mask(img, x0, x1, y0, y1):
    """The stencil figures in a box of a hatch strip: grey-blue on rust orange. {(x, y)}"""
    out = set()
    for y in range(y0, y1):
        for x in range(x0, x1):
            r, g, b, _a = _px(img, x, y)
            if b >= r - 12 and r < 150:
                out.add((x, y))
    return out


def _split(mask):
    """Figures in a mask, left to right: [(x0, y0, x1, y1)] by the empty columns between them."""
    if not mask:
        return []
    cols = sorted({x for x, _y in mask})
    runs, start, last = [], cols[0], cols[0]
    for c in cols[1:]:
        if c > last + 2:
            runs.append((start, last))
            start = c
        last = c
    runs.append((start, last))
    out = []
    for a, b in runs:
        ys = [y for x, y in mask if a <= x <= b]
        if b - a >= 3 and len(ys) > 20:
            out.append((a, min(ys), b + 1, max(ys) + 1))
    return out


def figures(img):
    """{figure: (mask, box)} of the stencil figures the hatch strips have."""
    out = {}
    for text, x in STRIPS.items():
        m = _figure_mask(img, x, x + STRIP_W, BAND[0], BAND[1])
        boxes = _split(m)
        if len(boxes) != len(text):
            continue
        for ch, box in zip(text, boxes):
            if ch not in out:
                out[ch] = ({(px, py) for px, py in m if box[0] <= px < box[2] and box[1] <= py < box[3]}, box)
    return out


def sheet(game, number):
    """The numbers sheet as DDS bytes, its 92 plate showing `number` (a string of figures the strips have)."""
    w, h, px = dds.decode(game.read_file(SHEET), SIZE)[:3]
    if (w, h) != (SIZE, SIZE):
        raise ValueError('The game\'s numbers sheet isn\'t %d square' % SIZE)
    img = bytearray(px)
    figs = figures(img)
    missing = [c for c in number if c not in figs]
    if missing:
        raise ValueError('The game\'s sheet has no stencil figure %s to draw with' % ', '.join(missing))
    x0, y0, x1, y1 = PLATE
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
    # the old figures: rust on the plate's dark face, near its middle
    old = [(x, y) for y in range(y0, y1) for x in range(x0, x1)
           if (x - cx) ** 2 + (y - cy) ** 2 < 82 ** 2 and _px(img, x, y)[0] > _px(img, x, y)[2] + 35 and _px(img, x, y)[0] > 70]
    if not old:
        raise ValueError('No figures found on the plate to take the place of')
    rust = [_px(img, x, y) for x, y in old]
    ox0, oy0 = min(x for x, _ in old), min(y for _, y in old)
    ox1, oy1 = max(x for x, _ in old) + 1, max(y for _, y in old) + 1
    # take them off: the blank plate's face at the same place on it
    for y in range(oy0 - 6, oy1 + 6):
        for x in range(ox0 - 6, ox1 + 6):
            s = ((y * SIZE + x + BLANK_SHIFT) * 4)
            d = (y * SIZE + x) * 4
            img[d:d + 4] = px[s:s + 4]
    # the new ones, as tall as the old, side by side as wide as the old pair with the strips' own spacing
    hgt = oy1 - oy0
    scaled = []
    for ch in number:
        m, (a, b, c, d) = figs[ch]
        k = hgt / (d - b)
        scaled.append((m, (a, b, c, d), k, int((c - a) * k)))
    gap = max(4, hgt // 8)
    total = sum(s[3] for s in scaled) + gap * (len(scaled) - 1)
    at = cx - total // 2
    n = 0
    for m, (a, b, c, d), k, wd in scaled:
        for y in range(oy0, oy1):
            for x in range(at, at + wd):
                # (how much of the pixel the scaled figure covers, from 4 x 4 points in it: smooth edges)
                cover = sum(1 for p in range(4) for q in range(4)
                            if (a + int((x - at + (p + 0.5) / 4) / k), b + int((y - oy0 + (q + 0.5) / 4) / k)) in m) / 16.0
                if cover:
                    r, g, bb, _al = rust[(x * 7919 + y * 104729) % len(rust)]
                    i = (y * SIZE + x) * 4
                    img[i:i + 3] = bytes(round(img[i + j] * (1 - cover) + v * cover) for j, v in enumerate((r, g, bb)))
                    n += 1
        at += wd + gap
    return dds.encode(SIZE, SIZE, bytes(img)), n


def paths(number):
    return ('textures' + BS + 'folab' + BS + 'vault%s' % number + BS + 'vault%snumbers.dds' % number,
            'meshes' + BS + 'folab' + BS + 'vault%s' % number + BS + 'Vault%sGearDoor.nif' % number)


def ops(game, pr, number, gear_ref=None):
    """(ops, report): the sheet and the door's model among the mod's own files (written now), a DOOR of the mod's own named
    '$gear50' (for number 50), and, given gear_ref (cell, ref), that door swapped onto it."""
    tex, mesh = paths(number)
    gear = next(f for f, (_i, r) in game.forms.items() if r.tag == 'DOOR' and game.edid(f) == GEAR)
    model = game.describe(gear)[3]
    data, drawn = sheet(game, number)
    nif = nifwrite.retexture(game.read_file('meshes' + BS + model), {SHEET.lower(): tex})
    root = library.assets_dir(pr)
    library._put(root, tex, data)
    library._put(root, mesh, nif)
    rec = recordio.load(game, gear)
    rec['subs'] = [s for s in rec['subs'] if s['tag'] != 'MODT']
    recordio.set_field(rec, 'EDID', 'FOLabVault%sGearDoor' % number, label='Editor ID')
    for s in rec['subs']:
        if s['tag'] == 'MODL':
            s['value'] = mesh[len('meshes' + BS):]
    name = 'gear%s' % number
    out = [{'op': 'record_new', 'record': rec, 'name': name}]
    if gear_ref:
        out.append({'op': 'swap', 'cell': gear_ref[0], 'ref': gear_ref[1], 'base': '$' + name})
    return out, {'texture': tex, 'mesh': mesh, 'figure_pixels': drawn, 'model_from': model}
