"""The mod conflict check, over small plugins in a fake Data folder (never the real game's list). Each kind of clash, the
harmless ones, form IDs told through each file's own masters, the cache, a move with its backup."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import json, struct, threading, time

HOME = os.environ['FOLAB_HOME']
FAKE = os.path.join(HOME, 'fake game', 'Data')
LOCAL = os.path.join(HOME, 'fake local')
os.makedirs(FAKE)
os.makedirs(LOCAL)
REAL_LOCAL = os.environ.get('LOCALAPPDATA', '')
os.environ['LOCALAPPDATA'] = LOCAL              # (never the real plugins.txt)
import conflicts, install, loadorder, plugintree, tes4


def check(what, ok, extra=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' ' + str(extra) if extra != '' and not ok else ''))


def sub(tag, data):
    return struct.pack('<4sH', tag.encode(), len(data)) + data


edid = lambda s: sub('EDID', s.encode() + b'\0')
T0 = 1200000000
clock = [T0]


def tree_for(masters, esm=False):
    head = sub('HEDR', struct.pack('<fiI', 1.34, 0, 0x900)) + sub('CNAM', b'test\0')
    for m in masters:
        head += sub('MAST', m.encode() + b'\0') + sub('DATA', b'\0' * 8)
    return plugintree.Plugin.empty(head, 1 if esm else 0)


def write(tree, name, folder=FAKE):
    clock[0] += 100
    path = os.path.join(folder, name)
    with open(path, 'wb') as f:
        f.write(tree.bytes())
    os.utime(path, (clock[0], clock[0]))
    return path


def plain(name, masters, records, esm=False, flags=None):
    """Records in their type's top group: (type, form ID, bytes[, flags])."""
    t = tree_for(masters, esm)
    for r in records:
        tag, fid, data = r[:3]
        t.top(tag).kids.append(plugintree.Rec.new(tag, r[3] if len(r) > 3 else 0, fid, data))
    return write(t, name)


G = plugintree.Group
R = plugintree.Rec.new


def inside(tree, cell, cell_data, kids, cell_flags=0):
    """An interior place with things in it."""
    top = tree.top('CELL')
    top.kids.append(G(0, tes4.G_INT_BLOCK, kids=[G(0, tes4.G_INT_SUBBLOCK, kids=[R('CELL', cell_flags, cell, cell_data),
                    G(cell, tes4.G_CELL_CHILDREN, kids=[G(cell, tes4.G_CELL_TEMPORARY, kids=kids)])])]))


def outside(tree, world, world_data, squares):
    """A world with squares: {(x, y): (cell form, [kids])}."""
    top = tree.top('WRLD')
    top.kids.append(R('WRLD', 0, world, world_data))
    cells = []
    for (x, y), (cell, kids) in squares.items():
        cells += [R('CELL', 0, cell, edid('Cell%d_%d' % (x & 255, y & 255)) + sub('XCLC', struct.pack('<2i', x, y))),
                  G(cell, tes4.G_CELL_CHILDREN, kids=[G(cell, tes4.G_CELL_TEMPORARY, kids=kids)])]
    top.kids.append(G(world, tes4.G_WORLD_CHILDREN, kids=[G(0, tes4.G_EXT_BLOCK, kids=[G(0, tes4.G_EXT_SUBBLOCK, kids=cells)])]))


def misc(name, value=5, weight=1.0, extra=b''):
    return edid(name) + sub('DATA', struct.pack('<if', value, weight)) + extra


def ref(base, x=0.0, door=None, extra=b''):
    out = sub('NAME', struct.pack('<I', base)) + extra
    if door is not None:
        out += sub('XTEL', struct.pack('<I6fI', door, 0, 0, 0, 0, 0, 0, 0))
    return out + sub('DATA', struct.pack('<6f', x, 0, 0, 0, 0, 0))


def vhgt(start=0.0, ramp=0):
    """Ground: flat at a start, or rising eastward by ramp steps a point."""
    steps = bytearray()
    for r in range(33):
        for c in range(33):
            steps.append(ramp & 255 if c else 0)
    return sub('VHGT', struct.pack('<f', start) + bytes(steps) + b'\0\0\0')


def order_list(*names, dates=True):
    os.makedirs(os.path.join(LOCAL, 'FalloutNV'), exist_ok=True)
    with open(install.plugins_txt(), 'w', encoding='cp1252', newline='\r\n') as f:
        f.write('\n'.join(names) + '\n')
    for n in names if dates else ():             # (the game goes by the files' dates: the list only says which are on)
        clock[0] += 100
        if os.path.isfile(os.path.join(FAKE, n)):
            os.utime(os.path.join(FAKE, n), (clock[0], clock[0]))


def find(rep, issue):
    return [r for g in rep['groups'] for r in g['rows'] if r['issue'] == issue]


def only(rep, issue, word):
    return [r for r in find(rep, issue) if word in r['text']]


# ---------- the game, a small one ----------
NV = 'FalloutNV.esm'
GUN, GUN2, GUN3, LOCK, GONE, SAME_IT, OTHER_IT, ORDER_IT, STAT = 0x900, 0x901, 0x902, 0x903, 0x904, 0x905, 0x906, 0x907, 0x908
NPC, SCPT, QUEST = 0x910, 0x911, 0x912
HALL, HOUSE, DOOR_A, DOOR_B = 0x920, 0x921, 0x922, 0x923
WORLD, C00, C10, NAV0, LAND0, LAND1 = 0x930, 0x931, 0x932, 0x933, 0x934, 0x935

game = tree_for([], True)
for tag, fid, data in (('MISC', GUN, misc('Gun')), ('MISC', GUN2, misc('GunTwo')), ('MISC', GUN3, misc('GunThree')), ('MISC', LOCK, misc('Lock')),
                       ('MISC', GONE, misc('Gone')), ('MISC', SAME_IT, misc('SameThing')), ('MISC', OTHER_IT, misc('OtherThing')), ('MISC', ORDER_IT, misc('OrderThing')),
                       ('STAT', STAT, edid('Crate')),
                       ('CONT', 0x90A, edid('Chest') + sub('CNTO', struct.pack('<Ii', GUN, 1))),
                       ('NPC_', NPC, edid('Trudy') + sub('FULL', b'Trudy\0')),
                       ('SCPT', SCPT, edid('GunScript') + sub('SCTX', b'; game\0')),
                       ('QUST', QUEST, edid('GunQuest') + sub('FULL', b'Quest\0'))):
    game.top(tag).kids.append(R(tag, 0, fid, data))
