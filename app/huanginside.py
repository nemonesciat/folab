"""The Huáng's halls opened (the user, 22 Nov 2026: "Yes, make insides"): each hall settlers.py stood in their courtyards
gets a real door where its door was painted, and a place of the mod's own behind it, in their style (huangset's rooms
and furniture), lived in and cared for.

Which hall is what (`ROLES`): the red-roofed hall nearest the freighter is the elders' hall (an audience room with its
dais, their rooms behind); the plain hall farthest from it, out by the maize, is the granary; every other hall is a
family's home (living room with the family altar, sleeping room, kitchen). Homes differ one from the next (`variant`:
mirrored, the quilts' colours, a screen, a scroll, a rug).

    ops(gd, pr)                 (ops, report): one Undo. The halls swapped for huangset's hall with a doorway (same spot,
                                same frame), each door stood flat on the hall's front, the places made (CELL copied from
                                `LIGHT_FROM` for its sound and image space, dry, its own warm light, owned by the
                                Huáng's faction when the mod has it), furnished, lit, doors linked both ways: in front
                                of the inside door facing in, and a step out on the porch facing out. Names: the places
                                are '$hgN', their doors '$hgNo' (outside) and '$hgNx' (inside).
    walk(gd, place)             each plan walked from its real collision before any navmesh (walkcheck): from the
                                arrival inside to the middle of every room and every bed's and chair's side.
    navmesh_ops(gd, pr, names)  after ops are applied: each place's navmesh.

Places' frame (huangset): floor at z 0, the inside door's back on y 0, the rooms in +y."""
import math
import random

import huangset as HS
import placewater
import recordio

PREFIX = 'FOLabHuang'
LIGHT_FROM = 'GSDocMitchellHouse'       # (a lived-in game home: its sound, music and image space)
DOOR_FROM = 'NVGoodSpringsHomeExtDoor'  # (a wooden house door's sounds)
LAMP_FROM = 'LamplightInteriorWarm'
LAMP = {'Radius': 420, 'Red': 255, 'Green': 186, 'Blue': 112}
AMBIENT = (70, 56, 44)                  # (the rooms' own ambient: warm, the lanterns do the rest)
CHEST_FROM = 'NVDLC02LootClothesHouseCabinet01Old'      # (a household's clothes)
JAR_FROM = 'NVDLC02ClayPot01FRUITGRAIN'                 # (Honest Hearts' pots of fruit and grain)
FACTION = 'FOLabHuangFaction'           # (factionfolk's: the places are theirs, so taking from them is stealing)
ARRIVE_IN = 110.0                       # (in from the inside door)
ARRIVE_OUT = 110.0                      # (out on the porch from the outside door)
DOOR_Z = 40.0                           # (the hall's platform: the door's foot over the hall's origin)
LANTERN_Z = HS.H - HS.LANTERN_DROP - 58.0
LIGHT_Z = LANTERN_Z + 30.0
TAU = 2 * math.pi
# headings: a piece's front (-y) towards...
TO_DOOR, TO_BACK, TO_PX, TO_NX = 0.0, math.pi, 1.5 * math.pi, 0.5 * math.pi
# a chair faces +y at 0 (the game's): facing...
SIT_PY, SIT_NY, SIT_PX, SIT_NX = 0.0, math.pi, 0.5 * math.pi, 1.5 * math.pi
CHAIR_Z = -HS.SEATS['chair'][2]


