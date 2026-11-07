"""Does this place really work in the game? A report, not the user walking it.

The game walks a place, writes what it finds, a report reads it back (after the Workshop's game test harness):

    make_plan(gd, project, cell)     what to check, from what FOLab already has: floor points per square from the navmesh,
                                     doors and where they lead, things that should rest on something, who was placed
    run_test(...)                    gametestguard's isolation round the game; the checker is gametestcheck's text
    make_report(plan, text, ...)     the result file to findings, worst first, whether the run finished or not

The real start is launch_real(): it needs the words from the page (CONFIRM), and refuses under tests. Tests hand run_test
a fake game. Nothing has yet run in the real game: docs/game-test-first-run.md says what only that can prove.

Engine apart from game: everything about how the original game is run is in launch_real, game_settings and
gametestcheck; a source port would change those three and keep the plan and the report."""
import json
import math
import os
import shutil
import struct
import subprocess
import threading
import time

import espwrite
import gametestcheck as C
import gametestguard as G
import loadorder
import navbuild
import project
import refinfo
import tes4

CONFIRM = 'START THE GAME'
TEST_PREFIX = 'FOLabGT '                # (the test copy's name: never the plugin installed under the mod's own name)
SQUARE = 256.0                          # (a floor point for every square this size, per level)
LEVEL = 128.0
MAX_POINTS, MAX_DOORS, MAX_THINGS, MAX_ACTORS, MAX_WALKS = 240, 40, 150, 40, 3
REST_TYPES = {'MISC', 'WEAP', 'ARMO', 'AMMO', 'ALCH', 'BOOK', 'NOTE', 'KEYM', 'CONT', 'FURN', 'IMOD', 'CHIP', 'CMNY', 'CCRD', 'TERM'}
WALKER = ('1ERefugeeAAM', 'DefaultFollowPlayerFar')
WALK_TICKS = 300

# seconds each step takes, to cap a run by its size (ticks are every 2 frames: about 30 a second at 60 frames)
SECONDS = {'go': 25, 'point': 2.5, 'thing': 1, 'actor': 2, 'door': 30, 'walk': 15}

SEVERITIES = ('critical', 'error', 'warn', 'info')
# fall and move limits, in game units (a metre is about 70)
FELL = 256.0            # below the floor by this much: through it
DROPPED = 64.0          # below the floor by this: the floor isn't where the navmesh said
STILL_FALLING = 24.0    # between the two looks, a beat apart
PUSHED = 48.0           # sideways: something solid at the spot pushed the player off it
LIFTED = 64.0           # above the floor: standing on something there
BOX_NEAR = 48.0         # a ray this short counts as blocked; nearly all round is boxed in
FLOAT = 16.0            # a thing's base over what's under it
BURIED = 24.0           # what's under it is higher than its base
THING_MOVED = 32.0      # physics moved it from where it was put
ACTOR_FELL = 128.0
LANDED_FAR = 128.0


# ---------- the plan ----------

def _mesh_of(gd, pr, ckey):
    """(mesh dicts with verts and tris, where it came from, notes). The mod's, else the game's, else one made just for this
    plan and not kept."""
    notes = []
    now = pr.navmesh.get(ckey)
    if now and not now.get('stub'):
        return [now] + [o for o in now.get('others', []) if not o.get('stub')], 'the mod\'s navmesh', notes
    game = navbuild.game_entries(gd, ckey)
    if game:
        return [navbuild.game_copy(gd, e) for e in game], 'the game\'s navmesh', notes
    if navbuild.is_outside(gd, ckey):
        return [], 'none', ['This square has no navmesh and FOLab makes outside ones by area: only its doors and things are checked.']
    try:
        data, _rep = navbuild.generate(gd, pr, ckey)
    except (navbuild.NavError, ValueError, KeyError, IndexError) as e:
        return [], 'none', ['No navmesh could be made for the floor points (%s).' % e]
    notes.append('The place has no navmesh yet: the floor points come from one made just for this plan (not kept).')
    return [data], 'made for this plan', notes


def floor_points(meshes, square=SQUARE, level=LEVEL):
    """One point per square per level, on the triangle whose middle is nearest the square's, so every piece of floor the
    navmesh knows is stood on."""
    best = {}
    for m in meshes:
        v = m['verts']
        for t in m['tris']:
            a, b, c = v[t[0]], v[t[1]], v[t[2]]
            x, y, z = (a[0] + b[0] + c[0]) / 3, (a[1] + b[1] + c[1]) / 3, (a[2] + b[2] + c[2]) / 3
            k = (math.floor(x / square), math.floor(y / square), round(z / level))
            d = (x - (k[0] + 0.5) * square) ** 2 + (y - (k[1] + 0.5) * square) ** 2
            if k not in best or d < best[k][0]:
                best[k] = (d, x, y, z)
    return [[round(p[1], 1), round(p[2], 1), round(p[3], 1)] for _k, p in sorted(best.items())]


def islands(meshes):
    """How many separate pieces the mesh is in, by triangles sharing an edge: floors no one can walk between."""
    out = []
    for m in meshes:
        tris = m['tris']
        up = list(range(len(tris)))

        def find(i):
            while up[i] != i:
                up[i] = up[up[i]]
                i = up[i]
            return i
        edges = {}
        for n, t in enumerate(tris):
            for a, b in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])):
                k = (min(a, b), max(a, b))
                if k in edges:
                    up[find(n)] = find(edges[k])
                else:
                    edges[k] = n
        sizes = {}
        for n in range(len(tris)):
            sizes.setdefault(find(n), []).append(n)
        for group in sizes.values():
            out.append({'tris': len(group), 'at': list(m['verts'][tris[group[0]][0]])[:3]})
    return sorted(out, key=lambda g: -g['tris'])


def _handle(pr, key):
    """(file, 6 hex digits) that GetFormFromMod finds a form by; '@mod' for the mod itself, filled in when the test copy's name is known."""
    if key.startswith('+'):
        return '@mod', key[1:].upper().zfill(6)
    name, low = key.rsplit(':', 1)
    return ('@mod' if name.lower() == pr.plugin.lower() else name), low.upper().zfill(6)


def _low(key):
    """A form's own number, without its file: what a form ID the game prints is compared by."""
    return (key.rsplit(':', 1)[-1] if ':' in key else key[1:]).upper().zfill(6)[-6:]