inside(game, HALL, edid('Hall') + sub('XCLL', b'\x10' * 40), [R('REFR', 0, DOOR_A, ref(STAT, door=DOOR_B))])
inside(game, HOUSE, edid('House'), [R('REFR', 0, DOOR_B, ref(STAT, door=DOOR_A)),
                                    R('REFR', 0, 0x924, ref(STAT, x=1.0))])
outside(game, WORLD, edid('World'), {(0, 0): (C00, [R('LAND', 0, LAND0, vhgt()), R('NAVM', 0, NAV0, sub('NVER', struct.pack('<I', 11)))]),
                                     (1, 0): (C10, [R('LAND', 0, LAND1, vhgt())])})
write(game, NV)

# ---------- a form ID goes by its file, whatever number the plugin has for it ----------
# (DLC.esm is index 1 for Mine.esp, but index 2 for Later.esp, which has another master in between)
DLC_FORM = 0x800
plain('DLC.esm', [NV], [('MISC', 0x01000000 | DLC_FORM, misc('DlcThing'))], esm=True)
plain('Lib.esm', [NV], [('MISC', 0x01000000 | 0x801, misc('LibThing'))], esm=True)
plain('Mine.esp', [NV, 'DLC.esm'], [('MISC', GUN, misc('Gun', value=99)),                     # (changed, and a later plugin overwrites)
                                    ('MISC', GUN2, misc('GunTwo', value=99)),                 # (a later plugin has the same bytes)
                                    ('MISC', GUN3, misc('GunThree', value=99)),               # (later plugin differs only in what's not mine)
                                    ('MISC', 0x01000000 | DLC_FORM, misc('DlcThing', value=7)),   # (a record of the DLC's)
                                    ('MISC', 0x02000000 | 0xA00, misc('MyOwnThing')),          # (my own)
                                    ('NPC_', NPC, edid('Trudy') + sub('FULL', b'Trudy Mine\0')),
                                    ('SCPT', SCPT, edid('GunScript') + sub('SCTX', b'; mine\0')),
                                    ('QUST', QUEST, edid('GunQuest') + sub('FULL', b'Mine\0')),
                                    ('CONT', 0x90A, edid('Chest') + sub('CNTO', struct.pack('<Ii', GUN, 1)) + sub('CNTO', struct.pack('<Ii', GUN2, 1)))])
later = tree_for([NV, 'Lib.esm', 'DLC.esm'])
for tag, fid, data in (('MISC', GUN, misc('Gun', value=50)),
                       ('MISC', GUN2, misc('GunTwo', value=99)),
                       ('MISC', GUN3, misc('GunThree', value=99, weight=9.0)),    # (the weight isn't mine to lose)
                       ('MISC', 0x02000000 | DLC_FORM, misc('DlcThing', value=8)),
                       ('NPC_', NPC, edid('Trudy') + sub('FULL', b'Trudy Later\0')),
                       ('SCPT', SCPT, edid('GunScript') + sub('SCTX', b'; later\0')),
                       ('QUST', QUEST, edid('GunQuest') + sub('FULL', b'Later\0')),
                       ('CONT', 0x90A, edid('Chest') + sub('CNTO', struct.pack('<Ii', GUN, 1)) + sub('CNTO', struct.pack('<Ii', LOCK, 1)))):
    later.top(tag).kids.append(R(tag, 0, fid, data))
write(later, 'Later.esp')
order_list(NV, 'DLC.esm', 'Lib.esm', 'Mine.esp', 'Later.esp')
mine = os.path.join(FAKE, 'Mine.esp')

times0 = {f: os.path.getmtime(os.path.join(FAKE, f)) for f in os.listdir(FAKE)}
with open(install.plugins_txt(), 'rb') as f:
    txt0 = f.read()
marks = []
rep = conflicts.check(FAKE, mine, lambda *a: marks.append(a))
print('  summary:', rep['summary'], 'issues:', [(i['issue'], i['count']) for i in rep['issues']])
check('checking changes no file and not the list', txt0 == open(install.plugins_txt(), 'rb').read() and
      times0 == {f: os.path.getmtime(os.path.join(FAKE, f)) for f in os.listdir(FAKE)})
check('the real plugins.txt wasn\'t the one used', not REAL_LOCAL or not install.plugins_txt().startswith(REAL_LOCAL))
check('progress is told, file by file', any(m[0] == 'reading' and m[3] == 'Later.esp' for m in marks) and any(m[0] == 'comparing' for m in marks))

over = find(rep, 'overwritten')
gun = [r for r in over if 'Gun (' in r['text']]
check('a later plugin overwriting a change: found, and who wins', gun and gun[0]['wins'] == 'Later.esp', over)
check('it names the field that\'s lost', gun and any('Value' in f or 'DATA' in f for f in gun[0]['fields']), gun and gun[0]['fields'])
check('byte-identical: not a clash', not only(rep, 'overwritten', 'GunTwo') and rep['harmless'].get('same') == 1, rep['harmless'])
check('differs only in a field the mod left alone: not a clash', not only(rep, 'overwritten', 'GunThree') and rep['harmless'].get('other_fields', 0) >= 1, rep['harmless'])
check('form IDs through each file\'s own masters: same record, different numbers', any('DlcThing' in r['text'] and r['wins'] == 'Later.esp' for r in over), over)
check('a record of mine nobody else has isn\'t mentioned', not any('MyOwnThing' in r['text'] for g in rep['groups'] for r in g['rows']))
by = {g['kind']: g for g in rep['groups']}
check('grouped: items', 'items' in by and any('Gun (' in r['text'] for r in by['items']['rows']))
check('grouped: characters', 'npcs' in by and any('Trudy' in r['text'] for r in by['npcs']['rows']))
check('grouped: scripts', 'scripts' in by and any('GunScript' in r['text'] for r in by['scripts']['rows']))
check('grouped: quests', 'quests' in by and any('GunQuest' in r['text'] for r in by['quests']['rows']))
chest = [r for r in over if 'Chest' in r['text']]
check('an inventory line I added and they don\'t have is lost', chest and any('Item' in f or 'CNTO' in f or 'nventory' in f for f in chest[0]['fields']), chest)
check('what to do: move after them, offered as a move', gun and gun[0]['move'] == {'plugin': 'Mine.esp', 'after': 'Later.esp'}, gun and gun[0].get('move'))
check('plain words: what the player notices', gun and gun[0]['notice'] and gun[0]['advice'])
m = next((x for x in rep['mods'] if x['name'] == 'Later.esp'), None)
check('a line per mod: how often they win', m and m['beats'] >= 5 and m['move'], m)

