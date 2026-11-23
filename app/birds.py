"""Waikiki's birds (the user, 23 Nov 2026: "make parrots or indigenous hawaiian birds using the crows in fnv"): FOLab's own
birds on the game's one bird, the Raven (NVCrRaven), as the game has it:

  skeleton   creatures\\NVRaven\\Skeleton.nif (CAT rig: 5 bones a wing, 2 tail, jaw), ragdoll of 3 bodies
  body       NVRaven.NIF: one skinned shape, 345 vertices, textures\\creatures\\raven\\Raven.dds (alpha tested) + _N
  moves      mtidle.kf (perched, 4.9 s), SpecialIdle_TurnLeft (looks round), SpecialIdle_FlyAway (6.4 s: the flight is
             in the animation, 2,780 out and 430 up, then it stops). No walk, hop or flying loop: a bird perches, looks
             round and flies off, nothing else.
  its ways   BlackbirdSinging: within 512 of the player or hit, it plays FlyAway, then Disable + MarkForDelete.

So a bird here is a copy of the Raven's record (flags Flies + Walks, aggression 0, the void critters' faction, its
takeoff and fly-away sounds) with its own body: NVRaven.NIF with its picture path changed (nifwrite), in the Raven's own
folder because the creature's model list (NIFZ) names bodies beside the skeleton, and a picture of FOLab's own painted
over the Raven's by body part (`labels`: every triangle of the body named by where it lies in the bind pose, so the
feathers' light and shade and the alpha are the Raven's). The bill keeps its shape (the 'i'iwi's curve can't be painted).
Base scale (BNAM) is the Raven's 2.5 for a bird about 70 long; ours are smaller.

A flock never goes for good: its birds have a persistent XMarker of their own as enable parent, opposite (`roost`,
placed disabled, so they show). A bird near the player (`FLUSH`) or hit plays FlyAway; `FLIGHT` seconds on, before the
flight's end would put it back on its perch, it enables the roost and the whole flock is gone. The quest's script
(`QUEST`) disables a roost again `BACK` days later once the player is `AWAY` from it: the flock is back.

Where (`spots`): honeycreepers ('i'iwi, 'apapane) in the trees of the ridges and valleys (land over `UPLAND`, far from
Waikiki's middle), parakeets in Waikiki's own trees (within `waikikilife.WAIKIKI_R`); a flock `FLOCK` birds in one
tree, flocks `APART`, at most `MOST` of a kind. Perched at the tree's crown (`PERCH` of its height, a step out from the
trunk): the Raven's Flies flag should keep one there; if the game drops it, it sits under its tree. Not yet seen in game.

    pictures(gd)            {kind: PIL RGBA image}  (numpy, PIL: a build step, as armourset)
    files(gd)               {path: bytes} for every kind
    ops(gd, pr, world)      (ops, report): records, script, quest, roosts and birds, one Undo
"""
import json
import math
import random

KINDS = {
    # name: (shown name, base scale, colours by part)
    'iiwi': ("'I'iwi", 0.9, {'head': (206, 34, 26), 'body': (214, 40, 30), 'belly': (220, 52, 36), 'wing': (24, 20, 20),
                             'tail': (22, 18, 18), 'bill': (226, 140, 100), 'leg': (206, 96, 66)}),
    'apapane': ("'Apapane", 0.85, {'head': (160, 16, 30), 'body': (168, 20, 34), 'belly': (176, 30, 40), 'vent': (236, 234, 228),
                                   'wing': (26, 22, 22), 'tail': (24, 20, 20), 'bill': (30, 26, 26), 'leg': (36, 30, 30)}),
    'parakeet': ('Parakeet', 1.25, {'head': (132, 200, 80), 'body': (118, 190, 70), 'belly': (150, 206, 96),
                                    'wing': (84, 156, 56), 'tail': (86, 152, 112), 'bill': (198, 36, 40), 'leg': (128, 120, 118)}),
}
RAVEN = 'NVCrRaven'
RAVEN_BODY = 'meshes\\creatures\\nvraven\\nvraven.nif'
RAVEN_TEX = 'textures\\creatures\\raven\\Raven.dds'
BODY = 'meshes\\creatures\\nvraven\\folab%s_%s.nif'     # (mod, kind; beside the skeleton: NIFZ names bodies in its folder)
TEX = 'textures\\folab\\%s\\birds\\%s.dds'              # (mod, kind)
EYE = ((70, 103), 9)        # (the Raven's eye on its picture, 512 square: kept as the Raven's)
SIZE = 512

