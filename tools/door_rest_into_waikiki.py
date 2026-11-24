"""door_rest_into_waikiki.py [real] [--home H] [--app A]: the doors the door pick step left picked at only some spots (the
Workshop's item 2, 23 Nov 2026), from door_rest_survey.json (door_rest_survey.py, then door_rest_game.py):

1. bars: a DoorBarricade standing 89-110 in front of a door that something leads to (it covered the whole leaf; the game
   stands its bars there on doors it shuts, doorclear.py; these doors were given a way in after). Taken out only if
   nothing names it, it isn't persistent, and the arrival stays clear.
2. size: doors FOLab stood at 1 where the game stands the same door in the same building at 0.95 or 0.9 (townbuild's
   catalogue left a door's scale out; fixed on the doors branch): set to the game's.
3. moved: a door the game has no like of, moved out along its face by the survey's best 1..6 where that picks more and
   what is under its leaf stays within 2 of what it was (it doesn't float), no other door within OTHER_DOOR, and the
   arrival not left behind it (one closer than ARRIVE_CLEAR set in front again, never off the navmesh if it was on).

Each door first picked as the survey found it (a door since changed is left and listed). Held (listed with the reason):
doors as the game stands them, moves that would float, moves of doors in the game's own pose, loose things that are
FOLab's seated rubble heaps or a copied place's crates. Touched cells' navmeshes made again; then every door picked again,
arrivalcheck over the whole mod (no new errors). One Undo; no backup (the install makes it); refuses while the game runs
(not on a FOLabScratch home). Dry run without `real`."""
import collections, json, math, os, struct, subprocess, sys, time

ARGS = sys.argv[1:]
REAL = 'real' in ARGS


def opt(name, default):
    return ARGS[ARGS.index(name) + 1] if name in ARGS else default


HOME = opt('--home', r'C:\Users\AMD RYZEN\Claude Code Projects\FOLab\packaging\out\FOLab')
APP = opt('--app', r'C:\Users\AMD RYZEN\Claude Code Projects\FOLab\app')
HERE = os.path.dirname(os.path.abspath(__file__))
ARRIVE_CLEAR, OTHER_DOOR, FLOAT_MOST, RESEAT = 70.0, 24.0, 2.0, 96.0
SUPPORT_UP, SUPPORT_DOWN = 24.0, 200.0
os.environ['FOLAB_HOME'] = HOME
os.environ['FOLAB_NO_GAME_WRITES'] = '1'
sys.path.insert(0, APP)
sys.path.insert(0, HERE)
sys.stdout.reconfigure(encoding='utf-8')
t0 = time.time()
say = lambda *a: print('%5.0fs' % (time.time() - t0), *a, flush=True)
if REAL and 'FOLabScratch' not in HOME:
    running = subprocess.run(['tasklist'], capture_output=True, text=True).stdout.lower()
    busy = [n for n in ('falloutnv.exe', 'nv-rs.exe', 'nvrs.exe', 'folab.exe', 'modorganizer.exe', 'nvse_loader.exe', 'play.exe', 'geck.exe')
            if n in running]
    if busy:
        sys.exit('not while these run: ' + ', '.join(busy))
import gamedata, project, server, doorswap, recordio, navbuild, arrivalcheck, land as _land  # noqa: E402
import doorpick  # noqa: E402
src = os.path.join(project.PROJECTS_DIR, 'Waikiki.json')
was = project.modified(src)
say('mod', src, time.strftime('%d %b %H:%M', time.localtime(was)))
if REAL and getattr(project, 'holder', None) and project.holder(src):
    sys.exit('Waikiki is open in FOLab: close it first')
server.not_while_playing = lambda: None
server.GD = gamedata.GameData(); server.BR = None
pr = project.Project.open('Waikiki'); server.load_game(pr); server.PR = pr
gd = server.GD
name = doorswap.Names(gd, pr)
rep = json.load(open(os.path.join(HERE, 'door_rest_survey.json'), encoding='utf-8'))
rows = {r['door']: r for r in rep['rows'] if r.get('picked')}
_g = {}


