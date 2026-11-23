"""Inside the Missouri (battleship.py), and the way aboard: four places of the mod's own, built from New Vegas's own
Utility kit (the grey steel rooms and passageways of its service tunnels and plant rooms: `KIT`) by FOLab's kit planner,
furnished with the game's naval furniture and lit by the kit's own fittings, joined by the game's doors, and the gangway
and pier that bring you aboard.

    the second deck   "Broadway", the long passageway (a corridor one square wide), with off it: to port the wardroom
                      (a long table under its white cloth, navy chairs, sofas, a rug, bookcases), the captain's cabin,
                      the sick bay, the port berthing (bunks in rows, lockers); to starboard the mess deck (naval tables
                      with their benches, pillars), the galley, the ship's store and barber shop, the starboard berthing.
                      In from the quarterdeck at its after end; at its forward end down to the engine room; off the mess
                      deck to Turret Two.
    the engine room   two turbine casings and the reduction gears aft of them, the gauge boards by the door, pumps.
    Turret Two        three guns' breeches, their barrels out through the forward bulkhead, the turret officer's booth.
    the pilot house   three squares across, two deep; the ports along the forward bulkhead (FOLab's own: sea and sky
                      painted behind the glass, since the game draws nothing outside a place), the helm behind them
                      (FOLab's own: the wheel, the brass telegraphs and the binnacle: the game has none), consoles on the
                      side bulkheads, the captain's chair, the chart table.

Each place is a `Layout`: rooms and corridors on the kit's 256-unit squares, which squares have doorways between them,
the doorways out (`exit`: which place and door each leads to), the things in it (by editor ID, against a wall or where
they stand). `build` makes it: `kitplan.fill` picks the kit's pieces so every side agrees, `kitplan.walk_check` walks the
pieces' real collision from the first room to every square, then with the doors, lights and furniture in, and refuses
(ValueError, saying what) when it can't. `board` gives the ops: the places' records (copies of a game interior's, for its
lighting and sound), every piece and thing in them, the doors linked, the quarterdeck and bridge doors on the ship, the
gangway, the pier to the shore, the map marker. `navmesh_ops` then makes each place's navmesh."""
import collections
import hashlib
import math
import os
import random

import battleship
import kitdress
import kitindex
import kitplan
import landmarks
import modelsets
import placewater
import recordio
import roadgen
import texwear as tw
import townbuild
import worldrec
from battleship import _box, _cyl
from modelsets import look
from texwear import Field, Picture, Wear, grade, mix, mul

SET = 'ship'
KIT = 'dungeons' + chr(92) + 'utility'
ROOMS, HALLS = 'rooms', 'hall'          # (the kit's families: its rooms, its small passageways)
S = 256.0                   # (the kit's square)
FACE = 109.0                # (a wall's face from the middle of its square: the kit's walls stand 19 inside the square's edge)
DOOR_IN = 'UtlDoor01'       # (the door the game hangs in this kit's doorways: inside, and every way out of a place)
DOOR = 'RCSmDoor01'         # (on her deck, outside: the game's bulkhead door, its leaf across y, 145 wide, its face to x)
LIKE = 'NellisHangar2'      # (whose place record the places copy: a steel hall's light and sound)
MARKER = ('USS Missouri', 8)
TRIES = 24                  # (seeds a place may take before it's refused)


# ---------- the helm, FOLab's own (the game has no ship's wheel) ----------

def veneer(colour=(132, 84, 46), size=512, seed=1160, panels=1):
    """Varnished wood, long-grained, the varnish gone cloudy and worn through at the edges."""
    c = Picture(size, size, gloss=60)
    grain = Field(size, size, seed, cells=2, octaves=5, stretch=(0.2, 4.0))
    cloud = Field(size, size, seed + 1, cells=5, octaves=4)
    wr = Wear(size, size, seed, grime=0.5, rain=0.3, ledges=(0.0,))
    pw = size / float(panels)
    for p in range(size * size):
        x, y = p % size, p // size
        u = x % pw
        col = mul(colour, 0.78 + 0.3 * (0.5 + 0.5 * math.sin(grain.v[p] * 26 + x * 0.02)))
        h, gl = 0.5, 70
        if u < 5 or u > pw - 5:
            col, h = mul(col, 0.6), 0.4
        if cloud.v[p] > 0.66:
            col, gl = mix(col, (180, 170, 150), 0.2), 20
        c.rgb[p], c.ht[p], c.gloss[p] = grade(wr.on(x, y, col)), h, gl
    return c


def gauges(size=512, seed=1220, across=4, down=3):
    """A board of round dials in brass rims: cream faces with black marks and a needle each, the glass dusty."""
    c = Picture(size, size, gloss=40)
    rnd = random.Random(seed)
    cw, ch = size / float(across), size / float(down)
    wr = Wear(size, size, seed, grime=0.7, rain=0.6, ledges=(0.0,))
    needles = [rnd.uniform(-2.4, 2.4) for _ in range(across * down)]
    for y in range(size):
        for x in range(size):
            p = y * size + x
            i, j = int(x / cw), int(y / ch)
            cx, cy = (i + 0.5) * cw, (j + 0.42) * ch
            r = min(cw, ch) * 0.36
            d = math.hypot(x - cx, y - cy)
            col, h, g = mul((118, 122, 120), 0.9 + 0.1 * wr.mid.v[p]), 0.5, 30
            if d < r:
                col, h, g = (226, 216, 186), 0.45, 90
                a = math.atan2(y - cy, x - cx)
                if r * 0.8 < d < r * 0.9 and int((a + math.pi) / (math.pi / 12)) % 2 == 0:
                    col = (40, 36, 30)
                na = needles[j * across + i] - math.pi / 2
                along = (x - cx) * math.cos(na) + (y - cy) * math.sin(na)
                off = abs(-(x - cx) * math.sin(na) + (y - cy) * math.cos(na))
                if 0 < along < r * 0.78 and off < 1.6:
                    col = (150, 30, 26)
            elif d < r * 1.14:
                col, h, g = mul((176, 140, 72), 0.85 + 0.3 * wr.fine.v[p]), 0.7, 120
            c.rgb[p], c.ht[p], c.gloss[p] = grade(wr.on(x, y, col)), h, g
    return c


def carpet(colour=(40, 52, 108), size=512, seed=1140):
    """Navy blue carpet, worn pale along the walked lines, stained."""
    from texwear import Cells, smooth
    c = Picture(size, size, gloss=4)
    wr = Wear(size, size, seed, grime=0.5, rain=0.0)
    nap = Field(size, size, seed + 1, cells=128, octaves=1)
    worn = Field(size, size, seed + 2, cells=3, octaves=4)
    stain = Cells(size, size, seed + 3, n=6)
    for p in range(size * size):
        x, y = p % size, p // size
        col = mul(colour, 0.85 + 0.25 * nap.v[p])
        col = mix(col, (96, 102, 126), 0.18 * smooth(0.6, 0.9, worn.v[p]))
        if stain.d1[p] < 0.08 and stain.id[p] % 5 == 0:
            col = mix(col, (60, 50, 40), 0.3)
        c.rgb[p], c.ht[p] = grade(wr.on(x, y, col), sat=0.8, warm=(1.0, 1.0, 1.0)), 0.45 + 0.1 * nap.v[p]
    return c


def cloth(colour=(226, 224, 214), size=256, seed=1200, stains=0.5):
    """Cloth: a tablecloth or a curtain, the weave, yellowed, stained, dust in the folds."""
    from texwear import Cells
    c = Picture(size, size, gloss=6)
    weave = Field(size, size, seed, cells=128, octaves=1)
    st = Cells(size, size, seed + 1, n=5)
    wr = Wear(size, size, seed, grime=0.5, rain=0.0)
    for p in range(size * size):
        x, y = p % size, p // size
        col = mul(colour, 0.88 + 0.16 * weave.v[p] + 0.04 * ((x + y) % 2))
        if st.d1[p] < 0.2 * stains and st.id[p] % 2 == 0:
            col = mix(col, (150, 120, 80), 0.4)
        c.rgb[p], c.ht[p] = grade(wr.on(x, y, col)), 0.5
    return c


