"""What the World tools ask of the server (web/worldtools.js, web/navtool.js): navmeshes outside and by hand, regions, map
markers, encounter zones, cell details, roads and distant land. server.py hands every /api/w/ request here.

Making navmeshes for many cells takes minutes, so it runs in a thread of its own and the page asks how it's going: it only
reads while it works (the game's files are memory maps, the mod's changes plain dicts), and its result goes in as one Undo."""
import threading

import navbuild
import navedit

JOB = {'running': False}
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


def get(path, q, gd, pr, ctx):
    """A GET: the answer, or None if it isn't one of these."""
    if path == '/api/w/nav/status':
        return nav_status(gd, pr, q['world'])
    if path == '/api/w/nav/job':
        return dict(JOB)
    if path == '/api/w/nav/meshes':
        return {'cells': [navedit.view(gd, pr, k) for k in q['cells'].split('|') if k]}
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
    return None
