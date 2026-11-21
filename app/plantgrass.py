"""FOLab's low plants as the game's own grass (plantgrass.py): the grasses and the small fern grown by the land itself.

Placed one at a time, every tuft and fern is a thing for the game to draw: round the Castaway's start 20,000 of them
took the frame rate down (the user, 20 Nov 2026: "frame rates are way too low now"), and put in clumps to save drawing
they could not follow the ground ("ferns floating in the air everywhere"). The game covers its own ground another
way: a landscape texture (LTEX) names grasses (GNAM, GRAS records), and the game stands them over every quarter of
land the texture lies on, each on the ground where it is and leaning with it (flag 4), drawn in batches by the grass
shader. So FOLab's low plants become grasses:

  - `model`: each piece's one shape written as the game's grass models are (nifmake.build_grass: BSFadeNode, one
    NiTriStrips with the game's stencil, TallGrassShaderProperty and alpha blocks), under meshes\\folab\\grass\\;
  - `ops`: the GRAS records the mod hasn't yet (`KINDS`: density, slopes, sizes as the game's own grasses have them),
    named 'grass_<piece>' for the same apply;
  - `carry`: the ops that add them to the mod's grass-bearing ground (its own LTEX records that have a GNAM already:
    laid only where grass may grow, off roads and beaches; greenground's rules), keeping the grasses they had.

Where grass grows is grassrule.py's, and it is the land's paint that decides it: a step that lays more grass-bearing
ground lays these too. What still stands one at a time is what gives the jungle its shape (taro, ti, heliconia, ferns,
shrubs, trees: plantsplit)."""
import math
import os

import library
import modelmake
import nifmake
import plantsplit as ps
import plantsheet  # noqa: F401  (after plantsplit, whose shrubs it puts on one sheet: one shape, as a grass must be)
import recordio

FOLDER = 'meshes\\folab\\grass'
# piece: (density, min slope, max slope, position range, height range, colour range, wave period, flags). The game's
# green grasses: density 25-45, max slope 40-50, position range 17-32, height range 0.35-0.75, colour range 0.1-0.2,
# wave 12-50, flags 6 (uniform scaling, fit to slope).
KINDS = {
    # (thick: the user, 20 Nov 2026, "im starting to realize im starting at the mojave here. WHERE ARE THE PLANTS": the
    # ground's own grass is what can be lush and cheap; placed plants are held to a budget, plantsplit.BUDGET_CITY)
    'grass_tuft': (60, 0, 60, 26.0, 0.5, 0.15, 30.0, 6),
    'grass_fine': (60, 0, 60, 26.0, 0.5, 0.15, 24.0, 6),
    'grass_dark': (50, 0, 60, 26.0, 0.45, 0.12, 36.0, 6),
    'grass_gold': (36, 0, 60, 28.0, 0.45, 0.15, 30.0, 6),
    'grass_dry': (36, 0, 60, 28.0, 0.45, 0.15, 40.0, 6),
    'grass_lush': (50, 0, 55, 26.0, 0.55, 0.15, 20.0, 6),
    'fern_small': (30, 0, 60, 36.0, 0.5, 0.12, 50.0, 6),
    'ground_fern': (16, 0, 55, 44.0, 0.45, 0.12, 50.0, 6),
    'taro_small': (10, 0, 45, 48.0, 0.4, 0.1, 60.0, 6),
    'shrub_low_a': (12, 0, 45, 52.0, 0.4, 0.12, 60.0, 6),
    'shrub_low_b': (12, 0, 45, 52.0, 0.4, 0.12, 60.0, 6),
    # (the jungle's bigger plants, one shape each now (plantsheet): grown by the ground too, sparsely)
    'taro': (4, 0, 40, 64.0, 0.35, 0.1, 60.0, 6),
    'heliconia': (4, 0, 40, 64.0, 0.35, 0.1, 60.0, 6),
    'ti_red': (3, 0, 40, 64.0, 0.35, 0.1, 60.0, 6),
    'ti_green': (3, 0, 40, 64.0, 0.35, 0.1, 60.0, 6),
}


# how far each sways at its top (the game's grasses: up to 0.75 at a tip); stiff plants hardly at all
SWAY = {'fern_small': 0.08, 'ground_fern': 0.08, 'taro_small': 0.05, 'shrub_low_a': 0.04, 'shrub_low_b': 0.04,
        'taro': 0.04, 'heliconia': 0.04, 'ti_red': 0.03, 'ti_green': 0.03}


