"""Big jobs (bigjobs.py): the runner every whole-world step goes through. A real mod in the scratch home, a stand-in
server and world, and stand-in steps: the mod copied into backups first, every step one Undo between them (a later step
sees what an earlier one did), progress in either shape a builder gives it, counts and navmesh cells reported, the next
jobs offered, Undo only while the job is the last change, nothing while the game runs or another long job changes the
mod, a failure keeping what was done as one Undo. Then every real job's steps are importable builders."""
import os
import sys
import threading
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import backups  # noqa: E402
import bigjobs  # noqa: E402
import project  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


class GD:
    def __init__(self):
        self._grid = {(x, y): 500 + x * 10 + y for x in range(2) for y in range(2)}

    def grid(self, world):
        return self._grid if world == 7 else {}

    def key(self, c):
        return 'W.esp:%06X' % c

    def from_key(self, k):
        return int(k.split(':')[1], 16)


class Srv:
    _lock = threading.RLock()
    playing = False

    def __init__(self, pr):
        self.GD, self.PR = GD(), pr

    def not_while_playing(self):
        if self.playing:
            raise ValueError('The game is running')

    def edit(self, label, ops):
        self.PR.apply(label, ops)
        return {'state': self.state()}

    def state(self):
        return {'undo': self.PR.undo_stack[-1][0] if self.PR.undo_stack else None}

    def worlds(self):
        return [{'id': 'W.esp:000007', 'edid': 'Test', 'name': 'Test', 'cells': 4, 'plugin': 'W.esp'}]

    def kits_folder(self):
        return ''


def wait():
    for _ in range(200):
        if not bigjobs.JOB.get('running'):
            return
        time.sleep(0.05)


pr = project.Project.create('Jobs')
pr.apply('First', [{'op': 'add', 'cell': 'W.esp:0001F4', 'base': 'X', 'p': [0, 0, 0, 0, 0, 0]}])
srv = Srv(pr)
cell = 'W.esp:0001F4'
seen = {}


def step_one(c):
    c.said('Doing one', 1, 2)
    return [{'op': 'add', 'cell': cell, 'base': 'Y', 'p': [10, 0, 0, 0, 0, 0]},
            {'op': 'add', 'cell': cell, 'base': 'Y', 'p': [20, 0, 0, 0, 0, 0]}], {'things': 2, 'cells': [cell], 'note': 'ok'}


def step_two(c):
    c.said(3, 4)                                      # (groundfit's shape: numbers only)
    seen['refs'] = len(c.pr.cells[cell]['refs'])      # (what step one did is in the mod already)
    rk = next(iter(c.pr.cells[cell]['refs']))
    return [{'op': 'remove', 'cell': cell, 'ref': rk}], {'gone': 1}


bigjobs.JOBS['t'] = ('Test job', 'about', [step_one, step_two], ['seat', 'nonesuch'], True)
before_undo = len(pr.undo_stack)
st = bigjobs.start(srv, 't', 'W.esp:000007')
check('starts running', st['running'] and st['title'] == 'Test job')
wait()
j = bigjobs.status()
check('finished ok', j.get('ok') is True, j.get('error'))
check('a later step saw the earlier one applied', seen.get('refs') == 3, seen)
check('two steps, one Undo', len(pr.undo_stack) == before_undo + 1 and pr.undo_stack[-1][0] == 'Test job', [u[0] for u in pr.undo_stack])
check('counts in words', j['counts'] == {'added': 2, 'taken out': 1}, j['counts'])
check('report cut short, cells left out', j['report'][0] == {'things': 2, 'note': 'ok'}, j['report'])
check('navmesh cells named by x, y', j['navmesh'] == [(0, 0)], j['navmesh'])
check('next jobs: only real ones', j['then'] == ['seat'], j['then'])
bk = os.path.join(backups.folder(), j['backup'])
check('the mod copied into backups first, a "before" copy', os.path.isfile(os.path.join(bk, 'Jobs.json')) and
      backups.classify(j['backup'])[2] == 'mod', j['backup'])
