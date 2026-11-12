"""The script compiler: New Vegas script source (the GECK's language) to the game's bytecode.

    r = compile_script(source_text, GameForms(gd))
    r.data                the bytecode (SCDA)
    r.subrecords(...)     SCHR, SCDA, SCTX, SLSD + SCVR for each variable, SCRV / SCRO for each reference

FalloutNV.esm is the test: its scripts carry both their source and the bytes the game's own compiler gave them, and
this compiler gives the same bytes (tests/test_scriptc.py, and tools/script_oracle.py for the whole game).

How the bytes come out, in the game's way, because the bytes depend on it:

- Two passes. The first reads every line and resolves only its first word, so the reference in front of a command
  (`player.AddItem`) takes its place in the reference list before anything else in the script does. The second
  compiles line by line: a `ref` declaration adds that variable to the list, everything else as it's met.
- A line is [0x1C, ref number if it has a reference], its code, the size of what follows, then what follows. Word by
  word, parameters are short tagged items: r = reference number, s/f = a short / float variable, G = a global, n = a
  32-bit integer, z = a double, and a few parameters take a bare 16-bit number or a length and some text.
- Expressions are kept as text, in postfix, with a space before every token: numbers stay as their digits, operators as
  their characters; a variable or a function call inside is the same tagged bytes. So `x + 1 > 2` becomes
  ` s\\x01\\x00 1 + 2 >`. Operators have the game's priorities (&& binds looser than ||; unary minus is written ~).
- Jumps count lines, not bytes: `if` stores how many compiled lines to skip when false. Declarations aren't lines.

A script's variables keep their numbers when it is compiled again (old_vars), as they do in the game, so saves and
other scripts that use them stay right; a variable that went away leaves its number unused.

Forms are found through a small interface (see GameForms), so a mod's own records can be added beside the game's."""
import json
import os
import struct

import scriptx
import tes4

ENC = 'cp1252'
MAX_LINE = 0x200
MAX_SIZE = 0x4000
MAX_NESTING = 10

# The commands with a line of their own
C_BEGIN, C_END, C_SHORT, C_LONG, C_FLOAT, C_SET, C_IF, C_ELSE, C_ELSEIF, C_ENDIF = 0x10, 0x11, 0x12, 0x13, 0x14, 0x15, \
    0x16, 0x17, 0x18, 0x19
C_REFERENCE_ON, C_SCRIPTNAME, C_RETURN, C_REF = 0x1C, 0x1D, 0x1E, 0x1F
C_STRING_VAR, C_ARRAY_VAR = scriptx.C_STRING_VAR, scriptx.C_ARRAY_VAR     # (xNVSE's: no line of the game's has these)
DECLARATIONS = (C_SHORT, C_LONG, C_FLOAT, C_REF, C_STRING_VAR, C_ARRAY_VAR)
VAR_KIND = {C_SHORT: 'i', C_LONG: 'i', C_FLOAT: 'f', C_REF: 'r', C_STRING_VAR: 's', C_ARRAY_VAR: 'a'}
# The three that take a message rather than plain parameters: (has buttons, text written in the line)
MESSAGE_COMMANDS = {0x1059: (False, False), 0x114D: (True, False), 0x11B9: (False, True)}

SCRIPT_OBJECT, SCRIPT_QUEST, SCRIPT_EFFECT = 0, 1, 0x100

REF_TAGS = frozenset('REFR ACHR ACRE PGRE PMIS PBEA PFLA PCBE'.split())
ITEM_TAGS = frozenset('ARMO AMMO MISC WEAP BOOK KEYM ALCH NOTE IMOD CMNY CCRD CHIP LIGH CDCK LVLI ARMA'.split())
BOUND_TAGS = ITEM_TAGS | frozenset('ACTI TACT TERM CONT DOOR STAT SCOL MSTT FURN NPC_ CREA LVLC LVLN GRAS TREE SOUN '
                                   'ASPC ADDN IDLM CAMS PROJ EXPL'.split())
# Parameter type -> (what it's called in errors, the record types it can name). No types means any form.
PARAM_FORMS = {
    3: ('inventory object', ITEM_TAGS), 50: ('inventory object', ITEM_TAGS | {'FLST'}),
    53: ('object', BOUND_TAGS | REF_TAGS | {'FLST'}), 4: ('object reference', REF_TAGS),
    6: ('actor', frozenset('ACHR ACRE'.split())), 24: ('map marker', REF_TAGS), 26: ('container reference', REF_TAGS),
    7: ('spell item', frozenset('SPEL BOOK'.split())), 9: ('interior cell', {'CELL'}), 47: ('encounter zone', {'ECZN'}),
    48: ('idle form', {'IDLE'}), 37: ('form list', {'FLST'}), 38: ('menu icon', {'MICN'}), 39: ('perk', {'PERK'}),
    40: ('note', {'NOTE'}), 27: ('worldspace', {'WRLD'}), 11: ('magic item', frozenset('SPEL ALCH ENCH INGR'.split())),
    31: ('effect setting', {'MGEF'}), 12: ('sound', {'SOUN'}), 54: ('music type', {'MUSC'}), 13: ('topic', {'DIAL'}),
    14: ('quest', {'QUST'}), 15: ('race', {'RACE'}), 16: ('class', {'CLAS'}), 17: ('faction', {'FACT'}),
    62: ('reputation', {'REPU'}), 65: ('challenge', {'CHAL'}), 63: ('casino', {'CSNO'}), 64: ('casino chip', {'CHIP'}),
    66: ('caravan money', {'CMNY'}), 67: ('caravan card', {'CCRD'}), 68: ('caravan deck', {'CDCK'}),
    69: ('region', {'REGN'}), 19: ('global', {'GLOB'}), 20: ('furniture or form list', frozenset('FURN FLST'.split())),
    21: ('object', BOUND_TAGS), 25: ('actor base', frozenset('NPC_ CREA'.split())), 29: ('package', {'PACK'}),
    30: ('combat style', {'CSTY'}), 33: ('weather', {'WTHR'}), 42: ('imagespace modifier', {'IMAD'}),
    43: ('imagespace', {'IMGS'}), 34: ('NPC', {'NPC_'}), 35: ('owner', frozenset('NPC_ FACT'.split())),
    36: ('effect shader', {'EFSH'}), 49: ('message', {'MESG'}), 56: ('NPC or leveled character',
                                                                   frozenset('NPC_ LVLN'.split())),
    57: ('creature or leveled creature', frozenset('CREA LVLC'.split())), 58: ('leveled character', {'LVLN'}),
    59: ('leveled creature', {'LVLC'}), 60: ('leveled item', {'LVLI'}), 61: ('form', None),
    46: ('voice type', {'VTYP'}),
}


