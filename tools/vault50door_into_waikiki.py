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
- Clear of the door (23 Nov, the Workshop: "a bunch of leaves clipped into it"): the entrance's ivy and evergreen sprigs
  within 10 of the space the disc sweeps as it opens (pulled 120 back, rolled 270 aside) taken out of its model, the rest
  kept, and its own ruined drill (the intact door brings its drill to the same spot: v50leaves.py); BlackPlane01 behind
  the doorway removed; anything placed whose bounds reach into that space removed (no door, nothing linked or persistent).
  Run on a mod that has the first version already, it does only these.
- The landing up to the entrance (the story session, 23 Nov: are the landing and the door one piece of navmesh? They were
  not: vaultgate stands the entrance 125 over the landing, so the front of its apron is a ledge 40 to 100 over the land and
  the door's navmesh was an island of 20 triangles under it). The land in front of the apron (`RAMP_HALF` either side of
  the door) is raised to just under the apron's own top at its front edge and eased back over `RAMP_EASE`; only ever
  raised; what stands on that ground moves with it.
Checks after, from the saved mod: doorpick 50 of 50; no line through the doorway passes (the door shut it); the arrival
clear (arrivalcheck); no foliage or drill triangle of the entrance left in the swept space; nothing placed in it; the
landing in front and the door's own navmesh triangle in one piece. One Undo; no backup (the install makes the one);
refuses while the game runs (not on a FOLabScratch home). Dry run without `real`.
Tell whoever rebuilds vaultgate: the entrance ref's base is FOLab's piece now."""
import math, os, shutil, struct, subprocess, sys, time

ARGS = sys.argv[1:]
REAL = 'real' in ARGS


def opt(name, default):
    return ARGS[ARGS.index(name) + 1] if name in ARGS else default


HOME = opt('--home', r'C:\Users\AMD RYZEN\Claude Code Projects\FOLab\packaging\out\FOLab')
APP = opt('--app', r'C:\Users\AMD RYZEN\Claude Code Projects\FOLab\app')     # (the main checkout: what the installs build with)
HERE = os.path.dirname(os.path.abspath(__file__))
ENT, DOOR, DOOR_REC = '+0A1640', '+0A1641', '+0C1DA0'

BS = chr(92)
ENT_MODEL = 'folab' + BS + 'vault50' + BS + 'Vault22EntranceOpen.nif'
DOOR_MODEL = 'folab' + BS + 'vault50' + BS + 'VGearDoor50.nif'
PLUG_MODEL = 'folab' + BS + 'vault50' + BS + 'Vault50Plug.nif'
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
import doorpick, entcut, gear50, v50leaves  # noqa: E402
AT, TURN = v50leaves.AT, v50leaves.TURN    # (the door's origin and turn in the entrance's frame: the game's ruined disc's spot)
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
AGAIN = recordio.field(pr.records[DOOR_REC], 'MODL').lower().endswith('vgeardoor50.nif')
if AGAIN:
    sys.exit('Vault 50 has an intact door already (an earlier version of this step): run on a mod without it')
say('the whole step')
form = lambda e, tag: next(f for f, (i, r) in gd.forms.items() if r.tag == tag and gd.edid(f) == e)
ent_f, gear_f, r108_f = form('Vault22Entrance', 'STAT'), form('VGearDoor01', 'ACTI'), form('VGearDoorR108', 'DOOR')
ent_raw = gd.read_file(gd.model_path('STAT', gd.describe(ent_f)[3]))
ent_cut, gone = ent_raw, []                # (the disc stands at the doorway's face, in front of the game's slab: no cut)
leaves_before = v50leaves.check(ent_cut)
ent_cut, leaf_counts = v50leaves.cut(ent_cut)
gear_raw = gd.read_file(gd.model_path('ACTI', gd.describe(gear_f)[3]))
old_plate = [t['path'] for t in nifwrite.textures_in(gear_raw) if t['path'].lower().endswith('vgeardoor03.dds')]
gear_nif = nifwrite.retexture(gear_raw, {p: PLATE for p in old_plate})
plate, _im = gear50.picture(gd)
plate_n = gd.read_file(chr(92).join(['textures', 'dungeons', 'vault', 'VGearDoor03_n.dds']))
# the game's invisible slab over the doorway (entcut.PLUG, y -139 to -99) stood in front of the disc where the game stands
# it, so it is cut; a plug of FOLab's own as wide and high, just behind the disc's face, keeps the rest of the doorway
# shut (the disc stands 100 to one side of the hole's middle, as the game's does: a strip 85 wide beside it)
PLUG_BOX = (-207.8, -80.0, -89.2, 79.2, -64.0, 240.0)        # (x, y, z from and to, in the entrance's frame)
import nifmake  # noqa: E402
x0, y0, z0, x1, y1, z1 = PLUG_BOX
corners = [(x, y, z) for z in (z0, z1) for y in (y0, y1) for x in (x0, x1)]
faces = [[0, 2, 3, 1], [4, 5, 7, 6], [0, 1, 5, 4], [2, 6, 7, 3], [0, 4, 6, 2], [1, 3, 7, 5]]
hidden = {'p': [-100.0, -72.0, 50.0, -99.9, -72.0, 50.0, -100.0, -72.0, 50.1], 'n': [0.0, -1.0, 0.0] * 3,
          'uv': [0.0, 0.0, 0.01, 0.0, 0.0, 0.01], 'i': [0, 1, 2],
          'tex': chr(92).join(['textures', 'dungeons', 'vault', 'VGearDoor01.dds'])}    # (one speck inside the disc: a model needs a shape)
plug_nif = nifmake.build('FOLabVault50Plug', [hidden], [{'points': corners, 'faces': faces, 'material': 'metal'}])
files = {'meshes' + BS + ENT_MODEL: ent_cut, 'meshes' + BS + DOOR_MODEL: gear_nif, PLATE: plate, PLATE[:-4] + '_n.dds': plate_n}
say('entrance: %d triangles of its collision collapsed (the slab) | the door model on %s | files %d' % (len(gone), old_plate, len(files)))
say('entrance drawn: foliage and drill triangles in the swept space %d; taken out (out, kept) %s' % (leaves_before, leaf_counts))
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
plug_rec = recordio.load(gd, form('BlackPlane01', 'STAT'))
plug_rec['subs'] = [s_ for s_ in plug_rec['subs'] if s_['tag'] not in ('MODT',)]
recordio.set_field(plug_rec, 'EDID', 'FOLabVault50Plug', label='Editor ID')
recordio.set_field(plug_rec, 'MODL', PLUG_MODEL, label='Model')
for s_ in plug_rec['subs']:
    if s_['tag'] == 'OBND':
        for f, v in zip([f for f in s_['fields'] if 'name' in f], (x0, y0, z0, x1, y1, z1)):
            f['value'] = int(round(v))
plug_rec.pop('copied_from', None)
# places
eck, er = refs[ENT]
dck, dr = refs[DOOR]
ep = er['p']
c, sn = math.cos(ep[5]), math.sin(ep[5])
wx, wy = ep[0] + AT[0] * c + AT[1] * sn, ep[1] - AT[0] * sn + AT[1] * c
dp = [round(wx, 2), round(wy, 2), round(ep[2] + AT[2], 2), 0.0, 0.0, round((ep[5] + TURN) % math.tau, 4)]
out = (math.sin(dp[5]), math.cos(dp[5]))   # (the door's own +y, its plate's side: out to the crater)
# the arrival outside, facing out: straight out from the disc's middle, 64 in front of the apron, on the landing. The game
# puts you out of Vault 22 at (-77.4, -436.2) (its inside door's XTEL, in the entrance's frame), but here the land falls
# away there, east of vaultgate's landing (107 under it, off the navmesh); 100 in front of the disc it stood against the
# apron's lip. Its height is set from the ground under it below
ARRIVE = (-67.0, -300.0)      # (straight out from the disc's middle)
aw = (ep[0] + ARRIVE[0] * c + ARRIVE[1] * sn, ep[1] - ARRIVE[0] * sn + ARRIVE[1] * c)
ops = [] if AGAIN else [{'op': 'record_new', 'record': ent_rec, 'name': 'v50_entrance'},
                        {'op': 'record', 'key': DOOR_REC, 'record': door_rec},
                        {'op': 'swap', 'cell': eck, 'ref': ENT, 'base': '$v50_entrance'},
                        {'op': 'move', 'cell': dck, 'ref': DOOR, 'p': dp},
]
for k, (ck, r) in refs.items():
    t = r.get('tel') or {}
    if not AGAIN and t.get('door') == DOOR and t.get('p'):
        na = [round(aw[0], 2), round(aw[1], 2), t['p'][2], 0.0, 0.0, round((ep[5] + math.pi) % math.tau, 4)]
        ops.append({'op': 'tel', 'cell': ck, 'ref': k, 'tel': dict(t, p=na)})


def door_world(x, y, z):
    """The door's frame (turned about z) to the world."""
    c_, s_ = math.cos(dp[5]), math.sin(dp[5])
    return (dp[0] + x * c_ - y * s_, dp[1] + x * s_ + y * c_, dp[2] + z)


