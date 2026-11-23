"""Crops of FOLab's own for the Huáng's plantations north of the Koʻolau (the user, 23 Nov 2026: "Vary it up ... 'mutant'
versions"; "Yes, both": the mix and the cane). The game has no sugar cane, so this is one, grown as the wasteland grows things:
oversized (6-8 m), its canes a deep wine red with pale joints, its leaves a sickly yellow-green with red ribs.

A piece is a whole row (one thing for the game to draw where a field would otherwise be hundreds): ROW long, CLUMPS clumps
of CANES canes each. The canes are closed tubes; a low solid runs the row's length, so the player walks into the cane, not
through it; the far model is the row's mass in its colours."""
import math
import random

import modelsets
import texpaint as tp
from modelsets import look, limb, _fronds

SET = 'crops'
ROW = 896.0
CLUMPS = 7
CANES = 4
CANE_RED = (112, 34, 46)
LEAF = (150, 158, 62)
RIB = (150, 56, 56)

modelsets.TEXTURES.update({
    'crops/cane': lambda: tp.bark_rings(colour=CANE_RED, size=128, rings=3, seed=150),
    'crops/cane_leaf': lambda: tp.lance_leaf(colour=LEAF, rib=RIB, w=64, h=256, seed=151),
    'crops/cane_far': lambda: tp.foliage(size=128, seed=152, leaves=400, leaf=0.09, slim=0.18, dark=(70, 40, 36), light=(150, 156, 66)),
})


def cane_row(seed=1):
    """A row of sugar cane along x, its middle at the origin."""
    rnd = random.Random(seed)
    looks = {'cane': look('crops/cane', tile=64), 'leaf': look('crops/cane_leaf', alpha=True),
             'far': look('crops/cane_far', tile=256)}
    parts = [{'shape': 'box', 'size': [ROW, 90, 160], 'at': [0, 0, 0], 'look': None, 'solid': True, 'material': 'wood'},   # (only to walk into)
             {'shape': 'box', 'size': [ROW, 140, 470], 'at': [0, 0, 0], 'look': 'far', 'far_only': True}]
    step = ROW / CLUMPS
    for c in range(CLUMPS):
        cx = -ROW / 2 + step * (c + 0.5) + rnd.uniform(-18, 18)
        cy = rnd.uniform(-14, 14)
        for k in range(CANES):
            a = math.radians(k * 137.5 + rnd.uniform(-20, 20))
            d = rnd.uniform(6, 26)
            foot = (cx + math.cos(a) * d, cy + math.sin(a) * d, -6)
            tall = rnd.uniform(390, 560)
            lean = rnd.uniform(0.04, 0.12)
            top = (foot[0] + math.cos(a) * tall * lean, foot[1] + math.sin(a) * tall * lean, tall)
            parts.append(limb(foot, top, rnd.uniform(5.5, 7.0), 4.2, 'cane', sides=6, solid=False, caps=True))
            parts += _fronds(rnd, 4, top, (160, 240), 24, 'leaf', up=(70, -10), droop=(40, 80), fold=12, segments=4)
    return {'name': 'FOLabCropCaneRow', 'looks': looks, 'parts': parts}


modelsets.PIECES['cane_row'] = {'label': 'Sugar cane, a row', 'set': SET, 'file': 'cane_row', 'describe': cane_row, 'edid': 'FOLabCropCaneRow'}
