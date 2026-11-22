"""door_reach_into_waikiki.py [real] [--home H] [--app A]: the doors the ways-in and doorway steps linked (51) made usable.
The user, 22 Nov 2026: a door hung on a plastered wall caught the crosshair only at its rim. doorray casts rays from 80 in
front of each door at eye height over a grid on its face against everything's collision; a door counts when every ray meets
it first. Before: 22 of 51 (8 partly, 21 not at all): what shut the doorway still standing in front (DoorBarricade, a door's
static twin, a broken door), rubble, or the building's own collision covering the doorway.

Fix, per door, until every ray hits: what blocks it and is loose (a barricade, a door static, a broken door, rubble) taken
away; then the door stood out from the wall in STEP units, at most MOST, its links kept; whoever arrives outside by it is put
in front of it again if it now stands within ARRIVE_CLEAR of the arrival. Touched cells' navmeshes made again. One Undo.
Dry run without `real`; backup; refuses while the game runs (not on a FOLabScratch home)."""
import json, math, os, shutil, struct, subprocess, sys, time

ARGS = sys.argv[1:]
REAL = 'real' in ARGS


def opt(name, default):
    return ARGS[ARGS.index(name) + 1] if name in ARGS else default


HOME = opt('--home', r'C:\Users\AMD RYZEN\Claude Code Projects\FOLab\packaging\out\FOLab')
APP = opt('--app', r'C:\Users\AMD RYZEN\Claude Code Projects\FOLab\app')
HERE = os.path.dirname(os.path.abspath(__file__))
STEP, MOST, ARRIVE_CLEAR = 2.0, 120.0, 70.0
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

import gamedata, project, server, doorswap, doorset, recordio, navbuild  # noqa: E402
sys.path.insert(0, HERE)
import doorray  # noqa: E402
import doorout  # noqa: E402
LOOSE_WORDS = ('barricade', 'rubble', 'debris', 'broken') + doorout.CLUTTER
src = os.path.join(project.PROJECTS_DIR, 'Waikiki.json')
was = project.modified(src)
say('mod', src, time.strftime('%d %b %H:%M', time.localtime(was)))
server.not_while_playing = lambda: None
server.GD = gamedata.GameData(); server.BR = None
pr = project.Project.open('Waikiki'); server.load_game(pr); server.PR = pr
gd = server.GD
name = doorswap.Names(gd, pr)
worlds = {gd.edid(w): w for w in gd.worlds()}
cgrid = gd.grid(worlds[doorset.CITY])
city = {gd.key(c) for c in cgrid.values()}
refs = {rk: (ck, r) for ck, c in pr.cells.items() for rk, r in (c.get('refs') or {}).items() if not r.get('removed')}


def model_of(base):
    try:
        if base.startswith('+'):
            rec = pr.records.get(base)
            m = recordio.field(rec, 'MODL') if rec else None
            return ('meshes' + chr(92) + m) if m else None
        t, e, f, m = gd.describe(gd.from_key(base))
        return gd.model_path(t, m) if m else None
    except Exception:
        return None


def obnd(base):
    try:
        if base.startswith('+'):
            s = next(x for x in pr.records[base]['subs'] if x['tag'] == 'OBND')
            return [int(f['value']) for f in s['fields'] if 'name' in f]
        return list(struct.unpack('<6h', gd.fields(gd.from_key(base))['OBND'][:12]))
    except Exception:
        return [-60, -10, 0, 60, 10, 200]


# the 51: the 16 city doors the 10:06 ways-in run linked, and the 35 of the 11:01 doorways step (its report)
WAYS_IN = ['+012BAE', '+013270', '+013DED', '+0131C1', '+00C851', '+010D5B', '+013AE9', '+012D75', '+006C15', '+0131D4',
           '+012C12', '+012BB8', '+006BBF', '+006C8D', '+006C90', '+0048A4']
cut = json.load(open(os.path.join(HERE, 'cut_doorways_report.json')))['linked']
doors = WAYS_IN + [x['door_ref'] for x in cut]
doors = [d for d in doors if d in refs and (refs[d][1].get('tel') or {}).get('door') in refs]
say('doors', len(doors))
R = doorray.Rays(gd, pr, {k: v for k, v in refs.items() if v[0] in city}, model_of)     # (the city only: the hotels' small worlds stand copies at the same spots)