def _home(v):
    """A family's home: [(piece, x, y, z, heading)], lights [(x, y)], in the place's frame. v: `variant`."""
    D, S = HS.HOME_D, HS.HOME_SPLIT
    out = [
        # the living room: the altar facing the door, a scroll over it; the table and stools; two chairs by a table
        ('huang_altar', 0.0, S - 26.0, 0.0, TO_DOOR),
        ('huang_scroll', 0.0, S - 1.0, 122.0, TO_DOOR),
        ('huang_table', -300.0, 170.0, 0.0, TO_DOOR),
        ('huang_tea', -300.0, 170.0, 80.0, 0.3),
        ('huang_stool', -370.0, 170.0, 0.0, 0.0), ('huang_stool', -230.0, 170.0, 0.0, 0.0),
        ('huang_stool', -300.0, 100.0, 0.0, 0.0), ('huang_stool', -300.0, 240.0, 0.0, 0.0),
        ('huang_table', 330.0, 170.0, 0.0, TO_DOOR),
        ('huang_chair', 252.0, 170.0, CHAIR_Z, SIT_PX), ('huang_chair', 408.0, 170.0, CHAIR_Z, SIT_NX),
        ('huang_cabinet', -472.0, 270.0, 0.0, TO_PX),
        # the sleeping room: the bed's head on the back wall, a chest, the wash stand
        (v['bed'], -255.0, D - 88.0, 0.0, 0.0),
        ('huang_chest', -470.0, 420.0, 0.0, TO_PX),
        ('huang_basin', -60.0, D - 50.0, 0.0, 0.0),
        # the kitchen: the range on the back wall, shelves, jars, baskets, a table
        ('huang_stove', 230.0, D - 46.0, 0.0, TO_DOOR),
        ('huang_shelf', 478.0, 470.0, 0.0, TO_NX),
        ('huang_jar', 55.0, D - 40.0, 0.0, 0.0), ('huang_jar', 118.0, D - 36.0, 0.0, 0.6),
        ('huang_baskets', 432.0, D - 56.0, 0.0, TO_DOOR),
        ('huang_table', 120.0, 470.0, 0.0, TO_DOOR),
        ('huang_stool', 52.0, 470.0, 0.0, 0.0), ('huang_stool', 188.0, 470.0, 0.0, 0.0),
    ]
    if v['rug']:
        out.append(('huang_rug', -300.0, 170.0, 0.0, 0.0))
    if v['screen']:
        out.append(('huang_screen', 400.0, 300.0, 0.0, TO_DOOR))
    if v['scroll2']:
        out.append(('huang_scroll', 499.0, 280.0, 110.0, TO_NX))
    lights = [(-250.0, 170.0), (250.0, 170.0), (-255.0, 470.0), (255.0, 480.0)]
    return out, lights


def _elders():
    D, S = HS.ELDER_D, HS.ELDER_SPLIT
    up = HS.DAIS_UP
    out = [
        # the audience room: three chairs on the dais facing the door, stools with tea between, benches down the sides,
        # a rug before the dais, scrolls on the side walls, jars in its back corners
        ('huang_chair', -110.0, 545.0, up + CHAIR_Z, SIT_NY), ('huang_chair', 0.0, 545.0, up + CHAIR_Z, SIT_NY),
        ('huang_chair', 110.0, 545.0, up + CHAIR_Z, SIT_NY),
        ('huang_stool', -55.0, 565.0, up, 0.0), ('huang_stool', 55.0, 565.0, up, 0.0),
        ('huang_tea', -55.0, 565.0, up + 46.0, 0.2), ('huang_tea', 55.0, 565.0, up + 46.0, -0.4),
        ('huang_bench', -250.0, 300.0, 0.0, 0.0), ('huang_bench', 250.0, 300.0, 0.0, 0.0),
        ('huang_rug', 0.0, 300.0, 0.0, 0.0),
        ('huang_scroll', -699.0, 150.0, 110.0, TO_PX), ('huang_scroll', -699.0, 500.0, 110.0, TO_PX),
        ('huang_scroll', 699.0, 150.0, 110.0, TO_NX), ('huang_scroll', 699.0, 500.0, 110.0, TO_NX),
        ('huang_jar', -650.0, 590.0, 0.0, 0.0), ('huang_jar', 650.0, 590.0, 0.0, 0.0),
        # the elders' rooms: a bed each, a cabinet, a chest
        ('huang_bed_red', -450.0, D - 88.0, 0.0, 0.0),
        ('huang_cabinet', -672.0, 760.0, 0.0, TO_PX),
        ('huang_chest', -278.0, 720.0, 0.0, TO_NX),
        ('huang_bed_green', 450.0, D - 88.0, 0.0, 0.0),
        ('huang_cabinet', 672.0, 760.0, 0.0, TO_NX),
        ('huang_chest', 278.0, 720.0, 0.0, TO_PX),
        # the study between them, the eldest's: the desk and its chair, a cabinet, a bed
        ('huang_desk', -175.0, 760.0, 0.0, TO_PX),
        ('huang_chair', -112.0, 760.0, CHAIR_Z, SIT_NX),
        ('huang_cabinet', 178.0, 720.0, 0.0, TO_NX),
        ('huang_bed', 40.0, D - 88.0, 0.0, 0.0),
    ]
    lights = [(0.0, 120.0), (0.0, 330.0), (-350.0, 300.0), (350.0, 300.0), (-470.0, 850.0), (470.0, 850.0), (0.0, 850.0)]
    return out, lights


