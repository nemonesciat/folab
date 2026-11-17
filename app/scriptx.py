"""xNVSE's own expressions, compiled to its bytes: `let`, `if eval`, `while ... loop`, `foreach`, `call`, the array and
string commands, `string_var` and `array_var`, and `begin Function {...}` scripts. The part of scriptc.py's compiler that
the game's own compiler never had (a mixin of its _Compiler).

Worked out from real mods' compiled scripts, line beside bytes, and proven the same way (tools/script_oracle.py
--plugin): nothing here is taken on trust from memory of how xNVSE does it.

A command that takes expressions is compiled as:
    count of arguments (1 byte), then each argument: its length in bytes, counting these two (2 bytes), and its tokens
with the tokens in the order a stack machine wants them (operands, then the operator). A token is one byte and what it
needs after it:
    B n           a whole number 0..255            I nn / L nnnn   bigger ones            Z (8 bytes)   one with a fraction
    S len chars   words in quotes                  R ref           a form, by its place in the script's reference list
    G ref         a global                         V type ref var  a variable: type 0 fraction, 1 whole, 2 string,
                                                                   3 array, 4 ref; ref 0 for the script's own
    X ref opcode len ...   a command: len counts itself; then the command's own parameters, compiled its own way
    (a byte under 0x40)    an operator, by its number below
`while` and `foreach` keep, before their argument, where in the script the matching `loop` line ends (4 bytes). A
function's `begin` keeps its parameters (variable number and type each) and its array variables. Inside one of the
game's own expressions (an `if`, a `set`), such a command is an X with its bytes after it. As a parameter of an ordinary
command, an expression in brackets is FF FF, its length, its tokens."""
import struct

VAR_TYPES = {'f': 0, 'i': 1, 's': 2, 'a': 3, 'r': 4}
# text: (number, how tightly it binds, binds to the right)
BINARY = {':=': (0, 2, True), '=': (0, 2, True), '||': (1, 5, False), '&&': (2, 7, False), ':': (3, 9, False), '==': (4, 13, False), '!=': (5, 13, False),
          '>': (6, 15, False), '<': (7, 15, False), '>=': (8, 15, False), '<=': (9, 15, False), '|': (10, 16, False), '&': (11, 17, False),
          '<<': (12, 18, False), '>>': (13, 18, False), '+': (14, 19, False), '-': (15, 19, False), '*': (16, 21, False),
          '/': (17, 21, False), '%': (18, 21, False), '^': (19, 23, True), '<-': (26, 2, False), '+=': (28, 2, True),
          '*=': (29, 2, True), '/=': (30, 2, True), '^=': (31, 2, True), '-=': (32, 2, True), '->': (35, 91, False), '::': (36, 3, False)}
UNARY = {'-': (20, 25), '!': (21, 27), '$': (27, 20), '#': (33, 20), '*': (34, 20), '&': (37, 20)}
SUBSCRIPT = (24, 90)
SYMBOLS = sorted(set(BINARY) | set(UNARY) | {'(', ')', '[', ']', ','}, key=len, reverse=True)
C_STRING_VAR, C_ARRAY_VAR = -2, -3          # (pseudo line codes: the game has no such declarations)
BLOCK_FUNCTION = 0x0D
FUNCTION_VERSION = 1


def assigns(rest):
    """Does what follows a line's first word make the line an assignment (`x = 5`, `x += 1`, `a[2] := 3`)?"""
    rest = rest.lstrip(b' \t')
    if rest[:1] == b'[':
        return True
    return rest[:2] in (b':=', b'+=', b'-=', b'*=', b'/=', b'^=') or (rest[:1] == b'=' and rest[1:2] != b'=')


LAMBDA = 'A function written inside a line (%s) is not something FOLab can compile yet: compile this script in the GECK started through xNVSE.'


def inline_function(text):
    """Is there a function written inside this line: `(begin Function {...}` to a later `end)`, or `{...} => ...`?"""
    low = b' '.join(bytes(text).lower().split())
    return b'(begin function' in low or b'( begin function' in low or b'=>' in low


def _ident_start(c):
    return 65 <= c <= 90 or 97 <= c <= 122 or c == 95


def _ident(c):
    return _ident_start(c) or 48 <= c <= 57