def _cell_words(gd, pr, ckey):
    """(editor ID, name) of a place, the mod's own too."""
    rec = pr.records.get(ckey)
    if rec:
        import recordio
        return recordio.field(rec, 'EDID') or '', recordio.field(rec, 'FULL') or ''
    f = gd.fields(gd.from_key(ckey))
    return tes4.zstr(f.get('EDID', b'')), tes4.zstr(f.get('FULL', b''))


def _go_there(gd, pr, ckey):
    """How the game is told to go to a place: ('coc', edid) or ('cow', world's edid, grid x, grid y), or None."""
    if navbuild.is_outside(gd, ckey):
        c = gd.from_key(ckey)
        grid = gd.cell_grid(c)
        w = gd.edid(gd.ext_cells[c])
        return ('cow', w, grid[0], grid[1]) if grid and w else None
    edid = _cell_words(gd, pr, ckey)[0]
    return ('coc', edid) if edid else None


def _door_target(gd, pr, ckey, key):
    """Where a door leads as the mod leaves it: {'door', 'cell', 'edid', 'name', 'p', 'interior'}, or None."""
    ch = (pr.cells.get(ckey) or {}).get('refs', {}).get(key) or {}
    if 'tel' in ch and ch['tel']:
        tel = ch['tel']
        dest = None
        for ck, c in pr.cells.items():
            if tel['door'] in c['refs']:
                dest = ck
                break
        if dest is None and not tel['door'].startswith('+'):
            fid = gd.from_key(tel['door'])
            dest = gd.key(gd.ref_cell[fid]) if fid in gd.ref_cell else None
        edid, name = _cell_words(gd, pr, dest) if dest else ('', '')
        return {'door': tel['door'], 'cell': dest, 'edid': edid, 'name': name, 'p': list(tel['p'])[:6],
                'interior': bool(dest and (dest.startswith('+') or gd.from_key(dest) in gd.interiors))}
    if key.startswith('+'):
        return None
    t = refinfo.door_target(gd, gd.from_key(key))
    if not t:
        return None
    return {'door': t['door'], 'cell': t['cell'], 'edid': t.get('cell_edid', ''), 'name': t.get('cell_name', ''), 'p': t['p'], 'interior': t['interior']}


def _walker(gd):
    """(file, hex) of the NPC and of the follow package the walk test uses: plain ones of the game's, or None."""
    out = []
    for want in WALKER:
        hit = next((f for f, (_i, r) in gd.forms.items() if r.tag in ('NPC_', 'PACK') and f >> 24 == 0 and gd.edid(f) == want), None)
        if hit is None:
            return None
        out.append(('FalloutNV.esm', '%06X' % (hit & 0xFFFFFF)))
    return out


def _thin(items, most):
    if len(items) <= most:
        return items
    step = len(items) / most
    return [items[int(n * step)] for n in range(most)]


def _nearest(points, p):
    return min(points, key=lambda q: (q[0] - p[0]) ** 2 + (q[1] - p[1]) ** 2 + (q[2] - p[2]) ** 2) if points else None


def _bottom(gd, base, scale):
    """How far under a thing's middle its base is, from its bounds (0 when it has none or is the mod's own)."""
    if base is None:
        return 0.0
    b = gd.fields(base).get('OBND')
    if not b or len(b) < 12:
        return 0.0
    return struct.unpack_from('<6h', b)[2] * (scale or 1.0)


def make_plan(gd, pr, ckey, walks=True, run=''):
    """Everything to check in one place, as plain data, with the plan lines the checker reads."""
    go = _go_there(gd, pr, ckey)
    edid, name = _cell_words(gd, pr, ckey) if not navbuild.is_outside(gd, ckey) else (gd.edid(gd.ext_cells[gd.from_key(ckey)]), 'Outside')
    plan = {'version': 1, 'run': run, 'cell': ckey, 'edid': edid, 'name': name, 'mod': pr.name, 'plugin': pr.plugin, 'outside': navbuild.is_outside(gd, ckey),
            'points': [], 'doors': [], 'things': [], 'actors': [], 'walks': [], 'notes': [], 'offline': [], 'mesh': {}}
    if not go:
        plan['offline'].append({'kind': 'no_editor_id', 'sev': 'critical', 'text': 'This place has no editor ID, so the game can\'t be sent to it.', 'go': {'cell': ckey}})
    meshes, source, notes = _mesh_of(gd, pr, ckey)
    plan['notes'] += notes
    pts = floor_points(meshes)
    if len(pts) > MAX_POINTS:
        plan['notes'].append('Only %d of %d floor points are stood on, spread evenly, to keep the run short.' % (MAX_POINTS, len(pts)))
        pts = _thin(pts, MAX_POINTS)
    parts = islands(meshes)
    plan['mesh'] = {'source': source, 'triangles': sum(len(m['tris']) for m in meshes), 'pieces': len(parts)}
    for g in parts[1:6]:
        plan['offline'].append({'kind': 'navmesh_piece', 'sev': 'warn', 'text': 'A piece of navmesh (%d triangles) joins nothing else: people can\'t walk to it.' % g['tris'],
                                'go': {'cell': ckey}, 'p': [round(v, 1) for v in g['at']]})
    if not pts:
        plan['notes'].append('No floor points: nothing is stood on.')
    refs = navbuild.place_refs(gd, pr, ckey)
    mine = (pr.cells.get(ckey) or {}).get('refs', {})
    uid = [100]

    def new_id():
        uid[0] += 1
        return uid[0]
    plan['points'] = [{'id': new_id(), 'p': p} for p in pts]
    for r in refs:
        kind = navbuild._base_type(gd, pr, r['bkey'])
        pos = [round(v, 1) for v in r['pos']]
        if r['leads']:
            target = _door_target(gd, pr, ckey, r['ref'])
            near = _nearest(pts, pos)
            front = near if near and math.dist(near, pos) < 512 else pos
            mod, low = _handle(pr, r['ref'])
            d = {'id': new_id(), 'ref': r['ref'], 'mod': mod, 'hex': low, 'p': pos, 'front': front, 'to': target}
            if target is None:
                plan['offline'].append({'kind': 'door_nowhere_on_record', 'sev': 'error', 'text': 'A door says it leads somewhere, but FOLab can\'t find where.', 'go': {'cell': ckey, 'ref': r['ref']}, 'p': pos})
            else:
                plan['doors'].append(d)
        elif r['ref'] in mine and kind in REST_TYPES:
            mod, low = _handle(pr, r['ref'])
            plan['things'].append({'id': new_id(), 'ref': r['ref'], 'mod': mod, 'hex': low, 'p': pos, 'type': kind, 'bottom': round(_bottom(gd, r['base'], r['scale']), 1)})
        elif r['ref'] in mine and kind in ('NPC_', 'CREA'):
            mod, low = _handle(pr, r['ref'])
            plan['actors'].append({'id': new_id(), 'ref': r['ref'], 'mod': mod, 'hex': low, 'p': pos, 'type': kind})
    for name_, most, word in (('doors', MAX_DOORS, 'doors'), ('things', MAX_THINGS, 'things'), ('actors', MAX_ACTORS, 'characters')):
        if len(plan[name_]) > most:
            plan['notes'].append('Only %d of %d %s are checked.' % (most, len(plan[name_]), word))
            plan[name_] = _thin(plan[name_], most)
    who = _walker(gd) if walks else None
    if who and len(pts) >= 2 and not plan['outside']:
        pairs = _far_pairs(pts)[:MAX_WALKS]
        plan['walks'] = [{'id': new_id(), 'a': a, 'b': b, 'ticks': WALK_TICKS} for a, b in pairs]
    plan['walker'] = who
    plan['go'] = list(go) if go else None
    plan['steps'] = plan_steps(plan)
    plan['estimate'] = estimate(plan)
    return plan