def _granary():
    D = HS.STORE_D
    out = [
        ('huang_bin', -300.0, D - 56.0, 0.0, TO_DOOR), ('huang_bin', 0.0, D - 56.0, 0.0, TO_DOOR), ('huang_bin', 300.0, D - 56.0, 0.0, TO_DOOR),
        ('huang_jar', -462.0, 90.0, 0.0, 0.0), ('huang_jar', -462.0, 160.0, 0.0, 0.7), ('huang_jar', -462.0, 450.0, 0.0, 1.3),
        ('huang_jar', -400.0, 470.0, 0.0, 2.1),
        ('huang_sacks', 300.0, 110.0, 0.0, 0.2), ('huang_sacks', -250.0, 330.0, 0.0, 2.9), ('huang_sacks', 260.0, 380.0, 0.0, 1.6),
        ('huang_maize_rack', 482.0, 200.0, 0.0, TO_NX), ('huang_maize_rack', 482.0, 450.0, 0.0, TO_NX),
        ('huang_baskets', -200.0, 70.0, 0.0, 0.0),
        ('huang_table_long', -250.0, 200.0, 0.0, TO_DOOR),
        ('huang_bench', -420.0, 300.0, 0.0, 0.0),
        ('huang_maize_strings', -300.0, D - 1.0, 130.0, TO_DOOR), ('huang_maize_strings', 0.0, D - 1.0, 130.0, TO_DOOR),
        ('huang_maize_strings', 300.0, D - 1.0, 130.0, TO_DOOR),
    ]
    lights = [(-250.0, 320.0), (250.0, 320.0), (0.0, 120.0)]
    return out, lights


def variant(n):
    """The n'th home's differences from the others."""
    rng = random.Random(4410 + n)
    return {'mirror': n % 2 == 1, 'bed': ('huang_bed', 'huang_bed_red', 'huang_bed_green')[n % 3],
            'rug': rng.random() < 0.7, 'screen': n % 2 == 0, 'scroll2': rng.random() < 0.5}


SHELLS = {'home': 'huang_home', 'elders': 'huang_elders', 'granary': 'huang_granary'}
NAMES = {'home': 'Huang Home', 'elders': 'Elders\' Hall', 'granary': 'Granary'}
EDIDS = {'home': 'Home%02d', 'elders': 'EldersHall', 'granary': 'Granary'}


def plan(role, n=0):
    """(shell piece, [(piece, x, y, z, heading)], lights [(x, y)]) for a place."""
    if role == 'elders':
        things, lights = _elders()
    elif role == 'granary':
        things, lights = _granary()
    else:
        v = variant(n)
        things, lights = _home(v)
        if v['mirror']:          # (the home's shell is the same either way round)
            things = [(p, -x, y, z, (-h) % TAU) for p, x, y, z, h in things]
            lights = [(-x, y) for x, y in lights]
    return SHELLS[role], things, lights


# ---------- which hall is what ----------

