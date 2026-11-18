"""The Missouri aground off the Natatorium, and the way aboard through it (the lore: docs/waikiki-lore-additions.md,
"The battleship and the Natatorium").

She lies along the shore on the reef off the Natatorium's sea wall, bow to the Natatorium's own -x (on Waikiki: north,
toward Waikiki and Pearl Harbor), her starboard side to the shore. Not floating: she sits on the bottom at the height
that brings her main deck at the way aboard `RISE` over the sea wall's top, and the sea floor is shaped to her (under her
hull just under it, raised round her to `REEF` over her keel and eased back into the slope by `EASE`), so she reads as
resting on it. Her decks stay level.

The way aboard, all level walking but the tower: the street, up the steps through the arch (historicset.natatorium), along
the walk over the bleachers to the top of the pool's side wall on `SIDE`, along it to the sea wall, then a timber pier
(the game's dock planking on its pylons, at the sea wall's height) `PIER_LONG` out across the shallows, and a scaffold
stair tower lashed to her hull (`tower`: two flights and their landings, pipe and planks) up to the gap in her rails at
the gangway. The bathhouse (a door in the pavilion on that side) is a copy of one of the game's small police stations
for now (`BATHHOUSE`): guardroom, armoury and cells to come. The map marker stands at the arch.

`beach` gives one Undo's ops and a report: everything that stood on her moved with her (in every world that has a copy
of her: the hotels' small worlds), the old gangway, pier and marker out, the new way in. `navmesh_cells` lists the cells
whose navmeshes are to be made again after."""
import math

import battleship
import historicset
import landmarks
import modelsets
import osmplace
import recordio
import roadgen
import shipinside
import shipplace
import townbuild
import worldrec

RISE = 300.0                # (the tower's climb: from the pier, at the sea wall's top, to her main deck)
PIER_LONG = 2048.0          # (eight steps of the dock planking)
SIDE = 1                    # (the pool's side wall the way runs along: +x of the Natatorium; on Waikiki the south one)
TOWER_OUT = 700.0           # (the tower's foot landing reaches this far out from her side)
REEF = 120.0                # (the sea floor round her: up to this over her keel)
NEAR, EASE = 500.0, 2200.0  # (at that height out to NEAR from her side, back to the floor as it was by EASE)
UNDER = 8.0                 # (the floor under her hull this far under it)
BATHHOUSE = ('PrimmSheriffStation', 'FOLabNatBathhouse', 'Natatorium Bathhouse')
BATH_DOOR = 'OffDoorMetalSmL01'     # (its leaf across y, 128 wide, its face to x)
MARKER = ('USS Missouri', 8)
PLANTS = [('v22Fern', -250, 1600, 'Z3', 0.6), ('v22Grass', 220, 1500, 'Z3', 0.8), ('NVDLC02BushA01LeavesOnly', 200, -900, 'Z3', 0.45),
          ('v22Fern', -700, -2050, 'Z1', 0.5), ('v22Grass', -650, 2800, 'Z1', 0.7), ('v22Fern', 600, 2450, 'Z1r', 0.55),
          ('NVDLC02BushA01LeavesOnly', 480, -5560, 'deck', 0.5), ('v22Grass', -460, -5620, 'deck', 0.9)]


# ---------- the stair tower ----------

