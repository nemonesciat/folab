"""The game's road slabs and rubble piles a mod stands, swapped for FOLab's own (rubbleset), and laid in the ground.

`ops(gd, pr)`: each piece's files among the mod's own and its STAT (modelsets.put), then a 'swap' of every thing of the
mod's own whose base is one rubbleset.REPLACES names (several pieces for one base go in turn by the ref, so neighbours
differ), and for a heap a 'move' that seats it (`seat_one`). Road pieces are made in the game slab's frame, so they stay
where they lie: roadbed lays them as it lays the game's (`roadbed._flat_bases` knows them by their records).

`seat_one(ground, p, s, piece)`: tilted to the ground under its rim (fitted as osmdress.seat_lying fits), then let down
until no point of its rim is over the ground (RIM_UNDER under the highest); if that buries it more than BURY_MOST of its
height (a heap on a crest), it comes up to that much, its skirt (SKIRT_2 deep at its foot) still covering its rim's
lower side. osmdress.seat_lying seats the mod's rubbleset pieces the same way.

`check(gd, pr, world)`: how every rubbleset piece lies: a piece floats where a tip of its skirt is over the ground (a
gap shows under it there), is perched where its whole rim is more than osmdress.SEAT_ON over the ground, buried by how
much of its height its rim is under at the deepest. Road pieces are checked the same way at their edges and ends.

`apply(gd, pr)`: the ops as one Undo; navmeshes that were current before stay current (the road's top is the game
slab's; a heap is a mound of the same size where a mound was)."""
import math

import modelsets
import navgen
import recordio
import roadbed
import rubbleset

RIM_UNDER = 1.0         # a heap's rim at its highest ground goes this far under it
BURY_MOST = 0.35        # and the heap is never sunk by more than this share of its height (at its lowest ground) while its skirt still reaches the ground
GONE_HANG = 8.0         # a heap whose skirt still ends this far over the ground somewhere (a pad's edge, a drop) is taken out
BURY_GONE = 2.0         # and one whose rim is under the ground by more than twice its height somewhere (across a drop)
LIE_MOST = 0.7          # (as osmdress.LIE_MOST: the steepest a thing that lies on the ground is tilted)
LIE_FROM = 0.05


def _yaw(p):
    R = navgen._turn(p[3], p[4], p[5])
    return math.atan2(R[0][0], R[1][0])


def _world(p, R, lx, ly, lz):
    return (p[0] + R[0][0] * lx + R[0][1] * ly + R[0][2] * lz, p[1] + R[1][0] * lx + R[1][1] * ly + R[1][2] * lz,
            R[2][0] * lx + R[2][1] * ly + R[2][2] * lz)