# side by side
cmp = conflicts.compare(FAKE, mine, 'FalloutNV.esm:%06X' % GUN)
check('side by side: every copy in load order, the last wins', [c['plugin'] for c in cmp['columns']] == [NV, 'Mine.esp', 'Later.esp'] and cmp['columns'][-1].get('wins'), cmp['columns'])
check('side by side: a row that differs is marked', any(r['differs'] for r in cmp['rows']) and any(not r['differs'] for r in cmp['rows']), cmp['rows'])
cmp = conflicts.compare(FAKE, mine, 'DLC.esm:%06X' % DLC_FORM)
check('side by side: across different numbering', [c['plugin'] for c in cmp['columns']] == ['DLC.esm', 'Mine.esp', 'Later.esp'], cmp['columns'])

# ---------- the cache ----------
d = conflicts.cache_dir()
kept = sorted(os.listdir(d))
check('each file\'s headers kept in FOLab\'s own cache', len(kept) == 5 and all(n.endswith('.idx') for n in kept), kept)
check('nothing written beside the game', not [f for f in os.listdir(FAKE) if not f.endswith(('.esm', '.esp'))])
conflicts._mem.clear()
calls = []
real_scan = conflicts._scan
conflicts._scan = lambda p: calls.append(p) or real_scan(p)
again = conflicts.check(FAKE, mine)
check('second run reads the cache, not the files', not calls, calls)
check('and finds the same', again['summary'] == rep['summary'])
conflicts._mem.clear()
plain('Later2.esp', [NV], [('MISC', GUN, misc('Gun', value=51))])
os.utime(os.path.join(FAKE, 'Later2.esp'), (clock[0], clock[0]))
again = conflicts.check(FAKE, mine)
check('a file not on the list isn\'t read', not calls and not any(x['name'] == 'Later2.esp' for x in again['mods']))
order_list(NV, 'DLC.esm', 'Lib.esm', 'Mine.esp', 'Later.esp', 'Later2.esp', dates=False)
conflicts._mem.clear()
plain('Later.esp', [NV], [('MISC', GUN, misc('Gun', value=52))])
calls.clear()
again = conflicts.check(FAKE, mine)
names = {os.path.basename(c) for c in calls}
check('a changed file is read again, the others aren\'t', 'Later.esp' in names and 'FalloutNV.esm' not in names, names)
check('its old entry is gone', sum(1 for n in os.listdir(d) if n.lower().startswith('later.esp.')) == 1, os.listdir(d))
conflicts._scan = real_scan
os.remove(os.path.join(FAKE, 'Later2.esp'))

# ---------- floats a hair apart aren't a change ----------
plain('Hair.esp', [NV], [('MISC', LOCK, misc('Lock', weight=1.0 + 1e-6)), ('MISC', OTHER_IT, misc('OtherThing', value=9))])
plain('Hair2.esp', [NV], [('MISC', LOCK, misc('Lock', value=3)), ('MISC', OTHER_IT, misc('OtherThing', value=9, weight=1.0 + 1e-6))])
order_list(NV, 'Hair.esp', 'Hair2.esp')
rep = conflicts.check(FAKE, os.path.join(FAKE, 'Hair.esp'))
check('a float changed only by rounding is no change, and no loss', not rep['groups'], rep['groups'])

# ---------- page scripts: this one's names are its own (a repeated const stops a whole script loading) ----------
import re
web = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app', 'web')
top = re.compile(r'^(?:const|let|var|function|async function)\s+([A-Za-z_$][\w$]*)', re.M)
with open(os.path.join(web, 'conflicts.js'), encoding='utf-8') as f:
    src = f.read()
mine_names = set(top.findall(src))
others = set()
for fn in os.listdir(web):
    if fn.endswith('.js') and fn != 'conflicts.js':
        with open(os.path.join(web, fn), encoding='utf-8') as f:
            others |= set(top.findall(f.read()))
check('every global of conflicts.js is its own', mine_names and not mine_names & others, mine_names & others)
check('...and has the prefix', all(n.lower().startswith('mcf') for n in mine_names), mine_names)
ids = set(re.findall(r'id="(mcf-[\w-]+)"', src))
check('its element IDs too', ids and all(i.startswith('mcf-') for i in ids))

# ---------- a mod that loads last wins, and who loses by it ----------
plain('Early.esp', [NV], [('MISC', GUN, misc('Gun', value=20, weight=3.0))])
plain('Last.esp', [NV], [('MISC', GUN, misc('Gun', value=30))])
order_list(NV, 'Early.esp', 'Last.esp')
rep = conflicts.check(FAKE, os.path.join(FAKE, 'Last.esp'))
under = find(rep, 'you_overwrite')
check('winning: someone else\'s change undone is told', under and under[0]['losers'] == ['Early.esp'], under)
check('...and no overwritten row', not find(rep, 'overwritten'))
plain('Dirty.esp', [NV], [('MISC', GUN, misc('Gun'))])
order_list(NV, 'Early.esp', 'Dirty.esp')
rep = conflicts.check(FAKE, os.path.join(FAKE, 'Dirty.esp'))
under = find(rep, 'you_overwrite')
check('a copy that changes nothing and undoes theirs: said so', under and under[0].get('itm') and 'changes nothing' in under[0]['text'], under)
# (the copy is built on Early: then Early isn't someone else, it's under it on purpose)
plain('Built.esp', [NV, 'Early.esp'], [('MISC', GUN, misc('Gun', value=70))])
order_list(NV, 'Early.esp', 'Built.esp')
rep = conflicts.check(FAKE, os.path.join(FAKE, 'Built.esp'))
check('a master under it isn\'t a clash', not rep['groups'] and rep['contested'] == 0, rep['groups'])

