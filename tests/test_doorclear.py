"""No boards in front of a door that leads somewhere (doorclear.py): a DoorBarricade stood a step out from a mod's door
with a link, next to where you come out, is taken out; one beside a door with no link, one far from where you come out,
and one inside a place are left; the game's own barricade stands about 100 out from its door, past townbuild's SHUT_SAME."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import doorclear  # noqa: E402
import gamedata  # noqa: E402
import project  # noqa: E402
import townbuild  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


gd = gamedata.GameData()


def key_of(edid, tag):
    return gd.key(next(f for f, (_i, r) in gd.forms.items() if r.tag == tag and gd.edid(f) == edid))


bar = key_of('DoorBarricade', 'STAT')
door = key_of('NVCraftsmanHomeDoor', 'DOOR')
crate = key_of('CrateLarge01', 'STAT')
world = next(w for w in gd.worlds() if gd.edid(w) == 'WastelandNV')
cells = list(gd.grid(world).values())
out, out2 = gd.key(cells[0]), gd.key(cells[1])
inside = gd.key(next(iter(gd.interiors)))
pr = project.Project.create('doorclear test')
pr.cells[out] = {'refs': {
    '+000100': {'base': door, 'p': [0, 0, 0, 0, 0, 0], 'tel': {'door': '+000200', 'p': [5, 5, 0, 0, 0, 0]}},
    '+000101': {'base': bar, 'p': [0, -95, 10, 0, 0, 0]},           # (in front, beside where you come out)
    '+000102': {'base': crate, 'p': [0, -60, 0, 0, 0, 0]},          # (not a bar)
    '+000103': {'base': door, 'p': [2000, 0, 0, 0, 0, 0]},          # (a door with no link)
    '+000104': {'base': bar, 'p': [2000, -95, 10, 0, 0, 0]},
}}
pr.cells[out2] = {'refs': {
    '+000110': {'base': door, 'p': [10000, 0, 0, 0, 0, 0], 'tel': {'door': '+000210', 'p': [0, 0, 0, 0, 0, 0]}},
    '+000111': {'base': bar, 'p': [10150, 0, 0, 0, 0, 0]},          # (a barred doorway beside it: far from where you stand out)
    '+000112': {'base': bar, 'p': [5, -90, 0, 0, 0, 0]},           # (filed in the next cell, in front of the first door)
}}
pr.cells[inside] = {'refs': {
    '+000200': {'base': door, 'p': [0, 0, 0, 0, 0, 0], 'tel': {'door': '+000100', 'p': [0, -40, 0, 0, 0, 0]}},
    '+000210': {'base': door, 'p': [500, 0, 0, 0, 0, 0], 'tel': {'door': '+000110', 'p': [10000, -260, 0, 0, 0, 0]}},
    '+000201': {'base': bar, 'p': [0, 95, 10, 0, 0, 0]},
}}
o, rep = doorclear.ops(gd, pr)
gone = {x['ref'] for x in o}
check('the bar in front of a door that leads somewhere goes', '+000101' in gone, sorted(gone))
check('one filed in another cell goes too', '+000112' in gone, sorted(gone))
check('nothing else goes', gone == {'+000101', '+000112'}, sorted(gone))
check('the report counts it', rep['removed'] == 2 and rep['kinds'] == {'DoorBarricade': 2}, rep)
check('the game\'s barricade stands past SHUT_SAME, within CLEAR', townbuild.SHUT_SAME < 95 < doorclear.CLEAR)
check('in_the_way', doorclear.in_the_way((0, 0), 0, 0, -95, 10) and not doorclear.in_the_way((0, 0), 0, 0, -400, 0))
check('bars are told by name', doorclear.is_bar('DoorBarricade') and doorclear.is_bar('WoodPlanksGroup05') and not doorclear.is_bar('NVCraftsmanHomeDoor'))
