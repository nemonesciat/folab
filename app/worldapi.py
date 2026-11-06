"""What the World tools ask of the server (web/worldtools.js, web/navtool.js): navmeshes outside and by hand, regions, map
markers, encounter zones, cell details, roads and distant land. server.py hands every /api/w/ request here.

Making navmeshes for many cells takes minutes, so it runs in a thread of its own and the page asks how it's going: it only
reads while it works (the game's files are memory maps, the mod's changes plain dicts), and its result goes in as one Undo."""
import os
import threading

import navbuild
import lodgen
import navedit
import roadgen
import scatter
import worldrec as R

JOB = {'running': False}
LOD_JOB = {'running': False}
_job_lock = threading.Lock()


def _cell_keys(gd, world, cells):
    grid = gd.grid(gd.from_key(world))
    out = []
    for xy in cells:
        c = grid.get(tuple(xy))
        if c is not None:
            out.append(gd.key(c))
    return out


def nav_job(gd, pr, lock, world, cells, apply_ops, label):
    """Start making meshes for these cells."""
    keys = _cell_keys(gd, world, cells)
    if not keys:
        raise ValueError('None of those squares has a cell.')
    with _job_lock:
        if JOB.get('running'):
            raise ValueError('Navmeshes are already being made: wait for those first.')
        JOB.clear()
        JOB.update(running=True, done=0, total=len(keys), world=world)

    def progress(n, total, _ck):
        JOB['done'] = n

    def work():
        try:
            ops, rep = navbuild.generate_area(gd, pr, keys, progress)
            with lock:
                state = apply_ops(pr, label, ops)
            JOB.update(result=rep, state=state, ok=True)
        except Exception as e:  # (whatever goes wrong, the page has to hear about it)
            JOB.update(error=str(e), ok=False)
        JOB['running'] = False
    threading.Thread(target=work, daemon=True).start()
    return dict(JOB)


def nav_status(gd, pr, world):
    w = gd.from_key(world)
    return {'cells': navbuild.world_status(gd, pr, w) if pr else {}, 'job': {k: v for k, v in JOB.items() if k != 'state'}}


def lod_job(gd, pr, world):
    """Make a world's distant land in a thread of its own: it writes only into the mod's folder under build."""
    with _job_lock:
        if LOD_JOB.get('running'):
            raise ValueError('Distant land is already being made.')
        LOD_JOB.clear()
        LOD_JOB.update(running=True, done=0, total=0)

    def progress(n, total):
        LOD_JOB.update(done=n, total=total)

    def work():
        try:
            LOD_JOB.update(result=lodgen.generate(gd, pr, world, lodgen.out_folder(pr), progress=progress), ok=True)
        except Exception as e:  # (whatever goes wrong, the page has to hear about it)
            LOD_JOB.update(error=str(e), ok=False)
        LOD_JOB['running'] = False
    threading.Thread(target=work, daemon=True).start()
    return dict(LOD_JOB)


def scatter_found(gd, pr, world, x, y):
    """What the Scatter brush can put down here: what the game placed round here, and the objects of the regions it's in."""
    w = gd.from_key(world)
    found = scatter.learn(gd, w, x, y)
    sets = list(scatter.SETS)
    mine = R.scatter_set(gd, pr, w, x, y)
    if mine:
        found['region'] = mine
        sets = [('region', 'This region\'s objects')] + sets
    return {'sets': sets, 'found': found}


def get(path, q, gd, pr, ctx):
    """A GET: the answer, or None if it isn't one of these."""
    if path == '/api/w/nav/status':
        return nav_status(gd, pr, q['world'])
    if path == '/api/w/nav/job':
        return dict(JOB)
    if path == '/api/w/nav/meshes':
        return {'cells': [navedit.view(gd, pr, k) for k in q['cells'].split('|') if k]}
    if path == '/api/w/choices':
        return R.choices(gd, pr, set(q['types'].split(',')))
    if path == '/api/w/regions':
        return {'regions': R.regions_list(gd, pr, gd.from_key(q['world']))}
    if path == '/api/w/region':
        return R.region_read(gd, pr, q['key'])
    if path == '/api/w/region/learn':
        return {'objects': R.region_objects_from_game(gd, gd.from_key(q['world']), int(q['x']), int(q['y']))}
    if path == '/api/w/zones':
        return {'zones': R.zones_list(gd, pr, gd.from_key(q['world']))}
    if path == '/api/w/markers':
        return {'markers': R.markers_list(gd, pr, gd.from_key(q['world'])), 'types': R.MARKER_TYPES}
    if path == '/api/w/cell':
        return R.cell_details(gd, pr, q['cell'])
    if path == '/api/w/cell/at':
        return {'cell': R.ckey_of(gd, gd.from_key(q['world']), (int(q['x']), int(q['y'])))}
    if path == '/api/w/encounter/choices':
        return R.encounter_choices(gd, pr)
    if path == '/api/w/lod':
        out = lodgen.report_for(gd, pr, gd.from_key(q['world'])) if pr else {}
        out['made'] = bool(pr and os.path.isdir(lodgen.out_folder(pr)))
        out['installed'] = bool(pr and os.path.isfile(lodgen.manifest_path(pr)))
        out['job'] = {k: v for k, v in LOD_JOB.items()}
        return out
    if path == '/api/w/lod/job':
        return dict(LOD_JOB)
    return None