def halls(gd, pr):
    """[{'cell', 'ref', 'p', 's', 'red', 'depth', 'piece'}] of settlerset's halls the mod stands (outside)."""
    want = {}
    for k, rec in pr.records.items():
        if k.startswith('+') and rec.get('type') == 'STAT':
            e = recordio.field(rec, 'EDID')
            if e in HS.HALLS:
                want[k] = e
    out = []
    for ck, c in pr.cells.items():
        if ck.startswith('+'):
            continue
        for rk, r in (c.get('refs') or {}).items():
            if r.get('removed') or r.get('base') not in want or not r.get('p'):
                continue
            e = want[r['base']]
            piece, depth = HS.HALLS[e]
            out.append({'cell': ck, 'ref': rk, 'p': r['p'], 's': r.get('s', 1.0), 'red': e.endswith('Red'), 'depth': depth, 'piece': piece})
    return sorted(out, key=lambda h: h['ref'])


def _freighter(gd, pr):
    for k, rec in pr.records.items():
        if k.startswith('+') and recordio.field(rec, 'EDID') == 'FOLabSettlerFreighter':
            for ck, c in pr.cells.items():
                for rk, r in (c.get('refs') or {}).items():
                    if r.get('base') == k and not r.get('removed') and r.get('p'):
                        return r['p'][:2]
    return None


def roles(gd, pr, found):
    """{hall ref: role}: the red hall nearest the freighter the elders', the plain hall farthest from it the granary."""
    ship = _freighter(gd, pr) or (sum(h['p'][0] for h in found) / len(found), sum(h['p'][1] for h in found) / len(found))
    d = lambda h: math.hypot(h['p'][0] - ship[0], h['p'][1] - ship[1])
    out = {h['ref']: 'home' for h in found}
    reds = sorted([h for h in found if h['red']], key=d)
    plain = sorted([h for h in found if not h['red']], key=d)
    if reds:
        out[reds[0]['ref']] = 'elders'
    if plain:
        out[plain[-1]['ref']] = 'granary'
    return out


# ---------- records ----------

def _game(gd, edid, tag):
    fid = next((f for f, (_i, r) in gd.forms.items() if r.tag == tag and gd.edid(f) == edid), None)
    if fid is None:
        raise ValueError('the game files lack %s %s' % (tag, edid))
    return fid


def _set_bounds(rec, box):
    for s in rec['subs']:
        if s['tag'] == 'OBND':
            for f, v in zip([f for f in s['fields'] if 'name' in f], box):
                f['value'] = int(v)


def _files(pr, made):
    import os
    import library
    root = library.assets_dir(pr)
    for rel, data in made['files'].items():
        full = os.path.join(root, rel)
        if not os.path.isfile(full) or open(full, 'rb').read() != data:
            library._put(root, rel, data)


def _mine(pr, edid, rtype):
    for k, rec in pr.records.items():
        if k.startswith('+') and rec.get('type') == rtype and recordio.field(rec, 'EDID') == edid:
            return k
    return None


KEEP_FROM = {'DOOR': ('EDID', 'OBND', 'FULL', 'MODL', 'SNAM', 'ANAM', 'FNAM'), 'FURN': ('EDID', 'OBND', 'FULL', 'MODL', 'MNAM')}
SEAT_OF = {'huang_chair': 'chair', 'huang_bench': 'bench', 'huang_bed': 'bed', 'huang_bed_red': 'bed', 'huang_bed_green': 'bed'}
CONT_OF = {'huang_chest': CHEST_FROM, 'huang_jar': JAR_FROM}


