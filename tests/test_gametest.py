"""The game test harness: the plan from a real place, the checker's text, the report from hand-made result files, and the
isolation layer end to end around a fake game. Fake folders throughout: the real game, its Data, INIs and plugins.txt are only
ever read (the plan reads the game's records), and launch_real is never let through."""
import os
import sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'app'))
import json
import math
import shutil
import struct
import subprocess
import time

HOME = os.environ['FOLAB_HOME']
os.environ.setdefault('FOLAB_NV_INI', os.path.join(HOME, 'ini'))    # (launch_real refuses with this set)
REAL_LOCAL = os.environ.get('LOCALAPPDATA', '')
os.environ['LOCALAPPDATA'] = os.path.join(HOME, 'fake local')       # (never the real plugins.txt)
import espwrite
import gamedata
import gametest as T
import gametestcheck as C
import gametestguard as G
import navbuild
import plugintree
import project
import recordio
import tes4


def check(what, ok, extra=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' ' + str(extra) if extra != '' and not ok else ''))


gd = gamedata.GameData()

# ---------- a real game place, as a mod changes it ----------
by_tag = lambda tag, test=lambda f: True: next(f for f, (i, r) in gd.forms.items() if r.tag == tag and f >> 24 == 0 and test(f))
mesh_cell = None
for c in sorted(gd.interiors):
    if c >> 24:
        continue
    if not navbuild.game_entries(gd, gd.key(c)) or not gd.edid(c):
        continue
    refs = gd.refs(c)
    doors = [r for r in refs if r['leads'] and r['pos']]
    if doors and 15 < len(refs) < 200:
        ok = False
        for d in doors:
            t = T.refinfo.door_target(gd, d['ref'])
            ok = ok or bool(t and t['cell'])
        if ok:
            mesh_cell = c
            break
check('a small game place with a navmesh and a door to test on', mesh_cell is not None)
ckey = gd.key(mesh_cell)
pr = project.Project.create('GT Test')
misc = gd.key(by_tag('MISC', lambda f: bool(gd.fields(f).get('OBND'))))
npc = gd.key(by_tag('NPC_'))
stat = gd.key(by_tag('STAT'))
some = next(r for r in gd.refs(mesh_cell) if r['pos'])
[thing_key] = pr.apply('t', [{'op': 'add', 'cell': ckey, 'base': misc, 'p': [some['pos'][0], some['pos'][1], some['pos'][2] + 40, 0, 0, 0]}])
[npc_key] = pr.apply('n', [{'op': 'add', 'cell': ckey, 'base': npc, 'p': [some['pos'][0] + 50, some['pos'][1], some['pos'][2], 0, 0, 0]}])
[stat_key] = pr.apply('s', [{'op': 'add', 'cell': ckey, 'base': stat, 'p': [some['pos'][0], some['pos'][1], some['pos'][2], 0, 0, 0]}])
plan = T.make_plan(gd, pr, ckey, run='RUN1')
print('  place', plan['edid'], {k: len(plan[k]) for k in ('points', 'doors', 'things', 'actors', 'walks')}, plan['mesh'], plan['estimate'], 's')

