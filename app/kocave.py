"""The first cave in the Ko'olau ridges (the user, 22 Nov 2026: "the first cave goes in the Ko'olau ridges"): a place of the
mod's own filled with the game's cave kit, its way out at the kit's own cave mouth, and a door into the hillside outside
(rockdoor.py). Nothing in it says whose it is or what happened there: that's not decided (docs/waikiki-caves.md).

- **Inside.** `kitplan.filled` tiles an area with the cave kit's one-square tunnel pieces (512 a square), every side agreeing,
  kept only if walking reaches most of it and gets nowhere else; squares nobody can get into are left out. The hole check
  reads cave rock now (22 Nov 2026: floor running on under a low overhang isn't a hole; the 33 to 37 "holes" in the samples
  were all that).
- **The way out** is a `CaveHallAntagonizerEntrance` (the piece the game hangs its cave load doors in, 28 times) whose mouth
  opens on nothing beyond the area, with the door the game hangs there (kitdress survey `exits`, FalloutNV's own first).
- **Dressed** from the game's own caves (kitdress.dress over the kit's survey: each piece gets what that piece had in a real
  cave, lights among it), then walked again with everything in.

    make(game, kits, w, h, seed, store, cache, survey)   {'plan', 'made', 'items', 'walk', 'exit', 'ts'} or None
    ops(...)                                             {'ops', 'said', 'inside'} for a place of the mod's own, or {'note'}"""
import math
import random

import kitdress as D
import kitindex as K
import kitplan as P

KIT = 'dungeons' + chr(92) + 'caves'
MOUTH = 'CaveHallAntagonizerEntrance'
SIZE = (10, 8)              # (squares of 512: about 73 by 58 m)
KEEP_LOOKING = 5            # (caves that walk, tried before the biggest is kept)
BIG_ENOUGH = 0.6            # (...or one this much of the area)
NOT_IN = ('Gore', 'Blood', 'Skeleton', 'Skull', 'Corpse', 'NCR', 'Legion', 'Grave')    # (what a cave nobody's story is told in yet keeps out)


def _mouths(game, ts, made):
    """[(piece, way out)]: the kit's cave mouths that open on nothing beyond the area."""
    squares = {m.cell[:2] for m in made}
    out = []
    for m in made:
        if game.edid(game.from_key(m.key)) != MOUTH:
            continue
        p = ts.kit.pieces[m.key]
        for d in range(4):
            n = (m.cell[0] + P.DX[d][0], m.cell[1] + P.DX[d][1])
            side = (d + m.turn) % 4
            if n not in squares and any(s['side'] == side and s['open'] for s in p.slots):
                out.append((m, d))
    return out


def mouth_door(game, sv, m, d, rng):
    """(door key, [x, y, z, rx, ry, rz]): where the game hangs a cave door of its own in this mouth piece, on the side that
    opens out (side 1 is the piece's +y, side 3 its -y), FalloutNV's doors only. None if the game never did."""
    side = (d + m.turn) % 4
    options = []
    for (door, x, y, z, rz), n in sv.exits.get(m.key, {}).items():
        if not door.lower().startswith('falloutnv.esm:') or (y > 0) != (side == 1):
            continue
        options.append(((door, x, y, z, rz), n))
    if not options:
        return None
    (door, x, y, z, rz) = D._pick(options, rng)
    return door, D._world(m, x, y, z, 0.0, 0.0, rz)


def make(game, kits, w, h, seed, store, cache, survey, tries=16):
    """The biggest cave of a few that walk with a way out (`KEEP_LOOKING` of them, or one filling `BIG_ENOUGH` of the
    area)."""
    sv = (survey or {}).get(KIT)
    best, found = None, 0
    for k in range(tries):
        got = P.filled(game, kits, KIT, w, h, seed + k * 101, store, cache)
        if not got:
            continue
        plan, made = got
        ts = store[('fill', KIT)]
        mouths = _mouths(game, ts, made)
        if not mouths or sv is None:
            continue
        rng = random.Random(seed + k)
        # (the mouth furthest from the area's middle: you walk in to find the rest)
        mx = sum(m.cell[0] for m in made) / len(made)
        my = sum(m.cell[1] for m in made) / len(made)
        mouths.sort(key=lambda md: -math.hypot(md[0].cell[0] - mx, md[0].cell[1] - my))
        m, d = mouths[0]
        got = mouth_door(game, sv, m, d, rng)
        if not got:
            continue
        exit_item = D.Item(got[0], got[1], 1.0, 'exit', 0)
        plan.exit = (m.cell, d)          # (the walk's hole check leaves the doorway itself alone)
        ts.floor = 0
        items = D.dress(ts, sv, plan, made, rng)
        # (no loot the game left in its own caves: an NCR helmet doesn't belong on the island; what's here is the user's to say)
        items = [it for it in items if it.what not in ('door', 'exit', 'loot') and not any(w_ in (sv.info.get(it.key, ('', (), ''))[2] or '') for w_ in NOT_IN)]
        items.append(exit_item)
        walk = P.walk_check(game, ts, plan, made, cache, D.item_refs(game, items))
        if walk['escaped'] or walk['edges'] or len(walk['missing']) > 0.1 * walk['squares']:
            continue
        lost = set(walk['missing'])
        if lost:
            made = [q for q in made if q.cell not in lost]
            items = [it for it in items if it.piece is None or it.piece.cell not in lost]
        got = {'plan': plan, 'made': made, 'items': items, 'walk': walk, 'exit': (m, d), 'ts': ts, 'seed': seed + k * 101}
        # (the biggest of those that walk: a cave worth going into)
        if best is None or len(made) > len(best['made']):
            best = got
        if len(made) >= w * h * BIG_ENOUGH:
            break
        found += 1
        if found >= KEEP_LOOKING:
            break
    return best


def inside_arrival(g, origin=(0.0, 0.0, 0.0)):
    """Where you arrive inside: the middle of the mouth's square, facing in. [x, y, z, 0, 0, heading]"""
    m, d = g['exit']
    st = g['ts'].step
    dx, dy = P.DX[d]
    x, y = m.cell[0] * st - dx * 64.0, m.cell[1] * st - dy * 64.0
    walk = g['walk']
    return [round(origin[0] + x, 1), round(origin[1] + y, 1), round(origin[2] + m.z + 24.0, 1), 0.0, 0.0, round(math.atan2(-dx, -dy) % math.tau, 4)]


def ops(game, kits, w, h, seed, store, cache, survey, origin=(0.0, 0.0, 0.0)):
    g = make(game, kits, w, h, seed, store, cache, survey)
    if not g:
        return {'note': 'No cave of this size walked out right with a way out: try another seed.'}
    ts = g['ts']
    out = P.as_ops(ts, g['made'], origin) + D.item_ops(g['items'], origin)
    kinds = {}
    for it in g['items']:
        kinds[it.what] = kinds.get(it.what, 0) + 1
    said = 'A cave of %d pieces of the game\'s cave kit, %d lights and %d other things from its own caves; its way out at a cave mouth. Walked: %d squares reached, none missing, no way out but the door.' % (
        len(g['made']), kinds.get('light', 0), sum(v for k, v in kinds.items() if k not in ('light', 'exit')), len(g['made']))
    return {'ops': out, 'said': said, 'inside': inside_arrival(g, origin), 'g': g}