def tower():
    """The scaffold stair tower in its frame: the origin at her deck's edge, her main deck at z 0, out from her along +x.
    T (the top landing, x 2..382, y -150..150, at 0) is met by flight two coming up along +y at x 300 from M (the middle
    landing, x 220..560, y -500..-337.5, at -RISE/2), which flight one reaches up along -y at x 480 from B (the foot
    landing, x 400..700, y -150..150, at -RISE), where the pier comes in from +x. Pipes from each landing's corners
    down into the sea floor, braced; planks on the landings; a rail round the open sides; lashings to her hull."""
    P = []
    h = RISE / 2.0
    run = h * battleship.LADDER_RUN
    ym = -150.0 - run

    def landing(x0, x1, y0, y1, z):
        battleship._box(P, [x1 - x0, y1 - y0, 14], [(x0 + x1) / 2, (y0 + y1) / 2, z - 14], 'teak', faces={'bottom': 'dark'}, material='wood')
        for x in (x0 + 8, x1 - 8):
            for y in (y0 + 8, y1 - 8):
                battleship._cyl(P, 7, 1400 + z + 60, [x, y, -1400], 'rust', sides=6, caps=False)
        for y in (y0 + 8, y1 - 8):
            battleship._box(P, [x1 - x0, 6, 6], [(x0 + x1) / 2, y, z - 120], 'rust', solid=False)
            battleship._box(P, [x1 - x0, 6, 6], [(x0 + x1) / 2, y, z - 420], 'rust', turn=[0, math.degrees(math.atan2(260, x1 - x0)), 0], solid=False)
    landing(2, 382, -150, 150, 0.0)
    landing(220, 560, ym - 162.5, ym, -h)
    landing(400, 700, -150, 150, -RISE)
    battleship.ladder(P, 480, -150.0, -RISE, ym, -h, wide=130)
    battleship.ladder(P, 300, ym, -h, -150.0, 0.0, wide=130)
    # (rails: pipe at waist height round the open edges, a solid low wall where a fall is: none on the pier's side or hers)
    for ((xa, ya), (xb, yb)), z in ((((382, -150), (382, 150)), 0.0), (((2, 150), (382, 150)), 0.0), (((220, ym - 162.5), (560, ym - 162.5)), -h),
                                  (((560, ym - 162.5), (560, ym)), -h), (((400, 150), (700, 150)), -RISE), (((220, ym - 162.5), (220, ym)), -h)):
        ln = math.hypot(xb - xa, yb - ya)
        yaw = math.degrees(math.atan2(-(xb - xa), yb - ya))
        battleship._box(P, [5, ln, 5], [(xa + xb) / 2, (ya + yb) / 2, z + 80], 'rust', turn=[0, 0, yaw], solid=False)
        battleship._box(P, [20, ln, 90], [(xa + xb) / 2, (ya + yb) / 2, z], None, turn=[0, 0, yaw], solid=True)
    for y in (-120, 0, 120):                         # (lashed to her: chain from the top landing's corners to her side)
        battleship._cyl(P, 4, 260, [4, y, -20], 'rust', sides=5, turn=[0, -160, 0], caps=False)
    return {'name': 'FOLabShipStairTower', 'looks': battleship._looks(), 'parts': P}


modelsets.PIECES.setdefault('mo_tower', {'label': 'Stair tower', 'set': battleship.SET, 'file': 'mo_tower', 'describe': tower, 'edid': 'FOLabShipStairTower'})


# ---------- frames ----------

def local_of(pose, x, y):
    """A world point in a frame at pose (x, y, z, turn): (lx, ly)."""
    c, s = math.cos(pose[3]), math.sin(pose[3])
    dx, dy = x - pose[0], y - pose[1]
    return dx * c - dy * s, dx * s + dy * c


def world_of(pose, lx, ly):
    return shipplace.to_world(pose[0], pose[1], pose[3], lx, ly)


def carry(old, new, p):
    """A placement p [x, y, z, rx, ry, rz] that stood in frame old, as it stands in frame new."""
    lx, ly = local_of(old, p[0], p[1])
    x, y = world_of(new, lx, ly)
    return [round(x, 2), round(y, 2), round(p[2] - old[2] + new[2], 2)] + list(p[3:5]) + [round((p[5] - old[3] + new[3]) % math.tau, 4)]


def on_her(pose, x, y, z=None, pad=150.0):
    """Is x, y over her (her hull's outline at its widest, `pad` more), and z (when given) over her waterline?"""
    lx, ly = local_of(pose, x, y)
    if abs(ly) > battleship.HALF + pad:
        return False
    if abs(lx) > battleship.half_beam(max(-battleship.HALF, min(battleship.HALF, ly))) + pad:
        return False
    return z is None or z > pose[2] + 100.0


def hull_bottom(ly, ax):
    """Her hull's underside at ly along her, ax out from her middle (in her frame), or None where ax is past her side."""
    s = min(1.0, max(0.0, (ly + battleship.HALF) / battleship.LONG))
    sec = list(reversed(battleship.section(s)))                     # (the keel's middle first, out and up to the deck edge)
    if ax > max(w for w, _z in sec):
        return None
    for (w0, z0), (w1, z1) in zip(sec, sec[1:]):
        if w0 <= ax <= w1 and w1 > w0:
            return z0 + (z1 - z0) * (ax - w0) / (w1 - w0)
    return sec[0][1]


