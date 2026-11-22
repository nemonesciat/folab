"""The game's doors on Waikiki's buildings swapped for FOLab's own (doorset), and the hotels' lift doors; one Undo.

`ops(gd, pr)`: each door piece's files among the mod's own and its DOOR record (`door_record`: a copy of the game door
it replaces, its sounds kept, this model, no script), then for every door the mod stands at one of a building's
doorways (doorset.DOORWAYS, within doorset.NEAR of it in the building's frame) a 'swap' of its base and a 'move' to the
doorway as the building stands (its place, turn and scale). The same ref: where it leads (XTEL), what leads to it, its
lock, owner and name stay as they were. The Kilauea's way in goes onto its drum's glass (doorset.KILAUEA). Lift doors
(doorset.LIFTS) in every cell, the hotels' floors and small worlds too: a 'swap' only (same frame); the static copies
the game's lift door has get a static of the same model.

Every world of the mod is looked at: the hotels' small worlds stand copies of the city's buildings and the open hotels.

`check(gd, pr)`: every FOLab door the mod stands, how far from its doorway (should be 0), and the lift doors left.
`apply(gd, pr)`: the ops as one Undo; navmeshes current before stay current (a door is where a door was, its box
closing the same doorway). `py -3 app/doorswap.py` with FOLAB_HOME set says what it would do to the open Waikiki."""
import math

import doorset
import library
import modelsets
import recordio

KEEP = ('EDID', 'OBND', 'FULL', 'MODL', 'SNAM', 'ANAM', 'FNAM')


def _turn(lx, ly, rz):
    c, s = math.cos(rz), math.sin(rz)
    return lx * c + ly * s, -lx * s + ly * c


def _local(x, y, bp, s):
    c, sn = math.cos(bp[5]), math.sin(bp[5])
    dx, dy = x - bp[0], y - bp[1]
    return (dx * c - dy * sn) / s, (dx * sn + dy * c) / s


def spot(bp, s, lx, ly, lz, out_deg):
    """The world's [x y z rx ry rz] of a doorway in a building standing at bp scaled s: a door's -y out of it."""
    tx, ty = _turn(lx * s, ly * s, bp[5])
    return [round(bp[0] + tx, 2), round(bp[1] + ty, 2), round(bp[2] + lz * s, 2), 0.0, 0.0,
            round((bp[5] + math.radians(out_deg + 180.0)) % math.tau, 5)]


class Names:
    """Editor IDs and types of bases, the game's and the mod's, looked up once."""

    def __init__(self, gd, pr):
        self.gd, self.pr, self.cache = gd, pr, {}

    def __call__(self, key):
        if key not in self.cache:
            try:
                if key.startswith('+'):
                    rec = self.pr.records[key]
                    self.cache[key] = (recordio.field(rec, 'EDID'), rec.get('type'))
                else:
                    f = self.gd.from_key(key)
                    self.cache[key] = (self.gd.edid(f), self.gd.forms[f][1].tag)
            except (KeyError, ValueError, IndexError):
                self.cache[key] = (None, None)
        return self.cache[key]


def door_record(gd, game_edid, piece, made):
    """A DOOR of the mod's own: the game's door `game_edid` (its sounds, flags, name) with the piece's model."""
    fid = next(f for f, (_i, r) in gd.forms.items() if r.tag == 'DOOR' and gd.edid(f) == game_edid)
    rec = recordio.load(gd, fid)
    rec['subs'] = [s for s in rec['subs'] if s['tag'] in KEEP]
    recordio.set_field(rec, 'EDID', doorset.PIECES[piece]['edid'], label='Editor ID')
    recordio.set_field(rec, 'MODL', made['mesh'][7:], label='Model')
    for s in rec['subs']:
        if s['tag'] == 'OBND':
            for f, v in zip([f for f in s['fields'] if 'name' in f], made['box']):
                f['value'] = int(v)
    rec.pop('copied_from', None)
    return rec