def piece_record(gd, piece, made):
    """The mod's record for a piece: a FURN for what is sat or lain on (the game furniture it copies, its markers), a
    CONT for chests and jars (the game container it copies: its contents), the DOOR (a house door's sounds), else a STAT."""
    edid = HS.PIECES[piece]['edid']
    model = made['mesh'][7:]
    if piece == 'huang_door':
        rtype, src = 'DOOR', DOOR_FROM
    elif piece in SEAT_OF:
        rtype, src = 'FURN', HS.SEATS[SEAT_OF[piece]][0]
    elif piece in CONT_OF:
        rtype, src = 'CONT', CONT_OF[piece]
    else:
        import modelsets
        return 'STAT', modelsets._static(edid, model, made['box'], modelsets.VWD if made.get('far') else 0)
    rec = recordio.load(gd, _game(gd, src, rtype))
    if rtype in KEEP_FROM:
        rec['subs'] = [s for s in rec['subs'] if s['tag'] in KEEP_FROM[rtype]]
    else:
        rec['subs'] = [s for s in rec['subs'] if s['tag'] not in ('MODT', 'SCRI')]
    recordio.set_field(rec, 'EDID', edid, label='Editor ID')
    recordio.set_field(rec, 'MODL', model, label='Model')
    _set_bounds(rec, made['box'])
    rec.pop('copied_from', None)
    return rtype, rec


def lamp_record(gd):
    rec = recordio.load(gd, _game(gd, LAMP_FROM, 'LIGH'))
    recordio.set_field(rec, 'EDID', PREFIX + 'LanternLight', label='Editor ID')
    for s in rec['subs']:
        if s['tag'] == 'DATA':
            for f in s['fields']:
                if f.get('name') in LAMP:
                    f['value'] = LAMP[f['name']]
    rec.pop('copied_from', None)
    return rec


def place_record(gd, pr, edid, full):
    rec = recordio.load(gd, _game(gd, LIGHT_FROM, 'CELL'))
    rec['subs'] = [s for s in rec['subs'] if s['tag'] not in ('XOWN', 'XRNK')]
    placewater.make_dry(rec)
    recordio.set_field(rec, 'EDID', edid, label='Editor ID')
    recordio.set_field(rec, 'FULL', full, label='Name')
    for s in rec['subs']:
        if s['tag'] == 'XCLL':
            for f in s['fields']:
                if f.get('name') in ('Ambient red', 'Ambient green', 'Ambient blue'):
                    f['value'] = AMBIENT[('Ambient red', 'Ambient green', 'Ambient blue').index(f['name'])]
        if s['tag'] == 'LNAM':
            for f in s['fields']:
                if f.get('name') == 'Flags':
                    f['value'] = int(f['value']) & ~1          # (its own ambient, not the template's)
    fac = _mine(pr, FACTION, 'FACT')
    if fac:
        at = next((i + 1 for i, s in enumerate(rec['subs']) if s['tag'] in ('XCLW', 'LNAM', 'LTMP', 'XCLL', 'DATA')), len(rec['subs']))
        rec['subs'].insert(at, {'tag': 'XOWN', 'kind': 'formid', 'label': 'Owner', 'value': fac})
    rec.pop('copied_from', None)
    return rec


# ---------- where things go ----------

def _turn(lx, ly, rz):
    c, s = math.cos(rz), math.sin(rz)
    return lx * c + ly * s, -lx * s + ly * c


def door_spot(h):
    """The hall's door: [x y z rx ry rz] outside (flat on its front, -y out), and the arrival a step out facing out."""
    bp, s = h['p'], h['s']
    tx, ty = _turn(0.0, -h['depth'] / 2.0 * s, bp[5])
    door = [round(bp[0] + tx, 2), round(bp[1] + ty, 2), round(bp[2] + DOOR_Z * s, 2), 0.0, 0.0, round(bp[5] % TAU, 5)]
    ox, oy = _turn(0.0, -ARRIVE_OUT, bp[5])
    arrive = [round(door[0] + ox, 2), round(door[1] + oy, 2), door[2], 0.0, 0.0, round((bp[5] + math.pi) % TAU, 5)]
    return door, arrive


INSIDE_DOOR = [0.0, 0.0, 0.0, 0.0, 0.0, math.pi]
ARRIVAL_IN = [0.0, ARRIVE_IN, 0.0, 0.0, 0.0, 0.0]


