"""Waikiki's collectibles (the user, 25 Nov 2026, docs/waikiki-decisions.md): seven dashboard hula dolls, each +1 to one
SPECIAL for good (Waikiki's bobbleheads: the 1950s car-dash bobbing hula girl, kitsch, not sacred figures), and a secret
set of Huang jade charms, each +5 to one skill ("Skills, +5 each"), one per New Vegas skill as Fallout 3's skill
bobbleheads. Collecting a whole set gives a hidden reward of its own ("a hidden perk for each collecting all").

- **Models** (FOLab's own, closed solids; `doll`, `charm`): a doll on a sprung base, grass skirt, lei, a flower in her
  hair, each in her own pose and colours (`DOLLS`); a charm a small carved jade pendant on a red cord, in five carvings
  (bi disc, gourd, fish, cicada, coin) and four jades (`CHARMS`). Loose items: one box of collision (nifmake.build_dropped).
- **Records:** a MISC each (the game's coffee mug's layout, weightless, worth nothing to a trader), a script each
  (OnAdd player): the first time it reaches you, the stat goes up (ModAV: as Fallout 3's bobbleheads), a message, and the
  set's count; the set complete, its reward. The quest FOLabCollectibles keeps what was found (so dropping one and
  picking it up again gives nothing).
- **Set rewards** (abilities, added by the last find's script, `REWARDS`): all seven dolls, "Island Time" (+10 Action
  Points); all thirteen charms, "Jade Heart" (+3 Damage Threshold, and +10 Huang face, once).
  - Decided (the user, 25 Nov 2026: "Yes, as proposed"): Island Time is also +10% speed outdoors in the island's world.
- **Where** (`SPOTS`): places worth reaching for the dolls; Huang and hard places for the charms. Each rests on a
  real surface there (a table, desk, shelf, console, crate, a car's roof: lootplace.Seat on the placed things' own
  collision), the one farthest from the way in, `DOOR_CLEAR` from every door and arrival, `PEOPLE_CLEAR` from anyone
  standing. Nothing is hinted yet.

    plan(gd, pr)       (rows, skipped)
    ops(gd, pr, P)     (ops, report): one Undo; the models' and pictures' files go among the mod's own
"""
import json
import math
import re

import modelsets
import recordio
import texpaint as tp
from modelsets import look

LABEL = "Waikiki's collectibles"
SET = 'collect'
QUEST, QSCRIPT = 'FOLabCollectibles', 'FOLabCollectiblesScript'
SPECIAL = ['Strength', 'Perception', 'Endurance', 'Charisma', 'Intelligence', 'Agility', 'Luck']
SKILLS = ['Barter', 'EnergyWeapons', 'Explosives', 'Guns', 'Lockpick', 'Medicine', 'MeleeWeapons', 'Repair', 'Science', 'Sneak',
          'Speech', 'Survival', 'Unarmed']
SHOWN = {'EnergyWeapons': 'Energy Weapons', 'MeleeWeapons': 'Melee Weapons'}
DOLL_GAIN, CHARM_GAIN = 1, 5
# doll: (arms (left, right) as angles from hanging down, sideways; hips' lean; skirt; top and lei; flower)
DOLLS = {
    'Strength': ((150, 150), 0, 'straw', 'red', 'white'),          # (both arms up, a strongwoman's flex)
    'Perception': ((100, 20), 8, 'green', 'yellow', 'red'),        # (a hand shading her eyes)
    'Endurance': ((60, 60), -6, 'straw', 'blue', 'yellow'),        # (arms out, swaying)
    'Charisma': ((80, 120), 10, 'pink', 'white', 'pink'),          # (a wave and a smile)
    'Intelligence': ((30, 95), 0, 'green', 'purple', 'white'),     # (a finger raised)
    'Agility': ((110, 70), -12, 'straw', 'orange', 'red'),         # (mid-step, hips well over)
    'Luck': ((45, 135), 6, 'green', 'gold', 'yellow'),             # (one arm up for luck)
}
SKIRTS = {'straw': (196, 168, 96), 'green': (96, 150, 70), 'pink': (220, 130, 150)}
TOPS = {'red': (196, 40, 44), 'yellow': (236, 196, 50), 'blue': (50, 110, 200), 'white': (236, 232, 220), 'purple': (130, 70, 160),
        'orange': (232, 128, 40), 'gold': (210, 170, 60), 'pink': (232, 120, 160)}