def _far_pairs(points):
    """Pairs of points to walk between, far apart and on the same floor: first the longest such, then the next from what's left."""
    rows = sorted(points, key=lambda p: (p[2], p[0], p[1]))
    out, used = [], set()
    for _ in range(MAX_WALKS):
        best = None
        for i, a in enumerate(rows):
            if i in used:
                continue
            for j, b in enumerate(rows):
                if j > i and j not in used and abs(a[2] - b[2]) < LEVEL:
                    d = (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2
                    if d > (SQUARE * 2) ** 2 and (best is None or d > best[0]):
                        best = (d, i, j)
        if not best:
            break
        out.append((rows[best[1]], rows[best[2]]))
        used |= {best[1], best[2]}
    return out


def plan_steps(plan):
    """The lines the checker reads, in order. Doors last: each one leaves the place, so each is followed by a way back."""
    steps, go_id = [], [1]

    def go():
        steps.append([C.GO, go_id[0], 1])
        go_id[0] += 1
    go()
    if plan['points']:
        steps.append([C.CAL, 99, *plan['points'][0]['p']])
    steps += [[C.STAND, p['id'], *p['p']] for p in plan['points']]
    steps += [[C.THING, t['id'], t['mod'], t['hex'], *t['p']] for t in plan['things']]
    steps += [[C.ACTOR, a['id'], a['mod'], a['hex'], *a['p']] for a in plan['actors']]
    steps += [[C.NPC, w['id'], *w['a'], *w['b'], w['ticks']] for w in plan['walks']]
    for d in plan['doors']:
        steps.append([C.DOOR, d['id'], d['mod'], d['hex'], *d['front']])
        go()
    steps.append([C.DONE, 0])
    return steps


def estimate(plan):
    gos = 1 + len(plan['doors'])
    return int(gos * SECONDS['go'] + len(plan['points']) * SECONDS['point'] + len(plan['things']) * SECONDS['thing'] +
               len(plan['actors']) * SECONDS['actor'] + len(plan['doors']) * SECONDS['door'] + sum(w['ticks'] / 30 + SECONDS['walk'] for w in plan['walks']))


def limits_for(plan):
    """The time cap: twice the estimate and some, for a start that's slow; never over an hour."""
    return G.Limits(cap=min(3600, 2 * plan['estimate'] + 420))


# ---------- reading a result file ----------

def read_lines(text):
    """The file to rows, whatever state it's in: {'rows': [dict with 'kind'], 'bad': lines it couldn't read}."""
    rows, bad = [], []
    for raw in text.replace('\r', '').split('\n'):
        line = raw.strip()
        if not line:
            continue
        parts = line.split('|')
        fields = C.RESULTS.get(parts[0])
        if fields is None or len(parts) - 1 != len(fields):
            bad.append(line[:120])
            continue
        row = {'kind': parts[0]}
        try:
            for f, v in zip(fields, parts[1:]):
                row[f] = v if f in C.TEXT_FIELDS else float(v)
        except ValueError:
            bad.append(line[:120])
            continue
        rows.append(row)
    return {'rows': rows, 'bad': bad}


def has_finished(path):
    """Has the checker written its last line?"""
    try:
        with open(path, 'rb') as f:
            f.seek(0, 2)
            f.seek(max(0, f.tell() - 200))
            tail = f.read().replace(b'\r', b'')
    except OSError:
        return False
    return tail.startswith(b'done|') or b'\ndone|' in tail


def _calibrate(rows, plan):
    """Does a ray mean what the checker takes it to? From the one measured first: straight down lands on the floor under the
    player, and facing north goes north. Without this no ray's answer counts."""
    row = next((r for r in rows if r['kind'] == 'cal'), None)
    if not row:
        return {'ok': False, 'why': 'The calibration step wasn\'t reached.'}
    if row['dz'] == -99999:
        return {'ok': False, 'why': 'A ray straight down gave no answer.'}
    if abs(row['dz'] - row['z']) > 64:
        return {'ok': False, 'why': 'A ray straight down landed %d units from the floor under the player: rays don\'t mean what the checker thinks.' % abs(row['dz'] - row['z'])}
    if row['nx'] == -99999:
        return {'ok': False, 'why': 'A ray facing north gave no answer.'}
    if row['ny'] < row['y'] - 1 or abs(row['nx'] - row['x']) > max(abs(row['ny'] - row['y']), 32):
        return {'ok': False, 'why': 'A ray facing north went elsewhere (%.0f, %.0f from the player).' % (row['nx'] - row['x'], row['ny'] - row['y'])}
    return {'ok': True, 'why': ''}


LAST_STEP_ADVICE = [
    ('no lines', 'The game never wrote a word. Look first at jip_ln_nvse.log (the script runner says if a text wouldn\'t compile), then at whether the game reached its main menu.', 'gr-rules'),
    ('no tick', 'The first script ran, but the tick never did. Look at console.txt and at SetGameMainLoopCallback and CompileScript.', 'tick'),
    ('no move', 'The tick ran, but the game never got into the place. The likeliest cause is coc from the main menu without a save.', 'coc'),
    ('no stand', 'The game reached the place, but the first measurement never came. Look at SetPosEx and at reading the plan.', 'plan'),
    ('partway', 'The checker stopped partway. The last line written says which step it was on.', 'partway'),
]


def _advice(rows, ending):
    kinds = {r['kind'] for r in rows}
    if ending in ('finished',):
        return None
    if not rows:
        k = 'no lines'
    elif 'go' not in kinds:
        k = 'no tick'
    elif 'at' not in kinds:
        k = 'no move'
    elif 'stand' not in kinds and 'cal' not in kinds:
        k = 'no stand'
    else:
        k = 'partway'
    a = next(x for x in LAST_STEP_ADVICE if x[0] == k)
    return {'stage': k, 'text': a[1], 'doc': 'docs/game-test-first-run.md#' + a[2]}


def _go(plan, p=None, ref=None):
    out = {'cell': plan['cell']}
    if ref:
        out['ref'] = ref
    if p:
        out['p'] = p
    return out


def _judge_stand(plan, pt, r, rays_ok, add):
    x, y, z = pt['p']
    dz, side = r['z2'] - z, math.hypot(r['x2'] - x, r['y2'] - y)
    still = r['z1'] - r['z2']
    p = [r['x2'], r['y2'], r['z2']]
    at = _go(plan, pt['p'])
    if dz < -FELL or still > STILL_FALLING:
        add('fell_through', 'error', 'The player fell through the floor at (%.0f, %.0f): %.0f below it and %s.' % (x, y, -dz, 'still falling' if still > STILL_FALLING else 'stopped there'), at, p)
    elif dz < -DROPPED:
        add('dropped', 'warn', 'The floor at (%.0f, %.0f) is %.0f lower than the navmesh has it.' % (x, y, -dz), at, p)
    elif dz > LIFTED:
        add('lifted', 'warn', 'At (%.0f, %.0f) the player was lifted %.0f: something stands on that part of the floor.' % (x, y, dz), at, p)
    if side > PUSHED and dz >= -DROPPED:        # (anyone falling drifts: that's the fall, not something on the spot)
        add('pushed_off', 'warn', 'At (%.0f, %.0f) the player was pushed %.0f sideways: something solid is on the spot.' % (x, y, side), at, p)
    if r['water']:
        add('in_water', 'info', 'The point at (%.0f, %.0f) is in water.' % (x, y), at, p)
    if rays_ok:
        rays = [r['d%d' % i] for i in range(8)]
        near = sum(1 for d in rays if 0 <= d < BOX_NEAR)
        if near >= 7:
            add('boxed_in', 'error', 'At (%.0f, %.0f) something is within %d units on %d of 8 sides: nobody fits there.' % (x, y, BOX_NEAR, near), at, p)
        elif near >= 5:
            add('tight', 'info', 'At (%.0f, %.0f) something is close on %d of 8 sides.' % (x, y, near), at, p)


def _judge_thing(plan, t, r, rays_ok, add):
    at = _go(plan, t['p'], t['ref'])
    if not r['found']:
        return add('thing_missing', 'error', 'The game has no such thing: %s %s (%s).' % (t['type'], t['ref'], t['mod']), at, t['p'])
    if r['disabled']:
        return
    fell = t['p'][2] - r['z']
    if abs(fell) > THING_MOVED or math.hypot(r['x'] - t['p'][0], r['y'] - t['p'][1]) > THING_MOVED:
        add('thing_moved', 'warn', 'A %s moved from where it was put (%.0f down): it was left hanging, or physics took it.' % (t['type'], fell), at, [r['x'], r['y'], r['z']])
    if not rays_ok:
        return
    if r['hit'] == -99999:
        return add('nothing_under', 'warn', 'Nothing was found under a %s.' % t['type'], at, t['p'])
    if r['hitform'].upper().endswith(t['hex']):
        return 'own'                # (the ray stopped on the thing: it can't say what's under it)
    base = r['z'] + t.get('bottom', 0)
    if base - r['hit'] > FLOAT:
        add('thing_floating', 'warn', 'A %s floats %.0f over what\'s under it.' % (t['type'], base - r['hit']), at, t['p'])
    elif r['hit'] - base > BURIED:
        add('thing_buried', 'warn', 'A %s has its base %.0f under the first solid thing above it: buried, or under something.' % (t['type'], r['hit'] - base), at, t['p'])


def _judge_actor(plan, a, r, add):
    at = _go(plan, a['p'], a['ref'])
    if not r['found']:
        return add('actor_missing', 'error', 'The game has no such character: %s.' % a['ref'], at, a['p'])
    p = [r['x'], r['y'], r['z']]
    if r['dead']:
        add('actor_dead', 'error', 'A character is dead by the time the player arrives.', at, p)
    if a['p'][2] - r['z'] > ACTOR_FELL:
        add('actor_fell', 'error', 'A character fell %.0f below where they were put: through the floor.' % (a['p'][2] - r['z']), at, p)
    elif r['air']:
        add('actor_in_air', 'warn', 'A character isn\'t on the ground.', at, p)
    if r['water']:
        add('actor_in_water', 'info', 'A character is in water.', at, p)


def _judge_door(plan, d, r, land, add):
    at = _go(plan, d['p'], d['ref'])
    to = d['to'] or {}
    where = to.get('name') or to.get('edid') or 'its other side'
    if not r['found']:
        return add('door_missing', 'error', 'The game has no such door (%s).' % d['ref'], at, d['p'])
    if not r['load']:
        return add('door_not_load', 'error', 'The game doesn\'t treat a door leading to %s as a load door.' % where, at, d['p'])
    if r['locked']:
        return add('door_locked', 'info', 'A door to %s is locked: it wasn\'t gone through.' % where, at, d['p'])
    low = r['form'].strip().upper()[-6:]
    if low.strip('0') == '':
        return add('door_leads_nowhere', 'error', 'A door to %s leads nowhere in the game.' % where, at, d['p'])
    if to.get('interior') and to.get('cell') and low != _low(to['cell']):
        add('door_wrong_place', 'error', 'A door should lead to %s; the game says %s (%s).' % (where, r['name'] or '?', r['form']), at, d['p'])
    if land is None:
        return add('door_not_gone_through', 'warn', 'A door to %s: the walk stopped before landing on the other side.' % where, at, d['p'])
    landed = land['form'].strip().upper()[-6:]
    if to.get('interior') and to.get('cell') and landed != _low(to['cell']):
        add('door_did_not_lead', 'error', 'Through a door to %s, the player ended up in %s (%s).' % (where, land['name'] or '?', land['form']), at, d['p'])
    elif to.get('p'):
        away = math.dist([land['x'], land['y']], to['p'][:2])
        if away > LANDED_FAR:
            add('door_landed_away', 'warn', 'A door to %s lands %.0f from its arrival point.' % (where, away), at, d['p'])
        if to['p'][2] - land['z2'] > FELL:
            add('door_fell', 'error', 'Through a door to %s the player falls %.0f below the arrival.' % (where, to['p'][2] - land['z2']), at, d['p'])
        elif land['z1'] - land['z2'] > STILL_FALLING:
            add('door_fell', 'warn', 'Through a door to %s the player is still falling after arriving.' % where, at, d['p'])


def make_report(plan, text, ending=None, differences=(), problems=(), seconds=None):
    """The result file to findings, worst first, with what was and wasn't reached. Any text at all gives a report: a run
    that stopped partway says how far it got and claims nothing about the rest."""
    read = read_lines(text or '')
    rows = read['rows']
    findings = []

    def add(kind, sev, words, go=None, p=None):
        findings.append({'kind': kind, 'sev': sev, 'text': words, 'go': go or {'cell': plan['cell']}, 'p': p})
    for d in differences:
        add('your_file_changed', 'critical', 'Your %s %s during the run.' % (d['file'], {'changed': 'is not as it was', 'added': 'is new', 'gone': 'has gone'}.get(d['how'], d['how'])))
    for w in problems:
        add('not_put_back', 'critical', 'FOLab couldn\'t put this back yet (it tries again next time it starts): %s' % w)
    boots = [r for r in rows if r['kind'] == 'boot']
    if plan.get('run') and boots and any(b['run'] != plan['run'] for b in boots):
        add('other_run', 'critical', 'This result file comes from another run: nothing in it can be trusted for this one.')
        rows = []
    cal = _calibrate(rows, plan)
    latest = {}
    for r in rows:
        latest[(r['kind'], r.get('id'))] = r                # (a step tried twice: the last answer)
    by_id = lambda kind, i: latest.get((kind, float(i)))
    done = {'points': 0, 'things': 0, 'actors': 0, 'doors': 0, 'walks': 0}
    own = 0
    for pt in plan['points']:
        r = by_id('stand', pt['id'])
        if r:
            done['points'] += 1
            _judge_stand(plan, pt, r, cal['ok'], add)
    for t in plan['things']:
        r = by_id('thing', t['id'])
        if r:
            done['things'] += 1
            own += _judge_thing(plan, t, r, cal['ok'], add) == 'own'
    for a in plan['actors']:
        r = by_id('actor', a['id'])
        if r:
            done['actors'] += 1
            _judge_actor(plan, a, r, add)
    for d in plan['doors']:
        r = by_id('door', d['id'])
        if r:
            done['doors'] += 1
            _judge_door(plan, d, r, by_id('land', d['id']), add)
    for w in plan['walks']:
        r = by_id('npc', w['id'])
        if r:
            done['walks'] += 1
            if r['dist'] >= 300:
                add('no_path', 'error', 'Told to follow across the place, someone was still %.0f away after the time allowed: the navmesh doesn\'t bring them.' % r['dist'], _go(plan, w['b']), w['a'])
    for r in rows:
        if r['kind'] == 'died':
            add('player_died', 'error', 'The player died at step %.0f, god mode or no.' % r['id'])
        elif r['kind'] == 'abort':
            add('checker_gave_up', 'error', 'The checker gave up: %s.' % r['why'])
    # did it even get to the right place?
    first_at = next((r for r in rows if r['kind'] == 'at'), None)
    if first_at and not plan.get('outside') and first_at['form'].strip().upper()[-6:] != _low(plan['cell']):
        add('wrong_place', 'critical', 'The game went to %s (%s), not to this place. Nothing it measured is about this place.' % (first_at['name'] or '?', first_at['form']))
    for o in plan.get('offline', []):
        add(o['kind'], o['sev'], o['text'], o.get('go'), o.get('p'))
    finished = any(r['kind'] == 'done' for r in rows)
    totals = {k: len(plan[k]) for k in done}
    if not finished:
        short = sum(totals.values()) - sum(done.values())
        add('did_not_finish', 'critical' if not rows else 'error', G.ENDINGS.get(ending, 'The run stopped before the end (%s).' % (ending or 'no reason recorded')) +
            (' %d of %d checks weren\'t reached: this report says nothing about them.' % (short, sum(totals.values()))))
    if rows and not cal['ok']:
        add('rays_not_trusted', 'warn', 'Rays were left out of this report: %s So boxed-in and floating weren\'t judged.' % cal['why'])
    if read['bad']:
        add('unreadable_lines', 'info', 'Lines in the result file that couldn\'t be read: %d.' % len(read['bad']))
    if own:
        add('thing_own_ray', 'info', '%d things stopped the ray themselves, so what\'s under them wasn\'t judged.' % own)
    # (within a severity: the user's own files, then that the run stopped, then what it found)
    first = {'your_file_changed': 0, 'not_put_back': 0, 'did_not_finish': 1}
    findings.sort(key=lambda f: (SEVERITIES.index(f['sev']), first.get(f['kind'], 2)))
    bad = [f for f in findings if f['sev'] in ('critical', 'error')]
    verdict = 'never started' if not rows else 'incomplete' if not finished else 'problems' if bad else 'works'
    words = {'never started': 'The game never started checking.', 'incomplete': 'The run stopped before the end: this is only part of an answer.',
             'problems': 'It ran to the end and found problems.', 'works': 'It ran to the end and nothing serious turned up.'}[verdict]
    kinds = {}
    for f in findings:
        kinds[f['kind']] = kinds.get(f['kind'], 0) + 1
    return {'run': plan.get('run'), 'cell': plan['cell'], 'name': plan.get('name') or plan.get('edid'), 'verdict': verdict, 'said': words, 'ending': ending,
            'ending_said': G.ENDINGS.get(ending, ending or ''), 'finished': finished, 'done': done, 'totals': totals, 'rays': cal, 'findings': findings, 'kinds': kinds,
            'seconds': seconds, 'advice': _advice(rows, 'finished' if finished else ending), 'differences': list(differences), 'last_line': _last(rows)}


def _last(rows):
    for r in reversed(rows):
        if r['kind'] != 'beat':
            return {k: v for k, v in r.items()}
    return None


# ---------- the run ----------

def game_settings():
    """What the INIs say for a run: saves apart, no autosaves, windowed, runs in the background, doesn't hold the mouse
    or keyboard, quiet, straight to the main menu."""
    return {('General', 'sLocalSavePath'): G.TEST_SAVES + '\\', ('General', 'bAlwaysActive'): 1,
            ('General', 'SIntroSequence'): '', ('General', 'sMainMenuMovieIntro'): '',
            ('GamePlay', 'bSaveOnTravel'): 0, ('GamePlay', 'bSaveOnWait'): 0, ('GamePlay', 'bSaveOnRest'): 0, ('GamePlay', 'bSaveOnInteriorExteriorSwitch'): 0,
            ('Display', 'bFull Screen'): 0, ('Display', 'iSize W'): 1024, ('Display', 'iSize H'): 768,
            ('Controls', 'bBackground Mouse'): 1, ('Controls', 'bBackground Keyboard'): 1,
            ('Audio', 'fDefaultMasterVolume'): 0}


def test_name(plugin):
    return TEST_PREFIX + plugin


def needed_plugins(data_dir, plugin_path):
    """The masters the mod needs, each one's own too, in the game's order; raises Refused when one's missing."""
    files = loadorder.scan_files(data_dir)
    pf = tes4.PluginFile(plugin_path)
    try:
        want = list(pf.header['masters'])
    finally:
        pf.close()
    seen = {}
    while want:
        m = want.pop()
        if m.lower() in seen:
            continue
        row = files.get(m.lower())
        if not row or row.get('error'):
            raise G.Refused('The mod needs %s, which isn\'t in the Data folder.' % m)
        seen[m.lower()] = row
        want += row['masters']
    return [r['name'] for r in loadorder.in_game_order(seen.values())]


def preflight(paths, plan=None, running=G.game_pids):
    """What stands in the way, read only: [{'ok', 'text'}]. Everything must be ok but the notes ('note': True)."""
    rows = []

    def row(ok, text, note=False):
        rows.append({'ok': bool(ok), 'text': text, 'note': note})
    gd_dir = paths.game_dir
    row(not running(), 'The game isn\'t running.' if not running() else 'The game is running: close it first.')
    row(os.path.isfile(os.path.join(gd_dir, 'nvse_loader.exe')), 'xNVSE\'s loader is beside the game.')
    row(os.path.isfile(os.path.join(gd_dir, 'nvse_1_4.dll')), 'xNVSE is in.')
    jip = os.path.join(paths.data_dir, 'NVSE', 'plugins', 'jip_nvse.dll')
    row(os.path.isfile(jip), 'JIP LN NVSE is in (the checker runs through it).')
    row(any(os.path.isfile(os.path.join(paths.ini_dir, f)) for f in G.INI_FILES), 'The game\'s settings files are there.')
    row(os.path.isdir(os.path.dirname(paths.plugins_txt)), 'The game\'s plugins.txt folder is there.')
    row(not os.path.exists(G.journal_path(paths.work)), 'No earlier run is waiting to be put back.')
    if os.path.isfile(jip) and os.path.isfile(os.path.join(gd_dir, 'nvse_1_4.dll')):
        trouble = C.recheck(gd_dir)
        row(not trouble, 'Every command the checker uses is in your xNVSE and JIP.' if not trouble else 'Commands not as expected: ' + '; '.join(trouble[:3]))
    if plan is not None:
        row(plan.get('go'), 'The game can be sent to this place.' if plan.get('go') else 'The place has no editor ID: the game can\'t be sent there.')
        row(plan['points'] or plan['doors'] or plan['things'], 'There\'s something to check here.')
    runner = os.path.join(paths.data_dir, 'NVSE', 'plugins', 'scripts')
    others = [f for f in (os.listdir(runner) if os.path.isdir(runner) else []) if f.lower().endswith('.txt') and f.lower() != 'gr_folab_load.txt']
    if others:
        row(True, 'Other mods\' text scripts will still run (%s): only plugins can be switched off.' % ', '.join(others[:5]), note=True)
    dlls = [f for f in (os.listdir(os.path.dirname(jip)) if os.path.isdir(os.path.dirname(jip)) else []) if f.lower().endswith('.dll')]
    row(True, 'xNVSE will load these %d plugins as always: %s.' % (len(dlls), ', '.join(dlls[:8])), note=True)
    return rows


def prepare(plan, plugin_path, assets, paths, session, when=None):
    """Everything into place, each change in the journal first. Returns where the result file will be."""
    when = when or time.time()
    data = paths.data_dir
    masters = needed_plugins(data, plugin_path)
    copy = test_name(os.path.basename(plugin_path))
    plan_lines = [[copy if x == '@mod' else x for x in s] for s in plan['steps']]
    for rel, text in C.game_files(plan_lines, {1: tuple(plan['go'])}, *(plan.get('walker') or (('FalloutNV.esm', '000000'), ('FalloutNV.esm', '000000'))), plan['run']).items():
        session.put_file(text.encode('cp1252', 'replace'), os.path.join(data, rel))
    session.put_file(plugin_path, os.path.join(data, copy), when=when)
    session.put_file(C.checker_plugin(), os.path.join(data, C.CHECKER_PLUGIN), when=when + 2)
    if assets and os.path.isdir(assets):
        for top, _dirs, names in os.walk(assets):
            for n in names:
                p = os.path.join(top, n)
                session.put_file(p, os.path.join(data, os.path.relpath(p, assets)))
    mine = os.path.join(data, 'NVSE', 'plugins', 'scripts', 'gr_folab_load.txt')    # (Play here's: it'd load a save)
    if os.path.exists(mine):
        session.note_file(mine)
        os.remove(mine)
    folder = os.path.join(data, C.FOLDER)
    for f in (C.RESULT_FILE, C.CONSOLE_FILE, 'went.txt'):
        session.note_file(os.path.join(folder, f))
    session.make_folder(folder)
    session.make_folder(os.path.join(paths.ini_dir, G.TEST_SAVES))
    session.set_plugins(masters + [copy, C.CHECKER_PLUGIN])
    session.set_ini(game_settings())
    return os.path.join(folder, C.RESULT_FILE)


def _read_text(path):
    try:
        with open(path, encoding='cp1252', errors='replace', newline='') as f:
            return f.read()
    except OSError:
        return ''


LOGS = ['jip_ln_nvse.log', 'nvse.log', 'falloutnv_error.log', 'falloutnv_havok.log']


def _collect(paths, run_dir):
    """The run's own files and the game's logs to the run's folder, before they're taken away."""
    folder = os.path.join(paths.data_dir, C.FOLDER)
    for f in (C.RESULT_FILE, C.CONSOLE_FILE):
        p = os.path.join(folder, f)
        if os.path.isfile(p):
            shutil.copy2(p, os.path.join(run_dir, f))
    for f in LOGS:
        p = os.path.join(paths.game_dir, f)
        if os.path.isfile(p):
            try:
                shutil.copy2(p, os.path.join(run_dir, 'game ' + f))
            except OSError:
                pass


def _finish(plan, paths, run_dir, ending, restored, seconds):
    text = _read_text(os.path.join(run_dir, C.RESULT_FILE))
    rep = make_report(plan, text, ending, restored.get('differences', ()), restored.get('problems', ()), seconds)
    rep['restored'] = restored
    with open(os.path.join(run_dir, 'report.json'), 'w', encoding='utf-8') as f:
        json.dump(rep, f, indent=1)
    return rep


def run_test(plan, plugin_path, assets, paths, run_dir, launcher, limits=None, running=G.game_pids, input_grabbed=None, stop_asked=None, on_state=None, alive=None):
    """One whole run. launcher(paths) starts the game and returns something with pid, alive(), stop(). Everything is put
    back in the finally, whatever happened. Returns the report. Refuses (G.Refused) before changing anything if it can't go.
    alive: is that process still going (for a run left over from before; tests give their own)."""
    say = on_state or (lambda s: None)
    os.makedirs(run_dir, exist_ok=True)
    if running():
        raise G.Refused('The game is running: close it first. Nothing was changed.')
    was = recover_run(paths.work, alive=alive)
    if was.get('state') == 'game still running':
        raise G.Refused('The game from an earlier test run is still running.')
    if not plan.get('go'):
        raise G.Refused('The game can\'t be sent to this place: it has no editor ID.')
    needed_plugins(paths.data_dir, plugin_path)
    saves = paths.saves()
    before = G.fingerprint(paths)
    limits = limits or limits_for(plan)
    with open(os.path.join(run_dir, 'plan.json'), 'w', encoding='utf-8') as f:
        json.dump(plan, f, indent=1)
    session = G.Session.begin(paths, plan['run'], before, note=run_dir)
    start, ending = time.time(), 'failed to start'
    proc = None
    try:
        say('preparing')
        result = prepare(plan, plugin_path, assets, paths, session)

        def live():
            d = G.differences(before, G.fingerprint(paths, full=False, saves_dir=saves), only=['saves/'])
            if d:
                return 'your saves changed'
            if input_grabbed and input_grabbed():
                return 'mouse taken'
            return None
        say('starting the game')
        proc = launcher(paths)
        session.set_pid(proc.pid)
        say('running')
        ending = G.supervise(proc, result, limits, has_finished, live=live, stop_asked=stop_asked)
    finally:
        say('putting everything back')
        if proc is not None and proc.alive():
            proc.stop()
        _collect(paths, run_dir)
        restored = session.restore()
    say('done')
    return _finish(plan, paths, run_dir, ending, restored, round(time.time() - start))


def recover_run(work, alive=None):
    """A run that was cut off: its results saved, everything put back, and a report written from what it got."""
    if not os.path.exists(G.journal_path(work)):
        return {'state': 'clean'}
    s = G.Session.load(work)
    run_dir = s.j.get('note')
    alive = alive or (lambda pid: pid in G.game_pids())
    if s.j.get('pid') and alive(s.j['pid']):
        return {'state': 'game still running', 'pid': s.j['pid'], 'run': s.j['run']}
    if run_dir and os.path.isdir(run_dir):
        _collect(s.paths, run_dir)
    restored = G.recover(work, alive=lambda pid: False)
    if run_dir and os.path.isfile(os.path.join(run_dir, 'plan.json')):
        with open(os.path.join(run_dir, 'plan.json'), encoding='utf-8') as f:
            plan = json.load(f)
        _finish(plan, s.paths, run_dir, 'cut off', restored, None)
    return dict(restored, run=s.j['run'], run_dir=run_dir)


# ---------- the real start: locked ----------

class Locked(Exception):
    """The real game was asked for without what it takes."""


class RealGame:
    """The game this run started, by its process number. Only ever that one."""

    def __init__(self, pid):
        self.pid = pid

    def alive(self):
        return self.pid in G.game_pids()

    def stop(self):
        if self.alive():
            G.stop_pid(self.pid)


def check_unlocked(confirmation):
    """Before anything is touched: a run's preparing writes into the real Data folder, so the lock can't wait for the launch."""
    if confirmation != CONFIRM:
        raise Locked('The game starts only when the page says "%s".' % CONFIRM)
    if os.environ.get('FOLAB_NV_INI'):
        raise Locked('This FOLab is pointed at test settings: it won\'t touch the real game.')


def launch_real(paths, confirmation):
    """THE ONE PLACE FOLAB STARTS THE GAME FOR A TEST. It needs the words the page asks the user to type, and it refuses when
    FOLAB_NV_INI is set, which every test and test server does. Through xNVSE's loader, as Play does; never takes the
    focus or sends keys. Not run yet: see docs/game-test-first-run.md."""
    check_unlocked(confirmation)
    loader = os.path.join(paths.game_dir, 'nvse_loader.exe')
    if not os.path.isfile(loader):
        raise Locked('xNVSE\'s loader isn\'t beside the game.')
    info = subprocess.STARTUPINFO()
    info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    info.wShowWindow = 4            # (SW_SHOWNOACTIVATE: asks the game not to come to the front)
    subprocess.Popen([loader], cwd=paths.game_dir, startupinfo=info, close_fds=True,
                     creationflags=getattr(subprocess, 'DETACHED_PROCESS', 0) | getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0))
    end = time.time() + 90
    while time.time() < end:
        pids = G.game_pids()
        if pids:
            return RealGame(pids[0])
        time.sleep(1)
    raise Locked('The game didn\'t start within 90 seconds.')


