"""Waikiki's money (the user, 25 Nov 2026: "Go ahead and make those the currency"; the decisions in docs/waikiki-decisions.md).

- **Kala** (kālā), the everyday money, in place of caps. The game's own caps (Caps001, form 0x0F, the money every trader
  barters in) get a new name, model and Pip-Boy picture: a pre-war brass resort token, the Kilauea's own machine token,
  which the court backs. The game's fonts are cp1252 and have no ā, so on screen it is "Kala" (as g2pzh writes pinyin
  without tone marks). The Pip-Boy's and barter screen's "CAPS" label is the interface's own text, not changed here.
- **An tongbao** (`TONGBAO`), the Huáng money: a brass cash coin with a square hole, strung on cord, cast from salvage
  (partly melted kala). A MISC with weight and value.
- **Charged power cells**, the pirates' trade money: the game's Energy Cell (`CELL`). The Vault sells them (decided): a
  Cell Exchange machine in Vault 50's cell charging room sells energy and microfusion cells for kala (`EXCHANGE`).
- **Bango tags** (`BANGO`), plantation scrip a Huáng house pays its farmers, good only at the house store: the item and
  its trading mode; the store is placed with the An questline (`store_lines`).

**Paying in coin.** The barter window only knows kala, so a trader who takes another money has a line "Let's trade in
tongbao." (or cells, or bango tags): its script turns every coin you carry into kala at that trader's rate and opens the
barter window; when it closes, the quest FOLabMoney turns the kala you have over what you had before back into coins at
the same rate (whole coins; the rest stays kala). So a Huáng trader takes tongbao at `RATES['tongbao']` and pays you in
them; a pirate trader takes cells at `RATES['cells']`, better than their worth in kala.
- Huáng traders: northfolk's (`HUANG_TRADERS`). Pirate traders: piratedeal's, once you deal with them.
- **The money changer** (Qianshang [proposal], a Huáng at the Makapuʻu gate market's stalls): tongbao for kala at
  `CHANGER_BUYS`, kala for tongbao at `CHANGER_SELLS`; Barter 50 gets `CHANGER_BETTER` for good.

**Goods into money** (`REPRICE`): what was paid in goods because money was undecided, in the mod's lines: the court's
toll, the catchers' bribe and the collectors' share in kala, the pirates' road toll in cells, the brokering pay in each
side's money. The words that named the goods are reworded and voiced again (`REWORD`). The Kailua trader's "caps" lines
say kala (`REWORD`).

    plan(gd, pr)       {'rows', 'skipped', ...}
    apply(pr, gd, P)   one Undo (VOICE: the lines added and the ones reworded)
"""
import json
import math
import re

import modelsets
import recordio
import texpaint as tp
from modelsets import look

LABEL = "Waikiki's money: kala, tongbao, power cells"
SET = 'money'
QUEST, SCRIPT = 'FOLabMoney', 'FOLabMoneyScript'
VOICE = [QUEST]                          # (the quests whose lines are reworded are added by apply)
VOICE_ONLY = set()                       # (of those, only the new lines and the reworded ones: set by apply)
KALA = 'Kala'
CAPS = 0x0F                              # (Caps001: the engine's own money)
CELL, CELL_MF = 'AmmoSmallEnergyCell', 'AmmoMicroFusionCell'
TONGBAO = ('FOLabTongbao', 'An Tongbao', 8, 0.02)          # (editor ID, name, value in kala, weight)
BANGO = ('FOLabBangoTag', 'Bango Tag', 0, 0.02)
# what a trader takes a coin at (kala), in the trading modes: 1 tongbao, 2 cells, 3 bango
RATES = {'tongbao': 10, 'cells': 4, 'bango': 5}
MODES = {'tongbao': 1, 'cells': 2, 'bango': 3}
CHANGER_BUYS, CHANGER_BETTER, CHANGER_SELLS, CHANGER_BARTER = 8, 9, 12, 50
EXCHANGE = {'energy': (CELL, 10, 30), 'microfusion': (CELL_MF, 10, 50)}     # (what, how many, kala)
HUANG_TRADERS = ('FOLabHuangTraderKailua', 'FOLabHuangHerbalistKaneohe')
PIRATE_TRADERS = (('FOLabPirateTraderKahala', 'dealkahala'), ('FOLabPirateTraderMarina', 'dealmarina'))
CHANGER = ('FOLabMoneyChanger', 'Qianshang')
GATE, STALL = "Makapu'u Gate", 'FOLabBambooMarketStall'
GATE_GUARD = 'FOLabMakapuuGuard'
VAULT = 'FOLabKaauVault'
RACK, NEAR_RACK = 'ComputerRack01', ('LootAmmoBoxMicroFusionCellsLock', 'LootAmmoBoxPowerCellsRNDLock', 'DrainedMicrofusionCell')
MACHINE = ('NVDLC01VendingArtDeco', 'FOLabCellExchange', 'Cell Exchange')
DOOR_CLEAR, PEOPLE_CLEAR = 160.0, 120.0
# goods paid in the mod's lines, by quest: (game item, count) -> (money, count); money 'kala', 'cells', 'tongbao'
STIM = 'Stimpak'
REPRICE = {
    'FOLabPirateDeals': {('RemoveItem', STIM, 1): ('kala', 10)},                         # (the court's toll post)
    'FOLabCatchers': {('RemoveItem', STIM, 2): ('kala', 20)},                            # ("Take these and forget you saw me.")
    'FOLabTributeDay': {('RemoveItem', STIM, 1): ('kala', 10)},                          # ("Add this to the Kahuna's share")
    'FOLabParley': {('RemoveItem', STIM, 1): ('cells', 5), ('RemoveItem', STIM, 2): ('cells', 10)},
    'FOLabBroker': {('AddItem', STIM, 2): ('kala', 20), ('AddItem', STIM, 1): ('kala', 10),
                    ('AddItem', 'NVHealingPowder', 2): ('tongbao', 2), ('AddItem', 'NVHealingPowder', 1): ('tongbao', 1)},
}
SHOWN = {'kala': KALA, 'cells': 'Energy Cells', 'tongbao': 'Tongbao'}
REWORD = {   # the words a line or topic had: what it says now
    "Everyone's the Kahuna's guest. Toll's a stimpak.": "Everyone's the Kahuna's guest. Toll's ten kala.",
    "Pay the toll. (1 Stimpak)": "Pay the toll. (10 Kala)",
    "Two. That's the soft touch rate. Go on.": "Ten. That's the soft touch rate. Go on.",
    "Silk. Guns. Bullets. You pay caps, you look.": "Silk. Guns. Bullets. You pay kala, you look. Tongbao, better.",
    "Come back. Bring caps.": "Come back. Bring tongbao.",
}
WORDS = {
    'trade_tongbao': "Let's trade in tongbao.", 'trade_cells': "Let's trade in cells.",
    'huang_yes': "Tongbao. Good. Tongbao count ten kala here.",
    'pirate_yes': "Charged cells? Now you're talking. Four kala a cell, and I pay in cells.",
    'hello': "Tongbao, kala. I change. Small cut.",
    'sell10': "Change ten tongbao for kala.", 'sellall': "Change all my tongbao for kala.", 'buy10': "Buy ten tongbao. (%d Kala)" % (10 * CHANGER_SELLS),
    'haggle': "Eight kala a coin? That's robbery.", 'what': "What is a tongbao?",
    'sell10_yes': "Ten tongbao. Eighty kala. Count it.", 'sell10_better': "Ten tongbao. Ninety kala. Do not tell.",
    'sellall_yes': "All. Eight kala each. Count it.", 'sellall_better': "All. Nine kala each. For you.",
    'buy10_yes': "Ten tongbao. Hold them close, outsider.",
    'haggle_yes': "...Nine. For you, nine. Do not tell the others.",
    'haggle_no': "Eight. Or go to Waikiki and eat kala.",
    'what_yes': "Our money. Cast here, from what the sea gives. Some from your kala, melted. "
                "At a Huang shop a tongbao counts ten kala. Here I buy for eight and sell for twelve. That is my rice.",
    'exchange': "Vault 50 Cell Exchange. Charged cells, sold for kala.",
    'exchange_short': "Not enough kala.", 'exchange_sold': "The machine hums and drops the cells into the tray.",
}
TRADE_FROM = 'VendorContainerChet'