CARVINGS = ['bi', 'gourd', 'fish', 'cicada', 'coin']
JADES = {'imperial': (40, 140, 80), 'celadon': (150, 190, 150), 'mutton': (220, 222, 200), 'spinach': (36, 90, 52)}
CHARMS = {s: (CARVINGS[i % len(CARVINGS)], list(JADES)[i % len(JADES)]) for i, s in enumerate(SKILLS)}
REWARDS = {'hula': ('FOLabIslandTime', 'Island Time', 'IncreaseActionPoints', 10,
                    "Every hula doll on the island is yours. The island's pace is yours now: +10 Action Points, and you move a little faster outdoors on the island."),
           'jade': ('FOLabJadeHeart', 'Jade Heart', 'IncreaseDamageThreshold', 3,
                    "Every jade charm is yours. The elders would call it a sign: +3 Damage Threshold, and the Huang think better of you.")}
JADE_FACE = 10
ISLAND_WORLD, ISLAND_SPEED = 'FOLabWaikiki', 10       # (Island Time's second effect: speed, only in the island's world)
GETINWORLDSPACE = 310
# where each goes: (place editor ID or ('near', map marker, radius), what to rest on: editor ID words)
SURFACE = r'Table|Desk|Counter|Shelf|Shelves|Dresser|Cabinet|Altar|Console|Crate|Bench|Footlocker|Locker|Trunk|Chest|Workbench|Bar\b|Stand'
SPOTS = {
    ('hula', 'Strength'): ('FOLabMissouriTurretTwo', SURFACE),
    ('hula', 'Perception'): (('near', 'Diamond Head Lookout', 1500.0), SURFACE + r'|Rock|Sign|Barricade|Sandbag'),
    ('hula', 'Endurance'): ('FOLabPelesPipe', SURFACE),
    ('hula', 'Charisma'): ('FOLabKahunaPalmsFloor5', SURFACE),
    ('hula', 'Intelligence'): ('FOLabMissouriPilotHouse', SURFACE),
    ('hula', 'Agility'): (('near', 'Pali Checkpoint', 3000.0), r'Car\d*Hulk|CarHulk|Car0|Truck|Bus|Van'),
    ('hula', 'Luck'): (('near', 'Kahala Reef', 7000.0), r'^Boat\d'),           # (the pirates' boats on the Kahala shore)
    ('jade', 'Speech'): ('FOLabFreighterHold', SURFACE),
    ('jade', 'Barter'): ('FOLabHuangGranary', SURFACE),
    ('jade', 'Medicine'): ('FOLabHuangHome01', SURFACE),
    ('jade', 'Survival'): ('FOLabHuangHome03', SURFACE),
    ('jade', 'Lockpick'): ('FOLabHuangEldersHall', SURFACE),
    ('jade', 'Science'): ('FOLabKaauVault', SURFACE),
    ('jade', 'Repair'): ('FOLabMissouriEngineRoom', SURFACE),
    ('jade', 'Explosives'): ('FOLabMissouri2ndDeck', SURFACE),
    ('jade', 'Unarmed'): ('FOLabPelesPipe', SURFACE),
    ('jade', 'Sneak'): ('FOLabKilaueaFloor4', SURFACE),
    ('jade', 'MeleeWeapons'): ('FOLabKilaueaFloor3', SURFACE),
    ('jade', 'Guns'): ('FOLabKahunaPalmsFloor4', SURFACE),
    ('jade', 'EnergyWeapons'): (('near', 'Wrecked freighter', 3000.0), SURFACE + r'|Wreck|Hull|Container'),
}
DOOR_CLEAR, PEOPLE_CLEAR, APART = 300.0, 150.0, 150.0
ON_TOP = 15.0                   # (resting this near the surface's top: on it, not on the floor beside it)


# ---------- pictures ----------
def _plain(colour, seed, grain=0.12, size=64):
    c = tp.Canvas(size, size)
    n = tp.Noise(seed, 8)
    c.paint(lambda x, y: (tp._shade(colour, 1.0 - grain / 2 + grain * n.at(x * 8.0 / size, y * 8.0 / size)), 0.5))
    return c


def _skirt(colour, seed):
    """Grass strands: thin vertical streaks, darker between."""
    c = tp.Canvas(64, 64)
    n = tp.Noise(seed, 16)

    def fn(x, y):
        s = 0.5 + 0.5 * math.sin(x * 1.9 + 3 * n.at(x / 8.0, 0.3))
        return tp._shade(colour, 0.7 + 0.35 * s), 0.3 + 0.5 * s
    c.paint(fn)
    return c