def ops(gd, pr):
    """(ops, report): see the module's docstring."""
    found = halls(gd, pr)
    if not found:
        raise ValueError('the mod has none of the settlers\' halls (settlers.py) to open')
    role = roles(gd, pr, found)
    out = []
    keys = {}

    def record(piece):
        if piece in keys:
            return keys[piece]
        made = HS.build(piece)
        _files(pr, made)
        rtype, rec = piece_record(gd, piece, made)
        k = _mine(pr, HS.PIECES[piece]['edid'], rtype)
        if k:
            keys[piece] = k
        else:
            out.append({'op': 'record_new', 'record': rec, 'name': 'huang_' + piece})
            keys[piece] = '$huang_' + piece
        return keys[piece]
    lamp = _mine(pr, PREFIX + 'LanternLight', 'LIGH')
    if not lamp:
        out.append({'op': 'record_new', 'record': lamp_record(gd), 'name': 'huang_lamp'})
        lamp = '$huang_lamp'
    door = record('huang_door')
    rep = {'places': [], 'halls': len(found)}
    n_home = 0
    for i, h in enumerate(found):
        r = role[h['ref']]
        n = n_home
        if r == 'home':
            n_home += 1
        shell, things, lights = plan(r, n)
        tag = 'hg%d' % i
        edid = PREFIX + (EDIDS[r] % (n + 1) if r == 'home' else EDIDS[r])
        if _mine(pr, edid, 'CELL'):
            raise ValueError('%s is already a place of the mod\'s: the halls are open already' % edid)
        # the hall: the same, with a doorway of its own
        out.append({'op': 'swap', 'cell': h['cell'], 'ref': h['ref'], 'base': record(h['piece'])})
        out.append({'op': 'record_new', 'record': place_record(gd, pr, edid, NAMES[r]), 'name': tag})
        cell = '$' + tag
        out.append({'op': 'add', 'cell': cell, 'base': record(shell), 'p': [0.0] * 6, 's': 1.0})
        for piece, x, y, z, hd in things:
            out.append({'op': 'add', 'cell': cell, 'base': record(piece), 'p': [round(x, 2), round(y, 2), round(z, 2), 0.0, 0.0, round(hd % TAU, 5)], 's': 1.0})
        for x, y in lights:
            out.append({'op': 'add', 'cell': cell, 'base': record('huang_lantern'), 'p': [x, y, LANTERN_Z, 0.0, 0.0, 0.0], 's': 1.0})
            out.append({'op': 'add', 'cell': cell, 'base': lamp, 'p': [x, y, LIGHT_Z, 0.0, 0.0, 0.0], 's': 1.0})
        spot, arrive = door_spot(h)
        out.append({'op': 'add', 'cell': h['cell'], 'base': door, 'p': spot, 's': h['s'], 'name': tag + 'o'})
        out.append({'op': 'add', 'cell': cell, 'base': door, 'p': list(INSIDE_DOOR), 's': 1.0, 'name': tag + 'x'})
        out.append({'op': 'tel', 'cell': h['cell'], 'ref': '$' + tag + 'o', 'tel': {'door': '$' + tag + 'x', 'p': list(ARRIVAL_IN)}})
        out.append({'op': 'tel', 'cell': cell, 'ref': '$' + tag + 'x', 'tel': {'door': '$' + tag + 'o', 'p': arrive}})
        rep['places'].append({'tag': tag, 'role': r, 'edid': edid, 'hall': h['ref'], 'cell': h['cell'], 'things': len(things), 'lights': len(lights),
                              'door': spot, 'arrive_out': arrive})
    return out, rep


# ---------- before any navmesh: the walk ----------

