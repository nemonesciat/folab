"""The new-world checklist (Health's "Your worlds" section, /api/tools/worldcheck): what every world a mod makes or
changes outside needs, checked, after what Waikiki went without for days:

- a Pip-Boy map (`pipboy`): a world FOLab made had none, so the Pip-Boy's map was blank and nothing could be fast
  travelled to (worldmap.py);
- a far view (`far`): without one the hills past the loaded cells are the old ground, or nothing ("the distant hills look
  so barren", 20 Nov 2026);
- cell edges that meet (`torn`): two neighbours whose heights disagree along their shared edge show a crack or a cliff
  ("terrain shearing here", 19 Nov 2026: 25 edges);
- water by the sea (`water`): a cell given its own water level over a beach draws a sheet of water in the air ("a panel
  of water above the land", 19 Nov 2026: 13 cells);
- draws (`draws`): the heaviest spots round the mod's cells (drawcount.py; Waikiki's start drew 12,693 at 12 fps).

Each finding: {check, level: 'error'|'warn'|'info', text, cells: [(x, y)], fix: a Big job's key or None}. `run` goes
through every world the mod has cells, land or water in. Read only: nothing changes here.
"""
import os

import drawcount
import land as landmod
import lodgen
import recordio

TORN = 8.0          # heights along a shared edge further apart than this (one VHGT step) are a tear
SIDE = 33


def worlds_of(gd, pr):
    """The worlds the mod has outside cells, land or water in: {world form: set of (x, y) it changed}."""
    keys = set(pr.cells) | set(pr.land) | set(getattr(pr, 'water', {}) or {})
    out = {}
    for w in gd.worlds():
        grid = gd.grid(w)
        if not grid:
            continue
        mine = {xy for xy, c in grid.items() if gd.key(c) in keys}
        if mine:
            out[w] = mine
    return out


def own_world(gd, pr, w):
    return bool(pr.source) and gd.names[w >> 24] == pr.plugin.lower()


def _world_field(gd, pr, w, tag):
    rec = pr.records.get(gd.key(w))
    if rec:
        return recordio.field(rec, tag)
    v = gd.fields(w).get(tag)
    return v.split(b'\0')[0].decode('cp1252', 'replace') if isinstance(v, bytes) else v


def check_pipboy(gd, pr, w, assets):
    if not own_world(gd, pr, w) and gd.key(w) not in pr.records:
        return []               # (the game's own worlds have their maps)
    rec = pr.records.get(gd.key(w))
    if (any(x.get('tag') == 'WNAM' for x in rec.get('subs', [])) if rec else 'WNAM' in gd.fields(w)):
        return []               # (a world under a parent, as the game's Lucky38World: the parent's map is the one shown)
    icon = _world_field(gd, pr, w, 'ICON')
    if not icon:
        return [{'check': 'pipboy', 'level': 'error', 'fix': 'pipboy', 'cells': [],
                 'text': "No Pip-Boy map: the Pip-Boy's map is blank, and nothing can be fast travelled to."}]
    rel = 'textures\\' + icon.replace('/', '\\').lstrip('\\')
    if not (assets and os.path.isfile(os.path.join(assets, rel))) and not gd.find_file(rel):
        return [{'check': 'pipboy', 'level': 'error', 'fix': 'pipboy', 'cells': [],
                 'text': "The Pip-Boy map's picture is missing (%s): the map shows blank." % icon}]
    return [{'check': 'pipboy', 'level': 'info', 'fix': 'pipboy', 'cells': [],
             'text': 'Has a Pip-Boy map. Draw it again after the ground or the buildings change.'}]


def check_far(gd, pr, w, changed_land):
    if not changed_land and not own_world(gd, pr, w):
        return []
    import library
    edid = gd.edid(w).lower()
    files = []
    # (the far ground goes to build/<mod> distant land/ or, made for the mod, into its own files: either counts)
    for top in (lodgen.out_folder(pr), library.assets_dir(pr)):
        lod = os.path.join(top, 'meshes', 'landscape', 'lod')
        for name in (os.listdir(lod) if os.path.isdir(lod) else []):
            if name.lower() == edid:
                for root, _dirs, fs in os.walk(os.path.join(lod, name)):
                    files += [os.path.join(root, f) for f in fs]
    if not files:
        return [{'check': 'far', 'level': 'warn', 'fix': None, 'cells': [],
                 'text': "No far view made for the ground you changed: past the loaded cells the game shows %s. "
                         "World tools' Far view makes it." % ('nothing' if own_world(gd, pr, w) else 'the old ground')}]
    import time
    newest = max(os.path.getmtime(f) for f in files)
    return [{'check': 'far', 'level': 'info', 'fix': None, 'cells': [],
             'text': 'Far view made %s. Make it again after changing the ground or the buildings.' % time.strftime('%d %b %H:%M', time.localtime(newest))}]


def _heights(gd, pr, w, grid, xy, cache):
    if xy not in cache:
        c = grid.get(xy)
        h = None
        if c is not None:
            mine = pr.land.get(gd.key(c))
            if mine and mine.get('h'):
                h = mine['h']
            else:
                entry = gd.land_at(w, xy[0], xy[1])
                if entry:
                    try:
                        h = landmod.decode(gd, entry, {})['h']
                    except Exception:
                        h = None
        cache[xy] = h
    return cache[xy]


