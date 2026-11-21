"""What the Land from real maps panel asks of the server (web/mapland.js): files the person brings, the preview and its numbers, the new world as a job of its own,
and the way back. server.py hands every /api/maps/ request here (with itself as srv), outside its lock: reading a file or making a world takes minutes,
and the page has to be able to ask how it's going.

The person's files are copied to maps/ under FOLab's home when they pick them. FOLab fetches nothing. What a world was made from is kept in projects/<mod> maps/made.json, so
OpenStreetMap can be laid on it later (its marker layer beside it, layers.json), and the mod as it was in projects/<mod> before map/, so that it can be put back. (In folders: every .json directly
in projects/ is listed as a mod.)"""
import json
import os
import re
import shutil
import threading
import traceback

import coast
import osmcover
import osmdress
import elevation
import espwrite
import landcover
import roadbed
import worldlife
import landmarks
import landsoft
import mapscale as MS
import mapworld
import navbuild
import osm
import osmplace
import project
import townbuild

CHUNK = 1 << 20
JOB = {'running': False}
OPEN = {'file': None, 'raster': None, 'thumb': None, 'pictures': {}}
_job_lock = threading.Lock()


def maps_dir():
    d = os.path.join(project.HOME, 'maps')
    os.makedirs(d, exist_ok=True)
    return d


def file_path(name):
    p = os.path.join(maps_dir(), os.path.basename(name or ''))
    if not os.path.basename(name or '') or not os.path.isfile(p):
        raise ValueError('That file isn\'t here any more: pick it again.')
    return p


def files():
    out = []
    for n in sorted(os.listdir(maps_dir())):
        p = os.path.join(maps_dir(), n)
        if os.path.isfile(p) and not n.endswith('.tmp'):
            out.append({'name': n, 'size': os.path.getsize(p)})
    return out


def upload(stream, n, name):
    """The file the person picked, copied here as it comes in."""
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', os.path.basename(name or '')).strip()
    if not name:
        raise ValueError('That file has no name.')
    p = os.path.join(maps_dir(), name)
    with open(p + '.tmp', 'wb') as f:
        left = n
        while left > 0:
            b = stream.read(min(CHUNK, left))
            if not b:
                break
            f.write(b)
            left -= len(b)
    if left:
        os.remove(p + '.tmp')
        raise ValueError('The file didn\'t all arrive.')
    os.replace(p + '.tmp', p)
    return {'file': name, 'size': n, 'files': files()}


# ---------- a job at a time ----------

def _start(work, **fields):
    with _job_lock:
        if JOB.get('running'):
            raise ValueError('FOLab is still working on the last one: wait for that first.')
        JOB.clear()
        JOB.update(running=True, said='Starting', done=0, total=0, **fields)

    def run():
        try:
            JOB.update(result=work(), ok=True)
        except Exception as e:  # (whatever goes wrong, the page has to hear about it)
            traceback.print_exc()              # (into FOLab's log: what a problem report needs)
            JOB.update(error=str(e), ok=False)
        JOB['running'] = False
    threading.Thread(target=run, daemon=True).start()
    return dict(JOB)


def _said(what, done=0, total=0):
    JOB.update(said=what, done=done, total=total)


# ---------- opening a file ----------

def raster_of(name):
    """The file as a Raster: the last one opened is kept in memory."""
    if OPEN['file'] != name or OPEN['raster'] is None:
        r = elevation.read_file(file_path(name), lambda n, m: _said('Reading the file', n, m))
        OPEN.update(file=name, raster=r, thumb=None, pictures={})
    return OPEN['raster']


def describe(r, name):
    lo, hi, missing = r.stats()
    mx, my = r.metres_per_pixel()
    geo = r.geo
    d = {'file': name, 'name': r.name, 'kind': r.kind, 'w': r.w, 'h': r.h, 'low': lo, 'high': hi, 'missing': missing, 'notes': r.notes,
         'plain': bool(r.plain and not r.folab), 'folab': bool(r.folab), 'placed': bool(geo), 'mpp': [mx, my] if geo else None}
    if geo and geo['kind'] == 'deg':
        d['where'] = '%.3f, %.3f' % (geo['y0'] - geo['dy'] * (r.h - 1) / 2, geo['x0'] + geo['dx'] * (r.w - 1) / 2)
    return d


def open_job(name):
    file_path(name)

    def work():
        _said('Reading the file')
        r = raster_of(name)
        _said('Drawing it')
        out = describe(r, name)
        out['plan'] = MS.Plan(r, {}).report()
        out['compressions'] = MS.COMPRESSIONS
        out['limits'] = {'soft': MS.SOFT_CELLS, 'hard': MS.HARD_CELLS}
        return out
    return _start(work, kind='open')


def picture(name, q):
    r = raster_of(name)
    opts = {'base': q.get('base'), 'low_m': q.get('low_m'), 'high_m': q.get('high_m'), 'mpp': q.get('mpp'), 'compress': 1, 'exag': 1}
    opts = {k: v for k, v in opts.items() if v not in (None, '')}
    k = json.dumps(opts, sort_keys=True)
    if k not in OPEN['pictures']:
        if OPEN['thumb'] is None:
            OPEN['thumb'] = mapworld.thumbnail(r)
        OPEN['pictures'] = {k: mapworld.shaded(r, OPEN['thumb'], opts)}
    return OPEN['pictures'][k]


# ---------- the new world ----------

def _mod_folder(pr):
    d = os.path.join(project.PROJECTS_DIR, pr.name + ' maps')
    os.makedirs(d, exist_ok=True)
    return d


def _sidecar(pr):
    return os.path.join(_mod_folder(pr), 'made.json')