class CompileError(Exception):
    """Bad source. line is the line of the source it's on (from 1), or 0 when it's the script as a whole."""

    def __init__(self, message, line=0, text=''):
        self.message, self.line, self.text = message, line, text
        Exception.__init__(self, 'line %d: %s' % (line, message) if line else message)


_tables = None


class _Tables:
    def __init__(self):
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scriptfuncs.json'), encoding='utf-8') as f:
            t = json.load(f)
        self.names = {}
        self.by_code = {}
        for name, short, code in t['keywords']:
            self.names.setdefault(name.lower(), code)
            if short:
                self.names.setdefault(short.lower(), code)
        for table in (t['script'], t['console']):
            for e in table:
                self.names.setdefault(e['name'].lower(), e['code'])
                if e['short']:
                    self.names.setdefault(e['short'].lower(), e['code'])
                self.by_code[e['code']] = e
        # what xNVSE and its plugins add (tools/gen_extfuncs.py reads them from the user's own files); the game's own names win
        try:
            with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'extfuncs.json'), encoding='utf-8') as f:
                ext = json.load(f)['commands']
        except (OSError, ValueError, KeyError):
            ext = []
        for e in ext:
            if e['code'] in self.by_code:
                continue
            self.names.setdefault(e['name'].lower(), e['code'])
            if e['short']:
                self.names.setdefault(e['short'].lower(), e['code'])
            self.by_code[e['code']] = e
        self.blocks = {}
        for e in t['blocks']:
            self.blocks.setdefault(e['name'].lower(), e)
            if e['short']:
                self.blocks.setdefault(e['short'].lower(), e)
        self.kinds = t['param_kinds']
        self.operators = t['operators']
        self.lists = {
            5: {n.lower(): i for i, n in enumerate(t['actor_values'])},
            51: {n.lower(): i for i, n in enumerate(t['alignments'])},
            55: {n.lower(): i for i, n in enumerate(t['crit_stages'])},
            52: {n.lower(): i for i, n in enumerate(t['equip_types'])},
            41: {n.lower(): i for i, n in enumerate(t['misc_stats']) if n},
            18: {n.lower(): i for i, n in enumerate(t['sexes'])},
            10: {n.lower(): i for i, n in reversed(list(enumerate(t['anim_groups'])))},
            32: {n.lower(): v for n, v in t['form_types'].items()},
        }


def tables():
    global _tables
    if _tables is None:
        _tables = _Tables()
    return _tables


def _isalpha(c):
    return 65 <= c <= 90 or 97 <= c <= 122


def _isdigit(c):
    return 48 <= c <= 57


def _isalnum(c):
    return _isalpha(c) or _isdigit(c)


def _is_int(raw):
    s = raw[1:] if raw[:1] == b'-' else raw
    return bool(s) and all(_isdigit(c) for c in s)


def _is_number(raw):
    s = raw[1:] if raw[:1] == b'-' else raw
    if not s or s == b'.' or s.count(b'.') > 1:
        return False
    return all(_isdigit(c) or c == 46 for c in s)


def _atol(raw):
    return max(-0x80000000, min(0x7FFFFFFF, int(raw.decode('ascii'))))


def _atof(raw):
    return float(raw.decode('ascii'))


class _Word:
    """A word of a line and what it turned out to be."""
    __slots__ = ('raw', 'ref', 'kind', 'code', 'var', 'form')

    def __init__(self):
        self.raw, self.ref, self.kind, self.code, self.var, self.form = b'', 0, '', 0, 0, None

    @property
    def text(self):
        return self.raw.decode(ENC, 'replace')

    @property
    def name(self):
        return self.text.lower()


class _Ref:
    """An entry of the script's reference list: a form, or (var set) one of its own ref variables."""
    __slots__ = ('name', 'text', 'form', 'var', 'line')

    def __init__(self, text, form=None, var=0, line=0):
        self.text, self.name, self.form, self.var, self.line = text, text.lower(), form, var, line


class _Line:
    __slots__ = ('number', 'text', 'code', 'ref', 'whole')

    def __init__(self, number, text):
        self.number, self.text, self.whole, self.code, self.ref = number, text, text, 0, 0


class Compiled:
    """vars: [(number, name, is it an integer)]; refs: [(name, Form or None, variable number or 0)], numbered from 1."""

    def __init__(self, name, data, script_type, var_count, variables, refs, source):
        self.name, self.data, self.script_type, self.var_count = name, data, script_type, var_count
        self.vars, self.refs, self.source = variables, refs, source

    def schr(self):
        return struct.pack('<IIIIHH', 0, len(self.refs), len(self.data), self.var_count, self.script_type, 1)

    def subrecords(self, form_id=lambda fid: fid):
        """[(tag, bytes)] in the game's order. form_id turns a global form ID into the plugin's own numbering."""
        out = [('SCHR', self.schr()), ('SCDA', self.data), ('SCTX', self.source)]
        for num, name, is_int in self.vars:
            out.append(('SLSD', struct.pack('<I12sB7s', num, b'\0' * 12, 1 if is_int else 0, b'\0' * 7)))
            out.append(('SCVR', name.encode(ENC, 'replace') + b'\0'))
        for _name, form, var in self.refs:
            if var:
                out.append(('SCRV', struct.pack('<I', var)))
            else:
                out.append(('SCRO', struct.pack('<I', form_id(form.fid))))
        return out