def group_of(ck):
    if ck not in _g:
        try:
            w = gd.ext_cells.get(gd.from_key(ck))
        except Exception:
            w = None
        _g[ck] = ('world', w) if w is not None else ('place', ck)
    return _g[ck]


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
        return None


def all_refs():
    return {rk: (ck, r) for ck, c in pr.cells.items() for rk, r in (c.get('refs') or {}).items() if not r.get('removed')}


def leads_of(refs):
    leads, named = {}, set()
    for rk, (ck, r) in refs.items():
        t = r.get('tel') or {}
        if t.get('door') and t.get('p'):
            leads.setdefault(t['door'], []).append((ck, rk, t['p']))
            named.add(t['door'])
    return leads, named


def on_navmesh(ck, x, y, z):
    m = pr.navmesh.get(ck)
    if not m:
        return False
    vs = m['verts']
    for t in m['tris']:
        a, b, c = (vs[i] for i in t[:3])
        if abs((a[2] + b[2] + c[2]) / 3.0 - z) > 120:
            continue
        def s_(p1, q1, r1): return (p1[0] - r1[0]) * (q1[1] - r1[1]) - (q1[0] - r1[0]) * (p1[1] - r1[1])
        d = (s_((x, y), a, b), s_((x, y), b, c), s_((x, y), c, a))
        if not (min(d) < 0 < max(d)):
            return True
    return False


