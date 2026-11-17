"""The Missouri (battleship.py) stood in a mod's sea, in place of the carrier othergame and aboard.py made.

`stand` puts her in at a spot, floating at the sea's level, her model and textures among the mod's own files.
`carrier` finds the carrier as it stands in a mod, with everything its way aboard put outside (the pier, the door
frames and doors on the hull, the marker); `carrier_ops` takes all of that out, and `swap` stands the Missouri where
the carrier lay, along the same line, her port side (the gangway's) to the nearer shore. The carrier's base inside
(a copy of a Nellis hangar) is left to the caller: shipinside gives her decks of her own."""
import math

import aboard
import landmarks
import modelsets
import recordio
import roadgen
import waikikiset
import battleship

PIECE = 'missouri'
CARRIER = 'FOLabRC'                 # (the carrier's statics: Rivet City's pieces, by the mod's editor IDs)
MARKER_NAME = 'USS Missouri'


def _turn(lx, ly, rz):
    c, s = math.cos(rz), math.sin(rz)
    return lx * c + ly * s, -lx * s + ly * c


def to_world(x, y, rz, lx, ly):
    tx, ty = _turn(lx, ly, rz)
    return x + tx, y + ty


def _cell(gd, world, x, y):
    c = gd.grid(world).get((int(x // 4096), int(y // 4096)))
    return gd.key(c) if c is not None else None


def stand(gd, pr, world, x, y, turn, scale=1.0):
    """(ops, info): her files into the mod, her record (named '$model_missouri' when new), her placed at x, y turned
    by `turn` (her bow towards the turned -y), floating at the water there, with her lights."""
    ops, info = modelsets.put(pr, PIECE)
    key = info['key'] or '$model_' + PIECE
    water = roadgen.Ground(gd, pr, world).water(x, y) or 0.0
    ck = _cell(gd, world, x, y)
    if ck is None:
        raise ValueError('There is no sea cell at %d, %d.' % (x, y))
    ops.append({'op': 'add', 'cell': ck, 'base': key, 'p': [round(x, 1), round(y, 1), round(water, 1), 0.0, 0.0, round(turn % math.tau, 4)], 's': scale,
                'name': 'missouri'})          # (not kept loaded: with it the game drew her and her far model at once, and they flickered)
    for o in waikikiset.lights(gd, pr, PIECE, x, y, water, turn, scale):
        o['cell'] = _cell(gd, world, o['p'][0], o['p'][1]) or ck
        ops.append(o)
    info.update(x=round(x), y=round(y), turn=round(turn % math.tau, 4), scale=scale, water=water)
    return ops, info


# ---------- the carrier she replaces ----------

def carrier(gd, pr, prefix='FOLab'):
    """The carrier as it stands in the mod: {'pieces': [(cell, ref)], 'outside': [(cell, ref)] (its way aboard's pier,
    frames, doors and marker), 'middle': (x, y), 'along': its long line's turn, 'hangar': the base's cell key or None}, or None."""
    own = {k: recordio.field(r, 'EDID') or '' for k, r in pr.records.items() if k.startswith('+')}
    rc = {k for k, e in own.items() if e.startswith(prefix + 'RC')}
    if not rc:
        return None
    pieces, pts = [], []
    for ck, c in pr.cells.items():
        if ck.startswith('+'):
            continue
        for rk, r in c['refs'].items():
            if r.get('base') in rc and r.get('p') and not r.get('removed'):
                pieces.append((ck, rk))
                pts.append(r['p'])
    if not pieces:
        return None
    mx, my = sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)
    # (its long line: the direction the pieces spread furthest)
    sxx = sum((p[0] - mx) ** 2 for p in pts)
    syy = sum((p[1] - my) ** 2 for p in pts)
    sxy = sum((p[0] - mx) * (p[1] - my) for p in pts)
    ang = 0.5 * math.atan2(2 * sxy, sxx - syy)                  # (of the x axis, anticlockwise)
    along = math.atan2(math.cos(ang), math.sin(ang))            # (the turn that lays a thing's y along it)
    hangar = next((k for k, e in own.items() if e == prefix + aboard.PLACE[0] and pr.records[k].get('type') == 'CELL'), None)
    outside = []
    found = aboard._bases(gd, (aboard.DOOR, landmarks.DOCK, landmarks.PYLON[0]))
    dockish = {gd.key(found[k]) for k in (landmarks.DOCK, landmarks.PYLON[0]) if found[k] is not None}
    door = gd.key(found[aboard.DOOR]) if found[aboard.DOOR] is not None else None
    frames = [r['p'] for ck, rk in pieces for r in [pr.cells[ck]['refs'][rk]] if own.get(r['base']) == prefix + aboard.FRAME]
    hull_door = None
    for ck, c in pr.cells.items():
        if ck.startswith('+'):
            continue
        for rk, r in c['refs'].items():
            p = r.get('p')
            if not p or not rk.startswith('+'):
                continue
            if r.get('base') == door and any(math.dist(p[:3], f[:3]) < 40 for f in frames):
                outside.append((ck, rk))                    # (a door in one of the ship's frames)
                if abs(p[2] - min(f[2] for f in frames)) < 40:
                    hull_door = p
            elif (r.get('marker') or {}).get('name') == aboard.MARKER[0]:
                outside.append((ck, rk))
    if hull_door is not None:
        # the pier: dock pieces and pylons on the line straight out of the hull door, turned as it is
        yaw = hull_door[5] - aboard.DOOR_IN_FRAME[3]
        nx, ny = math.sin(yaw), math.cos(yaw)
        for ck, c in pr.cells.items():
            if ck.startswith('+'):
                continue
            for rk, r in c['refs'].items():
                p = r.get('p')
                if r.get('base') in dockish and p and rk.startswith('+') and abs((p[5] - yaw + math.pi) % math.tau - math.pi) < 0.01:
                    dx, dy = p[0] - hull_door[0], p[1] - hull_door[1]
                    if abs(dx * ny - dy * nx) < 64 and -64 < dx * nx + dy * ny < aboard.PIER_MOST + 2000:
                        outside.append((ck, rk))
    return {'pieces': pieces, 'outside': outside, 'middle': (mx, my), 'along': along, 'hangar': hangar, 'hull_door': hull_door}


def carrier_ops(pr, got, prefix='FOLab'):
    """Ops that take the carrier and what stands outside for its way aboard out of the mod, and its statics' records
    (nothing else names them then). The hangar place stays."""
    ops = [{'op': 'remove', 'cell': ck, 'ref': rk} for ck, rk in got['pieces'] + got['outside']]
    for k, r in pr.records.items():
        if k.startswith('+') and r.get('type') == 'STAT' and (recordio.field(r, 'EDID') or '').startswith(prefix + 'RC'):
            ops.append({'op': 'record_revert', 'key': k})
    return ops


def shore_side(gd, pr, world, x, y, turn, reach=6000.0):
    """+1 when her port side (+x in her frame) at the gangway looks to land nearer than her starboard, else -1."""
    ground = roadgen.Ground(gd, pr, world)
    water = ground.water(x, y) or 0.0
    best = {}
    gy = battleship.SPOTS['gangway_y']
    for sgn in (1, -1):
        d = battleship.half_beam(gy)
        while d < reach:
            px, py = to_world(x, y, turn, sgn * d, gy)
            g = ground.at(px, py)
            if g is None:
                break
            if g >= water:
                best[sgn] = d
                break
            d += 128.0
    if not best:
        return 1
    return min(best, key=best.get)


def world_cells(gd, world):
    """The keys of a world's grid cells."""
    return {gd.key(c) for c in gd.grid(world).values()}


def standing(pr, gd=None, world=None):
    """Where the Missouri stands in the mod: (cell, ref, place) or None. With gd and world: in that world only (a hotel's
    small world holds a copy of the city round it, her among it: the first copy found was taken for her, 17 Nov 2026)."""
    import modelsets
    key = modelsets.record_of(pr, PIECE)
    only = world_cells(gd, world) if world is not None else None
    for ck, c in pr.cells.items():
        if only is not None and ck not in only:
            continue
        for rk, r in c['refs'].items():
            if key and r.get('base') == key and not r.get('removed'):
                return ck, rk, r['p']
    return None


def unboard_ops(gd, pr, world, prefix='FOLab'):
    """Ops that take her out again, with everything board and stand put round her (her places and all in them, the doors
    on her deck, the gangway, the pier, the marker, her lights), so she can be stood afresh. Her records stay (stand
    and board use them again)."""
    import modelsets
    import shipinside
    got = standing(pr, gd, world)
    if not got:
        return []
    ck0, rk0, p = got
    city = world_cells(gd, world)          # (only her world: the copies of what is round her in the hotels' small worlds stay)
    places = {k for k, r in pr.records.items() if k.startswith('+') and r.get('type') == 'CELL'
              and recordio.field(r, 'EDID') in {prefix + e for e, _f, _fn in shipinside.PLACES.values()}}
    gang = modelsets.record_of(pr, 'mo_gangway')
    found = aboard._bases(gd, (landmarks.DOCK, landmarks.PYLON[0]))
    dockish = {gd.key(f) for f in found.values() if f is not None}
    lights = {gd.key(f) for f, (_i, r) in gd.forms.items() if r.tag == 'LIGH'}
    spots = [to_world(p[0], p[1], p[5], lx, ly) for _e, lx, ly, _lz in waikikiset.LIGHTS.get(PIECE, ())]
    gangways = [r['p'] for ck, c in pr.cells.items() if ck in city for r in c['refs'].values() if gang and r.get('base') == gang and not r.get('removed')]
    ops = [{'op': 'remove', 'cell': ck0, 'ref': rk0}]
    for ck, c in pr.cells.items():
        if ck.startswith('+') or ck not in city:
            continue
        for rk, r in c['refs'].items():
            if not rk.startswith('+') or rk == rk0 or r.get('removed') or not r.get('p'):
                continue
            q = r['p']
            leads = (r.get('tel') or {}).get('door')
            gone = (gang and r.get('base') == gang) or (r.get('marker') or {}).get('name') == shipinside.MARKER[0]
            gone = gone or (leads and any(leads in (pr.cells.get(pk) or {}).get('refs', {}) for pk in places))
            gone = gone or (r.get('base') in lights and any(math.hypot(q[0] - sx, q[1] - sy) < 2 for sx, sy in spots))
            if not gone and r.get('base') in dockish:
                for g in gangways:              # (the pier: straight out from the gangway's landing, turned as it is)
                    nx, ny = math.cos(g[5]), -math.sin(g[5])
                    dx, dy = q[0] - g[0], q[1] - g[1]
                    if abs(dx * ny - dy * nx) < 64 and 0 < dx * nx + dy * ny < shipinside.PIER_MOST + 3000:
                        gone = True
            if gone:
                ops.append({'op': 'remove', 'cell': ck, 'ref': rk})
    for k in places:
        ops += place_ops(pr, k)
    return ops


def restand(gd, pr, world, prefix='FOLab'):
    """(ops, report): her taken out with all round her and stood again where she was, along the same line, with this
    FOLab's model, insides and way aboard."""
    import shipinside
    got = standing(pr, gd, world)
    if not got:
        raise ValueError("The Missouri isn't in this world of the mod.")
    _ck, _rk, p = got
    ops = unboard_ops(gd, pr, world, prefix)
    more, info = stand(gd, pr, world, p[0], p[1], p[5])
    ops += more
    aboard_ops, rep = shipinside.board(gd, pr, world, (p[0], p[1], info['water'], info['turn']), prefix, again=True)
    # (her first insides were one model of FOLab's own a place: their records go with the places that held them)
    old = [k for k, r in pr.records.items() if k.startswith('+') and r.get('type') == 'STAT' and recordio.field(r, 'EDID') in shipinside.OLD_SHELLS]
    going = {(o['cell'], o['ref']) for o in ops if o['op'] == 'remove'}
    used = {r.get('base') for ck, c in pr.cells.items() for rk, r in c['refs'].items() if not r.get('removed') and (ck, rk) not in going}
    shells = [{'op': 'record_revert', 'key': k} for k in old if k not in used]
    return ops + aboard_ops + shells, dict(info, removed=len(ops), aboard=rep, old_shells=len(shells))


def place_ops(pr, ckey):
    """Ops that take one of the mod's own places out whole: everything in it, its navmesh, its record."""
    ops = [{'op': 'remove', 'cell': ckey, 'ref': rk} for rk in list((pr.cells.get(ckey) or {}).get('refs', {}))]
    if ckey in pr.navmesh:
        ops.append({'op': 'navmesh_revert', 'cell': ckey})
    ops.append({'op': 'record_revert', 'key': ckey})
    return ops


def swap(gd, pr, world, prefix='FOLab', insides=True):
    """(ops, report): the carrier out (and the base its way aboard made), the Missouri in where it lay, along its
    line, her gangway side to the shore; with insides, her own (shipinside.board). Navmeshes after: shipinside.navmesh_ops."""
    import shipinside
    got = carrier(gd, pr, prefix)
    if not got:
        raise ValueError('There is no carrier in this mod to replace.')
    x, y = got['middle']
    turn = got['along']                                         # (her gangway goes down whichever side faces the land: shipinside.board)
    ops = carrier_ops(pr, got, prefix)
    if got['hangar'] and insides:
        ops += place_ops(pr, got['hangar'])
    more, info = stand(gd, pr, world, x, y, turn)
    ops += more
    rep = dict(info, removed=len(got['pieces']), outside=len(got['outside']), hangar=got['hangar'])
    if insides:
        more, rep['aboard'] = shipinside.board(gd, pr, world, (x, y, info['water'], info['turn']), prefix)
        ops += more
    return ops, rep
