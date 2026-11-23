"""vault50door_into_waikiki.py [real] [--home H] [--app A]: Vault 50's gear door, intact, with 50 on its plate, opened from
anywhere on its face (the Workshop's item 3, option b, 23 Nov 2026). Today's door (the ruined VGearDoorR22, re-numbered)
stands where Vault 22's entrance closes the doorway in its own collision: 0 of 50 spots picked it.

- The entrance (Vault22Entrance, +0A1640) gets a model of FOLab's own: the game's, with the slab that closes the doorway
  in its collision (12 triangles, entcut.PLUG) collapsed in place; walls, ring and everything else as they were.
- The gear door: the game's intact VGearDoor01 model (its Open and Close are VGearDoorR108's own), its plate's picture
  VGearDoor03 painted "50" (gear50.py; PIL), stood on the doorway's middle (entrance frame x -60.5, y -105, z 20, turned
  180: its face where the slab's front was). The door's record (+0C1DA0, FOLabVault50GearDoor) becomes a copy of
  VGearDoorR108's (its gear sounds) on that model; the ref (+0A1641) keeps its link.
- Whoever comes out of the Vault arrives in front of the disc. The door's cell's navmesh made again.
Checks after, from the saved mod: doorpick 50 of 50; no line through the doorway passes (the door shut it); the arrival
clear (arrivalcheck). One Undo; backup; refuses while the game runs (not on a FOLabScratch home). Dry run without `real`.
Tell whoever rebuilds vaultgate: the entrance ref's base is FOLab's piece now."""
import math, os, shutil, struct, subprocess, sys, time

ARGS = sys.argv[1:]
REAL = 'real' in ARGS


def opt(name, default):
    return ARGS[ARGS.index(name) + 1] if name in ARGS else default


HOME = opt('--home', r'C:\Users\AMD RYZEN\Claude Code Projects\FOLab\packaging\out\FOLab')
APP = opt('--app', r'C:\Users\AMD RYZEN\Claude Code Projects\FOLab\.claude\worktrees\zealous-rosalind-5e1645\app')
HERE = os.path.dirname(os.path.abspath(__file__))
ENT, DOOR, DOOR_REC = '+0A1640', '+0A1641', '+0C1DA0'
AT = (-60.5, -105.0, 20.0)             # (the door's origin in the entrance's frame)
BS = chr(92)
ENT_MODEL = 'folab' + BS + 'vault50' + BS + 'Vault22EntranceOpen.nif'
DOOR_MODEL = 'folab' + BS + 'vault50' + BS + 'VGearDoor50.nif'
PLATE = 'textures' + BS + 'folab' + BS + 'vault50' + BS + 'VGearDoor03_50.dds'
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
import gamedata, project, server, recordio, nifwrite, library, navbuild, hkshape, arrivalcheck  # noqa: E402
import doorpick, entcut, gear50  # noqa: E402
src = os.path.join(project.PROJECTS_DIR, 'Waikiki.json')
was = project.modified(src)
say('mod', src, time.strftime('%d %b %H:%M', time.localtime(was)))
server.not_while_playing = lambda: None
server.GD = gamedata.GameData(); server.BR = None
pr = project.Project.open('Waikiki'); server.load_game(pr); server.PR = pr
gd = server.GD


def refs_now():
    return {rk: (ck, r) for ck, c in pr.cells.items() for rk, r in (c.get('refs') or {}).items() if not r.get('removed')}


refs = refs_now()
for k in (ENT, DOOR):
    if k not in refs:
        sys.exit('no ' + k + ' in the mod')
if recordio.field(pr.records[DOOR_REC], 'MODL').lower().endswith('vgeardoor50.nif'):
    sys.exit('Vault 50 has the intact door already: run already?')
form = lambda e, tag: next(f for f, (i, r) in gd.forms.items() if r.tag == tag and gd.edid(f) == e)
ent_f, gear_f, r108_f = form('Vault22Entrance', 'STAT'), form('VGearDoor01', 'ACTI'), form('VGearDoorR108', 'DOOR')
ent_raw = gd.read_file(gd.model_path('STAT', gd.describe(ent_f)[3]))
ent_cut, gone = entcut.cut(ent_raw)
gear_raw = gd.read_file(gd.model_path('ACTI', gd.describe(gear_f)[3]))
old_plate = [t['path'] for t in nifwrite.textures_in(gear_raw) if t['path'].lower().endswith('vgeardoor03.dds')]
gear_nif = nifwrite.retexture(gear_raw, {p: PLATE for p in old_plate})
plate, _im = gear50.picture(gd)
plate_n = gd.read_file(chr(92).join(['textures', 'dungeons', 'vault', 'VGearDoor03_n.dds']))
files = {'meshes' + BS + ENT_MODEL: ent_cut, 'meshes' + BS + DOOR_MODEL: gear_nif, PLATE: plate, PLATE[:-4] + '_n.dds': plate_n}
say('entrance: %d triangles of its collision collapsed (the slab) | the door model on %s | files %d' % (len(gone), old_plate, len(files)))
# records
ent_rec = recordio.load(gd, ent_f)
ent_rec['subs'] = [s for s in ent_rec['subs'] if s['tag'] not in ('MODT',)]
recordio.set_field(ent_rec, 'EDID', 'FOLabVault22EntranceOpen', label='Editor ID')
recordio.set_field(ent_rec, 'MODL', ENT_MODEL, label='Model')
ent_rec.pop('copied_from', None)
door_rec = recordio.load(gd, r108_f)
door_rec['subs'] = [s for s in door_rec['subs'] if s['tag'] not in ('MODT',)]
recordio.set_field(door_rec, 'EDID', 'FOLabVault50GearDoor', label='Editor ID')
recordio.set_field(door_rec, 'MODL', DOOR_MODEL, label='Model')
gb = struct.unpack('<6h', gd.fields(gear_f)['OBND'][:12])
for s in door_rec['subs']:
    if s['tag'] == 'OBND':
        for f, v in zip([f for f in s['fields'] if 'name' in f], gb):
            f['value'] = int(v)
