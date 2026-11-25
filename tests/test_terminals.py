"""FOLab's terminal maker (terminals.py): a terminal written from plain text into a small mod of its own, then written as a
plugin and read back as the game reads it. Laid out as the game's terminals (subrecord order over FalloutNV.esm's 344), its
lock and difficulty, items releasing a door and a safe by their result scripts, a sub-menu, notes; the plain text's
mistakes refused. Nothing goes near the real game."""
import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import browse  # noqa: E402
import espwrite  # noqa: E402
import gamedata  # noqa: E402
import health  # noqa: E402
import project  # noqa: E402
import server  # noqa: E402
import terminals as T  # noqa: E402
import tes4  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


TEXT = """Terminal: FOLabTestTerminal
Name: Clinic Stores
Model: wall
Lock: average
Password: FOLabTestPassword
Note: FOLabTestPassword | Clinic password
  The password is SURF.
Welcome:
  WAIKIKI CLINIC STORES
  Authorised staff only.
== Open the medicine store
Unlocks: FOLabTestDoorREF by script
Says: Store door released.
== Open the safe
Unlocks: FOLabTestSafeREF
== Records
=== Stock list
Says:
  Stimpaks: 4
  Med-X: 1
=== Doctor's diary
Note: FOLabTestDiary | Doctor's diary
  The boats are late again.
"""

# ---- the plain text ----
spec = T.plan(TEXT)
check('read: editor ID, name, model, lock, password', (spec['edid'], spec['name'], spec['model'], spec['lock'], spec['password']) ==
      ('FOLabTestTerminal', 'Clinic Stores', 'wall', 'average', 'FOLabTestPassword'))
check('read: the welcome keeps its lines', spec['welcome'] == 'WAIKIKI CLINIC STORES\nAuthorised staff only.', repr(spec['welcome']))
check('read: three items, the third a sub-menu of two', [i['text'] for i in spec['items']] == ['Open the medicine store', 'Open the safe', 'Records']
      and [i['text'] for i in spec['items'][2]['menu']] == ['Stock list', "Doctor's diary"])
check('read: a says of several lines', spec['items'][2]['menu'][0]['says'] == 'Stimpaks: 4\nMed-X: 1', repr(spec['items'][2]['menu'][0]['says']))
check('read: the locks released', T.unlocks(spec) == ['FOLabTestDoorREF', 'FOLabTestSafeREF'])
check('read: notes, the item showing its own', [n['edid'] for n in spec['notes']] == ['FOLabTestPassword', 'FOLabTestDiary']
      and spec['items'][2]['menu'][1]['note'] == 'FOLabTestDiary' and spec['notes'][1]['text'] == 'The boats are late again.')
check('read: the Science a lock asks', T.science_needed(spec) == 50 and T.science_needed(T.plan('Terminal: X\n== a\n')) == 0)
check('read: by script, said or not', T.plan('Terminal: X\n== a\nUnlocks: R\n')['items'][0]['unlocks'] == [('R', 'script')]
      == T.plan('Terminal: X\n== a\nUnlocks: R by script\n')['items'][0]['unlocks'])
bad = {'no editor ID': '== a\n', 'no item': 'Terminal: X\n', 'a wrong lock': 'Terminal: X\nLock: medium\n== a\n',
       'a sub-item with nothing above': 'Terminal: X\n=== a\n', 'an unknown setting': 'Terminal: X\nColour: red\n== a\n',
       'a wrong way': 'Terminal: X\n== a\nUnlocks: R by magic\n', 'by note (no such route)': 'Terminal: X\n== a\nUnlocks: R by note\n'}
for what, text in bad.items():
    try:
        T.plan(text)
        check('refused: ' + what, False)
    except T.TermError:
        check('refused: ' + what, True)

# ---- a small mod: a place, a locked door and a locked safe with editor IDs ----
G = server.GD = gamedata.GameData()
server.BR = browse.Browse(G, lambda: server.PR)
pr = server.PR = project.Project.create('Terminal Test')
key = lambda e, tag: G.key(next(f for f, (i, r) in G.forms.items() if r.tag == tag and G.edid(f) == e))
place = server.new_place({'from': key('CrimsonCaravanBarracks01', 'CELL'), 'edid': 'FOLabTestClinic', 'name': 'Test Clinic'})['made'][0]
lock = {'level': 255}
made = server.edit('locked things', [
    {'op': 'add', 'cell': place, 'base': key('BarracksDoor', 'DOOR'), 'p': [0, 0, 0, 0, 0, 0], 's': 1.0,
     'extra': {'persistent': True, 'edid': 'FOLabTestDoorREF', 'props': {'lock': lock}}},
    {'op': 'add', 'cell': place, 'base': key('SafeWall01', 'CONT') if any(G.edid(f) == 'SafeWall01' for f in G.forms) else key('Footlocker01Military', 'CONT'),
     'p': [200, 0, 0, 0, 0, 0], 's': 1.0, 'extra': {'persistent': True, 'edid': 'FOLabTestSafeREF', 'props': {'lock': lock}}}])['made']