def edid_of(piece):
    return 'FOLabGrass' + ''.join(w.title() for w in piece.split('_'))


def model(pr, piece):
    """The grass model of a piece among the mod's files; its path under meshes\\."""
    made = modelmake.make(ps.ms.PIECES[piece]['describe']())
    if len(made['shapes']) != 1:
        raise ValueError('%s has %d shapes: a grass is one' % (piece, len(made['shapes'])))
    root = library.assets_dir(pr)
    for rel, data in ps.ms.build(piece)['files'].items():           # (its picture, as the placed piece has it)
        if rel.lower().endswith('.dds') and not os.path.isfile(os.path.join(root, rel)):
            library._put(root, rel, data)
    rel = FOLDER + '\\' + piece + '.nif'
    data = nifmake.build_grass(edid_of(piece), made['shapes'][0], sway=SWAY.get(piece, 0.3))
    full = os.path.join(root, rel)
    if not os.path.isfile(full) or open(full, 'rb').read() != data:
        library._put(root, rel, data)
    return rel[len('meshes\\'):]


def _data_fields(piece):
    dens, smin, smax, pos, hgt, col, wave, flags = KINDS[piece]
    names = ('Density', 'Min slope', 'Max slope', 'Unknown', 'Units from water', 'Water rule', 'Position range',
             'Height range', 'Colour range', 'Wave period', 'Flags')
    codes = ('B', 'B', 'B', 'B', 'H', 'I', 'f', 'f', 'f', 'f', 'B')
    vals = (dens, smin, smax, 205, 0, 0, pos, hgt, col, wave, flags)
    fields = [{'name': n, 'code': c, 'value': v} for n, c, v in zip(names, codes, vals)]
    fields.insert(5, {'pad': 'cdcd'})
    fields.append({'pad': 'cdcdcd'})                     # (as the game's own are padded)
    return fields


def refresh(pr):
    """'record' ops bringing grasses the mod has already in line with KINDS (and their models written afresh)."""
    import copy
    out = []
    for piece in KINDS:
        k = key_of(pr, piece)
        if not k:
            continue
        path = model(pr, piece)
        rec = copy.deepcopy(pr.records[k])
        for s in rec['subs']:
            if s['tag'] == 'DATA':
                s['fields'] = _data_fields(piece)
            elif s['tag'] == 'MODL':
                s['value'] = path
        if rec != pr.records[k]:
            out.append({'op': 'record', 'key': k, 'record': rec})
    return out


def key_of(pr, piece):
    e = edid_of(piece)
    for k, rec in pr.records.items():
        if rec.get('type') == 'GRAS' and recordio.field(rec, 'EDID') == e:
            return k
    return None


def ops(pr):
    """(ops, {piece: key or '$grass_<piece>'}): the grass records the mod hasn't yet, their models written."""
    out, keys = [], {}
    for piece in KINDS:
        path = model(pr, piece)
        k = key_of(pr, piece)
        if k:
            keys[piece] = k
            continue
        fields = _data_fields(piece)
        rec = {'type': 'GRAS', 'flags': 0, 'src': '', 'subs': [
            {'tag': 'EDID', 'label': 'Editor ID', 'kind': 'z', 'value': edid_of(piece)},
            {'tag': 'OBND', 'label': 'Bounds', 'kind': 'struct', 'fields': [{'name': n, 'code': 'h', 'value': 0} for n in ('X1', 'Y1', 'Z1', 'X2', 'Y2', 'Z2')]},
            {'tag': 'MODL', 'label': 'Model', 'kind': 'z', 'value': path},
            {'tag': 'DATA', 'label': 'Data', 'kind': 'struct', 'fields': fields}]}
        out.append({'op': 'record_new', 'record': rec, 'name': 'grass_' + piece})
        keys[piece] = '$grass_' + piece
    return out, keys