# ---------- where she goes ----------

def natatorium(gd, pr, world):
    """The Natatorium's placement in the world: (cell, ref, p) or None."""
    key = modelsets.record_of(pr, 'natatorium')
    city = shipplace.world_cells(gd, world)
    for ck, c in pr.cells.items():
        if ck in city:
            for rk, r in c['refs'].items():
                if key and r.get('base') == key and not r.get('removed'):
                    return ck, rk, r['p']
    return None


def spot(nat_p):
    """(her pose (x, y, z, turn), the tower's (x, y, z, turn), the pier's line (start x, y, step dx, dy, z)) off the
    Natatorium standing at nat_p."""
    n = nat_p[5]
    nat = (nat_p[0], nat_p[1], nat_p[2], n)
    gy = battleship.SPOTS['gangway_y']
    wall_top = nat_p[2] + 260.0
    out = historicset.NAT_SEA - 100.0                               # (the sea wall's outer face)
    tx, ty = world_of(nat, SIDE * historicset.NAT_SIDE, out - PIER_LONG - TOWER_OUT)
    t_turn = (n - math.pi / 2) % math.tau                           # (the tower's +x: the Natatorium's +y, to the shore)
    turn = (n + math.pi / 2) % math.tau                             # (her bow: the Natatorium's -x; her starboard to the shore)
    z = wall_top + RISE - battleship.deck_z(gy)
    hb = battleship.half_beam(gy)
    ox, oy = shipplace.to_world(0, 0, turn, -hb, gy)                # (her starboard deck edge at the gangway, from her middle)
    ship = (tx - ox, ty - oy, round(z, 1), turn)
    tow = (tx, ty, round(wall_top + RISE, 1), t_turn)
    sx, sy = world_of(nat, SIDE * historicset.NAT_SIDE, out)
    ex, ey = world_of(nat, SIDE * historicset.NAT_SIDE, out - 1.0)
    return ship, tow, (sx, sy, ex - sx, ey - sy, wall_top)


# ---------- the floor under and round her ----------