modelsets.TEXTURES.update({
    'ship/in_carpet': carpet,
    'ship/in_cloth': cloth,
    'ship/in_curtain': lambda: cloth(colour=(36, 66, 150), seed=1202, stains=0.2),
    'ship/in_veneer': veneer,
    'ship/in_gauges': gauges,
    'ship/in_black': lambda: tw.steel(colour=(40, 40, 40), size=256, seed=1208, rust=0.3, flake=0.2),
    'ship/in_brass': lambda: tw.steel(colour=(186, 150, 76), size=256, seed=1210, rust=0.15, flake=0.0, gloss=120),
    'ship/in_machine': lambda: tw.steel(colour=(112, 122, 116), size=512, seed=1211, rust=0.22, flake=0.05, gloss=60),
})


def helm():
    """The helm as hers: a grey stand with a dial board, the wooden wheel on its spokes, an engine order telegraph in brass
    either side, the binnacle ahead of it. Its origin is the middle of the stand on the deck; the wheel faces +y (aft)."""
    parts = []
    looks = dict(battleship._looks())
    looks.update({'veneer': look('ship/in_veneer', tile=120), 'gauges': look('ship/in_gauges'), 'brass': look('ship/in_brass', tile=96),
                  'black': look('ship/in_black', tile=128), 'machine': look('ship/in_machine', tile=200)})
    _box(parts, [150, 70, 110], [0, 0, 0], 'machine', material='metal')
    _box(parts, [130, 4, 60], [0, -36, 70], 'gauges', solid=False)
    _cyl(parts, 8, 30, [0, 35, 80], 'black', sides=8, turn=[90, 0, 0], solid=False)
    # the wheel, facing aft: its rim of 16 segments (a part turned about y points its own z along (sin, 0, cos)), spokes from
    # the hub to the rim, a handle out past the rim on each. (The rim was a bare tube 6 deep, seen edge on from the helmsman's
    # place: there was none to see. A spoke stood off the hub, the lowest 40 under the deck: the helm stood 40 in the air)
    for k in range(16):
        a = 22.5 * k
        r = math.radians(a)
        _box(parts, [19, 7, 7], [math.sin(r) * 41, 66, 80 + math.cos(r) * 41], 'veneer', turn=[0, a, 0], solid=False)
    _cyl(parts, 10, 10, [0, 66, 80], 'brass', sides=10, turn=[90, 0, 0], solid=False)                  # its hub
    for k in range(8):
        a = 45 * k
        r = math.radians(a)
        _box(parts, [4, 4, 42], [0, 66, 80], 'veneer', turn=[0, a, 0], solid=False)
        _cyl(parts, 3, 16, [math.sin(r) * 47, 66, 80 + math.cos(r) * 47], 'veneer', sides=6, turn=[0, a, 0], solid=False)
    for sx in (-1, 1):
        _cyl(parts, 16, 96, [sx * 150, 10, 0], 'brass', sides=10)                                           # telegraphs
        _cyl(parts, 30, 10, [sx * 150, 10, 104], 'gauges', sides=14, turn=[90, 0, 0], solid=False)
        _cyl(parts, 32, 4, [sx * 150, 4, 104], 'brass', sides=14, turn=[90, 0, 0], solid=False, caps=False)
        _box(parts, [6, 6, 40], [sx * 150, 20, 104], 'brass', turn=[0, sx * 30, 0], solid=False)
    _cyl(parts, 26, 96, [0, -150, 0], 'brass', sides=12)                                                     # the binnacle
    parts.append({'shape': 'ball', 'r': 24, 'sides': 10, 'rings': 5, 'at': [0, -150, 96], 'look': 'brass', 'solid': False})
    for sx in (-1, 1):
        parts.append({'shape': 'ball', 'r': 12, 'sides': 8, 'rings': 4, 'at': [sx * 40, -150, 92], 'look': 'black', 'solid': False})
    return {'name': 'FOLabMissouriHelm', 'looks': looks, 'parts': parts}


modelsets.PIECES.setdefault('mo_helm', {'label': 'Helm', 'set': SET, 'file': 'mo_helm', 'describe': helm, 'edid': 'FOLabMissouriHelm'})


# (the pilot house's ports: the game draws nothing outside a place, so the sea and sky are painted behind the glass, as the
# game's own windows are lit panes. PORTS round ports a panel, a panel PORTS_WIDE by PORTS_HIGH, the picture 1024 by 256)
PORTS, PORTS_WIDE, PORTS_HIGH = 5, 640.0, 128.0


def ports(w=1024, h=256, seed=1230):
    """A strip of the pilot house's forward bulkhead: grey steel, PORTS round ports in brass rims, through each one the sky
    paling to a hazy horizon and the grey-blue sea below it, the glass salted at its edges."""
    c = Picture(w, h, gloss=40)
    wr = Wear(w, h, seed, grime=0.6, rain=0.5, ledges=(0.0,))
    swell = Field(w, h, seed + 1, cells=64, octaves=3, stretch=(4.0, 0.5))
    cloud = Field(w, h, seed + 2, cells=4, octaves=4, stretch=(3.0, 1.0))
    kx, ky = w / PORTS_WIDE, h / PORTS_HIGH           # (pixels a unit: the picture is stretched over the panel)
    r = PORTS_HIGH * 0.36
    horizon = 0.56
    for y in range(h):
        for x in range(w):
            p = y * w + x
            u, v = x / kx, y / ky
            i = int(u / (PORTS_WIDE / PORTS))
            cx, cy = (i + 0.5) * PORTS_WIDE / PORTS, PORTS_HIGH * 0.5
            d = math.hypot(u - cx, v - cy)
            col, ht, g = mul((106, 112, 110), 0.9 + 0.15 * wr.mid.v[p]), 0.5, 40
            if d < r:
                t = (v - (cy - r)) / (2 * r)
                if t < horizon:
                    col = mix((150, 176, 196), (212, 216, 210), (t / horizon) ** 1.5)
                    col = mix(col, (236, 236, 230), 0.35 * max(0.0, cloud.v[p] - 0.55) / 0.45)
                else:
                    s = (t - horizon) / (1 - horizon)
                    col = mul(mix((104, 128, 140), (58, 80, 96), s), 0.9 + 0.2 * swell.v[p])
                col = mix(col, (190, 186, 172), 0.25 * max(0.0, (d / r) - 0.75) / 0.25)       # (salt on the glass)
                ht, g = 0.42, 160
                c.rgb[p], c.ht[p], c.gloss[p] = tuple(int(min(255, max(0, v))) for v in col), ht, g   # (the view is not worn, only the steel round it)
                continue
            if d < r * 1.18:
                col, ht, g = mul((176, 140, 72), 0.85 + 0.3 * wr.fine.v[p]), 0.75, 120
            c.rgb[p], c.ht[p], c.gloss[p] = grade(wr.on(x, y, col)), ht, g
    return c


modelsets.TEXTURES['ship/in_ports'] = ports


def port_panel():
    """The ports along the forward bulkhead: a steel panel standing out from the wall, the view painted on its face, a
    sill under it. Its origin is the middle of its foot on the deck; its face is +y (aft, into the room); it stands
    PORT_SILL up to the ports' foot."""
    looks = dict(battleship._looks())
    looks.update({'ports': look('ship/in_ports'), 'machine': look('ship/in_machine', tile=200)})
    parts = []
    _box(parts, [PORTS_WIDE + 40, 30, PORT_SILL], [0, 0, 0], 'machine', material='metal')                    # (the bulkhead under the ports, to the sill)
    _box(parts, [PORTS_WIDE, 4, PORTS_HIGH], [0, 13, PORT_SILL], 'ports', solid=False)                       # (the ports)
    _box(parts, [PORTS_WIDE + 40, 30, 20], [0, 0, PORT_SILL + PORTS_HIGH], 'machine', solid=False)           # (the steel over them)
    return {'name': 'FOLabMissouriPorts', 'looks': looks, 'parts': parts}


PORT_SILL = 110.0
modelsets.PIECES.setdefault('mo_ports', {'label': 'Pilot house ports', 'set': SET, 'file': 'mo_ports', 'describe': port_panel,
                                         'edid': 'FOLabMissouriPorts'})
OWN = {'helm': 'mo_helm', 'ports': 'mo_ports'}      # (names in a Layout for FOLab's own pieces, not the game's)


# ---------- the game's own things in FOLab's cloth ----------