# ---------- the page ----------

def work_dir():
    return os.path.join(project.HOME, 'gametest')


def runs_dir():
    return os.path.join(work_dir(), 'runs')


def real_paths(data_dir):
    import gameini
    import install
    return G.Paths(data_dir, gameini.folder(), install.plugins_txt(), work_dir())


def new_run_id():
    return time.strftime('%Y-%m-%d %H%M%S')


_state = {'thread': None, 'state': 'idle', 'run': None, 'stop': False, 'error': None, 'recovered': None}


def on_start():
    """The next start after a crash: called once as FOLab comes up, before anything else."""
    try:
        _state['recovered'] = recover_run(work_dir())
    except (OSError, ValueError) as e:
        _state['recovered'] = {'state': 'could not restore', 'problems': [str(e)]}


def _places(S):
    out = []
    keys = list(S.PR.cells)
    keys += [k for k, r in S.PR.records.items() if r.get('type') == 'CELL' and k not in keys]
    for k in keys:
        if not k.startswith('+') and S.GD.from_key(k) in S.GD.ext_cells:
            grid = S.GD.cell_grid(S.GD.from_key(k)) or (0, 0)
            out.append({'key': k, 'name': '%s %d, %d' % (S.GD.edid(S.GD.ext_cells[S.GD.from_key(k)]), grid[0], grid[1])})
        else:
            e, n = S.place_name(k)
            out.append({'key': k, 'name': n or e or k})
    return sorted(out, key=lambda p: p['name'].lower())