def seat_one(g, p, s, piece):
    """A heap's place laid on the ground as it is (g.at(x, y)): [x, y, z, rx, ry, rz] (more of p kept), or None where
    there is no ground under it."""
    rim, _tips, height = rubbleset.foot(piece)
    yaw = _yaw(p)
    dx, dy = math.sin(yaw), math.cos(yaw)
    pts = []
    for lx, ly, _lz in rim:
        z = g.at(p[0] + dx * lx * s - dy * ly * s, p[1] + dy * lx * s + dx * ly * s)
        if z is not None:
            pts.append((lx * s, ly * s, z))
    if len(pts) < max(6, len(rim) // 2):
        return None
    _mx, _my, _mz, b, c = roadbed._fit(pts)
    b, c = max(-LIE_MOST, min(LIE_MOST, b)), max(-LIE_MOST, min(LIE_MOST, c))
    rot = roadbed._turn_plane(dx, dy, b, c) if max(abs(b), abs(c)) >= LIE_FROM else (0.0, 0.0, p[5])
    R = navgen._turn(*rot)
    under = []
    for lx, ly, lz in rim:
        wx, wy, oz = _world(p, R, lx * s, ly * s, lz * s)
        gz = g.at(wx, wy)
        if gz is not None:
            under.append((gz, oz))
    z = min(gz - oz for gz, oz in under) - RIM_UNDER
    bury = max(gz - (z + oz) for gz, oz in under)
    most = BURY_MOST * height * s
    if bury > most:
        # (up, but only as far as its skirt still reaches the ground all round: a gap under it is worse than a
        # heap sunk deeper on rough ground)
        room = []
        for lx, ly, lz in _tips:
            wx, wy, oz = _world(p, R, lx * s, ly * s, lz * s)
            gz = g.at(wx, wy)
            if gz is not None:
                room.append(gz - (z + oz))
        z += max(0.0, min(bury - most, min(room) if room else 0.0))
    # (where the ground beyond its rim falls away faster than its skirt, down until the skirt touches all round)
    low = []
    for lx, ly, lz in _tips:
        wx, wy, oz = _world(p, R, lx * s, ly * s, lz * s)
        gz = g.at(wx, wy)
        if gz is not None:
            low.append(z + oz - gz)
    if low and max(low) > 0:
        z -= max(low) + 0.5
    return [p[0], p[1], round(z, 1), round(rot[0], 4), round(rot[1], 4), round(rot[2] % math.tau, 4)] + list(p[6:])


def gone(g, p, s, piece):
    """Whether a seated heap still shows a gap under its skirt (GONE_HANG): rubble is no loss, so it goes."""
    hang, _over, bury = lies(g, p, s, piece)
    return hang > GONE_HANG or bury > BURY_GONE


def lies(g, p, s, piece):
    """(hang, over, bury): how far the highest tip of its skirt is over the ground (> 0: a gap shows there), how far its
    rim's lowest point is over the ground (> SEAT_ON everywhere: it stands on something), how much of its height its
    rim is under the ground at the deepest."""
    rim, tips, height = rubbleset.foot(piece)
    R = navgen._turn(p[3], p[4], p[5])
    hang, over, bury = -1e9, 1e9, 0.0
    for lx, ly, lz in tips:
        wx, wy, oz = _world(p, R, lx * s, ly * s, lz * s)
        gz = g.at(wx, wy)
        if gz is not None:
            hang = max(hang, p[2] + oz - gz)
    for lx, ly, lz in rim:
        wx, wy, oz = _world(p, R, lx * s, ly * s, lz * s)
        gz = g.at(wx, wy)
        if gz is not None:
            over = min(over, p[2] + oz - gz)
            bury = max(bury, gz - (p[2] + oz))
    return hang, over, bury / max(1.0, height * s)


def _game_keys(gd):
    """{game editor ID: form key} of the bases REPLACES names."""
    out = {}
    for f, (_i, r) in gd.forms.items():
        if r.tag == 'STAT':
            e = gd.edid(f)
            if e in rubbleset.REPLACES:
                out[e] = gd.key(f)
    return out


def pieces_of(pr):
    """{record key: piece} of the rubbleset pieces the mod has records for."""
    out = {}
    for k, rec in pr.records.items():
        if k.startswith('+') and rec.get('type') == 'STAT':
            piece = rubbleset.piece_of_edid(recordio.field(rec, 'EDID'))
            if piece:
                out[k] = piece
    return out


def _turn_of(rk, n):
    return sum(rk.encode()) % n


def _groups():
    """{rubbleset piece: the choices it was picked from} (the most choices where it is among several)."""
    out = {}
    for choices in rubbleset.REPLACES.values():
        for piece in choices:
            if len(choices) > len(out.get(piece, ())):
                out[piece] = choices
    return out


def ops(gd, pr, world=None, which=None, respread=False):
    """(ops, report). world: only its cells (default: every outside cell); which: only these game editor IDs.
    respread: things already swapped for a heap whose choices have grown since (rubbleset added looks) are picked
    again by the same rule, so the new looks are spread over what was swapped before."""
    import roadgen
    modelsets._all_sets()
    game = {k: e for e, k in _game_keys(gd).items() if which is None or e in which}
    cells = {gd.key(c) for c in gd.grid(world).values()} if world is not None else None
    g = roadgen.Ground(gd, pr, world) if world is not None else None
    out, rep = [], {'swapped': {}, 'made': [], 'seated': 0, 'no_ground': 0, 'cells': set()}
    key_of = {p: k for k, p in pieces_of(pr).items()}
    found = []
    for ck, c in pr.cells.items():
        if ck.startswith('+') or (cells is not None and ck not in cells):
            continue
        for rk, r in c.get('refs', {}).items():
            b = r.get('base')
            if rk.startswith('+') and b in game and not r.get('removed') and r.get('p') and r['p'][2] > -20000:
                found.append((ck, rk, r, game[b]))
    if respread:
        groups, mine = _groups(), pieces_of(pr)
        for ck, c in pr.cells.items():
            if ck.startswith('+') or (cells is not None and ck not in cells):
                continue
            for rk, r in c.get('refs', {}).items():
                piece = mine.get(r.get('base'))
                if (piece and rk.startswith('+') and not rubbleset.is_road(piece) and not r.get('removed') and r.get('p')
                        and r['p'][2] > -20000):
                    choices = groups.get(piece, (piece,))
                    if choices[_turn_of(rk, len(choices))] != piece:
                        found.append((ck, rk, r, choices))
    for ck, rk, r, edid in found:
        choices = edid if isinstance(edid, tuple) else rubbleset.REPLACES[edid]
        edid = edid if isinstance(edid, str) else 'again'
        piece = choices[_turn_of(rk, len(choices))]
        if piece not in key_of:
            put_ops, info = modelsets.put(pr, piece)
            out += put_ops
            key_of[piece] = info['key'] or '$model_' + piece
            rep['made'].append(info['edid'])
        out.append({'op': 'swap', 'cell': ck, 'ref': rk, 'base': key_of[piece]})
        rep['swapped'][edid] = rep['swapped'].get(edid, 0) + 1
        rep['cells'].add(ck)
        if rubbleset.is_road(piece) or g is None:
            continue
        new = seat_one(g, r['p'], float(r.get('s') or 1.0), piece)
        if new is None:
            rep['no_ground'] += 1
            continue
        if gone(g, new, float(r.get('s') or 1.0), piece):
            out.append({'op': 'remove', 'cell': ck, 'ref': rk})
            rep['taken_out'] = rep.get('taken_out', 0) + 1
            continue
        out.append({'op': 'move', 'cell': ck, 'ref': rk, 'p': new})
        rep['seated'] += 1
    rep['cells'] = sorted(rep['cells'])
    return out, rep


def check(gd, pr, world):
    """How the mod's rubbleset pieces lie: {'heaps': {...}, 'roads': {...}} each with how many, how many float (a tip of
    the skirt over the ground), by how much at worst, how many are perched (osmdress.SEAT_ON), the worst buried share,
    and `worst`: the ten that hang most (cell, ref, piece, hang)."""
    import osmdress
    import roadgen
    g = roadgen.Ground(gd, pr, world)
    mine = pieces_of(pr)
    inside = {gd.key(c) for c in gd.grid(world).values()}
    out = {}
    for kind in ('heaps', 'roads'):
        out[kind] = {'pieces': 0, 'float': 0, 'float_8': 0, 'hang_most': 0.0, 'perched': 0, 'bury_most': 0.0, 'worst': []}
    for ck, c in pr.cells.items():
        if ck not in inside:
            continue
        for rk, r in c.get('refs', {}).items():
            piece = mine.get(r.get('base'))
            if not piece or r.get('removed') or not r.get('p'):
                continue
            hang, over, bury = lies(g, r['p'], float(r.get('s') or 1.0), piece)
            o = out['roads' if rubbleset.is_road(piece) else 'heaps']
            o['pieces'] += 1
            if hang > 0:
                o['float'] += 1
                o['float_8'] += hang > 8
                o['worst'].append((round(hang, 1), ck, rk, piece))
            o['hang_most'] = max(o['hang_most'], round(hang, 1))
            o['perched'] += over > osmdress.SEAT_ON
            o['bury_most'] = max(o['bury_most'], round(bury, 2))
    for o in out.values():
        o['worst'] = sorted(o['worst'], reverse=True)[:10]
    return out


def refresh(pr):
    """Every rubbleset piece the mod has, its files written again as rubbleset makes them now (modelsets.put), and the
    ops that mark the ones with a far model 'visible when distant' (modelsets.VWD, as the game's own statics with a far
    model are): the road pieces swapped in on 21 Nov 2026 had none, and lodobj left the roads out of the far view.
    Returns (ops, report)."""
    modelsets._all_sets()
    out, rep = [], {'pieces': 0, 'far': [], 'flagged': []}
    for key, piece in sorted(pieces_of(pr).items()):
        _ops, info = modelsets.put(pr, piece)
        rep['pieces'] += 1
        made = modelsets.build(piece)
        if not made.get('far'):
            continue
        rep['far'].append(piece)
        rec = pr.records[key]
        if not int(rec.get('flags') or 0) & modelsets.VWD:
            out.append({'op': 'record', 'key': key, 'record': dict(rec, flags=int(rec.get('flags') or 0) | modelsets.VWD)})
            rep['flagged'].append(recordio.field(rec, 'EDID'))
    return out, rep


def sig_of(gd, pr, ck):
    import onepiece
    return onepiece.sig_of(gd, pr, ck)


def apply(gd, pr, world, label='Roads and rubble with no edges', which=None, respread=False):
    """The ops applied as one Undo; navmeshes that were current before stay marked current. Returns the report."""
    o, rep = ops(gd, pr, world, which, respread)
    cells = set(rep['cells'])
    current = {k: m for k, m in pr.navmesh.items() if k in cells and m.get('sig') == sig_of(gd, pr, k)}
    pr.apply(label, o)
    nav = [{'op': 'navmesh', 'cell': k, 'mesh': dict(m, sig=sig_of(gd, pr, k))} for k, m in current.items()]
    if nav:
        pr.apply(label, nav, merge=True)
    rep['navmeshes_kept_current'] = len(nav)
    return rep