# ---------- pictures ----------
BRASS, BRASS_DARK = (196, 160, 82), (120, 92, 40)
BRONZE = (150, 128, 72)
CORD = (150, 40, 34)


def _brass_face(kind):
    """A coin's face, the whole picture the disc (its edge at the picture's edge), stamped work raised."""
    S = 128
    c = tp.Canvas(S, S)
    n = tp.Noise({'kala': 401, 'tongbao': 402, 'bango': 403}[kind], 10)
    base = BRASS if kind != 'tongbao' else BRONZE

    def fn(x, y):
        d = math.hypot(x - S / 2 + 0.5, y - S / 2 + 0.5) / (S / 2)
        col = tp._shade(base, 0.86 + 0.18 * n.at(x * 6.0 / S, y * 6.0 / S))
        if kind == 'tongbao':
            col = tp._mix(col, (84, 120, 96), 0.25 * max(0.0, n.at(x * 3.0 / S + 7, y * 3.0 / S) - 0.4))     # (verdigris)
        h = 0.5
        if 0.84 < d < 0.95:                 # (the raised rim)
            h, col = 0.7, tp._shade(col, 1.08)
        return col, h
    c.paint(fn)
    dark = tp._shade(base, 0.62)
    if kind == 'kala':
        c.line((22, 48), (106, 48), 1.5, dark)                                     # (the band the words sit in)
        x0 = (S - c.text_wide('KILAUEA', 11)) / 2
        c.text('KILAUEA', x0, 32, 11, dark, thick=2.2)
        # the volcano and its crown of fire
        c.line((34, 92), (56, 62), 3, dark)
        c.line((56, 62), (72, 62), 3, dark)
        c.line((72, 62), (94, 92), 3, dark)
        c.line((34, 92), (94, 92), 2, dark)
        for a, b in (((60, 58), (52, 46)), ((64, 57), (64, 44)), ((68, 58), (76, 46))):
            c.line(a, b, 2.4, dark)
        x0 = (S - c.text_wide('1 PLAY', 9)) / 2
        c.text('1 PLAY', x0, 98, 9, dark, thick=2.0)
    elif kind == 'tongbao':
        c.rect(52, 52, 76, 76, lambda x, y, col, h: ((26, 22, 16), 0.1))          # (the square hole: dark, and the cord through it)
        # four characters round the hole, as strokes (top 二, bottom 王, left and right 口)
        for a, b in (((56, 22), (72, 22)), ((54, 32), (74, 32)), ((54, 92), (74, 92)), ((56, 100), (72, 100)), ((54, 108), (74, 108)),
                     ((64, 92), (64, 108)), ((22, 56), (36, 56)), ((22, 72), (36, 72)), ((22, 56), (22, 72)), ((36, 56), (36, 72)),
                     ((92, 56), (106, 56)), ((92, 72), (106, 72)), ((92, 56), (92, 72)), ((106, 56), (106, 72)), ((92, 64), (106, 64))):
            c.line(a, b, 3.0, dark)
        c.line((48, 48), (80, 48), 2.4, dark)
        c.line((48, 80), (80, 80), 2.4, dark)
    else:                                   # (bango: a hole to hang it by, the house's mark, a number)
        c.rect(58, 14, 70, 26, lambda x, y, col, h: ((26, 22, 16), 0.1))
        x0 = (S - c.text_wide('NO', 12)) / 2
        c.text('NO', x0, 36, 12, dark, thick=2.4)
        x0 = (S - c.text_wide('147', 22)) / 2
        c.text('147', x0, 58, 22, dark, thick=3.6)
        c.line((40, 94), (88, 94), 2.4, dark)
    return c


def _plain(colour, seed, grain=0.15, size=32):
    c = tp.Canvas(size, size)
    n = tp.Noise(seed, 4)
    c.paint(lambda x, y: (tp._shade(colour, 1.0 - grain / 2 + grain * n.at(x * 4.0 / size, y * 4.0 / size)), 0.5))
    return c


