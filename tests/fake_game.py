"""A stand-in for the game, for test_gametest: it does what the checker should make the real game do, and looks at what a
real game would find. Not a test itself. No game goes near this.

    fake_game.py <data dir> <ini dir> <plugins.txt> <saves dir> <mode> [at]

Modes: ok, fall (the first point drops the player), crash, hang (stops partway, stays open), silent (stays open, writes
nothing), saves (changes one of the user's saves), noquit (finishes, doesn't quit), badrays (rays mean something else).
Like WriteStringToFile: the first line makes the file, each later one adds a line break and then itself."""
import json
import os
import sys
import time

data, ini, txt, saves, mode = sys.argv[1:6]
at = int(sys.argv[6]) if len(sys.argv) > 6 else 3
folder = os.path.join(data, 'FOLabGameTest')
out = os.path.join(folder, 'lines.txt')
seen = {}


def write(line):
    new = not os.path.exists(out)
    with open(out, 'a', encoding='cp1252') as f:
        f.write(('' if new else '\n') + line)


def sleep_forever():
    while True:
        time.sleep(1)


# what a game would see as it starts
seen['plugins'] = [l.strip() for l in open(txt, encoding='cp1252') if l.strip() and not l.startswith('#')]
for fn in ('Fallout.ini', 'FalloutPrefs.ini'):
    p = os.path.join(ini, fn)
    if os.path.isfile(p):
        seen[fn] = open(p, encoding='cp1252').read()
scripts = os.path.join(data, 'NVSE', 'plugins', 'scripts')
seen['scripts'] = sorted(os.listdir(scripts))
seen['tick'] = os.path.isfile(os.path.join(data, 'NVSE', 'user_defined_functions', 'folabgt_tick.txt'))
seen['checker'] = os.path.isfile(os.path.join(data, 'FOLab Game Test.esp'))
gr = open(os.path.join(scripts, 'gr_folabgt.txt'), encoding='cp1252').read()
run = gr.split('boot|gr|')[1].split('"')[0]
with open(os.path.join(os.path.dirname(data), 'fake game saw.json'), 'w', encoding='utf-8') as f:
    json.dump(seen, f)

if mode == 'silent':
    sleep_forever()
if mode == 'crash' and at == 0:
    sys.exit(1)
write('boot|gr|%s' % run)
if mode == 'saves':
    with open(os.path.join(saves, os.listdir(saves)[0]), 'ab') as f:
        f.write(b'x')
    sleep_forever()

steps = []
n = 0
while True:
    p = os.path.join(folder, 'plan', '%d.txt' % n)
    if not os.path.isfile(p):
        break
    with open(p, encoding='cp1252') as f:
        text = f.read()
    assert len(text) < 16000, 'a plan file over what ReadStringFromFile reads'
    steps += [l.split('|') for l in text.splitlines()]
    n += 1

number = 0
first_stand = True
for s in steps:
    kind = int(s[0])
    i = s[1]
    if number == at and mode in ('crash', 'hang'):
        if mode == 'crash':
            sys.exit(1)
        sleep_forever()
    number += 1
    if kind == 0:       # go
        write('go|' + i)
        write('at|%s|%s|%s|0|0|0' % (i, os.environ['FAKE_CELL_FORM'], 'The Place'))
    elif kind == 1:     # cal
        x, y, z = map(float, s[2:5])
        if mode == 'badrays':
            write('cal|%s|%.1f|%.1f|%.1f|-99999|-99999|-99999|-99999|-99999|-99999' % (i, x, y, z))
        else:
            write('cal|%s|%.1f|%.1f|%.1f|%.1f|%.1f|%.1f|%.1f|%.1f|%.1f' % (i, x, y, z, x, y, z, z + 300, x, y + 200))
    elif kind == 2:     # stand
        x, y, z = map(float, s[2:5])
        if mode == 'fall' and first_stand:
            write('stand|%s|%.1f|%.1f|%.1f|%.1f|%.1f|%.1f|1|0|-1|-1|-1|-1|-1|-1|-1|-1' % (i, x, y, z - 400, x, y, z - 900))
        else:
            write('stand|%s|%.1f|%.1f|%.1f|%.1f|%.1f|%.1f|0|0|200|200|200|200|200|200|200|200' % (i, x, y, z, x, y, z))
        first_stand = False
    elif kind == 3:     # thing
        x, y, z = map(float, s[4:7])
        write('thing|%s|1|%.1f|%.1f|%.1f|0|%.1f|00000000' % (i, x, y, z, z))
    elif kind == 4:     # actor
        x, y, z = map(float, s[4:7])
        write('actor|%s|1|%.1f|%.1f|%.1f|0|0|0' % (i, x, y, z))
    elif kind == 5:     # door
        write('door|%s|1|1|0|%s|Over There' % (i, os.environ['FAKE_DOOR_FORM']))
        arrive = json.loads(os.environ['FAKE_ARRIVE']).get(i, [0, 0, 0])
        write('land|%s|%s|Over There|%.1f|%.1f|%.1f|%.1f|0' % (i, os.environ['FAKE_DOOR_FORM'], arrive[0], arrive[1], arrive[2], arrive[2]))
    elif kind == 6:     # npc
        write('npc|%s|120.0|140' % i)
    elif kind == 7:     # done
        write('done|%d' % number)
    time.sleep(0.005)
if mode == 'noquit':
    sleep_forever()
# (the game writes its prefs when it quits: restore must put them back)
p = os.path.join(ini, 'FalloutPrefs.ini')
if os.path.isfile(p):
    with open(p, 'a', encoding='cp1252') as f:
        f.write('; the game wrote this on quitting\n')