def _jade(colour, seed):
    """Jade: cloudy, veined, a little light in it."""
    c = tp.Canvas(64, 64)
    n = tp.Noise(seed, 6)
    m = tp.Noise(seed + 1, 20)

    def fn(x, y):
        cloud = n.at(x * 6.0 / 64, y * 6.0 / 64)
        vein = abs(m.at(x * 20.0 / 64, y * 20.0 / 64) - 0.5) < 0.04
        col = tp._mix(colour, (240, 246, 236), 0.25 * cloud)
        if vein:
            col = tp._shade(col, 0.82)
        return col, 0.6 + 0.2 * cloud
    c.paint(fn)
    return c


def _textures():
    T = {'collect/skin': lambda: _plain((214, 160, 120), 301, 0.08), 'collect/hair': lambda: _plain((28, 22, 20), 302, 0.2),
         'collect/base': lambda: _plain((196, 160, 70), 303, 0.3), 'collect/spring': lambda: _plain((170, 170, 176), 304, 0.25),
         'collect/cord': lambda: _plain((176, 30, 34), 305, 0.2), 'collect/gold': lambda: _plain((200, 166, 72), 306, 0.25)}
    for k, col in SKIRTS.items():
        T['collect/skirt_' + k] = (lambda col=col, k=k: _skirt(col, 310 + len(k)))
    for k, col in TOPS.items():
        T['collect/top_' + k] = (lambda col=col, k=k: _plain(col, 320 + len(k), 0.15))
    for k, col in JADES.items():
        T['collect/jade_' + k] = (lambda col=col, k=k: _jade(col, 340 + len(k)))
    return T


modelsets.TEXTURES.update(_textures())


# ---------- models ----------
def doll(stat):
    """A dashboard hula girl, about 14 units tall, standing on her base at the origin, facing -y."""
    (al, ar), lean, skirt, top, flower = DOLLS[stat]
    L = {'skin': look('collect/skin', tile=None), 'hair': look('collect/hair', tile=None), 'base': look('collect/base', tile=None),
         'spring': look('collect/spring', tile=None), 'skirt': look('collect/skirt_' + skirt, tile=None),
         'top': look('collect/top_' + top, tile=None), 'flower': look('collect/top_' + flower, tile=None)}
    hip = 5.0
    P = [{'shape': 'cylinder', 'r': 3.2, 'h': 1.0, 'sides': 14, 'look': 'base'},
         {'shape': 'cylinder', 'r': 0.7, 'h': 1.4, 'sides': 8, 'at': [0, 0, 1.0], 'look': 'spring'},
         {'shape': 'cylinder', 'r': 0.45, 'h': 2.4, 'sides': 6, 'at': [-0.6, 0, 1.6], 'look': 'skin'},
         {'shape': 'cylinder', 'r': 0.45, 'h': 2.4, 'sides': 6, 'at': [0.6, 0, 1.6], 'look': 'skin'},
         {'shape': 'cone', 'r': 2.6, 'r2': 1.3, 'h': 3.0, 'sides': 14, 'at': [0, 0, 2.6], 'turn': [0, lean, 0], 'look': 'skirt'},
         {'shape': 'cylinder', 'r': 1.25, 'r2': 1.0, 'h': 3.4, 'sides': 10, 'at': [0, 0, hip + 0.4], 'turn': [0, lean / 2, 0], 'look': 'skin'},
         {'shape': 'cylinder', 'r': 1.3, 'r2': 1.3, 'h': 0.9, 'sides': 10, 'at': [0, 0, hip + 1.9], 'turn': [0, lean / 2, 0], 'look': 'top'},
         {'shape': 'cylinder', 'r': 1.45, 'h': 0.45, 'sides': 12, 'at': [0, 0, hip + 3.3], 'look': 'flower'},
         {'shape': 'ball', 'r': 1.3, 'sides': 10, 'rings': 7, 'at': [0, 0, hip + 3.8], 'look': 'skin'},
         {'shape': 'ball', 'r': 1.4, 'sides': 10, 'rings': 7, 'scale': [1.05, 1.05, 0.85], 'at': [0, 0.35, hip + 4.5], 'look': 'hair'},
         {'shape': 'ball', 'r': 0.5, 'sides': 8, 'rings': 5, 'at': [-1.15, -0.2, hip + 5.6], 'look': 'flower'}]
    for side, a in ((-1, al), (1, ar)):
        # (an arm hangs from its shoulder: a cylinder turned about y by the angle, its foot at the shoulder)
        P.append({'shape': 'cylinder', 'r': 0.32, 'h': 3.2, 'sides': 6, 'turn': [0, 180 - side * a, 0],
                  'at': [side * 1.35, 0, hip + 3.0], 'look': 'skin'})
    return {'name': 'FOLabHulaDoll' + stat, 'looks': L, 'parts': P}