class _Compiler(scriptx.Expressions):
    def __init__(self, source, forms, script_type, old_vars, old_count, partial, strict):
        self.src = source
        self.forms, self.t = forms, tables()
        self.script_type, self.partial, self.strict = script_type, partial, strict
        self.old_vars = {n.lower(): (i, is_int) for i, n, is_int in old_vars}
        self.count = old_count or max([i for i, _n, _f in old_vars] or [0])
        self.quest = script_type == SCRIPT_QUEST
        self.vars = []          # [(number, name, is integer)], as declared
        self.var_names = {}     # lower name -> (number, is integer)
        self.refs = []
        self.out = bytearray()
        self.name = ''
        self.lines = []
        self.lineno = 0
        self.text = b''
        self.block_at = None
        self.x_init()

    def err(self, message):
        raise CompileError(message, self.lineno, self.text.decode(ENC, 'replace'))

    # -- reading lines ---------------------------------------------------------------------------------------------

    def read_lines(self):
        """Each line that means something: comments gone, leading junk and trailing blanks off. A line starts at its
        first letter, digit or quote mark; a ; ends it wherever it is, even inside quotes (as in the game)."""
        src, pos, n = self.src, 0, len(self.src)
        number, cur, started = 1, bytearray(), False
        while True:
            c = src[pos] if pos < n else 0
            pos += 1
            if c == 59:                                                         # ;
                while c and c != 10:
                    c = src[pos] if pos < n else 0
                    pos += 1
            if c in (13, 10, 0):
                if c == 13 and pos < n and src[pos] == 10:
                    pos += 1
                text = bytes(cur).rstrip(b' \t')
                if text:
                    self.lines.append(_Line(number, text))
                if not c:
                    return
                number += 1
                cur, started = bytearray(), False
                continue
            if len(cur) + 1 >= MAX_LINE:
                self.lineno, self.text = number, bytes(cur)
                self.err('A line can be at most %d characters long.' % MAX_LINE)
            if _isalnum(c) or c == 34:
                started = True
            if started:
                cur.append(c)

    def first_pass(self):
        for line in self.lines:
            self.lineno, self.text = line.number, line.whole
            if scriptx.inline_function(line.text):
                self.err(scriptx.LAMBDA % '(begin Function {...} ... end), or {...} => ...')
            w = _Word()
            cur = [0]
            if not self.word(w, line.text + b'\0', cur, True, True):
                self.err('This line makes no sense here: it needs to start with a command.')
            line.ref = w.ref
            if w.kind != 'X' and w.name in ('string_var', 'array_var') and not w.ref:
                line.code = C_STRING_VAR if w.name == 'string_var' else C_ARRAY_VAR
                line.text = line.text[cur[0]:]
                continue
            if w.kind != 'X' and 'let' in self.t.names and scriptx.assigns(line.text[cur[0]:]):
                line.code, line.ref = self.t.names['let'], 0         # (xNVSE: `x = 5` on its own is `let x := 5`)
                continue
            if w.kind != 'X':
                self.err('Unknown command "%s".' % w.text)
            if 0x100 <= w.code < 0x1CD:
                self.err('"%s" is a console command: it can\'t be used in a script.' % w.text)
            line.code = w.code
            line.text = line.text[cur[0]:]
            if w.code == C_SCRIPTNAME:
                nw, c2 = _Word(), [0]
                if not self.word(nw, line.text + b'\0', c2, False, False):
                    self.err('scn needs a name for the script.')
                self.name = nw.text
            if w.code in (C_IF, C_ELSEIF) and not line.text:
                self.err('%s needs a condition.' % ('if' if w.code == C_IF else 'elseif'))

    def check_blocks(self):
        inside, opened = False, 0
        for line in self.lines:
            self.lineno, self.text = line.number, line.whole
            if line.code in DECLARATIONS or line.code == C_SCRIPTNAME:
                continue
            if line.code == C_BEGIN:
                if inside:
                    self.err('A begin inside a begin: end the one on line %d first.' % opened)
                inside, opened = True, line.number
            elif line.code == C_END:
                if not inside:
                    self.err('An end without a begin.')
                inside = False
            elif not inside:
                self.err('This has to be inside a begin ... end block.')
        if inside:
            self.lineno = opened
            self.err('This begin has no end.')

    # -- words -----------------------------------------------------------------------------------------------------

    def word(self, w, text, cur, allow_ref, lenient):
        """Read the next word at cur[0] into w; return its length. allow_ref: it can be `something.word`, and what it
        is gets worked out. lenient: an unknown name in front of the dot is let through for now (it might be declared
        further down; a last check catches it if it never is)."""
        i = cur[0]
        while text[i] in (9, 32, 44):
            i += 1
        n = 0
        if text[i] == 34:
            rest = text[i:].split(b'\0')[0]
            count = rest.count(b'"')
            if count < 2 or count & 1:
                cur[0] = i
                self.err('Mismatched quote marks.')
            end = text.index(b'"', i + 1)
            w.raw = text[i + 1:end]
            n = len(w.raw)
            i = end + 1
            if text[i] == 46:
                self._ref_prefix(w, allow_ref, lenient)
                cur[0] = i + 1
                return self.word(w, text, cur, True, lenient)
        if n == 0:
            start = i
            while _isalnum(text[i]) or text[i] in (46, 45, 95):
                c = text[i]
                i += 1
                if c == 46 and _isalpha(text[start]):
                    w.raw = text[start:i - 1]
                    self._ref_prefix(w, allow_ref, lenient)
                    cur[0] = i
                    return self.word(w, text, cur, True, lenient)
            n = i - start
            if n:
                w.raw = text[start:i]
        cur[0] = i
        if allow_ref:
            if w.ref > 0:
                if not self.resolve(w) and not self.command(w):
                    self.err('Unknown variable or function "%s".' % w.text)
                entry = self.refs[w.ref - 1]
                is_ref = entry.form is not None and entry.form.tag in REF_TAGS
                is_quest = entry.form is not None and entry.form.tag == 'QUST'
                if entry.form is not None and not is_ref and not is_quest and not lenient:
                    self.err('"%s" can\'t go in front of a dot: only references and quests can.' % entry.text)
                if is_quest and w.kind == 'X':
                    self.err('Functions can\'t be called on quests.')
            if not w.kind and not self.resolve(w):
                self.command(w)
        return n

    def _ref_prefix(self, w, allow_ref, lenient):
        if not allow_ref:
            self.err('A reference (something with a dot) isn\'t allowed here.')
        if w.ref > 0:
            self.err('Only one reference can go in front of a word.')
        if not self.reference(w, False, lenient):
            self.err('Unknown object "%s".' % w.text)

    def resolve(self, w):
        """Is the word a variable (of the reference in front of it, or this script's), or a global?"""
        name = w.name
        if w.form is not None:
            vs = w.form.script_vars()
            if vs is None or name not in vs:
                w.var, w.kind = 0, ''
                return False
            w.var, is_int = vs[name]
            w.kind = 's' if is_int else 'f'
            return True
        if w.ref:
            w.var, w.kind = 0, ''
            return False
        w.var = 0
        found = self.var_names.get(name) or self.old_vars.get(name)
        if found:
            w.var = found[0]
            w.kind = 's' if found[1] else 'f'
            return True
        form = self.forms.find_edid(name)
        if form is not None and form.tag == 'GLOB' and self.reference(w, False, False):
            w.var, w.kind = 0, 'G'
            return True
        w.var, w.kind = 0, ''
        return False

    def command(self, w):
        code = self.t.names.get(w.name)
        if code is None:
            return False
        w.kind, w.code = 'X', code
        return True

    def reference(self, w, variable, lenient):
        """Find the word in the reference list, or add it. variable: it is one of this script's ref variables."""
        name = w.name
        for i, e in enumerate(self.refs):
            if e.name == name:
                w.ref, w.form = i + 1, e.form
                if variable:
                    e.var = w.var
                else:
                    w.var = e.var
                return True
        form = None
        if not variable:
            form = self.forms.find(name)
            if form is not None and self.strict and form.tag in REF_TAGS and not form.persistent:
                self.err('"%s" isn\'t a persistent reference, so a script can\'t use it. Tick Persistent on it.' %
                         w.text)
            if form is None and not lenient:
                return False
        e = _Ref(w.text, form, w.var if variable else 0, self.lineno)
        self.refs.append(e)
        w.form = form
        w.ref = len(self.refs)
        return True

    # -- parameters ------------------------------------------------------------------------------------------------

    def params(self, fn, text, whole_line):
        """fn's parameters from text: (bytes, how much of the text they took)."""
        if fn['code'] in MESSAGE_COMMANDS:
            return self.message_params(fn, text)
        return self.standard_params(fn['params'], text, whole_line)

    def standard_params(self, params, text, whole_line):
        buf = text + b'\0'
        cur = [0]
        out = bytearray(struct.pack('<H', len(params)))
        for i, (ptype, optional, pname) in enumerate(params):
            allow_ref, is_form = (1, 0) if ptype == 44 else self.t.kinds[ptype]      # (44: JIP's double, a number)
            at = cur[0]
            while buf[at] in (9, 32, 44):
                at += 1
            if buf[at] == 40:                                                    # ( an expression of xNVSE's, worked out as the line runs
                data, cur[0] = self.x_param(buf[:-1], at)
                out += data
                continue
            w = _Word()
            if buf[at] == 36 and ptype == 0:                                     # $ a string variable's words
                end = at + 1
                while _isalnum(buf[end]) or buf[end] == 95:
                    end += 1
                w.raw, cur[0] = buf[at:end], end
                out += struct.pack('<H', len(w.raw)) + w.raw
                continue
            n = self.word(w, buf, cur, bool(allow_ref), False)
            if not n:
                if not optional:
                    self.err('Missing parameter: %s.' % pname)
                out[:2] = struct.pack('<H', i)
                return bytes(out), cur[0]
            if not allow_ref and (w.ref > 0 or w.kind):
                self.err('%s can\'t be a variable.' % pname)
            if is_form:
                self.form_param(ptype, pname, w, out)
            else:
                self.value_param(ptype, pname, w, n, out)
        if whole_line and cur[0] < len(text):
            self.err('The line should end after its parameters, but there is more: "%s".' %
                     text[cur[0]:].decode(ENC, 'replace'))
        return bytes(out), cur[0]

    def form_param(self, ptype, pname, w, out):
        if not self.reference(w, False, False) or not w.ref:
            self.err('"%s" not found (for %s).' % (w.text, pname))
        spec = PARAM_FORMS.get(ptype)
        if spec is None:
            self.err('Parameters of type %d aren\'t supported yet (%s).' % (ptype, pname))
        what, tags = spec
        if not w.var:
            if w.form is None or (tags is not None and w.form.tag not in tags):
                self.err('"%s" isn\'t a valid %s (for %s).' % (w.text, what, pname))
            if ptype == 9 and not w.form.interior:
                self.err('"%s" isn\'t an interior cell (for %s).' % (w.text, pname))
            if ptype == 24 and not w.form.is_map_marker():
                self.err('"%s" isn\'t a map marker (for %s).' % (w.text, pname))
        out += b'r' + struct.pack('<H', w.ref)

    def value_param(self, ptype, pname, w, n, out):
        if ptype == 0:                                                           # text
            out += struct.pack('<H', n) + w.raw
        elif ptype in (1, 2, 23, 44):                                            # a number or a variable (44: JIP's double)
            if w.ref > 0:
                out += (b'G' if w.kind == 'G' else b'r') + struct.pack('<H', w.ref)
            if w.kind != 'G':
                if w.var > 0:
                    out += w.kind.encode('ascii') + struct.pack('<H', w.var)
                elif ptype in (2, 44):
                    if not _is_number(w.raw):
                        self.err('Unknown variable "%s" (for %s).' % (w.text, pname))
                    out += b'z' + struct.pack('<d', _atof(w.raw))
                else:
                    if not _is_int(w.raw):
                        self.err('Unknown variable "%s" (for %s).' % (w.text, pname))
                    out += b'n' + struct.pack('<i', _atol(w.raw))
        elif ptype == 8:                                                         # an axis
            c = w.raw[:1].upper()
            if c not in (b'X', b'Y', b'Z'):
                self.err('%s must be an axis: X, Y or Z.' % pname)
            out += c
        elif ptype == 28:                                                        # a crime type
            if not _is_int(w.raw) or not 0 <= _atol(w.raw) < 5:
                self.err('%s must be a crime type, a number from 0 to 4.' % pname)
            out += struct.pack('<H', _atol(w.raw))
        elif ptype in self.t.lists:                                              # a name from a list of the game's
            v = self.t.lists[ptype].get(w.name)
            if v is None:
                self.err('"%s" isn\'t a valid %s.' % (w.text, pname))
            out += struct.pack('<H', v)
        else:
            self.err('Parameters of type %d aren\'t supported yet (%s).' % (ptype, pname))

    def message_params(self, fn, text):
        """A message: the version (1), which message, how many values fill its %s and those values; then its duration,
        or for the one with buttons their texts."""
        buttons, literal = MESSAGE_COMMANDS[fn['code']]
        buf = text + b'\0'
        cur = [0]
        out = bytearray(struct.pack('<H', 1))
        w = _Word()
        n = self.word(w, buf, cur, False, False)
        pname = fn['params'][0][2]
        if literal:
            if not n:
                self.err('No message text.')
            out += struct.pack('<H', n) + w.raw
            body = w.raw
        else:
            if not n:
                self.err('Missing parameter: %s.' % pname)
            if not self.reference(w, False, False) or not w.ref:
                self.err('"%s" not found (for %s).' % (w.text, pname))
            if not w.var and (w.form is None or w.form.tag != 'MESG'):
                self.err('"%s" isn\'t a message.' % w.text)
            out += b'r' + struct.pack('<H', w.ref)
            body = w.form.message_text() if w.form is not None else b''
        count, i = 0, 0
        while i < len(body):
            if body[i] == 37:
                if body[i + 1:i + 2] == b'%':
                    i += 1
                else:
                    count += 1
            i += 1
        if count >= 10:
            self.err('A message can fill in at most %d values.' % 10)
        out += struct.pack('<H', count)
        for k in range(count):
            v = _Word()
            if not self.word(v, buf, cur, True, False):
                self.err('Too few values for this message: it wants %d, there are %d.' % (count, k))
            if not v.kind:
                self.err('Unknown variable "%s" in the message\'s values.' % v.text)
            if v.ref > 0:
                out += (b'G' if v.kind == 'G' else b'r') + struct.pack('<H', v.ref)
            if v.kind != 'G':
                if v.var <= 0:
                    self.err('"%s" can\'t be one of the message\'s values.' % v.text)
                out += v.kind.encode('ascii') + struct.pack('<H', v.var)
        if not literal:
            if buttons:
                labels = []
                while len(labels) < 10:
                    b = _Word()
                    if not self.word(b, buf, cur, False, False):
                        break
                    labels.append(b.raw)
                out += struct.pack('<H', len(labels))
                for b in labels:
                    out += struct.pack('<HH', 1, len(b)) + b
            else:
                d = _Word()
                duration = 0
                if self.word(d, buf, cur, False, False):
                    if not _is_int(d.raw):
                        self.err('A message\'s time must be a whole number.')
                    duration = _atol(d.raw)
                out += struct.pack('<i', duration)
        return bytes(out), cur[0]

    # -- expressions -----------------------------------------------------------------------------------------------

    def infix(self, text):
        """An expression with its words turned into their tagged bytes, the rest left as it is."""
        out = bytearray()
        buf = text + b'\0'
        i, n = 0, len(text)
        while i < n:
            c = text[i]
            if _isalpha(c) or c == 34:
                w = _Word()
                cur = [i]
                if not self.word(w, buf, cur, True, True):
                    self.err('Something is missing in this expression.')
                i = cur[0]
                if w.ref > 0:
                    out += (b'G' if w.kind == 'G' else b'r') + struct.pack('<H', w.ref)
                if w.var > 0:
                    out += w.kind.encode('ascii') + struct.pack('<H', w.var)
                elif w.kind == 'X':
                    out += b'X' + struct.pack('<H', w.code)
                    fn = self.t.by_code.get(w.code)
                    if fn is None:
                        self.err('"%s" can\'t be used in an expression.' % w.text)
                    if fn['ref'] and self.quest and not w.ref:
                        self.err('%s needs a reference in front of it in a quest script (like player.%s).' %
                                 (w.text, w.text))
                    if fn.get('expr'):
                        data, took = self.x_args(text[i:], fn['code'] == self.x_call)
                        out += struct.pack('<H', len(data)) + data
                        i += took
                    elif fn['params']:
                        data, took = self.params(fn, text[i:], False)
                        out += struct.pack('<H', len(data)) + data
                        i += took
                    else:
                        out += b'\0\0'
                elif w.kind != 'G':
                    if not w.ref and self.reference(w, False, False):
                        out += b'Z' + struct.pack('<H', w.ref)
                    else:
                        self.err('Unknown word "%s": not a variable, a function or anything with that name.' % w.text)
            if i < n:
                out.append(text[i])
            i += 1
        return bytes(out)

    def next_token(self, s, pos):
        """The next token of the expression: (its bytes, its operator number or 16 for an operand, where it ended)."""
        ops = self.t.operators
        while s[pos] != 0 and (s[pos] < 33 or s[pos] > 127):
            pos += 1
        out = bytearray()
        beginning = True
        kind = 16
        while s[pos] != 0:
            c = s[pos]
            word = struct.unpack_from('<h', s, pos + 1)[0] if pos + 3 <= len(s) else 0
            # X: a function call, whole (the game's own numbers, or one xNVSE or a plugin added)
            if c == 88 and (0x1000 <= word < 0x1280 or (word >= 0x1400 and word in self.t.by_code)):
                size = struct.unpack_from('<h', s, pos + 3)[0] + 5
                out += s[pos:pos + size]
                pos += size
                break
            if c in b'slfGZ':
                out += s[pos:pos + 3]
                pos += 3
                break
            if c == 114:                                                         # r: and what it's in front of
                out += s[pos:pos + 3]
                pos += 3
                beginning = False
                continue
            if c == 110:
                out += s[pos:pos + 5]
                pos += 5
                break
            if c == 122:
                out += s[pos:pos + 9]
                pos += 9
                break
            if c == 34:
                end = s.find(b'"', pos + 1)
                end = end + 1 if end >= 0 else s.index(b'\0', pos)
                out += s[pos:end]
                pos = end
                break
            if c in (32, 9):
                break
            hit, partial = None, False
            for h, (_prio, text) in enumerate(ops):
                t = text.encode('ascii')
                p = 0
                while p < len(t) and s[pos + p] == t[p]:
                    p += 1
                if p:
                    partial = True
                if p == len(t):
                    hit = h
                    break
            if hit is not None:
                if beginning:
                    kind = hit
                    t = ops[hit][1].encode('ascii')
                    out += t
                    pos += len(t)
                break
            if partial:
                self.err('An operator isn\'t right here (= must be ==, & must be &&, | must be ||, ! must be !=).')
            out.append(c)
            beginning = False
            pos += 1
        return bytes(out), kind, pos

    def postfix(self, infix):
        """The game's shunting-yard: operators wait on a stack, operands go straight out."""
        s = b'(' + infix + b')\0\0\0\0\0\0\0\0'
        ops = self.t.operators
        stack = []
        out = bytearray()
        pos, had_operand = 0, False
        while True:
            token, kind, pos = self.next_token(s, pos)
            if not token:
                break
            if kind < 16:
                if kind == 0:
                    if len(stack) >= 64:
                        self.err('Too many nested brackets in this expression.')
                    stack.append(0)
                elif kind == 1:
                    if not stack:
                        self.err('A ) here has no ( to match it.')
                    while True:
                        top = stack.pop()
                        if top == 0:
                            break
                        out += b' ' + ops[top][1].encode('ascii')
                        if not stack:
                            self.err('A ) here has no ( to match it.')
                else:
                    if kind == 10 and not had_operand:
                        kind = 15
                    while stack:
                        top = stack.pop()
                        if ops[top][0] >= ops[kind][0]:
                            out += b' ' + ops[top][1].encode('ascii')
                        else:
                            stack.append(top)
                            break
                    if len(stack) >= 64:
                        self.err('This expression is too long.')
                    stack.append(kind)
            else:
                out += b' ' + token
            if kind == 16:
                had_operand = True
            elif 1 < kind < 16:
                had_operand = False
        if stack:
            self.err('Brackets don\'t match in this expression.')
        return bytes(out)

    # -- lines -----------------------------------------------------------------------------------------------------

    def jump_size(self, at):
        """How many compiled lines the condition on line at skips: up to the else, elseif or endif that answers it."""
        count = depth = 0
        for line in self.lines[at + 1:]:
            c = line.code
            if c in (C_SHORT, C_LONG, C_FLOAT, C_STRING_VAR, C_ARRAY_VAR):
                continue
            if c == C_IF:
                count += 1
                depth += 1
                if depth >= MAX_NESTING:
                    self.err('ifs can nest at most %d deep.' % MAX_NESTING)
            elif c in (C_ELSE, C_ELSEIF):
                if depth == 0:
                    return count
                count += 1
            elif c == C_ENDIF:
                if depth == 0:
                    return count
                depth -= 1
                count += 1
            else:
                count += 1
        self.err('This has no endif.')

    def compile_line(self, at, line):
        c = line.code
        body = bytearray()
        text = line.text
        if c == C_SCRIPTNAME or c in (C_RETURN, C_ENDIF, C_REFERENCE_ON):
            pass
        elif c == C_BEGIN:
            self.begin_line(line, body)
        elif c == C_END:
            if self.block_at is None:
                self.err('An end without a begin.')
            start = struct.unpack_from('<I', self.out, self.block_at)[0]
            struct.pack_into('<I', self.out, self.block_at, len(self.out) - start)
            self.block_at = None
        elif c in DECLARATIONS:
            self.declare(line)
            return
        elif c == C_SET:
            self.set_line(line, body)
        elif c in (C_IF, C_ELSEIF):
            if text.count(b'(') != text.count(b')'):
                self.err('Brackets don\'t match.')
            expr = self.expression(text.lstrip(b' \t,'))
            body += struct.pack('<HH', self.jump_size(at), len(expr)) + expr
        elif c == C_ELSE:
            body += struct.pack('<H', self.jump_size(at))
        else:
            fn = self.t.by_code.get(c)
            if fn is None:
                self.err('This can\'t be used as a line of its own.')
            if fn['ref'] and self.quest and not line.ref:
                self.err('This function needs a reference in front of it in a quest script (like player.Something).')
            if fn['ref'] and line.ref:
                e = self.refs[line.ref - 1]
                if e.form is not None and e.form.tag not in REF_TAGS and not e.var:
                    self.err('"%s" can\'t go in front of this function: it must be a reference or a ref variable.' %
                             e.text)
            if fn.get('expr'):
                self.x_line(fn, text, body)
            elif fn['params']:
                data, _took = self.params(fn, text, True)
                body += data
        if len(self.out) + len(body) + 10 >= MAX_SIZE:
            self.err('The script is too big (the game allows %d bytes of compiled code).' % MAX_SIZE)
        if line.ref:
            self.out += struct.pack('<HH', C_REFERENCE_ON, line.ref)
        self.out += struct.pack('<HH', c, len(body)) + body
        self.x_after(c, len(self.out) - len(body))

    def begin_line(self, line, body):
        w = _Word()
        cur = [0]
        if not self.word(w, line.text + b'\0', cur, False, False):
            self.err('begin needs a block type (GameMode, OnActivate...).')
        block = self.t.blocks.get(w.name)
        if block is None and w.name == 'function':                               # (xNVSE's: a script others call)
            body += struct.pack('<H', scriptx.BLOCK_FUNCTION)
            self.block_at = len(self.out) + 4 + len(body)
            body += bytes(4)
            self.x_function(line.text[cur[0]:], body)
            struct.pack_into('<I', body, 2, len(self.out) + len(body))
            return
        if block is None:
            self.err('"%s" isn\'t a block type.' % w.text)
        if block['ref'] and self.quest:
            self.err('A quest script can\'t have a %s block.' % block['name'])
        body += struct.pack('<H', block['code'])
        # The block's size sits after the code; for now it holds where the block's lines start, and end works it out.
        # (From four bytes before they really start, so a block's size takes in its end line too.)
        self.block_at = len(self.out) + 4 + len(body)
        body += bytes(4)
        if block['params']:
            data, _took = self.standard_params(block['params'], line.text[cur[0]:], False)
            body += data
        struct.pack_into('<I', body, 2, len(self.out) + len(body))

    def declare(self, line):
        w = _Word()
        cur = [0]
        if not self.word(w, line.text + b'\0', cur, False, False):
            self.err('A variable needs a name.')
        name = w.text
        if self.strict and not self.valid_var_name(w):
            self.err('"%s" can\'t be a variable\'s name: something else already has it.' % name)
        is_int = line.code in (C_SHORT, C_LONG, C_STRING_VAR)     # (a string variable is kept as a whole number: which string)
        self.var_kinds.setdefault(w.name, VAR_KIND[line.code])
        old = self.old_vars.get(w.name)
        if old:
            num = old[0]
        else:
            self.count += 1
            num = self.count
        self.vars.append((num, name, is_int))
        self.var_names.setdefault(w.name, (num, is_int))
        if line.code == C_REF:
            w.var = num
            self.reference(w, True, False)

    def valid_var_name(self, w):
        return self.forms.find(w.name) is None and w.name not in self.t.names

    def set_line(self, line, body):
        text = line.text + b'\0'
        w = _Word()
        cur = [0]
        if not self.word(w, text, cur, True, True):
            self.err('set needs a variable to set.')
        if not w.kind or w.kind == 'X':
            self.err('Unknown variable "%s".' % w.text)
        to = _Word()
        self.word(to, text, cur, False, False)
        if to.raw[:2].lower() != b'to':
            self.err('set needs a "to": set %s to something.' % w.text)
        if w.ref > 0:
            body += (b'G' if w.kind == 'G' else b'r') + struct.pack('<H', w.ref)
        if w.var > 0:
            body += w.kind.encode('ascii') + struct.pack('<H', w.var)
        rest = line.text[cur[0]:]
        if rest.count(b'(') != rest.count(b')'):
            self.err('Brackets don\'t match in this set.')
        rest = rest.lstrip(b' \t,')
        if not rest:
            self.err('set needs a value: set %s to something.' % w.text)
        expr = self.expression(rest)
        body += struct.pack('<H', len(expr)) + expr

    def expression(self, text):
        infix = self.infix(text)
        if not infix:
            self.err('Something is missing: an expression was expected here.')
        return self.postfix(infix)

    def run(self):
        self.read_lines()
        self.first_pass()
        if not self.partial:
            if not self.lines or self.lines[0].code != C_SCRIPTNAME:
                self.lineno = self.lines[0].number if self.lines else 1
                raise CompileError('A script has to start with "scn ScriptName".', self.lineno)
            self.check_blocks()
        for at, line in enumerate(self.lines):
            self.lineno, self.text = line.number, line.whole
            self.compile_line(at, line)
        self.lineno = 0
        for e in self.refs:
            if e.form is None and not e.var:
                raise CompileError('Unknown name "%s" in front of a dot: no form or ref variable has it.' % e.text,
                                   e.line)
        refs = [(e.text, e.form, e.var) for e in self.refs]
        return Compiled(self.name, bytes(self.out), self.script_type, self.count, self.vars, refs, self.src)