ops, keys = T.ops(G, pr, spec)
check('ops: notes, sub-menu, terminal, keys in order', [o['record']['type'] for o in ops] == ['NOTE', 'NOTE', 'TERM', 'TERM']
      and list(keys) == T.edids(spec), list(keys))
got = server.edit('the terminal', ops)['made']
check('ops: one Undo, keys as reserved', got == [keys[e] for e in T.edids(spec)])
server.edit('the terminal stood', [{'op': 'add', 'cell': place, 'base': keys['FOLabTestTerminal'], 'p': [100, 100, 0, 0, 0, 0], 's': 1.0}])
try:
    T.ops(G, pr, spec)
    check('a second terminal of the same editor ID refused', False)
except T.TermError:
    check('a second terminal of the same editor ID refused', True)

# ---- written and read back ----
os.makedirs(project.BUILD_DIR, exist_ok=True)
out = os.path.join(project.BUILD_DIR, 'Terminal Test.esp')
espwrite.write(G, pr, out)
g = gamedata.GameData(plugins=list(gamedata.OFFICIAL) + [out])
i = len(g.plugins) - 1
mine = {tes4.zstr(g.fields(f).get('EDID', b'')): f for f, (n, r) in g.forms.items() if n == i}
subs = lambda e: list(tes4.iter_subrecords(g.plugins[i].data(g.forms[mine[e]][1])))
t = subs('FOLabTestTerminal')
head = [k for k, _ in t][:8]
check('TERM laid out as the game\'s', head == ['EDID', 'OBND', 'FULL', 'MODL', 'DESC', 'SNAM', 'PNAM', 'DNAM'], head)
d = dict(t)
check('TERM: average lock, locked, wall model', d['DNAM'][:2] == bytes([2, 0]) and d['MODL'].rstrip(b'\0').lower() == b'terminals\\terminal01.nif')
check('TERM: the welcome has the game\'s line ends', d['DESC'] == b'WAIKIKI CLINIC STORES\r\nAuthorised staff only.\0')
local = {e: g.forms[f][1].formid for e, f in mine.items()}
refs = {}
for f, (n, r) in g.cell_refs[next(c for c in g.interiors if g.edid(c) == 'FOLabTestClinic')].items():
    e = tes4.zstr(dict(tes4.iter_subrecords(g.plugins[n].data(r))).get('EDID', b''))
    if e:
        refs[e] = r.formid
check('TERM: the password note', struct.unpack('<I', d['PNAM'])[0] == local['FOLabTestPassword'])
items, cur = [], None
for k, v in t:
    if k == 'ITXT':
        cur = {'text': v.rstrip(b'\0').decode(), 'subs': []}
        items.append(cur)
    elif cur is not None:
        cur['subs'].append((k, v))
check('TERM: three items', [x['text'] for x in items] == ['Open the medicine store', 'Open the safe', 'Records'])
one = dict(items[0]['subs'])
check('item 1: its script unlocks the door, the SCRO naming it', one.get('SCTX') == b'FOLabTestDoorREF.Unlock'
      and struct.unpack('<I', one['SCRO'])[0] == refs['FOLabTestDoorREF'])
check('item 1: its result text', one['RNAM'] == b'Store door released.\0')
two = dict(items[1]['subs'])
check('item 2: its script unlocks the safe, no note', two.get('SCTX') == b'FOLabTestSafeREF.Unlock' and 'INAM' not in two and struct.unpack('<I', two['SCRO'])[0] == refs['FOLabTestSafeREF'])
three = dict(items[2]['subs'])
check('item 3: opens the sub-menu', struct.unpack('<I', three['TNAM'])[0] == local['FOLabTestTerminalMenu3'])
sm = dict(subs('FOLabTestTerminalMenu3'))
check('sub-menu: not locked again', sm['DNAM'][1] & T.NOT_LOCKED)
n = dict(subs('FOLabTestDiary'))
check('note: text, its title, ended as the game\'s', n['TNAM'] == b'The boats are late again.\0' and n['FULL'] == b"Doctor's diary\0" and n['DATA'] == b'\x01')
for e in ('FOLabTestDoorREF', 'FOLabTestSafeREF'):
    r = g.forms.get(g.to_global(i, refs[e]))
    rd = dict(tes4.iter_subrecords(g.plugins[i].data(r[1])))
    check('%s: persistent, locked' % e, r[1].flags & tes4.PERSISTENT and rd['XLOC'][0] == 255)
s = health.check_file(g, out)['summary']
check('the plugin passes health with no errors', s.get('error', 0) == 0, s)
