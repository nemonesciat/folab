"""The Castaway's start at Hanauma Bay (docs/waikiki-story-plan.md, "The Castaway", decided 19 Nov 2026):

The slave boat bound for the Vault went down off Koko Head on its way in to the Flotilla. You come to on the sand
inside the bay at dawn, with the wreck on the reef in front of you and what the sea brought in strewn round: planks,
broken crates, barrels, sacks, a cage from the boat's hold on its side. Someone picking over the wreck wakes you; the
Pip-Boy came off the drowned on the beach.

Here: the wreck (`WRECK`) aground on the bay's reef (`REEF`, where it is shallow enough), the flotsam along the
tideline either side of where you lie (`wake`: the first dry sand from the water at `NEAR`), the comber's camp at the
back of the beach, three named markers for what comes later (`SPOTS`: where you lie, where the drowned slaver lies,
where the comber stands over you), and the map marker. People (the comber, the drowned) and the opening's talk come
with the people and quests after the navmesh run. `ops` returns (ops, report, cells, start) with the new game's
start spot (cell, [x, y, z, facing])."""
import math

import ridgeplaces
import shipinside
import townbuild
import worldrec

NEAR = (98500.0, -36200.0)           # (in the bay, off its beach)
REEF = (99300.0, -37600.0)
WRECK = 'Boat02a'
FLOTSAM = [('WoodPlanksGroup01', 3), ('WoodPlanksGroup03', 2), ('WoodPlanksGroup05', 2), ('NVDLC04MilitaryCrateBroken01', 2),
           ('NVDLC04MilitaryCrateBroken02', 1), ('Barrel01', 3), ('CrateGenericNV', 2), ('NVDLC04LootSackEmpty', 2)]
CAGE = 'DeathClawCage'
CAMP = [('CampfireCrafting03', 1), ('NVBedrollL', 1), ('CrateGenericNV', 2), ('Barrel01', 1)]
MARKER = 'XMarkerHeading'
SPOTS = {'wakes': 'FOLabHanaumaWake', 'drowned': 'FOLabHanaumaDrowned', 'comber': 'FOLabHanaumaComber'}
NAMES = {WRECK, CAGE, MARKER} | {e for e, _n in FLOTSAM} | {e for e, _n in CAMP}


def ops(gd, pr, world, side, cat=None):
    import server
    cat = cat if cat is not None else townbuild.load(gd, server.kits_folder())
    B = ridgeplaces.Builder(gd, pr, world, side, cat)
    found = shipinside._forms(gd, NAMES)
    B.key_of.update({e: gd.key(f) for e, f in found.items()})
    rep = {'missing': sorted(NAMES - set(found))}
    g = B.ground
    # where you lie: from out in the bay towards the land (west), the first sand a little over the water
    x, y = NEAR
    while (g.at(x, y) or -1e9) < 24.0 and x > NEAR[0] - 6000:
        x -= 32.0
    wx, wy = x - 120.0, y
    wz = g.at(wx, wy) or 0.0
    rx, ry = REEF
    facing = math.atan2(rx - wx, ry - wy) % math.tau            # (looking out at the wreck)
    pl = ridgeplaces.Place(B, 'hanauma', wx, wy, 0.0)
    pl.taken.append((wx, wy, 90.0))                              # (the spot you lie on kept clear)

    def raw(edid, px, py, pz, rz, tilt=(0.0, 0.0), extra=None):
        ck = B.w.cell_at(px, py)
        if ck is None or edid not in B.key_of:
            return None
        o = {'op': 'add', 'cell': ck, 'base': B.key_of[edid], 'p': [round(px, 1), round(py, 1), round(pz, 1), round(tilt[0], 4), round(tilt[1], 4),
             round(rz % math.tau, 4)], 's': 1}
        if extra:
            o['extra'] = extra
        B.ops.append(o)
        B.cells.add(ck)
        return o
    # the wreck, aground and heeled over
    bg = g.at(rx, ry) or -200.0
    raw(WRECK, rx, ry, bg + 70.0, 2.2, tilt=(0.1, -0.34))
    rep['wreck'] = {'at': [round(rx), round(ry)], 'seabed': round(bg)}
    # the tideline: flotsam along the shore either side of you (north and south of the spot), a cage on its side
    n = 0
    k = 0
    for e, count in FLOTSAM:
        for _ in range(count):
            for tr in range(16):
                along = (-1) ** k * (180.0 + 110.0 * (k // 2) + 37.0 * tr)
                inland = ((k * 53) % 140) - 50.0
                if pl.put(e, wx - inland, wy + along, (k * 1.7 + tr) % math.tau, r=60.0):
                    n += 1
                    break
            k += 1
    cage = False
    for tr in range(24):
        ang = tr * 2.399
        if pl.put(CAGE, wx - 80.0 + math.cos(ang) * (300 + 40 * tr), wy + math.sin(ang) * (300 + 40 * tr), 1.1, r=80.0, tilt=(0.0, 1.45), sink=60.0):
            cage = True
            break
    rep['flotsam'] = n
    rep['cage'] = cage
    # the comber's camp at the back of the beach, where the sand meets the slope up to the road
    cx, cy = wx - 700.0, wy + 500.0
    for tr in range(20):
        if (g.at(cx, cy) or 0.0) < 260.0:
            break
        cx += 40.0
    camp = 0
    for e, count in CAMP:
        for j in range(count):
            for tr in range(10):
                a = j * 2.4 + tr * 0.8 + len(e)
                if pl.put(e, cx + math.cos(a) * (150 + 30 * tr), cy + math.sin(a) * (150 + 30 * tr), a, r=50.0):
                    camp += 1
                    break
    rep['camp'] = {'at': [round(cx), round(cy)], 'things': camp}
    # the spots, named for what comes later
    spots = {'wakes': (wx, wy, facing), 'drowned': (wx + 30.0, wy + 300.0, 0.4), 'comber': (wx - 90.0, wy + 60.0, (facing + math.pi) % math.tau)}
    for what, (sx, sy, sr) in spots.items():
        raw(MARKER, sx, sy, (g.at(sx, sy) or wz) + 4.0, sr, extra={'persistent': True, 'edid': SPOTS[what]})
    B.ops.append(worldrec.marker_op(gd, world, [round(wx - 300.0, 1), round(wy, 1), round((g.at(wx - 300.0, wy) or wz) + 60, 1)], 'Hanauma Bay', 4, flags=3))
    rep['wakes'] = [round(wx), round(wy), round(wz), round(facing, 3)]
    start = (B.w.cell_at(wx, wy), [round(wx, 1), round(wy, 1), round(wz + 8.0, 1), round(facing, 4)])
    moves = [{'op': 'move', 'cell': ck, 'ref': rk, 'p': p} for (ck, rk), p in sorted(B.moved.items()) if (ck, rk) not in B.gone]
    return moves + B.ops, rep, sorted(B.cells), start