# (a name in a Layout: the game's thing whose mesh is copied with some of its pictures swapped for FOLab's own, as a
# record of the mod's own. Its shape and collision are the game's: the walk is checked with the game's own)
DRESSED = {
    'ClothTable': ('NVULBanquetTable01', {'textures\\dungeons\\nv_casino\\nv_ultralux\\NV_UL_MarbleBlack02_D.dds': 'ship/in_cloth'}),
    'NavyRug': ('NVLucky38Rug01', {'textures\\clutter\\rugs\\NVLucky38Rug_D.dds': 'ship/in_carpet',
                                   'textures\\clutter\\rugs\\NVLucky38Rug_N.dds': ('ship/in_carpet', True)}),
    'BerthCurtain': ('RCClothWall02', {'textures\\dungeons\\rivetcity\\RCsidepanel12.dds': 'ship/in_curtain',
                                      'textures\\dungeons\\rivetcity\\RCsidepanel12_n.dds': ('ship/in_curtain', True)}),
}


def game_edid(name):
    return DRESSED[name][0] if name in DRESSED else name


def dressed_ops(gd, pr, name, prefix='FOLab'):
    """(ops, base): the dressed thing's mesh and pictures among the mod's files, and its record (none if the mod has it)."""
    import library
    import nifwrite
    edid, swap = DRESSED[name]
    f = _forms(gd, [edid])[edid]
    model = gd.describe(f)[3]
    changes, root = {}, library.assets_dir(pr)
    for old, tex in swap.items():
        tex, normal = tex if isinstance(tex, tuple) else (tex, False)
        changes[old] = modelsets.tex_path(tex, normal)
        for path, data in zip((modelsets.tex_path(tex), modelsets.tex_path(tex, True)), modelsets.texture_files(tex)):
            library._put(root, path, data)
    data = gd.read_file('meshes\\' + model)
    wrong = nifwrite.prove(data, changes)
    if wrong:
        raise ValueError('The %s copied with her own pictures did not read back right: %s' % (edid, '; '.join(wrong)))
    rel = 'meshes\\folab\\%s\\%s.nif' % (SET, name.lower())
    library._put(root, rel, nifwrite.retexture(data, changes))
    mine = prefix + 'Missouri' + name
    key = _own(pr, mine, gd.describe(f)[0])
    if key:
        return [], key
    rec = recordio.load(gd, f)
    rec['subs'] = [s_ for s_ in rec['subs'] if s_['tag'] not in ('MODT', 'MODS', 'MODD')]
    recordio.set_field(rec, 'EDID', mine, label='Editor ID')
    recordio.set_field(rec, 'MODL', rel[7:], label='Model')
    rec['copied_from'] = gd.key(f)
    return [{'op': 'record_new', 'record': rec, 'name': 'dressed_' + name}], '$dressed_' + name


# ---------- a place, as squares and things ----------

# (which way each thing's front faces in its own frame, as a game turn in degrees: 0 is +y. Furniture's sitting and
# lying markers lie in front of it; the rest were looked at in the editor)
FRONT = {'GenericBookcase01': 180.0}


class Layout:
    """A place before it's built: rooms and corridors on the kit's squares (i across, +x to port; j along, +y aft; the
    square's middle at (i, j) * S), doorways between them, the doors out, and the things in it."""

    def __init__(self, name):
        self.name = name
        self.rooms, self.halls, self.ways, self.exits, self.things = [], [], [], {}, []

    def room(self, purpose, i0, j0, w, h, name=None):
        """A room of w by h squares from square (i0, j0); returns its number. A room's inside walls stand at FACE from its
        outer squares' middles: x from i0 * S - FACE to (i0 + w - 1) * S + FACE."""
        self.rooms.append({'purpose': purpose, 'name': name or purpose, 'cells': [(i, j) for i in range(i0, i0 + w) for j in range(j0, j0 + h)],
                           'box': (i0 * S - FACE, j0 * S - FACE, (i0 + w - 1) * S + FACE, (j0 + h - 1) * S + FACE)})
        return len(self.rooms) - 1

    def hall(self, cells):
        self.halls.append(list(cells))

    def way(self, a, b):
        """A doorway, with the game's door in it, between two squares side by side (a room's and what it opens on)."""
        self.ways.append((tuple(a), tuple(b)))

    def exit(self, tag, c, d, to):
        """A door out of the place from square c through its side d (0 +x, 1 +y, 2 -x, 3 -y); to: (place, door tag)."""
        self.exits[tag] = {'cell': tuple(c), 'side': d, 'to': to}

    def put(self, edid, x, y, z=0.0, face=0.0, floor=True, s=1.0):
        """Something standing at x, y, its front facing `face` degrees (0 +y, 90 +x: clockwise, as the game turns things).
        floor: z is over the deck and the thing is stood on it by its own mesh (many of the game's are centred on their
        middle); else z is where its origin goes."""
        self.things.append({'edid': edid, 'at': (x, y, z), 'face': face, 'floor': floor, 's': s})

    def wall(self, edid, room, side, along, gap=4.0, z=0.0, floor=True, face=None):
        """Something with its back to a room's wall: side 'n' (+y), 's', 'e' (+x), 'w'; along: where its middle is along
        the wall, from the wall's west or south end; facing out into the room unless face says otherwise."""
        self.things.append({'edid': edid, 'room': room, 'side': side, 'along': along, 'gap': gap, 'at': (0.0, 0.0, z), 'floor': floor, 's': 1.0,
                            'face': {'n': 180.0, 's': 0.0, 'e': 270.0, 'w': 90.0}[side] if face is None else face})


