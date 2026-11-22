"""Big jobs: the one-click steps a whole world needs, as buttons (the Tools tab Big jobs, web/bigjobs.js, /api/jobs/...).

Waikiki was finished by scripts: about a hundred of them each loaded the mod, refused while the game ran, copied the mod
to "<mod> before <step>", ran one builder, applied its ops as one Undo and saved (docs/folab-from-waikiki.md). This is
that, once, for anyone: pick a job and a world, and it

  - refuses while the game runs, or while another long job (a map step, a navmesh run) is changing the mod;
  - copies the mod's file into backups as "<mod> before <job> MMDD-HHMM" just before its first change goes in (none when
    nothing needs changing; backups.py tidies those only on a click);
  - runs in the background with what it's on and how far it has got;
  - lands as ONE Undo, however many steps it has (later steps `merge`), and the card offers Undo while it is the last one;
  - says what changed and what to do next: the jobs to run after it (`then`: anything that moves ground or buildings is
    followed by putting things back on the ground), and the cells whose navmesh is now out of date.

Each job is a list of steps; a step is fn(ctx) -> (ops, report) and is applied before the next one runs, so a later step
sees what an earlier one did (close_gaps after fit). Steps are the builders' own entry points, unchanged.
"""
import os
import re
import shutil
import threading
import time
import traceback

import backups

JOB = {'running': False}
_job_lock = threading.Lock()


class Ctx:
    """What a step gets: the game, the mod, the world, progress, and the buildings catalogue when asked for."""
    def __init__(self, srv, world):
        self.srv, self.gd, self.pr, self.world = srv, srv.GD, srv.PR, world
        self._cat = None

    def said(self, *a):
        """Progress from any builder: (what, done, total), (done, total) or (what,)."""
        what = next((x for x in a if isinstance(x, str)), JOB.get('said', ''))
        nums = [x for x in a if isinstance(x, (int, float)) and not isinstance(x, bool)]
        JOB.update(said=what, done=nums[0] if nums else 0, total=nums[1] if len(nums) > 1 else 0)

    @property
    def cat(self):
        if self._cat is None:
            import townbuild
            self.said("Reading the game's buildings")
            self._cat = townbuild.load(self.gd, self.srv.kits_folder(), self.said)
        return self._cat

    def cells_xy(self):
        return list(self.gd.grid(self.world).keys())


# ---------- the steps (each the builder's own entry point) ----------

def _float(c):
    import settleup
    return settleup.settle(c.gd, c.pr, c.world, c.cat, progress=c.said, everything=True)


def _fit(c):
    import groundfit
    return groundfit.fit(c.gd, c.pr, c.world, cat=c.cat, progress=c.said)


def _gaps(c):
    import groundfit
    c.said('Closing gaps under walls')
    return groundfit.close_gaps(c.gd, c.pr, c.world, cat=c.cat)


def _lying(c):
    import osmdress
    return osmdress.seat_lying(c.gd, c.pr, c.world, c.said)


def _on_roads(c):
    import roadbed
    c.said('Lifting things out of the road pieces')
    return roadbed.onto_roads(c.gd, c.pr, c.world)


def _pieces(c):
    import groundfit
    c.said('Letting standing things down off slopes')
    return groundfit.settle_pieces(c.gd, c.pr, c.world)


def _plants(c):
    import plantsplit
    import modelsets
    import recordio
    # (a mod with none of FOLab's plants has nothing to rework: without this the job still put 28 plant records in it)
    mine = {recordio.field(r, 'EDID') for k, r in c.pr.records.items() if k.startswith('+') and r.get('type') == 'STAT'}
    pieces = set(plantsplit.CLUMPS) | set(plantsplit.SHAPE) | set(plantsplit.LOW_GREEN)
    if not any(modelsets.PIECES[p]['edid'] in mine for p in pieces if p in modelsets.PIECES):
        return [], {"FOLab's plants in the mod": 0}
    c.said("Reading every cell's plants (a minute or more on a big world)")
    return plantsplit.rework(c.gd, c.pr, c.world, c.cells_xy(), progress=c.said)


def _pipboy(c):
    import worldmap
    return worldmap.ops(c.gd, c.pr, c.world, progress=c.said)


def _towers(c):
    import guardtower
    c.said("Finding the game's guard towers")
    return guardtower.swap_ops(c.gd, c.pr)


def _tower_pads(c):
    import guardtower
    c.said('Levelling ground under towers on slopes')
    return guardtower.pad(c.gd, c.pr, c.world)


def _restyle(c):
    import restyle
    c.said('Finding the Mojave buildings')
    return restyle.ops(c.gd, c.pr)


SEAT = 'seat'

