"""Swap the game's Mojave buildings a mod stands for FOLab's own (restyleset.REPLACES), one Undo.

Each of FOLab's restyle pieces is made in the frame of the game building it replaces, with its doorways where the
catalogue stands that building's doors (restyleset's docstring). So a swap is the same ref with another base ('swap'):
its place, its turn and every door, link, lock and shut door beside it stay as they were. What else changes:
  - the piece's files go among the mod's own and its STAT is made (modelsets.put), first in the ops;
  - its lights stand with it (waikikiset.LIGHTS), unless one of its kind is already near (LIGHT_APART);
  - the cells its box reaches are listed (`cells`): their navmeshes were made round the old building's walls, so they
    are made again (navbuild.generate_area) after the swap; and the world's distant blocks (lodobj) drew the old one.

`py -3 app/restyle.py [piece ...]` with FOLAB_HOME set says what a swap of the open mod's Waikiki would do (no save)."""
import math

import landmarks
import modelsets
import restyleset
import waikikiset

CELL = 4096.0


def _edid_of_base(gd, key, cache):
    if key not in cache:
        try:
            cache[key] = gd.edid(gd.from_key(key))
        except (KeyError, ValueError, IndexError):
            cache[key] = None
    return cache[key]


def where(gd, pr, pieces=None):
    """[(cell key, ref key, ref, piece)] of every game building the mod stands outside that a restyle piece replaces (or,
    for restyleset.GAME_SWAPS, piece is ('game', its editor ID))."""
    want = {e: p for e, p in restyleset.REPLACES.items() if pieces is None or p in pieces}
    want.update({e: ('game', e) for e in restyleset.GAME_SWAPS if pieces is None or 'billboards' in pieces})
    cache, out = {}, []
    for ck, cell in pr.cells.items():
        if ck.startswith('+'):
            continue                            # (a place of the mod's own: inside)
        for rk, r in (cell.get('refs') or {}).items():
            b = r.get('base')
            if b and not b.startswith('+') and not r.get('removed'):
                e = _edid_of_base(gd, b, cache)
                if e in want:
                    out.append((ck, rk, r, want[e]))
    return out


def _cells_round(gd, pr, ck, x, y, rz, box):
    """The outside cells a box turned rz at x, y reaches (keys of the mod's world), its own first."""
    try:
        cid = gd.from_key(ck)
        world = gd.ext_cells.get(cid)
        grid = gd.grid(world) if world is not None else {}
    except (KeyError, ValueError, IndexError):
        grid = {}
    got = [ck]
    for bx in (box[0], box[3]):
        for by in (box[1], box[4]):
            tx, ty = landmarks._turn(bx, by, rz)
            k = grid.get((int(math.floor((x + tx) / CELL)), int(math.floor((y + ty) / CELL))))
            if k is not None and gd.key(k) not in got:
                got.append(gd.key(k))
    return got


def ops(gd, pr, pieces=None):
    """(ops, report): the swap of every one the mod stands. report: {'swapped': {piece: n}, 'lights', 'cells': [cell keys
    whose navmesh should be made again], 'refs': [(cell, ref)], 'pieces': {piece: put's info}}."""
    modelsets._all_sets()
    found = where(gd, pr, pieces)
    out, rep = [], {'swapped': {}, 'lights': 0, 'cells': [], 'refs': [], 'pieces': {}}
    base_of = {}
    turn = {}
    for ck, rk, r, piece in [f for f in found if isinstance(f[3], tuple)]:
        names, lift = restyleset.GAME_SWAPS[piece[1]]
        k = turn[piece[1]] = turn.get(piece[1], -1) + 1
        key = next((gd.key(f) for f, (_i, rec) in gd.forms.items() if rec.tag == 'STAT' and gd.edid(f) == names[k % len(names)]), None)             if names[k % len(names)] not in base_of else base_of[names[k % len(names)]]
        if key is None:
            continue
        base_of[names[k % len(names)]] = key
        out.append({'op': 'swap', 'cell': ck, 'ref': rk, 'base': key})
        if lift:
            out.append({'op': 'move', 'cell': ck, 'ref': rk, 'p': r['p'][:2] + [round(r['p'][2] + lift, 1)] + r['p'][3:]})
        rep['swapped'][piece[1]] = rep['swapped'].get(piece[1], 0) + 1
        rep['refs'].append((ck, rk))
    found = [f for f in found if not isinstance(f[3], tuple)]
    for _ck, _rk, _r, piece in found:
        if piece in base_of:
            continue
        put_ops, info = modelsets.put(pr, piece)
        out += put_ops
        base_of[piece] = info['key'] or '$model_' + piece
        rep['pieces'][piece] = {k: info[k] for k in ('edid', 'mesh', 'box', 'triangles')}
    lit = [(r['p'][0], r['p'][1]) for c in pr.cells.values() for r in (c.get('refs') or {}).values()
           if r.get('base') and _edid_of_base(gd, r['base'], {}) in ('FireBrightOrange', 'ExtLightWarm02')] if found else []
    for ck, rk, r, piece in found:
        out.append({'op': 'swap', 'cell': ck, 'ref': rk, 'base': base_of[piece]})
        rep['swapped'][piece] = rep['swapped'].get(piece, 0) + 1
        rep['refs'].append((ck, rk))
        x, y, z = r['p'][:3]
        rz, s = r['p'][5], r.get('s', 1.0)
        for o in waikikiset.lights(gd, pr, piece, x, y, z, rz, s, cell=ck):
            if all(math.hypot(o['p'][0] - a, o['p'][1] - b) > waikikiset.LIGHT_APART for a, b in lit):
                out.append(o)
                lit.append((o['p'][0], o['p'][1]))
                rep['lights'] += 1
        for c in _cells_round(gd, pr, ck, x, y, rz, rep['pieces'][piece]['box']):
            if c not in rep['cells']:
                rep['cells'].append(c)
    return out, rep


if __name__ == '__main__':
    import json
    import sys
    import gamedata
    import project
    import server
    server.not_while_playing = lambda: None
    server.GD = gamedata.GameData()
    server.BR = None
    p = project.Project.open('Waikiki')
    server.load_game(p)
    o, r = ops(server.GD, p, sys.argv[1:] or None)
    print(len(o), 'ops')
    print(json.dumps(r, indent=1))
