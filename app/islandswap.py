"""Swap the Mojave's commonest outdoor things a mod stands for FOLab's island pieces (islandset.REPLACES), one Undo.

Each island piece is made in the frame of the game piece it stands in for, so a swap is the same ref with another base
('swap'); where the game piece stands differently from ours (islandset.LIFT: Honest Hearts' canyon rocks sit on their
origin, the base game's are sunk half) the ref is raised too ('move'). Every ref of the mod's world outside counts: the
game's own ones in its plugin as well as those the mod added. Places of the mod's own (insides) are left.

Small things change no navmesh worth making again (a crate, a chair: the game's meshes cut round neither); the shelter
and the big rocks are listed in `cells` for whoever wants them made again. Nothing here is far-off (only the shelter has a
far model), so lodobj needs running again only for shelters.

`where` reads; `ops` also puts each piece's files and STAT (modelsets.put) first."""
import islandset
import modelsets

BIG = ('tarp_shelter',)                 # (pieces whose cells' navmeshes are worth making again)


def where(gd, pr, pieces=None):
    """[(cell key, ref key, p, game editor ID, piece)] of every game thing the mod's world stands outside that an island
    piece replaces: the plugin's own refs as the mod leaves them, and the mod's added ones."""
    want = {e: p for e, p in islandset.REPLACES.items() if pieces is None or p in pieces}
    edid_of, out = {}, []

    def edid(key):
        if key not in edid_of:
            try:
                edid_of[key] = gd.edid(gd.from_key(key))
            except (KeyError, ValueError, IndexError):
                edid_of[key] = None
        return edid_of[key]
    worlds = set()
    for ck in pr.cells:
        if ck.startswith('+'):
            continue
        try:
            cid = gd.from_key(ck)
        except (KeyError, ValueError, IndexError):
            continue
        if cid in gd.ext_cells:
            worlds.add(gd.ext_cells[cid])
    own_file = (pr.source_path() if getattr(pr, 'source', None) else '').replace('\\', '/').rsplit('/', 1)[-1].lower()
    cells = [cid for cid, w in gd.ext_cells.items() if w in worlds]
    for cid in cells:
        ck = gd.key(cid)
        changed = (pr.cells.get(ck) or {}).get('refs') or {}
        for e in gd.refs(cid):
            rk = gd.key(e['ref'])
            if own_file and not rk.lower().startswith(own_file + ':'):
                continue                    # (a master's ref: the mod's world is its own plugin's)
            ch = changed.get(rk) or {}
            if ch.get('removed') or e['base'] is None:
                continue
            base = ch.get('base') or gd.key(e['base'])
            name = edid(base) if not base.startswith('+') else None
            if name in want:
                p = ch.get('p') or list(e['pos']) + list(e['rot'])
                if p[2] > -20000:
                    out.append((ck, rk, p, name, want[name]))
        for rk, r in changed.items():
            if rk.startswith('+') and not r.get('removed') and r.get('base') and not r['base'].startswith('+'):
                name = edid(r['base'])
                if name in want and r.get('p', [0, 0, 0])[2] > -20000:
                    out.append((ck, rk, r['p'], name, want[name]))
    return out


def ops(gd, pr, pieces=None):
    """(ops, report): report {'swapped': {piece: n}, 'lifted': n, 'cells': [cells of big pieces], 'pieces': {piece: info}}."""
    modelsets._all_sets()
    found = where(gd, pr, pieces)
    out, rep = [], {'swapped': {}, 'lifted': 0, 'cells': [], 'pieces': {}}
    base_of = {}
    for _ck, _rk, _p, _e, piece in found:
        if piece in base_of:
            continue
        put_ops, info = modelsets.put(pr, piece)
        out += put_ops
        base_of[piece] = info['key'] or '$model_' + piece
        rep['pieces'][piece] = {k: info[k] for k in ('edid', 'mesh', 'box', 'triangles')}
    for ck, rk, p, name, piece in found:
        out.append({'op': 'swap', 'cell': ck, 'ref': rk, 'base': base_of[piece]})
        lift = islandset.LIFT.get(name)
        if lift:
            out.append({'op': 'move', 'cell': ck, 'ref': rk, 'p': [p[0], p[1], round(p[2] + lift, 1)] + list(p[3:6])})
            rep['lifted'] += 1
        rep['swapped'][piece] = rep['swapped'].get(piece, 0) + 1
        if piece in BIG and ck not in rep['cells']:
            rep['cells'].append(ck)
    return out, rep


