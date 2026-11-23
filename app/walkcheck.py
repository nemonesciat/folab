"""Walks a set of things from its real collision before anything is navmeshed: stairs, ladders, decks, platforms.

A navmesh remake of a big world takes hours (Waikiki's 1,407 meshes, 17 Nov 2026), and a walkable piece fixed after the
meshes were made means making them again: the Missouri's ladders stood on the deck's last 20 units, the guard towers
went up without the parts that carry their stairs and floors, and both were found in the game. So a set is walked first,
the way navgen sees it:

  - its collision is laid into columns (navgen.Field) and the places to stand joined by steps (navgen.Graph), eroded by
    an actor's radius, exactly as a navmesh is made;
  - the walk starts from the ground round it (flat ground at z 0 in the set's frame, a margin past its box) or from
    given start points (a ship's gangway: there is no ground);
  - short: every area big enough to stand about on (MIN_AREA places) that the walk doesn't come to, though it would if
    actors were thin: the way there is narrower than an actor (a ladder whose feet are on a deck's last few units). A fault;
  - unreached: the other areas out of reach (roofs, truck beds): listed, not a fault, since many are meant to be;
  - invisible: every place walked to where nothing is drawn within SEEN of it (its own column or one round it). Collision
    with no model over it: the guard tower's ramps without its parts, a solid left where a model moved. A fault;
  - goals: points the set promises can be walked to (a lookout, a bridge door), each reached or not.

Items are dicts: 'base' (a form key of the game's) or 'nif' (a model's bytes: FOLab's own, made by modelmake) or 'model'
(a path under Data), with 'pos', 'rot' (radians, the game's x, y, z) and 'scale'. `of_set` and `of_piece` make them from
a landmark set (landmarks.lift) and from one of FOLab's own pieces (modelsets.build). `py -3 app/walkcheck.py [name ...]`
walks FOLab's own walkable pieces and the landmark sets, or the ones named."""
import math
import struct
import sys

import hkshape
import navgen
import nif

VOXEL = 16.0
MARGIN = 512.0          # flat ground this far past the set's box all round
MIN_AREA = 40           # places (16 x 16 each): an area smaller than this isn't somewhere to stand about (navgen's MIN_REGION)
SEEN = 24.0             # a place to stand with nothing drawn this close above or below it is invisible
MIN_INVISIBLE = 12      # places joined together: fewer is a seam or a rounded edge, not a floor
GOAL_REACH = 160.0      # a goal counts as reached if a place walked to is this close to it (seen from above)...
GOAL_UP = 64.0          # ...and this close in height (not the deck inside a closed house beside it)
SAY_OUT = 6             # how many areas out of reach `say` lists
# (An area out of reach any other way is only listed: a bunker's roof, a truck's bed, the guard tower's top deck. The
# game's own navmeshes round its guard towers stop at the last landing too, about 760 over the tower's origin.)


def _solid_and_drawn(gd, item, cache):
    """(solid pieces [(flat points, corners, soup)], drawn pieces) of an item's model, in its own frame."""
    if 'nif' in item:
        key = ('nif', id(item['nif']))
        data = item['nif']
    else:
        path = item.get('model')
        if path is None:
            try:
                btype, _e, _f, model = gd.describe(gd.from_key(item['base']))
            except (KeyError, IndexError, ValueError):
                return [], []
            if btype not in navgen.SOLID_BASES or not model:
                return [], []
            path = gd.model_path(btype, model)
        key = ('path', path.lower())
        if key in cache:
            return cache[key]
        try:
            data = gd.read_file(path)
        except (FileNotFoundError, OSError):
            cache[key] = ([], [])
            return cache[key]
    if key in cache:
        return cache[key]
    solid, drawn = [], []
    try:
        for s in hkshape.collision_shapes(data):
            if s['layer'] in hkshape.LAYERS_SOLID and s['i']:
                solid.append((s['v'], s['i'], s['soup']))
    except (hkshape.Unread, nif.NifError, struct.error, IndexError):
        pass
    try:
        for s in nif.mesh_from_nif(data):
            drawn.append((s['p'], s['i'], True))
    except (nif.NifError, struct.error, IndexError):
        pass
    cache[key] = (solid, drawn)
    return cache[key]


def _ref(item):
    return {'pos': tuple(item.get('pos', (0.0, 0.0, 0.0))), 'rot': tuple(item.get('rot', (0.0, 0.0, 0.0))),
            'scale': item.get('scale', 1.0)}


def _box(field):
    v = field.v
    iys = [k[0] for k in field.cols]
    ixs = [k[1] for k in field.cols]
    return min(ixs) * v, min(iys) * v, (max(ixs) + 1) * v, (max(iys) + 1) * v