def _second():
    L = Layout('second')
    L.hall([(0, j) for j in range(-10, 11)])
    rooms = [('wardroom', 1, -10, 4, -9), ('cabin', 1, -6, 3, -5), ('sickbay', 1, -3, 4, -2), ('berthing', 1, 1, 10, (3, 8)),
             ('mess', -3, -10, 6, -7), ('galley', -3, -4, 4, -3), ('store', -3, 0, 4, 1), ('berthing', -3, 4, 7, (5, 9))]
    n = {}
    for purpose, i0, j0, h, doors in rooms:
        side = 1 if i0 > 0 else -1
        k = L.room(purpose, i0, j0, 3, h, ('port ' if side > 0 else 'starboard ') + purpose if purpose == 'berthing' else purpose)
        n[(purpose, side)] = k
        for j in (doors if isinstance(doors, tuple) else (doors,)):
            L.way((side, j), (0, j))
    L.exit('qd', (0, 10), 1, ('deck', 'qd'))
    L.exit('eng', (0, -10), 3, ('engine', 'up'))
    L.exit('tur', (-2, -10), 3, ('turret', 'out'))
    # the wardroom: the long table under its cloth, chairs down both sides, sofas at the ends, bookcases on her side
    w = n[('wardroom', 1)]
    for k, y in enumerate((-2533, -2271, -2009, -1747)):
        for j, x in enumerate((235, 405, 575, 745)):
            L.put('NavyRug', x, y, 0.4 + 0.5 * ((j + k) % 2), 90)   # (the blue carpet, near wall to wall; overlaps a little apart in height)
    L.put('ClothTable', 600, -2176)
    for y in (-2380, -2240, -2110, -1980):
        L.put('NavalChairStatic', 470, y, face=90)
        L.put('NavalChairStatic', 730, y, face=270)
    for y in (-2330, -2040):
        L.put('DinnerPlate01', 570, y, 44.5, floor=False)
        L.put('DinnerPlate01', 630, y + 70, 44.5, floor=False)
    L.put('WhiskeyBottle01Empty01', 610, -2180, 44.5, floor=False)
    L.wall('NVDLC01SofaF', w, 's', 330)
    L.wall('NVDLC01SofaF', w, 'n', 330)
    L.wall('GenericBookcase01', w, 'e', 160)
    L.wall('GenericBookcase01', w, 'e', 830)
    L.put('LamplightInteriorWarm', 600, -2176, 150, floor=False)
    # the captain's cabin
    c = n[('cabin', 1)]
    L.wall('DeskOfficeWooden', c, 'e', 200)
    L.put('ComputerNavalChair01R', 735, -1445, face=90)
    L.put('Typewriter01', 830, -1460, 56, 270, floor=False)
    L.wall('NVbedtwin01', c, 'n', 560)
    L.wall('GenericSafe01', c, 'n', 330)
    L.wall('GenericBookcase01', c, 's', 560)
    L.wall('NVDLC01SofaF', c, 's', 250)
    for k, y in enumerate((-1560, -1290, -1020)):
        for j, x in enumerate((235, 405, 575, 745)):
            L.put('NavyRug', x, y, 0.4 + 0.5 * ((j + k) % 2), 90)
    L.put('NavalTable01', 540, -1120, face=90)
    L.put('NavalChairStatic', 470, -1170, face=0)
    L.put('NavalChairStatic', 610, -1170, face=0)
    L.put('Ashtray', 540, -1110, 54, floor=False)
    L.put('LamplightInteriorWarm', 520, -1280, 140, floor=False)
    # the sick bay
    s = n[('sickbay', 1)]
    for a in (150, 480, 810):
        L.wall('NVbedtwin01', s, 'e', a)
    L.wall('LockerVault01Hospital', s, 'n', 420)
    L.wall('LockerVault01Hospital', s, 'n', 480)
    L.wall('NavalTable01', s, 's', 420, face=0)
    L.put('SurgicalTray01', 560, -820, 54, floor=False)
    L.put('AnesthesiaMachineR01NoSound', 640, -560)
    L.put('LootFirstAidKitNV', 572, -840, 54, floor=False)
    L.put('Gurney01NoShadow', 460, -230, face=0)
    L.wall('LockerVault01Hospital', s, 'n', 540)
    L.wall('LockerVault01Hospital', s, 'n', 600)
    L.wall('MetalShelf01', s, 'n', 230)
    L.wall('DrinkSinkMetal00Rads', s, 's', 160)
    # the berthing either side: bunks with their heads to her side and a row down the middle, lockers at the after end
    for side in (1, -1):
        b = n[('berthing', side)]
        x0, y0, x1, y1 = L.rooms[b]['box']
        doors = [j * S for (i, j), _o in L.ways if i == side and L.rooms[b]['cells'][0][1] <= j]
        hull = 'e' if side > 0 else 'w'
        a = 75.0
        while a < y1 - y0 - 160:
            L.wall('BedFrame01Bunk', b, hull, a)
            y = y0 + a
            if all(abs(y - d) > 230 for d in doors):
                L.put('BedFrame01Bunk', side * 480, y, face=270 if side > 0 else 90)
            a += 135
        for k in range(7):
            L.wall('Locker01Military', b, 'n', 120 + k * 92)
        a = 75.0
        while a < y1 - y0 - 160:
            # (blue curtains along the hull row's open side, as her racks have)
            L.wall('BerthCurtain', b, hull, a, gap=170.0)
            a += 270
        for k in range(3):
            L.put('Footlocker01MilitaryNV', side * 680, y0 + 140 + k * 405, face=270 if side > 0 else 90)
    L.put('SkeletonWholeBodyClothes', 560, 1550, 2, 70)                                   # (somebody stayed aboard)
    # the mess deck: naval tables with a bench either side, two pillars down the middle
    m = n[('mess', -1)]
    for x in (-700, -330):
        for y in (-2380, -2080, -1780, -1480):
            if x == -330 and y == -1780:
                continue                                    # (in front of the door from Broadway)
            L.put('NavalTable01', x, y)
            L.put('NavalBench01TableBothSides', x, y, face=0)       # (a bench either side in the one piece: put once)
            L.put('CafeteriaTray01', x, y + 30, 54, floor=False)
            L.put('CoffeeMug01', x + 5, y - 40, 54, floor=False)
    for y in (-1930, -1630):
        L.put('UtlRmFreeCol01', -515, y, 0, floor=False)
    L.wall('RCPowerBox01', m, 'w', 800)
    # the galley: ranges along her side, the serving line, lockers
    g = n[('galley', -1)]
    for a in (250, 340, 430):
        L.wall('OvenRangeDirty01NoFood', g, 'w', a)
    L.put('BigPot', -835, -883, 91, floor=False)
    L.put('PotCookingMetal', -835, -703, 91, floor=False)
    L.wall('VCounter01', g, 'n', 260)
    L.wall('VCounter01', g, 'n', 510)
    L.wall('Locker01Kitchen', g, 's', 180)
    L.wall('Locker01Kitchen', g, 's', 280)
    for y in (-920, -580):
        L.put('dlcanchgenmetaltable01', -560, y)                 # (the work tables down the middle)
    L.put('CookingPot01', -590, -920, 56, floor=False)
    L.put('BigPot', -520, -580, 56, floor=False)
    L.put('CoffeeKettle', -620, -185, 74, floor=False)
    L.wall('DrinkSinkMetal00Rads', g, 's', 420)
    L.wall('DrinkSinkMetal00Rads', g, 's', 490)
    L.wall('MetalShelf01', g, 'w', 650)
    L.wall('MetalShelf01', g, 'w', 760)
    L.wall('CrateShippingMilitary', g, 's', 600)
    L.wall('CrateShippingMilitary', g, 's', 650)
    # the ship's store and the barber's chair
    st = n[('store', -1)]
    L.put('VCounter01', -560, 520, face=90)
    L.put('CashRegisterEmpty', -545, 560, 74, 90, floor=False)
    for a in (200, 330, 460, 590):
        L.wall('MetalShelf01', st, 'w', a)
    L.wall('SignBarber01', st, 'n', 560, z=150, floor=False)
    for a in (720, 850):
        L.wall('MetalShelf01', st, 'w', a)
    L.wall('CrateLarge01', st, 's', 200)
    L.wall('CrateShippingMilitary', st, 's', 420)
    L.put('AmmoBoxSTATIC', -560, 450, 74, 90, floor=False)
    L.put('NVTOPSChair01F', -420, 760, face=270)
    return L


def _engine():
    L = Layout('engine')
    e = L.room('engine room', -3, -4, 7, 9)
    L.exit('up', (0, -4), 3, ('second', 'eng'))
    for sx in (-1, 1):
        L.put('NVNellisLargeFuelTank', sx * 470, -330, face=90)                           # the turbines' casings
        L.put('IndustrialMachine02NoSound', sx * 470, 520, face=90)                       # the reduction gears
    for a in (420, 490, 560, 1194, 1264, 1334):
        L.wall('GenericConsoleStack01NoAnim', e, 's', a)
    L.wall('IndustrialMachine11NoSound', e, 'n', 330)
    L.wall('IndustrialMachine11NoSound', e, 'n', 1424)
    L.wall('IndustrialMachine04NoSound', e, 'n', 877)
    L.put('GenericConsolePanel04NoAnim', -130, -820, face=0)
    L.put('GenericConsolePanel04NoAnim', 130, -820, face=0)
    L.wall('Locker01Military', e, 'e', 900)
    L.wall('Locker01Military', e, 'e', 990)
    L.wall('ToolboxContainer', e, 'w', 900)
    L.put('Clipboard01', 140, -820, 95, floor=False)
    return L


def _turret():
    L = Layout('turret')
    t = L.room('gun house', -3, -3, 7, 6)
    L.exit('out', (-1, 2), 1, ('second', 'tur'))
    for x in (-520, 0, 520):
        L.put('NVNellisArtilleryStatic', x, -623, 0, 0, s=1.3)    # (breech in the room, barrel out through the forward bulkhead)
    for a in (900, 970, 1040):
        L.wall('GenericConsolePanel04NoAnim', t, 'n', a)
    L.wall('Console01STATIC', t, 'n', 1300)
    L.put('ComputerNavalChair01R', 230, 400, face=0)
    for x in (-260, 260):
        L.put('IndustrialMachine05NoSound', x, 20, face=0)        # (the powder hoists come up between the guns)
    for a in (300, 1100):
        L.wall('CrateLarge01', t, 'w' if a < 600 else 'e', 500)
    for k in range(4):
        L.put('AmmoBoxSTATIC', -700 + k * 30, 240, 0)
    L.wall('Locker01Military', t, 'e', 1150)
    return L


