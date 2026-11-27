"""Play reports (playreports.py): nv-rs's F12 report folders read (place.txt as nv-rs writes it, the log's one line, a
missing place, the note under nv-rs's prompt), matched against a small plugin made here (a world with a persistent and a
grid cell, an interior), the mod's things near the spot with their kind and step, the live mod's changes read without
touching its files, pages written only where allowed. Everything in the scratch home; no game, no nv-rs."""
import json
import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import playreports as P  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


HOME = os.environ.get('FOLAB_HOME') or os.path.join(os.environ.get('TEMP', '.'), 'folab-playreports')
os.makedirs(HOME, exist_ok=True)

# --- a plugin made by hand: FalloutNV.esm as its one master, so its own forms are 0x01xxxxxx --------------------------


def sub(tag, data):
    return tag.encode() + struct.pack('<H', len(data)) + data


def z(s):
    return s.encode('cp1252') + b'\0'


def rec(tag, fid, subs, flags=0):
    data = b''.join(subs)
    return tag.encode() + struct.pack('<IIIII', len(data), flags, fid, 0, 0) + data


def grup(label, gtype, body):
    lab = label.encode() if isinstance(label, str) else struct.pack('<I', label)
    return b'GRUP' + struct.pack('<I', 24 + len(body)) + lab + struct.pack('<iII', gtype, 0, 0) + body


def ref(fid, base, pos, edid=None, extra=(), flags=0):
    subs = ([sub('EDID', z(edid))] if edid else []) + [sub('NAME', struct.pack('<I', base))] + list(extra)
    subs.append(sub('DATA', struct.pack('<6f', *pos, 0, 0, 0)))
    return rec('REFR', fid, subs, flags)


W, PC, GC, HOUSE = 0x01000800, 0x01000801, 0x01000802, 0x01000803
ROCK, CRATE = 0x01000810, 0x01000811
GAME_BARREL = 0x0002F546               # a game base (FalloutNV.esm's numbering)
NEAR, FAR, GONE, SHELF, MARKER = 0x01000900, 0x01000901, 0x0010AAAA, 0x01000902, 0x01000903

stats = grup('STAT', 0, rec('STAT', ROCK, [sub('EDID', z('FOLabPlayTestRock')),
                                           sub('MODL', z('folab\\rubble\\heap_a.nif'))]) +
             rec('STAT', CRATE, [sub('EDID', z('FOLabPlayTestCrate')), sub('MODL', z('folab\\island\\crate.nif'))]))
persistent = grup(PC, 6, grup(PC, 8, ref(MARKER, 0x10, (-81000, -11000, 100), extra=[
    sub('XMRK', b''), sub('FULL', z('Test Beach'))])))
grid_children = grup(GC, 6, grup(GC, 9,
                                 ref(NEAR, ROCK, (-80100, -10050, 160)) +
                                 ref(FAR, CRATE, (-77000, -9000, 150)) +
                                 ref(GONE, GAME_BARREL, (-79950, -9990, -30000), flags=0x800)))
world_children = grup(W, 1,
                      rec('CELL', PC, [sub('DATA', b'\x02')]) + persistent +
                      grup(struct.unpack('<I', struct.pack('<hh', -1, -1))[0], 4,
                           grup(struct.unpack('<I', struct.pack('<hh', -1, -3))[0], 5,
                                rec('CELL', GC, [sub('DATA', b'\x02'), sub('XCLC', struct.pack('<iiI', -20, -3, 0))]) +
                                grid_children)))
worlds = grup('WRLD', 0, rec('WRLD', W, [sub('EDID', z('FOLabPlayTestWorld'))]) + world_children)
cells = grup('CELL', 0, grup(3, 2, grup(3, 3, rec('CELL', HOUSE, [sub('EDID', z('FOLabPlayTestHouse')),
                                                                  sub('DATA', b'\x01')]) +
                                   grup(HOUSE, 6, grup(HOUSE, 9, ref(SHELF, CRATE, (30, 0, 20), edid='FOLabLootShelf'))))))
header = rec('TES4', 0, [sub('HEDR', struct.pack('<fiI', 1.34, 9, 0x904)), sub('MAST', z('FalloutNV.esm')),
                         sub('DATA', b'\0' * 8)])
esp = os.path.join(HOME, 'PlayTest.esp')
with open(esp, 'wb') as f:
    f.write(header + stats + cells + worlds)

# --- place.txt as nv-rs writes it (its own tests' lines, crates/host/src/report_place.rs) ------------------------------

OUT = ('worldspace: WastelandNV (0x000da726)\ncell: 0x000de4c2 at grid (-10, 4)\nposition: -39000 18200 5800\n'
       'view: pitch 3.0 heading 270.0 (degrees)\ngame hour: 17.50\nweather: 0x0000abcd\nlighting: a=1 b=0\n'
       'console: cow WastelandNV -10 4; player.setpos x -39000; player.setpos y 18200; player.setpos z 5800; '
       'player.setangle x 3.0; player.setangle z 270.0; set gamehour to 17.50\n')
