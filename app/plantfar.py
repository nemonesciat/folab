"""Far versions of FOLab's trees (plantfar.py): so the jungle doesn't stop at the edge of the loaded cells.

Past the cells the game has loaded nothing is drawn but the far ground and what the distant blocks hold (lodobj.py), and
a block holds a placed thing only if its model has a far version beside it (<model>_lod.nif). FOLab's plants had none,
so every tree and palm vanished a few cells off (the user, 20 Nov 2026: "trees and plants fade way too soon in game";
nv-rs's fade settings were already far out: the cut-off was the loaded edge itself).

Each of FAR_TREES gets, in its far model only ('far_only' parts, modelsets.far_of): its crown as one low egg the size and
place of its leaves, in an opaque leafy picture ('jungle/canopy_far': a block's sheet holds no see-through), and its trunk
from its foot to the crown's underside (modelsets.limb, its own bark). About 60 triangles a tree; a block is one draw
whatever it holds. Shrubs and low plants get none: the far ground's own green (farfoliage) stands for them."""
import math

import modelmake
import modelsets as ms
import texpaint as tp

FAR_TREES = ('jungle_tree', 'jungle_banyan', 'jungle_tall', 'palm_tall', 'palm_young', 'tree_fern', 'bamboo', 'banana')
CROWN_FILL = 0.85               # the egg a little inside the leaves' box: a box's corners are air


def _canopy_far():
    c = tp.foliage(size=256, seed=41, leaves=1400, leaf=0.05)
    base = (40, 70, 34)
    for i in range(c.w * c.h):
        a = c.a[i] if c.a is not None else 1.0
        r, g, b = c.rgb[i]
        c.rgb[i] = (r * a + base[0] * (1 - a), g * a + base[1] * (1 - a), b * a + base[2] * (1 - a))
    c.a = None                                  # (opaque: the distant blocks' sheet has no see-through)
    return c


if 'jungle/canopy_far' not in ms.TEXTURES:
    ms.TEXTURES['jungle/canopy_far'] = _canopy_far


def _far_parts(desc):
    made = modelmake.make(desc)
    leaf = [s for s in made['shapes'] if s.get('alpha')]
    wood = [s for s in made['shapes'] if not s.get('alpha')]
    if not leaf:
        return None, None
    xs = [v for s in leaf for v in s['p'][0::3]]
    ys = [v for s in leaf for v in s['p'][1::3]]
    zs = [v for s in leaf for v in s['p'][2::3]]
    x0, x1, y0, y1, z0, z1 = min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    rx, ry, rz = (x1 - x0) / 2 * CROWN_FILL, (y1 - y0) / 2 * CROWN_FILL, (z1 - z0) / 2 * CROWN_FILL
    bottom = z0 + (z1 - z0) * (1 - CROWN_FILL) / 2
    parts = [{'shape': 'ball', 'r': 1.0, 'sides': 7, 'rings': 4, 'scale': [rx, ry, rz], 'at': [cx, cy, bottom],
              'look': 'far_canopy', 'far_only': True, 'solid': False}]
    bark = None
    if wood:
        # (its trunk: from the middle of the wood at the ground to under the crown, as thick as the wood is at its foot)
        foot = [(s['p'][k], s['p'][k + 1]) for s in wood for k in range(0, len(s['p']), 3) if s['p'][k + 2] < 40]
        if foot:
            fx = sum(p[0] for p in foot) / len(foot)
            fy = sum(p[1] for p in foot) / len(foot)
            r0 = max(6.0, min(60.0, max(math.hypot(p[0] - fx, p[1] - fy) for p in foot) * 0.6))
            bark = next((k for k, v in desc['looks'].items() if not v.get('alpha')), None)
            if bark:
                q = ms.limb((fx, fy, 0.0), (cx, cy, bottom + rz * 0.6), r0, r0 * 0.6, bark, sides=5)
                q = dict(q, far_only=True, solid=False)
                parts.append(q)
    return parts, bark


def _wrap(original):
    def describe():
        desc = original()
        parts, _bark = _far_parts(desc)
        if not parts:
            return desc
        looks = dict(desc['looks'], far_canopy=ms.look('jungle/canopy_far'))
        return dict(desc, looks=looks, parts=list(desc['parts']) + parts)
    return describe


for _p in FAR_TREES:
    if _p in ms.PIECES and not ms.PIECES[_p].get('far_trees'):
        ms.PIECES[_p]['describe'] = _wrap(ms.PIECES[_p]['describe'])
        ms.PIECES[_p]['far_trees'] = True
