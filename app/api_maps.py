"""What the Land from real maps panel asks of the server (web/mapland.js): files the person brings, the preview and its numbers, the new world as a job of its own,
and the way back. server.py hands every /api/maps/ request here (with itself as srv), outside its lock: reading a file or making a world takes minutes,
and the page has to be able to ask how it's going.

The person's files are copied to maps/ under FOLab's home when they pick them. FOLab fetches nothing. What a world was made from is kept in projects/<mod> maps.json, so
OpenStreetMap can be laid on it later, and the mod as it was in projects/<mod> before map/, so that it can be put back."""
import json
import os
import re
import shutil
import threading

import elevation
import espwrite
import mapscale as MS
import mapworld
import osm
import osmplace
import project

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

def _sidecar(pr):
    return os.path.join(project.PROJECTS_DIR, pr.name + ' maps.json')


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
        tpl = srv.GD.from_key(body['template']) if body.get('template') else next(w for w in srv.GD.worlds() if srv.GD.edid(w) == 'WastelandNV')
        _said('Learning how the game paints its land')
        with srv._lock:
            shaped = mapworld.options(plan, grid, srv.GD, tpl, body.get('ltex'), int(body.get('seed', 1)), lambda n, m: _said('Painting and packing the land', n, m))
            _said('Painting and packing the land', 0, plan.count())
            edid = re.sub(r'[^A-Za-z0-9_]', '', body.get('edid') or '')
            try:
                out = srv.new_world({'name': body.get('name') or '', 'edid': edid, 'template': body.get('template'), 'height': shaped['height'],
                                     'ltex': body.get('ltex')}, shaped)
            except Exception:
                _put_back_after_failure(srv)
                raise
            d = read_sidecar(srv.PR)
            d[edid] = {'file': name, 'opts': opts, 'W': plan.W, 'H': plan.H, 'x0': plan.x0, 'y0': plan.y0, 'col0': plan.col0, 'row0': plan.row0, 'upx': plan.upx, 'upy': plan.upy,
                       'base': plan.base, 'k': plan.k, 'compress': plan.compress, 'exag': plan.exag, 'geo': r.geo, 'px_w': r.w, 'px_h': r.h}
            write_sidecar(srv.PR, d)
        stats = dict(grid.stats, cells=plan.count(), world=out['world'], z_low=min(grid.pts), z_high=max(grid.pts))
        stats['size'] = os.path.getsize(srv.PR.plugin_path())
        return {'state': out, 'world': out['world'], 'report': stats}
    return _start(work, kind='make')


# ---------- going back to before the world ----------

def _before(name):
    return os.path.join(project.PROJECTS_DIR, name + ' before map')


def keep_before(pr, edid):
    """The mod as it is, kept before a world is made from a map, to go back to."""
    d = _before(pr.name)
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d)
    src = pr.source_path()
    if src and os.path.isfile(src):
        shutil.copy2(src, os.path.join(d, 'source.esp'))
    with open(os.path.join(d, 'project.json'), 'w', encoding='utf-8') as f:
        json.dump({'edid': edid, 'project': pr.to_dict()}, f)


def undo_label(pr):
    """What Undo says when there's nothing else to undo: the world, if nothing has been changed since it was made."""
    if pr.undo_stack or pr.count():
        return None
    p = os.path.join(_before(pr.name), 'project.json')
    if not os.path.isfile(p):
        return None
    return 'New world from a map'


def _restore(pr):
    d = _before(pr.name)
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


def _put_back_after_failure(srv):
    """A world that failed part-way: the plugin wasn't changed unless it got as far as opening it, so make sure of the mod."""
    if srv.PR is not None:
        return
    # (new_world had let go of the mod and couldn't open it again: the kept copy is the truth)
    names = [n[:-len(' before map')] for n in os.listdir(project.PROJECTS_DIR) if n.endswith(' before map')]
    for n in names:
        pr = project.Project.open(n)
        if pr.source and os.path.isfile(os.path.join(_before(n), 'project.json')):
            _restore(pr)
            srv.open_project(n)
            return


def undo_world(srv):
    """Back to the mod as it was before the world from a map: the plugin written again without it."""
    srv.not_while_playing()
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


def _layers_path(pr):
    return os.path.join(project.PROJECTS_DIR, pr.name + ' map layers.json')


def read_layers(pr):
    try:
        with open(_layers_path(pr), encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _side_of(srv, world):
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
            state = srv.edit('OpenStreetMap: %s' % name, ops) if ops else srv.state()
            all_layers = read_layers(srv.PR)
            all_layers[srv.GD.edid(w)] = layer
            with open(_layers_path(srv.PR) + '.tmp', 'w', encoding='utf-8') as f:
                json.dump(all_layers, f)
            os.replace(_layers_path(srv.PR) + '.tmp', _layers_path(srv.PR))
        return {'state': state, 'report': report}
    return _start(work, kind='osm_lay')


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
    if path == '/api/maps/osm/read':
        return {'job': osm_read_job(body, srv)}
    if path == '/api/maps/osm/lay':
        return {'job': osm_lay_job(body, srv)}
    if path == '/api/maps/restore':
        with srv._lock:
            if not srv.PR or not os.path.isfile(os.path.join(_before(srv.PR.name), 'project.json')):
                raise ValueError('There\'s nothing to go back to.')
            return undo_world(srv)
    raise ValueError('No such thing to do: ' + path)