p = P.parse_place(OUT.replace('\n', '\r\n'))
check('outside place: world', p['world'] == {'edid': 'WastelandNV', 'formid': 0xDA726}, p['world'])
check('outside place: cell, grid, position', p['cell'] == {'edid': None, 'formid': 0xDE4C2} and p['grid'] == [-10, 4]
      and p['position'] == [-39000, 18200, 5800], p)
check('outside place: view and hour', p['view'] == {'pitch': 3.0, 'heading': 270.0} and p['hour'] == 17.5)
one = P.parse_place(OUT.strip().replace('\n', '; '))
check("the log's one line reads the same", one == p, one)
p = P.parse_place('interior cell: GSDocMitchellHouse (0x00104c1c)\nposition: -39000 18200 5800\n'
                  'console: coc GSDocMitchellHouse; player.setpos x -39000; player.setpos y 1; player.setpos z 2\n')
check('inside place', p['interior'] and p['cell']['edid'] == 'GSDocMitchellHouse' and p['position'][2] == 5800, p)
p = P.parse_place('worldspace: 0x01000d7e\ncell: 0x01000d80 at grid (2, 3)\nconsole: player.setpos x 1\n')
check('no editor id, no position: the cell\'s middle', p['world'] == {'edid': None, 'formid': 0x01000D7E} and
      P.spot_of(p) == (2.5 * 4096, 3.5 * 4096, 0.0, True), P.spot_of(p))
check('no place', P.parse_place('no place: nothing in this program writes it\n') ==
      {'missing': 'no place: nothing in this program writes it'})
check("the note under nv-rs's prompt", P.note_of(P.PROMPT + '\r\n\r\nrock floats\r\nby the road\r\n') ==
      'rock floats\nby the road' and P.note_of(P.PROMPT + '\r\n\r\n') == '')

# --- a session of reports ---------------------------------------------------------------------------------------------

root = os.path.join(HOME, 'nv-rs')
reports = os.path.join(root, 'userdata', 'reports')
mods = os.path.join(root, 'mods')
os.makedirs(mods, exist_ok=True)


def report(n, place=None, log='', note='', start='run one\n', picture=True):
    d = os.path.join(reports, '%03d' % n)
    os.makedirs(d, exist_ok=True)
    if place is not None:
        with open(os.path.join(d, 'place.txt'), 'w', newline='\r\n') as f:
            f.write(place)
    with open(os.path.join(d, 'log.txt'), 'w') as f:
        f.write(log)
    with open(os.path.join(d, 'log-start.txt'), 'w') as f:
        f.write(start)
    with open(os.path.join(d, 'note.txt'), 'w', newline='\r\n') as f:
        f.write(P.PROMPT + '\n\n' + note)
    if picture:
        with open(os.path.join(d, 'picture.bmp'), 'wb') as f:
            f.write(b'BM' + b'\0' * 60)


# the running game numbers the mod's forms by load order (0x0b...), so worlds match by editor ID
report(1, 'worldspace: FOLabPlayTestWorld (0x0b000800)\ncell: 0x0b000802 at grid (-20, -3)\nposition: -80000 -10000 150\n'
          'console: cow FOLabPlayTestWorld -20 -3; player.setpos x -80000; player.setpos y -10000; player.setpos z 150\n',
       log='start\nsomething failed to load\n', note='rock floats by the road\n')
report(2, None, log='F12: place: interior cell: FOLabPlayTestHouse (0x0b000803); position: 0 0 0; '
                    'console: coc FOLabPlayTestHouse; player.setpos x 0\nF12: report in x\n', picture=False)
report(3, 'no place: nothing in this program writes it\n', note='crashed after this', start='run two\n')
report(4, 'interior cell: GSDocMitchellHouse (0x00104c1c)\nposition: 1 2 3\n')

# the live mod: the rock moved, a new thing added, the shelf taken out; its .changes must stay as it is
live = os.path.join(HOME, 'PlayTest.json')
with open(live, 'w') as f:
    json.dump({'name': 'PlayTest', 'cells': {
        '+000802': {'refs': {'+000900': {'base': '+000810', 'p': [-80100, -10050, 200, 0, 0, 0], 's': 1.0}}},
        '+000803': {'refs': {'+000902': {'removed': True}}}}}, f)
changes = os.path.join(HOME, 'PlayTest.changes')
lines = (json.dumps({'base': 'whatever'}) + '\n' +
         json.dumps({'set': {'cells': {'+000802': {'refs': {
             '+000900': {'base': '+000810', 'p': [-80100, -10050, 200, 0, 0, 0], 's': 1.0},
             '+000950': {'base': '+000811', 'p': [-80010, -10010, 150, 0, 0, 0], 's': 1.0}}}}}}) + '\n')
with open(changes, 'w') as f:
    f.write(lines)