FLUSH = 700.0               # (the player this near: off it goes; the Raven's 512 was for crows on open ground)
FLIGHT = 5.5                # (seconds: the flight is 6.4, then the animation would set it back on the perch)
BACK = 0.25                 # (days, a quarter: six game hours)
AWAY = 6000.0               # (the flock comes back to its own tree only with the player this far: out of sight)
# each kind's call: a sound of its own, the Raven's fly-away call's settings (from the bird, 260 to 2,800 off, a little
# pitch shift) over one of the game's songbird folders (Honest Hearts' forest birds are these same files, but set to
# play at random spots round the listener). Idle sound (type 4) at CALL_CHANCE, as the game's critters have theirs.
# Chosen by folder, not by ear.
CALLS = {'iiwi': 'fx\\amb\\amb_desertdefault\\birds\\a\\', 'apapane': 'fx\\amb\\amb_desertdefault\\birds\\c\\',
         'parakeet': 'fx\\amb\\amb_desertdefault\\birds\\b\\'}
CALL_FROM = 'NPCRavenFlyAwayVox'
CALL_CHANCE = 50
SCRIPT = 'FOLabBirdScript'
QUEST = 'FOLabBirdRoosts'
QUEST_SCRIPT = 'FOLabBirdRoostsScript'
ROOST = 'FOLabRoost%02d'
MARKER = 'XMarker'

FLOCK = (2, 3)
APART = 8000.0              # (two cells: never thick)
MOST = {'iiwi': 7, 'apapane': 7, 'parakeet': 8}
UPLAND = 1200.0             # (ground this high or over: the ridges and the valleys' upper forest)
PERCH = 0.85
SEED = 23


# ---------- the picture ----------

def part_of(x, y, z):
    """The Raven's body in its bind pose (x forward, y left, z up; wings spread along y): which part a point is."""
    if abs(y) > 4.5:
        return 'wing'
    if x > 8.5:
        return 'bill'
    if x > 4:
        return 'ring' if x < 5.2 and z < 11.5 else 'head'
    if x < -7:
        return 'tail'
    if z < 4.5:
        return 'leg'
    if x < -3 and z < 8:
        return 'vent'
    if z < 8.5:
        return 'belly'
    return 'body'


FALLBACK = {'ring': 'head', 'vent': 'belly', 'belly': 'body'}


def labels(gd):
    """{part: bool mask} over the Raven's picture (SIZE square), from its body's triangles."""
    import numpy as np
    from PIL import Image, ImageDraw, ImageFilter
    import nif
    s = nif.mesh_from_nif(gd.read_file(RAVEN_BODY), placed=False)[0]
    P, uv, idx = s['p'], s['uv'], s['i']
    ims = {}
    for t in range(0, len(idx), 3):
        ks = idx[t:t + 3]
        part = part_of(*[sum(P[3 * k + a] for k in ks) / 3 for a in range(3)])
        if part not in ims:
            ims[part] = Image.new('L', (SIZE, SIZE), 0)
        ImageDraw.Draw(ims[part]).polygon([((uv[2 * k] % 1) * SIZE, (uv[2 * k + 1] % 1) * SIZE) for k in ks], fill=255)
    return {p: np.asarray(im.filter(ImageFilter.MaxFilter(3))) > 0 for p, im in ims.items()}


def _raven(gd):
    import numpy as np
    import dds
    w, h, px = dds.decode(gd.read_file(RAVEN_TEX), want=SIZE)[:3]
    assert (w, h) == (SIZE, SIZE), (w, h)
    return np.frombuffer(bytes(px), np.uint8).reshape(h, w, 4).astype(np.float32)