# key: (title, what it does in plain words, steps, jobs to run after it, needs a world)
JOBS = {
    'float': ('Things floating or sunk',
              "Everything the mod placed that hangs in the air or is sunk into a roof is set down on what is really under it "
              "(the land, roofs, walls, the game's own collision). Roof camps whose roof is gone are taken out.",
              [_float], [], True),
    'street': ('Buildings set to their streets',
               "Each building of the mod's let down to the street the roads make, its yard eased back to the land, close "
               "neighbours at one level; then daylight under walls closed. Run after the roads are laid.",
               [_fit, _gaps], [SEAT, 'float'], True),
    SEAT: ('Things back on the ground',
           "Everything that lies on the ground (rubble, rocks, litter) tilted to the ground as it is now; things standing in "
           "a road piece lifted onto it; tents, crates and wrecks on slopes let down. Run after anything that moves ground.",
           [_lying, _on_roads, _pieces], ['float'], True),
    'plants': ("Plants: on the ground, within the draw budget",
               "FOLab's plant clumps taken apart into single plants, each cell kept to a number of draws the game can show "
               "(the start of Waikiki drew 12,693 and ran at 12 fps), and every plant seated by its own foot: nothing "
               "hanging, nothing buried. Can take a long time on a big world.",
               [_plants], [], True),
    'pipboy': ("Pip-Boy map",
               "Draws the world's map for the Pip-Boy (heights, sea, roads, buildings) and points the world at it, so the "
               "map isn't blank and places can be fast travelled to. Run again after the ground or buildings change.",
               [_pipboy], [], True),
    'towers': ("FOLab's guard towers",
               "Every one of the game's guard towers the mod placed becomes FOLab's own (whole, no floating panels), in the "
               "same spot; its loose parts go. Towers on slopes get a level pad.",
               [_towers, _tower_pads], [SEAT], True),
    'restyle': ("Mojave buildings restyled",
                "The game's Wild West buildings the mod placed (saloons, general stores, old west shops, the schoolhouse, "
                "Nipton's hall) swapped for FOLab's island-style pieces, doors and links kept; billboards naming Mojave "
                "places swapped for others.",
                [_restyle], [], False),
}


def busy_elsewhere(srv):
    """Another long job changing the mod: a Real map step or a navmesh run."""
    try:
        import api_maps
        if api_maps.JOB.get('running'):
            return 'a Real map step'
    except ImportError:
        pass
    try:
        import worldapi
        if worldapi.JOB.get('running'):
            return 'a navmesh run'
    except (ImportError, AttributeError):
        pass
    return None


def _backup(pr, title):
    """The mod's file as it is, into backups/"<mod> before <job> MMDD-HHMM"/ (backups.classify's 'mod' kind)."""
    name = os.path.splitext(os.path.basename(pr.path))[0]
    title = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', '', title).strip()     # (Windows allows none of these in a folder's name)
    dest = os.path.join(backups.folder(), '%s before %s %s' % (name, title.lower(), time.strftime('%m%d-%H%M')))
    n = 2
    while os.path.exists(dest):
        dest = os.path.join(backups.folder(), '%s before %s (%d) %s' % (name, title.lower(), n, time.strftime('%m%d-%H%M')))
        n += 1
    os.makedirs(dest)
    pr.compact()                            # (the mod as one file: its .changes folded into its .json)
    shutil.copy2(pr.path, os.path.join(dest, os.path.basename(pr.path)))
    return os.path.basename(dest)


def _counts(ops):
    """What the ops do, in words a person reads: how many added, moved, taken out..."""
    n = {}
    for o in ops:
        k = o.get('op')
        if k == 'remove' or (k == 'move' and o.get('p') and o['p'][2] < -20000):
            n['taken out'] = n.get('taken out', 0) + 1
        elif k == 'add':
            n['added'] = n.get('added', 0) + 1
        elif k == 'move':
            n['moved'] = n.get('moved', 0) + 1
        elif k == 'swap':
            n['swapped'] = n.get('swapped', 0) + 1
        elif k == 'land':
            n['ground squares changed'] = n.get('ground squares changed', 0) + 1
        elif k in ('record', 'record_new'):
            n['records'] = n.get('records', 0) + 1
        elif k:
            n['other changes'] = n.get('other changes', 0) + 1
    return n


def _short(rep):
    """A builder's report cut to what reads in a card: numbers, short words, and lengths of lists."""
    out = {}
    for k, v in (rep or {}).items():
        if isinstance(v, bool) or v is None:
            continue
        if isinstance(v, (int, float)):
            out[k] = round(v, 1) if isinstance(v, float) else v
        elif isinstance(v, str) and len(v) < 120:
            out[k] = v
        elif isinstance(v, (list, tuple, set)) and k != 'cells':
            out[k] = len(v)
        elif isinstance(v, dict) and all(isinstance(x, (int, float)) for x in v.values()) and len(v) <= 12:
            out[k] = dict(v)
    return out


def _nav_cells(srv, world, reps):
    """Cells the reports name as needing their navmesh again, as (x, y) of `world`."""
    keys = set()
    for r in reps:
        for c in (r or {}).get('cells') or []:
            keys.add(c if isinstance(c, str) else None)
    keys.discard(None)
    if not keys or world is None:
        return []
    return sorted(xy for xy, c in srv.GD.grid(world).items() if srv.GD.key(c) in keys)