def walk(gd, items, ground=0.0, starts=None, goals=None, labels=None, voxel=None):
    """{'reached', 'standing' (places), 'unreached': [area], 'invisible': [area], 'goals': [{'label', 'at', 'reached'}],
    'ok'}. An area is {'at': (x, y, z) its middle, 'places', 'item': the label of what stands under its middle}.
    ground: the height of flat ground round the set (None: no ground, start from `starts` only). voxel: the columns'
    size, VOXEL unless given: outdoor navmeshes are made at navgen.VOXEL_OUT (32), where a way narrow at 16 closes."""
    vox = voxel or VOXEL
    cos = math.cos(math.radians(navgen.SLOPE_MAX))
    field = navgen.Field(vox, cos)
    seen = navgen.Field(vox, -1.0)
    cache = {}
    solid_by = []
    for n, item in enumerate(items):
        solid, drawn = _solid_and_drawn(gd, item, cache)
        r = _ref(item)
        before = len(field.cols)
        if solid:
            navgen._lay_ref(field, r, solid)
        if drawn:
            navgen._lay_ref(seen, r, drawn)
        solid_by.append((n, before))
    if not field.cols:
        return {'reached': 0, 'standing': 0, 'unreached': [], 'invisible': [], 'goals': [], 'ok': False, 'empty': True}
    if ground is not None:
        x0, y0, x1, y1 = _box(field)
        x0, y0, x1, y1 = x0 - MARGIN, y0 - MARGIN, x1 + MARGIN, y1 + MARGIN
        field.add(x0, y0, ground, x1, y0, ground, x1, y1, ground, True)
        field.add(x0, y0, ground, x1, y1, ground, x0, y1, ground, True)
    g = navgen.Graph(navgen._places(field, navgen.HEADROOM), vox, navgen.STEP, navgen.HEADROOM)
    keep = g.erode([True] * len(g.p), navgen.RADIUS)
    pieces, label = g.pieces(keep)
    start = set()
    for k, piece in enumerate(pieces):
        if any(g.p[i][5] for i in piece):
            start.add(k)
    for pos in starts or ():
        i = g.nearest(pos, navgen.SEED_REACH, keep)
        if i is not None:
            start.add(label[i])

    def where(piece):
        xs = [(g.p[i][1] + 0.5) * vox for i in piece]
        ys = [(g.p[i][0] + 0.5) * vox for i in piece]
        zs = [g.p[i][2] for i in piece]
        mid = (sum(xs) / len(xs), sum(ys) / len(ys), sum(zs) / len(zs))
        return tuple(round(c) for c in mid)

    def under(at):
        return _nearest_item(gd, items, at, cache, labels)

    on = [keep[i] and label[i] in start for i in range(len(g.p))]
    reached = sum(1 for i in range(len(g.p)) if on[i] and not g.p[i][5])
    standing = sum(1 for i in range(len(keep)) if keep[i] and not g.p[i][5])
    # the same places not eroded: an area joined to where the walk starts only that way has a way to it narrower than
    # an actor (a ladder's feet on a deck's last few units, a stair squeezed past a post)
    _p0, label0 = g.pieces([True] * len(g.p))
    start0 = {label0[i] for i in range(len(g.p)) if on[i]}
    short, unreached = [], []
    for k, piece in enumerate(pieces):
        if k in start or len(piece) < MIN_AREA:
            continue
        at = where(piece)
        area = {'at': at, 'places': len(piece), 'item': under(at)}
        (short if any(label0[i] in start0 for i in piece) else unreached).append(area)
    # invisible: places walked to (not the flat ground) with nothing drawn near
    bad = [False] * len(g.p)
    for i, q in enumerate(g.p):
        if not on[i] or q[5]:
            continue
        iy, ix, z = q[0], q[1], q[2]
        hit = False
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                for s in seen.cols.get((iy + dy, ix + dx), ()):
                    if s[0] - SEEN <= z <= s[1] + SEEN:
                        hit = True
                        break
                if hit:
                    break
            if hit:
                break
        bad[i] = not hit
    groups, _l = g.pieces(bad)
    invisible = []
    for piece in groups:
        if len(piece) >= MIN_INVISIBLE:
            at = where(piece)
            invisible.append({'at': at, 'places': len(piece), 'item': under(at)})
    out_goals = []
    r = int(GOAL_REACH // vox)
    for goal in goals or ():
        lab, at = goal[0], goal[1]
        cx, cy = math.floor(at[0] / vox), math.floor(at[1] / vox)
        hit = any(on[i] and abs(g.p[i][2] - at[2]) <= GOAL_UP and math.hypot(dx, dy) * vox <= GOAL_REACH
                  for dy in range(-r, r + 1) for dx in range(-r, r + 1) for i in g.by.get((cy + dy, cx + dx), ()))
        out_goals.append({'label': lab, 'at': tuple(round(c) for c in at), 'reached': hit})
    unreached.sort(key=lambda a: -a['places'])
    short.sort(key=lambda a: -a['places'])
    invisible.sort(key=lambda a: -a['places'])
    return {'reached': reached, 'standing': standing, 'short': short, 'unreached': unreached, 'invisible': invisible,
            'goals': out_goals, 'ok': bool(start) and (ground is not None or reached > 0) and not short and not invisible and all(x['reached'] for x in out_goals)}


def _nearest_item(gd, items, at, cache, labels):
    """The label of the item whose middle is nearest a point (seen from above)."""
    best, bd = None, 1e30
    for n, item in enumerate(items):
        x, y = item.get('pos', (0, 0, 0))[:2]
        d = math.hypot(x - at[0], y - at[1])
        if d < bd:
            best, bd = n, d
    if best is None:
        return None
    if labels:
        return labels[best]
    item = items[best]
    if 'base' in item:
        try:
            return gd.edid(gd.from_key(item['base'])) or item['base']
        except (KeyError, ValueError):
            return item['base']
    return item.get('label') or item.get('model') or 'model %d' % best


def of_set(lifted, skip=()):
    """Items from a landmark set as landmarks.lift gives it (its pieces round its own middle, up from the ground)."""
    out = []
    for key, dx, dy, dz, rx, ry, rz, sc in lifted['pieces']:
        if key in skip:
            continue
        out.append({'base': key, 'pos': (dx, dy, dz), 'rot': (rx, ry, rz), 'scale': sc})
    return out


def of_piece(piece):
    """One of FOLab's own pieces (modelsets.PIECES) as an item, made afresh: its model's bytes at the origin."""
    import modelsets
    made = modelsets.build(piece)
    return {'nif': made['nif'], 'pos': (0.0, 0.0, 0.0), 'rot': (0.0, 0.0, 0.0), 'scale': 1.0,
            'label': modelsets.PIECES[piece]['label']}


# FOLab's own pieces people walk on, and how each is walked: from the ground, or (a ship) from given points; goals it
# promises. Frames as each piece is made (towerset, historicset, battleship docstrings).
def walkable():
    import battleship
    z = battleship.deck_z
    gy = battleship.SPOTS['gangway_y']
    gx = battleship.half_beam(gy) - 40.0
    qx, qy, qz = battleship.SPOTS['qd']
    z3 = z(-2150) + 270 + 260 + 250             # (the 03 level's roof, as battleship.missouri works it out)
    return {
        'missouri': {'ground': None, 'starts': [(gx, gy, z(gy)), (-gx, gy, z(gy))],
                     'goals': [('quarterdeck door', (qx, qy + 60.0, qz)), ('the bow', (0.0, -8000.0, z(-8000.0))),
                               ('the bridge door', (battleship.SPOTS['bridge'][0], battleship.SPOTS['bridge'][1] + 60.0, z3)),
                               ('port bridge wing', (-560.0, -1700.0, z3)), ('starboard bridge wing', (560.0, -1700.0, z3))]},
        'natatorium': {}, 'battery_randolph': {}, 'guard_tower': __import__('guardtower').WALK,
    } | __import__('bambooset').WALKS | __import__('treevillage').WALKS | {v['open']: {'ground': None, 'starts': [tuple(v['arrive_in'][:3])]} for v in _views().values()}


def _views():
    """The open hotels (hotelinside.VIEWS), walked from where the way in puts you: their lobbies are entered by a door."""
    import hotelinside
    return hotelinside.VIEWS


def check_piece(gd, piece, how=None):
    import modelsets
    if piece not in modelsets.PIECES:
        import bambooset, battleship, guardtower, historicset, towerset, treevillage  # noqa: F401  (they add their pieces)
    how = how if how is not None else walkable().get(piece, {})
    return walk(gd, [of_piece(piece)], ground=how.get('ground', 0.0), starts=how.get('starts'), goals=how.get('goals'), voxel=how.get('voxel'))


def check_set(gd, name, skip=()):
    import landmarks
    lifted = landmarks.lift(gd, name)
    if lifted is None:
        return None
    return walk(gd, of_set(lifted, skip))


def say(name, rep):
    if rep is None:
        return '%s: not in these game files' % name
    lines = ['%s: %s  (%d places reached of %d to stand on)' % (name, 'ok' if rep['ok'] else 'PROBLEMS', rep['reached'], rep['standing'])]
    for a in rep['short']:
        lines.append('   TOO NARROW TO GET TO: %d places at %s, on %s' % (a['places'], a['at'], a['item']))
    for a in rep['unreached'][:SAY_OUT]:
        lines.append('   (out of reach: %d places at %s, on %s)' % (a['places'], a['at'], a['item']))
    if len(rep['unreached']) > SAY_OUT:
        lines.append('   (and %d more out of reach: roofs, closed insides)' % (len(rep['unreached']) - SAY_OUT))
    for a in rep['invisible']:
        lines.append('   nothing drawn: %d places at %s, on %s' % (a['places'], a['at'], a['item']))
    for gl in rep['goals']:
        lines.append('   %s %s at %s' % ('reached' if gl['reached'] else 'NOT REACHED:', gl['label'], gl['at']))
    return '\n'.join(lines)


def main(names):
    import gamedata
    import landmarks
    gd = gamedata.GameData()
    import bambooset, battleship, guardtower, historicset, towerset, treevillage  # noqa: F401
    own = list(walkable())
    sets = [n for n, s in landmarks.SETS.items() if not s.get('own')]
    for name in names or own + sets:
        if name in own or name in __import__('modelsets').PIECES:
            print(say(name, check_piece(gd, name)))
        else:
            print(say(name, check_set(gd, name)))


if __name__ == '__main__':
    main(sys.argv[1:])