before = (os.path.getmtime(changes), os.path.getsize(changes))

out = os.path.join(HOME, 'pages')
steps = P.Steps({'FOLabPlayTest': ['testmodule'], 'FOLabLoot': ['lootplace']}, {'rubble': ['rubbleset']})
pages, jpath, done = P.run(reports, out, esp=esp, live=live, data_dir=None, steps=steps)
by = {r['name']: r for r in done}
check('four reports, oldest first', [r['name'] for r in done] == ['001', '002', '003', '004'])
check('a page per run of the game', len(pages) == 2 and all(os.path.isfile(x) for x in pages), pages)
r1 = by['001']
check('report 1: world and cell found in the plugin', r1['at']['world'] == 'FOLabPlayTestWorld' and
      r1['at']['found'] and r1['at']['spot'] == [-80000, -10000, 150], r1['at'])
near = {n['ref']: n for n in r1['near']}
check('report 1: the rock is near, the crate far off', '+000900' in near and '+000901' not in near, sorted(near))
n = near.get('+000900', {})
check("report 1: the rock's base, step and kind", n.get('base') == 'FOLabPlayTestRock' and n.get('step') ==
      ['testmodule'] and n.get('kind') == 'added by the mod' and n.get('distance') == 112, n)
g = near.get('FalloutNV.esm:10AAAA', {})
check('report 1: a game thing taken out shows as such', g.get('kind') == 'a game thing the mod took out' and
      g.get('starts_off'), g)
check('report 1: the nearest map marker', r1['landmark'] == {'name': 'Test Beach', 'distance': 1414}, r1['landmark'])
check('report 1: the note and the log line', r1['note'] == 'rock floats by the road' and
      r1['log_hints'] == ['something failed to load'], (r1['note'], r1['log_hints']))
lc = {c['ref']: c['what'] for c in r1['live_changes']}
check('report 1: the live mod moved the rock and added a crate since', lc == {
    '+000900': 'moved since the build', '+000950': 'added since the build'}, lc)
r2 = by['002']
check("report 2: place from the log's line, inside the house", r2['at']['interior'] and
      r2['at']['cells'] == ['FOLabPlayTestHouse'] and r2['picture'] is None, r2['at'])
sh = r2['near'][0] if r2['near'] else {}
check('report 2: the shelf by its own editor ID', sh.get('edid') == 'FOLabLootShelf' and sh.get('step') ==
      ['lootplace'], sh)
check('report 2: the shelf taken out in the live mod', [c['what'] for c in r2['live_changes']] ==
      ['taken out since the build'], r2['live_changes'])
check('report 3: no place, still listed with its note', by['003']['at'] is None and by['003']['note'] ==
      'crashed after this')
check("report 4: the game's own place: nothing of the mod's", by['004']['at'] == {
    'world': None, 'world_found': True, 'cells': [], 'interior': True, 'found': False, 'spot': [1, 2, 3],
    'spot_guessed': False} and by['004']['near'] == [], by['004']['at'])
check("the live mod's files untouched", (os.path.getmtime(changes), os.path.getsize(changes)) == before and
      open(changes).read() == lines)
text = open(pages[0], encoding='utf-8').read()
check('page: the picture linked from the page', '](../nv-rs/userdata/reports/001/picture.bmp)' in text, text[:400])
check('page: the go-there line and the table', 'cow FOLabPlayTestWorld -20 -3' in text and
      '| 112 | `+000900` | FOLabPlayTestRock (STAT) | testmodule | added by the mod |' in text)
j = json.load(open(jpath, encoding='utf-8'))
check('json: every report', [r['name'] for r in j['reports']] == ['001', '002', '003', '004'])
check('--from: only later reports', [r['name'] for r in P.read_reports(reports, 3)] == ['003', '004'])

# --- never into the game or nv-rs's own folders -------------------------------------------------------------------------
for bad in (mods, os.path.join(root, 'app'), os.path.join(root, 'userdata', 'modgame', 'Data')):
    try:
        P.run(reports, bad, esp=esp, steps=steps)
        check('refused ' + bad, False)
    except ValueError:
        check('refused ' + os.path.relpath(bad, root), True)
pages2, _, _ = P.run(reports, None, esp=esp, steps=steps)
check("by default beside the reports (nv-rs's userdata)", all(os.path.dirname(x) == os.path.join(root, 'userdata')
                                                              for x in pages2), pages2)

# --- the step tables from FOLab's own modules -----------------------------------------------------------------------
sets = P.steps_by_set()
check("model folders name their set's module", sets.get('rubble', [None])[0] == 'rubbleset' and
      sets.get('bamboo', [None])[0] == 'bambooset', (sets.get('rubble'), sets.get('bamboo')))
check('a model folder', P.set_of('meshes\\folab\\rubble\\heap_a.nif') == 'rubble' and
      P.set_of('clutter\\barrel01.nif') is None)