def drop(rk):
    """Leave a ref out of the rays from now on (it is taken away)."""
    p = refs[rk][1]['p']
    lst = R.grid.get((int(p[0] // 1024), int(p[1] // 1024)), [])
    if rk in lst:
        lst.remove(rk)


ops, report, gone = [], [], set()
for rk in doors:
    ck, r = refs[rk]
    pd = r['tel']['door']
    pck, prr = refs[pd]
    a = prr['tel']['p']
    vx, vy = a[0] - r['p'][0], a[1] - r['p'][1]
    ln = math.hypot(vx, vy)
    out = (vx / ln, vy / ln)
    b = obnd(r['base'])
    first = R.door(rk, out, b)
    res, p, removed = first, list(r['p']), []
    # 1. loose things in its way taken away, and 2. the door stood out from the wall a STEP at a time, until every ray meets it
    def clear(res, p):
        loose = [base for base in res['blocked_by'] if any(w in (name(base)[0] or '').lower() for w in LOOSE_WORDS)
                 or ((name(base)[0] or '').lower().endswith('static') and 'door' in (name(base)[0] or '').lower())]
        took = False
        for ork, orr in list(R.near(p[0], p[1])):
            dx, dy = orr['p'][0] - p[0], orr['p'][1] - p[1]
            along, across = dx * out[0] + dy * out[1], abs(-dx * out[1] + dy * out[0])
            # (only what stands in front of this door: a neighbouring doorway's static stays)
            big = any(w in (name(orr['base'])[0] or '').lower() for w in ('rubble', 'heap'))    # (a heap is wide: further out)
            reach = 320 if big else 140
            if ork != rk and orr['base'] in loose and -40 <= along <= reach and across <= reach and ork not in gone:
                gone.add(ork)
                drop(ork)
                ops.append({'op': 'remove', 'cell': refs[ork][0], 'ref': ork})
                removed.append(name(orr['base'])[0])
                took = True
        return took
    moved = 0.0
    for _round in range(200):
        if res['hits'] == res['rays']:
            break
        if clear(res, p):
            res = R.door(rk, out, b, p)
            continue
        if moved >= MOST:
            break
        moved += STEP
        p = list(r['p'])
        p[0], p[1] = round(r['p'][0] + out[0] * moved, 2), round(r['p'][1] + out[1] * moved, 2)
        res = R.door(rk, out, b, p)
    if moved:
        if res['hits'] < res['rays']:
            p, moved = list(r['p']), 0.0           # (no good: left where it was, reported)
            res = R.door(rk, out, b, p)
        else:
            ops.append({'op': 'move', 'cell': ck, 'ref': rk, 'p': p})
            # the arrival outside stays in front of it
            if (a[0] - p[0]) * out[0] + (a[1] - p[1]) * out[1] < ARRIVE_CLEAR:
                k = ARRIVE_CLEAR + 40.0
                na = [round(p[0] + out[0] * k, 2), round(p[1] + out[1] * k, 2), a[2], a[3], a[4], a[5]]
                ops.append({'op': 'tel', 'cell': pck, 'ref': pd, 'tel': dict(prr['tel'], p=na)})
    report.append({'door': rk, 'is': name(r['base'])[0], 'before': '%d/%d' % (first['hits'], first['rays']),
                   'after': '%d/%d' % (res['hits'], res['rays']), 'removed': removed, 'stood_out': moved, 'cell': ck,
                   'still_blocked_by': {name(k)[0]: v for k, v in res['blocked_by'].items()}})
    say(rk, name(r['base'])[0], report[-1]['before'], '->', report[-1]['after'], 'removed', removed, 'out %.0f' % moved,
        report[-1]['still_blocked_by'] or '')
ok_before = sum(1 for x in report if x['before'].split('/')[0] == x['before'].split('/')[1])
ok_after = sum(1 for x in report if x['after'].split('/')[0] == x['after'].split('/')[1])
say('hit across the face: before %d of %d, after %d of %d | removed %d | stood out %d, most %.0f' % (
    ok_before, len(report), ok_after, len(report), len(gone), sum(1 for x in report if x['stood_out']), max([x['stood_out'] for x in report] or [0])))
json.dump(report, open(os.path.join(HERE, 'door_reach_report.json'), 'w'), indent=1)
if not ops:
    sys.exit('nothing to do: run already?')
if not REAL:
    say('dry run: nothing saved (the list: door_reach_report.json)')
    sys.exit(0)
if project.modified(src) != was:
    sys.exit('Waikiki changed while this ran: stopping')
back = os.path.join(HOME, 'backups', 'Waikiki before door reach %s' % time.strftime('%m%d-%H%M'))
os.makedirs(back)
for f in (src, os.path.splitext(src)[0] + '.changes'):
    if os.path.isfile(f):
        shutil.copy2(f, back)
say('backup', back)
label = 'Doors one can reach: what stood in front taken away, doors stood clear of their walls'
pr.apply(label, ops)
say('applied and saved')
cells = sorted({x['cell'] for x in report if x['stood_out'] or x['removed']})
t1 = time.time()
nops, nrep = navbuild.generate_area(gd, pr, cells)
pr.apply(label, nops, merge=True)
say('navmeshes made again for %d cells in %.0fs' % (len(cells), time.time() - t1), {k: nrep.get(k) for k in ('cells', 'doors', 'doors_missed', 'neighbours')})
# checks: the rays again over the saved mod, every link both ways
refs = {rk: (ck, r) for ck, c in pr.cells.items() for rk, r in (c.get('refs') or {}).items() if not r.get('removed')}
R = doorray.Rays(gd, pr, {k: v for k, v in refs.items() if v[0] in city}, model_of)     # (the city only: the hotels' small worlds stand copies at the same spots)
bad, full = [], 0
for rk in doors:
    ck, r = refs[rk]
    pd = r['tel']['door']
    a = refs[pd][1]['tel']['p']
    vx, vy = a[0] - r['p'][0], a[1] - r['p'][1]
    ln = math.hypot(vx, vy)
    res = R.door(rk, (vx / ln, vy / ln), obnd(r['base']))
    if res['hits'] == res['rays']:
        full += 1
    else:
        bad.append('%s %d/%d' % (rk, res['hits'], res['rays']))
    if (refs[pd][1].get('tel') or {}).get('door') != rk:
        bad.append('%s not linked both ways' % rk)
same = doorswap.same_arrivals(pr)
if same:
    bad.append('pairs arriving at one spot: %s' % same)
say('after, from the saved mod: hit across the face %d of %d' % (full, len(doors)))
say('CHECKS: ' + ('all good' if not bad else 'PROBLEMS: ' + '; '.join(bad)))