modelsets.TEXTURES.update({
    'money/kala_face': lambda: _brass_face('kala'), 'money/tongbao_face': lambda: _brass_face('tongbao'),
    'money/bango_face': lambda: _brass_face('bango'), 'money/brass': lambda: _plain(BRASS, 411),
    'money/bronze': lambda: _plain(BRONZE, 412), 'money/cord': lambda: _plain(CORD, 413, 0.25)})


# ---------- models ----------
def kala_model():
    """A brass token two units across, lying flat, the stamped face up."""
    L = {'edge': look('money/brass', tile=None), 'face': look('money/kala_face', tile=None)}
    return {'name': 'FOLabKalaToken', 'looks': L,
            'parts': [{'shape': 'cylinder', 'r': 1.0, 'h': 0.16, 'sides': 24, 'look': 'edge', 'cap_look': 'face', 'material': 'metal'}]}


def tongbao_model():
    """Five cash coins strung on a red cord, lying on their sides along y, the cord's knotted ends past them."""
    L = {'edge': look('money/bronze', tile=None), 'face': look('money/tongbao_face', tile=None), 'cord': look('money/cord', tile=None)}
    P = []
    for i in range(5):
        y = -0.9 + 0.45 * i
        P.append({'shape': 'cylinder', 'r': 0.85, 'h': 0.12, 'sides': 20, 'turn': [90, 0, 8 - 4 * i], 'at': [0, y + 0.06, 0.85],
                  'look': 'edge', 'cap_look': 'face', 'material': 'metal'})
    P += [{'shape': 'box', 'size': [0.14, 3.0, 0.14], 'at': [0, 0, 0.85], 'look': 'cord'},
          {'shape': 'ball', 'r': 0.22, 'sides': 8, 'rings': 5, 'at': [0, 1.55, 0.85], 'look': 'cord'},
          {'shape': 'ball', 'r': 0.22, 'sides': 8, 'rings': 5, 'at': [0, -1.55, 0.85], 'look': 'cord'}]
    return {'name': 'FOLabTongbao', 'looks': L, 'parts': P}


def bango_model():
    """A stamped brass tag, oval, lying flat."""
    L = {'edge': look('money/brass', tile=None), 'face': look('money/bango_face', tile=None)}
    return {'name': 'FOLabBangoTag', 'looks': L,
            'parts': [{'shape': 'cylinder', 'r': 1.1, 'h': 0.08, 'sides': 24, 'scale': [0.85, 1.0, 1.0], 'look': 'edge', 'cap_look': 'face',
                       'material': 'metal'}]}


def _build(desc, key):
    import modelmake
    import nifmake
    made = modelmake.make(desc)
    made['nif'] = nifmake.build_dropped(desc['name'], made['shapes'], mass=0.05, material='metal')
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
    return {'kala': (kala_model(), _build(kala_model(), 'kala_token')), 'tongbao': (tongbao_model(), _build(tongbao_model(), 'tongbao')),
            'bango': (bango_model(), _build(bango_model(), 'bango_tag'))}


