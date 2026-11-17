"""The commands xNVSE and its plugins add (app/extfuncs.json, read from the user's files by tools/gen_extfuncs.py): the
compiler knows their names and numbers and writes the plain ones exactly as a real mod's compiled scripts have them
(the bytes below are from JSawyer Ultimate's own scripts). The ones that take xNVSE's own expressions are refused with
a line that says why, not as unknown words."""
import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import gamedata  # noqa: E402
import scriptc  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


t = scriptc.tables()
gd = gamedata.GameData()
forms = scriptc.GameForms(gd, list(range(len(gd.plugins))))

# ---------- the table ----------
want = {'GetNVSEVersion': 0x1400, 'SetWeight': 0x1407, 'SetHealth': 0x1408, 'ListAddForm': 0x1442, 'PrintToConsole': 0x14A0, 'printc': 0x14A0,
        'SetArmorAR': 0x14B4, 'Let': 0x1539, 'ForEach': 0x153D, 'ar_Append': 0x1566, 'sv_Replace': 0x1575, 'SetEquipmentBipedMask': 0x15C6,
        'FileExists': 0x2201, 'SetBaseKarma': 0x2320, 'SetDetonationTimer': 0x2773}
got = {n: t.names.get(n.lower()) for n in want}
check('extender commands have the numbers real compiled scripts use', got == want, {n: hex(v or 0) for n, v in got.items() if v != want[n]})
check('the game\'s own commands keep theirs', t.names['additem'] == 4098 and t.names['getdistance'] == 4097)
ext = [e for e in t.by_code.values() if e.get('from')]
check('over 1,500 of them, from xNVSE and JIP LN', len(ext) > 1500 and {e['from'] for e in ext} >= {'xNVSE', 'jip_nvse'}, len(ext))
check('none takes a number the game uses', all(e['code'] >= 0x1400 for e in ext))


def body(lines, kind=scriptc.SCRIPT_OBJECT):
    src = 'scn FOLabExtTest\nref rForm\nshort n\nbegin GameMode\n%s\nend\n' % '\n'.join('\t' + x for x in lines)
    return scriptc.compile_script(src.replace('\n', '\r\n').encode('cp1252'), forms, kind).data


def statement(line):
    """The compiled bytes of one line: its opcode and what follows it."""
    b = body([line])
    at = b.index(struct.pack('<H', 0x10)) + 4 + struct.unpack_from('<H', b, b.index(struct.pack('<H', 0x10)) + 2)[0]
    op, ln = struct.unpack_from('<HH', b, at)
    return op, b[at + 4:at + 4 + ln].hex()


# ---------- plain commands, as a real mod has them compiled ----------
real = [('SetWeight 6, rForm', 0x1407, '02007a0000000000001840720100'), ('SetHealth 125, rForm', 0x1408, '02006e7d000000720100'),
        ('SetArmorAR 1000, rForm', 0x14B4, '02006ee8030000720100'), ('SetDetonationTimer 0', 0x2773, '01007a0000000000000000')]
for line, op, data in real:
    got = statement(line)
    check('%s compiles to the real mod\'s bytes' % line.split()[0], got == (op, data), '%04X %s' % got)
op, data = statement('PrintC "Form %i is here.", rForm')
check('PrintC: its words and what fills them', op == 0x14A0 and bytes.fromhex(data)[4:4 + 16] == b'Form %i is here.' and data.endswith('660100'), data)
b = body(['if IsKeyPressed 42', '\tset n to 1', 'endif'])
check('an extender command inside a condition', struct.pack('<H', 0x1453) in b)
b = body(['if rForm.GetNVSEVersion > 5', '\tset n to GetNVSEVersion', 'endif'])
check('and as a value', b.count(struct.pack('<H', 0x1400)) == 2)

# ---------- xNVSE's own expressions (scriptx.py), as the same mod has them compiled ----------
SRC = '''scn FOLabExprTest
ref rForm
short iNum
float fMult
array_var aForms
string_var sName
short iPos
begin GameMode
%s
end
'''


def xbody(lines):
    return scriptc.compile_script((SRC % '\n'.join(lines)).replace('\n', '\r\n').encode('cp1252'), forms, scriptc.SCRIPT_OBJECT)


def xstatement(line, nth=0):
    b = xbody([line] if isinstance(line, str) else line).data
    at = b.index(struct.pack('<H', 0x10))
    at += 4 + struct.unpack_from('<H', b, at + 2)[0]
    for _ in range(nth):
        at += 4 + struct.unpack_from('<H', b, at + 2)[0]
    op, ln = struct.unpack_from('<HH', b, at)
    return op, b[at + 4:at + 4 + ln].hex()