# (the swept space sampled every 16, in the door's frame; v50leaves.swept reads the entrance's, the door turned half round)
SWEEP = [door_world(x, y, z) for x in range(-160, 440, 16) for y in range(-160, 50, 16) for z in range(-130, 190, 16)
         if v50leaves.swept(v50leaves.door_to_entrance(x, y, z), 0.0)]


def name_of(b):
    try:
        return recordio.field(pr.records[b], 'EDID') if b.startswith('+') else gd.edid(gd.from_key(b))
    except Exception:
        return '?'


def obnd(b):
    try:
        if b.startswith('+'):
            s_ = next(x for x in pr.records[b]['subs'] if x['tag'] == 'OBND')
            return [int(f['value']) for f in s_['fields'] if 'name' in f]
        return list(struct.unpack('<6h', gd.fields(gd.from_key(b))['OBND'][:12]))
    except Exception:
        return None


def in_sweep(refs_):
    """Things placed whose bounds reach into the disc's swept space: [(ref, cell, editor ID)]."""
    import navgen
    named = {(r.get('tel') or {}).get('door') for ck, r in refs_.values()}
    out = []
    for rk, (ck, r) in refs_.items():
        p = r.get('p')
        if rk in (ENT, DOOR) or not p or not r.get('base') or math.dist(p[:3], dp[:3]) > 1500:
            continue
        if r.get('tel') or r.get('persistent') or rk in named or name_of(r['base']) == 'FOLabVault50Plug':
            continue
        b = obnd(r['base'])
        if not b or b == [0] * 6:
            continue
        M = navgen._turn(*p[3:6])
        s_ = float(r.get('s') or 1.0)
        for q in SWEEP:
            v = [(q[k] - p[k]) / s_ for k in range(3)]
            lx, ly, lz = (sum(M[k][j] * v[k] for k in range(3)) for j in range(3))
            if b[0] <= lx <= b[3] and b[1] <= ly <= b[4] and b[2] <= lz <= b[5]:
                out.append((rk, ck, name_of(r['base'])))
                break
    return out