check('the copy is the mod before the job', len(project.Project(os.path.join(bk, 'Jobs.json')).cells[cell]['refs']) == 1)

out = bigjobs.undo(srv)
check('Undo takes the whole job back', len(pr.cells[cell]['refs']) == 1 and pr.undo_stack[-1][0] == 'First')
try:
    bigjobs.undo(srv)
    check('undo twice refused', False)
except ValueError:
    check('undo twice refused', True)

# undo only while it is the last change
bigjobs.start(srv, 't', 'W.esp:000007')
wait()
pr.apply('Something else', [{'op': 'add', 'cell': cell, 'base': 'Z', 'p': [0, 0, 0, 0, 0, 0]}])
try:
    bigjobs.undo(srv)
    check('no Undo of the job once something else was done', False)
except ValueError:
    check('no Undo of the job once something else was done', True)

# refusals
srv.playing = True
try:
    bigjobs.start(srv, 't', 'W.esp:000007')
    check('refused while the game runs', False)
except ValueError:
    check('refused while the game runs', True)
srv.playing = False
import api_maps  # noqa: E402
api_maps.JOB['running'] = True
try:
    bigjobs.start(srv, 't', 'W.esp:000007')
    check('refused while a map step runs', False)
except ValueError as e:
    check('refused while a map step runs', 'Real map' in str(e))
api_maps.JOB['running'] = False
for bad, args in (('no world', ('t', None)), ('a world with no ground', ('t', 'W.esp:000009')), ('no such job', ('zz', None))):
    try:
        bigjobs.start(srv, *args)
        check('refused: ' + bad, False)
    except ValueError:
        check('refused: ' + bad, True)

# a failure part way: what was done stays, as one Undo
n = len(pr.undo_stack)


def boom(c):
    raise RuntimeError('broke')


bigjobs.JOBS['f'] = ('Failing job', 'about', [step_one, boom], [], True)
bigjobs.start(srv, 'f', 'W.esp:000007')
wait()
j = bigjobs.status()
check('a failure is reported, its part done is one Undo', j['ok'] is False and 'broke' in j['error'] and j['undo'] == 'Failing job'
      and len(pr.undo_stack) == n + 1)

# a title Windows won't have in a folder's name (the plants job's colon)
bigjobs.JOBS['c'] = ('Plants: a/b "c"?', 'about', [step_one], [], True)
bigjobs.start(srv, 'c', 'W.esp:000007')
wait()
j = bigjobs.status()
check('a title with a colon still gets its backup', j['ok'] is True and os.path.isdir(os.path.join(backups.folder(), j['backup'])), j.get('error'))
del bigjobs.JOBS['c']

# nothing to change: no Undo step
bigjobs.JOBS['n'] = ('Nothing job', 'about', [lambda c: ([], {})], [], True)
n = len(pr.undo_stack)
bigjobs.start(srv, 'n', 'W.esp:000007')
wait()
check('nothing to change: no Undo step, no backup copy', bigjobs.status()['changed'] is False and len(pr.undo_stack) == n
      and not bigjobs.status().get('backup'))

# the page
p = bigjobs.page(srv)
check('page lists the jobs and the worlds, the mod\'s first', p['worlds'][0]['mine'] and any(x['key'] == 'pipboy' for x in p['jobs']))

# every real job's steps are the builders' own, importable
for k in ('t', 'f', 'n'):
    del bigjobs.JOBS[k]
import importlib  # noqa: E402
import inspect  # noqa: E402
bad = []
for k, (_t, _a, steps, then, _w) in bigjobs.JOBS.items():
    for s in steps:
        for name in [ln.split('import ')[1].strip() for ln in inspect.getsource(s).splitlines() if ln.strip().startswith('import ')]:
            try:
                importlib.import_module(name)
            except Exception as e:
                bad.append((k, name, str(e)))
    bad += [(k, t, 'no such job') for t in then if t not in bigjobs.JOBS]
check('every job\'s builders import, every next job exists', not bad, bad)