def picture(gd, kind, labs=None, raven=None):
    """The kind's picture: each part its colour, lit and shaded as the Raven's feathers are there (each texel's
    brightness over its part's middle brightness), the Raven's alpha and eye."""
    import numpy as np
    from PIL import Image
    labs = labs or labels(gd)
    rv = _raven(gd) if raven is None else raven
    lum = rv[..., :3].mean(axis=2)
    out = rv.copy()
    colours = KINDS[kind][2]
    done = np.zeros(lum.shape, bool)
    # (smaller parts last: a texel two parts share takes the smaller one's colour)
    for part in sorted(labs, key=lambda p: -labs[p].sum()):
        m = labs[part]
        col = colours.get(part) or colours.get(FALLBACK.get(part, ''), None) or colours.get(FALLBACK.get(FALLBACK.get(part, ''), ''), None)
        if col is None:
            continue
        mid = max(8.0, float(np.median(lum[m]))) if m.any() else 40.0
        shade = (np.clip(lum / mid, 0.5, 1.6) ** 0.7)[..., None]     # (the Raven's feather light, softened)
        dark = sum(col) < 120                       # (black feathers keep more of the Raven's own sheen)
        lit = np.array(col, np.float32)[None, None, :] * (shade if not dark else (0.6 + 0.4 * shade))
        if dark:
            lit = lit + 0.25 * rv[..., :3]
        out[..., :3] = np.where(m[..., None], np.clip(lit, 0, 255), out[..., :3])
        done |= m
    (ex, ey), er = EYE
    yy, xx = np.mgrid[0:SIZE, 0:SIZE]
    eye = (xx - ex) ** 2 + (yy - ey) ** 2 < er * er
    out[..., :3] = np.where(eye[..., None], rv[..., :3], out[..., :3])
    return Image.fromarray(out.astype(np.uint8), 'RGBA')


def pictures(gd):
    labs, rv = labels(gd), _raven(gd)
    return {k: picture(gd, k, labs, rv) for k in KINDS}


def raven_picture_path(raven):
    """The Raven body's picture path as its file spells it (its normal map stays the Raven's)."""
    import nifwrite
    return next(t['path'] for t in nifwrite.textures_in(raven) if t['path'].lower().endswith('raven.dds'))


def files(gd, slug):
    """{path under Data: bytes}: each kind's body (the Raven's with its picture path changed) and picture (DXT5)."""
    import dds
    import nifwrite
    raven = gd.read_file(RAVEN_BODY)
    old = raven_picture_path(raven)
    out = {}
    for k, im in pictures(gd).items():
        out[BODY % (slug, k)] = nifwrite.retexture(raven, {old: TEX % (slug, k)})
        out[TEX % (slug, k)] = dds.compress(dds.encode(im.size[0], im.size[1], im.tobytes(), cut=75))
    return out


def put_files(gd, pr):
    """The files among the mod's own (projects/<mod> assets/). Returns their paths."""
    import library
    root = library.assets_dir(pr)
    made = files(gd, library.slug(pr.name))
    for rel, data in made.items():
        library._put(root, rel, data)
    return sorted(made)


# ---------- records ----------

def _game(gd, tag, edid):
    got = [f for f, (_i, r) in gd.forms.items() if r.tag == tag and gd.edid(f) == edid]
    if not got:
        raise ValueError('the game has no %s %s' % (tag, edid))
    return min(got, key=lambda f: f >> 24)


def call(gd, kind):
    """The kind's call: the Raven's fly-away call's SOUN over its songbird folder."""
    import recordio
    rec = json.loads(json.dumps(recordio.load(gd, _game(gd, 'SOUN', CALL_FROM))))
    rec['src'] = ''
    for s in rec['subs']:
        if s['tag'] == 'EDID':
            s['value'] = 'FOLabBird%sCall' % kind.capitalize()
        elif s['tag'] == 'FNAM':
            s['value'] = CALLS[kind]
    return rec


def creature(gd, kind, script_key, slug, call_key=None):
    """The kind's CREA: the Raven's, its body, name, scale and script FOLab's own, its call as its idle sound."""
    import recordio
    shown, scale, _c = KINDS[kind]
    rec = json.loads(json.dumps(recordio.load(gd, _game(gd, 'CREA', RAVEN))))
    rec['src'] = ''
    if call_key:
        at = next(i for i, s in enumerate(rec['subs']) if s['tag'] == 'CSDT')
        t = next(s for s in rec['subs'] if s['tag'] == 'CSDT')
        i_ = next(s for s in rec['subs'] if s['tag'] == 'CSDI' and s['value'])
        c_ = next(s for s in rec['subs'] if s['tag'] == 'CSDC')
        rec['subs'][at:at] = [dict(t, fields=[dict(t['fields'][0], value=4)]), dict(i_, value=call_key),
                              dict(c_, fields=[dict(c_['fields'][0], value=CALL_CHANCE)])]
    for s in rec['subs']:
        if s['tag'] == 'EDID':
            s['value'] = 'FOLabBird%s' % kind.capitalize()
        elif s['tag'] == 'FULL':
            s['value'] = shown
        elif s['tag'] == 'NIFZ':
            s['value'] = (BODY % (slug, kind)).rsplit(chr(92), 1)[1] + chr(0)
        elif s['tag'] == 'SCRI':
            s['value'] = script_key
        elif s['tag'] == 'BNAM':
            s['fields'][0]['value'] = scale
        elif s['tag'] == 'OBND':
            box = (-13, -9, 0, 13, 9, 18)            # (the Tier0 Raven's, at base scale 2.5)
            s['fields'] = [dict(f, value=int(round(v * scale / 2.5))) for f, v in zip(s['fields'], box)]
    return rec


