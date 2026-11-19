"""Shipping containers, FOLab's own (the game has none, only railway boxcars): a 40-foot box (12.2 m by 2.44 by 2.6:
`LONG`, `WIDE`, `HIGH` in game units) of corrugated steel painted and faded, double doors at one end with their bars,
corner posts; in four colours (`COLOURS`). For the Flotilla's ship (flotilla.py), stacked on her deck.

Front towards -y (the doors), standing on z 0, as every piece of modelsets. Solid all through: walked on when stacked."""
import modelsets
import texpaint as tp
from modelsets import look

LONG, WIDE, HIGH = 854.0, 171.0, 182.0
COLOURS = {'red': (138, 52, 40), 'blue': (52, 76, 104), 'green': (62, 92, 60), 'rust': (122, 82, 52)}
SET = 'cargo'

for _name, _c in COLOURS.items():
    modelsets.TEXTURES['cargo/side_' + _name] = (lambda c=_c, n=_name: tp.corrugated(c, seed=700 + len(n), ridges=24))
    modelsets.TEXTURES['cargo/door_' + _name] = (lambda c=_c, n=_name: tp.painted_metal(c, seed=720 + len(n), rust=0.25))
modelsets.TEXTURES['cargo/frame'] = lambda: tp.painted_metal((60, 58, 54), seed=740, rust=0.35)


def container(colour):
    lk = {'side': look('cargo/side_' + colour, tile=180, turned=True), 'door': look('cargo/door_' + colour, tile=120),
          'frame': look('cargo/frame', tile=64)}
    P = [{'shape': 'box', 'size': [WIDE, LONG, HIGH], 'at': [0, 0, 0], 'look': 'side', 'faces': {'front': 'door', 'back': 'door'},
          'solid': True, 'material': 'metal', 'far': True}]
    for sx in (-1, 1):                          # (corner posts, top and bottom rails)
        for sy in (-1, 1):
            P.append({'shape': 'box', 'size': [14, 14, HIGH + 2], 'at': [sx * (WIDE / 2 - 5), sy * (LONG / 2 - 5), 0], 'look': 'frame', 'solid': False})
        for z in (0, HIGH - 10):
            P.append({'shape': 'box', 'size': [10, LONG, 12], 'at': [sx * (WIDE / 2 - 3), 0, z], 'look': 'frame', 'solid': False})
    for x in (-WIDE / 4, -WIDE / 10, WIDE / 10, WIDE / 4):   # (the door bars)
        P.append({'shape': 'box', 'size': [4, 4, HIGH - 20], 'at': [x, -LONG / 2 - 3, 10], 'look': 'frame', 'solid': False})
    return {'name': 'FOLabCargoContainer' + colour.title(), 'looks': lk, 'parts': P}


PIECES = {'cargo_' + c: ('Shipping container, ' + c, (lambda c=c: container(c))) for c in COLOURS}
for _k, (_label, _fn) in PIECES.items():
    modelsets.PIECES.setdefault(_k, {'label': _label, 'set': SET, 'file': _k[6:], 'describe': _fn, 'edid': _fn()['name']})