planes = [(rk, ck) for rk, (ck, r) in refs.items() if r.get('p') and name_of(r.get('base') or '') == 'BlackPlane01'
          and math.dist(r['p'][:3], dp[:3]) < 600]
swept_refs = [x for x in in_sweep(refs) if x[0] not in {k for k, c in planes}]
say('BlackPlane01 behind the doorway: %d | placed things in the swept space: %d %s' % (len(planes), len(swept_refs), [x[2] for x in swept_refs]))
ops += [{'op': 'remove', 'cell': ck, 'ref': rk} for rk, ck in planes] + [{'op': 'remove', 'cell': ck, 'ref': rk} for rk, ck, e in swept_refs]
# the landing brought up to the apron's front edge
import land as _land  # noqa: E402
RAMP_HALF, RAMP_EASE, RAMP_MOST = 220.0, 320.0, 140.0     # (either side of the door's middle, AT[0])
W = arrivalcheck.World(gd, pr)
ent_tris = W.ref_tris(ENT)
world = gd.ext_cells.get(gd.from_key(eck))


def apron_top(x, y):
    """The top of the entrance's floor at (x, y) (its highest solid under the entrance's origin), or None."""
    best = None
    for t in ent_tris:
        if t[1] <= x <= t[2] and t[3] <= y <= t[4]:
            d_ = doorpick._hit((x, y, ep[2] - 10.0), (0.0, 0.0, -1.0), t[0])
            if d_ is not None:
                z_ = ep[2] - 10.0 - d_
                best = z_ if best is None or z_ > best else best
    return best


forms, before_h = {}, {}


def form_of(cx, cy):
    if (cx, cy) not in forms:
        cell = gd.grid(world).get((cx, cy))
        if cell is None:
            return None
        mine = pr.land.get(gd.key(cell))
        e_ = gd.land_at(world, cx, cy)
        if not mine and not e_:
            return None
        f_ = dict(mine) if mine else _land.decode(gd, e_, {})
        f_['h'] = [float(v) for v in f_['h']]
        forms[(cx, cy)] = f_
        before_h[(cx, cy)] = list(f_['h'])
    return forms[(cx, cy)]