def list_runs():
    d = runs_dir()
    out = []
    for name in sorted(os.listdir(d), reverse=True)[:30] if os.path.isdir(d) else []:
        p = os.path.join(d, name, 'report.json')
        if os.path.isfile(p):
            with open(p, encoding='utf-8') as f:
                r = json.load(f)
            out.append({'run': name, 'name': r.get('name'), 'verdict': r.get('verdict'), 'counts': r.get('kinds')})
    return out


def _summary(plan):
    return {k: plan[k] for k in ('cell', 'edid', 'name', 'mesh', 'notes', 'offline', 'estimate', 'outside')} | \
           {'counts': {k: len(plan[k]) for k in ('points', 'doors', 'things', 'actors', 'walks')}, 'steps': len(plan['steps'])}


def get(name, q, S):
    if name == 'status':
        rec = recover_run(work_dir()) if _state['thread'] is None or not _state['thread'].is_alive() else {'state': 'running'}
        if _state['recovered'] and _state['recovered'].get('state') != 'clean':
            rec = dict(_state['recovered'], earlier=True)
        return {'state': _state['state'], 'run': _state['run'], 'error': _state['error'], 'running': bool(_state['thread'] and _state['thread'].is_alive()),
                'recovery': rec, 'confirm': CONFIRM, 'runs': list_runs(), 'places': _places(S) if S.PR else [], 'mod': S.PR.name if S.PR else None}
    if not S.PR:
        raise ValueError('Open or start a mod first.')
    if name == 'plan':
        with S._lock:
            plan = make_plan(S.GD, S.PR, q['cell'])
        return {'plan': _summary(plan), 'preflight': preflight(real_paths(S.GD.data_dir), plan)}
    if name == 'report':
        p = os.path.join(runs_dir(), os.path.basename(q['run']), 'report.json')
        with open(p, encoding='utf-8') as f:
            return json.load(f)
    raise FileNotFoundError(name)