def items_of(role, n=0):
    """walkcheck items for a place's plan, and its goals [(label, (x, y, z))]."""
    shell, things, lights = plan(role, n)
    built = {}

    def nif(piece):
        if piece not in built:
            built[piece] = HS.build(piece)['nif']
        return built[piece]
    items = [{'nif': nif(shell), 'pos': (0.0, 0.0, 0.0), 'rot': (0.0, 0.0, 0.0), 'scale': 1.0, 'label': shell}]
    items.append({'nif': nif('huang_door'), 'pos': tuple(INSIDE_DOOR[:3]), 'rot': tuple(INSIDE_DOOR[3:]), 'scale': 1.0, 'label': 'door'})
    goals = []
    for piece, x, y, z, hd in things:
        items.append({'nif': nif(piece), 'pos': (x, y, z), 'rot': (0.0, 0.0, hd), 'scale': 1.0, 'label': piece})
        if piece in SEAT_OF:                    # (where someone gets on: the markers' spots, turned with the piece)
            for mx, my, mz, _o, _a, _b in HS.SEATS[SEAT_OF[piece]][1]:
                tx, ty = _turn(mx, my, hd)
                goals.append(('%s at %d,%d side' % (piece, x, y), (x + tx, y + ty, z + mz)))
    for name, (x0, y0, x1, y1) in HS.ROOMS[shell].items():
        goals.append(('middle of ' + name, ((x0 + x1) / 2.0, (y0 + y1) / 2.0, 0.0)))
    return items, goals


def walk(gd, role, n=0):
    import walkcheck
    items, goals = items_of(role, n)
    rep = walkcheck.walk(gd, items, ground=None, starts=[tuple(ARRIVAL_IN[:3])], goals=goals)
    return rep


def navmesh_ops(gd, pr, names, tags):
    """After ops are applied (names: project.names as they left them): each place's navmesh. ({'op': 'navmesh'} ops,
    {tag: report or why not})."""
    import navbuild
    out, rep = [], {}
    for t in tags:
        ck = names.get(t)
        if not ck:
            continue
        try:
            data, r = navbuild.generate(gd, pr, ck)
        except navbuild.NavError as e:
            rep[t] = str(e)
            continue
        out.append({'op': 'navmesh', 'cell': ck, 'mesh': data})
        rep[t] = r
    return out, rep


# ---------- who lives there ----------
# A Huáng who sleeps in a place walks to it at night (`SLEEP_AT`, for `SLEEP_FOR` hours) and lies in their bed; some spend
# a while at home by day too (sandboxing round their bed's room for `DAY_FOR` hours from the hour given). Both packages
# lead to the person's linked ref (the game's DefaultSleepAlwaysLinkedRef and DefaultSandboxLinkedMarker512, scheduled), so
# the bed is linked to their ref outside (XLKR) and kept loaded (persistent); their own packages follow these.
SLEEP_AT, SLEEP_FOR, DAY_FOR = 22, 8, 2
SLEEP_FROM, DAY_FROM = 'DefaultSleepAlwaysLinkedRef', 'DefaultSandboxLinkedMarker512'


def _pack(gd, src, edid, hour, hours):
    rec = recordio.load(gd, _game(gd, src, 'PACK'))
    recordio.set_field(rec, 'EDID', edid, label='Editor ID')
    for s in rec['subs']:
        if s['tag'] == 'PSDT':
            for f in s['fields']:
                if f.get('name') == 'Time':
                    f['value'] = int(hour)
                elif f.get('name') == 'Duration':
                    f['value'] = int(hours)
    rec.pop('copied_from', None)
    return rec


def _refs_of(pr, base, inside=None):
    out = []
    for ck, c in pr.cells.items():
        if inside is not None and ck != inside:
            continue
        for rk, r in (c.get('refs') or {}).items():
            if r.get('base') == base and not r.get('removed'):
                out.append((ck, rk, r))
    return sorted(out, key=lambda t: t[1])