def points(gx, gy):
    out_ = []
    for cx in ({gx // 32, (gx - 1) // 32} if gx % 32 == 0 else {gx // 32}):
        for cy in ({gy // 32, (gy - 1) // 32} if gy % 32 == 0 else {gy // 32}):
            f_ = form_of(cx, cy)
            if f_:
                out_.append((f_, (cx, cy), (gy - cy * 32) * 33 + (gx - cx * 32)))
    return out_


def ground(x, y, h_of):
    gx, gy = x / 128.0, y / 128.0
    x0, y0 = int(math.floor(gx)), int(math.floor(gy))
    fx, fy = gx - x0, gy - y0
    v = []
    for a, b in ((x0, y0), (x0 + 1, y0), (x0, y0 + 1), (x0 + 1, y0 + 1)):
        pts_ = points(a, b)
        if not pts_:
            return None
        f_, k_, i_ = pts_[0]
        v.append(h_of(k_, f_)[i_])
    return (v[0] * (1 - fx) + v[1] * fx) * (1 - fy) + (v[2] * (1 - fx) + v[3] * fx) * fy


# (the apron's front edge, along the entrance's x: where its top starts, walking in from the crater)
edge = {}
SPAN = range(int(AT[0] - RAMP_HALF), int(AT[0] + RAMP_HALF) + 1, 16)
for ax in SPAN:
    for ay in range(-400, 0, 4):
        wx_, wy_ = ep[0] + ax * c + ay * sn, ep[1] - ax * sn + ay * c
        z_ = apron_top(wx_, wy_)
        if z_ is not None:
            edge[ax] = (ay, z_)
            break
raised, ramp_moved = 0, []
if edge:
    lo_y = min(v[0] for v in edge.values()) - RAMP_EASE - 128
    for gy in range(int((ep[1] + lo_y - 256) // 128), int((ep[1] + 0) // 128) + 2):
        for gx in range(int((ep[0] + AT[0] - RAMP_HALF - RAMP_EASE) // 128) - 1, int((ep[0] + AT[0] + RAMP_HALF + RAMP_EASE) // 128) + 2):
            wx_, wy_ = gx * 128.0, gy * 128.0
            lx_ = (wx_ - ep[0]) * c - (wy_ - ep[1]) * sn
            ly_ = (wx_ - ep[0]) * sn + (wy_ - ep[1]) * c
            k_ = min(edge, key=lambda a: abs(a - lx_))
            ey_, ez_ = edge[k_]
            if ly_ > ey_ + 8:
                continue                              # (under the apron: left)
            want = math.floor((ez_ - 2.0) / 8.0) * 8.0
            d_ = math.hypot(max(abs(lx_ - AT[0]) - RAMP_HALF, 0.0), max(ey_ - ly_, 0.0))
            if d_ >= RAMP_EASE:
                continue
            u_ = d_ / RAMP_EASE
            u_ = u_ * u_ * (3 - 2 * u_)
            for f_, kk, i_ in points(gx, gy):
                old = f_['h'][i_]
                if want - old > RAMP_MOST or want <= old:
                    continue
                f_['h'][i_] = round((want * (1 - u_) + old * u_) / 8.0) * 8.0
                raised += 1
    # what stands on that ground moves with it (not the entrance, its door or anything named or linked)
    for rk, (ck, r) in refs.items():
        p_ = r.get('p')
        if not p_ or rk in (ENT, DOOR) or r.get('tel') or r.get('persistent') or math.dist(p_[:2], ep[:2]) > 2000:
            continue
        g0 = ground(p_[0], p_[1], lambda k_, f_: before_h[k_])
        g1 = ground(p_[0], p_[1], lambda k_, f_: f_['h'])
        if g0 is None or g1 is None or abs(g1 - g0) < 2.0 or abs(p_[2] - g0) > 60:
            continue
        np_ = list(p_)
        np_[2] = round(p_[2] + (g1 - g0), 1)
        ramp_moved.append({'op': 'move', 'cell': ck, 'ref': rk, 'p': np_})
land_ops = [{'op': 'land', 'cell': gd.key(gd.grid(world)[k_]), 'land': f_} for k_, f_ in sorted(forms.items()) if f_['h'] != before_h[k_]]
say('the landing up to the apron: its front edge found at %d of %d spots, %d land points raised in %d cells, %d things moved with it'
    % (len(edge), len(SPAN), raised, len(land_ops), len(ramp_moved)))
say('  the front edge of the apron (entrance x: y, top):', {k: (v[0], round(v[1])) for k, v in sorted(edge.items())})
ops += land_ops + ramp_moved
# the arrival out of the Vault on what is under it now (the apron's top or the raised land), not where it used to be
for o in ops:
    if o['op'] == 'tel':
        ax_, ay_ = o['tel']['p'][0], o['tel']['p'][1]
        under = [z_ for z_ in (apron_top(ax_, ay_), ground(ax_, ay_, lambda k_, f_: f_['h'])) if z_ is not None]
        if under:
            o['tel'] = dict(o['tel'], p=[ax_, ay_, round(max(under) + 4.0, 1)] + list(o['tel']['p'][3:]))
            say('arrival out of the Vault at', o['tel']['p'])
say('door at', dp, '| ops', len(ops))
if not REAL:
    say('dry run: nothing saved, no files written')
    sys.exit(0)
if project.modified(src) != was:
    sys.exit('Waikiki changed while this ran: stopping')
root = library.assets_dir(pr)
for rel, data in files.items():
    library._put(root, rel, data)
label = "Vault 50's gear door: intact, 50 on its plate, the doorway open to it"
if ops:
    pr.apply(label, ops)
say('applied and saved; files written', len(files))
nops, nrep = navbuild.generate_area(gd, pr, sorted({dck, eck}))
pr.apply(label, nops, merge=bool(ops))
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
    E += doorpick._world(s['v'], s['i'], (0, 0, TURN), AT, 1.0)
leaks = [(x, z) for x in range(-420, 260, 16) for z in range(10, 230, 20)
         if not any((lambda d_: d_ is not None and d_ < 700)(doorpick._hit((x, -420.0, z), (0.0, 1.0, 0.0), t_)) for t_ in E)]
say('lines straight through the doorway:', len(leaks), "(the game's, uncut, with its ruined door: 1)", leaks)
ac = arrivalcheck.check(gd, pr)
mine = [b for b in ac['bad'] if b['door'] == DOOR]
say('arrivals out of the Vault: %s' % ('clear' if not mine else mine))
left = v50leaves.check(gd.read_file('meshes' + BS + ENT_MODEL))
say('entrance as written: foliage or drill triangles in the swept space', left)
still = in_sweep(refs)
say('placed things in the swept space now:', len(still), [x[2] for x in still])
# the landing in front and the door's triangle, one piece of the cell's navmesh
m = pr.navmesh.get(dck) or {}
tris, verts = m.get('tris') or [], m.get('verts') or []
door_tri = next((d_[1] for d_ in (m.get('doors') or []) if d_[0] == DOOR), None)
seen = set([door_tri]) if door_tri is not None else set()
todo = list(seen)
while todo:
    t_ = tris[todo.pop()]
    for k in range(3):
        if not (t_[6] >> k & 1) and t_[3 + k] != 0xFFFF and t_[3 + k] not in seen:
            seen.add(t_[3 + k])
            todo.append(t_[3 + k])


def mid(t_):
    return [sum(verts[t_[c]][a] for c in range(3)) / 3.0 for a in range(3)]


landing = [k for k, t_ in enumerate(tris)
           if (lambda c_: -15200 <= c_[0] <= -13600 and 58950 <= c_[1] <= 59750 and abs(c_[2] - 15136) < 80)(mid(t_))]
joined = [k for k in landing if k in seen]
say('navmesh: door triangle %s, %d triangles reach it; landing triangles %d, of them joined to the door %d'
    % (door_tri, len(seen), len(landing), len(joined)))
bad = []
if res['picked'] < res['spots']:
    bad.append('door picked at %d of %d' % (res['picked'], res['spots']))
if len(leaks) > 1:
    bad.append('%d lines pass through the doorway' % len(leaks))
if [b for b in mine if 'blocked' in b['why'] or 'inside' in b['why']]:
    bad.append('the arrival out of the Vault is in something')
if left:
    bad.append('%d foliage or drill triangles still in the swept space' % left)
if still:
    bad.append('%d placed things in the swept space' % len(still))
if door_tri is None or not landing or len(joined) < len(landing) * 0.9:
    bad.append('the landing and the door are not one piece of navmesh (%d of %d)' % (len(joined), len(landing)))
say('CHECKS: ' + ('all good' if not bad else 'PROBLEMS: ' + '; '.join(bad)))