# ---------- someone built on my mod ----------
plain('Base.esp', [NV], [('MISC', GUN, misc('Gun', value=33)), ('MISC', 0x01000000 | 0xB00, misc('BaseOwn'))])
plain('Patch.esp', [NV, 'Base.esp'], [('MISC', GUN, misc('Gun', value=34)), ('MISC', 0x01000000 | 0xB00, misc('BaseOwn', value=12))])
order_list(NV, 'Base.esp', 'Patch.esp')
rep = conflicts.check(FAKE, os.path.join(FAKE, 'Base.esp'))
pa = find(rep, 'patched')
check('a plugin built on mine is a patch, not an overwrite', len(pa) == 2 and not find(rep, 'overwritten'), rep['issues'])
check('and my own record is matched through its master list', any('BaseOwn' in r['text'] for r in pa), pa)
check('a patch can\'t be loaded under: no move offered', not any(r.get('move') for r in pa))

# ---------- deleted records ----------
DEL = tes4.DELETED
plain('Killer.esp', [NV], [('MISC', GONE, b'', DEL)])
plain('Changer.esp', [NV], [('MISC', GONE, misc('Gone', value=9))])
order_list(NV, 'Changer.esp', 'Killer.esp')
rep = conflicts.check(FAKE, os.path.join(FAKE, 'Changer.esp'))
dl = find(rep, 'deleted')
check('a later plugin deleting what I change', dl and 'Killer.esp deletes' in dl[0]['text'] and dl[0]['sev'] == 'error', rep['issues'])
rep = conflicts.check(FAKE, os.path.join(FAKE, 'Killer.esp'))
dl = find(rep, 'deleted')
check('my mod deleting what they change', dl and 'Your mod deletes' in dl[0]['text'], rep['issues'])
os.utime(os.path.join(FAKE, 'Changer.esp'), (clock[0] + 500, clock[0] + 500))
conflicts._mem.clear()
rep = conflicts.check(FAKE, os.path.join(FAKE, 'Changer.esp'))
dl = find(rep, 'deleted')
check('overriding a record someone deleted brings it back', dl and 'brings back' in dl[0]['text'], rep['issues'])
os.utime(os.path.join(FAKE, 'Changer.esp'), (clock[0], clock[0]))
# (my thing links to a record a mod deleted)
plain('Linker.esp', [NV], [('REFR', 0x01000C00, ref(GONE))])
order_list(NV, 'Linker.esp', 'Killer.esp')
rep = conflicts.check(FAKE, os.path.join(FAKE, 'Linker.esp'))
dl = find(rep, 'deleted')
check('a link to something a mod deleted', dl and 'links to' in dl[0]['text'] and 'Killer.esp' in dl[0]['text'], rep['issues'])

# ---------- a topic both add to ----------
plain('TopicA.esp', [NV], [('DIAL', 0x913, edid('Greet') + sub('QSTI', struct.pack('<I', QUEST)))])
plain('TopicB.esp', [NV], [('DIAL', 0x913, edid('Greet') + sub('QSTI', struct.pack('<I', 0x914)))])
order_list(NV, 'TopicA.esp', 'TopicB.esp')
rep = conflicts.check(FAKE, os.path.join(FAKE, 'TopicA.esp'))
check('a topic both add to: told, not an error', find(rep, 'topic') and find(rep, 'topic')[0]['sev'] == 'warn' and not find(rep, 'overwritten'), rep['issues'])

# ---------- places: settings, placed things, doors ----------
def place_mod(name, masters, cell, cell_data, kids, flags=0):
    t = tree_for(masters)
    inside(t, cell, cell_data, kids, flags)
    return write(t, name)