def _pilot():
    # (a pilot house is narrow and low with ports all along its front: three squares across, two deep (it was three by
    # four, a hall); the ports across the forward bulkhead, the helm behind them, consoles on the side bulkheads)
    L = Layout('pilot')
    p = L.room('pilot house', -1, -1, 3, 2)
    L.exit('out', (1, 0), 1, ('deck', 'bridge'))
    L.wall('ports', p, 's', 365, gap=0)
    L.put('helm', 0, -150, face=0)
    for side in ('w', 'e'):
        for a in (70, 150):
            L.wall('GenericConsolePanel04NoAnim', p, side, a)
    L.put('ComputerNavalChair01R', -250, -160, face=180)
    L.put('NavalTable01', -230, 20, face=90)
    L.put('Clipboard01', -215, 20, 54, 30, floor=False)
    L.put('Handradio', -270, 10, 54, floor=False)
    L.wall('Telephone01', p, 'e', 330, z=120, floor=False)
    return L


PLACES = {'second': ('Missouri2ndDeck', 'USS Missouri - Second Deck', _second),
          'engine': ('MissouriEngineRoom', 'USS Missouri - Engine Room', _engine),
          'turret': ('MissouriTurretTwo', 'USS Missouri - Turret Two', _turret),
          'pilot': ('MissouriPilotHouse', 'USS Missouri - Pilot House', _pilot)}
_layouts = {}


def layout(key):
    if key not in _layouts:
        _layouts[key] = PLACES[key][2]()
    return _layouts[key]


# ---------- building it from the kit ----------

def kits_folder(gd):
    """Where FOLab keeps what it measured of these game files' kits (the server's kits_folder, from the game data alone)."""
    import project
    sig = hashlib.md5('|'.join('%s:%d:%d' % (p.path, os.path.getsize(p.path), os.path.getmtime(p.path)) for p in gd.plugins).encode()).hexdigest()[:12]
    return os.path.join(project.HOME, 'cache', 'kits', sig)


_kit = {}


def kit(gd):
    """(the kit's PlanTiles, the dressing survey of it), read once per game data (the first time: a couple of minutes)."""
    if id(gd) not in _kit:
        folder = kits_folder(gd)
        kits = kitindex.load(gd, folder)
        if KIT not in kits:
            raise ValueError('The game files lack the Utility kit (%s) her insides are built from.' % KIT)
        sv = kitdress.load(gd, kits, folder).get(KIT)
        _kit.clear()
        _kit[id(gd)] = (kitplan.PlanTiles(kits[KIT], gd), sv)
    return _kit[id(gd)]


def plan_of(ts, L):
    plan = kitplan.Plan(ts.step)
    rooms = [plan.add_room(r['purpose'], ROOMS, [(i, j, 0) for i, j in r['cells']], k == 0) for k, r in enumerate(L.rooms)]
    for cells in L.halls:
        plan.add_hall(HALLS, [(i, j, 0) for i, j in cells])
    if not rooms:
        raise ValueError('%s has no room.' % L.name)
    # (the first owner is where the walk starts: the first room)
    def door_wide(c, d):
        # (an opening of the width the game hangs its door in: a corridor running on into nothing is no doorway)
        plan.forced[c] = plan.forced.get(c, -1) & ts.width_mask(d, DOOR_WIDTHS)
    for a, b in L.ways:
        plan.link(a + (0,), b + (0,))
        for c, o in ((a, b), (b, a)):
            door_wide(c + (0,), next(i for i in range(4) if (c[0] + kitplan.DX[i][0], c[1] + kitplan.DX[i][1]) == o))
    for e in L.exits.values():
        c = e['cell'] + (0,)
        n = (c[0] + kitplan.DX[e['side']][0], c[1] + kitplan.DX[e['side']][1], 0)
        plan.add_void([n], 'outside')
        plan.link(c, n)
        door_wide(c, e['side'])
    return plan