def charm(skill):
    """A small carved jade pendant, about 4 units, lying flat (its face up), its red cord's loop at +y."""
    carving, jade = CHARMS[skill]
    L = {'jade': look('collect/jade_' + jade, tile=None), 'cord': look('collect/cord', tile=None), 'gold': look('collect/gold', tile=None)}
    if carving == 'bi':
        P = [{'shape': 'cylinder', 'r': 1.8, 'h': 0.4, 'sides': 16, 'look': 'jade'},
             {'shape': 'cylinder', 'r': 0.55, 'h': 0.5, 'sides': 10, 'at': [0, 0, -0.05], 'look': 'gold'}]
    elif carving == 'gourd':
        P = [{'shape': 'ball', 'r': 1.3, 'sides': 10, 'rings': 6, 'scale': [1, 1, 0.4], 'at': [0, -0.6, 0], 'look': 'jade'},
             {'shape': 'ball', 'r': 0.9, 'sides': 10, 'rings': 6, 'scale': [1, 1, 0.4], 'at': [0, 1.2, 0], 'look': 'jade'}]
    elif carving == 'fish':
        P = [{'shape': 'ball', 'r': 1.0, 'sides': 10, 'rings': 6, 'scale': [0.8, 2.0, 0.45], 'at': [0, -0.2, 0], 'look': 'jade'},
             {'shape': 'cone', 'r': 0.9, 'h': 1.2, 'sides': 6, 'turn': [-90, 0, 0], 'scale': [1, 1, 0.4], 'at': [0, -2.1, 0.45], 'look': 'jade'}]
    elif carving == 'cicada':
        P = [{'shape': 'ball', 'r': 0.8, 'sides': 10, 'rings': 6, 'scale': [0.9, 2.0, 0.6], 'look': 'jade'},
             {'shape': 'box', 'size': [1.2, 2.4, 0.25], 'at': [-0.9, -0.4, 0.1], 'turn': [0, 0, 12], 'look': 'jade'},
             {'shape': 'box', 'size': [1.2, 2.4, 0.25], 'at': [0.9, -0.4, 0.1], 'turn': [0, 0, -12], 'look': 'jade'}]
    else:                                   # (coin: a round with a square hole's rim)
        P = [{'shape': 'cylinder', 'r': 1.6, 'h': 0.35, 'sides': 16, 'look': 'jade'},
             {'shape': 'box', 'size': [0.9, 0.9, 0.45], 'at': [0, 0, -0.05], 'look': 'gold'}]
    P += [{'shape': 'cylinder', 'r': 0.35, 'h': 0.5, 'sides': 8, 'at': [0, 2.3, 0], 'look': 'gold'},        # (the bail)
          {'shape': 'box', 'size': [0.25, 2.6, 0.25], 'at': [0, 3.8, 0.05], 'look': 'cord'},
          {'shape': 'cone', 'r': 0.45, 'r2': 0.15, 'h': 1.4, 'sides': 6, 'turn': [90, 0, 0], 'at': [0, 5.0, 0.3], 'look': 'cord'}]
    return {'name': 'FOLabJadeCharm' + skill, 'looks': L, 'parts': P}


def _build(desc, key):
    import modelmake
    import nifmake
    made = modelmake.make(desc)
    made['nif'] = nifmake.build_dropped(desc['name'], made['shapes'], mass=0.3, material='glass')
    made['mesh'] = 'meshes\\folab\\%s\\%s.nif' % (SET, key)
    files = {made['mesh']: made['nif']}
    for tex in made['textures']:
        tname = next((n for n in modelsets.TEXTURES if modelsets.tex_path(n) == tex or modelsets.tex_path(n, True) == tex), None)
        if tname is None:
            raise ValueError('%s names a texture no set draws: %s' % (key, tex))
        files[modelsets.tex_path(tname)], files[modelsets.tex_path(tname, True)] = modelsets.texture_files(tname)
    made['files'] = files
    return made


def models():
    """{(set, name): (description, made)} of all twenty."""
    out = {}
    for s in SPECIAL:
        d = doll(s)
        out[('hula', s)] = (d, _build(d, 'hula_' + s.lower()))
    for s in SKILLS:
        d = charm(s)
        out[('jade', s)] = (d, _build(d, 'jade_' + s.lower()))
    return out