def floor_points(gd, pr, world, ship):
    """{(gx, gy): height} for the land points (128 apart) under and round her, as `REEF` and `EASE` say."""
    ground = roadgen.Ground(gd, pr, world)
    keel = ship[2] + battleship.KEEL
    reef = keel + REEF
    out = {}
    reach = battleship.HALF + EASE
    for gx in range(int((ship[0] - reach) // 128), int((ship[0] + reach) // 128) + 2):
        for gy in range(int((ship[1] - reach) // 128), int((ship[1] + reach) // 128) + 2):
            x, y = gx * 128.0, gy * 128.0
            lx, ly = local_of(ship, x, y)
            if abs(ly) > reach:
                continue
            g = ground.at(x, y)
            if g is None:
                continue
            lyc = max(-battleship.HALF, min(battleship.HALF, ly))
            hb = hull_bottom(lyc, abs(lx)) if abs(ly) <= battleship.HALF else None
            if hb is not None:
                # (just under her where she is low; where her side curves up past the reef's height, the reef)
                want = min(max(g, reef), ship[2] + hb - UNDER)
                if abs(want - g) >= 8:
                    out[(gx, gy)] = round(want / 8.0) * 8.0
                continue
            # (outside her: how far from her side, or from her bow or stern)
            side = max(abs(lx) - battleship.half_beam(lyc), 0.0)
            end = max(abs(ly) - battleship.HALF, 0.0)
            d = math.hypot(side, end)
            if d > EASE or g >= reef:
                continue
            want = reef if d <= NEAR else reef + (g - reef) * (d - NEAR) / (EASE - NEAR)
            if want - g >= 8:
                out[(gx, gy)] = round(want / 8.0) * 8.0
    return out


# ---------- all of it ----------

def _forms(gd, edids):
    return shipinside._forms(gd, edids)


def _old_way(gd, pr, cells_of_world, pose):
    """(cell, ref) of the old gangway, its pier and the marker 'USS Missouri' in those cells."""
    gang = modelsets.record_of(pr, 'mo_gangway')
    found = _forms(gd, (landmarks.DOCK, landmarks.PYLON[0]))
    dockish = {gd.key(f) for f in found.values()}
    gangways = [r['p'] for ck, c in pr.cells.items() if ck in cells_of_world for r in c['refs'].values()
                if gang and r.get('base') == gang and not r.get('removed')]
    out = []
    for ck, c in pr.cells.items():
        if ck not in cells_of_world:
            continue
        for rk, r in c['refs'].items():
            if not rk.startswith('+') or r.get('removed') or not r.get('p'):
                continue
            q = r['p']
            gone = (gang and r.get('base') == gang) or (r.get('marker') or {}).get('name') == MARKER[0]
            if not gone and r.get('base') in dockish:
                for g in gangways:
                    nx, ny = math.cos(g[5]), -math.sin(g[5])
                    dx, dy = q[0] - g[0], q[1] - g[1]
                    if abs(dx * ny - dy * nx) < 64 and 0 < dx * nx + dy * ny < shipinside.PIER_MOST + 3000:
                        gone = True
            if gone:
                out.append((ck, rk))
    return out


def _worlds_with_her(gd, pr, key):
    """{world form: (cell, ref, p)} for every world holding a copy of her."""
    out = {}
    for ck, c in pr.cells.items():
        f = gd.from_key(ck) if not ck.startswith('+') else None
        wf = gd.ext_cells.get(f) if f is not None else None
        if wf is None:
            continue
        for rk, r in c['refs'].items():
            if r.get('base') == key and not r.get('removed') and r.get('p'):
                out[wf] = (ck, rk, r['p'])
    return out


def beach(gd, pr, world, prefix='FOLab'):
    """(ops, report): see the module's docstring."""
    key = modelsets.record_of(pr, shipplace.PIECE)
    if not key:
        raise ValueError("The Missouri isn't in this mod.")
    nat = natatorium(gd, pr, world)
    if not nat:
        raise ValueError("The Natatorium isn't in this world of the mod.")
    here = shipplace.standing(pr, gd, world)
    if not here:
        raise ValueError("The Missouri isn't in this world of the mod.")
    old_p = here[2]
    old = (old_p[0], old_p[1], old_p[2], old_p[5])
    ship, tow, pier = spot(nat[2])
    rep = {'ship': [round(v, 1) for v in ship], 'was': [round(v, 1) for v in old]}
    ops = []
    # her files afresh (the damage), the Natatorium's (its steps and walk), the tower's
    for piece in (shipplace.PIECE, 'natatorium'):
        more, _info = modelsets.put(pr, piece)
        ops += more
    more, info = modelsets.put(pr, 'mo_tower')
    ops += more
    tower_key = info['key'] or '$model_mo_tower'
    red = [(lx, ly) for e, lx, ly, _lz in [('NVLightNeonRed', 0, -1200, 4900)]]     # (the red light on her foremast's top: the mast is down)
    # everything on her, in every world that has her: taken up and put down again in her new place (a thing of the mod's
    # own stays in the cell it was added to, so each goes out and comes in again, everything about it kept)
    moved, gone, doors = 0, 0, {}
    worlds = _worlds_with_her(gd, pr, key)
    for wf, (wck, wrk, wp) in worlds.items():
        wpose = (wp[0], wp[1], wp[2], wp[5])
        cells = shipplace.world_cells(gd, wf)
        grid = gd.grid(wf)
        newpose = (ship[0] + wpose[0] - old[0], ship[1] + wpose[1] - old[1], ship[2], ship[3]) if wf != world else ship
        for ck, rk in _old_way(gd, pr, cells, wpose):
            ops.append({'op': 'remove', 'cell': ck, 'ref': rk})
            gone += 1
        for ck, c in list(pr.cells.items()):
            if ck not in cells:
                continue
            for rk, r in list(c['refs'].items()):
                q = r.get('p')
                if not q or r.get('removed') or not rk.startswith('+') or r.get('base') == modelsets.record_of(pr, 'mo_gangway'):
                    continue
                if not (rk == wrk or on_her(wpose, q[0], q[1], q[2])):
                    continue
                lx, ly = local_of(wpose, q[0], q[1])
                if any(math.hypot(lx - a, ly - b) < 3 for a, b in red) and q[2] - wpose[2] > 3000:
                    ops.append({'op': 'remove', 'cell': ck, 'ref': rk})
                    gone += 1
                    continue
                p = carry(wpose, newpose, q)
                nc = grid.get((int(p[0] // 4096), int(p[1] // 4096)))
                ops.append({'op': 'remove', 'cell': ck, 'ref': rk})
                if nc is None:
                    gone += 1
                    continue
                extra = {k: v for k, v in r.items() if k not in ('base', 'p', 's', 'tel')}
                name = 'mv_%s' % rk[1:]
                op = {'op': 'add', 'cell': gd.key(nc), 'base': r['base'], 'p': p, 's': r.get('s', 1.0), 'name': name}
                if extra:
                    op['extra'] = extra
                ops.append(op)
                if r.get('tel'):
                    doors[rk] = (gd.key(nc), name, r['tel'], wpose, newpose)
                moved += 1
    # the links: a moved door keeps where it leads; whatever led to it (her insides' doors) leads to it where it is now
    for rk, (nck, name, tel, wpose, newpose) in doors.items():
        ops.append({'op': 'tel', 'cell': nck, 'ref': '$' + name, 'tel': dict(tel)})
    for ck, c in pr.cells.items():
        for rk, r in c['refs'].items():
            t = r.get('tel')
            if t and t.get('door') in doors and not r.get('removed'):
                _nck, name, _tel, wpose, newpose = doors[t['door']]
                ops.append({'op': 'tel', 'cell': ck, 'ref': rk, 'tel': {'door': '$' + name, 'p': carry(wpose, newpose, t['p'])}})
    rep.update(moved=moved, removed=gone, doors=len(doors), worlds=len(worlds))
    grid = gd.grid(world)

    def cell_at(x, y):
        c = grid.get((int(x // 4096), int(y // 4096)))
        return gd.key(c) if c is not None else None
    # what the hull would bury on the sea floor where she lies now
    buried = 0
    for ck, c in pr.cells.items():
        if ck not in shipplace.world_cells(gd, world):
            continue
        for rk, r in c['refs'].items():
            q = r.get('p')
            if q and not r.get('removed') and r.get('base') != key and on_her(ship, q[0], q[1], pad=60.0) and q[2] < ship[2] + battleship.deck_z(0) - 60:
                if rk.startswith('+') or not any(o.get('ref') == rk for o in ops):
                    ops.append({'op': 'remove', 'cell': ck, 'ref': rk})
                    buried += 1
    rep['buried'] = buried
    # the tower, the pier
    found = _forms(gd, (landmarks.DOCK, landmarks.PYLON[0], BATH_DOOR) + tuple(p[0] for p in PLANTS))
    ops.append({'op': 'add', 'cell': cell_at(tow[0], tow[1]), 'base': tower_key, 'p': [round(tow[0], 1), round(tow[1], 1), tow[2], 0.0, 0.0, round(tow[3], 4)], 's': 1})
    sx, sy, dx, dy, top = pier
    ground = roadgen.Ground(gd, pr, world)
    dock, pylon = gd.key(found[landmarks.DOCK]), gd.key(found[landmarks.PYLON[0]])
    n = int(round(PIER_LONG / landmarks.DOCK_STEP))
    yaw = math.atan2(dx, dy) % math.tau
    pylons = 0
    for k in range(n):
        d = landmarks.DOCK_STEP * (k + 0.5)
        x, y = sx + dx * d, sy + dy * d
        oz = top - 32.0
        ops.append({'op': 'add', 'cell': cell_at(x, y), 'base': dock, 'p': [round(x, 1), round(y, 1), round(oz, 1), 0.0, 0.0, round(yaw, 4)], 's': 1})
        if k % 2 == 0:
            g = ground.at(x, y)
            z = oz - 224.0 - 97.0                   # (a pylon's top, 97 over its origin, under the planking's underside)
            while g is not None and z + 97.0 > g:
                ops.append({'op': 'add', 'cell': cell_at(x, y), 'base': pylon, 'p': [round(x, 1), round(y, 1), round(z, 1), 0.0, 0.0, round(yaw, 4)], 's': 1})
                pylons += 1
                z -= 335.0
    rep.update(pier=n, pylons=pylons, tower=[round(v, 1) for v in tow])
    # green things where soil gathered on her
    Z = battleship.missouri()['levels']
    zs = {'Z1': Z[0], 'Z3': Z[2], 'Z1r': Z[0] + 250, 'deck': None}
    for e, lx, ly, zk, sc in PLANTS:
        if e not in found:
            continue
        z = zs[zk] if zs[zk] is not None else battleship.deck_z(ly)
        x, y = world_of(ship, lx, ly)
        ops.append({'op': 'add', 'cell': cell_at(x, y), 'base': gd.key(found[e]), 'p': [round(x, 1), round(y, 1), round(ship[2] + z, 1), 0.0, 0.0, round((ly * 0.37) % math.tau, 4)], 's': sc})
    # the bathhouse: a door in the pavilion on the way's side, a copy of the game's place behind it
    natp = nat[2]
    natpose = (natp[0], natp[1], natp[2], natp[5])
    inside = townbuild.grand_inside(gd, BATHHOUSE[0])
    rep['bathhouse'] = None
    if inside and BATH_DOOR in found:
        tag = 'natbath'
        made, kept, door_names = townbuild.inside_ops(gd, inside, tag, BATHHOUSE[1], BATHHOUSE[2])
        ops += made
        # (on the pavilion's face to the pool, at the walk's height, facing the pool: the door's face is its x)
        px = SIDE * 1630.0                       # (the pavilion's inner part: over the side wall's end and the walk)
        x, y = world_of(natpose, px, 120.0 - 10.0)
        face = (natpose[3] - math.pi / 2) % math.tau
        ops.append({'op': 'add', 'cell': cell_at(x, y), 'base': gd.key(found[BATH_DOOR]), 'p': [round(x, 1), round(y, 1), round(natp[2] + historicset.NAT_WALK, 1), 0.0, 0.0, round(face, 4)],
                    's': 1, 'name': tag + 'o'})
        ax, ay = world_of(natpose, px, 120.0 - 120.0)
        arrive_out = [round(ax, 1), round(ay, 1), round(natp[2] + historicset.NAT_WALK + 8, 1), 0.0, 0.0, round((natpose[3] + math.pi) % math.tau, 4)]
        ops.append({'op': 'tel', 'cell': cell_at(x, y), 'ref': '$' + tag + 'o', 'tel': {'door': '$' + tag + 'x', 'p': inside['arrive_in']}})
        ops.append({'op': 'tel', 'cell': '$' + tag, 'ref': '$' + tag + 'x', 'tel': {'door': '$' + tag + 'o', 'p': arrive_out}})
        rep['bathhouse'] = {'things': kept, 'made': [(tag, inside['cell'], door_names)]}
    # the marker at the arch, on the street
    mx, my = world_of(natpose, 0.0, historicset.NAT_STEPS_FOOT + 250.0)
    m = worldrec.marker_op(gd, world, [round(mx, 1), round(my, 1), round((ground.at(mx, my) or natp[2]) + 40.0, 1)], MARKER[0], MARKER[1])
    if m.get('cell'):
        ops.append(m)
    # the sea floor
    W = osmplace.Work(gd, pr, world)
    pts = floor_points(gd, pr, world, ship)
    for (gx, gy), z in pts.items():
        W.put_point(gx, gy, z)
    ops += [{'op': 'land', 'cell': ck, 'land': W.over.land[ck]} for ck in sorted(W.changed)]
    rep['floor'] = {'points': len(pts), 'cells': len(W.changed)}
    rep['navmesh_cells'] = navmesh_cells(gd, world, old, ship, pier, natpose)
    return ops, rep


def navmesh_cells(gd, world, old, ship, pier, natpose):
    """Keys of the city's cells whose navmeshes are to be made again: where she was, where she is, the pier and tower, the
    Natatorium."""
    grid = gd.grid(world)
    out = set()
    for pose in (old, ship):
        for ly in range(-int(battleship.HALF) - 200, int(battleship.HALF) + 400, 1024):
            for lx in (-1400, 0, 1400):
                x, y = world_of(pose, lx, ly)
                c = grid.get((int(x // 4096), int(y // 4096)))
                if c is not None:
                    out.add(gd.key(c))
    sx, sy, dx, dy, _top = pier
    for d in range(0, int(PIER_LONG + TOWER_OUT) + 512, 256):
        c = grid.get((int((sx + dx * d) // 4096), int((sy + dy * d) // 4096)))
        if c is not None:
            out.add(gd.key(c))
    for lx in (-2000, 0, 2000):
        for ly in (-1800, 0, 1200):
            x, y = world_of(natpose, lx, ly)
            c = grid.get((int(x // 4096), int(y // 4096)))
            if c is not None:
                out.add(gd.key(c))
    return sorted(out)