def carry(pr, keys):
    """The ops that add the grasses (keys: their records' keys, made already) to every grass-bearing ground of the mod's
    own, keeping what it carries."""
    import copy
    out = []
    for k, rec in pr.records.items():
        if rec.get('type') != 'LTEX' or not any(s['tag'] == 'GNAM' for s in rec['subs']):
            continue
        r = copy.deepcopy(rec)
        have = {s.get('value') for s in r['subs'] if s['tag'] == 'GNAM'}
        last = max(i for i, s in enumerate(r['subs']) if s['tag'] == 'GNAM')
        add = [{'tag': 'GNAM', 'label': 'Grass', 'kind': 'F', 'value': g} for g in keys.values() if g not in have]
        if add:
            r['subs'][last + 1:last + 1] = add
            out.append({'op': 'record', 'key': k, 'record': r})
    return out


# the wild grounds that grow FOLab's grasses, by the game texture's editor ID: each gets a twin of the mod's own, the same
# picture and the same ground underfoot, with the grasses (the game's grasses its twin had kept). Never pavement, asphalt,
# gravel, sand, water, a road's; never a '...GrassPlain' (the fringe greenground keeps bare on purpose).
WILD = ('LRockCanyonRubble01', 'LRockCanyonRubbleDirt01', 'LDirtPebblesCanyon01', 'Dirt01', 'LMudDirtWasteland01',
        'LScrubDirtStripGreenNV01', 'LGrassGreenSuburbsNoGrass')
CLEAR = 320.0               # a quarter is given grass only if nothing that must stay bare is this near any of it (a grass
#                             sample spreads 256 round it)


def twin_edid(game_edid):
    return 'FOLabGrass' + game_edid


def twins(gd, pr, keys):
    """(ops, {game LTEX key: twin key or '$twin_<edid>'}): a grass-bearing twin of each WILD ground the mod hasn't yet."""
    like = {gd.edid(f): f for f, (_i, r) in gd.forms.items() if r.tag == 'LTEX'}
    have = {recordio.field(r, 'EDID'): k for k, r in pr.records.items() if r.get('type') == 'LTEX'}
    out, got = [], {}
    for e in WILD:
        f = like.get(e)
        if f is None:
            continue
        t = twin_edid(e)
        if t in have:
            got[gd.key(f)] = have[t]
            continue
        src = recordio.load(gd, f)
        subs = [dict(s) for s in src['subs'] if s['tag'] in ('EDID', 'TNAM', 'HNAM', 'SNAM')]
        for s in subs:
            if s['tag'] == 'EDID':
                s['value'] = t
        subs += [{'tag': 'GNAM', 'label': 'Grass', 'kind': 'F', 'value': g} for g in keys.values()]
        out.append({'op': 'record_new', 'record': {'type': 'LTEX', 'flags': 0, 'src': '', 'subs': subs}, 'name': 'twin_' + t})
        got[gd.key(f)] = '$twin_' + t
    return out, got


