"""The script compiler against the game: every script of every official file, compiled from the source it carries, must
give the bytes the game's own compiler gave. The few that don't are listed here with why: in those the source or what it
names changed after the bytes were made, so no compiler could give them. Then errors in bad source, and the writing."""
import collections
import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools'))
import gamedata  # noqa: E402
import playtest  # noqa: E402
import script_oracle  # noqa: E402
import scriptc  # noqa: E402

# (file, record type, form ID as the file writes it, which script in the record): why the game's bytes can't be had
SHIPPED_OUT_OF_STEP = {
    ('FalloutNV.esm', 'SCPT', 0x00127959, 0): "the other script's variable it reads is gone",
    ('FalloutNV.esm', 'SCPT', 0x0015F000, 0): 'its bytes are right but its header says not compiled',
    ('FalloutNV.esm', 'INFO', 0x0015AD0D, 1): 'source names a reference no longer in the file (no bytes either)',
    ('FalloutNV.esm', 'INFO', 0x000F246D, 1): 'bytes without any source',
    ('DeadMoney.esm', 'SCPT', 0x0100636B, 0): 'source names a package no longer in the file',
    ('DeadMoney.esm', 'QUST', 0x01013AA5, 3): 'source names a reference no longer in the file',
    ('OldWorldBlues.esm', 'SCPT', 0x0100D592, 0): 'source names a message no longer in the file',
    ('OldWorldBlues.esm', 'SCPT', 0x010154E8, 0): 'made when GetInCharGen had another number',
    ('LonesomeRoad.esm', 'SCPT', 0x0100AC93, 0): "the other script's variable has another number now",
    ('HonestHearts.esm', 'SCPT', 0x0100B667, 0): 'source names a reference no longer in the file',
    ('HonestHearts.esm', 'SCPT', 0x0100F8EF, 0): 'a package took over the editor ID of the one it used',
}
# A quest's variables that became floats after these lines were compiled against them as shorts
for formid in (0x0101136F, 0x01011369, 0x01010D0B, 0x01010D0C, 0x01010D0D, 0x01010D0E, 0x01010D0F, 0x01010D10):
    SHIPPED_OUT_OF_STEP[('DeadMoney.esm', 'INFO', formid, 0)] = "the quest's variable changed type"


def check(ok, what):
    print(('PASS ' if ok else 'FAIL ') + what)


gd = gamedata.GameData()
totals = collections.Counter()
wrong = {}
for pi, p in enumerate(gd.plugins):
    forms = scriptc.GameForms(gd, script_oracle.visible_plugins(gd, pi))
    for u in script_oracle.units(pi, p):
        cat, detail = script_oracle.compare(gd, pi, u, forms)
        if cat == 'empty':
            continue
        same = cat.startswith('match')
        totals[(u.tag, same)] += 1
        if not same:
            wrong[(u.plugin, u.tag, u.formid, u.part)] = cat + ': ' + detail
for tag in ('SCPT', 'INFO', 'QUST'):
    good, bad = totals[(tag, True)], totals[(tag, False)]
    check(good + bad > 1000 and good / (good + bad) > 0.99,
          '%s: %d of %d the same, byte for byte' % (tag, good, good + bad))
unexpected = {k: v for k, v in wrong.items() if k not in SHIPPED_OUT_OF_STEP}
for k, v in sorted(unexpected.items())[:20]:
    print('      %s %s %08X part %d: %s' % (k + (v[:300],)))
check(not unexpected, 'nothing differs beyond the %d known out of step in the shipped files (%d new)' % (
    len(SHIPPED_OUT_OF_STEP), len(unexpected)))
fixed = [k for k in SHIPPED_OUT_OF_STEP if k not in wrong]
check(not fixed, 'each of those still differs (else take it off the list): %s' % (fixed or 'yes'))


class Forms:
    """The interface a mod's own forms can come through: no game files in it."""

    def __init__(self, known):
        self.known = {k.lower(): scriptc.Form(self, fid, tag, True) for k, (fid, tag) in known.items()}
        self.vars = {}

    def find(self, name):
        return self.known.get(name.lower())

    find_edid = find

    def script_vars(self, form):
        return self.vars.get(form.fid)

    def message_text(self, form):
        return b'Value: %g, %%'

    def is_interior(self, form):
        return True

    def is_map_marker(self, form):
        return True


# Play here's script: the bytes FOLab already writes by hand, checked in test_play_here against the game's
SMALL = Forms({'player': (0x14, 'ACHR'), 'FOLabTestMarker': (0x800, 'REFR'), 'Stimpak': (0x15169, 'ALCH')})
msg = b'FOLab: Play here (Goodsprings)'
text = playtest.source(msg.decode(), True, [('Stimpak', 3)])
got = scriptc.compile_script(text, SMALL, scriptc.SCRIPT_QUEST)
check(got.data == playtest.compiled_script(msg, True, [(3, 3)]), "the same bytes as playtest's hand-compiled script")
check([r[1].fid for r in got.refs] == [0x14, 0x800, 0x15169],
      'its references in the same order: %r' % [r[0] for r in got.refs])
check(got.vars == [(1, 'done', True)] and got.name == 'FOLabTestScript', 'its variable and name')
check(got.schr() == struct.pack('<IIIIHH', 0, 3, len(got.data), 1, 1, 1), 'its header')
tags = [t for t, _b in got.subrecords()]
check(tags == ['SCHR', 'SCDA', 'SCTX', 'SLSD', 'SCVR', 'SCRO', 'SCRO', 'SCRO'],
      "subrecords in the game's order: %s" % tags)