def _files(pr, piece, write=True):
    """The piece's mesh and pictures among the mod's own files (write=False: only made); what modelsets.build made,
    with 'changed': the files that are new or differ."""
    import os
    made = modelsets.build(piece)
    root = library.assets_dir(pr)
    made['changed'] = [rel for rel, data in made['files'].items()
                       if not os.path.isfile(os.path.join(root, rel)) or open(os.path.join(root, rel), 'rb').read() != data]
    for rel, data in made['files'].items() if write else ():
        full = os.path.join(root, rel)
        if not os.path.isfile(full) or open(full, 'rb').read() != data:
            library._put(root, rel, data)
    return made


def records_of(pr):
    """{(piece, 'DOOR' or 'STAT'): record key} of the door pieces the mod has."""
    want = {v['edid']: k for k, v in doorset.PIECES.items()}
    out = {}
    for k, rec in pr.records.items():
        if k.startswith('+') and rec.get('type') in ('DOOR', 'STAT'):
            e = recordio.field(rec, 'EDID')
            piece = want.get(e) or want.get(e[:-6] if e.endswith('Static') else None)
            if piece:
                out[(piece, rec['type'])] = k
    return out


def _world_of(gd):
    """world(cell key): the world an outside cell is in, or the cell itself (a place inside is a world of its own). The
    hotels' small worlds stand copies of the city at the same spots, so doorways match doors of their own world only."""
    cache = {}

    def world(ck):
        if ck not in cache:
            try:
                w = gd.ext_cells.get(gd.from_key(ck))
            except (KeyError, ValueError, IndexError):
                w = None
            cache[ck] = w if w is not None else ck
        return cache[ck]
    return world