def cell_at(ck, x, y):
    g = group_of(ck)
    if g[0] != 'world':
        return ck
    c = gd.grid(g[1]).get((int(x // 4096), int(y // 4096)))
    return gd.key(c) if c is not None else ck


forms = {}


def land_z(world, x, y):
    def form(cx, cy):
        if (world, cx, cy) not in forms:
            cell = gd.grid(world).get((cx, cy))
            f_ = None
            if cell is not None:
                mine = pr.land.get(gd.key(cell))
                e_ = gd.land_at(world, cx, cy)
                if mine or e_:
                    f_ = dict(mine) if mine else _land.decode(gd, e_, {})
            forms[(world, cx, cy)] = f_
        return forms[(world, cx, cy)]
    gx, gy = x / 128.0, y / 128.0
    x0, y0 = int(math.floor(gx)), int(math.floor(gy))
    fx, fy = gx - x0, gy - y0
    v = []
    for a, b in ((x0, y0), (x0 + 1, y0), (x0, y0 + 1), (x0 + 1, y0 + 1)):
        cx, cy = a // 32, b // 32
        f_ = form(cx, cy)
        if not f_:
            return None
        v.append(float(f_['h'][(b - cy * 32) * 33 + (a - cx * 32)]))
    return (v[0] * (1 - fx) + v[1] * fx) * (1 - fy) + (v[2] * (1 - fx) + v[3] * fx) * fy


def floor_gap(W, ck, rk, r, box, out, p):
    """The door's foot over what is under its leaf, the worst of six spots; None where nothing is within reach."""
    s = float(r.get('s') or 1.0)
    c, sn = math.cos(p[5]), math.sin(p[5])
    thin_x = (box[3] - box[0]) < (box[4] - box[1])
    width = ((box[4] - box[1]) if thin_x else (box[3] - box[0])) * s
    thick = ((box[3] - box[0]) if thin_x else (box[4] - box[1])) * s
    mx, my = (box[0] + box[3]) / 2.0 * s, (box[1] + box[4]) / 2.0 * s
    q = (p[0] + mx * c + my * sn, p[1] - mx * sn + my * c)
    foot = p[2] + box[2] * s
    tx, ty = -out[1], out[0]
    worst = None
    for u in (-0.4, 0.0, 0.4):
        for f in (thick / 2.0, -thick / 2.0):
            x = q[0] + tx * u * width + out[0] * f
            y = q[1] + ty * u * width + out[1] * f
            best = None
            for t, ork in W.around(group_of(ck), x, y, 4, {rk}):
                d = arrivalcheck._hit((x, y, foot + SUPPORT_UP), (0.0, 0.0, -1.0), t[0])
                if d is not None and d <= SUPPORT_DOWN:
                    best = max(best, foot + SUPPORT_UP - d) if best is not None else foot + SUPPORT_UP - d
            g = group_of(ck)
            if g[0] == 'world':
                z = land_z(g[1], x, y)
                if z is not None and foot + SUPPORT_UP - SUPPORT_DOWN <= z <= foot + SUPPORT_UP:
                    best = z if best is None else max(best, z)
            if best is None:
                return None
            worst = foot - best if worst is None else max(worst, foot - best)
    return worst


refs = all_refs()
leads, named = leads_of(refs)
P = doorpick.Picker(gd, pr, refs, model_of, group_of)
W = arrivalcheck.World(gd, pr)


def pick(rk, p=None, refs_=None):
    ck, r = refs[rk]
    a = leads[rk][0][2]
    vx, vy = a[0] - r['p'][0], a[1] - r['p'][1]
    ln = math.hypot(vx, vy)
    return P.door(rk, (vx / ln, vy / ln), obnd(r['base']), p)


arr_before = arrivalcheck.check(gd, pr, W)
err_before = {(b.get('door'), b.get('ref')) for b in arrivalcheck.errors_of(arr_before)} if arrivalcheck.errors_of(arr_before) else set()
say('arrivals before:', arr_before['counts'])

ops, done, held = [], collections.Counter(), collections.defaultdict(list)
bars_gone, sized, moved, cells = [], [], [], set()
for rk, row in rows.items():
    if row['picked'][0] == row['spots']:
        continue
    if rk not in refs or rk not in leads:
        held['gone or no longer linked'].append(rk)
        continue
    ck, r = refs[rk]
    now = pick(rk)
    if now['picked'] != row['picked'][0]:
        held['changed since the survey'].append(rk)
        continue
    g2 = row.get('game2')
    as_game = bool(g2 and g2['pose_off'] < 20)
    # 1. a bar in front
    if row.get('bar'):
        ok = []
        for b in row['bar']['bars']:
            if b not in refs:
                continue
            br = refs[b][1]
            if br.get('tel') or br.get('persistent') or b in named or br.get('edid') or name(br['base'])[0] != 'DoorBarricade':
                held['bar is named, linked or persistent'].append(rk)
                ok = []
                break
            ok.append(b)
        if ok:
            for b in ok:
                ops.append({'op': 'remove', 'cell': refs[b][0], 'ref': b})
                cells.add(refs[b][0])
                bars_gone.append(b)
            done['bar taken out'] += 1
            continue
    # 2. the game's size
    if row.get('at_game_s') and as_game and row['at_game_s']['picked'] >= row['picked'][0]:
        ops.append({'op': 'move', 'cell': ck, 'ref': rk, 'p': list(r['p']), 's': row['at_game_s']['s']})
        sized.append((rk, row['at_game_s']['s']))
        done['set to the game\'s size'] += 1
        continue
    # 3. moved out
    best = row['best_out']
    if not best or row['picked'][best] <= row['picked'][0]:
        held['as the game stands it' if as_game else 'nothing within 6 picks more'].append(rk)
        continue
    if as_game:
        held['moving would help, but it stands as the game stands it'].append(rk)
        continue
    out = now['normal']
    p = list(r['p'])
    p[0], p[1] = round(r['p'][0] + out[0] * best, 2), round(r['p'][1] + out[1] * best, 2)
    box = obnd(r['base'])
    g0 = floor_gap(W, ck, rk, r, box, out, r['p'])
    gb = floor_gap(W, ck, rk, r, box, out, p)
    if g0 is None or gb is None or gb > max(g0, 0.0) + FLOAT_MOST:
        held['would float (%s -> %s under its foot)' % ('none' if g0 is None else round(g0), 'none' if gb is None else round(gb))].append(rk)
        continue
    near_door = [o for o, orr in P.near(group_of(ck), p[0], p[1]) if o != rk and name(orr['base'])[1] == 'DOOR'
                 and math.dist(orr['p'][:3], p[:3]) < OTHER_DOOR]
    if near_door:
        held['another door within %d' % OTHER_DOOR].append(rk)
        continue
    res = pick(rk, p)
    if res['picked'] <= now['picked']:
        held['moving picks no more now'].append(rk)
        continue
    mine = [{'op': 'move', 'cell': ck, 'ref': rk, 'p': p}]
    blocked = False
    for ack, ark, a in leads[rk]:
        if (a[0] - p[0]) * out[0] + (a[1] - p[1]) * out[1] < ARRIVE_CLEAR:
            na = list(a)
            na[0], na[1] = round(p[0] + out[0] * (ARRIVE_CLEAR + 40), 2), round(p[1] + out[1] * (ARRIVE_CLEAR + 40), 2)
            g = group_of(ck)
            by_, inside_ = W.judge(g, na[0], na[1], na[2] - 8.0, W.outside(g), skip=(rk,))
            if by_ or inside_:
                blocked = True        # (the spot in front of it stands in something: 2 of 49 on the first rehearsal)
                break
            if on_navmesh(cell_at(ck, na[0], na[1]), na[0], na[1], na[2] - 8) or not on_navmesh(cell_at(ck, a[0], a[1]), a[0], a[1], a[2] - 8):
                mine.append({'op': 'tel', 'cell': ack, 'ref': ark, 'tel': dict(refs[ark][1]['tel'], p=na)})
    if blocked:
        held['its arrival would have to go where something stands'].append(rk)
        continue
    ops.extend(mine)
    cells.add(ck)
    moved.append((rk, best, now['picked'], res['picked']))
    done['moved out'] += 1
say('done', dict(done))
for k, v in held.items():
    say('   held:', len(v), k)
say('bars out', len(bars_gone), '| doors sized', collections.Counter(s for _, s in sized), '| doors moved', len(moved),
    'by', collections.Counter(b for _, b, _, _ in moved))
if not REAL:
    say('dry run: nothing saved')
    sys.exit(0)
if project.modified(src) != was:
    sys.exit('Waikiki changed while this ran: stopping')
label = 'Doors one can open from more of the leaf'
touched = {o['ref'] for o in ops if o['op'] == 'move'} | {rk for rk, row in rows.items() if row.get('bar') and
                                                          any(b in bars_gone for b in row['bar']['bars'])}
was_on = {}
for rk in touched:
    ck = refs[rk][0]
    for ack, ark, a in leads.get(rk, ()):
        was_on[ark] = on_navmesh(cell_at(ck, a[0], a[1]), a[0], a[1], a[2] - 8)
pr.apply(label, ops)
outside = sorted(c for c in cells if group_of(c)[0] == 'world')
places = sorted(c for c in cells if group_of(c)[0] == 'place')
if outside:
    t1 = time.time()
    nops, nrep = navbuild.generate_area(gd, pr, outside)
    pr.apply(label, nops, merge=True)
    say('outside navmeshes made again: %d cells in %.0fs' % (len(outside), time.time() - t1))
pops = []
for c in places:
    try:
        data, words = navbuild.generate(gd, pr, c)
        pops.append({'op': 'navmesh', 'cell': c, 'mesh': data})
    except Exception as e:
        say('   place navmesh not made', c, e)
if pops:
    pr.apply(label, pops, merge=True)
say('applied and saved')

# --- an arrival on the navmesh before and off it now (the mesh made again round it) onto the nearest triangle that is clear
refs = all_refs()
leads, named = leads_of(refs)
W = arrivalcheck.World(gd, pr)
reseat, lost = [], []
for rk in touched:
    ck = refs[rk][0]
    for ack, ark, a in leads.get(rk, ()):
        cc = cell_at(ck, a[0], a[1])
        if not was_on.get(ark) or on_navmesh(cc, a[0], a[1], a[2] - 8):
            continue
        m = pr.navmesh.get(cc)
        cands = []
        for t in (m or {}).get('tris', ()):
            vs = [m['verts'][i] for i in t[:3]]
            c = [sum(v[j] for v in vs) / 3.0 for j in range(3)]
            d = math.hypot(c[0] - a[0], c[1] - a[1])
            if d < RESEAT and abs(c[2] - a[2]) < 40:
                cands.append((d, c))
        g = group_of(ck)
        put = None
        for d, c in sorted(cands):
            # (the first spot on the way from the arrival to the triangle's middle that is on the mesh and clear: the middle
            # alone can be under a porch roof when its edge isn't)
            for f in (0.2, 0.35, 0.5, 0.65, 0.8, 1.0):
                x, y = a[0] + (c[0] - a[0]) * f, a[1] + (c[1] - a[1]) * f
                z = a[2] - 8 + (c[2] - (a[2] - 8)) * f
                if not on_navmesh(cc, x, y, z):
                    continue
                by_, inside_ = W.judge(g, x, y, z, W.outside(g), skip=(rk,))
                if not by_ and not inside_:
                    put = (x, y, z)
                    break
            if put:
                break
        if put:
            na = list(a)
            na[0], na[1], na[2] = round(put[0], 2), round(put[1], 2), round(put[2] + 8, 2)
            reseat.append({'op': 'tel', 'cell': ack, 'ref': ark, 'tel': dict(refs[ark][1]['tel'], p=na)})
        else:
            lost.append(ark)
if reseat:
    pr.apply(label, reseat, merge=True)
say('arrivals put back on the navmesh', len(reseat), '| none clear within %d' % RESEAT, lost)

# --- after ---
refs = all_refs()
leads, named = leads_of(refs)
P = doorpick.Picker(gd, pr, refs, model_of, group_of)
W = arrivalcheck.World(gd, pr)
before_spots = after_spots = 0
worse, full_after = [], 0
for rk, row in rows.items():
    if rk not in refs or rk not in leads:
        continue
    res = pick(rk)
    before_spots += row['picked'][0]
    after_spots += res['picked']
    full_after += res['picked'] == res['spots']
    if res['picked'] < row['picked'][0]:
        worse.append((rk, row['picked'][0], res['picked']))
arr_after = arrivalcheck.check(gd, pr, W)
err_after = {(b.get('door'), b.get('ref')) for b in arrivalcheck.errors_of(arr_after)} if arrivalcheck.errors_of(arr_after) else set()
new_err = err_after - err_before
one_way = [rk for rk, _, _, _ in moved if (refs[rk][1].get('tel') or {}).get('door') in refs
           and (refs[refs[rk][1]['tel']['door']][1].get('tel') or {}).get('door') != rk]
say('doors in the list: picked everywhere %d of %d; spots %d -> %d of %d' % (
    full_after, len(rows), before_spots, after_spots, sum(r['spots'] for r in rows.values())))
say('arrivals after:', arr_after['counts'], '| new errors', len(new_err), '| doors picked less', len(worse), worse[:10],
    '| links one way', len(one_way))
json.dump({'bars_gone': bars_gone, 'sized': sized, 'moved': moved, 'held': held, 'worse': worse, 'new_arrival_errors': sorted(map(str, new_err))},
          open(os.path.join(HERE, 'door_rest_report.json'), 'w', encoding='utf-8'), indent=1)
say('CHECKS: ' + ('all good' if not worse and not new_err and not one_way and not lost else 'PROBLEMS: worse %d, new arrival errors %d, one way %d, arrivals left off the navmesh %d' % (
    len(worse), len(new_err), len(one_way), len(lost))))