def check_torn(gd, pr, w):
    """Shared edges between a cell whose ground the mod changed and its neighbours, that don't meet."""
    grid = gd.grid(w)
    mine = {xy for xy, c in grid.items() if gd.key(c) in pr.land}
    cache, torn, worst = {}, set(), 0.0
    seen = set()
    for (x, y) in mine:
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            pair = tuple(sorted(((x, y), (nx, ny))))
            if pair in seen:
                continue
            seen.add(pair)
            a, b = pair                                  # a is west of or south of b
            ha, hb = _heights(gd, pr, w, grid, a, cache), _heights(gd, pr, w, grid, b, cache)
            if not ha or not hb:
                continue
            if a[0] < b[0]:                              # (east edge of a, west edge of b)
                gap = max(abs(ha[r * SIDE + SIDE - 1] - hb[r * SIDE]) for r in range(SIDE))
            else:                                        # (north edge of a, south edge of b)
                gap = max(abs(ha[(SIDE - 1) * SIDE + c] - hb[c]) for c in range(SIDE))
            if gap > TORN:
                torn.add(a)
                torn.add(b)
                worst = max(worst, gap)
    if not torn:
        return []
    return [{'check': 'torn', 'level': 'error', 'fix': None, 'cells': sorted(torn),
             'text': "%d cells' ground doesn't meet its neighbour's along an edge (up to %d units apart): a crack or a cliff "
                     "shows there in the game. Smooth across the edge with the Ground brush." % (len(torn), round(worst))}]


def check_water(gd, pr, w):
    """A cell with a water level of its own over ground lower than it, beside cells at the world's own level: a sheet
    of water in the air by the sea."""
    grid = gd.grid(w)
    water = getattr(pr, 'water', {}) or {}
    cache, bad = {}, []
    for xy, c in grid.items():
        level = water.get(gd.key(c))
        if level is None:
            continue
        h = _heights(gd, pr, w, grid, xy, cache)
        if not h:
            continue
        under = sum(1 for v in h if v < level) / len(h)
        by_sea = any(gd.key(grid[n]) not in water or water.get(gd.key(grid[n])) is None
                     for n in ((xy[0] + 1, xy[1]), (xy[0] - 1, xy[1]), (xy[0], xy[1] + 1), (xy[0], xy[1] - 1)) if n in grid)
        if under > 0.05 and min(h) < level - 64 and by_sea and max(h) > level - 4:
            bad.append(xy)
    if not bad:
        return []
    return [{'check': 'water', 'level': 'warn', 'fix': None, 'cells': sorted(bad),
             'text': '%d cell%s have a water level of their own over part of their ground, beside cells at the world\'s own '
                     'level: by the sea that draws as a sheet of water in the air. Check each; if there\'s no pond there, '
                     'give it the world\'s level (Outside, the cell\'s Water).' % (len(bad), '' if len(bad) == 1 else 's')}]


def check_draws(gd, pr, w, progress=None):
    spots = drawcount.counter(gd, pr).busiest(w, most=5, progress=progress)
    heavy = [s for s in spots if s['draws'] > drawcount.HEAVY]
    if not heavy:
        return [{'check': 'draws', 'level': 'info', 'fix': None, 'cells': [s['at'] for s in spots[:1]],
                 'text': 'The heaviest spot round your cells draws %s: fine (the game\'s own busiest draws about %s).'
                         % (format(spots[0]['draws'], ',') if spots else 0, format(drawcount.GAME_BUSIEST, ','))}]
    worst = heavy[0]
    level = 'error' if worst['draws'] > drawcount.TOO_MUCH else 'warn'
    return [{'check': 'draws', 'level': level, 'fix': 'plants' if level == 'error' else None, 'cells': [s['at'] for s in heavy],
             'text': '%d spot%s draw more than the game ever does, the worst %s (the game\'s busiest about %s; 12,693 ran at 12 fps). '
                     'The draw count in the 3D view shows what it is there.' % (len(heavy), '' if len(heavy) == 1 else 's',
                                                                                 format(worst['draws'], ','), format(drawcount.GAME_BUSIEST, ','))}]


def run(gd, pr, progress=None):
    """[{world, name, edid, own, findings}] for every world the mod changed outside."""
    import library
    assets = library.assets_dir(pr)
    out = []
    for w, mine in worlds_of(gd, pr).items():
        name = _world_field(gd, pr, w, 'FULL') or gd.edid(w)
        said = (lambda what, d=0, t=0, n=name: progress('%s: %s' % (n, what), d, t)) if progress else None
        if said:
            said('Pip-Boy map and far view')
        changed_land = any(gd.key(gd.grid(w)[xy]) in pr.land for xy in mine)
        f = check_pipboy(gd, pr, w, assets) + check_far(gd, pr, w, changed_land)
        if said:
            said('Cell edges')
        f += check_torn(gd, pr, w)
        if said:
            said('Water')
        f += check_water(gd, pr, w)
        f += check_draws(gd, pr, w, said)
        out.append({'world': gd.key(w), 'name': name, 'edid': gd.edid(w), 'own': own_world(gd, pr, w), 'cells': len(mine), 'findings': f})
    out.sort(key=lambda r: (not r['own'], -r['cells']))
    return out


JOB = {'running': False}


def job(S, start=False):
    """The checklist as a background job (it counts draws round every cell the mod changed: a minute on a big world)."""
    import threading
    if start and not JOB.get('running'):
        if not S.PR:
            raise ValueError('Open or start a mod first.')
        JOB.clear()
        JOB.update(running=True, said='Starting', done=0, total=0)

        def work():
            try:
                with S._lock:
                    JOB.update(worlds=run(S.GD, S.PR, lambda w, d=0, t=0: JOB.update(said=w, done=d, total=t)), ok=True)
            except Exception as e:  # (the page has to hear about it)
                import traceback
                traceback.print_exc()
                JOB.update(error=str(e), ok=False)
            JOB['running'] = False
        threading.Thread(target=work, daemon=True).start()
    return dict(JOB)