# carried cell, same settings: no clash. changed settings, overwritten: a clash.
game_cell = edid('Hall') + sub('XCLL', b'\x10' * 40)
place_mod('CarryA.esp', [NV], HALL, game_cell, [R('REFR', 0, 0x01000D00, ref(STAT, x=2.0))])
place_mod('CarryB.esp', [NV], HALL, game_cell, [R('REFR', 0, 0x01000D00, ref(STAT, x=3.0))])
order_list(NV, 'CarryA.esp', 'CarryB.esp')
rep = conflicts.check(FAKE, os.path.join(FAKE, 'CarryA.esp'))
check('two mods carrying a place unchanged: no clash', not find(rep, 'cell_header') and rep['harmless'].get('no_change', 0) + rep['harmless'].get('same', 0) >= 1, rep['issues'])
check('new things with the same number in different plugins are different things', not find(rep, 'overwritten'), rep['issues'])
place_mod('Light.esp', [NV], HALL, edid('Hall') + sub('XCLL', b'\x20' * 40), [])
order_list(NV, 'Light.esp', 'CarryB.esp')
rep = conflicts.check(FAKE, os.path.join(FAKE, 'Light.esp'))
ch = find(rep, 'cell_header')
check('my place\'s settings overwritten by a later mod that only carries it', ch and ch[0]['wins'] == 'CarryB.esp' and ch[0]['group'] == 'cell', rep['issues'])
rep = conflicts.check(FAKE, os.path.join(FAKE, 'CarryB.esp'))
ch = find(rep, 'cell_header')
check('...and from the carrier\'s side: it undoes them', ch and ch[0].get('losers') == ['Light.esp'], rep['issues'])
# a placed thing moved by both
t = 0x924
place_mod('MoveA.esp', [NV], HOUSE, edid('House'), [R('REFR', 0, t, ref(STAT, x=100.0))])
place_mod('MoveB.esp', [NV], HOUSE, edid('House'), [R('REFR', 0, t, ref(STAT, x=200.0))])
order_list(NV, 'MoveA.esp', 'MoveB.esp')
rep = conflicts.check(FAKE, os.path.join(FAKE, 'MoveA.esp'))
mv = [r for r in find(rep, 'overwritten') if r['group'] == 'cell']
check('a placed thing moved by both: overwritten, in the places group', mv and 'where it stands' in mv[0]['fields'], rep['issues'])
check('it says what it is and where', mv and 'Crate' in mv[0]['text'] and 'House' in mv[0]['text'], mv)
# a thing moved by one, its scale by the other: mine is lost, whole-record rule
place_mod('ScaleB.esp', [NV], HOUSE, edid('House'), [R('REFR', 0, t, ref(STAT, x=1.0, extra=sub('XSCL', struct.pack('<f', 2.0))))])
order_list(NV, 'MoveA.esp', 'ScaleB.esp')
rep = conflicts.check(FAKE, os.path.join(FAKE, 'MoveA.esp'))
check('they changed something else, but their copy still has the old spot: my move is lost', find(rep, 'overwritten'), rep['issues'])
# carrying my move and adding scale: harmless
place_mod('ScaleC.esp', [NV], HOUSE, edid('House'), [R('REFR', 0, t, ref(STAT, x=100.0, extra=sub('XSCL', struct.pack('<f', 2.0))))])
order_list(NV, 'MoveA.esp', 'ScaleC.esp')
rep = conflicts.check(FAKE, os.path.join(FAKE, 'MoveA.esp'))
check('they keep my move and add a size: harmless', not find(rep, 'overwritten') and rep['harmless'].get('other_fields', 0) >= 1, rep['issues'])
# doors
place_mod('DoorMine.esp', [NV], HALL, game_cell, [R('REFR', 0, DOOR_A, ref(STAT, door=0x924))])
place_mod('DoorThey.esp', [NV], HALL, game_cell, [R('REFR', 0, DOOR_A, ref(STAT, door=DOOR_B, x=5.0))])
order_list(NV, 'DoorMine.esp', 'DoorThey.esp')
rep = conflicts.check(FAKE, os.path.join(FAKE, 'DoorMine.esp'))
dr = find(rep, 'door')
check('my door\'s link overwritten', dr and 'door link' in dr[0]['fields'], rep['issues'])
# my door leads to a door another mod re-links
own = 0x01000E00
place_mod('NewDoor.esp', [NV], HALL, game_cell, [R('REFR', 0, own, ref(STAT, door=0x924))])
t2 = tree_for([NV])
inside(t2, HOUSE, edid('House'), [R('REFR', 0, 0x924, ref(STAT, x=1.0, door=DOOR_A))])
write(t2, 'Relink.esp')
order_list(NV, 'NewDoor.esp', 'Relink.esp')
rep = conflicts.check(FAKE, os.path.join(FAKE, 'NewDoor.esp'))
dr = find(rep, 'door')
check('the door at the far end leads elsewhere', dr and 'somewhere else' in dr[0]['text'] and 'Relink.esp' in dr[0]['text'], rep['issues'])
t2 = tree_for([NV])
inside(t2, HOUSE, edid('House'), [R('REFR', DEL, 0x924, b'')])
write(t2, 'Relink.esp')
rep = conflicts.check(FAKE, os.path.join(FAKE, 'NewDoor.esp'))
check('the door at the far end removed', any('removed' in r['text'] for r in find(rep, 'door')), rep['issues'])

# ---------- navmesh, ground ----------
def world_mod(name, squares, masters=(NV,)):
    t = tree_for(list(masters))
    outside(t, WORLD, edid('World'), squares)
    return write(t, name)


nav = lambda *b: sub('NVER', struct.pack('<I', 11)) + sub('DATA', struct.pack('<I5I', C00, 0, 0, 0, 0, 0) + bytes(b))
world_mod('NavA.esp', {(0, 0): (C00, [R('NAVM', 0, NAV0, nav(1))])})
world_mod('NavB.esp', {(0, 0): (C00, [R('NAVM', 0, NAV0, nav(2))])})
world_mod('NavSame.esp', {(0, 0): (C00, [R('NAVM', 0, NAV0, nav(1))])})
world_mod('NavOwn.esp', {(0, 0): (C00, [R('NAVM', 0, 0x01000F00, nav(3))])})
order_list(NV, 'NavA.esp', 'NavB.esp')
rep = conflicts.check(FAKE, os.path.join(FAKE, 'NavA.esp'))
nv = find(rep, 'navmesh')
check('the same navmesh changed by both', nv and nv[0]['wins'] == 'NavB.esp' and nv[0]['sev'] == 'error' and nv[0]['group'] == 'navmesh', rep['issues'])
order_list(NV, 'NavA.esp', 'NavOwn.esp')
rep = conflicts.check(FAKE, os.path.join(FAKE, 'NavA.esp'))
nv = find(rep, 'navmesh')
check('two meshes of their own in one cell', nv and 'each put' in nv[0]['text'], rep['issues'])
order_list(NV, 'NavA.esp', 'NavSame.esp')
rep = conflicts.check(FAKE, os.path.join(FAKE, 'NavA.esp'))
check('the same navmesh byte for byte: no clash', not find(rep, 'navmesh') and rep['harmless'].get('same', 0) >= 1, rep['issues'])
plain('NaviA.esp', [NV], [('NAVI', 0x014B92, sub('NVER', struct.pack('<I', 11)) + sub('NVMI', b'\1' * 16))])
plain('NaviB.esp', [NV], [('NAVI', 0x014B92, sub('NVER', struct.pack('<I', 11)) + sub('NVMI', b'\2' * 16))])
order_list(NV, 'NaviA.esp', 'NaviB.esp')
rep = conflicts.check(FAKE, os.path.join(FAKE, 'NaviA.esp'))
check('NAVI isn\'t a clash: the game merges it', not rep['groups'] and rep['contested'] == 0, rep['groups'])