def bird_script():
    return '\r\n'.join([
        'scn %s' % SCRIPT,
        '; FOLab: a bird of a flock. Near the player or hit it flies off; before the flight would set it back on its',
        '; perch it switches its roost on, and the flock (opposite to the roost) is gone until the roosts quest brings it back.',
        'float fFly',
        'short bFlying',
        'ref rRoost',
        '',
        'Begin OnHit',
        '\tif bFlying == 0',
        '\t\tPlayIdle NVRavenFlyAway',
        '\t\tset fFly to %.1f' % FLIGHT,
        '\t\tset bFlying to 1',
        '\tendif',
        'End',
        '',
        'Begin GameMode',
        '\tif GetDead',
        '\t\treturn',
        '\tendif',
        '\tif bFlying == 0',
        '\t\tif GetDistance Player < %d' % FLUSH,
        '\t\t\tPlayIdle NVRavenFlyAway',
        '\t\t\tset fFly to %.1f' % FLIGHT,
        '\t\t\tset bFlying to 1',
        '\t\tendif',
        '\telse',
        '\t\tset fFly to fFly - GetSecondsPassed',
        '\t\tif fFly <= 0',
        '\t\t\tset bFlying to 0',
        '\t\t\tset rRoost to GetParentRef',
        '\t\t\tif rRoost',
        '\t\t\t\trRoost.Enable',
        '\t\t\telse',
        '\t\t\t\tDisable',
        '\t\t\tendif',
        '\t\tendif',
        '\tendif',
        'End', ''])


def quest_script(n):
    """Every roost switched off again (its flock back) BACK days after it went on, once the player is AWAY."""
    lines = ['scn %s' % QUEST_SCRIPT, '; FOLab: brings flown flocks back (birds.py).']
    lines += ['float fGone%02d' % k for k in range(1, n + 1)]
    lines += ['', 'Begin GameMode']
    for k in range(1, n + 1):
        r, v = ROOST % k, 'fGone%02d' % k
        lines += ['\tif %s.GetDisabled == 0' % r,
                  '\t\tif %s == 0' % v,
                  '\t\t\tset %s to GameDaysPassed' % v,
                  '\t\telseif GameDaysPassed - %s >= %.2f' % (v, BACK),
                  '\t\t\tif %s.GetDistance Player > %d' % (r, AWAY),
                  '\t\t\t\tset %s to 0' % v,
                  '\t\t\t\t%s.Disable' % r,
                  '\t\t\tendif',
                  '\t\tendif',
                  '\tendif']
    lines += ['End', '']
    return '\r\n'.join(lines)


# ---------- where ----------

# trees a bird sits in, by editor ID: honeycreepers in the forest's trees; parakeets in the town's palms, banyans and
# shade trees
FOREST = ('FOLabJungleTree', 'FOLabJungleTreeB', 'FOLabJungleTreeC', 'FOLabJungleBanyan', 'FOLabJungleBanyanB',
          'FOLabJungleBanyanC', 'FOLabGreenTreeA1', 'FOLabGreenTreeA2', 'FOLabGreenTreeA3', 'FOLabGreenTreeA4',
          'FOLabGreenTreeA5', 'FOLabGreenTreeA6', 'FOLabGreenTreeB1', 'FOLabGreenTreeB2', 'FOLabGreenTreeB3',
          'FOLabGreenTreeF1', 'FOLabGreenTreeF2')
TOWN = ('NVQueenPalm01', 'FOLabBeachPalmTall', 'NVDatePalm01', 'FOLabJungleBanyan', 'FOLabJungleBanyanB',
        'FOLabJungleBanyanC', 'FOLabGreenTreeA1', 'FOLabGreenTreeA2', 'FOLabGreenTreeB1', 'FOLabGreenTreeB2')