def _thread_run(S, plan, plugin, assets, paths, run_dir, confirmation):
    try:
        _state['error'] = None
        run_test(plan, plugin, assets, paths, run_dir, lambda p: launch_real(p, confirmation), input_grabbed=G.cursor_clipped,
                 stop_asked=lambda: _state['stop'], on_state=lambda s: _state.__setitem__('state', s))
    except (G.Refused, Locked, OSError, ValueError) as e:
        _state['error'] = str(e)
    finally:
        _state['state'] = 'idle'


def post(name, body, S):
    if name == 'stop':
        _state['stop'] = True
        return {'ok': True}
    if name == 'dismiss':
        _state['recovered'] = None
        return {'ok': True}
    if not S.PR:
        raise ValueError('Open or start a mod first.')
    if name == 'read':                  # (the report from a result file by hand: a run's, or one made to test with)
        with S._lock:
            plan = make_plan(S.GD, S.PR, body['cell'], run='')
        return make_report(plan, body.get('text', ''), body.get('ending'))
    if name == 'start':
        try:
            check_unlocked(body.get('confirmation'))
        except Locked as e:
            raise ValueError(str(e))
        if _state['thread'] and _state['thread'].is_alive():
            raise ValueError('A test run is going already.')
        run = new_run_id()
        run_dir = os.path.join(runs_dir(), run)
        os.makedirs(run_dir, exist_ok=True)
        with S._lock:
            plan = make_plan(S.GD, S.PR, body['cell'], run=run)
            plugin = os.path.join(run_dir, S.PR.plugin)
            espwrite.write(S.GD, S.PR, plugin)
        assets = os.path.join(project.BUILD_DIR, S.PR.plugin + ' assets')
        paths = real_paths(S.GD.data_dir)
        bad = [r['text'] for r in preflight(paths, plan) if not r['ok']]
        if bad:
            raise ValueError('Not yet: ' + bad[0])
        _state.update(stop=False, run=run, state='starting')
        t = threading.Thread(target=_thread_run, args=(S, plan, plugin, assets, paths, run_dir, body['confirmation']), daemon=True)
        _state['thread'] = t
        t.start()
        return {'run': run}
    raise FileNotFoundError(name)