# (variables here: rForm 1, iNum 2, fMult 3, aForms 4, sName 5, iPos 6; the mod's lines with its numbers swapped for these)
real = [('let iNum := 1', '010b00560100000200420100'), ('let iNum -= 1', '010b00560100000200420120'), ('let iNum *= 100', '010b0056010000020042641d'),
        ('let fMult := 0.5', '0112005600000003005a000000000000e03f00'), ('let iNum := fMult', '010f00560100000200560000000300' + '00'),
        ('let rForm := aForms[iPos]', '0116005604000001005603000004005601000006001800'),
        ('let iNum := *aForms', '0110005601000002005603000004002200'),
        ('let sName := "Russel.esp"', '011600560200000500530a0052757373656c2e65737000'),
        ('let rForm := aForms["value"]', '01180056040000010056030000040053050076616c75651800'),
        ('sv_Destruct sName', '010800560200000500'), ('ar_Append aForms, rForm', '0208005603000004000800560400000100'),
        ('SetFunctionValue 0', '0104004200'), ('SetFunctionValue rForm', '010800560400000100')]
for line, data in real:
    got = xstatement(line)
    check('%s' % line, got[1] == data, got[1])
op, data = xstatement('iNum = 5')
check('a bare assignment is a let', (op, data) == (0x1539, '010b00560100000200420500'), '%04X %s' % (op, data))
op, data = xstatement('let iNum := 0.5 + (GetArmorDT rForm) * fMult')
check('a command inside an expression, with the game\'s own way of writing its parameters',
      data == '012600560100000200' + '5a000000000000e03f' + '580000b31407000100720100' + '560000000300' + '100e00', data)
r = xbody(['while (iPos -= 1) > -1', '\tlet iNum += 1', 'loop'])
b = r.data
at = b.index(struct.pack('<H', 0x153B))
ln = struct.unpack_from('<H', b, at + 2)[0]
end = struct.unpack_from('<I', b, at + 4)[0]
check('while keeps where its loop line ends, then its condition', b[at + 8:at + 4 + ln].hex() == '010f0056010000060042012042011406'
      and b[end - 4:end] == struct.pack('<HH', 0x153C, 0), (end, b[at + 8:at + 4 + ln].hex()))
op, data = xstatement(['foreach (aForms <- GetListForms rForm)', 'loop'])
check('foreach: what it walks, and into what', op == 0x153D and data[8:] == '011500560300000400580000db15070001007201001a', data)
r = xbody(['if eval (iNum > 0)', '\tlet iNum := 0', 'endif'])
check('if eval: xNVSE\'s expression inside the game\'s own if', bytes.fromhex('20583a150c00010b00560100000200420006') in r.data)
check('string and array variables are declared as the mod\'s are', [(n, f) for _i, n, f in r.vars] ==
      [('rForm', False), ('iNum', True), ('fMult', False), ('aForms', False), ('sName', True), ('iPos', True)], r.vars)
fn = '''scn FOLabFnTest
ref rA
ref rB
short n
begin Function {rA, rB}
	let n := Call FOLabFnTest, rA, "x", 24
	SetFunctionValue n
end
'''
try:
    scriptc.compile_script(fn.replace('\n', '\r\n').encode(), forms, scriptc.SCRIPT_OBJECT)
    check('a script can\'t call itself by a name nothing has yet', False)
except scriptc.CompileError as e:
    check('calling a function nobody has made says so', 'FOLabFnTest' in e.message, e.message[:60])
fn = fn.replace('Call FOLabFnTest, rA', 'Call rB, rA')
b = scriptc.compile_script(fn.replace('\n', '\r\n').encode(), forms, scriptc.SCRIPT_OBJECT).data
check('begin Function keeps its parameters: which variables, and their kinds', bytes.fromhex('0d00') in b[:12] and b[14:23].hex() == '0102' + '010004' + '020004' + '00', b[:26].hex())
check('call: the function, then what it is given', bytes.fromhex('5800004515') in b and bytes.fromhex('01' + '0800560400000200' + '03' + '0800560400000100' + '0600530100' + '78' + '04004218') in b, b.hex())

# ---------- what FOLab can't write yet says so ----------
for line in ('CallAfter 0 ({} => PlayerREF.RemoveItem Caps001, 1, 1)', 'SetEventHandler "OnAdd" (begin Function {ref a}'):
    try:
        xbody([line])
        check('a function inside a line is refused', False)
    except scriptc.CompileError as e:
        check('a function inside a line is refused, saying why', 'inside a line' in e.message and 'xNVSE' in e.message)
try:
    body(['NoSuchCommandAtAll 1'])
    check('a word nobody knows is still unknown', False)
except scriptc.CompileError as e:
    check('a word nobody knows is still unknown', 'Unknown command' in e.message)

# ---------- names ----------
src = 'scn FOLabNames\r\nshort turn\r\nfloat label\r\nshort floor\r\nbegin GameMode\r\n\tset turn to label + floor\r\n\tlet floor := turn\r\nend\r\n'
r = scriptc.compile_script(src.encode(), forms, scriptc.SCRIPT_OBJECT)
check('a variable may share its name with an extender\'s command, and is the variable', [n for _i, n, _f in r.vars] == ['turn', 'label', 'floor']
      and bytes.fromhex('010f00560100000300560100000100' + '00') in r.data, r.data.hex())
try:
    scriptc.compile_script(b'scn FOLabNames2\r\nshort GetDistance\r\nbegin GameMode\r\nend\r\n', forms, scriptc.SCRIPT_OBJECT)
    check('but not with one of the game\'s own', False)
except scriptc.CompileError as e:
    check('but not with one of the game\'s own', 'already has it' in e.message)