PALM = ('Palm',)            # (a palm's birds sit on the fronds at the top, close in)
WHERE = {'iiwi': 'forest', 'apapane': 'forest', 'parakeet': 'town'}
LOW_TREE = 300.0            # (a tree under this tall isn't one a bird sits up in)


def _edid(gd, pr, key):
    import recordio
    if key.startswith('+'):
        r = pr.records.get(key)
        return recordio.field(r, 'EDID') if r else ''
    try:
        f = gd.from_key(key)
    except ValueError:
        return ''
    return gd.edid(f) if f in gd.forms else ''


def _bounds(gd, pr, key):
    import townbuild
    if key.startswith('+'):
        r = pr.records.get(key)
        s = next((s for s in (r or {}).get('subs', ()) if s['tag'] == 'OBND'), None)
        return [f['value'] for f in s['fields']] if s else None
    return townbuild.obnd(gd, key)


def trees(gd, pr, world):
    """[(x, y, z, scale, bounds, edid, cell)] of every tree a bird could sit in, in the world's cells."""
    cells = {gd.key(c) for c in gd.grid(world).values()}
    want = set(FOREST) | set(TOWN)
    base_ok, out = {}, []
    for ck, c in pr.cells.items():
        if ck not in cells:
            continue
        for _rk, r in c.get('refs', {}).items():
            b, p = r.get('base'), r.get('p')
            if r.get('removed') or not b or not p:
                continue
            if b not in base_ok:
                e = _edid(gd, pr, b)
                o = _bounds(gd, pr, b) if e in want else None
                base_ok[b] = (e, o) if o else None
            got = base_ok[b]
            if got:
                out.append((p[0], p[1], p[2], float(r.get('s', 1.0)), got[1], got[0], ck))
    return out


def spots(gd, pr, world, seed=SEED):
    """{kind: [(cell, [(x, y, z, yaw)])] a flock in its tree's cell}: flocks in trees of their place, APART, at most MOST each."""
    import roadgen
    import waikikilife
    rnd = random.Random(seed)
    _hot, mid = waikikilife.middle(pr)
    g = roadgen.Ground(gd, pr, world)
    every = sorted(trees(gd, pr, world))
    rnd.shuffle(every)
    taken, out = [], {k: [] for k in KINDS}
    for x, y, z, s, o, e, ck in every:
        tall = (o[5] - o[2]) * s
        if tall < LOW_TREE:
            continue
        far = math.hypot(x - mid[0], y - mid[1])
        place = 'town' if far < waikikilife.WAIKIKI_R and e in TOWN else None
        if place is None and e in FOREST and far > waikikilife.WAIKIKI_R:
            h = g.at(x, y)
            if h is not None and h >= UPLAND:
                place = 'forest'
        if place is None:
            continue
        kinds = [k for k, w in WHERE.items() if w == place and len(out[k]) < MOST[k]]
        if not kinds or any(math.hypot(x - a, y - b) < APART for a, b in taken):
            continue
        kind = rnd.choice(kinds)
        palm = any(w in e for w in PALM)
        half = max(abs(o[0]), abs(o[1]), abs(o[3]), abs(o[4])) * s
        up = z + (0.94 if palm else PERCH) * o[5] * s
        flock, turn = [], rnd.uniform(0, math.tau)
        for n in range(rnd.randint(*FLOCK)):
            a = turn + n * math.tau / 4.0 + rnd.uniform(-0.4, 0.4)
            out_by = (0.15 if palm else 0.35) * half * rnd.uniform(0.8, 1.2)
            flock.append((round(x + math.sin(a) * out_by, 1), round(y + math.cos(a) * out_by, 1),
                          round(up + rnd.uniform(-0.05, 0.03) * o[5] * s, 1), round(rnd.uniform(0, math.tau), 4)))
        out[kind].append((ck, flock))
        taken.append((x, y))
    return out


# ---------- the ops ----------