door_rec.pop('copied_from', None)
# places
eck, er = refs[ENT]
dck, dr = refs[DOOR]
ep = er['p']
c, sn = math.cos(ep[5]), math.sin(ep[5])
wx, wy = ep[0] + AT[0] * c + AT[1] * sn, ep[1] - AT[0] * sn + AT[1] * c
dp = [round(wx, 2), round(wy, 2), round(ep[2] + AT[2], 2), 0.0, 0.0, round((ep[5] + math.pi) % math.tau, 4)]
out = (-sn, -c)                        # (the entrance frame's -y: out to the crater)
# the arrival outside: 150 in front of the disc's face (its middle: local x 3.5, front y 34 turned to the room)
disc = (dp[0] + (-3.5) * math.cos(dp[5]) + (-34.0) * math.sin(dp[5]), dp[1] - (-3.5) * math.sin(dp[5]) + (-34.0) * math.cos(dp[5]))
ops = [{'op': 'record_new', 'record': ent_rec, 'name': 'v50_entrance'},
       {'op': 'record', 'key': DOOR_REC, 'record': door_rec},
       {'op': 'swap', 'cell': eck, 'ref': ENT, 'base': '$v50_entrance'},
       {'op': 'move', 'cell': dck, 'ref': DOOR, 'p': dp}]
for k, (ck, r) in refs.items():
    t = r.get('tel') or {}
    if t.get('door') == DOOR and t.get('p'):
        na = [round(disc[0] + out[0] * 150, 2), round(disc[1] + out[1] * 150, 2), t['p'][2], 0.0, 0.0, round(math.atan2(out[0], out[1]) % math.tau, 4)]
        ops.append({'op': 'tel', 'cell': ck, 'ref': k, 'tel': dict(t, p=na)})
say('door to', dp, '| ops', len(ops))
if not REAL:
    say('dry run: nothing saved, no files written')
    sys.exit(0)
if project.modified(src) != was:
    sys.exit('Waikiki changed while this ran: stopping')
back = os.path.join(HOME, 'backups', 'Waikiki before Vault 50 door %s' % time.strftime('%m%d-%H%M'))
os.makedirs(back)
for f in (src, os.path.splitext(src)[0] + '.changes'):
    if os.path.isfile(f):
        shutil.copy2(f, back)
say('backup', back)
root = library.assets_dir(pr)
for rel, data in files.items():
    library._put(root, rel, data)
label = "Vault 50's gear door: intact, 50 on its plate, the doorway open to it"
pr.apply(label, ops)
say('applied and saved; files written', len(files))
nops, nrep = navbuild.generate_area(gd, pr, sorted({dck, eck}))
pr.apply(label, nops, merge=True)
say('navmesh made again', {k: nrep.get(k) for k in ('cells', 'doors', 'doors_missed', 'neighbours')})
# checks from the saved mod
refs = refs_now()


def model_of(b):
    try:
        if b.startswith('+'):
            rr = pr.records.get(b)
            mm = recordio.field(rr, 'MODL') if rr else None
            return ('meshes' + BS + mm) if mm else None
        t_, e_, f_, mm = gd.describe(gd.from_key(b))
        return gd.model_path(t_, mm) if mm else None
    except Exception:
        return None


_g = {}


def group_of(cc):
    if cc not in _g:
        try:
            w = gd.ext_cells.get(gd.from_key(cc))
        except Exception:
            w = None
        _g[cc] = ('world', w) if w is not None else ('place', cc)
    return _g[cc]


P = doorpick.Picker(gd, pr, refs, model_of, group_of)
res = P.door(DOOR, out, [-150, -30, -121, 157, 34, 181])
say('doorpick: %d of %d' % (res['picked'], res['spots']), res['by'])
# no line straight through the doorway: the cut entrance and the door's own collision, in the entrance's frame
E = []
for s in hkshape.collision_shapes(gd.read_file('meshes' + BS + ENT_MODEL)):
    E += doorpick._world(s['v'], s['i'], (0, 0, 0), (0, 0, 0), 1.0)
for s in hkshape.collision_shapes(gd.read_file('meshes' + BS + DOOR_MODEL)):
    E += doorpick._world(s['v'], s['i'], (0, 0, math.pi), AT, 1.0)
leaks = [(x, z) for x in range(-420, 260, 16) for z in range(10, 230, 20)
         if not any((lambda d_: d_ is not None and d_ < 700)(doorpick._hit((x, -420.0, z), (0.0, 1.0, 0.0), t_)) for t_ in E)]
say('lines straight through the doorway:', len(leaks), '(the game\'s, uncut, with its ruined door: 1)')
ac = arrivalcheck.check(gd, pr)
mine = [b for b in ac['bad'] if b['door'] == DOOR]
say('arrivals out of the Vault: %s' % ('clear' if not mine else mine))
bad = []
if res['picked'] < res['spots']:
    bad.append('door picked at %d of %d' % (res['picked'], res['spots']))
if len(leaks) > 1:
    bad.append('%d lines pass through the doorway' % len(leaks))
if [b for b in mine if 'blocked' in b['why'] or 'inside' in b['why']]:
    bad.append('the arrival out of the Vault is in something')
say('CHECKS: ' + ('all good' if not bad else 'PROBLEMS: ' + '; '.join(bad)))