def worlds(srv):
    """The worlds a job can be run on: those the mod has changed first."""
    mine = set(srv.PR.cells) if srv.PR else set()
    out = []
    for w in srv.worlds():
        form = srv.GD.from_key(w['id'])
        has = any(srv.GD.key(c) in mine for c in srv.GD.grid(form).values()) if mine else False
        out.append(dict(w, mine=has))
    out.sort(key=lambda w: (not w['mine'],))
    return out


def page(srv):
    return {'jobs': [{'key': k, 'title': t, 'about': a, 'then': then, 'world': needs} for k, (t, a, _s, then, needs) in JOBS.items()],
            'worlds': worlds(srv) if srv.PR else [], 'job': status(), 'mod': srv.PR.plugin if srv.PR else None}


def status():
    return {k: v for k, v in JOB.items() if k != 'state'}


def _one_server(srv):
    """Builders written for scripts `import server` for its GD and kits_folder. In FOLab the server runs as __main__, so
    that import made a second, empty copy (GD None: "'NoneType' object has no attribute 'plugins'"): point the name at
    the running one."""
    import sys
    have = sys.modules.get('server')
    if have is not srv and getattr(srv, 'GD', None) is not None and getattr(have, 'GD', None) is None:
        sys.modules['server'] = srv


def start(srv, key, world_id=None):
    """Run a job in the background (see the module's docstring). Returns its status."""
    if key not in JOBS:
        raise ValueError('There is no job called %s.' % key)
    if not srv.PR:
        raise ValueError('Open or start a mod first.')
    srv.not_while_playing()
    _one_server(srv)
    other = busy_elsewhere(srv)
    if other:
        raise ValueError('FOLab is busy with %s that changes the mod: wait for it to finish first.' % other)
    title, _about, steps, then, needs = JOBS[key]
    world = None
    if needs:
        if not world_id:
            raise ValueError('Pick the world to run it on.')
        world = srv.GD.from_key(world_id)
        if world is None or not srv.GD.grid(world):
            raise ValueError("That world has no ground to work on.")
    with _job_lock:
        if JOB.get('running'):
            raise ValueError('A big job is already running: wait for it first.')
        JOB.clear()
        JOB.update(running=True, key=key, title=title, world=world_id, said='Starting', done=0, total=0, started=time.time())

    def work():
        ctx = Ctx(srv, world)
        reps, counts, step = [], {}, 0
        try:
            with srv._lock:
                if srv.PR is not ctx.pr:
                    raise ValueError('The mod was closed.')
                label = title
                for fn in steps:
                    ops, rep = fn(ctx)
                    reps.append(rep)
                    if ops:
                        if step == 0:           # (the copy only when something will change: a big mod's is 250 MB)
                            ctx.said('Copying the mod into backups first')
                            JOB['backup'] = _backup(ctx.pr, title)
                        ctx.said('Putting it in the mod')
                        if step == 0:
                            srv.edit(label, ops)
                        else:
                            ctx.pr.apply(label, ops, merge=True)
                        step += 1
                        for k, v in _counts(ops).items():
                            counts[k] = counts.get(k, 0) + v
                JOB.update(state=srv.state())
            JOB.update(ok=True, changed=bool(step), counts=counts, report=[_short(r) for r in reps],
                       navmesh=_nav_cells(srv, world, reps), then=[t for t in then if t in JOBS],
                       undo=label if step else None)
        except Exception as e:   # (whatever goes wrong, the page has to hear about it; what was applied stays one Undo)
            traceback.print_exc()
            JOB.update(ok=False, error=str(e), changed=bool(step), counts=counts, undo=title if step else None)
        JOB.update(running=False, took=round(time.time() - JOB['started']))
    threading.Thread(target=work, daemon=True).start()
    return status()


def undo(srv):
    """Undo the job just run, only while it is still the last thing done."""
    if JOB.get('running') or not JOB.get('undo'):
        raise ValueError('There is no big job to undo.')
    st = srv.PR.undo_stack if srv.PR else []
    if not st or st[-1][0] != JOB['undo']:
        raise ValueError('Something else was changed since: use Undo at the top (it goes one step at a time).')
    with srv._lock:
        srv.PR.undo()
        JOB['undo'] = None
        JOB['undone'] = True
        return {'state': srv.state(), 'job': status()}


def get(path, q, srv):
    if path == '/api/jobs':
        return page(srv)
    if path == '/api/jobs/status':
        return {'job': status()}
    raise ValueError('No such thing to ask: ' + path)


def post(path, body, srv):
    if path == '/api/jobs/start':
        return {'job': start(srv, body.get('job'), body.get('world'))}
    if path == '/api/jobs/undo':
        return undo(srv)
    if path == '/api/jobs/state':
        return {'state': srv.state()}
    raise ValueError('No such thing to do: ' + path)
