"""Fill every empty doorway doorways.py finds (the user, 25 Nov 2026, after a black doorway by the start ended a stream:
"fix everything, doorways"). Each empty doorway gets, by what the building has:

  boards        a doorway the game boards over on that building elsewhere: its own boards, as it stands them
  back door     a building that already has a way into a place of its own: a door in this doorway too, into the same
                place (you arrive where the front door puts you, and leave by the front)
  locked door   otherwise: the building's own door (the catalogue's, else `FALLBACK_DOOR`), locked, needing a key no one
                has: visibly shut, never a black hole

`EXTRA` are doorways the game draws but never fills on any of its uses of a model (found by eye from four-side views,
docs in the doorway report), in the model's frame: side, centre along it, width; `face` and `floor` measured here.

    plan(gd, pr, world, rows)   rows: doorways.Audit(...).run() -> [{fill, ...}]
    ops(gd, pr, world, plan)    (ops, report)
"""
import math

import recordio

FALLBACK_DOOR = 'BarracksDoor'
LOCKED = {'props': {'lock': {'level': 255, 'key': '', 'leveled': False}}}
LABEL = 'Every empty doorway filled'
# model editor ID: [(side '-y' '+y' '-x' '+x', centre along the side, width, floor z or None for the catalogue door's)]
EXTRA = {}


def _turn(lx, ly, rz):
    c, s = math.cos(rz), math.sin(rz)
    return lx * c + ly * s, -lx * s + ly * c