DOOR_WIDTHS = {136 // 24}       # (the Utility doorway the game hangs UtlDoor01 in, in door_table's 24-unit buckets)


def _door_at(ts, sv, m, d, want):
    """The pose of the door `want` (a key) in placed piece m's doorway on world side d, where the game hangs it there, or in
    any doorway that wide. None if the game never hangs it in one like it."""
    p = ts.kit.pieces[m.key]
    side = (d + m.turn) % 4
    slot = next((s for s in p.slots if s['side'] == side and s['open']), None)
    if slot is None:
        return None
    seen = collections.Counter()
    for table in (sv.doors, sv.exits):
        for (door, x, y, z, rz), n in table.get(m.key, {}).items():
            if door == want and kitdress._near_slot(p, x, y) is slot:
                seen[(x, y, z, rz)] += n
    if seen:
        x, y, z, rz = seen.most_common(1)[0][0]
        return kitdress._world(m, x, y, z, 0.0, 0.0, rz)
    kinds = kitdress.door_table(ts.kit, sv).get(slot['width'] // 24, {})
    inv = max(((n, i) for (door, i), n in kinds.items() if door == want), default=(0, None))[1]
    if inv is None:
        return None
    sx, sy = {0: (p.foot[2], slot['u']), 1: (slot['u'], p.foot[3]), 2: (p.foot[0], slot['u']), 3: (slot['u'], p.foot[1])}[side]
    return kitdress._world(m, sx, sy, 0.0, 0.0, 0.0, (inv - side * math.pi / 2) % (2 * math.pi))


_boxes = {}


def mesh_box(gd, f):
    """A thing's mesh bounds [x0, y0, z0, x1, y1, z1] (not its record's, which for furniture take in where one sits)."""
    if f not in _boxes:
        import library
        model = gd.describe(f)[3]
        _boxes[f] = library.bounds_of(gd.read_file('meshes\\' + model)) if model else [0, 0, 0, 0, 0, 0]
    return _boxes[f]


def _turned_box(b, rz):
    c, s = math.cos(rz), math.sin(rz)
    xs, ys = [], []
    for x in (b[0], b[3]):
        for y in (b[1], b[4]):
            xs.append(x * c + y * s)
            ys.append(-x * s + y * c)
    return min(xs), min(ys), max(xs), max(ys)


def stand(gd, L, t, f, helm_box=None):
    """Where a Layout thing stands: [x, y, z, 0, 0, rz] in the place."""
    edid = t['edid']
    rz = math.radians(t['face'] - FRONT.get(edid, 0.0)) % math.tau
    b = [v * t.get('s', 1.0) for v in (helm_box if f is None else mesh_box(gd, f))]
    x0, y0, x1, y1 = _turned_box(b, rz)
    x, y, z = t['at']
    if 'room' in t:
        rx0, ry0, rx1, ry1 = L.rooms[t['room']]['box']
        side, a, g = t['side'], t['along'], t['gap']
        if side in 'ns':
            x = rx0 + a - (x0 + x1) / 2
            y = ry1 - g - y1 if side == 'n' else ry0 + g - y0
        else:
            y = ry0 + a - (y0 + y1) / 2
            x = rx1 - g - x1 if side == 'e' else rx0 + g - x0
    if t['floor']:
        z = z - b[2]
    return [round(x, 2), round(y, 2), round(z, 2), 0.0, 0.0, round(rz, 4)]


class Built:
    """A place made: pieces [(key, p)], things [(key, p, edid)], doors inside [(key, p)], the doors out {tag: (key, p,
    arrive, to)}, the seed it took, its walk."""

    def __init__(self):
        self.pieces, self.things, self.lights, self.doors, self.exits = [], [], [], [], {}
        self.scales = []            # (beside things: each one's scale)
        self.helm = None
        self.own = []               # (FOLab's own pieces: [(piece, p)])


_built = {}


def _refs(gd, things, scales=()):
    out = []
    for n, (key, p, _e) in enumerate(things):
        out.append({'ref': 200000 + n, 'type': 'REFR', 'base': gd.from_key(key), 'pos': tuple(p[:3]), 'rot': tuple(p[3:6]),
                    'scale': scales[n] if n < len(scales) else 1.0, 'leads': False, 'bkey': key})
    return out


def build(gd, key, L=None, title=None):
    """A place built from the kit and walked: Built. Raises ValueError saying why when no seed gives one that walks.
    L, title: another ship's place (flotillainside.py), under a key of its own."""
    if (id(gd), key) in _built:
        return _built[(id(gd), key)]
    ts, sv = kit(gd)
    if sv is None:
        raise ValueError('No survey of what the game stands in the Utility kit, so her doors could not be hung.')
    L = L or layout(key)
    title = title or PLACES[key][1]
    want = {game_edid(t['edid']) for t in L.things if t['edid'] not in OWN} | {DOOR_IN}
    forms = _forms(gd, want)
    lacking = sorted(want - set(forms))
    if lacking:
        raise ValueError('The game files lack what the %s holds: %s.' % (title, ', '.join(lacking)))
    door_key = gd.key(forms[DOOR_IN])
    cache = {}
    why = collections.Counter()
    own_box = {n: _own_made(OWN[n])['box'] for n in {t['edid'] for t in L.things} & set(OWN)}
    for seed in range(TRIES):
        plan = plan_of(ts, L)
        made = kitplan.fill(ts, plan, seed)
        if not made:
            why['no pieces fit'] += 1
            continue
        out_at = []
        for e in L.exits.values():
            c, d = e['cell'], e['side']
            out_at.append(((c[0] + kitplan.DX[d][0] * 0.5) * S, (c[1] + kitplan.DX[d][1] * 0.5) * S))
        walk = kitplan.walk_check(gd, ts, plan, made, cache)
        edges = [q for q in walk['edges'] if all(abs(q[0] - x) > S * 0.6 or abs(q[1] - y) > S * 0.6 for x, y in out_at)]
        if walk['missing'] or walk['escaped'] or edges:
            why['the pieces did not walk (%d squares not reached, %d places outside, %d edges)' % (len(walk['missing']), len(walk['escaped']), len(edges))] += 1
            continue
        by = {m.cell: m for m in made if len(m.cells) == 1}
        B = Built()
        B.seed = seed
        B.pieces = [(m.key, [m.x, m.y, m.z, 0.0, 0.0, m.turn * math.pi / 2]) for m in made]
        ok = True
        for a, b in L.ways:
            ca, cb = a + (0,), b + (0,)
            room_side = ca if plan.owners[plan.cells[ca]]['kind'] == kitplan.ROOM else cb
            other = cb if room_side == ca else ca
            d = next(i for i in range(4) if (room_side[0] + kitplan.DX[i][0], room_side[1] + kitplan.DX[i][1]) == other[:2])
            p = _door_at(ts, sv, by[room_side], d, door_key) if room_side in by else None
            if p is None:
                ok = False
                break
            B.doors.append((door_key, [round(v, 4) for v in p]))
        for tag, e in L.exits.items():
            c = e['cell'] + (0,)
            p = _door_at(ts, sv, by[c], e['side'], door_key) if c in by else None
            if p is None:
                ok = False
                break
            dx, dy = kitplan.DX[e['side']]
            arrive = [c[0] * S - dx * 40.0, c[1] * S - dy * 40.0, 10.0, math.atan2(-dx, -dy) % math.tau]
            B.exits[tag] = (door_key, [round(v, 4) for v in p], arrive, e['to'])
        if not ok:
            why['a doorway the game hangs no %s in' % DOOR_IN] += 1
            continue
        # the kit's own light fittings, one rig throughout, as the game lights these pieces
        items = lights(gd, ts, sv, L, plan, made, random.Random(seed))
        B.lights = [(it.key, [round(v, 4) for v in it.p]) for it in items]
        for t in L.things:
            if t['edid'] in OWN:
                p = stand(gd, L, t, None, own_box[t['edid']])
                B.own.append((OWN[t['edid']], p))
                if t['edid'] == 'helm':
                    B.helm = p
                continue
            f = forms[game_edid(t['edid'])]
            B.things.append((gd.key(f), stand(gd, L, t, f), t['edid']))
            B.scales.append(t.get('s', 1.0))
        # (the helm is the mod's own model, which navgen reads from the mod's files: it stands in the open, in front of the
        # consoles, and the navmesh made after it's placed has it)
        walk = kitplan.walk_check(gd, ts, plan, made, cache, extra=_refs(gd, B.things, B.scales) + kitdress.item_refs(gd, items))
        lost = [c for c in walk['missing'] if not _under(gd, B, c)]
        if lost or walk['escaped']:
            why['with its things in, %d squares could not be reached (%s)' % (len(lost), ', '.join('%d,%d' % c[:2] for c in lost[:6]))] += 1
            continue
        B.under = len(walk['missing']) - len(lost)
        B.walk = walk
        B.plan = plan
        _built[(id(gd), key)] = B
        return B
    raise ValueError('The %s could not be built from the Utility kit in %d tries: %s.' % (
        title, TRIES, '; '.join('%s (%d)' % w for w in why.most_common())))


_own_built = {}


def _own_made(piece):
    if piece not in _own_built:
        _own_built[piece] = modelsets.build(piece)
    return _own_built[piece]


def _helm():
    return _own_made('mo_helm')


def _under(gd, B, c):
    """Is this square's middle under one of the place's things (a machine standing on it, so nobody walks there)?"""
    x, y = c[0] * S, c[1] * S
    for (key, p, _e), sc in zip(B.things, B.scales):
        b = [v * sc for v in mesh_box(gd, gd.from_key(key))]
        if b[5] - b[2] < 60:
            continue
        dx, dy = x - p[0], y - p[1]
        c_, s_ = math.cos(p[5]), math.sin(p[5])
        lx, ly = dx * c_ - dy * s_, dx * s_ + dy * c_          # (into the thing's own frame: the game turns clockwise)
        if b[0] - 48 <= lx <= b[3] + 48 and b[1] - 48 <= ly <= b[4] + 48:
            return True
    return False


# (the light the game gives its Utility rooms most: the caged metal fitting MetLight01b with its glow and a key light; warm
# in the officers' rooms, cool elsewhere)
LIGHT_FITTING = 'MetLight01b'
LIGHT_KEYS = {'cool': 'BasementLightKeyCool', 'warm': 'BasementLightKeyWarm'}
WARM = ('wardroom', 'cabin')
LIGHT_EVERY = 4.0           # (squares of floor to a light)


def lights(gd, ts, sv, L, plan, made, rng):
    """Every room and corridor lit by the one rig: of the sets the game stood on these same pieces, those with the caged
    fitting and its key light and nothing else that lights, spread evenly over each room. [kitdress.Item]"""
    names = {sv_key: gd.edid(gd.from_key(sv_key)) for sv_key in {it[0] for sets in sv.sets.values() for st in sets for it in st}}
    pieces = collections.defaultdict(list)
    for m in made:
        pieces[m.owner].append(m)
    found = _forms(gd, LIGHT_KEYS.values())
    keys = {k: gd.key(found[v]) for k, v in LIGHT_KEYS.items() if v in found}
    out = []
    for o in plan.owners:
        if o['kind'] == kitplan.VOID:
            continue
        key_light = keys.get('warm' if o['purpose'] in WARM else 'cool')
        good = []
        for m in pieces[o['n']]:
            sets = []
            for st in sv.sets.get(m.key, ()):
                ls = [names[it[0]] for it in st if sv.info.get(it[0], ('',))[0] == 'light']
                if ls and set(ls) <= set(LIGHT_KEYS.values()) and any(names[it[0]] == LIGHT_FITTING for it in st):
                    sets.append(st)
            if sets:
                good.append((m, sets))
        if not good:
            continue
        good.sort(key=lambda g: (g[0].y, g[0].x))
        want = max(1, int(round(len(o['cells']) / LIGHT_EVERY)))
        pick = [good[int((k + 0.5) * len(good) / want)] for k in range(min(want, len(good)))]
        for m, sets in pick:
            st = rng.choice(sets)
            for it in st:
                info = sv.info.get(it[0], ('thing',))
                if info[0] == 'light' or (info[0] == 'stat' and (names[it[0]] == LIGHT_FITTING or names[it[0]].startswith('FXGlow'))):
                    k = key_light if info[0] == 'light' and key_light else it[0]
                    w = kitdress._world(m, it[1], it[2], it[3], it[4], it[5], it[6])
                    if any(o2.key == k and abs(o2.p[0] - w[0]) < 2 and abs(o2.p[1] - w[1]) < 2 and abs(o2.p[2] - w[2]) < 2 for o2 in out):
                        continue            # (the same light twice on one spot: a set the game stood twice there, or a fitting's own)
                    out.append(kitdress.Item(k, w, it[7], info[0], o['n'], m))
    return out


def game_pieces(gd, B):
    """How many of a place's pieces are the game's own kit pieces (all of them, built right)."""
    ts, _sv = kit(gd)
    return sum(1 for k, _p in B.pieces if k in ts.kit.pieces)


def gangway():
    """The gangway down her side: from her deck's edge (the origin) out along +x and down to a landing at the
    pier's height, `DROP` under; treads, rails, a ramp under them to walk."""
    parts = []
    run = GANG_RUN
    battleship.ladder(parts, 0, run, -DROP, 0, 0, wide=120)
    for p in parts:                                     # (laid along y by ladder: turned to run along +x)
        p['at'] = [p['at'][1], -p['at'][0], p['at'][2]]
        t = p.get('turn', [0, 0, 0])
        p['turn'] = [t[0], t[1], t[2] - 90]
    parts.append({'shape': 'box', 'size': [260, 260, 14], 'at': [run + 120, 0, -DROP - 14], 'look': 'deck', 'solid': True, 'material': 'metal'})
    return {'name': 'FOLabShipGangway', 'looks': battleship._looks(), 'parts': parts}


GANG_RUN, DROP = 1000.0, 420.0
modelsets.PIECES.setdefault('mo_gangway', {'label': 'Gangway', 'set': SET, 'file': 'mo_gangway', 'describe': gangway, 'edid': 'FOLabShipGangway'})
OLD_SHELLS = tuple('FOLab' + e + 'Shell' for e, _f, _fn in PLACES.values())     # (her first insides: one model of FOLab's own a place)


# ---------- aboard ----------

PIER_MOST = 12000.0             # (no pier longer than this)


def _forms(gd, edids):
    """{editor ID: the game's form}, the base game's first, in one pass."""
    want = set(edids)
    out = {}
    for f, (_i, r) in gd.forms.items():
        e = gd.edid(f)
        if e in want and (e not in out or (f >> 24) == 0):
            out[e] = f
    return out


def _own(pr, edid, rtype):
    for k, r in pr.records.items():
        if k.startswith('+') and r.get('type') == rtype and recordio.field(r, 'EDID') == edid:
            return k
    return None


LOCKER_SPOTS = [(420.0, 190.0), (510.0, 190.0), (600.0, 190.0), (690.0, 190.0)]     # (the port berthing's forward wall)


def board(gd, pr, world, ship, prefix='FOLab', again=False):
    """(ops, report): her insides and the way aboard, for the Missouri standing at ship = (x, y, z, turn) in world.
    Raises ValueError with the reason when something it needs isn't there. again: her old places are being taken out in
    the same Undo (shipplace.restand), so ones of the same names are no reason to refuse."""
    import shipplace
    sx_, sy_, sz_, turn = ship
    for key, (edid, full, _fn) in PLACES.items():
        if not again and _own(pr, prefix + edid, 'CELL'):
            raise ValueError('She already has her insides (%s).' % full)
    built = {k: build(gd, k) for k in PLACES}
    forms = _forms(gd, {DOOR, landmarks.DOCK, landmarks.PYLON[0]})
    if DOOR not in forms:
        raise ValueError('The game files lack the bulkhead door (%s).' % DOOR)
    like = townbuild.grand_inside(gd, LIKE)
    ops, rep = [], {'places': {}, 'pieces': 0, 'things': 0, 'lights': 0, 'seeds': {}}
    cells, places, dressed, own = {}, {}, {}, {}
    for key, (edid, full, _fn) in PLACES.items():
        rec = recordio.load(gd, gd.from_key(like['cell']))
        rec['subs'] = [s for s in rec['subs'] if s['tag'] not in ('XOWN', 'XRNK')]
        placewater.make_dry(rec)
        recordio.set_field(rec, 'EDID', prefix + edid, label='Editor ID')
        recordio.set_field(rec, 'FULL', full, label='Name')
        ops.append({'op': 'record_new', 'record': rec, 'name': 'mo_' + key})
        cells[key] = ck = '$mo_' + key
        B = built[key]
        for k, p in B.pieces:
            ops.append({'op': 'add', 'cell': ck, 'base': k, 'p': [round(v, 4) for v in p], 's': 1})
        for (k, p, e), sc in zip(B.things, B.scales):
            if e in DRESSED:
                if e not in dressed:
                    more, dressed[e] = dressed_ops(gd, pr, e, prefix)
                    ops += more
                k = dressed[e]
            ops.append({'op': 'add', 'cell': ck, 'base': k, 'p': p, 's': sc})
        for k, p in B.lights:
            ops.append({'op': 'add', 'cell': ck, 'base': k, 'p': p, 's': 1})
        for k, p in B.doors:
            ops.append({'op': 'add', 'cell': ck, 'base': k, 'p': p, 's': 1})
        for piece, p in B.own:
            if piece not in own:
                more, info = modelsets.put(pr, piece)
                ops += more
                own[piece] = info['key'] or '$model_' + piece
            ops.append({'op': 'add', 'cell': ck, 'base': own[piece], 'p': p, 's': 1})
        for tag, (k, p, arrive, to) in B.exits.items():
            name = 'mo_%s_%s' % (key, tag)
            ops.append({'op': 'add', 'cell': ck, 'base': k, 'p': p, 's': 1, 'name': name})
            places[(key, tag)] = (ck, name, arrive, to)
        rep['places'][key] = full
        rep['pieces'] += len(B.pieces)
        rep['things'] += len(B.things)
        rep['lights'] += len(B.lights)
        rep['seeds'][key] = B.seed
    # the lockers of her old base go to the port berthing (empty: what they held stayed with the old copies)
    lockers = sorted(k for k, r in pr.records.items() if k.startswith('+') and r.get('type') == 'CONT' and (recordio.field(r, 'EDID') or '').startswith(prefix + 'Ship'))
    for (x, y), rk in zip(LOCKER_SPOTS, lockers):
        ops.append({'op': 'add', 'cell': cells['second'], 'base': rk, 'p': [x, y, 0.0, 0.0, 0.0, 0.0], 's': 1})
    rep['lockers'] = min(len(LOCKER_SPOTS), len(lockers))
    door_key = gd.key(forms[DOOR])
    Z = battleship.missouri()['levels']

    def on_ship(lx, ly, lz, face):
        x, y = shipplace.to_world(sx_, sy_, turn, lx, ly)
        return [round(x, 1), round(y, 1), round(sz_ + lz, 1), 0.0, 0.0, round((turn + face) % math.tau, 4)]

    def cell_at(x, y):
        c = gd.grid(world).get((int(x // 4096), int(y // 4096)))
        return gd.key(c) if c is not None else None
    for tag, (lx, ly, lz) in (('qd', battleship.SPOTS['qd']), ('bridge', (battleship.SPOTS['bridge'][0], battleship.SPOTS['bridge'][1], Z[2]))):
        p = on_ship(lx, ly + 18, lz, math.pi / 2)
        ck = cell_at(p[0], p[1])
        name = 'mo_deck_' + tag
        ops.append({'op': 'add', 'cell': ck, 'base': door_key, 'p': p, 's': 1, 'name': name})
        arrive = on_ship(lx, ly + 150, lz + 10, 0.0)
        places[('deck', tag)] = (ck, name, arrive[:3] + [arrive[5]], ('second', 'qd') if tag == 'qd' else ('pilot', 'out'))
    for (key, tag), (ck, name, _arrive, to) in places.items():
        _oc, oname, (x, y, z, rz), _t = places[to]
        ops.append({'op': 'tel', 'cell': ck, 'ref': '$' + name, 'tel': {'door': '$' + oname, 'p': [round(x, 2), round(y, 2), round(z, 2), 0.0, 0.0, round(rz % math.tau, 4)]}})
    rep['doors'] = len(places)
    # the gangway down her side, the pier from its foot to the shore, the marker
    gy = battleship.SPOTS['gangway_y']
    hb = battleship.half_beam(gy)
    ground = roadgen.Ground(gd, pr, world)
    start = hb + GANG_RUN + 250                             # (the pier starts at the gangway's landing)

    def pier_line(sgn):
        """(how far from the landing to land, straight out from her side; the line) or None when it meets no land."""
        gx, gyw = shipplace.to_world(sx_, sy_, turn, sgn * hb, gy)
        ex, ey = shipplace.to_world(sx_, sy_, turn, sgn * (hb + 1), gy)
        nx, ny = ex - gx, ey - gyw
        bx, by = shipplace.to_world(sx_, sy_, turn, sgn * start, gy)
        water = ground.water(gx, gyw) or sz_
        d = 0.0
        while d <= PIER_MOST:
            g = ground.at(bx + nx * d, by + ny * d)
            if g is None:
                return None
            if g >= water + landmarks.DECK - 8.0:
                return d, (gx, gyw, nx, ny, bx, by, water)
            d += 64.0
        return None
    lines = {sgn: pier_line(sgn) for sgn in (1, -1)}
    rep['shore'] = {('port' if k > 0 else 'starboard'): (round(v[0]) if v else None) for k, v in lines.items()}
    found = [(v[0], k) for k, v in lines.items() if v]
    if not found or landmarks.DOCK not in forms:
        raise ValueError('No shore lies within %d of either side of her gangway, so there is no pier to bring you aboard: '
                         'stand her nearer the land.' % PIER_MOST)
    far, sgn = min(found)
    gx, gyw, nx, ny, bx, by, water = lines[sgn][1]
    deck = water + landmarks.DECK
    out_yaw = math.atan2(nx, ny) % math.tau
    more, info = modelsets.put(pr, 'mo_gangway')
    ops += more
    face = 0.0 if sgn > 0 else math.pi
    ops.append({'op': 'add', 'cell': cell_at(gx, gyw), 'base': info['key'] or '$model_mo_gangway',
                'p': [round(gx, 1), round(gyw, 1), round(sz_ + battleship.deck_z(gy), 1), 0.0, 0.0, round((turn + face) % math.tau, 4)], 's': 1})
    rep['gangway'] = [round(gx), round(gyw)]
    rep['pier'] = 0
    n = int(math.ceil((far + landmarks.DOCK_STEP / 2) / landmarks.DOCK_STEP)) + landmarks.LANDING
    for k in range(n):
        dd = landmarks.DOCK_STEP * (k + 0.5) - 140
        x, y = bx + nx * dd, by + ny * dd
        ck = cell_at(x, y)
        if ck is None:
            raise ValueError('Her pier would leave the map before it reaches the shore.')
        ops.append({'op': 'add', 'cell': ck, 'base': gd.key(forms[landmarks.DOCK]), 'p': [round(x, 1), round(y, 1), round(water + landmarks.DOCK_UP, 1), 0.0, 0.0, round(out_yaw, 4)], 's': 1})
        g = ground.at(x, y)
        if landmarks.PYLON[0] in forms and k % 2 == 0 and g is not None and g <= water - 24:
            ops.append({'op': 'add', 'cell': ck, 'base': gd.key(forms[landmarks.PYLON[0]]), 'p': [round(x, 1), round(y, 1), round(water + landmarks.PYLON[1], 1), 0.0, 0.0, round(out_yaw, 4)], 's': 1})
        rep['pier'] += 1
    mx, my = bx + nx * (far + 200), by + ny * (far + 200)
    m = worldrec.marker_op(gd, world, [round(mx, 1), round(my, 1), round((ground.at(mx, my) or deck) + 40.0, 1)], MARKER[0], MARKER[1])
    if m.get('cell'):
        ops.append(m)
        rep['marker'] = MARKER[0]
    rep['side'] = 'port' if sgn > 0 else 'starboard'
    rep['pier_long'] = round(far + 250)
    rep['ship'] = [sx_, sy_, sz_, turn]
    return ops, rep


def walk(gd, pr, world, report, step=16.0):
    """The walk aboard as the collision holds it: from the pier's land end, along the pier, up the gangway and on to her
    deck, every `step` the highest solid underfoot (the dock pieces', the gangway's, her own, the ground). Returns {'rise':
    the biggest rise or fall between two samples, 'gaps': samples with nothing underfoot over the water, 'end': how high
    over her deck the walk ends, 'samples'}. A walker steps up about 30 at most."""
    import hkshape
    import shipplace
    found = _forms(gd, (landmarks.DOCK,))
    dock = gd.key(found[landmarks.DOCK]) if landmarks.DOCK in found else None
    ship, gang = modelsets.record_of(pr, 'missouri'), modelsets.record_of(pr, 'mo_gangway')
    things = []
    for c in pr.cells.values():
        for r in c['refs'].values():
            if r.get('removed') or not r.get('p'):
                continue
            b = r.get('base')
            if b in (ship, gang):
                path = 'meshes\\' + recordio.field(pr.records[b], 'MODL')
            elif b == dock:
                path = 'meshes\\' + gd.describe(found[landmarks.DOCK])[3]
            else:
                continue
            things.append((path, r['p']))
    shapes = {}

    def tris(path):
        if path not in shapes:
            out = []
            for sh in hkshape.collision_shapes(gd.read_file(path)):
                if sh['layer'] in hkshape.LAYERS_SOLID:
                    v, i = sh['v'], sh['i']
                    out += [tuple(tuple(v[i[k + a] * 3:i[k + a] * 3 + 3]) for a in range(3)) for k in range(0, len(i) - 2, 3)]
            shapes[path] = out
        return shapes[path]

    def under(x, y, z_top):
        best = None
        for path, p in things:
            if abs(x - p[0]) > 10000 or abs(y - p[1]) > 10000:
                continue
            c, s = math.cos(p[5]), math.sin(p[5])
            dx, dy = x - p[0], y - p[1]
            lx, ly = dx * c - dy * s, dx * s + dy * c          # (into the thing's own frame: the game turns clockwise)
            for a, b, cc in tris(path):
                if min(a[0], b[0], cc[0]) > lx or max(a[0], b[0], cc[0]) < lx or min(a[1], b[1], cc[1]) > ly or max(a[1], b[1], cc[1]) < ly:
                    continue
                d = (b[1] - cc[1]) * (a[0] - cc[0]) + (cc[0] - b[0]) * (a[1] - cc[1])
                if abs(d) < 1e-9:
                    continue
                u = ((b[1] - cc[1]) * (lx - cc[0]) + (cc[0] - b[0]) * (ly - cc[1])) / d
                v = ((cc[1] - a[1]) * (lx - cc[0]) + (a[0] - cc[0]) * (ly - cc[1])) / d
                if u < -1e-6 or v < -1e-6 or u + v > 1 + 1e-6:
                    continue
                h = p[2] + u * a[2] + v * b[2] + (1 - u - v) * cc[2]
                if h <= z_top and (best is None or h > best):
                    best = h
        return best
    ground = roadgen.Ground(gd, pr, world)
    sx, sy, sz, turn = report['ship']
    sgn = 1 if report['side'] == 'port' else -1
    gy = battleship.SPOTS['gangway_y']
    hb = battleship.half_beam(gy)
    a = shipplace.to_world(sx, sy, turn, sgn * (hb - 300), gy)                   # (on her deck, inboard of the rail)
    b = shipplace.to_world(sx, sy, turn, sgn * (hb + GANG_RUN + 250 + report['pier_long'] + 300), gy)
    L = math.hypot(b[0] - a[0], b[1] - a[1])
    ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
    water = ground.water(*a) or 0.0
    out = {'rise': 0.0, 'gaps': 0, 'samples': 0}
    last = None
    d = 0.0
    z = sz + battleship.deck_z(gy) + 60
    while d <= L:
        x, y = a[0] + ux * d, a[1] + uy * d
        h = under(x, y, (last if last is not None else z) + 40)
        g = ground.at(x, y)
        if g is not None and (h is None or g > h):
            h = g
        if h is None or h < water - 1:
            out['gaps'] += 1
        elif last is not None and abs(h - last) > out['rise']:
            out['rise'] = abs(h - last)
            out['worst'] = [round(d), round(last, 1), round(h, 1)]       # (how far out from her deck, from what to what)
        if h is not None:
            last = h
        out['samples'] += 1
        d += step
    out['deck'] = round(sz + battleship.deck_z(gy), 1)
    out['rise'] = round(out['rise'], 1)
    return out


def navmesh_ops(gd, pr, names):
    """After board's ops are applied (names: project.names as they left it): each place's navmesh as an op."""
    import navbuild
    out, rep = [], {}
    for key in PLACES:
        ck = names.get('mo_' + key)
        if not ck:
            continue
        try:
            data, r = navbuild.generate(gd, pr, ck)
        except navbuild.NavError as e:
            rep[key] = str(e)
            continue
        out.append({'op': 'navmesh', 'cell': ck, 'mesh': data})
        rep[key] = r
    return out, rep