ids = [struct.unpack('<I', b)[0] for t, b in got.subrecords(lambda fid: fid | 0x01000000) if t == 'SCRO']
check(ids[2] == 0x01015169, 'form IDs go through the numbering it is given')

# Variables keep their numbers when a script is compiled again; a new one takes the next free; float and int tags
src = 'scn A\nshort two\nfloat three\nref four\nbegin GameMode\nset three to two + 1\nend'
again = scriptc.compile_script(src, SMALL, old_vars=[(2, 'two', True), (9, 'gone', True)], old_count=9)
check([v[0] for v in again.vars] == [2, 10, 11], 'variables keep their numbers: %r' % again.vars)
check(b'f\x0a\x00' in again.data and b's\x02\x00' in again.data, 'set and read by number, f for a float, s for an int')
check(again.refs[0][2] == 11 and [t for t, _b in again.subrecords() if t.startswith('SCR')].count('SCRV') == 1,
      'a ref variable takes a place in the reference list (SCRV)')

# A result script: lines with no scn or block
res = scriptc.compile_result('player.AddItem Stimpak 1\r\n', SMALL)
check(res.data == struct.pack('<HHHHH', 0x1C, 1, 0x1002, 10, 2) + b'r\x02\x00n' + struct.pack('<i', 1),
      'a result script is just its lines')
check(scriptc.compile_result('; only a comment\r\n', SMALL).data == b'', 'a result script of comments is nothing')

# Expressions: the game's priorities, in postfix with a space before each token
def expr(e):
    body = scriptc.compile_script('scn A\nshort x\nbegin GameMode\nset x to %s\nend' % e, SMALL).data
    start = body.index(b'\x15\x00') + 9
    return body[start:body.index(b'\x11\x00\x00\x00', start)]


check(expr('1 + 2 * 3') == b' 1 2 3 * +', 'multiplying before adding')
check(expr('(1 + 2) * 3') == b' 1 2 + 3 *', 'brackets')
check(expr('-x') == b' s\x01\x00 ~', 'unary minus is ~')
check(expr('1 || 2 && 3') == b' 1 2 || 3 &&', "|| binds tighter than && in this language")
check(expr('Stimpak') == b' Z\x01\x00', 'a form as a value')
check(expr('player.GetAV Health') == b' r\x01\x00X\x0e\x10\x04\x00\x01\x00\x10\x00', 'a function with a reference and an actor value')

# The message commands count the %s in the text, and fill them
msgs = Forms({'player': (0x14, 'ACHR'), 'Note': (0x900, 'MESG')})
m = scriptc.compile_script('scn A\nfloat v\nbegin GameMode\nShowMessage Note v\nend', msgs).data
check(struct.pack('<H', 1) + b'r\x01\x00' + struct.pack('<H', 1) + b'f\x01\x00' + bytes(4) in m,
      'ShowMessage: one value for its one %g (%% is a percent sign), and a duration of 0')


# Bad source: which line, what was expected
def fails(src, line, words, **kw):
    try:
        scriptc.compile_script(src, SMALL, **kw)
    except scriptc.CompileError as e:
        check(e.line == line and words.lower() in e.message.lower(), 'error on line %d: %s' % (e.line, e.message))
        return
    check(False, 'no error for %r' % src)


OK = 'scn A\nshort x\nbegin GameMode\n%s\nend'
fails('begin GameMode\nend', 1, 'scn')
fails('', 1, 'scn')
fails(OK % 'blah 1', 4, 'Unknown command "blah"')
fails(OK % 'set x 1', 4, 'to')
fails(OK % 'set y to 1', 4, 'Unknown variable "y"')
fails(OK % 'set x to', 4, 'value')
fails(OK % 'set x to (1 + 2', 4, 'Brackets')
fails(OK % 'set x to nothing', 4, 'Unknown word "nothing"')
fails(OK % 'if x', 4, 'no endif')
fails(OK % 'if', 4, 'condition')
fails(OK % 'if x = 1\nendif', 4, 'operator')
fails(OK % 'player.AddItem', 4, 'Missing parameter')
fails(OK % 'player.AddItem Stimpak 1 0 7', 4, 'should end')
fails(OK % 'player.AddItem FOLabTestMarker 1', 4, 'valid inventory')
fails(OK % 'player.AddItem Nothing 1', 4, 'not found')
fails(OK % 'player.AddItem Stimpak many', 4, 'Unknown variable "many"')
fails(OK % 'Nobody.Disable', 4, 'Unknown name "Nobody"')
fails(OK % 'ShowWarning "oops', 4, 'quote')
fails(OK % 'tgm', 4, 'console')
fails(OK % 'Disable', 4, 'needs a reference', script_type=scriptc.SCRIPT_QUEST)
fails(OK % 'set Nobody.x to 1', 4, 'Unknown variable')
fails('scn A\nbegin NotABlock\nend', 2, 'block type')
fails('scn A\nbegin GameMode\nbegin GameMode\nend\nend', 3, 'begin inside a begin')
fails('scn A\nbegin GameMode', 2, 'no end')
fails('scn A\nend', 2, 'end without a begin')
fails('scn A\nset x to 1', 2, 'inside a begin')
fails('scn A\nshort Stimpak\nbegin GameMode\nend', 2, "can't be a variable's name")
long_line = 'scn A\n; a comment\n' + 'x' * 600
fails(long_line, 3, 'at most')
marker = Forms({'Temp': (0x801, 'REFR')})
marker.known['temp'].persistent = False
try:
    scriptc.compile_script('scn A\nbegin GameMode\nTemp.Disable\nend', marker)
    check(False, 'a non-persistent reference is refused')
except scriptc.CompileError as e:
    check('persistent' in e.message and e.line == 3, 'error on line %d: %s' % (e.line, e.message))