def _cell_of(gd, world, x, y):
    c = gd.grid(world).get((int(x // 4096), int(y // 4096)))
    return gd.key(c) if c is not None else None


def _catalogue(gd):
    import indoors
    return {b['key']: b for b in indoors.catalogue(gd)}


def _tel_of(gd, pr, ck, rk):
    """Where a door leads, as the mod leaves it: {'door', 'p'} or None."""
    ch = ((pr.cells.get(ck) or {}).get('refs') or {}).get(rk) or {}
    if 'tel' in ch:
        return ch['tel']
    if rk.startswith('+'):
        return None
    import struct
    try:
        x = gd.fields(gd.from_key(rk)).get('XTEL')
    except (KeyError, ValueError):
        return None
    if not x or len(x) < 28:
        return None
    door = struct.unpack_from('<I', x, 0)[0]
    p = list(struct.unpack_from('<6f', x, 4))
    try:
        return {'door': gd.key(door), 'p': [round(v, 3) for v in p]}
    except (KeyError, ValueError):
        return None


def wall_face(gd, model_path, side, along, wide, floor):
    """The wall's outer face coordinate on a side at a doorway: rays at waist height either side of the opening."""
    import numpy as np
    import nif
    shapes = nif.mesh_from_nif(gd.read_file(model_path))
    T = np.concatenate([np.asarray(s['p'], float).reshape(-1, 3)[np.asarray(s['i'], int).reshape(-1, 3)] for s in shapes if s['i']])
    run_ax, sign = {'-y': (1, +1), '+y': (1, -1), '-x': (0, +1), '+x': (0, -1)}[side]
    along_ax = 1 - run_ax
    hits = []
    for a in (along - wide / 2 - 24, along + wide / 2 + 24):
        for z in (floor + 80, floor + 140):
            P, Z, R = T[:, :, along_ax], T[:, :, 2], T[:, :, run_ax]
            ax, az = P[:, 0], Z[:, 0]
            bx, bz, cx, cz = P[:, 1] - ax, Z[:, 1] - az, P[:, 2] - ax, Z[:, 2] - az
            px, pz = a - ax, z - az
            den = bx * cz - cx * bz
            with np.errstate(divide='ignore', invalid='ignore'):
                u = (px * cz - cx * pz) / den
                w = (bx * pz - px * bz) / den
            hit = (np.abs(den) > 1e-9) & (u >= 0) & (w >= 0) & (u + w <= 1)
            if hit.any():
                r = R[hit, 0] + u[hit] * (R[hit, 1] - R[hit, 0]) + w[hit] * (R[hit, 2] - R[hit, 0])
                hits.append(float(r.min() if sign > 0 else r.max()))
    if not hits:
        return None
    hits.sort()
    return hits[len(hits) // 2]


def _out_of(side):
    return {'-y': (0, -1), '+y': (0, 1), '-x': (-1, 0), '+x': (1, 0)}[side]


def extra_slots(gd):
    """EXTRA as doorways.EXTRA_SLOTS: each doorway's middle on its wall's face, at its floor, its way out."""
    import doorways
    import indoors
    cat = {b['edid']: b for b in indoors.catalogue(gd)}
    got = {}
    for edid, ways in EXTRA.items():
        f = next((f for f, (_n, rr) in gd.forms.items() if rr.tag in ('STAT', 'SCOL') and gd.edid(f) == edid), None)
        if f is None:
            continue
        path = indoors.model_of(gd, None, gd.key(f))
        b = cat.get(edid) or {}
        zs = sorted(d['z'] for d in b.get('doors', ())) or sorted(d['z'] for d in b.get('shut', ()) if not d.get('board'))
        for side, along, wide, floor in ways:
            z = floor if floor is not None else (zs[len(zs) // 2] if zs else 0.0)
            face = wall_face(gd, path, side, along, wide, z)
            if face is None:
                continue
            x, y = (along, face) if side in ('-y', '+y') else (face, along)
            got.setdefault(edid, []).append({'x': round(x, 1), 'y': round(y, 1), 'z': z, 'out': _out_of(side), 'wide': wide,
                                             'from': 'drawn'})
    doorways.EXTRA_SLOTS.clear()
    doorways.EXTRA_SLOTS.update(got)
    return got


def plan(gd, pr, world, rows, make_places=False):
    """make_places: a building with no way in to a place of its own gets an unlocked door in its first empty doorway
    ('needs place': ruin_fresh makes the place), the rest of its doorways wait for it (the next pass makes them back
    doors). Without: those are locked. A door that leads nowhere ('dead') is locked."""
    cat = _catalogue(gd)
    by_ref = {}
    for r in rows:
        by_ref.setdefault(r['ref'], []).append(r)
    out, placed = [], set()
    for r in rows:
        if r['verdict'] == 'dead':
            out.append({'row': r, 'how': 'lock it'})
            continue
        if r['verdict'] != 'nothing' or r.get('from') == 'model':
            continue
        b = cat.get(r['base']) or {}
        front = next((o for o in by_ref[r['ref']] if o['verdict'] == 'linked' and o['by']), None)
        slot = None
        if r.get('from') == 'board':
            slot = next((d for d in b.get('shut', ()) if abs(d['x'] - r['local'][0]) < 1 and abs(d['y'] - r['local'][1]) < 1), None)
        fill = {'row': r}
        if slot is not None and slot.get('board'):
            fill['how'] = 'boards'
            fill['slot'] = slot
        elif front is not None:
            fill['how'] = 'back door'
            fill['front'] = front['by'][1]
        elif make_places and r['ref'] not in placed:
            fill['how'] = 'needs place'
            placed.add(r['ref'])
        elif make_places:
            continue                    # (a back door once its building has its place)
        else:
            fill['how'] = 'locked door'
        out.append(fill)
    return out


def _door_base(gd, cat, base):
    b = cat.get(base) or {}
    if b.get('doors'):
        d = b['doors'][0]
        return d['base'], d.get('s', 1.0), d.get('tx', 0.0), d.get('ty', 0.0)
    f = next((f for f, (_n, rr) in gd.forms.items() if rr.tag == 'DOOR' and gd.edid(f) == FALLBACK_DOOR), None)
    return gd.key(f), 1.0, 0.0, 0.0


def ops(gd, pr, world, fills):
    cat = _catalogue(gd)
    out, rep = [], {'boards': 0, 'back door': 0, 'locked door': 0, 'needs place': 0, 'locked': 0, 'skipped': []}
    for n, f in enumerate(fills):
        r = f['row']
        if f['how'] == 'lock it':               # (a door already there that leads nowhere)
            # (the door's own cell: it can stand in the next cell over from its building's)
            out.append({'op': 'props', 'cell': r['by'][3] if len(r['by']) > 3 else r['cell'], 'ref': r['by'][1], 'props': LOCKED['props']})
            rep['locked'] += 1
            continue
        p, rz, s = r['p'], r['rz'], r['s']
        ox, oy, oz = p[0], p[1], p[2]
        if f['how'] == 'boards':
            d = f['slot']
            dx, dy = _turn(d['x'] * s, d['y'] * s, rz)
            ck = _cell_of(gd, world, ox + dx, oy + dy)
            out.append({'op': 'add', 'cell': ck, 'base': d['base'],
                        'p': [round(ox + dx, 2), round(oy + dy, 2), round(oz + d['z'] * s, 2), d.get('tx', 0.0), d.get('ty', 0.0),
                              round((rz + d['rz']) % math.tau, 4)], 's': d.get('s', 1) * s})
            rep['boards'] += 1
            continue
        base, ds, tx, ty = _door_base(gd, cat, r['base'])
        lx, ly, lz = r['local']
        # the doorway's way out: from the catalogue's door rows the door's own turn; else from the side the slot is on
        b = cat.get(r['base']) or {}
        drow = next((d for d in list(b.get('doors', ())) + list(b.get('shut', ())) if abs(d['x'] - lx) < 1 and abs(d['y'] - ly) < 1), None)
        if drow is not None and not drow.get('board'):
            lrz = drow['rz']
        elif r.get('out'):
            ux, uy = r['out']               # (world already)
            lrz = (math.atan2(-ux, -uy) - rz) % math.tau
        else:
            # (a board slot on a building with no door in the catalogue: face away from the building's middle)
            lrz = math.atan2(-lx, -ly) % math.tau
        dx, dy = _turn(lx * s, ly * s, rz)
        ck = _cell_of(gd, world, ox + dx, oy + dy)
        name = 'dfill%d' % n
        o = {'op': 'add', 'cell': ck, 'base': base, 'name': name,
             'p': [round(ox + dx, 2), round(oy + dy, 2), round(oz + lz * s, 2), tx, ty, round((rz + lrz) % math.tau, 4)], 's': round(ds * s, 3)}
        if f['how'] == 'back door':
            tel = _tel_of(gd, pr, r['cell'], f['front'])
            if not tel:
                f['how'] = 'locked door'
            else:
                out.append(o)
                out.append({'op': 'tel', 'cell': ck, 'ref': '$' + name, 'tel': {'door': tel['door'], 'p': tel['p']}})
                rep['back door'] += 1
                continue
        if f['how'] == 'needs place':
            f['door'] = {'cell': ck, 'name': name, 'p': o['p'], 'base': base}
            out.append(o)
            rep['needs place'] += 1
            continue
        o['extra'] = LOCKED
        out.append(o)
        rep['locked door'] += 1
    return out, rep