def find(gd, pr):
    """[(cell, ref key, ref, piece, new p or None, new s or None, kind)] of every door the swap takes."""
    name = Names(gd, pr)
    world = _world_of(gd)
    by_cell = {}
    for ck, c in pr.cells.items():
        for rk, r in (c.get('refs') or {}).items():
            if r.get('base') and r.get('p') and not r.get('removed') and r['p'][2] > -20000:
                by_cell.setdefault(ck, []).append((rk, r))
    # the buildings with doorways, by where they stand (world spots), in every cell
    spots = []
    kil = []
    for ck, refs in by_cell.items():
        for rk, r in refs:
            e, t = name(r['base'])
            if e in doorset.DOORWAYS or (e and e.endswith('Open') and e[:-4] in doorset.DOORWAYS):
                s = float(r.get('s') or 1.0)
                for piece, lx, ly, lz, out, game in doorset.DOORWAYS[e if e in doorset.DOORWAYS else e[:-4]]:
                    spots.append((spot(r['p'], s, lx, ly, lz, out), s, piece, game, world(ck)))
            if e in ('FOLabLandmarkKilauea', 'FOLabLandmarkKilaueaOpen'):
                piece, rad, bearing, z, game = doorset.KILAUEA
                b = math.radians(bearing)
                out = (90.0 - bearing) % 360.0                 # (a face looking out along the bearing: 0 +y, 90 +x)
                s = float(r.get('s') or 1.0)
                spots.append((spot(r['p'], s, rad * math.cos(b), rad * math.sin(b), z, out), s, piece, game, world(ck)))
    grid = {}
    for k, sp in enumerate(spots):
        grid.setdefault((sp[4], int(sp[0][0] // 4096), int(sp[0][1] // 4096)), []).append(k)
    found, taken = [], set()
    for ck, refs in by_cell.items():
        for rk, r in refs:
            e, t = name(r['base'])
            if e in doorset.LIFTS:
                found.append((ck, rk, r, doorset.LIFTS[e], None, None, 'lift' if t == 'DOOR' else 'lift static'))
                continue
            if t != 'DOOR':
                continue
            x, y = r['p'][0], r['p'][1]
            best = None
            for gx in (-1, 0, 1):
                for gy in (-1, 0, 1):
                    for k in grid.get((world(ck), int(x // 4096) + gx, int(y // 4096) + gy), ()):
                        p, s, piece, game, _w = spots[k]
                        if e not in game:
                            continue
                        d = math.hypot(p[0] - x, p[1] - y)
                        near = doorset.NEAR * s + (1000 * s if piece == 'door_kilauea' else 0)
                        if d < near and abs(p[2] - r['p'][2]) < 260 * s and (best is None or d < best[0]):
                            best = (d, k)
            if best is None or best[1] in taken:
                continue
            taken.add(best[1])
            p, s, piece, game, _w = spots[best[1]]
            found.append((ck, rk, r, piece, p, s, 'door'))
    return found


def ops(gd, pr, write=True):
    """(ops, report). report: {'swapped': {piece: n}, 'moved_most', 'lifts', 'arrivals', 'cells', 'pieces': {piece:
    triangles}, 'files': the door files new or changed}. write=False: the files aren't written (a dry run)."""
    modelsets._all_sets()
    name = Names(gd, pr)
    found = find(gd, pr)
    have = records_of(pr)
    out, rep = [], {'swapped': {}, 'moved_most': 0.0, 'lifts': 0, 'cells': set(), 'pieces': {}, 'files': []}
    key_of = {}
    leads_to = {}                                   # door ref -> [(cell, ref)] whose link arrives in front of it
    for ock, c in pr.cells.items():
        for ork, orr in (c.get('refs') or {}).items():
            t = orr.get('tel')
            if t and t.get('door') and t.get('p') and not orr.get('removed'):
                leads_to.setdefault(t['door'], []).append((ock, ork, orr))
    rep['arrivals'] = 0
    for ck, rk, r, piece, p, s, kind in found:
        want = 'STAT' if kind == 'lift static' else 'DOOR'
        if (piece, want) not in key_of:
            made = _files(pr, piece, write)
            rep['pieces'][piece] = made['triangles']
            rep['files'] += [f for f in made['changed'] if f not in rep['files']]
            k = have.get((piece, want))
            if not k:
                if want == 'DOOR':
                    game = name(r['base'])[0]
                    rec = door_record(gd, game, piece, made)
                else:
                    rec = modelsets._static(doorset.PIECES[piece]['edid'] + 'Static', made['mesh'][7:], made['box'])
                tag = 'door_%s_%s' % (piece, want)
                out.append({'op': 'record_new', 'record': rec, 'name': tag})
                k = '$' + tag
            key_of[(piece, want)] = k
        out.append({'op': 'swap', 'cell': ck, 'ref': rk, 'base': key_of[(piece, want)]})
        rep['swapped'][piece] = rep['swapped'].get(piece, 0) + 1
        rep['cells'].add(ck)
        if kind.startswith('lift'):
            rep['lifts'] += 1
            continue
        moved = max(abs(a - b) for a, b in zip(r['p'][:3], p[:3]))
        rep['moved_most'] = max(rep['moved_most'], round(moved, 1))
        out.append({'op': 'move', 'cell': ck, 'ref': rk, 'p': p, 's': s})
        # (a door that moved with its building, say reseated up a slope since: whoever arrives by it arrives in front
        # of where it is now. Only the place moves by the door's own shift; doors' origins differ, so only past ARRIVE)
        dz = p[2] - r['p'][2] - doorset.ORIGIN_RISE.get(name(r['base'])[0], 0.0) * (s or 1.0)
        dx, dy = p[0] - r['p'][0], p[1] - r['p'][1]
        if piece == 'door_kilauea':
            # (the way out arrives in front of the door on the plinth, facing out, not where the old one put you)
            ox, oy = -math.sin(p[5]), -math.cos(p[5])
            k = doorset.KILAUEA_ARRIVE * (s or 1.0)
            ar = [round(p[0] + ox * k, 2), round(p[1] + oy * k, 2), round(p[2] + 8 * (s or 1.0), 2), 0.0, 0.0, round((p[5] + math.pi) % math.tau, 5)]
            for ock, ork, orr in leads_to.get(rk, ()):
                out.append({'op': 'tel', 'cell': ock, 'ref': ork, 'tel': dict(orr['tel'], p=ar)})
                rep['arrivals'] += 1
        elif piece not in doorset.HOTELS and max(abs(dx), abs(dy), abs(dz)) > doorset.ARRIVE:
            for ock, ork, orr in leads_to.get(rk, ()):
                t = orr['tel']
                q = list(t['p'])
                q[0], q[1], q[2] = round(q[0] + dx, 2), round(q[1] + dy, 2), round(q[2] + dz, 2)
                out.append({'op': 'tel', 'cell': ock, 'ref': ork, 'tel': dict(t, p=q)})
                rep['arrivals'] += 1
    rep['cells'] = sorted(rep['cells'])
    return out, rep


def check(gd, pr):
    """{'doors': n FOLab doors, 'off_most': the farthest any stands from its doorway, 'game_lifts': lift doors of the
    game's left, 'unlinked': FOLab doors that lead nowhere and aren't locked}."""
    modelsets._all_sets()
    mine = {k: piece for (piece, t), k in records_of(pr).items()}
    left = sum(1 for ck, rk, r, piece, p, s, kind in find(gd, pr) if kind.startswith('lift') and r['base'] not in mine)
    off, n, unlinked = 0.0, 0, 0
    for ck, rk, r, piece, p, s, kind in _found_mine(gd, pr, mine):
        n += 1
        if p is not None:
            off = max(off, max(abs(a - b) for a, b in zip(r['p'][:3], p[:3])))
        lock = (r.get('props') or {}).get('lock') or ((r.get('extra') or {}).get('props') or {}).get('lock')
        if kind == 'door' and not r.get('tel') and not lock:
            unlinked += 1
    return {'doors': n, 'off_most': round(off, 1), 'game_lifts': left, 'unlinked': unlinked}


def _found_mine(gd, pr, mine):
    """The FOLab doors the mod stands, with where their doorway is now (the building may have moved since)."""
    name = Names(gd, pr)
    back = mine
    out, spots = [], []
    for ck, c in pr.cells.items():
        for rk, r in (c.get('refs') or {}).items():
            if r.get('removed') or not r.get('p'):
                continue
            e, t = name(r.get('base') or '')
            if e in doorset.DOORWAYS or (e and e.endswith('Open') and e[:-4] in doorset.DOORWAYS):
                s = float(r.get('s') or 1.0)
                for piece, lx, ly, lz, o, _g in doorset.DOORWAYS[e if e in doorset.DOORWAYS else e[:-4]]:
                    spots.append((piece, spot(r['p'], s, lx, ly, lz, o)))
            if e in ('FOLabLandmarkKilauea', 'FOLabLandmarkKilaueaOpen'):
                piece, rad, bearing, z, _g = doorset.KILAUEA
                b = math.radians(bearing)
                s = float(r.get('s') or 1.0)
                spots.append((piece, spot(r['p'], s, rad * math.cos(b), rad * math.sin(b), z, (90.0 - bearing) % 360.0)))
    for ck, c in pr.cells.items():
        for rk, r in (c.get('refs') or {}).items():
            piece = back.get(r.get('base'))
            if not piece or r.get('removed') or not r.get('p'):
                continue
            if piece.startswith('lift'):
                out.append((ck, rk, r, piece, None, None, 'lift'))
                continue
            near = [p for pc, p in spots if pc == piece and math.hypot(p[0] - r['p'][0], p[1] - r['p'][1]) < 600]
            p = min(near, key=lambda p: math.hypot(p[0] - r['p'][0], p[1] - r['p'][1])) if near else None
            out.append((ck, rk, r, piece, p, None, 'door'))
    return out


def sig_of(gd, pr, ck):
    import onepiece
    return onepiece.sig_of(gd, pr, ck)


def apply(gd, pr, label='FOLab doors for the hotels, homes and lifts'):
    """The ops applied as one Undo; navmeshes that were current before stay marked current. Returns the report."""
    o, rep = ops(gd, pr)
    cells = set(rep['cells'])
    current = {k: m for k, m in pr.navmesh.items() if k in cells and m.get('sig') == sig_of(gd, pr, k)}
    pr.apply(label, o)
    nav = [{'op': 'navmesh', 'cell': k, 'mesh': dict(m, sig=sig_of(gd, pr, k))} for k, m in current.items()]
    if nav:
        pr.apply(label, nav, merge=True)
    rep['navmeshes_kept_current'] = len(nav)
    return rep


if __name__ == '__main__':
    import json
    import gamedata
    import project
    import server
    server.not_while_playing = lambda: None
    server.GD = gamedata.GameData()
    server.BR = None
    p = project.Project.open('Waikiki')
    server.load_game(p)
    o, r = ops(server.GD, p, write=False)
    print(len(o), 'ops')
    print(json.dumps(r, indent=1, default=list))