# Who (the people session's Huáng, 22 Nov 2026: Folk, Farmers and Elders may take packages ahead of their own; the patrol
# and road Shouwei and Zhao Lei at his gate are left as they are): the elders in their hall, a family in each home, a
# farmer at the granary's bench in the afternoon.
WHO = [('FOLabHuangElder01', 'FOLabHuangEldersHall', 'huang_bed_red', 0, 13),
       ('FOLabHuangElder02', 'FOLabHuangEldersHall', 'huang_bed_green', 0, None),
       ('FOLabHuangElder03', 'FOLabHuangEldersHall', 'huang_bed', 0, None),
       ('FOLabHuangFolk01', 'FOLabHuangHome01', 'huang_bed', 0, 12),
       ('FOLabHuangFolk02', 'FOLabHuangHome02', 'huang_bed_red', 0, None),
       ('FOLabHuangFolk03', 'FOLabHuangHome03', 'huang_bed_green', 0, 15),
       ('FOLabHuangFolk04', 'FOLabHuangHome04', 'huang_bed', 0, None),
       ('FOLabHuangFarmer01', 'FOLabHuangGranary', 'huang_bench', 0, 16)]


def people_ops(gd, pr, who=WHO):
    """who: [(NPC_ editor ID, place editor ID, what they use there: a piece ('huang_bed', 'huang_bench'...), which of
    them in the place (0 the first by key), the hour they come home by day or None)]. (ops, report): one Undo, applied
    on its own (the packages' keys are taken as planned)."""
    out, new, rep = [], [], {'housed': [], 'skipped': []}
    packs = {}

    def pack(kind, hour):
        key = (kind, hour)
        if key not in packs:
            edid = PREFIX + ('SleepAtHome' if kind == 'sleep' else 'DayAtHome%02d' % hour)
            k = _mine(pr, edid, 'PACK')
            if not k:
                src, h, n = (SLEEP_FROM, SLEEP_AT, SLEEP_FOR) if kind == 'sleep' else (DAY_FROM, hour, DAY_FOR)
                k = '+%06X' % (pr.next_id + len(new))      # (the records are made first: their keys known now)
                new.append({'op': 'record_new', 'record': _pack(gd, src, edid, h, n), 'name': edid})
            packs[key] = k
        return packs[key]
    for npc, place, piece, nth, day in who:
        nk = _mine(pr, npc, 'NPC_')
        ck = _mine(pr, place, 'CELL')
        pk = next((k for k, rec in pr.records.items() if k.startswith('+') and recordio.field(rec, 'EDID') == HS.PIECES[piece]['edid']), None)
        if not (nk and ck and pk):
            rep['skipped'].append((npc, 'no NPC_, place or piece'))
            continue
        placed = [t for t in _refs_of(pr, nk) if not t[0].startswith('+')]
        things = _refs_of(pr, pk, inside=ck)
        if len(placed) != 1 or nth >= len(things):
            rep['skipped'].append((npc, 'placed %d times; %d of %s there' % (len(placed), len(things), piece)))
            continue
        ock, ork, orr = placed[0]
        if orr.get('link'):
            rep['skipped'].append((npc, 'already linked to %s' % orr['link']))
            continue
        _bc, brk, _br = things[nth]
        rec = __import__('copy').deepcopy(pr.records[nk])
        first = next((i for i, s in enumerate(rec['subs']) if s['tag'] == 'PKID'), None)
        if first is None:
            rep['skipped'].append((npc, 'has no packages of its own'))
            continue
        mine = ([pack('sleep', SLEEP_AT)] if piece.startswith('huang_bed') else []) + ([pack('day', day)] if day is not None else [])
        if not mine:
            rep['skipped'].append((npc, 'neither a bed nor an hour by day'))
            continue
        rec['subs'][first:first] = [{'tag': 'PKID', 'label': 'AI package', 'kind': 'F', 'value': k} for k in mine]
        out.append({'op': 'record', 'key': nk, 'record': rec})
        out.append({'op': 'persist', 'cell': ck, 'ref': brk})
        out.append({'op': 'ref_set', 'cell': ock, 'ref': ork, 'set': {'link': brk, 'persistent': True}})
        rep['housed'].append((npc, place, piece, nth, day))
    return new + out, rep
