import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
"""Walking a set from its real collision before it's navmeshed (walkcheck.py): the game's guard tower walks with its
parts and shows its stairs as nothing drawn without them; a made-up platform reached up a ramp is walked to, one only
through a gap narrower than an actor is too narrow to get to, a ramp that stops short of its deck leaves the deck out
of reach; FOLab's own walkable pieces walk with no faults. Never starts the game."""
import gamedata, landmarks, modelmake, modelsets, walkcheck as W
import battleship


def check(what, ok):
    print(('PASS ' if ok else 'FAIL ') + what)


gd = gamedata.GameData()

# ---------- the game's guard tower ----------
L = landmarks.lift(gd, 'lookout')
check('the lookout set is in the game files', L is not None)
tower = [it for it in W.of_set(L) if gd.edid(gd.from_key(it['base'])).startswith('NVGuardTower01')]
check('the guard tower and its four parts', len(tower) == 5)
whole = W.walk(gd, tower)
check('with its parts: nothing drawn-less walked on, nothing too narrow', whole['ok'] and not whole['invisible'])
check("its top deck is out of reach, as the game's own navmeshes have it", any(a['at'][2] > 900 for a in whole['unreached']))
bare = W.walk(gd, [it for it in tower if gd.edid(gd.from_key(it['base'])) == 'NVGuardTower01'])
heights = sorted(a['at'][2] for a in bare['invisible'])
check('without them: its stairs walked on with nothing drawn, flight by flight (%s)' % heights,
      not bare['ok'] and len(heights) >= 5 and heights[-1] > 700)
check('said in words', 'nothing drawn' in W.say('bare tower', bare))

# ---------- made-up platforms ----------
LOOKS = {'dark': modelsets.look('kiosk'), 'deck': modelsets.look('kiosk')}


def model(parts):
    return {'nif': modelmake.make({'name': 'FOLabWalkTest', 'looks': LOOKS, 'parts': parts, 'shade': False, 'bevel': 0})['nif'],
            'label': 'test'}


def box(parts, size, at, solid=True):
    battleship._box(parts, size, at, 'deck', solid=solid)


TOP = 300.0
parts = []
box(parts, [600, 600, 20], [0, 0, TOP - 10])                       # a platform 300 up, its top at 300
battleship.ladder(parts, 0, -300 - TOP * 1.25, 0.0, -290, TOP)     # a ramp from the ground up onto its south edge
rep = W.walk(gd, [model(parts)], goals=[('the platform', (0, 0, TOP))])
check('a platform up a ramp is walked to', rep['ok'] and rep['goals'][0]['reached'])

narrow = list(parts)
box(narrow, [24, 200, 20], [0, 400, TOP - 10])                     # a strip 24 wide north of it...
box(narrow, [600, 600, 20], [0, 800, TOP - 10])                    # ...to a second platform
rep = W.walk(gd, [model(narrow)], goals=[('the far platform', (0, 800, TOP))])
check('a platform only through a gap narrower than an actor is too narrow to get to',
      not rep['ok'] and rep['short'] and abs(rep['short'][0]['at'][1] - 800) < 120 and not rep['goals'][0]['reached'])

short = []
box(short, [600, 600, 20], [0, 0, TOP - 10])
battleship.ladder(short, 0, -400 - (TOP - 80) * 1.25, 0.0, -400, TOP - 80)   # a ramp that stops 100 short and 80 under
rep = W.walk(gd, [model(short)], goals=[('the platform', (0, 0, TOP))])
check('a ramp that stops short of its deck: the deck not reached, a fault', not rep['ok'] and not rep['goals'][0]['reached'])

# ---------- FOLab's own ----------
for name in ('natatorium', 'battery_randolph'):
    rep = W.check_piece(gd, name)
    check("%s walks with no faults%s" % (name, '' if rep['ok'] else ': ' + W.say(name, rep)), rep['ok'])