# ---------- Pip-Boy pictures (as the game's: pale shapes on clear, their lines cut out) ----------
def _seg(px, py, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    ln = dx * dx + dy * dy
    t = max(0.0, min(1.0, ((px - a[0]) * dx + (py - a[1]) * dy) / ln)) if ln else 0.0
    return math.hypot(px - a[0] - t * dx, py - a[1] - t * dy)


def _strokes(words, x, y, high):
    """texpaint's block letters as line segments."""
    out, unit = [], high / 6.0
    for ch in words.upper():
        for s in tp.LETTERS.get(ch, ()):
            out += [((x + p[0] * unit, y + p[1] * unit), (x + q[0] * unit, y + q[1] * unit)) for p, q in zip(s, s[1:])]
        x += (5.6 if ch != ' ' else 3.5) * unit
    return out


def _coin_icon(cx, cy, rx, ry, thick):
    """inside(x, y) of a coin seen from above at a slant: its top ellipse and the band of its edge below."""
    def inside(x, y):
        e = ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1.0
        band = abs(x - cx) <= rx and cy <= y <= cy + thick + ry * math.sqrt(max(0.0, 1 - ((x - cx) / rx) ** 2))
        return e or band
    return inside


def icon(kind):
    """256 x 256 RGBA bytes: the Pip-Boy's picture of the money."""
    S = 256
    pale = (214, 214, 206)
    shapes, cuts, holes = [], [], []
    if kind == 'kala':
        cx, cy, rx, ry = 128, 118, 92, 58
        shapes.append(_coin_icon(cx, cy, rx, ry, 18))
        ring = lambda x, y, k: abs(math.hypot((x - cx) / (rx * k), (y - cy) / (ry * k)) - 1.0) * ry * k
        cuts += [lambda x, y: ring(x, y, 0.86) < 2.6, lambda x, y: abs(math.hypot((x - cx) / rx, (y - cy - 18) / ry) - 1) * ry < 2.2
                 and y > cy and abs(x - cx) < rx - 2]
        segs = [((96, 150), (118, 122)), ((118, 122), (138, 122)), ((138, 122), (160, 150)), ((96, 150), (160, 150)),
                ((123, 117), (116, 106)), ((128, 116), (128, 104)), ((133, 117), (140, 106))]
        segs += _strokes('KILAUEA', 128 - 72 / 2, 86, 10)
        cuts.append(lambda x, y: any(_seg(x, y, a, b) < 2.6 for a, b in segs))
    elif kind == 'tongbao':
        segs_all = []
        for i, (cx, cy) in enumerate(((80, 112), (128, 124), (176, 136))):
            rx, ry = 58, 40
            shapes.append(_coin_icon(cx, cy, rx, ry, 10))
            holes.append(lambda x, y, cx=cx, cy=cy: abs(x - cx) < 11 and abs(y - cy) < 8)
            segs_all += [((cx - 26, cy - 20), (cx + 26, cy - 20)), ((cx - 26, cy + 20), (cx + 26, cy + 20))]
            ring = lambda x, y, cx=cx, cy=cy, rx=rx, ry=ry: abs(math.hypot((x - cx) / (rx * 0.85), (y - cy) / (ry * 0.85)) - 1.0) * ry * 0.85 < 2.2
            cuts.append(ring)
            if i < 2:                       # (the next coin's edge over this one)
                nx, ny = (128, 124) if i == 0 else (176, 136)
                cuts.append(lambda x, y, nx=nx, ny=ny: abs(math.hypot((x - nx) / 58, (y - ny) / 40) - 1.0) * 40 < 2.4 and x < nx)
        cuts.append(lambda x, y: any(_seg(x, y, a, b) < 2.4 for a, b in segs_all))
        cord = [((30, 96), (80, 112)), ((80, 112), (128, 124)), ((128, 124), (176, 136)), ((176, 136), (226, 150))]
        shapes.append(lambda x, y: any(_seg(x, y, a, b) < 4.5 for a, b in cord[:1] + cord[-1:]))
    else:
        cx, cy, rx, ry = 128, 122, 74, 60
        shapes.append(_coin_icon(cx, cy, rx, ry, 10))
        holes.append(lambda x, y: math.hypot(x - cx, (y - (cy - ry + 18)) * 1.3) < 8)
        segs = _strokes('147', 128 - 60 / 2, 112, 26) + _strokes('NO', 128 - 25 / 2, 88, 12)
        cuts.append(lambda x, y: any(_seg(x, y, a, b) < 3.0 for a, b in segs))
        cuts.append(lambda x, y: abs(math.hypot((x - cx) / (rx * 0.86), (y - cy) / (ry * 0.86)) - 1.0) * ry * 0.86 < 2.2)
    px = bytearray(S * S * 4)
    for y in range(S):
        for x in range(S):
            if any(h(x, y) for h in holes) or not any(s(x, y) for s in shapes) or any(cut(x, y) for cut in cuts):
                continue
            i = 4 * (y * S + x)
            px[i:i + 4] = bytes(pale + (255,))
    return bytes(px)


def icon_files():
    import dds
    return {'textures\\interface\\icons\\pipboyimages\\items\\folab_%s.dds' % k: dds.encode(256, 256, icon(k)) for k in ('kala', 'tongbao', 'bango')}


# ---------- records ----------
def _game(gd, edid, tags):
    f = next((f for f, (_i, r) in gd.forms.items() if r.tag in tags and gd.edid(f) == edid), None)
    if f is None:
        raise ValueError('the game has no %s' % edid)
    return f


def _mod_key(pr, edid, tag=None):
    return next((k for k, r in pr.records.items() if (tag is None or r.get('type') == tag) and r.get('subs') and recordio.field(r, 'EDID') == edid), None)


def _icon_path(kind):
    return 'interface\\icons\\pipboyimages\\items\\folab_%s.dds' % kind


def kala_record(gd, made):
    """Caps001 as the mod has it: Kala, the token's model and picture; its value, weight and sounds the game's."""
    rec = json.loads(json.dumps(recordio.load(gd, CAPS)))
    subs = []
    for s in rec['subs']:
        if s['tag'] == 'MODT':
            continue
        if s['tag'] == 'FULL':
            s['value'] = KALA
        elif s['tag'] == 'MODL':
            s['value'] = made['mesh'][7:]
        elif s['tag'] == 'ICON':
            s['value'] = _icon_path('kala')
        elif s['tag'] == 'OBND':
            s['fields'] = [dict(q, value=int(round(v))) for q, v in zip(s['fields'], made['box'])]
        subs.append(s)
    rec['subs'] = subs
    return rec


def coin_record(gd, kind, made):
    """A MISC of the mod's own in Caps001's layout and with its sounds (picked up and put down as money is)."""
    edid, name, value, weight = TONGBAO if kind == 'tongbao' else BANGO
    rec = json.loads(json.dumps(recordio.load(gd, CAPS)))
    rec['src'] = ''
    subs = []
    for s in rec['subs']:
        if s['tag'] in ('MODT', 'SCRI'):
            continue
        if s['tag'] == 'EDID':
            s['value'] = edid
        elif s['tag'] == 'FULL':
            s['value'] = name
        elif s['tag'] == 'MODL':
            s['value'] = made['mesh'][7:]
        elif s['tag'] == 'ICON':
            s['value'] = _icon_path(kind)
        elif s['tag'] == 'OBND':
            s['fields'] = [dict(q, value=int(round(v))) for q, v in zip(s['fields'], made['box'])]
        elif s['tag'] == 'DATA':
            s['fields'] = [dict(q, value=value if q.get('name') == 'Value' else float(weight) if q.get('name') == 'Weight' else q.get('value'))
                           for q in s['fields']]
        subs.append(s)
    rec['subs'] = subs
    return rec


def _cond(fn, op, value, p1='', p2=0, run=0, glob=None):
    c = {'or': False, 'use_target': False, 'op': op, 'fn': fn, 'p1': p1, 'p2': p2, 'run': run, 'ref': '', 'value': float(value)}
    if glob:
        c['global'] = glob
    return c


def _var_index(pr, quest_edid):
    """{variable name (lower case): index} of a quest's script in the mod."""
    qk = _mod_key(pr, quest_edid, 'QUST')
    if not qk:
        return None, {}
    sk = recordio.field(pr.records[qk], 'SCRI')
    out, last = {}, None
    for sub in (pr.records.get(sk) or {'subs': []})['subs']:
        if sub['tag'] == 'SLSD':
            last = next(f['value'] for f in sub['fields'] if f.get('name') == 'Index')
        elif sub['tag'] == 'SCVR' and last is not None:
            out[sub['value'].lower()] = last
    return qk, out


def quest_source():
    """The script that settles a trade in coin once the barter window has closed."""
    L = ['scn %s' % SCRIPT, 'short mode', 'short step', 'short before', 'short n', 'short k', 'short back', 'short better', 'float waited', '',
         'Begin GameMode', '\tif step < 2', '\t\treturn', '\tendif',
         '\tif step == 2', '\t\tset waited to waited + GetSecondsPassed', '\t\tif waited < 2', '\t\t\treturn', '\t\tendif', '\tendif',
         '\tset n to player.GetItemCount Caps001', '\tset n to n - before', '\tset back to 0']
    for kind, mode in MODES.items():
        rate = RATES[kind]
        item = {'tongbao': TONGBAO[0], 'cells': CELL, 'bango': BANGO[0]}[kind]
        L += ['\tif mode == %d && n >= %d' % (mode, rate), '\t\tset back to n / %d' % rate,
              '\t\tif back * %d > n' % rate, '\t\t\tset back to back - 1', '\t\tendif',
              '\t\tif back > 0', '\t\t\tset k to back * %d' % rate, '\t\t\tplayer.RemoveItem Caps001 k 1', '\t\t\tplayer.AddItem %s back 1' % item,
              '\t\tendif', '\tendif']
    L += ['\tset step to 0', '\tset mode to 0', '\tset waited to 0', 'End', '',
          'Begin MenuMode 1053', '\tif step == 2', '\t\tset step to 3', '\tendif', 'End', '']
    return '\n'.join(L)


def trade_in(kind):
    """A line's end script: every coin of that kind into kala at the trader's rate, then the barter window."""
    item = {'tongbao': TONGBAO[0], 'cells': CELL, 'bango': BANGO[0]}[kind]
    q = QUEST
    return '\n'.join(['set %s.before to player.GetItemCount Caps001' % q, 'set %s.n to player.GetItemCount %s' % (q, item),
                      'if %s.n > 0' % q, 'player.RemoveItem %s %s.n 1' % (item, q), 'set %s.k to %s.n * %d' % (q, q, RATES[kind]),
                      'player.AddItem Caps001 %s.k 1' % q, 'endif', 'set %s.mode to %d' % (q, MODES[kind]), 'set %s.waited to 0' % q,
                      'set %s.step to 2' % q, 'ShowBarterMenu'])


def store_lines(gd, pr, topic, quest_key, who):
    """The bango store's line, for the house store the An questline stands (the quests session's step): a plain line."""
    import api_quests as aq
    tag = _mod_key(pr, BANGO[0], 'MISC')
    l = aq.new_line_plain(gd, pr, topic, quest_key, who, "Tags. Five kala each, in the house store. Nowhere else.",
                          conditions=[_cond(47, '>=', 1, tag, 0, 1)])
    l['end'] = {'source': trade_in('bango'), 'parts': None}
    return [l]


# ---------- where ----------
def _refs_of(gd, pr, cell_key):
    out = []
    for rk, r in ((pr.cells.get(cell_key) or {}).get('refs') or {}).items():
        b = r.get('base')
        if not b or r.get('removed') or not r.get('p'):
            continue
        out.append((rk, b, _edid_of(gd, pr, b), r))
    return out


_ED = {}


def _edid_of(gd, pr, key):
    if key not in _ED:
        if key.startswith('+'):
            r = pr.records.get(key) or {}
            _ED[key] = recordio.field(r, 'EDID') if r.get('subs') else ''
        else:
            try:
                _ED[key] = gd.edid(gd.from_key(key)) or ''
            except (KeyError, ValueError):
                _ED[key] = ''
    return _ED[key]


def _type_of(gd, pr, key):
    if key.startswith('+'):
        return (pr.records.get(key) or {}).get('type')
    try:
        return gd.forms[gd.from_key(key)][1].tag
    except (KeyError, ValueError):
        return None


def _changer_spot(gd, pr, rep):
    """Beside the market stall nearest the Makapuʻu gate's marker, in front of it, over a navmesh, clear of the gate guard."""
    import activity
    import factionfolk as ff
    import northfolk
    mk = ff._markers(pr)
    if GATE not in mk:
        rep['skipped'].append(('changer', 'no %s marker' % GATE))
        return None
    gck, g = mk[GATE]
    ctx = activity.Ctx(gd, pr)
    stalls = sorted((p for p in ctx.of(STALL) if math.hypot(p[0] - g[0], p[1] - g[1]) < 4000), key=lambda p: math.hypot(p[0] - g[0], p[1] - g[1]))
    guard = ctx.of(GATE_GUARD)
    for st in stalls:
        fx, fy = northfolk._frame(st, 0.0, -260.0)
        for r in (0, 100, 200, 300):
            for t in range(8 if r else 1):
                a = t * 2 * math.pi / 8
                px, py = fx + r * math.sin(a), fy + r * math.cos(a)
                if any(math.hypot(px - q[0], py - q[1]) < 300 for q in guard):
                    continue
                s = ctx.spot(px, py, 200.0)
                if s:
                    rz = northfolk.facing(s[:2], st[:2]) + math.pi
                    gates = ctx.of(*activity.GATES)
                    return {'p': [s[0], s[1], s[2], rz], 'cell': ctx.cell(s[0], s[1]), 'stall': [round(v) for v in st[:3]],
                            'from_gate_piece': round(min((math.hypot(s[0] - q[0], s[1] - q[1]) for q in gates), default=99999)),
                            'from_gate': round(math.hypot(s[0] - g[0], s[1] - g[1])),
                            'from_guard': round(min((math.hypot(s[0] - q[0], s[1] - q[1]) for q in guard), default=99999))}
    rep['skipped'].append(('changer', 'no open ground by the gate market\'s stalls'))
    return None


def _machine_spot(gd, pr, rep, box):
    """In Vault 50's cell charging room: beside a computer rack that has the room's cell boxes near, on the floor, clear of
    doors and people."""
    import lootplace
    vk = _mod_key(pr, VAULT, 'CELL')
    if not vk or vk not in pr.cells:
        rep['skipped'].append(('exchange', 'no %s' % VAULT))
        return None
    refs = _refs_of(gd, pr, vk)
    racks = [r for _k, _b, e, r in refs if e == RACK]
    near = [r['p'] for _k, _b, e, r in refs if e in NEAR_RACK]
    doors = [r['p'] for _k, b, _e, r in refs if _type_of(gd, pr, b) == 'DOOR']
    people = [r['p'] for _k, b, _e, r in refs if _type_of(gd, pr, b) in ('NPC_', 'CREA', 'LVLN', 'LVLC')]
    racks.sort(key=lambda r: min((math.hypot(r['p'][0] - q[0], r['p'][1] - q[1]) for q in near), default=1e9))
    if not racks:
        rep['skipped'].append(('exchange', 'no computer rack in the Vault'))
        return None
    S = lootplace.Seat(gd, pr, None)
    S.solids.load_round([vk])
    for rack in racks[:4]:
        x0, y0, z0, _a, _b, rz = rack['p'][:6]
        c, s = math.cos(rz), math.sin(rz)
        for lx, ly in ((90, 0), (-90, 0), (130, 0), (-130, 0), (90, -60), (-90, -60), (170, 0), (-170, 0)):
            x, y = x0 + lx * c + ly * s, y0 - lx * s + ly * c
            if any(math.hypot(x - d[0], y - d[1]) < DOOR_CLEAR for d in doors) or any(math.hypot(x - q[0], y - q[1]) < PEOPLE_CLEAR for q in people):
                continue
            p = S.at(x, y, rz, box, z0, outside=False)
            if p and abs(p[2] - z0) < 12:
                rep['exchange_rack'] = [round(v) for v in rack['p'][:3]]
                return {'cell': vk, 'p': [p[0], p[1], p[2], rz], 'from_cells': round(min((math.hypot(x - q[0], y - q[1]) for q in near), default=-1)),
                        'from_door': round(min((math.hypot(x - d[0], y - d[1]) for d in doors), default=99999))}
    rep['skipped'].append(('exchange', 'no clear floor beside the charging room\'s racks'))
    return None


def _repriced(gd, pr):
    """[(line key, plain line, what changed)] for every line of REPRICE's quests that pays or takes goods named there, and
    every line or topic whose words are in REWORD."""
    import questrec as qr
    caps = gd.key(CAPS)
    money = {'kala': ('Caps001', caps), 'cells': (CELL, gd.key(_game(gd, CELL, ('AMMO',)))),
             'tongbao': (TONGBAO[0], _mod_key(pr, TONGBAO[0], 'MISC') or '$' + TONGBAO[0])}
    quests = {_mod_key(pr, q, 'QUST'): q for q in REPRICE}
    item_key = {}
    out, topics = [], []
    for k, rec in pr.records.items():
        t = rec.get('type')
        if t == 'DIAL':
            name = recordio.field(rec, 'FULL') if rec.get('subs') else ''
            if name in REWORD:
                topics.append((k, name, REWORD[name]))
            continue
        if t != 'INFO':
            continue
        l = qr.info_plain(rec)
        changed = []
        q = quests.get(l['quest'])
        src = (l.get('end') or {}).get('source') or ''
        if q:
            for (verb, item, n), (m, mn) in REPRICE[q].items():
                pat = re.compile(r'(?im)^(\s*player\.%s\s+)%s\s+%d\b' % (verb, item, n))
                if pat.search(src):
                    src = pat.sub(lambda mo: '%s%s %d' % (mo.group(1), money[m][0], mn), src)
                    changed.append('%s %s %d -> %s %d' % (verb, item, n, money[m][0], mn))
                    if verb == 'RemoveItem':
                        if item not in item_key:
                            item_key[item] = gd.key(_game(gd, item, ('ALCH', 'MISC', 'AMMO')))
                        for c in l['conditions']:
                            if c['fn'] == 47 and c['p1'] == item_key[item] and c['op'] == '>=' and int(c['value']) == n:
                                c['p1'], c['value'] = money[m][1], float(mn)
        for r in l['responses']:
            tag = re.match(r'^\s*(\[[A-Z ]+\]\s*)?', r['text']).group(0)      # ("[FAILED] " stays in front)
            if r['text'][len(tag):] in REWORD:
                changed.append('words: %r' % r['text'])
                r['text'] = tag + REWORD[r['text'][len(tag):]]
        if changed:
            if l.get('end') and src:
                l['end'] = {'source': src, 'parts': None}
            out.append((k, l, changed))
    return out, topics


# ---------- the plan ----------
def plan(gd, pr):
    rep = {'skipped': [], 'rows': []}
    if _mod_key(pr, QUEST, 'QUST'):
        rep['skipped'].append(('all', 'the mod already has %s (Undo first)' % QUEST))
        return rep
    rows = rep['rows']
    ch = _changer_spot(gd, pr, rep)
    if ch:
        rows.append(dict(ch, what='changer'))
    mf = _game(gd, MACHINE[0], ('ACTI',))
    mrec = recordio.load(gd, mf)
    ob = next((s for s in mrec['subs'] if s['tag'] == 'OBND'), None)
    box = [f['value'] for f in ob['fields']] if ob else [-40, -30, 0, 40, 30, 180]
    m = _machine_spot(gd, pr, rep, box)
    if m:
        rows.append(dict(m, what='exchange'))
    for e in HUANG_TRADERS:
        rows.append({'what': 'huang trader', 'edid': e, 'have': bool(_mod_key(pr, e, 'NPC_'))})
    for e, v in PIRATE_TRADERS:
        rows.append({'what': 'pirate trader', 'edid': e, 'have': bool(_mod_key(pr, e, 'NPC_'))})
    lines, topics = _repriced(gd, pr)
    for k, l, what in lines:
        rows.append({'what': 'repriced', 'line': k, 'changed': what})
    for k, old, new in topics:
        rows.append({'what': 'topic', 'topic': k, 'from': old, 'to': new})
    rep['box'] = box
    return rep


# ---------- the change ----------
def ops(gd, pr, P=None):
    import api_quests as aq
    import api_scripts
    import factionfolk as ff
    import huangland
    import huangradio
    import library
    import questrec as qr
    import waikikilife as WL
    from activity import _new_key
    P = P or plan(gd, pr)
    if any(w == 'all' for w, _x in P['skipped']):
        raise ValueError(P['skipped'][0][1])
    rows = P['rows']
    rep = {'made': [], 'skipped': list(P['skipped']), 'placed': {}, 'repriced': [], 'reworded': [], 'missing': []}
    out, extra = [], {}
    M = models()
    root = library.assets_dir(pr)
    for _d, made in M.values():
        for path, data in made['files'].items():
            library._put(root, path, data)
    for path, data in icon_files().items():
        library._put(root, path, data)

    def record(edid, rec, key=None):
        k = key or _new_key(pr)
        extra[k] = rec
        out.append({'op': 'record', 'key': k, 'record': rec})
        rep['made'].append(edid)
        return k
    # the money
    record('Caps001', kala_record(gd, M['kala'][1]), gd.key(CAPS))
    tong = record(TONGBAO[0], coin_record(gd, 'tongbao', M['tongbao'][1]))
    record(BANGO[0], coin_record(gd, 'bango', M['bango'][1]))
    # the quest that settles a trade in coin
    qk, qsk = _new_key(pr), _new_key(pr)
    quest = qr.quest_record({'edid': QUEST, 'script': qsk, 'name': '', 'flags': {'start_enabled': True}, 'priority': 40,
                             'delay': 0.5, 'stages': [], 'objectives': []})
    sc = api_scripts.scripts()
    c = sc.compile(quest_source(), qsk, 'quest', dict(extra, **{qk: quest}))
    if not hasattr(c, 'subrecords'):
        raise ValueError('the money quest\'s script: %s' % (c,))
    srec = sc._record_of(c, SCRIPT)
    record(SCRIPT, srec, qsk)
    record(QUEST, quest, qk)
    index, last = {}, None
    for sub in srec['subs']:
        if sub['tag'] == 'SLSD':
            last = next(f['value'] for f in sub['fields'] if f.get('name') == 'Index')
        elif sub['tag'] == 'SCVR' and last is not None:
            index[sub['value'].lower()] = last
    topics = {}
    for k, words in (('tongbao', WORDS['trade_tongbao']), ('cells', WORDS['trade_cells']), ('sell10', WORDS['sell10']),
                     ('sellall', WORDS['sellall']), ('buy10', WORDS['buy10']), ('haggle', WORDS['haggle']), ('what', WORDS['what'])):
        topics[k] = record('FOLabMoney%s' % k.capitalize(), qr.topic_record({
            'edid': 'FOLabMoney%s' % k.capitalize(), 'name': words, 'priority': 50.0, 'kind': 0, 'flags': {'top_level': True},
            'quests': [{'quest': qk, 'links': []}]}))
    # the money changer, by the gate market's stall
    ch = next((r for r in rows if r['what'] == 'changer'), None)
    changer = None
    if ch:
        pool, used = huangland.face_pool(gd, pr)
        face, sex = None, 'M'
        for want in (('AsianOld', 'M'), ('AsianOld', 'F'), ('Asian', 'M'), ('Asian', 'F')):
            face = next((f for f in pool.get(want, []) if gd.key(f) not in used), None)
            if face is not None:
                sex = want[1]
                break
        if face is None:
            face, sex = huangradio._spare_face(gd, used)
        if face is None:
            rep['missing'].append('no Asian face left for the money changer')
        else:
            g = ff.GROUPS['huang_folk']
            items = [(ff._item(gd, pr, e), 1) for e in g['wear'][sex]] + [(tong, 40)]
            fac = ff._mod_key(pr, ff.FACTIONS['huang'][0], 'FACT')
            npc = ff.person(gd, pr, face, CHANGER[0], CHANGER[1], dict(g, package=WL.STAY), items, [], fac)
            changer = record(CHANGER[0], npc)
            x, y, z, rz = ch['p']
            out.append({'op': 'place', 'cell': ch['cell'], 'key': _new_key(pr), 'ref': {'base': changer, 'p': [x, y, z + 4, 0.0, 0.0, rz], 's': 1.0,
                                                                                        'persistent': True}})
            rep['placed']['changer'] = {'p': [round(v) for v in ch['p'][:3]], 'stall': ch['stall'], 'from_gate': ch['from_gate'],
                                        'from_guard': ch['from_guard'], 'face': gd.key(face), 'sex': sex}
    # the Vault's cell exchange
    mx = next((r for r in rows if r['what'] == 'exchange'), None)
    if mx:
        msgs = {k: _new_key(pr) for k in ('menu', 'short', 'sold')}
        import generators
        record('FOLabCellExchangeMsg', generators._message('FOLabCellExchangeMsg', WORDS['exchange'], [
            '%d Energy Cells (%d %s)' % (EXCHANGE['energy'][1], EXCHANGE['energy'][2], KALA),
            '%d Microfusion Cells (%d %s)' % (EXCHANGE['microfusion'][1], EXCHANGE['microfusion'][2], KALA), 'Leave']), msgs['menu'])
        record('FOLabCellExchangeShortMsg', generators._message('FOLabCellExchangeShortMsg', WORDS['exchange_short']), msgs['short'])
        record('FOLabCellExchangeSoldMsg', generators._message('FOLabCellExchangeSoldMsg', WORDS['exchange_sold']), msgs['sold'])
        skey, akey = _new_key(pr), _new_key(pr)
        L = ['scn FOLabCellExchangeScript', 'short menu', 'short button', '', 'Begin OnActivate', '\tif IsActionRef player == 0', '\t\treturn',
             '\tendif', '\tShowMessage FOLabCellExchangeMsg', '\tset menu to 1', 'End', '', 'Begin GameMode', '\tif menu == 0', '\t\treturn', '\tendif',
             '\tset button to GetButtonPressed', '\tif button == -1', '\t\treturn', '\tendif', '\tset menu to 0']
        for i, k in enumerate(('energy', 'microfusion')):
            item, n, price = EXCHANGE[k]
            L += ['\tif button == %d' % i, '\t\tif player.GetItemCount Caps001 >= %d' % price, '\t\t\tplayer.RemoveItem Caps001 %d' % price,
                  '\t\t\tplayer.AddItem %s %d' % (item, n), '\t\t\tShowMessage FOLabCellExchangeSoldMsg', '\t\telse',
                  '\t\t\tShowMessage FOLabCellExchangeShortMsg', '\t\tendif', '\tendif']
        L += ['End', '']
        cc = sc.compile('\n'.join(L), skey, 'object', extra)
        if not hasattr(cc, 'subrecords'):
            raise ValueError('the cell exchange\'s script: %s' % (cc,))
        record('FOLabCellExchangeScript', sc._record_of(cc, 'FOLabCellExchangeScript'), skey)
        mrec = recordio.load(gd, _game(gd, MACHINE[0], ('ACTI',)))
        model = recordio.field(mrec, 'MODL')
        acti = {'type': 'ACTI', 'flags': 0, 'src': '', 'subs': [
            {'tag': 'EDID', 'label': 'Editor ID', 'kind': 'z', 'value': MACHINE[1]},
            {'tag': 'OBND', 'label': 'Bounds', 'kind': 'struct', 'fields': [{'name': n, 'code': 'h', 'value': int(v)} for n, v in
                                                                             zip(('X1', 'Y1', 'Z1', 'X2', 'Y2', 'Z2'), P['box'])]},
            {'tag': 'FULL', 'label': 'Name', 'kind': 'z', 'value': MACHINE[2]},
            {'tag': 'MODL', 'label': 'Model', 'kind': 'z', 'value': model},
            {'tag': 'SCRI', 'label': 'Script', 'kind': 'F', 'value': skey}]}
        record(MACHINE[1], acti, akey)
        x, y, z, rz = mx['p']
        out.append({'op': 'place', 'cell': mx['cell'], 'key': _new_key(pr), 'ref': {'base': akey, 'p': [x, y, z, 0.0, 0.0, rz], 's': 1.0}})
        rep['placed']['exchange'] = {'p': [round(v) for v in mx['p'][:3]], 'from_cells': mx['from_cells'], 'from_door': mx['from_door']}
    # topics reworded
    for k, old, new in [(r['topic'], r['from'], r['to']) for r in rows if r['what'] == 'topic']:
        rec = json.loads(json.dumps(pr.records[k]))
        recordio.set_field(rec, 'FULL', new)
        out.append({'op': 'record', 'key': k, 'record': rec})
        rep['reworded'].append((old, new))
    rep['keys'] = {'quest': qk, 'script': qsk, 'tongbao': tong, 'changer': changer, 'topics': topics}
    # the lines (compiled once the records above are in the mod)
    lines = []

    def line(topic, who, words, conds=(), end='', skill=None):
        l = aq.new_line_plain(gd, pr, topic, qk, who, words, conditions=list(conds))
        if end:
            l['end'] = {'source': end, 'parts': None}
        lines.append(l)
    has = lambda item, n: _cond(47, '>=', n, item, 0, 1)
    caps = gd.key(CAPS)
    cell = gd.key(_game(gd, CELL, ('AMMO',)))
    for e in HUANG_TRADERS:
        nk = _mod_key(pr, e, 'NPC_')
        if nk:
            line(topics['tongbao'], nk, WORDS['huang_yes'], [has(tong, 1)], trade_in('tongbao'))
        else:
            rep['skipped'].append((e, 'not in the mod'))
    dq, dvars = _var_index(pr, 'FOLabPirateDeals')
    for e, v in PIRATE_TRADERS:
        nk = _mod_key(pr, e, 'NPC_')
        if nk and dq and v in dvars:
            line(topics['cells'], nk, WORDS['pirate_yes'], [_cond(79, '=', 1, dq, dvars[v]), has(cell, 1)], trade_in('cells'))
        else:
            rep['skipped'].append((e, 'not in the mod'))
    if changer:
        import skillcheck
        greeting = gd.key(_game(gd, 'GREETING', ('DIAL',)))
        better = lambda op: _cond(79, op, 1, qk, index['better']) if op == '=' else _cond(79, '=', 0, qk, index['better'])
        line(greeting, changer, WORDS['hello'])
        line(topics['sell10'], changer, WORDS['sell10_yes'], [has(tong, 10), better('0')],
             'player.RemoveItem %s 10\nplayer.AddItem Caps001 %d' % (TONGBAO[0], 10 * CHANGER_BUYS))
        line(topics['sell10'], changer, WORDS['sell10_better'], [has(tong, 10), better('=')],
             'player.RemoveItem %s 10\nplayer.AddItem Caps001 %d' % (TONGBAO[0], 10 * CHANGER_BETTER))
        for rate, words, cond in ((CHANGER_BUYS, WORDS['sellall_yes'], better('0')), (CHANGER_BETTER, WORDS['sellall_better'], better('='))):
            line(topics['sellall'], changer, words, [has(tong, 1), cond],
                 '\n'.join(['set %s.n to player.GetItemCount %s' % (QUEST, TONGBAO[0]), 'player.RemoveItem %s %s.n' % (TONGBAO[0], QUEST),
                            'set %s.k to %s.n * %d' % (QUEST, QUEST, rate), 'player.AddItem Caps001 %s.k' % QUEST]))
        line(topics['buy10'], changer, WORDS['buy10_yes'], [has(caps, 10 * CHANGER_SELLS)],
             'player.RemoveItem Caps001 %d\nplayer.AddItem %s 10' % (10 * CHANGER_SELLS, TONGBAO[0]))
        for l in skillcheck.check_lines(gd, pr, topics['haggle'], qk, changer, 'Barter', CHANGER_BARTER, WORDS['haggle_yes'], WORDS['haggle_no'],
                                        on_pass='set %s.better to 1' % QUEST, conditions=[better('0')]):
            lines.append(l)
        line(topics['what'], changer, WORDS['what_yes'])
    # goods into money, in the lines that had them
    reprice, _t = _repriced(gd, pr)
    rep['repriced'] = [(k, what) for k, _l, what in reprice]
    quests = set()
    for k, l, _what in reprice:
        quests.add(recordio.field(pr.records.get(l['quest']) or {'subs': []}, 'EDID'))
    rep['voice_quests'] = sorted(q for q in quests if q)
    rep['lines'] = len(lines)
    return out, rep, lines, reprice


def apply(pr, gd, P=None):
    """The records and places, then the new lines and the repriced ones compiled against them: one Undo."""
    import api_quests as aq
    o, rep, lines, reprice = ops(gd, pr, P)
    pr.apply(LABEL, o)
    later = [{'op': 'record_new', 'record': aq._compiled_line(gd, pr, l)} for l in lines]
    later += [{'op': 'record', 'key': k, 'record': aq._compiled_line(gd, pr, l)} for k, l, _w in reprice]
    pr.apply(LABEL, later, merge=True)
    del VOICE[1:]
    VOICE.extend(q for q in rep['voice_quests'] if q not in VOICE)
    qk = rep['keys']['quest']
    VOICE_ONLY.clear()
    VOICE_ONLY.update(k for k, r in pr.records.items() if r.get('type') == 'INFO' and qr_quest(r) == qk)
    VOICE_ONLY.update(k for k, _l, what in reprice if any(w.startswith('words:') for w in what))
    rep['voice_lines'] = len(VOICE_ONLY)
    return rep


def qr_quest(rec):
    import questrec as qr
    return qr.info_plain(rec)['quest']