world_mod('LandA.esp', {(0, 0): (C00, [R('LAND', 0, LAND0, vhgt(10.0))])})
world_mod('LandB.esp', {(0, 0): (C00, [R('LAND', 0, LAND0, vhgt(20.0))])})
order_list(NV, 'LandA.esp', 'LandB.esp')
rep = conflicts.check(FAKE, os.path.join(FAKE, 'LandA.esp'))
ld = find(rep, 'land')
check('ground changed by both, in the same square', ld and ld[0]['wins'] == 'LandB.esp' and 'ground shape' in ld[0]['fields'] and ld[0]['group'] == 'land', rep['issues'])
rep = conflicts.check(FAKE, os.path.join(FAKE, 'LandB.esp'))
ld = find(rep, 'land')
check('...and from the winner\'s side', ld and ld[0].get('losers') == ['LandA.esp'], rep['issues'])
sm = find(rep, 'land_seam')
check('a seam: my square stands at another height than the one beside it', sm and 'east' in sm[0]['text'], rep['issues'])
print('  seam:', sm and sm[0]['text'])
# (a square of mine raised along with its neighbour: no seam where the winners agree)
world_mod('LandBoth.esp', {(0, 0): (C00, [R('LAND', 0, LAND0, vhgt(20.0))]), (1, 0): (C10, [R('LAND', 0, LAND1, vhgt(20.0))])})
order_list(NV, 'LandBoth.esp')
rep = conflicts.check(FAKE, os.path.join(FAKE, 'LandBoth.esp'))
check('both squares raised together: no seam', not find(rep, 'land_seam') and not find(rep, 'land'), rep['issues'])
# (mine raises two squares; another mod wins one of them flat: a seam appears between mine and theirs)
world_mod('LandFlat.esp', {(1, 0): (C10, [R('LAND', 0, LAND1, vhgt(0.0, ramp=0))])})
order_list(NV, 'LandBoth.esp', 'LandFlat.esp')
rep = conflicts.check(FAKE, os.path.join(FAKE, 'LandBoth.esp'))
sm = find(rep, 'land_seam')
check('another mod winning the next square: a crack between the two', sm and 'LandFlat.esp' in sm[0]['text'] and 'east' in sm[0]['text'], rep['issues'])
check('land textures count as ground too', conflicts.label_of('LAND', 'ATXT') == 'ground textures')

# ---------- masters ----------
plain('Needs.esp', [NV, 'NotThere.esm'], [])
order_list(NV, 'Needs.esp')
rep = conflicts.check(FAKE, os.path.join(FAKE, 'Needs.esp'))
ms = find(rep, 'master')
check('a master that\'s missing, ranked first', ms and 'NotThere.esm' in ms[0]['text'] and rep['issues'][0]['issue'] == 'master', rep['issues'])
# (out of order: a master flagged plugin order)
plain('LibLate.esp', [NV], [])
plain('NeedLate.esp', [NV, 'LibLate.esp'], [])
order_list(NV, 'LibLate.esp', 'NeedLate.esp')
os.utime(os.path.join(FAKE, 'LibLate.esp'), (clock[0] + 900, clock[0] + 900))
conflicts._mem.clear()
rep = conflicts.check(FAKE, os.path.join(FAKE, 'NeedLate.esp'))
check('a master loading after it', any('loads after' in r['text'] for r in find(rep, 'master')), rep['issues'])
rep = conflicts.check(FAKE, os.path.join(FAKE, 'LibLate.esp'))
check('...and from the master\'s side', any('NeedLate.esp' in r['text'] for r in find(rep, 'master')), rep['issues'])
plain('Off.esp', [NV, 'SwitchedOff.esp'], [])
plain('SwitchedOff.esp', [NV], [])
order_list(NV, 'Off.esp')
rep = conflicts.check(FAKE, os.path.join(FAKE, 'Off.esp'))
check('a master that\'s switched off', any('switched off' in r['text'] for r in find(rep, 'master')), rep['issues'])
order_list(NV, 'Vanished.esp', 'Gone2.esp', 'Mine.esp')
rep = conflicts.check(FAKE, mine)
check('plugins on the list with no file: said, not failed', any('Vanished.esp' in n and 'mod manager' in n for n in rep['notes']), rep['notes'])

# ---------- ranking ----------
plain('RankA.esp', [NV], [('MISC', OTHER_IT, misc('OtherThing', value=2)), ('MISC', GONE, misc('Gone', value=2))])
plain('RankB.esp', [NV], [('MISC', OTHER_IT, misc('OtherThing', value=3)), ('MISC', GONE, b'', DEL)])
t3 = tree_for([NV, 'Absent.esm'])
for tag, fid, data, fl in (('MISC', OTHER_IT, misc('OtherThing', value=2), 0), ('MISC', GONE, misc('Gone', value=2), 0)):
    t3.top(tag).kids.append(R(tag, fl, fid, data))
inside(t3, HALL, edid('Hall') + sub('XCLL', b'\x30' * 40), [])
write(t3, 'RankM.esp')
order_list(NV, 'RankM.esp', 'RankB.esp', 'CarryB.esp')
conflicts._mem.clear()
rep = conflicts.check(FAKE, os.path.join(FAKE, 'RankM.esp'))
seq = [i['issue'] for i in rep['issues']]
check('ranked by what will go wrong', seq[:3] == ['master', 'deleted', 'overwritten'] and seq.index('overwritten') < seq.index('cell_header'), seq)
check('rows carry their rank in order', [g['kind'] for g in rep['groups']][:1] == ['masters'])

# ---------- moving: only at a click, dates and a backup, fake folders only ----------
plain('Dep.esp', [NV, 'MoveMe.esp'], [])
plain('MoveMe.esp', [NV], [('MISC', OTHER_IT, misc('OtherThing', value=2))])
plain('Wins.esp', [NV], [('MISC', OTHER_IT, misc('OtherThing', value=3))])
order_list(NV, 'MoveMe.esp', 'Wins.esp', 'Dep.esp')
conflicts._mem.clear()
rep = conflicts.check(FAKE, os.path.join(FAKE, 'MoveMe.esp'))
row = find(rep, 'overwritten')[0]
check('with something needing it in between... no: it can still go past Wins.esp', row['move'] == {'plugin': 'MoveMe.esp', 'after': 'Wins.esp'}, row)
names, bad = conflicts.plan_move(FAKE, 'MoveMe.esp', 'Dep.esp')
check('moving past a plugin that needs it is refused', bad and 'Dep.esp needs MoveMe.esp' in bad[0], bad)
try:
    conflicts.move(FAKE, 'MoveMe.esp', 'Dep.esp')
    check('refused for real', False)