def read_sidecar(pr):
    try:
        with open(_sidecar(pr), encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def write_sidecar(pr, d):
    with open(_sidecar(pr) + '.tmp', 'w', encoding='utf-8') as f:
        json.dump(d, f, indent=1)
    os.replace(_sidecar(pr) + '.tmp', _sidecar(pr))


def make_job(body, srv):
    if not srv.PR:
        raise ValueError('Start a mod first.')
    srv.not_while_playing()
    name = body['file']
    file_path(name)
    opts = dict(body.get('opts') or {})

    def work():
        _said('Reading the file')
        r = raster_of(name)
        plan = MS.Plan(r, opts)
        rep = plan.report()
        if rep['stop']:
            raise ValueError(rep['stop'])
        grid = MS.heights(plan, _said)
        side = {'file': name, 'opts': opts, 'W': plan.W, 'H': plan.H, 'x0': plan.x0, 'y0': plan.y0, 'col0': plan.col0, 'row0': plan.row0, 'upx': plan.upx, 'upy': plan.upy,
                'base': plan.base, 'k': plan.k, 'compress': plan.compress, 'exag': plan.exag, 'geo': r.geo, 'px_w': r.w, 'px_h': r.h}
        if body.get('bumps'):                # (an OpenStreetMap file: roofs a height file measured, off the flat ground its buildings stand on)
            _said('Taking roofs off the flat ground')
            side['bumps'] = body['bumps']
            _roofs_off(grid, side)
        sea = None
        if body.get('coast'):                # (an OpenStreetMap file: the sea is what's on the water's side of its coastline)
            _said('Reading the coastline')
            data = _osm_data(body['coast'])
            geo = osmplace.Georef(side, data)
            _said('Shaping the sea')
            sea = coast.shape_sea(grid, [[geo.xy(p) for p in line] for line in data.coast], plan.floor)
            if sea and not sea.get('leak'):
                MS.limit_slopes(grid.pts, grid.across, grid.down)
                side['coast'] = body['coast']
        painted = None
        if body.get('paint'):                # (an OpenStreetMap file: the ground painted by what the map says it is)
            data = _osm_data(body['paint'])
            geo = osmplace.Georef(side, data)
            if body.get('road_gap'):         # (side streets thinned for a squeezed world: laying and dressing go by the same)
                side['road_gap'] = float(body['road_gap'])
            painted = osmcover.MapCover(grid, data, geo.xy, osmcover.default_textures(srv.GD), _said, laid=osmplace.layout(data, side)['roads'])
            side['paint'] = body['paint']
        if body.get('relief'):               # (small shape in ground the height file leaves smooth; not under roads and buildings)
            _said('Giving the ground some shape')
            coast.roughen(grid, float(body['relief']), int(body.get('seed', 1)), painted.calm if painted else None)
            MS.limit_slopes(grid.pts, grid.across, grid.down)
            side['relief'] = float(body['relief'])
        tpl = srv.GD.from_key(body['template']) if body.get('template') else next(w for w in srv.GD.worlds() if srv.GD.edid(w) == 'WastelandNV')
        _said('Learning how the game paints its land')
        cover = None
        if body.get('cover'):
            _said('Reading the ground types')
            cover = landcover.Cover(_cover_raster(body['cover']['file']), body['cover']['rows'], r.geo, r.w, r.h, plan.pixel_of, (plan.x0, plan.y0))
        with srv._lock:
            shaped = mapworld.options(plan, grid, srv.GD, tpl, body.get('ltex'), int(body.get('seed', 1)), lambda n, m: _said('Painting and packing the land', n, m), cover or painted)
            _said('Painting and packing the land', 0, plan.count())
            edid = re.sub(r'[^A-Za-z0-9_]', '', body.get('edid') or '')
            name_now = srv.PR.name
            try:
                out = srv.new_world({'name': body.get('name') or '', 'edid': edid, 'template': body.get('template'), 'height': shaped['height'],
                                     'ltex': body.get('ltex')}, shaped)
            except Exception:
                _put_back_after_failure(srv, name_now)
                raise
            _commit_before(name_now)
            d = read_sidecar(srv.PR)
            d[edid] = side
            if cover:
                d[edid]['cover'] = {'file': body['cover']['file'], 'rows': body['cover']['rows']}
            write_sidecar(srv.PR, d)
            stats = dict(grid.stats, cells=plan.count(), world=out['world'], z_low=min(grid.pts), z_high=max(grid.pts))
            if body.get('coast'):
                stats['sea'] = sea or {'none': True}
            if painted:
                stats['ground'] = painted.summary()
            stats['size'] = os.path.getsize(srv.PR.plugin_path())
            if cover and any(row.get('scatter') != 'none' and float(row.get('density') or 0) > 0 for row in body['cover']['rows']):
                w = srv.GD.from_key(out['world'])
                ops, rep = landcover.scatter_ops(srv.GD, srv.PR, w, cover, tpl, mapworld.middle_of(srv.GD, tpl), int(body.get('seed', 1)), progress=_said)
                stats.update(rep)
                if ops:
                    _said('Putting it in the mod')
                    out = dict(srv.edit('Scatter by ground types', ops)['state'], world=out['world'])
            if cover and cover.note:
                stats['note'] = cover.note
        return {'state': out, 'world': out['world'], 'report': stats}
    return _start(work, kind='make')


# ---------- a world grown ----------

def _grown_before(name):
    return os.path.join(project.PROJECTS_DIR, name + ' before grow')


def grow_preview(body, srv):
    """What growing a world to a box would add: cells each way and in all, before anything is made."""
    import mapgrow
    w, side = _side_of(srv, body['world'])
    new, added = mapgrow.grown_side(side, [float(v) for v in body['box']])
    return {'added': dict(zip(('west', 'east', 'north', 'south'), added)), 'cells_now': side['W'] * side['H'],
            'cells_after': new['W'] * new['H'], 'new_cells': new['W'] * new['H'] - side['W'] * side['H'], 'W': new['W'], 'H': new['H']}


def grow_job(body, srv):
    """A world made from a height file grown to a bigger box of the same file (mapgrow.py): new cells made as the world
    was (roofs off the flat, the sea from the coastline, ground painted by what the map says, relief), the old ones as
    they are, the new eased into them. body: world, box [south, west, north, east] in degrees, file (an OpenStreetMap
    file covering the whole box: it stands in for the world's own from now on), seed. The mod's plugin as it was is
    kept in projects/<mod> before grow/ (Undo grow puts it back)."""
    import mapgrow
    srv.not_while_playing()
    w, side = _side_of(srv, body['world'])
    name = body.get('file')
    if name:
        file_path(name)

    def work():
        gd, pr = srv.GD, srv.PR
        edid = gd.edid(w)
        new, added = mapgrow.grown_side(side, [float(v) for v in body['box']])
        if not any(added):
            raise ValueError('The box asked for is no bigger than the world, or reaches past the height file: nothing to add.')
        _said('Reading the height file')
        r = raster_of(side['file'])
        plan = mapgrow.plan_of(r, new)
        side_new = dict(new)
        for k in ('bumps', 'coast', 'paint'):
            if side.get(k) and name:
                side_new[k] = name
        state = {}

        def shape(grid):
            if side_new.get('bumps'):
                _said('Taking roofs off the flat ground')
                _roofs_off(grid, side_new)
            if side_new.get('coast'):
                _said('Shaping the sea')
                data = _osm_data(side_new['coast'])
                geo = osmplace.Georef(side_new, data)
                sea = coast.shape_sea(grid, [[geo.xy(p) for p in line] for line in data.coast], plan.floor)
                if sea and not sea.get('leak'):
                    MS.limit_slopes(grid.pts, grid.across, grid.down)
                state['sea'] = sea
            if side_new.get('paint'):
                data = _osm_data(side_new['paint'])
                geo = osmplace.Georef(side_new, data)
                state['painted'] = osmcover.MapCover(grid, data, geo.xy, osmcover.default_textures(gd), _said, laid=osmplace.layout(data, side_new)['roads'])
            if side_new.get('relief'):
                _said('Giving the ground some shape')
                coast.roughen(grid, float(side_new['relief']), int(body.get('seed', 1)), state['painted'].calm if state.get('painted') else None)
                MS.limit_slopes(grid.pts, grid.across, grid.down)
        _said('The land as the mod has it now')
        old = mapgrow.old_heights(gd, pr, w)
        grid, _fixed, rep = mapgrow.land_grid(plan, old, shape, _said)
        tpl = gd.from_key(body['template']) if body.get('template') else next(x for x in gd.worlds() if gd.edid(x) == 'WastelandNV')
        _said('Learning how the game paints its land')
        shaped = mapworld.options(plan, grid, gd, tpl, None, int(body.get('seed', 1)), None, state.get('painted'))
        todo = sorted(mapgrow.cells_of(new) - set(gd.grid(w)))
        with srv._lock:
            # (the plugin as it was, and what says where it lies, kept to go back to)
            d = _grown_before(pr.name)
            shutil.rmtree(d, ignore_errors=True)
            os.makedirs(d)
            shutil.copy2(pr.source_path(), os.path.join(d, 'source.esp'))
            shutil.copy2(_sidecar(pr), os.path.join(d, 'made.json'))
            with open(os.path.join(d, 'next_id.json'), 'w', encoding='utf-8') as f:
                json.dump({'next_id': pr.next_id, 'edid': edid}, f)
            srv.release_source()
            n = mapgrow.add_cells(gd, pr, w, new, todo, shaped['land_for'], shaped['wet'], lambda a, b: _said('Painting and packing the new land', a, b))
            srv.load_game(pr)
            gd = srv.GD
            w2 = next(x for x in gd.worlds() if gd.edid(x) == edid)
            more = mapgrow.world_record_ops(gd, pr, w2)
            if more:
                srv.PR.apply('Grow the world', more)
            pr.save()
            sc = read_sidecar(pr)
            side_new['added'] = [list(c) for c in todo]
            side_new['grown_from'] = {k: side[k] for k in ('W', 'H', 'x0', 'y0', 'col0', 'row0')}
            sc[edid] = side_new
            write_sidecar(pr, sc)
        out = dict(rep, cells=n, added=dict(zip(('west', 'east', 'north', 'south'), added)), W=new['W'], H=new['H'])
        if state.get('sea') is not None:
            out['sea'] = {k: v for k, v in state['sea'].items() if not isinstance(v, (list, dict))}
        return {'state': srv.state(), 'report': out}
    return _start(work, kind='grow')


def new_cells_of(srv, world):
    """The cells the last growing added to a world (keys), and the world's other cells (keys): what later steps keep to."""
    w, side = _side_of(srv, world)
    added = {tuple(c) for c in side.get('added') or []}
    grid = srv.GD.grid(w)
    return ({srv.GD.key(c) for xy, c in grid.items() if xy in added},
            {srv.GD.key(c) for xy, c in grid.items() if xy not in added}, added)


GROW_STEPS = ('lay', 'buildings', 'dress', 'life', 'seam')       # ('navmesh' too when asked: the long one)
NAV_BATCH = 40


def grow_dress_job(body, srv):
    """The cells the last growing added made into more of the same world, as it was: the map laid (roads, water, pads),
    buildings stood on the new plots with their places behind them, things on the ground, the wild and the camps peopled,
    and the shared edges put back to the old cells' where a step moved them. Each step keeps to the new cells (and works
    only round them: mapgrow.only), nothing of the old cells changes. One Undo a step. body: world, file (the OpenStreetMap
    file the world was grown with), want (as osm/lay), steps (GROW_STEPS by default), seed, insides."""
    import mapgrow
    srv.not_while_playing()
    w, side = _side_of(srv, body['world'])
    name = body['file']
    file_path(name)
    steps = body.get('steps') or GROW_STEPS

    def work():
        gd, pr = srv.GD, srv.PR
        edid = gd.edid(w)
        new_keys, old_keys, added = new_cells_of(srv, body['world'])
        if not added:
            raise ValueError('This world hasn\'t been grown: nothing new to make.')
        reach = mapgrow.ring(added, 1)
        keep = lambda ops: mapgrow.keep_new(gd, ops, old_keys)
        seed = int(body.get('seed', 1))
        report = {'cells': len(added)}
        data = _osm_data(name)
        lay = mapgrow.lay_within(osmplace.layout(data, side), reach)
        if 'lay' in steps:
            want = body.get('want') or {'roads': sorted({r['class'] for r in lay['roads']} - {'track', 'path', 'foot'}), 'buildings': True, 'lakes': True,
                                        'rivers': True, 'streams': False}
            with srv._lock, mapgrow.only(gd, w, reach):
                _said('Laying the map on the new land')
                ops, rep, layer = osmplace.ops_for(gd, pr, w, lay, want, side['compress'], seed, _said)
                ops = keep(ops)
                if ops:
                    srv.edit('Grown: the map laid', ops)
                all_layers = read_layers(pr)
                had = all_layers.get(edid) or {'buildings': [], 'places': [], 'bridges': []}
                for k in ('buildings', 'places', 'bridges'):
                    rows = layer.get(k) or []
                    if k == 'buildings':
                        rows = [r for r in rows if mapgrow.middle_in(r['ring'], added)]
                    elif k == 'places':
                        rows = [r for r in rows if (int(r['p'][0] // 4096), int(r['p'][1] // 4096)) in added]
                    else:
                        rows = [r for r in rows if mapgrow.middle_in(r['line'], added)]
                    had[k] = list(had.get(k) or []) + rows
                all_layers[edid] = had
                with open(_layers_path(pr) + '.tmp', 'w', encoding='utf-8') as f:
                    json.dump(all_layers, f)
                os.replace(_layers_path(pr) + '.tmp', _layers_path(pr))
                report['lay'] = {k: v for k, v in rep.items() if k != 'cell_xy'}
        cat = townbuild.load(gd, srv.kits_folder(), _said)
        rows = [r for r in (read_layers(pr).get(edid) or {}).get('buildings') or [] if mapgrow.middle_in(r['ring'], added)]
        if 'buildings' in steps and any(r.get('pad') for r in rows):
            with srv._lock, mapgrow.only(gd, w, reach):
                _said('Putting up the buildings')
                squeeze = float(side.get('compress') or 1.0)
                ops, rep = townbuild.plan(gd, pr, w, rows, cat, seed, _said, insides=float(body.get('insides', townbuild.INSIDE_SHARE)),
                                          stretch=min(4.0, squeeze) if squeeze >= 1.5 else 1.0)
                made = rep.pop('made', [])
                ops = keep(ops)
                if ops:
                    srv.edit('Grown: buildings', ops)
                    names = dict(pr.names)
                    nav_ops = []
                    for k, (tag, _fam, src, doors) in enumerate(made):
                        _said('Making the places\' navmeshes', k, len(made))
                        key = names.get(tag)
                        if not key:
                            continue
                        data_ = townbuild.copied_navmesh(gd, pr, src, key, {g: names[n] for g, n in doors.items() if n in names})
                        if not data_:
                            try:
                                data_, _r = navbuild.generate(gd, pr, key)
                            except navbuild.NavError:
                                continue
                        nav_ops.append({'op': 'navmesh', 'cell': key, 'mesh': data_})
                    if nav_ops:
                        pr.apply('Grown: buildings', nav_ops, merge=True)
                    if made:
                        _said('Making repeated places their own')
                        import roomvary
                        rep['varied'] = roomvary.vary(gd, pr, merge=True, label='Grown: buildings')
                report['buildings'] = {k: v for k, v in rep.items() if not isinstance(v, (list, dict))}
        if 'dress' in steps:
            cover, _lay_all = map_cover(srv, body['world'], name, _said)
            with srv._lock, mapgrow.only(gd, w, reach):
                _said('Things on the new ground')
                ops, rep = osmdress.ops(gd, pr, w, cover, lay['roads'], seed, _said)
                more, rep['footings'] = osmdress.footings(gd, pr, w, cover, cat, seed, _said)
                ops += more
                more, rep['life'] = osmdress.life(gd, pr, w, cover, cat, seed, _said)
                ops += more
                more, rep['lots'] = osmdress.lots(gd, pr, w, cover, cat, rows, seed, _said)
                ops += more
                more, rep['scenes'] = osmdress.scenes(gd, pr, w, cover, lay['roads'], cat, seed, _said)
                ops += more
                marks = landmarks.standing(gd, pr, w)
                ops = landmarks.clear_of(ops, marks)
                inside = osmdress._Stands(osmdress.standing(gd, pr, w, cat), margin=24.0)
                ops = keep([o for o in ops if o.get('op') != 'add' or not inside.hit(o['p'][0], o['p'][1])])
                if ops:
                    srv.edit('Grown: things on the ground', ops)
                spots = [s for s in (rep['scenes'].get('spots') or []) if (int(s[0] // 4096), int(s[1] // 4096)) in added]
                kept = _kept(pr, 'scenes.json')
                kept[edid] = list(kept.get(edid) or []) + spots
                _kept(pr, 'scenes.json', kept)
                standing = osmdress.keep_of(osmdress.standing(gd, pr, w, cat)) + marks
                soft, rep['ground'] = landsoft.soften(gd, pr, w, standing, [(r['line'], osmdress.EDGE.get(r.get('class'), 300.0) * 0.8) for r in lay['roads']], _said)
                if keep(soft):
                    pr.apply('Grown: things on the ground', keep(soft), merge=True)
                _said('Laying the roads in the ground')
                bedded, rep['roads'] = roadbed.bed(gd, pr, w, osmdress.keep_of(osmdress.standing(gd, pr, w, cat)) + marks, _said)
                if keep(bedded):
                    pr.apply('Grown: things on the ground', keep(bedded), merge=True)
                more, rep['rough'] = osmdress.rough_roads(gd, pr, w, cover, lay['roads'], cat, seed, _said)
                more = keep(landmarks.clear_of(more, marks))
                if more:
                    pr.apply('Grown: things on the ground', more, merge=True)
                more, rep['seated'] = osmdress.seat_lying(gd, pr, w, _said)
                if keep(more):
                    pr.apply('Grown: things on the ground', keep(more), merge=True)
                report['dress'] = {k: (v if not isinstance(v, dict) else {a: b for a, b in v.items() if not isinstance(b, (list, dict))})
                                   for k, v in rep.items() if not isinstance(v, list)}
        if 'life' in steps:
            cover, _l = map_cover(srv, body['world'], name, _said)
            with srv._lock:
                _said('Who lives on the new land')
                ops = mapgrow.cellinfo_ops(gd, pr, w, added, (pr.newgame or {}).get('p'))
                with mapgrow.only(gd, w, added):
                    start = ((pr.newgame or {}).get('p') or [0.0, 0.0])[:2]
                    P = osmdress._Putter(gd, pr, w, cover)
                    L = worldlife.Life(gd, pr, w, start, seed)
                    inside = osmdress._Stands(osmdress.standing(gd, pr, w, cat), margin=120.0)
                    marks = landmarks.standing(gd, pr, w)
                    within = lambda x, y: inside.hit(x, y) or len(landmarks.clear_of([{'op': 'add', 'p': [x, y]}], marks)) == 0
                    L.blocked = within
                    spots = [s for s in (_kept(pr, 'scenes.json').get(edid) or []) if (int(s[0] // 4096), int(s[1] // 4096)) in added]
                    L.people(spots)
                    L.wildlife(P.kind, lambda x, y: within(x, y) or P.kind(x, y) in ('asphalt', 'seabed', None))
                    more, rep = L.done()
                ops += keep(more)
                if ops:
                    srv.edit('Grown: life', ops)
                report['life'] = rep
        if 'seam' in steps:
            with srv._lock:
                ops = mapgrow.seam_ops(gd, pr, w, added)
                if ops:
                    srv.edit('Grown: edges joined', ops)
                report['seam'] = len(ops)
        if 'navmesh' in steps:
            # (the new land's cells, a batch at a time, each joined to whatever is round it: the old cells at the edge are
            # made again as copies with links to the new, nothing else of them changes; about 4.5 s a cell)
            G = __import__('roadgen').Ground(gd, pr, w)
            grid = gd.grid(w)
            todo = sorted(gd.key(grid[xy]) for xy in added if xy in grid and max(G.cell(xy) or [-1]) >= 0)
            if body.get('nav_limit'):
                todo = todo[:int(body['nav_limit'])]
            made = missed = 0
            first = True
            for b in range(0, len(todo), NAV_BATCH):
                part = todo[b:b + NAV_BATCH]
                _said('Navmeshes for the new land', b, len(todo))
                with srv._lock:
                    try:
                        o, rep = navbuild.generate_area(gd, pr, part)
                    except navbuild.NavError:
                        o = []
                        for k in part:
                            try:
                                o1, _r = navbuild.generate_area(gd, pr, [k])
                                pr.apply('Grown: navmeshes', o1, merge=not first)
                                first = False
                                made += 1
                            except navbuild.NavError:
                                missed += 1
                        continue
                    pr.apply('Grown: navmeshes', o, merge=not first)
                    first = False
                    made += rep['cells']
            report['navmesh'] = {'cells': len(todo), 'made': made, 'missed': missed}
        return {'state': srv.state(), 'report': report}
    return _start(work, kind='grow_dress')


# ---------- going back to before the world ----------

def _before(name):
    return os.path.join(project.PROJECTS_DIR, name + ' before map')


def keep_before(pr, edid):
    """The mod as it is, kept before a world is made from a map, to go back to. It only takes the place of the last one kept once the new world has been made."""
    d = _before(pr.name) + ' new'
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d)
    src = pr.source_path()
    if src and os.path.isfile(src):
        shutil.copy2(src, os.path.join(d, 'source.esp'))
    with open(os.path.join(d, 'project.json'), 'w', encoding='utf-8') as f:
        json.dump({'edid': edid, 'project': pr.to_dict()}, f)


def _commit_before(name):
    shutil.rmtree(_before(name), ignore_errors=True)
    os.replace(_before(name) + ' new', _before(name))


def undo_label(pr):
    """What Undo says when there's nothing else to undo: the world, if nothing has been changed since it was made."""
    if pr.undo_stack or pr.count():
        return None
    p = os.path.join(_before(pr.name), 'project.json')
    if not os.path.isfile(p):
        return None
    return 'New world from a map'


def _restore(pr, d=None):
    d = d or _before(pr.name)
    with open(os.path.join(d, 'project.json'), encoding='utf-8') as f:
        kept = json.load(f)
    old = kept['project']
    if old.get('source'):
        back = os.path.join(d, 'source.esp')
        if os.path.isfile(back):
            shutil.copy2(back, os.path.join(project.PROJECTS_DIR, old['source']))
    elif pr.source:
        shutil.rmtree(os.path.join(project.PROJECTS_DIR, os.path.dirname(pr.source)), ignore_errors=True)
    with open(pr.path + '.tmp', 'w', encoding='utf-8') as f:
        json.dump(old, f, indent=1)
    os.replace(pr.path + '.tmp', pr.path)
    side = read_sidecar(pr)
    if kept.get('edid') in side:
        del side[kept['edid']]
        write_sidecar(pr, side)
    shutil.rmtree(d, ignore_errors=True)
    return pr.name


def _put_back_after_failure(srv, name):
    """A world that failed part-way. Up to the last step nothing of the mod has changed but its plugin being saved, so what was kept goes; if it got as far as letting go of the mod and couldn't
    open it again, the kept copy is the truth."""
    new = _before(name) + ' new'
    if srv.PR is None and os.path.isfile(os.path.join(new, 'project.json')):
        _restore(project.Project.open(name), new)
        srv.open_project(name)
    shutil.rmtree(new, ignore_errors=True)


def undo_world(srv):
    """Back to the mod as it was before the world from a map: the plugin written again without it."""
    srv.not_while_playing()
    srv.release_source()
    name = _restore(srv.PR)
    state = srv.open_project(name)
    pr = srv.PR
    w = espwrite.Writer(srv.GD, pr)
    w.force_all = not pr.source
    with open(pr.plugin_path(), 'wb') as f:
        f.write(w.build())
    return {'label': 'New world from a map', 'state': state, 'world_gone': True}


# ---------- OpenStreetMap on a world made from a map ----------

OSM = {'file': None, 'data': None}
COVER = {'file': None, 'raster': None}


def _cover_raster(name):
    if COVER['file'] != name or COVER['raster'] is None:
        COVER.update(file=name, raster=elevation.read_file(file_path(name), lambda n, m: _said('Reading the file', n, m)))
    return COVER['raster']


def cover_open_job(name, srv):
    file_path(name)

    def work():
        _said('Reading the file')
        r = _cover_raster(name)
        counts = landcover.classes_in(r)
        scheme = landcover.detect(counts)
        with srv._lock:
            rows = landcover.default_table(srv.GD, counts, scheme)
            tex = [{'key': srv.GD.key(f), 'edid': srv.GD.edid(f)} for f, (_i, x) in srv.GD.forms.items() if x.tag == 'LTEX']
        tex.sort(key=lambda t: t['edid'].lower())
        return {'file': name, 'scheme': scheme, 'rows': rows, 'textures': tex, 'sets': landcover.SCATTER_SETS, 'placed': bool(r.geo)}
    return _start(work, kind='cover')


def _layers_path(pr):
    return os.path.join(_mod_folder(pr), 'layers.json')


def read_layers(pr):
    try:
        with open(_layers_path(pr), encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _side_of(srv, world):
    if not srv.PR:
        raise ValueError('Start a mod first.')
    gd = srv.GD
    w = gd.from_key(world)
    side = read_sidecar(srv.PR).get(gd.edid(w))
    if not side:
        raise ValueError('This world wasn\'t made from a height file, so FOLab doesn\'t know where it lies on Earth.')
    return w, side


def _osm_data(name):
    if OSM['file'] != name or OSM['data'] is None:
        OSM.update(file=name, data=osm.read(file_path(name), name, lambda n: _said('Reading the file: %s things so far' % format(n, ','))))
    return OSM['data']


def osm_read_job(body, srv):
    name = body['file']
    file_path(name)
    _w, side = _side_of(srv, body['world'])

    def work():
        _said('Reading the file')
        data = _osm_data(name)
        _said('Laying it on the world')
        out = osmplace.summary(osmplace.layout(data, side))
        out['skipped'] = data.skipped
        out['file'] = name
        return out
    return _start(work, kind='osm_read')


def osm_lay_job(body, srv):
    name = body['file']
    file_path(name)
    srv.not_while_playing()
    w, side = _side_of(srv, body['world'])
    want = body.get('want') or {}

    def work():
        _said('Reading the file')
        data = _osm_data(name)
        lay = osmplace.layout(data, side)
        with srv._lock:
            ops, report, layer = osmplace.ops_for(srv.GD, srv.PR, w, lay, want, side['compress'], int(body.get('seed', 1)), _said)
            _said('Putting it in the mod')
            if not ops and not layer['buildings'] and not layer['places']:
                raise ValueError('Nothing in the file falls on this world.')
            state = srv.edit('OpenStreetMap: %s' % name, ops)['state'] if ops else srv.state()
            all_layers = read_layers(srv.PR)
            all_layers[srv.GD.edid(w)] = layer
            with open(_layers_path(srv.PR) + '.tmp', 'w', encoding='utf-8') as f:
                json.dump(all_layers, f)
            os.replace(_layers_path(srv.PR) + '.tmp', _layers_path(srv.PR))
        return {'state': state, 'report': report}
    return _start(work, kind='osm_lay')


def _roofs_off(grid, side):
    data = _osm_data(side['bumps'])
    geo = osmplace.Georef(side, data)
    spots = []
    for b in data.buildings:
        ring = [geo.xy(p) for p in b['ring']]
        spots += ring
        spots.append((sum(p[0] for p in ring) / len(ring), sum(p[1] for p in ring) / len(ring)))
    return coast.level_bumps(grid, spots)


def map_cover(srv, world, name, said=None):
    """What the map says each land point of a world made from it is: the land worked out again from the height file (and its
    coastline), as it was when the world was made."""
    _w, side = _side_of(srv, world)
    r = raster_of(side['file'])
    if side.get('grown_from'):
        # (a grown world's opts are still the first box's: a Plan worked out from them covers only the old cells, and every
        # step asking what the new land is found nothing there, 18 Nov 2026: its plants never went in)
        import mapgrow
        plan = mapgrow.plan_of(r, side)
    else:
        plan = MS.Plan(r, side.get('opts') or {})
    grid = MS.heights(plan, said)
    if side.get('bumps'):
        _roofs_off(grid, side)
    data = _osm_data(name)
    geo = osmplace.Georef(side, data)
    if side.get('coast'):
        sea = coast.shape_sea(grid, [[geo.xy(p) for p in line] for line in _osm_data(side['coast']).coast], plan.floor)
        if sea and not sea.get('leak'):
            MS.limit_slopes(grid.pts, grid.across, grid.down)
    lay = osmplace.layout(data, side)
    return osmcover.MapCover(grid, data, geo.xy, osmcover.default_textures(srv.GD), said, laid=lay['roads']), lay


def hotels_job(body, srv):
    """FOLab's own landmark hotels (modelsets.skyline) stood along a world's shore: one Undo. body: count, seed, or
    sites [[piece, x, y]]."""
    import modelsets
    srv.not_while_playing()
    name = body['file']
    file_path(name)
    w, _side = _side_of(srv, body['world'])

    def work():
        cover, lay = map_cover(srv, body['world'], name, _said)
        with srv._lock:
            ops, report = modelsets.skyline(srv.GD, srv.PR, w, cover, lay['roads'], int(body.get('count', 4)), int(body.get('seed', 1)), _said,
                                            [tuple(s) for s in body['sites']] if body.get('sites') else None)
            if not report['hotels']:
                raise ValueError('No place was found for a hotel: this world has no shore with level ground behind it.')
            _said('Putting it in the mod')
            state = srv.edit('Landmark hotels', ops)['state']
            kept = _kept(srv.PR, 'hotels.json')
            kept[srv.GD.edid(w)] = report['hotels']
            _kept(srv.PR, 'hotels.json', kept)
        return {'state': state, 'report': report}
    return _start(work, kind='hotels')


def coast_job(body, srv):
    """The coast's own hotels and one-off things (coastplace) stood over a world made from a map: one Undo. body: world,
    file (the OSM file the world was made with), seed, only [step names]."""
    import coastplace
    srv.not_while_playing()
    name = body['file']
    path = file_path(name)
    w, side = _side_of(srv, body['world'])

    def work():
        cover, lay = map_cover(srv, body['world'], name, _said)
        _said('Reading what the map has on the coast')
        marks = coastplace.osm_marks(path)
        geo = osmplace.Georef(side, _osm_data(name))
        with srv._lock:
            ops, report, hotels, things = coastplace.plan(srv.GD, srv.PR, w, cover, lay['roads'], geo.xy, marks, int(body.get('seed', 1)), _said,
                                                          body.get('only'))
            if not any(report.get(k) for k in ('hotels', 'lighthouse', 'aquarium', 'mast', 'groin', 'wreck')):
                raise ValueError('Nothing of the coast found a place: this world has no shore with room on it.')
            _said('Putting it in the mod')
            state = srv.edit('The coast', ops)['state']
            edid = srv.GD.edid(w)
            for fname, value in (('hotels.json', hotels), ('coast.json', things)):
                kept = _kept(srv.PR, fname)
                kept[edid] = value
                _kept(srv.PR, fname, kept)
        return {'state': state, 'report': report}
    return _start(work, kind='coast')


def green_job(body, srv):
    """The Mojave's bare brown painted over on wild ground only (greenground.py: by the land point, with what the map
    says each is): one Undo. body: world, file (the map)."""
    import greenground
    srv.not_while_playing()
    name = body['file']
    file_path(name)
    w, _side = _side_of(srv, body['world'])

    def work():
        cover, _lay = map_cover(srv, body['world'], name, _said)
        with srv._lock:
            ops, report = greenground.regreen(srv.GD, srv.PR, w, cover, _said)
            if not ops:
                raise ValueError('Nothing to change: this world\'s wild ground is already painted so, or it has none.')
            _said('Putting it in the mod')
            state = srv.edit('Green ground', ops)['state']
        return {'state': state, 'report': report}
    return _start(work, kind='green')


def plants_job(body, srv):
    """FOLab's own plants (modelsets.py; body 'set': 'beach', the default, 'jungle', or 'mountain': low cover for slopes) added to a world already
    dressed, over and above what grows there: one Undo. Nothing inside a building or a landmark. body 'only': 'new' plants only the
    cells the last growing added (the old ones have the set already)."""
    import modelsets
    srv.not_while_playing()
    name = body['file']
    file_path(name)
    w, _side = _side_of(srv, body['world'])

    def work():
        cover, _lay = map_cover(srv, body['world'], name, _said)
        cat = townbuild.load(srv.GD, srv.kits_folder(), _said)
        with srv._lock:
            which = body.get('set', 'beach')
            if which not in modelsets.EXTRA:
                raise ValueError('No set of plants called %s: there are %s.' % (which, ', '.join(modelsets.EXTRA)))
            only = None
            if body.get('only') == 'new':
                only = new_cells_of(srv, body['world'])[2]
                if not only:
                    raise ValueError("This world hasn't been grown: it has no new land to plant.")
            ops, report = modelsets.extra(srv.GD, srv.PR, w, cover, int(body.get('seed', 1)), _said, which, float(body.get('thick', 1.0)), only)
            ops = landmarks.clear_of(ops, landmarks.standing(srv.GD, srv.PR, w) + modelsets.footprints(srv.PR, srv.GD, w))     # (nor in a hotel)
            inside = osmdress._Stands(osmdress.standing(srv.GD, srv.PR, w, cat), margin=24.0)
            ops = [o for o in ops if o.get('op') != 'add' or not inside.hit(o['p'][0], o['p'][1])]
            report['plants'] = sum(1 for o in ops if o['op'] == 'add')
            if not report['plants']:
                raise ValueError("Nothing to plant: the map says nothing about this world's ground.")
            _said('Putting it in the mod')
            state = srv.edit(which.capitalize() + ' plants', ops)['state']
        return {'state': state, 'report': report}
    return _start(work, kind='plants')


def dress_job(body, srv):
    """Things on the ground by what the map says it is, and along the streets (osmdress.py): one Undo."""
    srv.not_while_playing()
    name = body['file']
    file_path(name)
    w, _side = _side_of(srv, body['world'])

    def work():
        cover, lay = map_cover(srv, body['world'], name, _said)
        cat = townbuild.load(srv.GD, srv.kits_folder(), _said)
        with srv._lock:
            seed = int(body.get('seed', 1))
            # FOLab's own palms, banana plants, hibiscus and dune grass: 'beach' adds them to the game's plants,
            # 'beach instead' puts them where the game's palms, banana plants, bushes and grass would have gone
            # (and the Mojave's desert plants, which don't grow on Oʻahu, always: modelsets.DESERT)
            import modelsets
            first, swaps = modelsets.swaps(srv.PR, only=None if body.get('plants') == 'beach instead' else modelsets.DESERT)
            ops, report = osmdress.ops(srv.GD, srv.PR, w, cover, lay['roads'], seed, _said, swaps=swaps)
            if body.get('plants') == 'beach':
                import modelsets
                more, report['beach'] = modelsets.extra(srv.GD, srv.PR, w, cover, seed, _said)
                first = [o for o in more if o['op'] != 'add']
                ops += [o for o in more if o['op'] == 'add']
            # (round each building what it was for, and a few places someone stopped at)
            more, report['footings'] = osmdress.footings(srv.GD, srv.PR, w, cover, cat, seed, _said)
            ops += more
            more, report['life'] = osmdress.life(srv.GD, srv.PR, w, cover, cat, seed, _said)
            ops += more
            plots = read_layers(srv.PR).get(srv.GD.edid(w), {}).get('buildings') or []
            more, report['lots'] = osmdress.lots(srv.GD, srv.PR, w, cover, cat, plots, seed, _said)      # (what nothing was built on)
            ops += more
            more, report['scenes'] = osmdress.scenes(srv.GD, srv.PR, w, cover, lay['roads'], cat, seed, _said)
            ops += more
            marks = landmarks.standing(srv.GD, srv.PR, w)
            ops = landmarks.clear_of(ops, marks)       # (nothing inside a landmark)
            # (nor inside a building: one that outgrew its squeezed plot stands on ground the map calls street or yard)
            inside = osmdress._Stands(osmdress.standing(srv.GD, srv.PR, w, cat), margin=24.0)
            ops = [o for o in ops if o.get('op') != 'add' or not inside.hit(o['p'][0], o['p'][1])]
            if not ops:
                raise ValueError("Nothing to put down: the map says nothing about this world's ground.")
            _said('Putting it in the mod')
            state = srv.edit('Things on the ground', first + ops)['state']
            kept = _kept(srv.PR, 'scenes.json')
            kept[srv.GD.edid(w)] = report['scenes'].get('spots', [])
            _kept(srv.PR, 'scenes.json', kept)
            if body.get('soften', True):
                # (sharp steps where plots and road beds meet eased, everything on them moved with the ground; then, where a
                # road is still rough, the reason for it: all in the same Undo)
                soft, report['ground'] = landsoft.soften(srv.GD, srv.PR, w, osmdress.keep_of(osmdress.standing(srv.GD, srv.PR, w, cat)) + marks,
                                                              [(r['line'], osmdress.EDGE.get(r.get('class'), 300.0) * 0.8) for r in lay['roads']], _said)
                if soft:
                    srv.PR.apply('Things on the ground', soft, merge=True)
                # (and last of what moves ground: every road piece laid in it again, the land brought up to each)
                _said('Laying the roads in the ground')
                bedded, report['roads'] = roadbed.bed(srv.GD, srv.PR, w, osmdress.keep_of(osmdress.standing(srv.GD, srv.PR, w, cat)) + marks, _said)
                if bedded:
                    srv.PR.apply('Things on the ground', bedded, merge=True)
                more, report['rough'] = osmdress.rough_roads(srv.GD, srv.PR, w, cover, lay['roads'], cat, seed, _said)
                more = landmarks.clear_of(more, marks)
                if more:
                    srv.PR.apply('Things on the ground', more, merge=True)
                # (last: whatever lies on the ground let down onto it as the ground now is)
                more, report['seated'] = osmdress.seat_lying(srv.GD, srv.PR, w, _said)
                if more:
                    srv.PR.apply('Things on the ground', more, merge=True)
                state = srv.state()
        return {'state': state, 'report': report}
    return _start(work, kind='dress')


def _kept(pr, name, data=None):
    """Something the later steps of a map-made world need from the earlier ones, kept beside its layers: read, or written."""
    path = os.path.join(os.path.dirname(_layers_path(pr)), name)
    if data is None:
        try:
            with open(path, encoding='utf-8') as f:
                return json.load(f)
        except (OSError, ValueError):
            return {}
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path + '.tmp', 'w', encoding='utf-8') as f:
        json.dump(data, f)
    os.replace(path + '.tmp', path)
    return data


# what a landmark is on the map
MARK_KIND = {'lucky38': 'monument', 'kilauea': 'monument', 'royal_hawaiian': 'monument', 'moana': 'monument', 'natatorium': 'monument',
             'battery_randolph': 'military','tops': 'urban ruins', 'tops_strip': 'urban ruins', 'grandhotel': 'urban ruins', 'ultraluxe': 'urban ruins',
             'gomorrah': 'urban ruins', 'battery': 'military', 'pool': 'monument', 'lookout': 'military'}
SCENE_MARK = {'raiders': ('Raider Camp', 'camp'), 'refuge': ('Refugee Camp', 'camp')}


def life_job(body, srv):
    """What makes a map-made world somewhere to be (worldlife.py): its weather, water and sound, zones that get harder
    with distance from the start, map markers, who lives at the camps and in the wild, a settlement. One Undo.
    body: world, file (the OpenStreetMap file), start [x, y] (else the mod's own new game's), air {name, weathers
    [[WTHR, chance]], sounds_like, water, music}, settlement (its name), harbour (its name), seed."""
    srv.not_while_playing()
    name = body['file']
    file_path(name)
    w, _side = _side_of(srv, body['world'])

    def work():
        cover, _lay = map_cover(srv, body['world'], name, _said)
        cat = townbuild.load(srv.GD, srv.kits_folder(), _said)
        with srv._lock:
            gd, pr = srv.GD, srv.PR
            start = body.get('start') or ((pr.newgame or {}).get('p') or [None])[:2]
            if not start or start[0] is None:
                raise ValueError('Say where the player starts first (the mod\'s own new game): what\'s safe and what\'s hard go by it.')
            seed = int(body.get('seed', 1))
            P = osmdress._Putter(gd, pr, w, cover)
            L = worldlife.Life(gd, pr, w, start, seed)
            inside = osmdress._Stands(osmdress.standing(gd, pr, w, cat), margin=120.0)
            marks = landmarks.standing(gd, pr, w)
            within = lambda x, y: inside.hit(x, y) or len(landmarks.clear_of([{'op': 'add', 'p': [x, y]}], marks)) == 0
            keep = lambda x, y: within(x, y) or P.kind(x, y) in ('asphalt', 'seabed', None)
            L.blocked = within
            edid = srv.GD.edid(w)
            air = body.get('air') or {}
            if air.get('weathers'):
                _said('Its weather, water and sound')
                L.air(air.get('name') or edid + 'Air', air['weathers'], air.get('sounds_like'), air.get('water'), air.get('music'))
            L.zones(edid)
            # a settlement: the nearest level open ground to the start that isn't on top of it
            if body.get('settlement'):
                _said('A settlement')
                rng, best = L.rng, None
                for _try in range(4000):
                    a, d = rng.uniform(0, 6.2832), rng.uniform(3500.0, 11000.0)
                    x, y = start[0] + d * __import__('math').sin(a), start[1] + d * __import__('math').cos(a)
                    if P.kind(x, y) not in ('grass', 'golf', 'trees', 'scrub', 'yard') or P.steep(x, y, 700.0) > 0.06:
                        continue
                    if any(keep(x + dx, y + dy) or (P.ground.at(x + dx, y + dy) or -1) < 16 for dx in (-1000, -500, 0, 500, 1000) for dy in (-1000, -500, 0, 500, 1000)):
                        continue
                    if best is None or d < best[0]:
                        best = (d, x, y)
                if best:
                    L.settlement(body['settlement'], best[1], best[2])
            _said('Names on the map')
            for m in (_kept(pr, 'landmarks.json').get(edid) or {}).get('stood', []):
                L.marker(m['x'], m['y'], m.get('name') or m['label'], MARK_KIND.get(m.get('set'), 'urban ruins'))
            hb = (_kept(pr, 'landmarks.json').get(edid) or {}).get('harbour') or {}
            if body.get('harbour') and hb.get('at'):
                L.marker(hb['at'][0], hb['at'][1], body['harbour'], 'factory')
            spots = (_kept(pr, 'scenes.json').get(edid) or [])
            n = {}
            for x, y, kind in spots:
                if kind in SCENE_MARK and n.get(kind, 0) < 6:
                    n[kind] = n.get(kind, 0) + L.marker(x, y, SCENE_MARK[kind][0], SCENE_MARK[kind][1])
            _said('Who lives there')
            L.people(spots)
            L.wildlife(P.kind, keep)
            ops, report = L.done()
            _said('Putting it in the mod')
            state = srv.edit('Life for the world', ops)['state']
        return {'state': state, 'report': report}
    return _start(work, kind='life')


def landmarks_job(body, srv):
    """The game's great buildings stood where the map has its own, and its piers built as a harbour (landmarks.py): one Undo.
    body: file (the OpenStreetMap file), sites [{set, lat, lon, turn, scale, level}], harbour."""
    srv.not_while_playing()
    name = body['file']
    file_path(name)
    w, side = _side_of(srv, body['world'])

    def work():
        data = _osm_data(name)
        geo = osmplace.Georef(side, data)
        lay = osmplace.layout(data, side)
        with srv._lock:
            landmarks.know(townbuild.load(srv.GD, srv.kits_folder(), _said))
            B = landmarks.Batch(srv.GD, srv.PR, w, lay['roads'], int(body.get('seed', 1)))
            report = {'stood': [], 'missed': []}
            for k, s in enumerate(body.get('sites') or []):
                _said('Standing the landmarks', k, len(body['sites']))
                if s.get('set') not in landmarks.SETS:
                    report['missed'].append(s.get('set'))
                    continue
                x, y = geo.xy((float(s['lat']), float(s['lon'])))
                got = B.stand(s['set'], x, y, s.get('turn'), float(s.get('scale') or 1.0), level=s.get('level', True))
                if got:
                    report['stood'].append(dict(got, name=s.get('name')))
                else:
                    report['missed'].append(s.get('name') or s['set'])
            if body.get('harbour'):
                _said('Building the harbour')
                piers = []
                for line in data.piers:
                    pts = [geo.xy(p) for p in line]
                    if len(pts) > 3 and line[0] == line[-1]:     # (drawn as an outline: its length is between its two furthest corners)
                        a, b = max(((p, q) for p in pts for q in pts), key=lambda pq: (pq[0][0] - pq[1][0]) ** 2 + (pq[0][1] - pq[1][1]) ** 2)
                        pts = [a, b]
                    piers.append(pts)
                report['harbour'] = B.harbour(piers)
            ops = B.done()
            if not ops:
                raise ValueError('Nothing was stood: none of it fitted, and the map has no piers over the water.')
            _said('Putting it in the mod')
            state = srv.edit('Landmarks and harbour', ops)['state']
            kept = _kept(srv.PR, 'landmarks.json')
            kept[srv.GD.edid(w)] = report
            _kept(srv.PR, 'landmarks.json', kept)
        return {'state': state, 'report': report}
    return _start(work, kind='landmarks')


def buildings_job(body, srv):
    """The game's buildings stood on the plots an OpenStreetMap file levelled (townbuild.py): one Undo."""
    srv.not_while_playing()
    w, _side = _side_of(srv, body['world'])

    def work():
        _said('Measuring the game\'s buildings (the first time only, about a minute)')
        cat = townbuild.load(srv.GD, srv.kits_folder(), _said)
        with srv._lock:
            rows = read_layers(srv.PR).get(srv.GD.edid(w), {}).get('buildings') or []
            if not any(r.get('pad') for r in rows):
                raise ValueError('There are no building plots on this world yet: lay an OpenStreetMap file with Buildings ticked first.')
            share = float(body.get('insides', townbuild.INSIDE_SHARE))
            squeeze = float(_side.get('compress') or 1.0)
            ops, report = townbuild.plan(srv.GD, srv.PR, w, rows, cat, int(body.get('seed', 1)), _said, insides=share,
                                         stretch=float(body['stretch']) if body.get('stretch') else (min(4.0, squeeze) if squeeze >= 1.5 else 1.0))
            if not report['buildings']:
                if report['had_one']:
                    raise ValueError('Every plot with room for one already has its buildings%s.' % (
                        ' (%s too small for any of the game\'s)' % report['nothing_fits'] if report['nothing_fits'] else ''))
                raise ValueError('No building fitted on any plot (%s too small to fit, %s in a road\'s way, %s on ground too steep).'
                                 % (report['nothing_fits'], report['blocked'], report['steep']))
            _said('Putting it in the mod')
            state = srv.edit('Buildings on the plots', ops)['state']
            # (each place behind a door walks: its navmesh, in the same Undo)
            names, made = dict(srv.PR.names), report.pop('made')
            # (the game's own, made by hand, where it can be taken as it is: the copy's things stand where the game's do; else one is made)
            nav_ops, report['navmesh_missed'], report['navmesh_game'] = [], 0, 0
            for k, (tag, _fam, src, doors) in enumerate(made):
                _said('Making the places\' navmeshes', k, len(made))
                key = names.get(tag)
                data = townbuild.copied_navmesh(srv.GD, srv.PR, src, key, {g: names[n] for g, n in doors.items() if n in names})
                if data:
                    report['navmesh_game'] += 1
                else:
                    try:
                        data, _r = navbuild.generate(srv.GD, srv.PR, key)
                    except navbuild.NavError:
                        report['navmesh_missed'] += 1
                        continue
                nav_ops.append({'op': 'navmesh', 'cell': key, 'mesh': data})
            if nav_ops:
                srv.PR.apply('Buildings on the plots', nav_ops, merge=True)
                state = srv.state()
            if made:
                # (the game has too few places of some kinds to lend: each copy after the first gets things and a light of its own)
                _said('Making repeated places their own')
                import roomvary
                report['varied'] = roomvary.vary(srv.GD, srv.PR, merge=True, label='Buildings on the plots')
                state = srv.state()
            report['places'] = [names[m[0]] for m in made if m[0] in names]
        return {'state': state, 'report': report}
    return _start(work, kind='buildings')


# ---------- routes ----------

def get(path, q, srv):
    """(what to send: data, and for pictures its content type)."""
    q = {k: (v[0] if isinstance(v, list) else v) for k, v in q.items()}
    if path == '/api/maps/job':
        return ({k: v for k, v in JOB.items()},)
    if path == '/api/maps/files':
        return ({'files': files(), 'job': {k: v for k, v in JOB.items() if k not in ('result',)}},)
    if path == '/api/maps/picture':
        return (picture(q['file'], q)[0], 'image/png')
    if path == '/api/maps/worlds':
        with srv._lock:
            return (read_sidecar(srv.PR) if srv.PR else {},)
    if path == '/api/maps/layers':
        with srv._lock:
            return (read_layers(srv.PR).get(q.get('edid'), {}) if srv.PR else {},)
    raise ValueError('No such thing to ask: ' + path)


def post(path, body, srv):
    if path == '/api/maps/open':
        return {'job': open_job(body['file'])}
    if path == '/api/maps/plan':
        name = body['file']
        if OPEN['file'] != name or OPEN['raster'] is None:
            raise ValueError('Open the file first.')
        r = OPEN['raster']
        plan = MS.Plan(r, body.get('opts') or {})
        out = plan.report()
        if OPEN['thumb'] is None:
            OPEN['thumb'] = mapworld.thumbnail(r)
        out['edges'] = mapworld.picture_edges(OPEN['thumb'])
        return out
    if path == '/api/maps/make':
        return {'job': make_job(body, srv)}
    if path == '/api/maps/cover/open':
        return {'job': cover_open_job(body['file'], srv)}
    if path == '/api/maps/osm/read':
        return {'job': osm_read_job(body, srv)}
    if path == '/api/maps/osm/lay':
        return {'job': osm_lay_job(body, srv)}
    if path == '/api/maps/buildings':
        return {'job': buildings_job(body, srv)}
    if path == '/api/maps/life':
        return {'job': life_job(body, srv)}
    if path == '/api/maps/landmarks':
        return {'job': landmarks_job(body, srv)}
    if path == '/api/maps/dress':
        return {'job': dress_job(body, srv)}
    if path == '/api/maps/hotels':
        return {'job': hotels_job(body, srv)}
    if path == '/api/maps/coast':
        return {'job': coast_job(body, srv)}
    if path == '/api/maps/green':
        return {'job': green_job(body, srv)}
    if path == '/api/maps/plants':
        return {'job': plants_job(body, srv)}
    if path == '/api/maps/grow/preview':
        return grow_preview(body, srv)
    if path == '/api/maps/grow':
        return {'job': grow_job(body, srv)}
    if path == '/api/maps/grow/dress':
        return {'job': grow_dress_job(body, srv)}
    if path == '/api/maps/restore':
        with srv._lock:
            if not srv.PR or not os.path.isfile(os.path.join(_before(srv.PR.name), 'project.json')):
                raise ValueError('There\'s nothing to go back to.')
            return undo_world(srv)
    raise ValueError('No such thing to do: ' + path)