# ---------- the finds, put where they make sense ----------
#
# Each find goes by things of a kind (FINDS: what it goes by, by editor ID, how many of those get one, how far out), seated
# by lootplace.Seat on the land or what stands there (never on a road, in water, in a doorway or another thing's footprint;
# each corner of its underside checked). The island pieces' own spots (the swapped chairs, crates, grills) count too.
FINDS = {
    'coconut': (('FOLabBeachPalmTall', 'FOLabBeachPalmYoung'), 0.3, (40.0, 110.0), 700),
    'pineapple': (('fruit_crates', 'FOLabWaikikiFruitStall', 'FOLabBambooMarketStall'), 0.5, (70.0, 140.0), 400),
    'tiki_mug': (('beach_chair', 'FOLabWaikikiTikiBar', 'FOLabWaikikiLanaiSet1', 'FOLabBeachBar', 'huli_grill'), 0.35, (35.0, 80.0), 400),
    'ukulele': (('CampfireCrafting03', 'beach_chair', 'FOLabBambooHut', 'FOLabBambooHutSmall'), 0.12, (60.0, 130.0), 160),
    'glass_float': (('FOLabWaikikiNetRack', 'FOLabWaikikiCrabPots', 'FOLabWaikikiOutrigger', 'FOLabWaikikiOutriggerRack', 'FOLabWaikikiSampan',
                     'FOLabBambooCanoeShed', 'FOLabBambooDryingRack', 'FOLabBeachUmbrella', 'FOLabWaikikiLifeguardTower'), 0.6, (90.0, 260.0), 240),
}


def finds_ops(gd, pr, found, seed=7, progress=None):
    """(ops, report): the finds' records (record_new, named) and where each stands ('add'). found: where()'s list, so the
    swapped pieces' spots count as what they'll be."""
    import math
    import random
    import lootplace
    rnd = random.Random(seed)
    piece_at = [(ck, p, piece) for ck, _rk, p, _e, piece in found]
    out, rep = [], {'placed': {}, 'tried': {}}
    own = {}
    for k, r in pr.records.items():
        if k.startswith('+'):
            e = next((s.get('value') for s in r.get('subs', []) if s.get('tag') == 'EDID'), None)
            if e:
                own[k] = e
    game_edid = {}
    spots = {k: [] for k in FINDS}
    want = {}
    for k, (by, *_r) in FINDS.items():
        for b in by:
            want.setdefault(b, []).append(k)
    world = None
    for ck, cell in pr.cells.items():
        if ck.startswith('+'):
            continue
        try:
            cid = gd.from_key(ck)
        except (KeyError, ValueError, IndexError):
            continue
        if cid not in gd.ext_cells:
            continue
        world = world if world is not None else gd.ext_cells[cid]
        for rk, r in (cell.get('refs') or {}).items():
            b = r.get('base')
            if not b or r.get('removed') or 'p' not in r:
                continue
            if b.startswith('+'):
                e = own.get(b)
            else:
                if b not in game_edid:
                    try:
                        game_edid[b] = gd.edid(gd.from_key(b))
                    except (KeyError, ValueError, IndexError):
                        game_edid[b] = None
                e = game_edid[b]
            for k in want.get(e, ()):
                spots[k].append((ck, r['p']))
    for ck, p, piece in piece_at:
        for k in want.get(piece, ()):
            spots[k].append((ck, p))
    S = lootplace.Seat(gd, pr, world)
    for k, (by, share, (near, far), most) in FINDS.items():
        name = ITEM_EDID[k]
        made = islandset.build_item(k)
        out.append({'op': 'record_new', 'record': islandset.item_record(gd, k, made), 'name': name})
        _put_item_files(pr, made)
        box = made['box']
        todo = [s for s in spots[k] if rnd.random() < share]
        rnd.shuffle(todo)
        n = 0
        for i, (ck, p) in enumerate(todo):
            if n >= most:
                break
            if progress and i % 100 == 0:
                progress(k, n, most)
            S.load(p[0], p[1])
            for _try in range(4):
                a, d = rnd.uniform(0, 2 * math.pi), rnd.uniform(near, far)
                x, y = p[0] + math.cos(a) * d, p[1] + math.sin(a) * d
                r = max(box[3] - box[0], box[4] - box[1]) / 2
                if not S.free(x, y, r):
                    continue
                g = S.G.at(x, y) if S.G else None
                at = S.at(x, y, rnd.uniform(0, 2 * math.pi), box, g if g is not None else p[2])
                if at is None:
                    continue
                cell = _cell_of(gd, S, at[0], at[1]) or ck
                out.append({'op': 'add', 'cell': cell, 'base': '$' + name, 'p': at, 's': 1.0})
                S.take(x, y, r)
                n += 1
                break
        rep['placed'][k] = n
        rep['tried'][k] = len(todo)
    return out, rep


ITEM_EDID = {k: 'FOLabItem' + ''.join(w.capitalize() for w in k.split('_')) for k in islandset.ITEMS}


def _cell_of(gd, S, x, y):
    return S.by_xy.get((int(x // 4096), int(y // 4096)))


def _put_item_files(pr, made):
    import os
    import library
    root = library.assets_dir(pr)
    for rel, data in made['files'].items():
        full = os.path.join(root, rel)
        if not os.path.isfile(full) or open(full, 'rb').read() != data:
            library._put(root, rel, data)