except ValueError:
    check('refused for real', True)
before = {f: os.path.getmtime(os.path.join(FAKE, f)) for f in os.listdir(FAKE)}
data_before = {f: open(os.path.join(FAKE, f), 'rb').read() for f in os.listdir(FAKE)}
txt_before = open(install.plugins_txt(), 'rb').read()
out = conflicts.move(FAKE, 'MoveMe.esp', 'Wins.esp')
check('a move keeps a backup first', out['changed'] and out['backup'] in loadorder.backups(), out)
now = [r['name'] for r in loadorder.read(FAKE)['rows']]
check('the move took: mine loads after theirs', now.index('MoveMe.esp') > now.index('Wins.esp'), now)
check('and the plugin that needs it still loads after it', now.index('Dep.esp') > now.index('MoveMe.esp'), now)
check('file contents untouched', data_before == {f: open(os.path.join(FAKE, f), 'rb').read() for f in os.listdir(FAKE)})
check('the game\'s own file keeps its date', os.path.getmtime(os.path.join(FAKE, NV)) == before[NV])
conflicts._mem.clear()
rep = conflicts.check(FAKE, os.path.join(FAKE, 'MoveMe.esp'))
check('after the move: mine wins, theirs is the one undone', find(rep, 'you_overwrite') and not find(rep, 'overwritten'), rep['issues'])
loadorder.restore(FAKE, out['backup'])
now = [r['name'] for r in loadorder.read(FAKE)['rows']]
check('and it can be put back', now.index('MoveMe.esp') < now.index('Wins.esp'), now)
check('put back: the list is as it was', txt_before == open(install.plugins_txt(), 'rb').read())
try:
    conflicts.plan_move(FAKE, NV, 'Wins.esp')
    check('the game\'s own files don\'t move', False)
except ValueError:
    check('the game\'s own files don\'t move', True)
plain('MasterMod.esm', [NV], [], esm=True)
try:
    conflicts.plan_move(FAKE, 'MasterMod.esm', 'Wins.esp')
    check('a master can\'t move among plugins', False)
except ValueError:
    check('a master can\'t move among plugins', True)
# a master can't be moved past a plugin: no move offered
plain('MasterMine.esm', [NV], [('MISC', ORDER_IT, misc('OrderThing', value=2))], esm=True)
plain('PlugTheirs.esp', [NV], [('MISC', ORDER_IT, misc('OrderThing', value=3))])
order_list(NV, 'MasterMine.esm', 'PlugTheirs.esp')
conflicts._mem.clear()
rep = conflicts.check(FAKE, os.path.join(FAKE, 'MasterMine.esm'))
row = find(rep, 'overwritten')[0]
check('a master losing to a plugin: no move, says why', not row['move'] and 'always loads before' in row['advice'], row)

# ---------- a mod not yet in Data, as it would be saved ----------
scratch = os.path.join(HOME, 'scratch')
os.makedirs(scratch)
t4 = tree_for([NV])
t4.top('MISC').kids.append(R('MISC', 0, LOCK, misc('Lock', value=2)))
p4 = write(t4, 'NotIn.esp', scratch)
plain('HasLock.esp', [NV], [('MISC', LOCK, misc('Lock', value=3))])
order_list(NV, 'HasLock.esp')
conflicts._mem.clear()
rep = conflicts.check(FAKE, p4)
check('a mod not in Data is checked as if loaded last', not rep['installed'] and rep['place'] == rep['of'] and find(rep, 'you_overwrite'), rep['issues'])
check('nothing kept for a scratch file', not any(n.lower().startswith('notin.esp') for n in os.listdir(d)))
# its copy in Data is replaced by the scratch one, at that place
t5 = tree_for([NV])
t5.top('MISC').kids.append(R('MISC', 0, LOCK, misc('Lock', value=4)))
write(t5, 'Inst.esp')
plain('HasLock2.esp', [NV], [('MISC', LOCK, misc('Lock', value=3))])
order_list(NV, 'Inst.esp', 'HasLock2.esp')
t6 = tree_for([NV])
t6.top('MISC').kids.append(R('MISC', 0, LOCK, misc('Lock', value=6)))
p6 = write(t6, 'Inst.esp', scratch)
conflicts._mem.clear()
rep = conflicts.check(FAKE, p6)
over = find(rep, 'overwritten')
check('a saved-over mod takes the place of its copy in Data', rep['installed'] and over and over[0]['wins'] == 'HasLock2.esp', rep['issues'])
cmp = conflicts.compare(FAKE, p6, 'FalloutNV.esm:%06X' % LOCK)
vals = [r for r in cmp['rows'] if r['differs']]
check('side by side reads the scratch copy', cmp['columns'][1]['mine'] and vals and '6' in str(vals[0]['values'][1]), vals)

# ---------- the page's way: on a thread, with status; the short line ----------
class FakeS:
    class GD:
        data_dir = FAKE
        forms = {}

        @staticmethod
        def from_key(k):
            raise ValueError(k)
    PR = None
    _lock = threading.Lock()


conflicts._mem.clear()
st = conflicts.start(FakeS, 'Inst.esp')
t0 = time.time()
while st['running'] and time.time() - t0 < 60:
    time.sleep(0.05)
    st = conflicts.status()
check('run on a thread, the result in the status', st.get('result') and st['result']['plugin'] == 'Inst.esp', st)
s = conflicts.short()
check('a short line for the health check', s and s['sev'] == 'error' and '1 clash' in s['text'] and not s['mine'], s)
check('the result can be sent to the page', json.dumps(st['result']) and True)
check('compare_last uses what was checked', conflicts.compare_last(FAKE, 'FalloutNV.esm:%06X' % LOCK)['columns'])
try:
    r = conflicts.start(FakeS, None)
    check('no mod and nothing picked: says so', r['error'] and not r['running'], r)