def ops(gd, pr, world, seed=SEED):
    """(ops, report): the bird script, the kinds, the roosts' script and quest, then roosts and birds. One Undo; nothing
    is changed here. Files are put_files' (call it too)."""
    import api_quests as aq
    import api_scripts
    import library
    import newgame
    import questrec as qr
    import recordio
    if any(r.get('type') == 'QUST' and recordio.field(r, 'EDID') == QUEST for r in pr.records.values()):
        raise ValueError('the mod already has %s' % QUEST)
    slug = library.slug(pr.name)
    where = spots(gd, pr, world, seed)
    flocks = [(k, f) for k in KINDS for f in where[k]]
    n_roosts = len(flocks)
    n_birds = sum(len(f) for _k, (_c, f) in flocks)
    # keys, in the order the ops make them: bird script, calls, kinds, roosts' script, quest, roosts, birds
    nk = len(KINDS)
    keys = aq._reserve(pr, 1 + 2 * nk + 2 + n_roosts + n_birds)
    script_key = keys[0]
    call_key = dict(zip(KINDS, keys[1:1 + nk]))
    kind_key = dict(zip(KINDS, keys[1 + nk:1 + 2 * nk]))
    qs_key, quest_key = keys[1 + 2 * nk], keys[2 + 2 * nk]
    roost_keys = keys[3 + 2 * nk:3 + 2 * nk + n_roosts]
    sc = api_scripts.scripts()
    c = sc.compile(bird_script(), script_key, 'object')
    if not hasattr(c, 'subrecords'):
        raise ValueError('the bird script does not compile: %s' % (c,))
    out = [{'op': 'record_new', 'record': sc._record_of(c, SCRIPT)}]
    out += [{'op': 'record_new', 'record': call(gd, k)} for k in KINDS]
    out += [{'op': 'record_new', 'record': creature(gd, k, script_key, slug, call_key[k])} for k in KINDS]
    extra = {rk: {'type': 'REFR', 'flags': newgame.PERSISTENT, 'subs': [{'tag': 'EDID', 'label': 'Editor ID', 'kind': 'z', 'value': ROOST % (n + 1)}]}
             for n, rk in enumerate(roost_keys)}
    quest = qr.quest_record({'edid': QUEST, 'script': qs_key, 'name': '', 'flags': {'start_enabled': True},
                             'priority': 50, 'delay': 5.0, 'stages': [], 'objectives': []})
    extra[quest_key] = quest
    c2 = sc.compile(quest_script(n_roosts), qs_key, 'quest', extra)
    if not hasattr(c2, 'subrecords'):
        raise ValueError('the roosts script does not compile: %s' % (c2,))
    out += [{'op': 'record_new', 'record': sc._record_of(c2, QUEST_SCRIPT)}, {'op': 'record_new', 'record': quest}]
    marker = gd.key(_game(gd, 'STAT', MARKER))
    birds, report = [], {k: {'flocks': 0, 'birds': 0} for k in KINDS}
    for n, ((k, (cell, flock)), rk) in enumerate(zip(flocks, roost_keys)):
        if not cell:
            raise ValueError('a flock with no cell')
        x = sum(b[0] for b in flock) / len(flock)
        y = sum(b[1] for b in flock) / len(flock)
        z = min(b[2] for b in flock)
        out.append({'op': 'add', 'cell': cell, 'base': marker, 'p': [round(x, 1), round(y, 1), round(z, 1), 0.0, 0.0, 0.0],
                    's': 1.0, 'extra': {'persistent': True, 'edid': ROOST % (n + 1), 'props': {'disabled': True}}})
        for b in flock:
            birds.append({'op': 'add', 'cell': cell, 'base': kind_key[k], 'p': [b[0], b[1], b[2], 0.0, 0.0, b[3]],
                          's': 1.0, 'extra': {'props': {'parent': {'ref': rk, 'opposite': True, 'popin': False}}}})
        report[k]['flocks'] += 1
        report[k]['birds'] += len(flock)
    out += birds
    return out, {'keys': keys, 'kinds': kind_key, 'script': script_key, 'quest': quest_key, 'roosts': n_roosts,
                 'birds': n_birds, 'by_kind': report}


def build(server):
    """The birds into the open mod: files, then one Undo. Returns the report."""
    gd, pr = server.GD, server.PR
    world = next(w for w in gd.worlds() if gd.edid(w) == 'FOLabWaikiki')
    o, rep = ops(gd, pr, world)
    rep['files'] = put_files(gd, pr)
    made = server.edit("Waikiki's birds", o)['made']
    assert made == rep['keys'], ('keys not as reserved', made[:5], rep['keys'][:5])
    return rep