def compile_script(source, forms, script_type=SCRIPT_OBJECT, old_vars=(), old_count=0, partial=False, strict=True):
    """Compile source (text, or bytes in the game's cp1252). Raises CompileError for bad source.

    forms: finds forms by editor ID (see GameForms).
    script_type: SCRIPT_OBJECT, SCRIPT_QUEST or SCRIPT_EFFECT. Functions that need a reference need it spelled out in a
        quest script.
    old_vars, old_count: when compiling a script again: its [(number, name, is integer)] and the highest number it has
        given out, so variables keep their numbers.
    partial: a result script (a quest stage's, or a dialogue line's): no scn, no blocks, just lines.
    strict: refuse what the editor refuses but the game's own files sometimes have from their long history (a variable
        named like a form, a non-persistent reference). A script being written always wants this on."""
    if isinstance(source, str):
        source = source.replace('\r\n', '\n').replace('\n', '\r\n').encode(ENC, 'replace')
    return _Compiler(source, forms, script_type, old_vars, old_count, partial, strict).run()


def compile_result(source, forms, strict=True):
    """A result script: what SCHR/SCDA/SCTX/SCRO hold in an INFO or a QUST stage."""
    return compile_script(source, forms, SCRIPT_OBJECT, partial=True, strict=strict)