def spread(gd, pr, world, cells, twin, progress=None):
    """'land' ops giving wild ground its grass-bearing twin (twin: {game LTEX key: twin key}) in every quarter of these
    cells with nothing that must stay bare within CLEAR: a road piece, a building, a landmark, the beach or the sea.
    (ops, {'given': n, 'kept bare: why': n})."""
    import copy
    import land
    import landmarks
    import osmdress
    import roadgen
    import server
    import townbuild
    import understory
    grid = gd.grid(world)
    keys = {gd.key(c) for c in grid.values()}
    on_road = understory._roads(gd, pr, world, keys)
    cat = townbuild.load(gd, server.kits_folder())
    built = osmdress._Stands(osmdress.standing(gd, pr, world, cat), margin=understory.NEAR_BUILT)
    in_mark = understory._in_boxes(list(landmarks.standing(gd, pr, world)) + list(ps.ms.footprints(pr, gd, world)))
    G = roadgen.Ground(gd, pr, world)
    cache, rep, ops = {}, {'given': 0}, []
    for n, xy in enumerate(cells):
        if progress and n % 50 == 0:
            progress('Grass on the wild ground', n, len(cells))
        ck = gd.key(grid[xy])
        form = copy.deepcopy(pr.land.get(ck)) if pr.land.get(ck) else None
        if not form:
            e = gd.land_at(world, *xy)
            form = land.decode(gd, e, cache) if e else None
        if not form or not form.get('q'):
            continue
        changed = False
        for q, quarter in enumerate(form['q']):
            if not any(l.get('key') in twin for l in quarter['layers']) and quarter.get('bkey') not in twin:
                continue
            x0, y0 = xy[0] * 4096 + (q % 2) * 2048, xy[1] * 4096 + (q // 2) * 2048
            why = None
            for j in range(11):
                for i in range(11):
                    x, y = x0 - CLEAR + i * (2048 + 2 * CLEAR) / 10, y0 - CLEAR + j * (2048 + 2 * CLEAR) / 10
                    g = G.at(x, y)
                    why = ('sea or beach' if g is None or g < 24 else 'road' if on_road(x, y) else
                           'building' if built.hit(x, y) or in_mark(x, y) else None)
                    if why:
                        break
                if why:
                    break
            if why:
                rep['kept bare: ' + why] = rep.get('kept bare: ' + why, 0) + 1
                continue
            for l in quarter['layers']:
                if l.get('key') in twin:
                    l['key'] = twin[l['key']]
            if quarter.get('bkey') in twin:
                quarter['bkey'] = twin[quarter['bkey']]
            rep['given'] += 1
            changed = True
        if changed:
            ops.append({'op': 'land', 'cell': ck, 'land': form})
    return ops, rep


HOLD = 0.9                  # a grass-bearing patch's strength: well over the game's threshold (greenground's)
PATCH = 2                   # points each way of a sample a patch covers (the game spreads a sample over 512 units)
CLEAR_PTS = 3               # and every point this far each way must be clear of roads, sea and beach (the game spreads a
#                             sample over 256 each way: 384 keeps blades off the asphalt; 512 left the city's lots bare)
BUILT_PTS = 2               # ...but of a building only the patch itself and a point round it
SAMPLES = (2, 6, 10, 14)
SPARE = 0.08              # a layer no stronger than this anywhere in its quarter may give its place to a grass-bearing one


def paint(gd, pr, world, cells, twin, progress=None):
    """'land' ops laying grass-bearing ground patch by patch (as greenground does): at each of a quarter's 16 grass
    samples whose top ground is wild, the twin of that ground over the sample's patch at HOLD, if every point CLEAR_PTS
    round it is clear of roads, buildings, landmarks, the beach and the sea. The look stays (the twin is the same
    picture as what showed). (ops, report)."""
    import copy
    import land
    import landmarks
    import osmdress
    import roadgen
    import server
    import townbuild
    import understory
    grid = gd.grid(world)
    keys = {gd.key(c) for c in grid.values()}
    on_road = understory._roads(gd, pr, world, keys)
    cat = townbuild.load(gd, server.kits_folder())
    built = osmdress._Stands(osmdress.standing(gd, pr, world, cat), margin=understory.NEAR_BUILT)
    in_mark = understory._in_boxes(list(landmarks.standing(gd, pr, world)) + list(ps.ms.footprints(pr, gd, world)))
    G = roadgen.Ground(gd, pr, world)
    twin_keys = set(twin.values())
    cache, rep, ops = {}, {'patches given': 0, 'already growing': 0}, []
    forms = {}
    bad_at = {}

    def bad(x, y):
        k = (round(x / 128), round(y / 128))
        if k not in bad_at:
            g = G.at(x, y)
            bad_at[k] = ('sea or beach' if g is None or g < 24 else 'road' if on_road(x, y) else
                         'building' if built.hit(x, y) or in_mark(x, y) else None)
        return bad_at[k]
    for n, xy in enumerate(cells):
        if progress and n % 20 == 0:
            progress('Grass on the wild ground', n, len(cells))
        ck = gd.key(grid[xy])
        form = copy.deepcopy(pr.land.get(ck)) if pr.land.get(ck) else None
        if not form:
            e = gd.land_at(world, *xy)
            form = land.decode(gd, e, cache) if e else None
        if not form or not form.get('q'):
            continue
        changed = False
        for q, quarter in enumerate(form['q']):
            qx, qy = (q % 2) * 16, (q // 2) * 16
            for sj in SAMPLES:
                for si in SAMPLES:
                    pt = sj * 17 + si
                    top = quarter.get('bkey')
                    for l in quarter['layers']:
                        if l.get('key') and l['a'][pt] > 0.5:
                            top = l['key']
                    if top in twin_keys:
                        rep['already growing'] += 1
                        continue
                    if top not in twin:
                        continue
                    why = None
                    for dj in range(-CLEAR_PTS, CLEAR_PTS + 1):
                        for di in range(-CLEAR_PTS, CLEAR_PTS + 1):
                            why = bad(xy[0] * 4096 + (qx + si + di) * 128, xy[1] * 4096 + (qy + sj + dj) * 128)
                            # (a building needs only its own footprint kept clear, not the 256 round the patch a road
                            # does: kept as far from them, the city's open lots grew nothing, 20 Nov 2026)
                            if why == 'building' and max(abs(di), abs(dj)) > BUILT_PTS:
                                why = None
                            if why:
                                break
                        if why:
                            break
                    if why:
                        rep['kept bare: ' + why] = rep.get('kept bare: ' + why, 0) + 1
                        continue
                    t = twin[top]
                    layer = next((l for l in quarter['layers'] if l.get('key') == t), None)
                    if layer is not None and not isinstance(layer['a'], list):
                        layer['a'] = list(layer['a'])
                    if layer is None:
                        if len(quarter['layers']) >= 6:
                            # (a quarter's six layers full: one that shows nowhere, or least, there, makes room, if what
                            # it shows anywhere is no more than a trace)
                            spare = min(quarter['layers'], key=lambda l: max(l['a']) if l.get('key') not in twin_keys else 9)
                            if spare.get('key') in twin_keys or max(spare['a']) > SPARE:
                                rep['no room for a layer'] = rep.get('no room for a layer', 0) + 1
                                continue
                            quarter['layers'].remove(spare)
                            rep['spare layer reused'] = rep.get('spare layer reused', 0) + 1
                        layer = {'key': t, 'a': [0.0] * 289}
                        quarter['layers'].append(layer)
                    for dj in range(-PATCH, PATCH + 1):
                        for di in range(-PATCH, PATCH + 1):
                            i, j = si + di, sj + dj
                            if 0 <= i < 17 and 0 <= j < 17:
                                layer['a'][j * 17 + i] = max(layer['a'][j * 17 + i], HOLD)
                    rep['patches given'] += 1
                    changed = True
        if changed:
            forms[ck] = form
    # (and none of it up through what stands there: a beach lounger, 21 Nov 2026)
    clear_under(gd, pr, world, cells=set(by_xy_keys(gd, world, cells)), forms=forms, rep=rep)
    for ck, form in forms.items():
        ops.append({'op': 'land', 'cell': ck, 'land': form})
    return ops, rep


def by_xy_keys(gd, world, cells):
    """The cell keys of these grid squares (x, y)."""
    grid = gd.grid(world)
    return [gd.key(grid[xy]) for xy in cells if xy in grid]


# --- no grass through what stands on the ground ------------------------------------------------------------------------
# (the user, 21 Nov 2026: grass growing up through a beach lounger. The game's grass knows nothing of placed things: a
# sample's nine points spread their weights over 512 units, so anything standing on grass-bearing ground has blades
# through it. Each of the nine points weighs a square round its own spot in the patch (the patch's tent: a quarter of the
# thickness 192 off, nothing at 256), blades moved at random by up to their spacing. Wherever such a square meets a placed
# thing's footprint, that point is made to grow nothing: a grass-bearing layer's strength there moves to the same picture
# with no grass (its plain twin), and a grass-bearing base is covered by that twin. The look stays.)
INFLUENCE = 192.0           # half the side of the square one of a sample's nine points puts blades over (thick enough to see)
JITTER = 32.0               # and a thing's footprint widened by this much (blades are moved at random from their spot)
ON_GROUND = 64.0            # a thing whose underside is more than this over the land (on a roof, a table) is left out
NOT_ON_GRASS = (r'(door|light|lamp|lantern|sign|wire|cable|vine|road|pavement|sidewalk|curb|kerb|plant|tree|bush|grass|'
                r'fern|palm|shrub|marker|fx|flower|weed|taro|heliconia)')


def _overlaps(cx, cy, half, foot):
    """Does the square (centre, half side) meet a turned box? foot: (x, y, cos, sin, x0, y0, x1, y1), local to world as
    settleup turns things: (x + lx cos + ly sin, y - lx sin + ly cos)."""
    px, py, c, s, x0, y0, x1, y1 = foot
    corners = [(px + lx * c + ly * s, py - lx * s + ly * c) for lx, ly in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))]
    sq = [(cx - half, cy - half), (cx + half, cy - half), (cx + half, cy + half), (cx - half, cy + half)]
    for ax in ((1.0, 0.0), (0.0, 1.0), (c, -s), (s, c)):
        a = [p[0] * ax[0] + p[1] * ax[1] for p in corners]
        b = [p[0] * ax[0] + p[1] * ax[1] for p in sq]
        if max(a) < min(b) or max(b) < min(a):
            return False
    return True