# ---------- records ----------
def _name(kind, stat):
    return ('Hula Doll - %s' if kind == 'hula' else 'Jade Charm - %s') % SHOWN.get(stat, stat)


def _edid(kind, stat):
    return ('FOLabHulaDoll' if kind == 'hula' else 'FOLabJadeCharm') + stat


def item_record(gd, kind, stat, made):
    f = min((f for f, (_i, r) in gd.forms.items() if r.tag == 'MISC' and gd.edid(f) == 'CoffeeMug01'), key=lambda f: f >> 24)
    rec = recordio.load(gd, f)
    rec['src'] = ''
    subs = []
    for s in rec['subs']:
        if s['tag'] in ('MODT', 'SCRI', 'YNAM', 'ZNAM'):
            if s['tag'] in ('YNAM', 'ZNAM'):
                subs.append(s)
            continue
        s = dict(s)
        if s['tag'] == 'EDID':
            s['value'] = _edid(kind, stat)
        elif s['tag'] == 'FULL':
            s['value'] = _name(kind, stat)
        elif s['tag'] == 'MODL':
            s['value'] = made['mesh'][7:]
        elif s['tag'] == 'OBND':
            s['fields'] = [dict(q, value=int(round(v))) for q, v in zip(s['fields'], made['box'])]
        elif s['tag'] == 'DATA':
            s['fields'] = [dict(q, value=0 if q.get('name') in ('Value', 'Weight') else q.get('value')) for q in s['fields']]
        subs.append(s)
    rec['subs'] = subs
    return rec


def item_source(kind, stat, n, total, reward_spell, msg, reward_msg):
    var, count = '%s%d' % (kind, n), '%scount' % kind
    L = ['scn %sScript' % _edid(kind, stat), '', 'Begin OnAdd player', '\tif %s.%s == 0' % (QUEST, var),
         '\t\tset %s.%s to 1' % (QUEST, var),
         '\t\tplayer.ModAV %s %d' % (stat, DOLL_GAIN if kind == 'hula' else CHARM_GAIN),
         '\t\tset %s.%s to %s.%s + 1' % (QUEST, count, QUEST, count), '\t\tShowMessage %s' % msg,
         '\t\tif %s.%s >= %d' % (QUEST, count, total), '\t\t\tplayer.AddSpell %s' % reward_spell, '\t\t\tShowMessage %s' % reward_msg]
    if kind == 'jade':
        import repstanding
        L.append('\t\t\t' + repstanding.bump('huang', JADE_FACE))
    L += ['\t\tendif', '\tendif', 'End', '']
    return '\n'.join(L)


def reward_spell(gd, key, world=None):
    """The set's ability. Island Time ('hula') gets a second effect, +`ISLAND_SPEED`% speed, conditioned on being in the
    island's world (`world`, its key: outdoors there, as interiors are no worldspace)."""
    edid, name, effect, mag, _words = REWARDS[key]
    f = next(f for f, (_i, r) in gd.forms.items() if r.tag == 'SPEL' and gd.edid(f) == 'RexBloodLegion')
    rec = recordio.load(gd, f)
    rec['src'] = ''
    mgef = gd.key(next(f for f, (_i, r) in gd.forms.items() if r.tag == 'MGEF' and gd.edid(f) == effect))
    for s in rec['subs']:
        if s['tag'] == 'EDID':
            s['value'] = edid
        elif s['tag'] == 'FULL':
            s['value'] = name
        elif s['tag'] == 'EFID':
            s['value'] = mgef
        elif s['tag'] == 'EFIT':
            for q in s['fields']:
                if q.get('name') == 'Magnitude':
                    q['value'] = mag
    if key == 'hula' and world:
        import questrec as qr
        efid = next(s for s in rec['subs'] if s['tag'] == 'EFID')
        efit = next(s for s in rec['subs'] if s['tag'] == 'EFIT')
        speed = gd.key(next(f for f, (_i, r) in gd.forms.items() if r.tag == 'MGEF' and gd.edid(f) == 'IncreaseSpeedMult'))
        e2 = json.loads(json.dumps(efit))
        for q in e2['fields']:
            if q.get('name') == 'Magnitude':
                q['value'] = ISLAND_SPEED
        rec['subs'] += [dict(json.loads(json.dumps(efid)), value=speed), e2,
                        qr.condition_sub({'or': False, 'use_target': False, 'op': '=', 'fn': GETINWORLDSPACE, 'p1': world, 'p2': 0,
                                          'run': 0, 'ref': '', 'value': 1.0})]
    return rec