class Form:
    """A form as the compiler needs it."""
    __slots__ = ('owner', 'fid', 'tag', 'persistent', 'plugin', 'rec')

    def __init__(self, owner, fid, tag, persistent, plugin=None, rec=None):
        self.owner, self.fid, self.tag, self.persistent = owner, fid, tag, persistent
        self.plugin, self.rec = plugin, rec

    def script_vars(self):
        """{lower name: (number, is integer)} of the script on this reference or quest, or None."""
        return self.owner.script_vars(self)

    def message_text(self):
        return self.owner.message_text(self)

    @property
    def interior(self):
        return self.owner.is_interior(self)

    def is_map_marker(self):
        return self.owner.is_map_marker(self)


class GameForms:
    """Finds forms by editor ID in the game's files; the interface a mod's own records can stand beside:

        find(name)       a Form by editor ID (any case), or by its form ID in hex, or None
        find_edid(name)  the same, by editor ID only

    plugins: the indexes in gd.plugins to look in, in load order (default all): the scripts of a master file were
    compiled without the files that came after it."""

    # Records that never carry an editor ID a script could use, and are many: not worth reading
    SKIP = frozenset('LAND NAVM NAVI PGRD INFO'.split())
    PLAYER_NAMES = ('player', 'playerref')
    MARKER_BASE = 0x10

    _shared = {}

    def __init__(self, gd, plugins=None):
        self.gd = gd
        self.plugins = list(range(len(gd.plugins))) if plugins is None else list(plugins)
        self._vars = {}
        self._player = Form(self, 0x14, 'ACHR', True)
        self._names = None

    def _plugin_index(self, i):
        """({lower editor ID: Record}, {global form ID: Record} of what isn't placed in the world) for one file."""
        key = (id(self.gd), i)
        got = GameForms._shared.get(key)
        if got is None:
            names, recs = {}, {}
            p = self.gd.plugins[i]
            mm = p.mm
            for rec, _path in p.walk():
                if rec.tag in self.SKIP:
                    continue
                if rec.tag not in REF_TAGS:
                    recs[self.gd.to_global(i, rec.formid)] = rec
                if rec.flags & tes4.COMPRESSED:
                    e = tes4.subrecord_dict(p.data(rec)).get('EDID')
                    if not e:
                        continue
                else:
                    o = rec.offset + 24
                    if mm[o:o + 4] != b'EDID':
                        continue
                    e = mm[o + 6:o + 6 + struct.unpack_from('<H', mm, o + 4)[0]]
                names[tes4.zstr(e).lower()] = rec
            got = GameForms._shared[key] = (names, recs)
        return got

    def _form(self, i, rec):
        if rec.tag == 'GMST':
            return None
        return Form(self, self.gd.to_global(i, rec.formid), rec.tag, bool(rec.flags & tes4.PERSISTENT), i, rec)

    def find_edid(self, name):
        name = name.lower()
        if name in self.PLAYER_NAMES:
            return self._player
        if self._names is None:
            self._names = {}
            for i in self.plugins:
                for n, rec in self._plugin_index(i)[0].items():
                    self._names[n] = (i, rec)
        hit = self._names.get(name)
        return self._form(*hit) if hit else None

    def find(self, name):
        form = self.find_edid(name)
        if form is not None:
            return form
        try:
            fid = int(name, 16)
        except ValueError:
            return None
        hit = self.gd.forms.get(fid) if fid else None
        return self._form(*hit) if hit else None

    def _record(self, fid):
        """The record the files in view give a form (not placed in the world): (file index, Record), or None."""
        for i in reversed(self.plugins):
            rec = self._plugin_index(i)[1].get(fid)
            if rec is not None:
                return i, rec
        return None

    def _fields(self, form):
        return self.gd.plugins[form.plugin].fields(form.rec)

    def script_vars(self, form):
        if form.plugin is None:
            return None
        f = self._fields(form)
        if form.tag == 'QUST':
            carrier, i = f, form.plugin
        elif form.tag in REF_TAGS:
            base = f.get('NAME')
            hit = self._record(self.gd.to_global(form.plugin, struct.unpack('<I', base)[0])) if base else None
            if not hit:
                return None
            i, rec = hit
            carrier = self.gd.plugins[i].fields(rec)
        else:
            return None
        scri = carrier.get('SCRI')
        return self.vars_of(self.gd.to_global(i, struct.unpack('<I', scri)[0])) if scri else None

    def vars_of(self, sid):
        """A script form's variables: {lower name: (number, is integer)}."""
        got = self._vars.get(sid)
        if got is None:
            got = {}
            hit = self._record(sid)
            if hit:
                i, rec = hit
                last = None
                for tag, data in tes4.iter_subrecords(self.gd.plugins[i].data(rec)):
                    if tag == 'SLSD':
                        last = (struct.unpack_from('<I', data, 0)[0], bool(data[16]))
                    elif tag == 'SCVR' and last:
                        got[tes4.zstr(data).lower()] = last
                        last = None
            self._vars[sid] = got
        return got

    def message_text(self, form):
        return self._fields(form).get('DESC', b'').split(bytes(1))[0]

    def is_interior(self, form):
        return form.fid in self.gd.interiors

    def is_map_marker(self, form):
        base = self._fields(form).get('NAME')
        return bool(base) and struct.unpack('<I', base)[0] & 0xFFFFFF == self.MARKER_BASE