except Exception as e:
    check('no mod and nothing picked: says so', False, e)

# ---------- speed: a list of many small plugins, kept headers ----------
many = [NV]
for i in range(150):
    n = 'Many%03d.esp' % i
    plain(n, [NV], [('MISC', OTHER_IT if i % 2 else SAME_IT, misc('Thing', value=i))] + [('STAT', 0x01000800 + k, edid('S%d' % k)) for k in range(300)])
    many.append(n)
t7 = tree_for([NV])
t7.top('MISC').kids.append(R('MISC', 0, OTHER_IT, misc('OtherThing', value=999)))
pm = write(t7, 'ManyMine.esp')
many.append('ManyMine.esp')
many.remove('Many000.esp')
many.append('Many000.esp')
order_list(*many)
conflicts._mem.clear()
t0 = time.time()
rep = conflicts.check(FAKE, pm)
first = time.time() - t0
conflicts._mem.clear()
t0 = time.time()
rep2 = conflicts.check(FAKE, pm)
second = time.time() - t0
print('  150 plugins: %.2fs first, %.2fs with kept headers' % (first, second))
check('150 small plugins in a few seconds', first < 20, first)
check('kept headers run faster than reading', second < max(first, 0.5), (first, second))
check('and find the same', rep['summary'] == rep2['summary'])

# ---------- the open mod, written by the real writer over the game's real records (read only); the list is the fake one ----------
import copy, espwrite, gamedata, health, modtools, project, recordio
os.environ.pop('FOLAB_NV_DATA', None)
gd = gamedata.GameData()
two = [f for f, (i, r) in gd.forms.items() if r.tag == 'MISC' and f >> 24 == 0][:2]
pr = project.Project.create('Clashing')
one = copy.deepcopy(recordio.load(gd, two[0]))
recordio.set_field(one, 'EDID', 'MineEdit')
pr.apply('m', [{'op': 'record', 'key': gd.key(two[0]), 'record': one},
               {'op': 'record', 'key': gd.key(two[1]), 'record': copy.deepcopy(recordio.load(gd, two[1]))}])


class RealS:
    _lock = threading.RLock()
    GD, PR = gd, pr

    @classmethod
    def edit(cls, label, ops):
        return {'made': cls.PR.apply(label, ops)}

    @staticmethod
    def state():
        return {}

    @staticmethod
    def not_while_playing():
        pass


raw = lambda f: gd.plugins[0].data(gd.forms[f][1])
FAKE2 = os.path.join(HOME, 'second game', 'Data')
os.makedirs(FAKE2)
t = tree_for([], True)
for f in two:
    t.top('MISC').kids.append(R('MISC', 0, f & 0xFFFFFF, raw(f)))
write(t, NV, FAKE2)
t = tree_for([NV])
t.top('MISC').kids.append(R('MISC', 0, two[1] & 0xFFFFFF, edid('TheirEarlierEdit')))
write(t, 'TheirEarly.esp', FAKE2)
t = tree_for([NV])
t.top('MISC').kids.append(R('MISC', 0, two[0] & 0xFFFFFF, edid('TheirEdit') + raw(two[0])[len(tes4.subrecord_dict(raw(two[0]))['EDID']) + 6:]))
later_path = write(t, 'TheirLater.esp', FAKE2)
order_list(NV, 'TheirEarly.esp', 'TheirLater.esp', dates=False)
# (not in Data, it would load last: a copy there gives it a place, under TheirLater)
mine_copy = os.path.join(FAKE2, pr.plugin)
espwrite.write(gd, pr, mine_copy)
when = os.path.getmtime(later_path) - 50
os.utime(mine_copy, (when, when))
order_list(NV, 'TheirEarly.esp', pr.plugin, 'TheirLater.esp', dates=False)
os.utime(os.path.join(FAKE2, 'TheirEarly.esp'), (when - 50, when - 50))
conflicts._mem.clear()
st = conflicts.start(RealS, None, data_dir=FAKE2)
t0 = time.time()
while st['running'] and time.time() - t0 < 120:
    time.sleep(0.05)
    st = conflicts.status()
out = st.get('result')
check('the open mod, as it would be saved', out and out['plugin'] == pr.plugin and out['mine_open'], st)
over = find(out, 'overwritten') if out else []
check('its change overwritten', over and over[0]['wins'] == 'TheirLater.esp' and 'MineEdit' in over[0]['text'], out and out['issues'])
check('a click goes to the record in the game', over and over[0]['go'] == {'record': gd.key(two[0])}, over and over[0].get('go'))
carried = find(out, 'you_overwrite') if out else []
check('the copy that changes nothing: a fix, as an undoable step', carried and carried[0].get('fix') == {'action': 'revert_record', 'key': gd.key(two[1]), 'label': 'Take the copy out'}, carried)
s = conflicts.short()
check('its short line is the open mod\'s', s and s['mine'] and s['sev'] == 'error', s)
cmp = conflicts.compare_last(FAKE2, gd.key(two[0]))
check('side by side has its unsaved edit', any('MineEdit' in str(r['values']) for r in cmp['rows']), cmp['rows'][:2])
fixed = health.apply_fixes(RealS, [carried[0]['fix']])
check('the fix takes the copy out', fixed['fixed'] == 1 and gd.key(two[1]) not in pr.records, fixed)
check('the tool hook answers', modtools.get('conflicts/status', {}, RealS)['running'] is False)


class FakeTools(RealS):
    class GD:
        data_dir = FAKE2


got = modtools.post('conflicts/move', {'plugin': pr.plugin, 'after': 'TheirLater.esp'}, FakeTools)
now = [r['name'] for r in loadorder.read(FAKE2)['rows']]
check('the move through the tool hook, with a backup', got['changed'] and got['backup'] and now.index(pr.plugin) > now.index('TheirLater.esp'), now)
for p in gd.plugins:
    p.close()
check('the real game\'s folder isn\'t where any of this ran', os.path.normcase(os.path.abspath(FAKE2)) != os.path.normcase(os.path.abspath(gd.data_dir)))

check('only ever the fake folder', os.path.dirname(os.path.dirname(install.plugins_txt())) == LOCAL)