# ---------- where ----------
def _key(pr, edid, tag=None):
    return next((k for k, r in pr.records.items() if (tag is None or r.get('type') == tag) and recordio.field(r, 'EDID') == edid), None)


def _box_of(gd, pr, base):
    import townbuild
    if base in pr.records:
        ob = next((s for s in pr.records[base]['subs'] if s['tag'] == 'OBND'), None)
        return [float(f['value']) for f in ob['fields'] if 'name' in f] if ob else None
    return townbuild.obnd(gd, base)


def _turn(x, y, rz):
    c, s = math.cos(rz), math.sin(rz)
    return x * c + y * s, -x * s + y * c


def _edid_of(gd, pr, b):
    if b in pr.records:
        return recordio.field(pr.records[b], 'EDID') or '' if pr.records[b].get('subs') else ''
    try:
        return gd.edid(gd.from_key(b)) or ''
    except (KeyError, ValueError, IndexError):
        return ''


def _surfaces(gd, pr, refs, word, near=None):
    """[(ref key, its edid, top middle (x, y, z), its turn)] of things whose editor ID says they're something to put a thing on."""
    rx = re.compile(word, re.I)
    out = []
    for rk, r in refs:
        b = r.get('base')
        if not b or r.get('removed') or not r.get('p'):
            continue
        e = _edid_of(gd, pr, b)
        if not rx.search(e) or re.search(r'Door|Marker|Light|Rug|Carpet|Trigger', e, re.I):
            continue
        box = _box_of(gd, pr, b)
        if not box:
            continue
        s = float(r.get('s') or 1.0)
        p = r['p']
        rz = p[5] if len(p) > 5 else 0.0
        big = max(box[3] - box[0], box[4] - box[1]) * s > 300
        if not big and (abs(p[3] if len(p) > 3 else 0) > 0.05 or abs(p[4] if len(p) > 4 else 0) > 0.05):
            continue                                        # (tipped over: nothing rests on it level; a listing wreck may be stood on)
        top = p[2] + box[5] * s
        if near and math.dist((p[0], p[1]), near[:2]) > near[2]:
            continue
        w, d = (box[3] - box[0]) * s, (box[4] - box[1]) * s
        nu, nv = max(1, min(6, int(w // 120) + 1)), max(1, min(6, int(d // 120) + 1))
        for i in range(nu):
            for j in range(nv):
                fx = 0.5 if nu == 1 else 0.15 + 0.7 * i / (nu - 1)
                fy = 0.5 if nv == 1 else 0.15 + 0.7 * j / (nv - 1)
                wx, wy = _turn((box[0] + (box[3] - box[0]) * fx) * s, (box[1] + (box[4] - box[1]) * fy) * s, rz)
                out.append((rk, e, (p[0] + wx, p[1] + wy, top), rz))
    return out


def _clear_of(gd, pr, refs, arrive):
    import robots
    doors, people = [], []
    for rk, r in refs:
        if r.get('removed') or not r.get('p'):
            continue
        if rk in arrive:
            doors.append(arrive[rk])
        t = robots._tag(gd, pr, r.get('base'))
        if t == 'DOOR' or r.get('tel'):
            doors.append(r['p'])
        elif t in robots.ACTOR_TAGS:
            people.append(r['p'])
    return doors, people


def plan(gd, pr):
    import factionfolk as ff
    import lootplace
    import robots
    rows, skipped = [], []
    if _key(pr, QUEST, 'QUST'):
        return rows, [(QUEST, 'already in the mod (Undo first)')]
    places = {recordio.field(r, 'EDID'): k for k, r in pr.records.items() if r.get('type') == 'CELL' and k.startswith('+')}
    mk = ff._markers(pr)
    arrive = robots.arrivals(pr)
    taken = []
    boxes = {('hula', s): doll_box() for s in SPECIAL}
    boxes.update({('jade', s): charm_box() for s in SKILLS})
    for (kind, stat), (where, word) in SPOTS.items():
        box = boxes[(kind, stat)]
        if isinstance(where, tuple):
            _w, marker, radius = where
            if marker not in mk:
                skipped.append((_edid(kind, stat), 'no map marker %s' % marker))
                continue
            mck, mp = mk[marker]
            world = gd.ext_cells.get(gd.from_key(mck)) if not mck.startswith('+') else None
            if world is None:
                skipped.append((_edid(kind, stat), '%s is not outside' % marker))
                continue
            S = lootplace.Seat(gd, pr, world)
            S.load(mp[0], mp[1])
            grid = gd.grid(world)
            refs = []
            cx, cy = int(mp[0] // 4096), int(mp[1] // 4096)
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    c = grid.get((cx + dx, cy + dy))
                    if c is not None:
                        ck = gd.key(c)
                        refs += [(rk, r, ck) for rk, r in ((pr.cells.get(ck) or {}).get('refs') or {}).items()]
            cells_of = {rk: ck for rk, _r, ck in refs}
            refs2 = [(rk, r) for rk, r, _c in refs]
            near = (mp[0], mp[1], radius)
            outside, from_ = True, mp[:2]
        else:
            ck = places.get(where)
            if not ck:
                skipped.append((_edid(kind, stat), 'no place %s' % where))
                continue
            S = lootplace.Seat(gd, pr, None)
            S.solids.load_round([ck])
            refs2 = list(((pr.cells.get(ck) or {}).get('refs') or {}).items())
            cells_of = {rk: ck for rk, _r in refs2}
            near, outside = None, False
            from_ = None
        doors, people = _clear_of(gd, pr, refs2, arrive)
        if from_ is None:
            from_ = doors[0][:2] if doors else (0.0, 0.0)
        cands = []
        for rk, e, (x, y, z), rz in _surfaces(gd, pr, refs2, word, near):
            if min((math.dist((x, y), d[:2]) for d in doors), default=1e9) < DOOR_CLEAR:
                continue
            if min((math.dist((x, y), q[:2]) for q in people), default=1e9) < PEOPLE_CLEAR:
                continue
            if any(c == cells_of[rk] and math.dist((x, y), t[:2]) < APART for c, t in taken):
                continue
            p = S.at(x, y, rz, box, z, outside=outside)
            if p is None:
                continue
            cands.append((p[2] + box[2] >= z - ON_TOP, math.dist((x, y), from_[:2]), rk, e, p))
        if not cands and not outside:          # (nothing to put it on: the floor at the place's far end, a cave's end)
            import robots as R
            for x, y, z in R._tris(gd, pr, ck):
                if min((math.dist((x, y), d[:2]) for d in doors), default=1e9) < DOOR_CLEAR or                         min((math.dist((x, y), q[:2]) for q in people), default=1e9) < PEOPLE_CLEAR or                         any(c == ck and math.dist((x, y), t[:2]) < APART for c, t in taken):
                    continue
                p = S.at(x, y, 0.0, box, z, outside=False)
                if p is not None:
                    cands.append((False, math.dist((x, y), from_[:2]), 'floor', 'the floor', p))
                    cells_of['floor'] = ck
        if not cands:
            skipped.append((_edid(kind, stat), 'no surface to rest on in %s' % (where if isinstance(where, str) else where[1])))
            continue
        top, d, rk, e, p = max(cands)                  # (on a top first; the farthest from the way in, or the marker's middle)
        taken.append((cells_of[rk], p))
        named = [r['p'] for _k, r in refs2 if r.get('edid') and r.get('p') and not r.get('removed')]
        posts = _posts(gd, pr) if outside else []
        rows.append({'named': round(min((math.dist(p[:2], q[:2]) for q in named), default=1e9)),
                     'trail': round(min((math.dist(p[:2], q[:2]) for q in posts), default=1e9)) if outside else None,
                     'kind': kind, 'stat': stat, 'cell': cells_of[rk], 'p': p, 'on': e if top or e == 'the floor' else 'the floor by ' + e,
                     'where': where if isinstance(where, str) else where[1],
                     'door': round(min((math.dist(p[:2], q[:2]) for q in doors), default=1e9)),
                     'people': round(min((math.dist(p[:2], q[:2]) for q in people), default=1e9)), 'from_way_in': round(d)})
    return rows, skipped


_POSTS = {}


def _posts(gd, pr):
    """The crest trail's signposts (secretcaches.TRAIL_POST), where a thing outside keeps off."""
    if id(pr) not in _POSTS:
        import secretcaches as SC
        _POSTS[id(pr)] = [r['p'] for _c, _k, r in SC._outside_refs(gd, pr, lambda r: _edid_of(gd, pr, r.get('base', '')) == SC.TRAIL_POST)]
    return _POSTS[id(pr)]


_BOX = {}


def doll_box():
    if 'hula' not in _BOX:
        _BOX['hula'] = _build(doll('Strength'), 'x')['box']
    return _BOX['hula']


def charm_box():
    if 'jade' not in _BOX:
        _BOX['jade'] = _build(charm('Barter'), 'x')['box']
    return _BOX['jade']


# ---------- the whole ----------
def ops(gd, pr, P=None):
    import api_scripts
    import library
    import newgame
    import questrec as qr
    from activity import _new_key
    rows, skipped = P or plan(gd, pr)
    if not rows:
        raise ValueError('nothing to place: %s' % (skipped,))
    M = models()
    root = library.assets_dir(pr)
    for _d, made in M.values():
        for path, data in made['files'].items():
            library._put(root, path, data)
    out, extra, rep = [], {}, {'made': [], 'placed': [], 'skipped': skipped}

    def record(edid, rec, key=None):
        k = key or _new_key(pr)
        extra[k] = rec
        out.append({'op': 'record', 'key': k, 'record': rec})
        rep['made'].append(edid)
        return k
    # the quest that remembers (its variables: one a find, and a count a set)
    qk, qsk = _new_key(pr), _new_key(pr)
    quest = qr.quest_record({'edid': QUEST, 'script': qsk, 'name': '', 'flags': {'start_enabled': True}, 'priority': 10,
                             'delay': 60.0, 'stages': [], 'objectives': []})
    src = ['scn %s' % QSCRIPT] + ['short hula%d' % (i + 1) for i in range(len(SPECIAL))] + \
          ['short jade%d' % (i + 1) for i in range(len(SKILLS))] + ['short hulacount', 'short jadecount', '',
                                                                     'Begin GameMode', '\tset hulacount to hulacount', 'End', '']
    sc = api_scripts.scripts()
    c = sc.compile('\n'.join(src), qsk, 'quest', {qk: quest})
    if not hasattr(c, 'subrecords'):
        raise ValueError('the collectibles quest script: %s' % (c,))
    record(QSCRIPT, sc._record_of(c, QSCRIPT), qsk)
    record(QUEST, quest, qk)
    rewards = {}
    world = _key(pr, ISLAND_WORLD, 'WRLD') or next((gd.key(f) for f, (_i, r) in gd.forms.items()
                                                     if r.tag == 'WRLD' and gd.edid(f) == ISLAND_WORLD), None)
    for key, (edid, name, _e, _m, words) in REWARDS.items():
        rewards[key] = (record(edid, reward_spell(gd, key, world)), record(edid + 'Msg', newgame._message_record(edid + 'Msg', words)))
    placed = {(r['kind'], r['stat']): r for r in rows}
    for kind, stats in (('hula', SPECIAL), ('jade', SKILLS)):
        for n, stat in enumerate(stats, 1):
            _d, made = M[(kind, stat)]
            ik, sk = _new_key(pr), _new_key(pr)
            item = item_record(gd, kind, stat, made)
            import api_characters as ac
            ac.insert(item, {'tag': 'SCRI', 'label': 'Script', 'kind': 'F', 'value': sk})
            words = ("You found the %s hula doll. +%d %s." % (stat, DOLL_GAIN, stat) if kind == 'hula' else
                     "You found a jade charm, carved for %s. +%d %s." % (SHOWN.get(stat, stat), CHARM_GAIN, SHOWN.get(stat, stat)))
            msg = record(_edid(kind, stat) + 'Msg', newgame._message_record(_edid(kind, stat) + 'Msg', words))
            total = len(stats)
            spell_edid, msg_edid = REWARDS[kind][0], REWARDS[kind][0] + 'Msg'
            extra[ik] = item
            c = sc.compile(item_source(kind, stat, n, total, spell_edid, _edid(kind, stat) + 'Msg', msg_edid), sk, 'object', extra)
            if not hasattr(c, 'subrecords'):
                raise ValueError('%s script: %s' % (_edid(kind, stat), c))
            record(_edid(kind, stat) + 'Script', sc._record_of(c, _edid(kind, stat) + 'Script'), sk)
            record(_edid(kind, stat), item, ik)
            _ = msg
            r = placed.get((kind, stat))
            if r:
                out.append({'op': 'place', 'cell': r['cell'], 'key': _new_key(pr), 'ref': {'base': ik, 'p': r['p'], 's': 1.0}})
                rep['placed'].append({'item': _name(kind, stat), 'where': r['where'], 'on': r['on'], 'door': r['door'],
                                      'people': r['people']})
    rep['items'] = len(SPECIAL) + len(SKILLS)
    rep['missing'] = [('not placed', s) for s in skipped] + ([] if world else [('Island Time', 'no world %s for its speed' % ISLAND_WORLD)])      # (the step's CHECKS fail on any: every one has its spot)
    return out, rep