def points_under(foot, half=INFLUENCE):
    """{(cell x, cell y): {(quarter, point)}}: every grass sample point whose blades would reach a footprint (`_overlaps`).
    A sample's nine points are rows and columns 1-3, 5-7, 9-11, 13-15 of a quarter: never an edge, so never shared."""
    px, py, c, s, x0, y0, x1, y1 = foot
    xs = [px + lx * c + ly * s for lx in (x0, x1) for ly in (y0, y1)]
    ys = [py - lx * s + ly * c for lx in (x0, x1) for ly in (y0, y1)]
    reach = half + 128.0
    out = {}
    for gy in range(int((min(ys) - reach) // 128), int((max(ys) + reach) // 128) + 2):
        for gx in range(int((min(xs) - reach) // 128), int((max(xs) + reach) // 128) + 2):
            u, v = gx % 32, gy % 32
            i, j = u % 16, v % 16
            if i % 4 == 0 or j % 4 == 0:
                continue                    # (not one of any sample's nine)
            si, sj = (i // 4) * 4 + 2, (j // 4) * 4 + 2
            # (the point's weight is spread round the patch spot two of its steps out from the sample: one step from it)
            cx, cy = (gx + i - si) * 128.0, (gy + j - sj) * 128.0
            if not _overlaps(cx, cy, half, foot):
                continue
            q = (1 if u >= 16 else 0) + (2 if v >= 16 else 0)
            out.setdefault((gx // 32, gy // 32), set()).add((q, j * 17 + i))
    return out


def _layer_of(layers, key, after):
    """The quarter's layer of `key` (made, just over `after` or at the bottom, if there is room), or None."""
    for l in layers:
        if l.get('key') == key:
            if not isinstance(l['a'], list):
                l['a'] = list(l['a'])
            return l
    if len(layers) >= 6:
        return None
    l = {'key': key, 'a': [0.0] * 289}
    layers.insert(layers.index(after) + 1 if after is not None else 0, l)
    return l


def clear_points(form, hits, grows, plain, rep):
    """Makes each (quarter, point) of `hits` in a land form grow nothing (see above). grows(key) -> bool; plain(key) -> the
    same picture with no grass, or None. True if the form changed."""
    changed = False
    for q, n in sorted(hits):
        quarter = form['q'][q]
        layers = quarter['layers']
        for l in list(layers):
            if not l.get('key') or not grows(l['key']) or l['a'][n] <= 0.0:
                continue
            if not isinstance(l['a'], list):
                l['a'] = list(l['a'])
            v, l['a'][n] = l['a'][n], 0.0
            changed = True
            rep['points cleared'] = rep.get('points cleared', 0) + 1
            pk = plain(l['key'])
            twin = _layer_of(layers, pk, after=l) if pk else None
            if twin is None:
                rep['cleared with no plain twin'] = rep.get('cleared with no plain twin', 0) + 1
                continue
            twin['a'][n] = min(1.0, twin['a'][n] + v)
        b = quarter.get('bkey')
        if b and grows(b):
            have = sum(l['a'][n] for l in layers if l.get('key'))
            if have >= 1.0:
                continue
            pk = plain(b)
            twin = _layer_of(layers, pk, after=None) if pk else None
            if twin is None:
                rep['base grows grass, no plain twin'] = rep.get('base grows grass, no plain twin', 0) + 1
                continue
            twin['a'][n] = min(1.0, twin['a'][n] + 1.0 - have)
            changed = True
            rep['points cleared'] = rep.get('points cleared', 0) + 1
    return changed


def ltex_rules(gd, pr):
    """(grows, plain): does an LTEX key carry grass; the same picture with none (by editor ID: a twin's game ground,
    '<edid>Plain', '<edid>NoGrass'), or None."""
    mine = {recordio.field(r, 'EDID'): k for k, r in pr.records.items() if r.get('type') == 'LTEX'}
    game = {}
    for f, (_i, r) in gd.forms.items():
        if r.tag == 'LTEX':
            game.setdefault(gd.edid(f), gd.key(f))
    seen_g, seen_p = {}, {}

    def rec_of(key):
        if key.startswith('+'):
            return pr.records.get(key)
        try:
            return recordio.load(gd, gd.from_key(key))
        except Exception:
            return None

    def grows(key):
        if key not in seen_g:
            rec = rec_of(key) or {}
            seen_g[key] = any(s['tag'] == 'GNAM' and s.get('value') for s in rec.get('subs', ()))
        return seen_g[key]

    def plain(key):
        if key not in seen_p:
            rec = rec_of(key) or {}
            e = recordio.field(rec, 'EDID') if rec.get('subs') else None
            got = None
            if e:
                bare = e[len('FOLabGrass'):] if e.startswith('FOLabGrass') else None
                tries = (bare, bare[:-5] if bare and bare.endswith('Grass') else None, e + 'Plain', e + 'NoGrass',
                         e[:-5] + 'NoGrass' if e.endswith('Grass') else None)
                for t in tries:
                    k = (mine.get(t) or game.get(t)) if t else None
                    if k and not grows(k):
                        got = k
                        break
            seen_p[key] = got
        return seen_p[key]
    return grows, plain


def clear_under(gd, pr, world, cells=None, forms=None, rep=None, progress=None):
    """'land' ops so that no grass grows through the things the mod placed on the ground in these cells (keys; None: every
    cell of the world): settleup's loose kinds but not doors, lights, signs, roads or plants, standing on the land. forms:
    {cell key: land form} already changed (paint's), laid over the mod's land and changed in place; cells changed here are
    added to it. (ops, report)."""
    import copy
    import re
    import types
    import land
    import roadgen
    import settleup
    rep = {} if rep is None else rep
    forms = {} if forms is None else forms
    skip = re.compile(NOT_ON_GRASS, re.I)
    by_xy = {xy: gd.key(c) for xy, c in gd.grid(world).items()}
    G = roadgen.Ground(gd, pr, world)
    solids = types.SimpleNamespace(cache={}, report={'collision': 0, 'drawn': 0, 'unread': 0, 'placed': 0})
    kinds, bounds, hits = {}, {}, {}
    todo = [ck for ck in by_xy.values() if (cells is None or ck in cells) and ck in pr.cells]
    for n, ck in enumerate(todo):
        if progress and n % 50 == 0:
            progress('Keeping grass out from under things', n, len(todo))
        for rk, r in pr.cells[ck].get('refs', {}).items():
            p, b = r.get('p'), r.get('base')
            if not rk.startswith('+') or r.get('removed') or not p or not b:
                continue
            if b not in kinds:
                kinds[b] = (settleup._type(gd, pr, b) in settleup.LOOSE_TYPES
                            and not skip.search(settleup._edid(gd, pr, b) or ''))
                bounds[b] = settleup._bounds(gd, pr, b, solids) if kinds[b] else None
            o = bounds[b]
            if not o:
                continue
            s = float(r.get('s') or 1.0)
            g = G.at(p[0], p[1])
            if g is None or p[2] + o[2] * s - g > ON_GROUND:
                continue
            foot = (p[0], p[1], math.cos(p[5]), math.sin(p[5]), o[0] * s - JITTER, o[1] * s - JITTER,
                    o[3] * s + JITTER, o[4] * s + JITTER)
            rep['things on the ground'] = rep.get('things on the ground', 0) + 1
            for xy, pts in points_under(foot).items():
                hits.setdefault(xy, set()).update(pts)
    if not hits:
        return [], rep
    grows, plain = ltex_rules(gd, pr)
    cache, ops = {}, []
    for xy, pts in sorted(hits.items()):
        ck = by_xy.get(xy)
        if ck is None:
            continue
        form = forms.get(ck)
        if form is None:
            form = copy.deepcopy(pr.land.get(ck)) if pr.land.get(ck) else None
            if not form:
                e = gd.land_at(world, *xy)
                form = land.decode(gd, e, cache) if e else None
        if not form or not form.get('q'):
            continue
        if clear_points(form, pts, grows, plain, rep):
            forms[ck] = form
            ops.append({'op': 'land', 'cell': ck, 'land': form})
    return ops, rep