def post(path, body, gd, pr, ctx):
    """A POST with a mod open: the answer, or None if it isn't one of these."""
    if path == '/api/w/nav/make':
        return {'job': nav_job(gd, pr, ctx['lock'], body['world'], body['cells'], ctx['apply'], 'Generate navmesh')}
    if path == '/api/w/nav/remove':
        ops = navbuild.remove_area(gd, pr, _cell_keys(gd, body['world'], body['cells']))
        return {'state': ctx['apply'](pr, 'Remove navmesh', ops), 'changed': len(ops)}
    if path == '/api/w/nav/edit':
        ops, label, cells = navedit.act(gd, pr, body)
        return {'state': ctx['apply'](pr, label, ops), 'cells': cells}
    if path == '/api/w/lod/make':
        return {'job': lod_job(gd, pr, gd.from_key(body['world']))}
    if path == '/api/w/lod/install':
        ctx['not_playing']()
        return {'files': lodgen.install(pr, gd.data_dir)}
    if path == '/api/w/lod/uninstall':
        ctx['not_playing']()
        return {'files': lodgen.uninstall(pr, gd.data_dir)}
    if path == '/api/w/region/save':
        ops, key = R.region_save(gd, pr, body)
        return {'state': ctx['apply'](pr, 'Region ' + body['region']['edid'], ops), 'key': key}
    if path == '/api/w/region/paint':
        return {'state': ctx['apply'](pr, 'Paint region', R.region_paint(gd, pr, body))}
    if path == '/api/w/zone/save':
        ops, key = R.zone_save(gd, pr, body)
        return {'state': ctx['apply'](pr, 'Zone ' + body['zone']['edid'], ops), 'key': key}
    if path == '/api/w/zone/paint':
        return {'state': ctx['apply'](pr, 'Paint zone', R.zone_paint(gd, pr, body))}
    if path == '/api/w/marker/add':
        w = gd.from_key(body['world'])
        x, y = body['p'][:2]
        z = roadgen.Ground(gd, pr, w).at(x, y)
        if z is None:
            raise ValueError('That\'s off the land.')
        return {'state': ctx['apply'](pr, 'Map marker', [R.marker_op(gd, w, [x, y, z + 32], body['name'], body['type'], body.get('flags', 3))])}
    if path == '/api/w/marker/remove':
        return {'state': ctx['apply'](pr, 'Remove map marker', [{'op': 'remove', 'cell': body['cell'], 'ref': body['ref']}])}
    if path == '/api/w/cell/set':
        return {'state': ctx['apply'](pr, 'Place details', [R.cell_ops(gd, pr, body['cell'], body['set'])])}
    if path == '/api/w/cell/revert':
        return {'state': ctx['apply'](pr, 'Place details as the game has them', [{'op': 'cellinfo_revert', 'cell': body['cell']}])}
    if path == '/api/w/road/make':
        w = gd.from_key(body['world'])
        ops, report = roadgen.road_ops(gd, pr, w, body)
        report['cell_xy'] = [list(gd.cell_grid(gd.from_key(k))) for k in report['cells']]
        return {'state': ctx['apply'](pr, 'Lay a road', ops), 'report': report}
    if path == '/api/w/patrol/make':
        w = gd.from_key(body['world'])
        g = roadgen.Ground(gd, pr, w)
        pts = []
        for p in body['points']:
            z = g.at(p[0], p[1])
            if z is None:
                raise ValueError('A point is off the land.')
            pts.append([p[0], p[1], z + 8])
        ops, rep = R.patrol_ops(gd, pr, dict(body, points=pts))
        rep['name'] = R.recordio.field(next(o['record'] for o in ops if o.get('key') == rep['actor']), 'EDID')
        return {'state': ctx['apply'](pr, 'A patrol', ops), 'report': rep}
    if path == '/api/w/encounter/make':
        w = gd.from_key(body['world'])
        g = roadgen.Ground(gd, pr, w)
        x, y = body['p'][:2]
        z = g.at(x, y)
        if z is None:
            raise ValueError('That\'s off the land.')
        ops = R.encounter_ops(gd, pr, dict(body, p=[x, y, z]))
        for o in ops:
            o['p'][2] = (g.at(o['p'][0], o['p'][1]) or z) + 16
        return {'state': ctx['apply'](pr, 'An encounter spot', ops), 'made': len(ops)}
    return None
