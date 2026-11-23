"""arrivals_into_waikiki.py [real] [--home H] [--app A]: every door puts you clear of what stands there (the user's third
report, 23 Nov 2026: out of a door and inside a rusted lean-to, FOLabWaikiki 96192, 58800). app/arrivalcheck.py (the doors
branch) judges every link's arrival against every ref's solid collision, the navmesh and its door; each one in something
(blocked, or under a roof among walls outside) is moved out from its door to the first clear spot, as far as needed; one
only off the navmesh no further than 300. One Undo; backup; refuses while the game runs (not on a FOLabScratch home).

--app must hold arrivalcheck.py (default: the doors branch's app). Dry run without `real`: the check and what it would move."""
import json, os, shutil, subprocess, sys, time

ARGS = sys.argv[1:]
REAL = 'real' in ARGS


def opt(name, default):
    return ARGS[ARGS.index(name) + 1] if name in ARGS else default


HOME = opt('--home', r'C:\Users\AMD RYZEN\Claude Code Projects\FOLab\packaging\out\FOLab')
APP = opt('--app', r'C:\Users\AMD RYZEN\Claude Code Projects\FOLab\.claude\worktrees\zealous-rosalind-5e1645\app')
HERE = os.path.dirname(os.path.abspath(__file__))
os.environ['FOLAB_HOME'] = HOME
os.environ['FOLAB_NO_GAME_WRITES'] = '1'
sys.path.insert(0, APP)
sys.stdout.reconfigure(encoding='utf-8')
t0 = time.time()
say = lambda *a: print('%5.0fs' % (time.time() - t0), *a, flush=True)
if REAL and 'FOLabScratch' not in HOME:
    running = subprocess.run(['tasklist'], capture_output=True, text=True).stdout.lower()
    busy = [n for n in ('falloutnv.exe', 'nv-rs.exe', 'nvrs.exe', 'folab.exe', 'modorganizer.exe', 'nvse_loader.exe', 'play.exe', 'geck.exe')
            if n in running]
    if busy:
        sys.exit('not while these run: ' + ', '.join(busy))
import gamedata, project, server, arrivalcheck  # noqa: E402
src = os.path.join(project.PROJECTS_DIR, 'Waikiki.json')
was = project.modified(src)
say('mod', src, time.strftime('%d %b %H:%M', time.localtime(was)), '| app', APP)
server.not_while_playing = lambda: None
server.GD = gamedata.GameData(); server.BR = None
pr = project.Project.open('Waikiki'); server.load_game(pr); server.PR = pr
gd = server.GD
W = arrivalcheck.World(gd, pr)
res = arrivalcheck.check(gd, pr, W)
say('before: links %d, flagged %d %s, in something %d' % (res['links'], len(res['bad']), res['counts'], len(arrivalcheck.errors_of(res))))
ops, rep = arrivalcheck.fix_ops(gd, pr, res['bad'], W)
say('to move', rep['moved'], '| of them clear but off the navmesh', rep.get('off_mesh_kept', 0), '| no spot found', len(rep['left']))
if not ops:
    sys.exit('nothing to do: run already?')
if not REAL:
    say('dry run: nothing saved')
    sys.exit(0)
if project.modified(src) != was:
    sys.exit('Waikiki changed while this ran: stopping')
back = os.path.join(HOME, 'backups', 'Waikiki before arrivals %s' % time.strftime('%m%d-%H%M'))
os.makedirs(back)
for f in (src, os.path.splitext(src)[0] + '.changes'):
    if os.path.isfile(f):
        shutil.copy2(f, back)
say('backup', back)
pr.apply('Doors put you clear of what stands there', ops)
say('applied and saved')
res2 = arrivalcheck.check(gd, pr)
errors = arrivalcheck.errors_of(res2)
say('after, from the saved mod: links %d, flagged %d %s, in something %d' % (res2['links'], len(res2['bad']), res2['counts'], len(errors)))
json.dump({'before': res['counts'], 'after': res2['counts'], 'left': res2['bad']}, open(os.path.join(HERE, 'arrivals_report.json'), 'w'), indent=1)
say('CHECKS: ' + ('all good (no door puts you in something; %d only off the navmesh, warnings)' % len(res2['bad']) if not errors else
                  'PROBLEMS: %d doors still put you in something: %s' % (len(errors), [r['ref'] for r in errors[:20]])))