check('floor points come from the game\'s navmesh', plan['mesh']['source'] == 'the game\'s navmesh' and len(plan['points']) > 3)
meshes = [navbuild.game_copy(gd, e) for e in navbuild.game_entries(gd, ckey)]
xs = [v[0] for m in meshes for v in m['verts']]
check('each point is on the mesh\'s floor plan', all(min(xs) <= p['p'][0] <= max(xs) for p in plan['points']))
squares = {(int(p['p'][0] // 256), int(p['p'][1] // 256), round(p['p'][2] / 128)) for p in plan['points']}
check('one point per square per level', len(squares) == len(plan['points']))
check('its doors are found, with where they lead', plan['doors'] and all(d['to'] and d['to']['p'] for d in plan['doors']))
check('the mod\'s loose thing should rest on something', [t['ref'] for t in plan['things']] == [thing_key] and plan['things'][0]['mod'] == '@mod')
check('the mod\'s thing is found by its own number', plan['things'][0]['hex'] == thing_key[1:].zfill(6))
check('its base\'s bottom is known', isinstance(plan['things'][0]['bottom'], float))
check('the placed character is checked', [a['ref'] for a in plan['actors']] == [npc_key])
check('a static isn\'t expected to rest', stat_key not in [t['ref'] for t in plan['things']])
check('game things not changed aren\'t judged', len(plan['things']) == 1)
check('an NPC and follow package of the game\'s are found', plan['walker'] and plan['walker'][0][0] == 'FalloutNV.esm')
if plan['walks']:
    a, b = plan['walks'][0]['a'], plan['walks'][0]['b']
    check('walks are between far points on one floor', abs(a[2] - b[2]) < 128 and (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 > 512 ** 2)
kinds = [s[0] for s in plan['steps']]
check('the plan starts by going there', kinds[0] == C.GO and kinds[1] == C.CAL)
check('and ends with the finished line', kinds[-1] == C.DONE)
at_door = [n for n, k in enumerate(kinds) if k == C.DOOR]
check('after each door, a way back', all(kinds[n + 1] == C.GO for n in at_door))
ids = [s[1] for s in plan['steps'] if s[0] in (C.STAND, C.THING, C.ACTOR, C.DOOR, C.NPC)]
check('every step has an ID of its own', len(ids) == len(set(ids)))

# (a door linked by the mod, in a place of the mod's own, and no navmesh)
rec = recordio.load(gd, mesh_cell)
recordio.set_field(rec, 'EDID', 'GTMyPlace', label='Editor ID')
[own] = pr.apply('p', [{'op': 'record_new', 'record': rec}])
door_base = gd.key(by_tag('DOOR'))
[piece] = pr.apply('x', [{'op': 'add', 'cell': own, 'base': gd.key(s['base']), 'p': list(s['pos']) + list(s['rot'])} for s in [r for r in gd.refs(mesh_cell) if r['pos'] and gd.forms[r['base']][1].tag == 'STAT'][:1]])
[door1] = pr.apply('d', [{'op': 'add', 'cell': own, 'base': door_base, 'p': [10, 20, 30, 0, 0, 0]}])
pr.apply('l', [{'op': 'tel', 'cell': own, 'ref': door1, 'tel': {'door': plan['doors'][0]['ref'], 'p': [1, 2, 3, 0, 0, 0]}}])
own_plan = T.make_plan(gd, pr, own, run='RUN2', walks=False)
check('a place of the mod\'s own goes by its editor ID', own_plan['go'] == ['coc', 'GTMyPlace'])
d = next(x for x in own_plan['doors'] if x['ref'] == door1)
check('a door the mod linked: its own link', d['to']['door'] == plan['doors'][0]['ref'] and d['to']['p'][:3] == [1, 2, 3] and d['to']['cell'] == ckey)
check('its handle says the mod', d['mod'] == '@mod')
pr.apply('f', [{'op': 'record', 'key': own, 'record': recordio.set_field(pr.records[own], 'EDID', '', label='Editor ID') or pr.records[own]}])
no_id = T.make_plan(gd, pr, own, run='X', walks=False)
check('no editor ID: the plan says the game can\'t go there', no_id['go'] is None and any(o['kind'] == 'no_editor_id' for o in no_id['offline']))

# (a mesh in two pieces is seen without the game)
two = {'verts': [[0, 0, 0], [100, 0, 0], [0, 100, 0], [1000, 0, 0], [1100, 0, 0], [1000, 100, 0]], 'tris': [[0, 1, 2], [3, 4, 5]]}
check('a navmesh in two pieces is two islands', len(T.islands([two])) == 2)
check('thinning keeps the count', len(T._thin(list(range(1000)), 240)) == 240)

# ---------- the checker's text ----------
cells = {1: ('coc', 'GTMyPlace')}
tick = C.tick_text(cells, ('FalloutNV.esm', '000123'), ('FalloutNV.esm', '000456'))
check('the tick has no trouble that can be seen without a game', C.check_text(tick, True) == [], C.check_text(tick, True))
check('every variable it uses is declared', C.undeclared_in(tick) == set(), C.undeclared_in(tick))
boot = C.boot_text('RUN1')
check('the first script is clean', C.check_text(boot) == [] and C.undeclared_in(boot) == set(), C.check_text(boot))
check('it starts logging the console, first thing', 'con_SCOF' in boot.split('\n')[1])
check('and writes its first words before anything can fail', boot.index('boot|gr|RUN1') < boot.index('CompileScript'))
check('the plan\'s kinds are all handled', all('fGtKind == %d' % k in tick for k in (C.GO, C.THING, C.ACTOR, C.DOOR, C.NPC, C.DONE)))
check('it uses no SendKeys or tapping of keys', not any(w in tick.lower() for w in ('tapkey', 'holdkey', 'tapcontrol', 'sendkeys')))
check('the first move happens once, whatever a reset does', 'went.txt' in tick)
check('a message box is closed, not waited on', 'if MenuMode 1001' in tick and 'CloseActiveMenu' in tick)
check('no string variable where a plain String goes', not any(c + ' $' in tick for c in ('ReadStringFromFile', 'GetFormFromMod', 'GetModIndex', 'FileExists')))
check('every local has a name of its own', all(v[1:3] == 'gt' for v in C.declared_in(tick)), sorted(C.declared_in(tick)))
check('a controller is off for the run, and never rumbles', T.game_settings().get(('Controls', 'bUse Joystick')) == 0
      and T.game_settings().get(('Controls', 'bGamePadRumble')) == 0 and T.game_settings().get(('Interface', 'bDisable360Controller')) == 1)
check('it never saves', not any(w in tick.lower() for w in ('savegame', 'con_save', 'autosave')))
files = C.game_files(plan['steps'], cells, plan['walker'][0], plan['walker'][1], 'RUN1')
check('the runner\'s scripts go where JIP looks', {'NVSE\\plugins\\scripts\\gr_folabgt.txt', 'NVSE\\plugins\\scripts\\gl_folabgt.txt', 'NVSE\\plugins\\scripts\\gn_folabgt.txt'} <= set(files))
check('the tick goes where xNVSE looks', 'NVSE\\user_defined_functions\\folabgt_tick.txt' in files)
many = [[C.STAND, n, 1234.5, -2345.5, 345.5] for n in range(1050)]
chunks = C.plan_chunks(many)
check('plan chunks: all there, each within what ReadStringFromFile reads', len(chunks) == 11 and all(len(t) < 16000 for t in chunks.values()))
check('a chunk has CHUNK lines', len(chunks['0.txt'].splitlines()) == C.CHUNK and chunks['1.txt'].splitlines()[0].split('|')[1] == '100')
bad = C.check_text('if x\r\nWriteStringToFile "p" 1 "stand|%.0f" a b\r\n')
check('a text check catches a missing endif and a wrong count', any('without endif' in b for b in bad) and any('2 values' in b for b in bad))
# against the user's own files, when they're there (only read)
game_dir = os.path.dirname(os.path.normpath(gd.data_dir))
if os.path.isfile(os.path.join(game_dir, 'nvse_1_4.dll')) and os.path.isfile(os.path.join(gd.data_dir, 'NVSE', 'plugins', 'jip_nvse.dll')):
    t = C.recheck(game_dir)
    check('every xNVSE and JIP command is in the DLLs with the parameters expected', t == [], t)
funcs = json.load(open(os.path.join(HERE, '..', 'app', 'scriptfuncs.json')))
script_names = {x['name'].lower() for x in funcs['script']} | {(x.get('short') or '').lower() for x in funcs['script']}
console_names = {x['name'].lower() for x in funcs['console']} | {(x.get('short') or '').lower() for x in funcs['console']}
check('every game command it calls is in the game\'s tables', all(n.lower() in script_names for n in C.GAME_COMMANDS), [n for n in C.GAME_COMMANDS if n.lower() not in script_names])
check('every console command too', all(n.lower() in console_names for n in C.CONSOLE_COMMANDS), [n for n in C.CONSOLE_COMMANDS if n.lower() not in console_names])

# the checker's plugin reads as a plugin
chk = os.path.join(HOME, C.CHECKER_PLUGIN)
with open(chk, 'wb') as f:
    f.write(C.checker_plugin())
pf = tes4.PluginFile(chk)
recs = list(pf.walk())
names = sorted(tes4.zstr(pf.fields(r).get('EDID', b'')) for r, _g in recs)
check('the checker\'s plugin has its globals', names == sorted(C.GLOBALS) and all(r.tag == 'GLOB' for r, _g in recs), names[:3])
check('its header counts them', pf.header['records'] == len(C.GLOBALS) and pf.header['masters'] == ['FalloutNV.esm'], pf.header)
check('form IDs are its own', all(r.formid >> 24 == 1 for r, _g in recs))
game_glob = next(f for f, (i, r) in gd.forms.items() if r.tag == 'GLOB')
one = recs[0][0]
check('a global is laid out as the game\'s are', list(pf.fields(one)) == list(gd.fields(game_glob)))
pf.close()
os.remove(chk)

# ---------- the report, from hand-made result files ----------
P = plan
pts, doors = P['points'], P['doors']
x0, y0, z0 = pts[0]['p']


def good_stand(pt, **over):
    x, y, z = pt['p']
    f = dict(x1=x, y1=y, z1=z, x2=x, y2=y, z2=z, air=0, water=0, d=[300] * 8)
    f.update(over)
    return 'stand|%d|%.1f|%.1f|%.1f|%.1f|%.1f|%.1f|%d|%d|%s' % (pt['id'], f['x1'], f['y1'], f['z1'], f['x2'], f['y2'], f['z2'], f['air'], f['water'], '|'.join(str(v) for v in f['d']))


home_low = T._low(ckey)
HEAD = ['boot|gr|RUN1', 'go|1', 'at|1|%s|The Place|%.1f|%.1f|%.1f' % ('01' + home_low, x0, y0, z0),
        'cal|99|%.1f|%.1f|%.1f|%.1f|%.1f|%.1f|%.1f|%.1f|%.1f' % (x0, y0, z0, x0, y0, z0, z0 + 200, x0, y0 + 300)]


def full(over=None, tail=True):
    """A whole good run; over: {id: replacement line}."""
    over = over or {}
    L = list(HEAD)
    for pt in pts:
        L.append(over.get(pt['id']) or good_stand(pt))
    for t in P['things']:
        L.append(over.get(t['id']) or 'thing|%d|1|%.1f|%.1f|%.1f|0|%.1f|00000000' % (t['id'], *t['p'], t['p'][2] + t['bottom']))
    for a in P['actors']:
        L.append(over.get(a['id']) or 'actor|%d|1|%.1f|%.1f|%.1f|0|0|0' % (a['id'], *a['p']))
    for w in P['walks']:
        L.append(over.get(w['id']) or 'npc|%d|100.0|120' % w['id'])
    for d in doors:
        low = T._low(d['to']['cell'])
        L.append(over.get(d['id']) or 'door|%d|1|1|0|01%s|Over There' % (d['id'], low))
        q = d['to']['p']
        L.append(over.get(('land', d['id'])) or 'land|%d|01%s|Over There|%.1f|%.1f|%.1f|%.1f|0' % (d['id'], low, q[0], q[1], q[2], q[2]))
    if tail:
        L.append('done|%d' % len(L))
    return '\n'.join(L)


def kinds_of(rep):
    return rep['kinds']


rep = T.make_report(P, full(), 'finished')
check('a whole good run: it works', rep['verdict'] == 'works', rep['findings'][:3])
check('everything is counted as reached', rep['done'] == rep['totals'], (rep['done'], rep['totals']))
check('rays are trusted after a good calibration', rep['rays']['ok'], rep['rays'])
check('no advice is needed', rep['advice'] is None)
rep = T.make_report(P, full().replace('\n', '\r\n'), 'finished')
check('line endings don\'t matter', rep['verdict'] == 'works')

r = T.make_report(P, full({pts[0]['id']: good_stand(pts[0], z1=z0 - 300, z2=z0 - 700, air=1)}), 'finished')
check('falling through the floor is an error', r['kinds'].get('fell_through') == 1 and r['verdict'] == 'problems', r['kinds'])
r = T.make_report(P, full({pts[0]['id']: good_stand(pts[0], z1=z0 - 100, z2=z0 - 100)}), 'finished')
check('a floor lower than the navmesh says is a warning', r['kinds'].get('dropped') == 1 and r['verdict'] == 'works', r['kinds'])
r = T.make_report(P, full({pts[0]['id']: good_stand(pts[0], x2=x0 + 90, y2=y0)}), 'finished')
check('pushed sideways is found', r['kinds'].get('pushed_off') == 1)
r = T.make_report(P, full({pts[0]['id']: good_stand(pts[0], d=[20] * 8)}), 'finished')
check('boxed in is an error', r['kinds'].get('boxed_in') == 1 and r['verdict'] == 'problems')
r = T.make_report(P, full({pts[0]['id']: good_stand(pts[0], d=[20, 20, 20, 20, 20, 300, 300, 300])}), 'finished')
check('tight isn\'t boxed in', 'boxed_in' not in r['kinds'] and r['kinds'].get('tight') == 1)
r = T.make_report(P, full({pts[0]['id']: good_stand(pts[0], d=[-1] * 8)}), 'finished')
check('rays with no answer aren\'t walls', 'boxed_in' not in r['kinds'])

t0 = P['things'][0]
line = lambda z, hit, form='00000000': 'thing|%d|1|%.1f|%.1f|%.1f|0|%.1f|%s' % (t0['id'], t0['p'][0], t0['p'][1], z, hit, form)
base = t0['p'][2] + t0['bottom']
r = T.make_report(P, full({t0['id']: line(t0['p'][2], base - 100)}), 'finished')
check('a thing over nothing near floats', r['kinds'].get('thing_floating') == 1, r['kinds'])
r = T.make_report(P, full({t0['id']: line(t0['p'][2], base + 100)}), 'finished')
check('a thing under something is buried', r['kinds'].get('thing_buried') == 1, r['kinds'])
r = T.make_report(P, full({t0['id']: line(t0['p'][2] - 100, base - 100)}), 'finished')
check('a thing physics moved is found', r['kinds'].get('thing_moved') == 1, r['kinds'])
r = T.make_report(P, full({t0['id']: line(t0['p'][2], base - 100, '01' + t0['hex'])}), 'finished')
check('a ray that stops on the thing itself judges nothing', 'thing_floating' not in r['kinds'] and r['kinds'].get('thing_own_ray') == 1, r['kinds'])
r = T.make_report(P, full({t0['id']: 'thing|%d|0|0|0|0|0|0|00000000' % t0['id']}), 'finished')
check('a thing the game hasn\'t got is an error', r['kinds'].get('thing_missing') == 1)
a0 = P['actors'][0]
r = T.make_report(P, full({a0['id']: 'actor|%d|1|%.1f|%.1f|%.1f|1|0|0' % (a0['id'], a0['p'][0], a0['p'][1], a0['p'][2] - 500)}), 'finished')
check('a character through the floor is an error', r['kinds'].get('actor_fell') == 1)
# walks: this place plans none of its own, so one is lent it
P_walk = json.loads(json.dumps(P))
P_walk['walks'] = [{'id': 9001, 'a': [x0, y0, z0], 'b': [x0 + 900, y0, z0], 'ticks': 300}]
P_walk['keeps'] = 512.0


def walked(dist):
    return T.make_report(P_walk, '\n'.join(full().split('\n')[:-1] + ['npc|9001|%.1f|0' % dist, 'done|9999']), 'finished')['kinds']


check('someone who can\'t follow is an error', walked(1500).get('no_path') == 1)
check('someone who came as near as a follower comes (360, within 512) arrived: real run, 8 Nov 2026', 'no_path' not in walked(360))
check('the follow package\'s distance is read from the game (%s)' % T._follow_keeps(gd), T._follow_keeps(gd) == 512)
near = T._far_pairs([[0, 0, 0], [600, 0, 0]], 512 + 256)
far = T._far_pairs([[0, 0, 0], [600, 0, 0], [0, 900, 0]], 512 + 256)
check('walks are only planned where arriving proves something: further apart than a follower stops short (%s, %s)' % (near, far),
      near == [] and len(far) == 1 and all(math.dist(a[:2], b[:2]) > 768 for a, b in far))
pts3 = [[0, 0, 0], [900, 0, 0], [0, 1000, 0]]
along = [[0, 5000, 1100], [5000, 0, 1500], [1100, 1500, 0]]       # (the far pair is 5,000 round by the mesh: a maze)
w3 = T._far_pairs(pts3, 768, along)
check('a walk is one the follower can finish: the straight-line farthest pair is 5,000 round by the mesh, so it is passed over (%s)' % w3,
      len(w3) == 1 and sorted(map(tuple, w3[0])) == [(0, 1000, 0), (900, 0, 0)])

d0 = doors[0]
low = T._low(d0['to']['cell'])
q = d0['to']['p']
r = T.make_report(P, full({d0['id']: 'door|%d|0|0|0|00000000|-' % d0['id'], ('land', d0['id']): 'beat|1'}), 'finished')
check('a door the game hasn\'t got is an error', r['kinds'].get('door_missing') == 1)
r = T.make_report(P, full({d0['id']: 'door|%d|1|1|0|00000000|' % d0['id'], ('land', d0['id']): 'beat|1'}), 'finished')
check('a door leading nowhere is an error', r['kinds'].get('door_leads_nowhere') == 1, r['kinds'])
# a door out to a world: the game names no cell for it (its far side is in the persistent cell); landing at the arrival is the proof
P_out = json.loads(json.dumps(P))
P_out['doors'][0]['to']['interior'] = False
r = T.make_report(P_out, full({d0['id']: 'door|%d|1|1|0|00000000|<NULL>' % d0['id'], ('land', d0['id']): 'land|%d|01000EA0|Outside|%.1f|%.1f|%.1f|%.1f|0' % (d0['id'], q[0], q[1], q[2], q[2])}), 'finished')
check('a door out to a world that lands at its arrival is fine, though the game names no cell', not any(k.startswith('door_') for k in r['kinds']), r['kinds'])
r = T.make_report(P_out, full({d0['id']: 'door|%d|1|1|0|00000000|<NULL>' % d0['id'], ('land', d0['id']): 'beat|1'}), 'finished')
check('one that never lands still leads nowhere', r['kinds'].get('door_leads_nowhere') == 1, r['kinds'])
r = T.make_report(P, full({d0['id']: 'door|%d|1|1|1|01%s|Over There' % (d0['id'], low), ('land', d0['id']): 'beat|1'}), 'finished')
check('a locked door is noted, not gone through', r['kinds'].get('door_locked') == 1 and 'door_not_gone_through' not in r['kinds'])
if d0['to']['interior']:
    r = T.make_report(P, full({('land', d0['id']): 'land|%d|01ABCDEF|Elsewhere|0|0|0|0|0' % d0['id']}), 'finished')
    check('landing in the wrong place is an error', r['kinds'].get('door_did_not_lead') == 1, r['kinds'])
    r = T.make_report(P, full({d0['id']: 'door|%d|1|1|0|01ABCDEF|Elsewhere' % d0['id']}), 'finished')
    check('a door the game sends elsewhere is an error', r['kinds'].get('door_wrong_place') == 1)
r = T.make_report(P, full({('land', d0['id']): 'land|%d|01%s|Over There|%.1f|%.1f|%.1f|%.1f|0' % (d0['id'], low, q[0] + 900, q[1], q[2], q[2])}), 'finished')
check('landing far from the arrival is a warning', r['kinds'].get('door_landed_away') == 1)
r = T.make_report(P, full({('land', d0['id']): 'land|%d|01%s|Over There|%.1f|%.1f|%.1f|%.1f|1' % (d0['id'], low, q[0], q[1], q[2], q[2] - 800)}), 'finished')
check('falling after a door is an error', r['kinds'].get('door_fell') == 1)

# stopped partway
cut = '\n'.join(full().split('\n')[:len(HEAD) + 3])
r = T.make_report(P, cut, 'game closed')
check('a run that stopped partway is incomplete', r['verdict'] == 'incomplete')
check('and says how far it got', r['done']['points'] == 3 and r['done']['doors'] == 0, r['done'])
check('did_not_finish is said and sorted to the top', r['findings'][0]['kind'] == 'did_not_finish' and 'crash' in r['findings'][0]['text'], r['findings'][:1])
check('it knows its last line', r['last_line']['kind'] == 'stand')
check('and what to look at', r['advice']['stage'] == 'partway' and r['advice']['doc'].endswith('#partway'))
torn = cut + '\nstand|%d|12.0|3' % pts[3]['id']
r = T.make_report(P, torn, 'game closed')
check('a line cut off halfway is noted, not believed', r['done']['points'] == 3 and r['kinds'].get('unreadable_lines') == 1)
r = T.make_report(P, '\x00\xff garbage\nmore|nonsense', 'game closed')
check('rubbish gives a report, not a crash', r['verdict'] == 'never started')
r = T.make_report(P, '', 'no first line')
check('an empty file: never started, and where to look', r['verdict'] == 'never started' and r['advice']['stage'] == 'no lines' and 'jip_ln_nvse.log' in r['advice']['text'])
check('it\'s the worst kind of not finishing', r['findings'][0]['sev'] == 'critical')
r = T.make_report(P, 'boot|gr|RUN1\nboot|gl|RUN1', 'no first line')
check('the first script but no tick: says so', r['advice']['stage'] == 'no tick')
r = T.make_report(P, 'boot|gr|RUN1\nabort|tick did not compile|0', 'game closed')
check('the checker giving up is reported', r['kinds'].get('checker_gave_up') == 1)
r = T.make_report(P, 'boot|gr|RUN1\ngo|1', 'went silent')
check('the move that never happened: says so', r['advice']['stage'] == 'no move' and r['advice']['doc'].endswith('#coc'))
r = T.make_report(P, 'boot|gr|SOMEONE ELSE\ngo|1\ndone|1', 'finished')
check('a file from another run isn\'t believed', r['kinds'].get('other_run') == 1 and not r['finished'])
r = T.make_report(P, full().replace('at|1|01' + home_low, 'at|1|01ABC123'), 'finished')
check('in the wrong place: nothing counts', r['kinds'].get('wrong_place') == 1 and r['findings'][0]['kind'] == 'wrong_place')
bad_cal = full().replace(HEAD[3], 'cal|99|%.1f|%.1f|%.1f|-99999|-99999|-99999|-99999|-99999|-99999' % (x0, y0, z0))
r = T.make_report(P, bad_cal.replace(good_stand(pts[0]), good_stand(pts[0], d=[20] * 8)), 'finished')
check('rays that mean something else: left out, and said', not r['rays']['ok'] and r['kinds'].get('rays_not_trusted') == 1 and 'boxed_in' not in r['kinds'], r['kinds'])
wrong_way = full().replace(HEAD[3], 'cal|99|%.1f|%.1f|%.1f|%.1f|%.1f|%.1f|%.1f|%.1f|%.1f' % (x0, y0, z0, x0, y0, z0 + 200, z0, x0, y0 + 300))
check('a ray "down" that goes up isn\'t trusted', not T.make_report(P, wrong_way, 'finished')['rays']['ok'])
order = T.make_report(P, full({pts[0]['id']: good_stand(pts[0], z1=z0 - 300, z2=z0 - 700), pts[1]['id']: good_stand(pts[1], water=1), pts[2]['id']: good_stand(pts[2], x2=pts[2]['p'][0] + 90)}), 'finished', [{'file': 'saves/a.fos', 'how': 'changed'}])
sevs = [T.SEVERITIES.index(f['sev']) for f in order['findings']]
check('worst first', sevs == sorted(sevs) and order['findings'][0]['kind'] == 'your_file_changed', [f['kind'] for f in order['findings']])
check('a place to go on each finding', all(f['go'].get('cell') for f in order['findings']))
r = T.make_report(P, '', None, (), ['Fallout.ini: held open'])
check('what couldn\'t be put back is at the top', r['findings'][0]['kind'] == 'not_put_back')
line1, tail = T.read_lines('done|5')['rows'][0], None
check('the finished line reads', line1 == {'kind': 'done', 'n': 5.0})
for kind, fields in C.RESULTS.items():
    made = '|'.join([kind] + ['1' for _ in fields])
    check('line kind %s round trips' % kind, T.read_lines(made)['rows'] and not T.read_lines(made)['bad'])


# ---------- isolation, end to end, round a fake game ----------
def make_world(name, mods=True):
    """A fake game: Data with small plugins, INIs and saves, plugins.txt with many mods on."""
    top = os.path.join(HOME, name)
    data = os.path.join(top, 'game', 'Data')
    ini = os.path.join(top, 'My Games')
    saves = os.path.join(ini, 'Saves')
    local = os.path.join(top, 'local', 'FalloutNV')
    for d in (data, saves, local, os.path.join(data, 'NVSE', 'plugins', 'scripts')):
        os.makedirs(d, exist_ok=True)

    def plugin(fn, masters, esm=False, when=1200000000):
        head = espwrite.join([('HEDR', struct.pack('<fiI', 1.34, 0, 0x800)), ('CNAM', b'x\0')] + [x for m in masters for x in (('MAST', m.encode() + b'\0'), ('DATA', b'\0' * 8))])
        tree = plugintree.Plugin.empty(head, 1 if esm else 0)
        p = os.path.join(data, fn)
        with open(p, 'wb') as f:
            f.write(tree.bytes())
        os.utime(p, (when, when))
    plugin('FalloutNV.esm', [], True)
    plugin('DeadMoney.esm', ['FalloutNV.esm'], True, 1200000100)
    plugin('Lib.esm', ['FalloutNV.esm'], True, 1200000200)
    plugin('Mission Mojave.esp', ['FalloutNV.esm'], False, 1300000000)
    plugin('IWS.esp', ['FalloutNV.esm'], False, 1300000100)
    # the mod's plugin, built elsewhere
    src = os.path.join(top, 'build')
    os.makedirs(src, exist_ok=True)
    data2 = data
    head = espwrite.join([('HEDR', struct.pack('<fiI', 1.34, 0, 0x800)), ('CNAM', b'x\0')] + [x for m in ('FalloutNV.esm', 'Lib.esm') for x in (('MAST', m.encode() + b'\0'), ('DATA', b'\0' * 8))])
    with open(os.path.join(src, 'GT Test.esp'), 'wb') as f:
        f.write(plugintree.Plugin.empty(head, 0).bytes())
    # the user's own things
    open(os.path.join(saves, 'Save 1 - Courier.fos'), 'wb').write(b'a save' * 100)
    open(os.path.join(saves, 'Save 1 - Courier.nvse'), 'wb').write(b'cosave')
    with open(os.path.join(ini, 'Fallout.ini'), 'w', encoding='cp1252', newline='\r\n') as f:
        f.write('[General]\nsLocalSavePath=Saves\\\nbAlwaysActive=0\nSIntroSequence=Fallout INTRO Vsk.bik\n[Display]\nbFull Screen=1\niSize W=2560\niSize H=1440\n[GamePlay]\nbSaveOnTravel=1\nbSaveOnWait=1\nbSaveOnRest=1\nbSaveOnInteriorExteriorSwitch=1\n[Controls]\nbBackground Mouse=0\n')
    with open(os.path.join(ini, 'FalloutPrefs.ini'), 'w', encoding='cp1252', newline='\r\n') as f:
        f.write('[Display]\niSize W=1920\niSize H=1080\n[Audio]\nfDefaultMasterVolume=0.8\n; a comment of the user\'s\n')
    os.chmod(os.path.join(ini, 'Fallout.ini'), 0o444)      # (kept read-only by the user)
    txt = os.path.join(local, 'plugins.txt')
    with open(txt, 'w', encoding='cp1252', newline='\r\n') as f:
        f.write('# my list\nFalloutNV.esm\nDeadMoney.esm\nMission Mojave.esp\nIWS.esp\n')
    # Play here's own autoload and something of another mod
    open(os.path.join(data, 'NVSE', 'plugins', 'scripts', 'gr_folab_load.txt'), 'w').write('LoadGame "Save 1"\n')
    open(os.path.join(data, 'NVSE', 'plugins', 'scripts', 'gr_other_mod.txt'), 'w').write('; another mod\n')
    # an NVSE-ish folder, so preflight can pass or be told
    paths = G.Paths(data, ini, txt, os.path.join(top, 'work'))
    return top, paths, os.path.join(src, 'GT Test.esp'), saves, data2


def snapshot(paths):
    out = {}
    for root in (paths.data_dir, paths.ini_dir, os.path.dirname(paths.plugins_txt)):
        for top, dirs, names in os.walk(root):
            for n in names:
                p = os.path.join(top, n)
                st = os.stat(p)
                with open(p, 'rb') as f:
                    out[p] = (f.read(), st.st_mtime_ns, st.st_mode)
            for n in dirs:
                out[os.path.join(top, n) + os.sep] = None
    return out


def same(a, b):
    return [k for k in sorted(set(a) | set(b)) if a.get(k, 0) != b.get(k, 0)]


class FakeProc:
    def __init__(self, popen):
        self.p, self.pid = popen, popen.pid
        self.stopped = False

    def alive(self):
        return self.p.poll() is None

    def stop(self):
        self.stopped = True
        self.p.kill()
        self.p.wait()


def fake_launcher(saves, mode, at=3, env=None, made=None):
    def start(paths):
        e = dict(os.environ, FAKE_CELL_FORM='01' + T._low(ckey), FAKE_DOOR_FORM='01' + T._low(plan['doors'][0]['to']['cell']),
                 FAKE_ARRIVE=json.dumps({str(d['id']): d['to']['p'][:3] for d in plan['doors']}), **(env or {}))
        pop = subprocess.Popen([sys.executable, os.path.join(HERE, 'fake_game.py'), paths.data_dir, paths.ini_dir, paths.plugins_txt, saves, mode, str(at)], env=e)
        proc = FakeProc(pop)
        if made is not None:
            made.append(proc)
        return proc
    return start


FAST = G.Limits(cap=25, first_line=4, silent=2, finish=2, poll=0.05, live_check=0.1)
NEVER = lambda: []
plan['walker'] = plan['walker'] or [('FalloutNV.esm', '000001'), ('FalloutNV.esm', '000002')]

top, paths, built, saves, data = make_world('w1')
snap = snapshot(paths)
run_dir = os.path.join(top, 'run')
made = []
states = []
rep = T.run_test(plan, built, None, paths, run_dir, fake_launcher(saves, 'ok', made=made), limits=FAST, running=NEVER, on_state=states.append)
print('  fake run:', rep['verdict'], rep['ending'], rep['done'], rep['kinds'], rep['seconds'])
check('the fake game ran the whole plan', rep['finished'] and rep['done'] == rep['totals'], rep['done'])
check('the report says it works', rep['verdict'] == 'works', rep['findings'][:3])
check('it ended by itself', rep['ending'] == 'finished')
check('the process wasn\'t stopped: it quit', not made[0].stopped)
diff = same(snap, snapshot(paths))
check('everything is back, byte for byte, dates and read-only too', diff == [], diff[:6])
check('the user\'s files all report no difference', rep['differences'] == [], rep['differences'])
check('the Data folder holds nothing of the run', not os.path.exists(os.path.join(data, C.FOLDER)) and not os.path.exists(os.path.join(data, C.CHECKER_PLUGIN)) and not os.path.exists(os.path.join(data, T.test_name('GT Test.esp'))))
check('the test saves folder is gone', not os.path.exists(os.path.join(paths.ini_dir, G.TEST_SAVES)))
check('the journal is gone', not os.path.exists(G.journal_path(paths.work)))
check('the result file and report are kept with the run', os.path.isfile(os.path.join(run_dir, C.RESULT_FILE)) and os.path.isfile(os.path.join(run_dir, 'report.json')) and os.path.isfile(os.path.join(run_dir, 'plan.json')))
check('states were reported', states[0] == 'preparing' and states[-1] == 'done')

saw = json.load(open(os.path.join(os.path.dirname(data), 'fake game saw.json')))
check('only the mod\'s masters, the mod and the checker were on', saw['plugins'] == ['FalloutNV.esm', 'Lib.esm', T.test_name('GT Test.esp'), C.CHECKER_PLUGIN], saw['plugins'])
check('the other mods weren\'t listed', 'IWS.esp' not in saw['plugins'] and 'Mission Mojave.esp' not in saw['plugins'])
for fn in ('Fallout.ini', 'FalloutPrefs.ini'):
    txt = saw[fn].lower()
    check(fn + ': no line says otherwise', 'isize w=2560' not in txt and 'isize w=1920' not in txt and 'bfull screen=1' not in txt)
ini = saw['Fallout.ini'].lower()
check('saves redirected', ('slocalsavepath=%s\\' % G.TEST_SAVES.lower()) in ini)
check('autosaves off', all(k + '=0' in ini for k in ('bsaveontravel', 'bsaveonwait', 'bsaveonrest', 'bsaveoninteriorexteriorswitch')))
check('windowed, running in the background, not holding the mouse', 'bfull screen=0' in ini and 'balwaysactive=1' in ini and 'bbackground mouse=1' in ini)
check('a setting neither had goes in the last', 'bbackground keyboard=1' in saw['FalloutPrefs.ini'].lower())
check('the user\'s comment stayed in the file during the run', 'a comment of the user' in saw['FalloutPrefs.ini'])
check('the runner\'s scripts and the tick were in place', 'gr_folabgt.txt' in saw['scripts'] and saw['tick'] and saw['checker'])
check('Play here\'s autoload was set aside', 'gr_folab_load.txt' not in saw['scripts'])
check('another mod\'s script was left alone', 'gr_other_mod.txt' in saw['scripts'])

# fell through: the report reads it through the whole chain
top, paths, built, saves, data = make_world('w2')
snap = snapshot(paths)
rep = T.run_test(plan, built, None, paths, os.path.join(top, 'run'), fake_launcher(saves, 'fall'), limits=FAST, running=NEVER)
check('a fall in the game comes out in the report', rep['kinds'].get('fell_through') == 1 and rep['verdict'] == 'problems', rep['kinds'])
check('still all back', same(snap, snapshot(paths)) == [])

# a crash partway
top, paths, built, saves, data = make_world('w3')
snap = snapshot(paths)
rep = T.run_test(plan, built, None, paths, os.path.join(top, 'run'), fake_launcher(saves, 'crash', at=4), limits=FAST, running=NEVER)
check('a game that crashes partway: incomplete, and how far', rep['verdict'] == 'incomplete' and rep['ending'] == 'game closed' and 0 < rep['done']['points'] < rep['totals']['points'], (rep['verdict'], rep['ending'], rep['done']))
check('after a crash, all back', same(snap, snapshot(paths)) == [], same(snap, snapshot(paths))[:4])

# hangs: the silent-file stop, only the process it started
top, paths, built, saves, data = make_world('w4')
snap = snapshot(paths)
made = []
bystander = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])
rep = T.run_test(plan, built, None, paths, os.path.join(top, 'run'), fake_launcher(saves, 'hang', at=4, made=made), limits=FAST, running=NEVER)
check('a hang is stopped when the file goes silent', rep['ending'] == 'went silent' and made[0].stopped, rep['ending'])
check('its process is gone', not made[0].alive())
check('another process wasn\'t touched', bystander.poll() is None)
bystander.kill()
bystander.wait()
check('after a hang, all back', same(snap, snapshot(paths)) == [])

# never wrote a word
top, paths, built, saves, data = make_world('w5')
snap = snapshot(paths)
rep = T.run_test(plan, built, None, paths, os.path.join(top, 'run'), fake_launcher(saves, 'silent'), limits=FAST, running=NEVER)
check('no first line: stopped, and says never started', rep['ending'] == 'no first line' and rep['verdict'] == 'never started', (rep['ending'], rep['verdict']))
check('where to look first', rep['advice']['stage'] == 'no lines')
check('and back', same(snap, snapshot(paths)) == [])

# the time cap
top, paths, built, saves, data = make_world('w6')
tight = G.Limits(cap=1.0, first_line=99, silent=99, finish=2, poll=0.05, live_check=0.1)
rep = T.run_test(plan, built, None, paths, os.path.join(top, 'run'), fake_launcher(saves, 'silent'), limits=tight, running=NEVER)
check('the time cap stops it', rep['ending'] == 'time cap', rep['ending'])

# a user's save changes: stop at once, and say so at the top
top, paths, built, saves, data = make_world('w7')
rep = T.run_test(plan, built, None, paths, os.path.join(top, 'run'), fake_launcher(saves, 'saves'), limits=FAST, running=NEVER)
check('a save changing stops the game at once', rep['ending'] == 'your saves changed', rep['ending'])
check('and is the first thing the report says', rep['findings'][0]['kind'] == 'your_file_changed' and 'saves/' in rep['findings'][0]['text'], rep['findings'][:1])
check('the changed save itself is left as it is (FOLab never touches saves)', os.path.getsize(os.path.join(saves, 'Save 1 - Courier.fos')) == 601)

# the mouse taken
top, paths, built, saves, data = make_world('w8')
rep = T.run_test(plan, built, None, paths, os.path.join(top, 'run'), fake_launcher(saves, 'hang', at=9999), limits=FAST, running=NEVER, input_grabbed=lambda: True)
check('the mouse taken stops it at once', rep['ending'] == 'mouse taken', rep['ending'])

# finishes, doesn't quit
top, paths, built, saves, data = make_world('w9')
made = []
rep = T.run_test(plan, built, None, paths, os.path.join(top, 'run'), fake_launcher(saves, 'noquit', made=made), limits=FAST, running=NEVER)
check('finished but won\'t quit: closed, and counted as finished', rep['finished'] and rep['ending'].startswith('finished') and made[0].stopped, rep['ending'])

# stop on request
top, paths, built, saves, data = make_world('w10')
rep = T.run_test(plan, built, None, paths, os.path.join(top, 'run'), fake_launcher(saves, 'silent'), limits=FAST, running=NEVER, stop_asked=lambda: True)
check('stopped on request', rep['ending'] == 'stopped on request')

# refused before anything changes
top, paths, built, saves, data = make_world('w11')
snap = snapshot(paths)
started = []
try:
    T.run_test(plan, built, None, paths, os.path.join(top, 'run'), lambda p: started.append(1), limits=FAST, running=lambda: [1234])
    check('refuses if the game is running', False)
except G.Refused as e:
    check('refuses if the game is running', 'running' in str(e) and not started)
check('nothing changed by a refusal', same(snap, snapshot(paths)) == [])
open(os.path.join(os.path.dirname(built), 'Needs.esp'), 'wb').write(plugintree.Plugin.empty(espwrite.join([('HEDR', struct.pack('<fiI', 1.34, 0, 0x800)), ('MAST', b'Gone.esm\0'), ('DATA', b'\0' * 8)]), 0).bytes())
try:
    T.run_test(plan, os.path.join(os.path.dirname(built), 'Needs.esp'), None, paths, os.path.join(top, 'run'), lambda p: started.append(1), limits=FAST, running=NEVER)
    check('refuses a mod whose master isn\'t in Data', False)
except G.Refused as e:
    check('refuses a mod whose master isn\'t in Data', 'Gone.esm' in str(e) and not started)
no_go = dict(plan, go=None)
try:
    T.run_test(no_go, built, None, paths, os.path.join(top, 'run'), lambda p: started.append(1), limits=FAST, running=NEVER)
    check('refuses a place it can\'t go to', False)
except G.Refused:
    check('refuses a place it can\'t go to', not started)
check('and still nothing changed', same(snap, snapshot(paths)) == [])

# a launcher that fails: all back
def fails(p):
    raise OSError('no loader')


try:
    T.run_test(plan, built, None, paths, os.path.join(top, 'run2'), fails, limits=FAST, running=NEVER)
    check('a failed start comes back as an error', False)
except OSError:
    check('a failed start comes back as an error', True)
check('and all is put back in the finally', same(snap, snapshot(paths)) == [], same(snap, snapshot(paths))[:4])

# the mod's own files go in and out; what was there comes back
top, paths, built, saves, data = make_world('w12')
assets = os.path.join(top, 'assets')
os.makedirs(os.path.join(assets, 'meshes', 'mine'))
open(os.path.join(assets, 'meshes', 'mine', 'a.nif'), 'w').write('mine')
os.makedirs(os.path.join(data, 'textures'), exist_ok=True)
os.makedirs(os.path.join(assets, 'textures'))
open(os.path.join(assets, 'textures', 'b.dds'), 'w').write('new')
open(os.path.join(data, 'textures', 'b.dds'), 'w').write('the user\'s')
snap = snapshot(paths)
seen_during = {}


def look(p):
    seen_during['a'] = os.path.isfile(os.path.join(p.data_dir, 'meshes', 'mine', 'a.nif'))
    seen_during['b'] = open(os.path.join(p.data_dir, 'textures', 'b.dds')).read()
    return fake_launcher(saves, 'ok')(p)


rep = T.run_test(plan, built, assets, paths, os.path.join(top, 'run'), look, limits=FAST, running=NEVER)
check('the mod\'s own files are in for the run', seen_during == {'a': True, 'b': 'new'}, seen_during)
check('and out after, what they replaced back', same(snap, snapshot(paths)) == [], same(snap, snapshot(paths))[:4])

# ---------- FOLab dying in the middle of a run ----------
top, paths, built, saves, data = make_world('w13')
snap = snapshot(paths)
inner = os.path.join(top, 'inner.py')
plan_file = os.path.join(top, 'plan.json')
json.dump(plan, open(plan_file, 'w'))
run_dir = os.path.join(top, 'run')
with open(inner, 'w') as f:
    f.write('''
import json, os, subprocess, sys, time
sys.path.insert(0, %r)
import gametest as T, gametestguard as G
plan = json.load(open(%r))
paths = G.Paths(%r, %r, %r, %r)
class P:
    def __init__(s, p): s.p, s.pid = p, p.pid
    def alive(s): return s.p.poll() is None
    def stop(s): s.p.kill()
def start(paths):
    return P(subprocess.Popen([sys.executable, %r, paths.data_dir, paths.ini_dir, paths.plugins_txt, %r, 'hang', '4']))
T.run_test(plan, %r, None, paths, %r, start, limits=G.Limits(cap=120, first_line=60, silent=60, poll=0.05), running=lambda: [])
''' % (os.path.join(HERE, '..', 'app'), plan_file, paths.data_dir, paths.ini_dir, paths.plugins_txt, paths.work, os.path.join(HERE, 'fake_game.py'), saves, built, run_dir))
harness = subprocess.Popen([sys.executable, inner], env=dict(os.environ, FAKE_CELL_FORM='01' + T._low(ckey), FAKE_DOOR_FORM='01000000', FAKE_ARRIVE='{}'))
result = os.path.join(data, C.FOLDER, C.RESULT_FILE)
end = time.time() + 30
while time.time() < end and not (os.path.isfile(result) and open(result).read().count('\n') >= 4):
    time.sleep(0.05)
check('the run is under way', os.path.isfile(result))
check('the isolation is in place while it runs', os.path.exists(os.path.join(data, C.CHECKER_PLUGIN)) and 'Mission Mojave' not in open(paths.plugins_txt).read())
harness.kill()      # (FOLab dies; the game it started goes on)
harness.wait()
check('a journal is left behind', os.path.exists(G.journal_path(paths.work)))
j = G.Session.load(paths.work).j
game_pid = j['pid']
check('with the game\'s number in it', bool(game_pid))
r = T.recover_run(paths.work, alive=lambda pid: pid == game_pid)
check('the next start won\'t pull files from under a game still running', r['state'] == 'game still running' and os.path.exists(G.journal_path(paths.work)))
check('nothing was put back yet', os.path.exists(os.path.join(data, C.CHECKER_PLUGIN)))
try:
    T.run_test(plan, built, None, paths, os.path.join(top, 'run3'), lambda p: None, limits=FAST, running=lambda: [], alive=lambda pid: pid == game_pid)
    check('a new run is refused while the old game runs', False)
except G.Refused:
    check('a new run is refused while the old game runs', True)
subprocess.run(['taskkill', '/F', '/PID', str(game_pid)], capture_output=True)
time.sleep(0.3)
r = T.recover_run(paths.work, alive=lambda pid: False)
check('once it\'s gone the next start puts everything back', r['state'] == 'restored', r)
check('byte for byte', same(snap, snapshot(paths)) == [], same(snap, snapshot(paths))[:4])
check('a second recovery has nothing to do', T.recover_run(paths.work)['state'] == 'clean')
rp = os.path.join(run_dir, 'report.json')
check('and the partial results still make a report', os.path.isfile(rp) and json.load(open(rp))['verdict'] == 'incomplete')
check('that says it was cut off', json.load(open(rp))['ending'] == 'cut off')

# restore can run twice, and a held file is retried
top, paths, built, saves, data = make_world('w14')
snap = snapshot(paths)
s = G.Session.begin(paths, 'R', G.fingerprint(paths))
s.set_plugins(['FalloutNV.esm'])
s.set_ini(T.game_settings())
s2 = G.Session.load(paths.work)
out = s2.restore()
check('restore from the journal alone', same(snap, snapshot(paths)) == [] and out['problems'] == [] and out['differences'] == [])
check('the journal is finished with', not os.path.exists(G.journal_path(paths.work)))
out2 = s2.restore()
check('restore twice does no harm', same(snap, snapshot(paths)) == [] and out2['problems'] == [])
# a journal started, nothing done yet: crash at the very first moment
s = G.Session.begin(paths, 'R2', G.fingerprint(paths))
check('a crash before any change: recovers clean', G.recover(paths.work, alive=lambda p: False)['state'] == 'restored' and same(snap, snapshot(paths)) == [])
s = G.Session.begin(paths, 'R3', G.fingerprint(paths))
try:
    G.Session.begin(paths, 'R4', G.fingerprint(paths))
    check('a second journal is refused', False)
except G.Refused:
    check('a second journal is refused', True)
G.recover(paths.work, alive=lambda p: False)

# fingerprints and differences
before = G.fingerprint(paths)
check('fingerprint covers saves, INIs, plugins.txt, plugins', {'saves/Save 1 - Courier.fos', 'ini/Fallout.ini', 'plugins.txt', 'data/FalloutNV.esm'} <= set(before), list(before)[:6])
open(os.path.join(saves, 'Save 2.fos'), 'wb').write(b'n')
after = G.fingerprint(paths)
check('a new save is seen', G.differences(before, after) == [{'file': 'saves/Save 2.fos', 'how': 'added'}])
os.remove(os.path.join(saves, 'Save 2.fos'))
os.chmod(os.path.join(paths.ini_dir, 'Fallout.ini'), 0o666)
with open(os.path.join(paths.ini_dir, 'Fallout.ini'), 'ab') as f:
    f.write(b'x')
check('a changed INI is seen', [d['file'] for d in G.differences(before, G.fingerprint(paths))] == ['ini/Fallout.ini'])
check('only: looks at that part alone', G.differences(before, G.fingerprint(paths), only=['saves/']) == [])
check('the user\'s save folder comes from the INI', G.Paths(data, paths.ini_dir, paths.plugins_txt, 'w').saves() == os.path.join(paths.ini_dir, 'Saves'))

# INI editing
lines, placed = G.edit_ini_lines(['[A]', 'x=1', '; x=9', 'y = 2', '[B]', 'x=3'], {('A', 'x'): 7})
check('an INI edit changes only that key, in that section', lines == ['[A]', 'x=7', '; x=9', 'y = 2', '[B]', 'x=3'] and placed == {('a', 'x')})
lines, _p = G.edit_ini_lines(['[A]', 'x=1'], {('B', 'z'): 5, ('A', 'w'): 6}, add=True)
check('new keys go in their sections', lines == ['[A]', 'w=6', 'x=1', '[B]', 'z=5'], lines)

# a stray game: found by name, not touched
check('game_pids only reads, and finds nothing called this', G.game_pids('no such game here.exe') == [])
check('pid_alive knows this process', G.pid_alive(os.getpid()) and not G.pid_alive(0))

# ---------- the launch stays locked ----------
never = []
real_popen = subprocess.Popen
subprocess.Popen = lambda *a, **k: never.append(a) or (_ for _ in ()).throw(AssertionError('Popen called'))
for words in (None, '', 'yes', 'start the game'):
    try:
        T.launch_real(paths, words)
        check('no confirmation, no game (%r)' % (words,), False)
    except T.Locked:
        check('no confirmation, no game (%r)' % (words,), not never)
try:
    T.launch_real(paths, T.CONFIRM)
    check('with the words, under tests: still no game', False)
except T.Locked as e:
    check('with the words, under tests: still no game', 'test settings' in str(e) and not never)
subprocess.Popen = real_popen


class S:                    # (what the page's routes need of server.py)
    import threading
    _lock = threading.RLock()
    GD, PR = gd, pr

    @staticmethod
    def place_name(k):
        return T._cell_words(gd, pr, k)


try:
    T.post('start', {'cell': ckey}, S)
    check('the page\'s start needs the words', False)
except ValueError as e:
    check('the page\'s start needs the words', 'START THE GAME' in str(e))
try:
    T.post('start', {'cell': ckey, 'confirmation': 'go'}, S)
    check('and only those', False)
except ValueError:
    check('and only those', T._state['thread'] is None)
real_data = {f: os.path.getmtime(os.path.join(gd.data_dir, f)) for f in os.listdir(gd.data_dir)}
try:
    T.post('start', {'cell': ckey, 'confirmation': T.CONFIRM}, S)
    check('with the words, under tests, the page stops before touching Data', False)
except ValueError as e:
    check('with the words, under tests, the page stops before touching Data', 'test settings' in str(e) and T._state['thread'] is None)
check('the real Data folder is as it was', real_data == {f: os.path.getmtime(os.path.join(gd.data_dir, f)) for f in os.listdir(gd.data_dir)})
got = T.get('status', {}, S)
check('the page\'s status lists the mod\'s places', any(p['key'] == ckey for p in got['places']) and got['confirm'] == T.CONFIRM and not got['running'])
check('and nothing in hand to recover', got['recovery']['state'] == 'clean')
r = T.post('read', {'cell': ckey, 'text': 'boot|gr|x\ngo|1', 'ending': 'went silent'}, S)
check('a result file by hand gives a report on the page', r['verdict'] == 'incomplete' and r['advice']['stage'] == 'no move')
got = T.get('plan', {'cell': ckey}, S)
check('the page\'s plan has its counts and what stands in the way', got['plan']['counts']['points'] == len(plan['points']) and any(not x['note'] for x in got['preflight']))
check('the real plugins.txt was never the one in play', not REAL_LOCAL or not os.environ['LOCALAPPDATA'].startswith(REAL_LOCAL))
