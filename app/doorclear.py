"""Doorways you can walk out of: no boards or barricade stood in front of a door that leads somewhere.

townbuild closes a building's doorways nobody goes through with what the game closes them with (`shut`: a door-shaped
static, a DoorBarricade, WoodPlanksGroup boards). Its catalogue counts a shut thing as filling a door's own doorway only
within townbuild.SHUT_SAME (80) of the door, but the game stands its DoorBarricade 75 to 125 out in front of the door
it bars. So where a building's door was given a place behind it, the barricade the game uses when that door is barred
still stood in front: coming out, you were left in the gap between the wall and the boards (the user, 21 Nov 2026,
nv-rs-pad: "exiting a house placed me inside the building shell"; 273 of Waikiki's 1,732 ways out).

`blocking` finds them in a mod as it is (a door with a link, a shut thing within CLEAR of it, not itself a door);
`ops` takes them out. townbuild leaves them out when it stands a building (`in_the_way`)."""
import math

import recordio

CLEAR = 170.0           # a shut thing this near (seen from above) a door that leads somewhere stands in its way...
CLEAR_UP = 150.0        # ...if it is this near in height too
AT_ARRIVAL = 160.0      # ...and this near where you stand coming out (not a barred doorway beside it)
AT_ARRIVAL_BARRICADE = 200.0   # (a DoorBarricade is wide, and always stands before a door of its own: none opens a hole)
SQ = 512.0
WORDS = ('barricade', 'woodplanksgroup')


def is_bar(edid):
    e = (edid or '').lower()
    return any(w in e for w in WORDS)


def in_the_way(door_xy, door_z, x, y, z):
    """Whether a shut thing at (x, y, z) stands in front of a door at door_xy, door_z (either in one frame)."""
    return math.hypot(x - door_xy[0], y - door_xy[1]) < CLEAR and abs(z - door_z) < CLEAR_UP


def _edid(gd, pr, base):
    if base.startswith('+'):
        r = pr.records.get(base)
        return recordio.field(r, 'EDID') if r else ''
    try:
        return gd.edid(gd.from_key(base)) or ''
    except (KeyError, ValueError):
        return ''


def blocking(gd, pr):
    """[(cell, ref, base editor ID, the door it blocks)] for every bar the mod stood in front of one of its own doors
    that leads somewhere."""
    names, out = {}, []
    arrive = {}                         # {door: [where you stand coming out of it]}: the far doors' links name it
    for c in pr.cells.values():
        for ch in (c.get('refs') or {}).values():
            t = ch.get('tel')
            if t and t.get('door') and t.get('p'):
                arrive.setdefault(t['door'], []).append(t['p'])
    doors, bars = [], []                # (outside only: a place's own things are the game's, as it furnished it)
    for ck, c in pr.cells.items():
        if ck.startswith('+') or gd.from_key(ck) in gd.interiors:
            continue
        for rk, ch in (c.get('refs') or {}).items():
            b, p = ch.get('base'), ch.get('p')
            if not p or ch.get('removed'):
                continue
            if ch.get('tel'):
                if rk in arrive:
                    doors.append((rk, p, arrive[rk]))
                continue
            if not b:
                continue
            if b not in names:
                names[b] = _edid(gd, pr, b)
            if is_bar(names[b]):
                bars.append((ck, rk, names[b], p))
    near = {}                           # (doors by square: a bar is filed in the cell it stands in, maybe not the door's)
    for d in doors:
        near.setdefault((int(d[1][0] // SQ), int(d[1][1] // SQ)), []).append(d)
    for ck, rk, e, p in bars:
        reach = AT_ARRIVAL_BARRICADE if 'barricade' in e.lower() else AT_ARRIVAL
        gx, gy = int(p[0] // SQ), int(p[1] // SQ)
        for dk, dp, ap in (d for x in (-1, 0, 1) for y in (-1, 0, 1) for d in near.get((gx + x, gy + y), ())):
            # (near the door seen from above, and beside where you stand coming out: a door up a flight has its
            # barricade at the foot of it, beside you)
            if math.hypot(p[0] - dp[0], p[1] - dp[1]) < CLEAR and                     any(math.hypot(p[0] - a[0], p[1] - a[1]) < reach and abs(p[2] - a[2]) < CLEAR_UP for a in ap):
                out.append((ck, rk, e, dk))
                break
    return out


def ops(gd, pr):
    """(ops, report): each bar in front of a door that leads somewhere taken out."""
    found = blocking(gd, pr)
    o = [{'op': 'remove', 'cell': ck, 'ref': rk} for ck, rk, _e, _d in found]
    kinds = {}
    for _c, _r, e, _d in found:
        kinds[e] = kinds.get(e, 0) + 1
    return o, {'removed': len(o), 'doors': len({d for *_x, d in found}), 'kinds': kinds, 'cells': sorted({ck for ck, *_x in found})}