class Expressions:
    """Mixed into scriptc._Compiler."""

    def x_init(self):
        self.var_kinds = {}         # lower name -> 'f' 'i' 's' 'a' 'r'
        self.loops = []             # where each open while/foreach keeps its end
        codes = self.t.names
        self.x_call, self.x_loop = codes.get('call'), codes.get('loop')
        self.x_openers = {codes.get('while'), codes.get('foreach')} - {None}

    # -- operands --------------------------------------------------------------------------------------------------

    def x_number(self, raw):
        text = raw.decode('ascii')
        if '.' in text:
            return b'Z' + struct.pack('<d', float(text))
        v = int(text, 16) if text[:2].lower() == '0x' else int(text)
        if v < 0x100:
            return b'B' + bytes([v])
        if v < 0x10000:
            return b'I' + struct.pack('<H', v)
        return b'L' + struct.pack('<I', v & 0xFFFFFFFF)

    def x_name(self, text, i):
        """The name at text[i:] (with what it is called on, if `thing.name`): (token bytes, where it ended)."""
        import scriptc
        start = i
        while i < len(text) and _ident(text[i]):
            i += 1
        w = scriptc._Word()
        w.raw = text[start:i]
        if i < len(text) and text[i] == 46 and i + 1 < len(text) and _ident_start(text[i + 1]):
            self._ref_prefix(w, True, False)
            i += 1
            start = i
            while i < len(text) and _ident(text[i]):
                i += 1
            w.raw = text[start:i]
            w.kind, w.var = '', 0
        if self.resolve(w):
            if w.kind == 'G':
                return b'G' + struct.pack('<H', w.ref), i
            kind = self.var_kinds.get(w.name, 'i' if w.kind == 's' else 'f') if not w.form else ('i' if w.kind == 's' else 'f')
            return b'V' + struct.pack('<BHH', VAR_TYPES[kind], w.ref, w.var), i
        if self.command(w):
            fn = self.t.by_code.get(w.code)
            if fn is None or 0x100 <= w.code < 0x1CD:
                self.err('"%s" can\'t be used in an expression.' % w.text)
            if fn['ref'] and self.quest and not w.ref:
                self.err('%s needs a reference in front of it in a quest script (like player.%s).' % (w.text, w.text))
            data, took = self.x_command(fn, text[i:])
            return b'X' + struct.pack('<HHH', w.ref, w.code, len(data) + 2) + data, i + took
        if w.ref:
            self.err('Unknown variable or function "%s".' % w.text)
        if not self.reference(w, False, False) or w.form is None:
            self.err('Unknown word "%s": not a variable, a function or anything with that name.' % w.text)
        return b'R' + struct.pack('<H', w.ref), i

    def x_command(self, fn, text):
        """A command's parameters as they sit inside an expression: (bytes, how much text they took)."""
        if not fn.get('expr'):
            if not fn['params']:
                return b'\0\0', 0
            return self.params(fn, text, False)
        return self.x_args(text, fn['code'] == self.x_call)

    # -- expressions -----------------------------------------------------------------------------------------------

    def x_expr(self, text, i):
        """One expression from text[i:], up to a comma or a closing bracket that isn't its own: (tokens, where it stopped)."""
        out = bytearray()
        stack = []                              # (operator number, binding, right) or '(' / '['
        operand = False                         # was the last thing a value?
        n = len(text)

        def pop_while(test):
            while stack and stack[-1] not in ('(', '[') and test(stack[-1]):
                out.append(stack.pop()[0])
        while True:
            while i < n and text[i] in (9, 32):
                i += 1
            if i >= n:
                break
            c = text[i]
            if 48 <= c <= 57 or (c == 46 and i + 1 < n and 48 <= text[i + 1] <= 57):
                j = i
                if text[i:i + 2].lower() == b'0x':
                    j += 2
                while j < n and (_ident(text[j]) or text[j] == 46):
                    j += 1
                raw = text[i:j]
                try:
                    tok = self.x_number(raw)
                    i = j
                except ValueError:              # (a name that starts with a digit, as some of the game's forms do)
                    tok, i = self.x_name(text, i)
                out += tok
                operand = True
                continue
            if c == 34:
                end = text.find(b'"', i + 1)
                if end < 0:
                    self.err('Mismatched quote marks.')
                s = text[i + 1:end]
                out += b'S' + struct.pack('<H', len(s)) + s
                i, operand = end + 1, True
                continue
            if _ident_start(c):
                tok, i = self.x_name(text, i)
                out += tok
                operand = True
                continue
            sym = next((s for s in SYMBOLS if text.startswith(s.encode(), i)), None)
            if c == 123:
                self.err('A function written inside a line ({...} => ...) is not something FOLab can compile yet: compile this '
                         'script in the GECK started through xNVSE.')
            if sym is None:
                self.err('"%s" makes no sense in this expression.' % chr(c))
            if sym == ',':
                break
            if sym == '(':
                stack.append('(')
                i, operand = i + 1, False
                continue
            if sym == '[':
                if not operand:
                    self.err('A [ needs something in front of it to look into.')
                pop_while(lambda t: t[1] >= SUBSCRIPT[1])
                stack.append('[')
                i, operand = i + 1, False
                continue
            if sym in (')', ']'):
                opener = '(' if sym == ')' else '['
                if opener not in stack:
                    break                       # (it closes something outside this expression)
                while stack[-1] not in ('(', '['):
                    out.append(stack.pop()[0])
                if stack.pop() != opener:
                    self.err('Brackets don\'t match in this expression.')
                if sym == ']':
                    out.append(SUBSCRIPT[0])
                i, operand = i + 1, True
                continue
            if not operand:
                if sym not in UNARY:
                    self.err('"%s" needs something in front of it.' % sym)
                code, bind = UNARY[sym]
                stack.append((code, bind, True))
                i += len(sym)
                continue
            if sym not in BINARY:
                self.err('"%s" can\'t go here in this expression.' % sym)
            code, bind, right = BINARY[sym]
            pop_while(lambda t: t[1] > bind or (t[1] == bind and not right))
            stack.append((code, bind, right))
            i, operand = i + len(sym), False
        while stack:
            top = stack.pop()
            if top in ('(', '['):
                self.err('Brackets don\'t match in this expression.')
            out.append(top[0])
        if not out:
            self.err('Something is missing: an expression was expected here.')
        return bytes(out), i

    def x_list(self, text, i=0):
        """Expressions with commas between them: ([tokens of each], where the list stopped)."""
        args, n = [], len(text)
        while True:
            while i < n and text[i] in (9, 32, 44):
                i += 1
            if i >= n or text[i] in (41, 93):
                return args, i
            tok, i = self.x_expr(text, i)
            args.append(tok)

    @staticmethod
    def x_pack(args):
        return b''.join(struct.pack('<H', len(a) + 2) + a for a in args)

    def x_args(self, text, is_call=False):
        """The arguments of a command that takes expressions: (bytes, how much text they took). `call` keeps the
        function apart from what it is given."""
        args, took = self.x_list(text)
        if len(args) > 255:
            self.err('Too many arguments.')
        if is_call:
            if not args:
                self.err('call needs a function to call.')
            return bytes([FUNCTION_VERSION]) + self.x_pack(args[:1]) + bytes([len(args) - 1]) + self.x_pack(args[1:]), took
        return bytes([len(args)]) + self.x_pack(args), took

    def x_param(self, text, i):
        """An expression in brackets given to an ordinary command as one of its parameters: (bytes, where it ended)."""
        tok, j = self.x_expr(text, i)
        return b'\xff\xff' + struct.pack('<H', len(tok) + 2) + tok, j

    # -- lines -----------------------------------------------------------------------------------------------------

    def x_line(self, fn, text, body):
        """A line that is one of these commands: `let ...`, `while ...`, `ar_Append ...`."""
        code = fn['code']
        if not text.strip(b' \t,'):
            return                              # (loop, break, continue: nothing after them, not even a count)
        if code in self.x_openers:
            body += bytes(4)                    # (where its loop ends: put in when the loop line is reached)
        data, took = self.x_args(text, code == self.x_call)
        if text[took:].strip(b' \t,)'):
            self.err('The line should end after its expression, but there is more: "%s".' % text[took:].decode('cp1252', 'replace'))
        body += data

    def x_after(self, code, start):
        """Once a line is in the script: note an opened loop, or tell the last opened one where it ends."""
        if code in self.x_openers:
            if len(self.loops) >= 32:
                self.err('Loops can nest at most 32 deep.')
            self.loops.append(start)
        elif code == self.x_loop:
            if not self.loops:
                self.err('A loop without a while or foreach to go back to.')
            struct.pack_into('<I', self.out, self.loops.pop(), len(self.out))

    def x_function(self, text, body):
        """What `begin Function {a, b}` keeps: its parameters (variable number and type), and the script's array variables."""
        text = text.strip()
        if not (text.startswith(b'{') and text.endswith(b'}')):
            self.err('A function\'s parameters go in curly brackets: begin Function {a, b}, or {} for none.')
        names = [p.strip() for p in text[1:-1].replace(b'\t', b' ').split(b',') if p.strip()]
        out = bytearray([FUNCTION_VERSION, len(names)])
        for raw in names:
            name = raw.decode('cp1252', 'replace').lower()
            found = self.var_names.get(name) or self.old_vars.get(name)
            if not found or name not in self.var_kinds:
                self.err('"%s" isn\'t one of this script\'s variables: declare a function\'s parameters above its begin.' % raw.decode('cp1252', 'replace'))
            out += struct.pack('<HB', found[0], VAR_TYPES[self.var_kinds[name]])
        out.append(0)       # (a list of array variables to clear went here in old xNVSEs; scripts compiled by today's have none)
        body += out
