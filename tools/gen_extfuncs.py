"""Generate app/extfuncs.json: the script commands xNVSE and its plugins add, read from the user's own files (never changed).

Each command is a 40-byte entry in its DLL: name, short name, opcode, help, whether it needs a calling reference, how
many parameters, where their list is (type name, type number, optional), and the three functions the game calls. A
plugin's entries hold no opcode: xNVSE numbers them as they register, and writes every one to nvse.log (the game must
have been started through xNVSE once). xNVSE's own are numbered in the order its start-up code adds them, read here
from that code; the count is checked against the first plugin's base in the log.

A command whose parse function is the game's own takes its parameters the way the game's commands do, and FOLab's
compiler can write it. The rest are parsed by xNVSE's own expression compiler ('expression': True): not yet.

    py -3 tools/gen_extfuncs.py
"""
import json
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'app'))
import gamedata  # noqa: E402

GAME_PARSE = 0x5B1BA0           # the game's own parameter parser, which plain commands name
NAME = re.compile(rb'^[A-Za-z_][A-Za-z0-9_]{1,63}$')


class Dll:
    def __init__(self, path):
        self.path = path
        with open(path, 'rb') as f:
            self.d = f.read()
        pe = struct.unpack_from('<I', self.d, 0x3c)[0]
        count, opt = struct.unpack_from('<H', self.d, pe + 6)[0], struct.unpack_from('<H', self.d, pe + 20)[0]
        self.base = struct.unpack_from('<I', self.d, pe + 52)[0]
        self.sections = []
        for i in range(count):
            o = pe + 24 + opt + i * 40
            name = self.d[o:o + 8].rstrip(b'\0').decode('latin-1')
            vs, va, rs, rp = struct.unpack_from('<IIII', self.d, o + 8)
            self.sections.append((name, self.base + va, max(vs, rs), rp, rs))

    def off(self, va):
        for _n, a, size, rp, rs in self.sections:
            if a <= va < a + size and va - a < rs:
                return va - a + rp
        return None

    def va(self, off):
        for _n, a, _size, rp, rs in self.sections:
            if rp <= off < rp + rs:
                return off - rp + a
        return None

    def text(self, va, most=256):
        o = self.off(va)
        if o is None:
            return None
        e = self.d.find(b'\0', o, o + most)
        return None if e < 0 else self.d[o:e]

    def entry(self, o):
        """The command at a file offset, or None when the bytes there aren't one."""
        if o + 40 > len(self.d):
            return None
        long_p, short_p, opcode, help_p, needs, n, params_p, exe_p, parse_p, eval_p, flags = struct.unpack_from('<IIIIHHIIIII', self.d, o)
        if needs > 1 or n > 40 or not long_p:
            return None
        name = self.text(long_p, 80)
        if not name or not NAME.match(name):
            return None
        short = self.text(short_p, 80) if short_p else b''
        if short is None or (short and not NAME.match(short)):
            return None
        if (n and self.off(params_p) is None) or (exe_p and self.off(exe_p) is None) or not exe_p:
            return None
        params = []
        for k in range(n):
            po = self.off(params_p) + 12 * k
            tname_p, tid, optional = struct.unpack_from('<III', self.d, po)
            tname = self.text(tname_p, 80) if tname_p else b''      # (JIP's parameters go unnamed)
            if tname is None or len(tname) > 60 or optional > 1 or (not tname and tid > 0x100):
                return None
            params.append([tid, bool(optional), tname.decode('latin-1')])
        return {'name': name.decode(), 'short': short.decode(), 'opcode': opcode, 'needs_ref': bool(needs), 'params': params,
                'parse': parse_p, 'va': self.va(o)}        # (parse 0: the plugin leaves it to xNVSE, which gives the game's own)

    def commands(self):
        """Every command entry in the file's data, by where it sits."""
        out = {}
        for name, a, _size, rp, rs in self.sections:
            if name.startswith('.text') or name.startswith('.reloc') or name.startswith('.rsrc'):
                continue
            for o in range(rp, rp + rs - 39, 4):
                e = self.entry(o)
                if e:
                    out[e['va']] = e
        return out

    def added_in_order(self, cmds):
        """The entries in the order the start-up code hands them over: each is pushed (68 imm32) before the call that adds it."""
        code = [(a, rp, rs) for name, a, _s, rp, rs in self.sections if name.startswith('.text')]
        seen = []
        for a, rp, rs in code:
            blob = self.d[rp:rp + rs]
            for m in re.finditer(rb'\x68(....)', blob, re.S):
                va = struct.unpack('<I', m.group(1))[0]
                if va in cmds:
                    seen.append((a + m.start(), va))
        return seen


def from_log(path):
    """{name lowered: (opcode, short name)} for every command xNVSE's log says a plugin registered."""
    out, order = {}, []
    with open(path, encoding='latin-1') as f:
        for line in f:
            m = re.match(r'Reg\w+Command\s+\[([0-9A-Fa-f]{4})\]\s+(\w+)(?:\s+\((\w+)\))?', line)
            if m:
                op = int(m.group(1), 16)
                out[m.group(2).lower()] = (op, m.group(3) or '')
                order.append((op, m.group(2)))
    return out, order


CORE_BASE = 0x1400
ANCHORS = {'GetNVSEVersion': 0x1400, 'SetWeight': 0x1407, 'ListAddForm': 0x1442, 'PrintToConsole': 0x14A0, 'SetArmorAR': 0x14B4,
           'Let': 0x1539, 'ForEach': 0x153D, 'SetFunctionValue': 0x1546, 'ar_Append': 0x1566, 'sv_Replace': 0x1575,
           'SetEquipmentBipedMask': 0x15C6}       # (as real mods' compiled scripts have them: the count is checked against these)


def core_commands(core, console):
    """xNVSE's own commands with the opcodes its start-up code gives them: every call that adds one, in order, counting
    from 0x1400. Two kinds of call: one hands over an entry (pushed just before), one a console command's name to offer
    scripts as con_<name>."""
    cc = core.commands()
    name, a, _size, rp, rs = next(x for x in core.sections if x[0].startswith('.text'))
    blob = core.d[rp:rp + rs]
    calls = {}
    for m in re.finditer(bytes([0xE8]) + b'(....)', blob, re.S):
        at = m.start()
        tgt = (a + at + 5 + struct.unpack('<i', m.group(1))[0]) & 0xffffffff
        calls.setdefault(tgt, []).append(at)
    # the adding function: the one most often called right after a push of an entry
    def after_push(at):
        w = blob[max(0, at - 24):at]
        return [struct.unpack_from('<I', w, k + 1)[0] for k in range(len(w) - 4) if w[k] == 0x68]
    add = max(calls, key=lambda t: sum(1 for at in calls[t] if any(v in cc for v in after_push(at))))
    first = min(at for at in calls[add] if any(cc.get(v, {}).get('name') == 'GetNVSEVersion' for v in after_push(at)))
    last = max(calls[add])
    # the importing function: called in the same stretch with a string in ecx (b9 imm32) naming a console command
    by_console = {e['name'].lower(): e for e in console}
    by_console.update({e['short'].lower(): e for e in console if e['short']})

    def named(at):
        w = blob[at - 5:at]
        s = core.text(struct.unpack_from('<I', w, 1)[0], 80) if w[0] == 0xb9 else None
        return s.decode('latin-1') if s and s.decode('latin-1').lower() in by_console else None
    imp = max((t for t in calls if t != add), key=lambda t: sum(1 for at in calls[t] if first <= at <= last and named(at)))
    events = sorted([(at, 'add') for at in calls[add] if first <= at <= last] + [(at, 'import') for at in calls[imp] if first <= at <= last and named(at)])
    default = max(set(e['parse'] for e in cc.values() if e['parse']), key=lambda p: sum(1 for e in cc.values() if e['parse'] == p))
    out = []
    for n, (at, kind) in enumerate(events):
        code = CORE_BASE + n
        if kind == 'import':
            c = by_console[named(at).lower()]
            out.append({'name': 'con_' + named(at), 'short': '', 'code': code, 'ref': c['ref'], 'params': c['params'], 'from': 'xNVSE'})
            continue
        e = next((cc[v] for v in reversed(after_push(at)) if v in cc), None)
        if e is None:
            continue                            # (an entry of xNVSE's inner workings, no name a script could write)
        out.append({'name': e['name'], 'short': e['short'], 'code': code, 'ref': int(e['needs_ref']),
                    'params': [[p[0], int(p[1]), p[2]] for p in e['params']], 'from': 'xNVSE',
                    **({'expr': 1} if e['parse'] != default else {})})
    got = {e['name']: e['code'] for e in out}
    wrong = {n: (hex(got.get(n, 0)), hex(c)) for n, c in ANCHORS.items() if got.get(n) != c}
    if wrong:
        raise SystemExit('This xNVSE numbers its commands differently from what real scripts show: %s' % wrong)
    return out


def plugin_commands(game, log):
    """Each plugin command the log lists, with its parameters from whichever plugin DLL holds its entry."""
    folder = os.path.join(game, 'Data', 'NVSE', 'Plugins')
    found = {}
    for fn in sorted(os.listdir(folder)) if os.path.isdir(folder) else []:
        if not fn.lower().endswith('.dll'):
            continue
        d = Dll(os.path.join(folder, fn))
        nonzero = [e['parse'] for e in d.commands().values() if e['parse'] and d.off(e['parse']) is not None]
        for e in d.commands().values():
            # (a parser of the plugin's own, or xNVSE's expression one handed over at start-up: not the game's)
            e['expr'] = bool(e['parse']) and e['parse'] != GAME_PARSE
            e['from'] = os.path.splitext(fn)[0]
            found.setdefault(e['name'].lower(), e)
    out, lost = [], []
    for name, (code, short) in log.items():
        e = found.get(name)
        if e is None:
            lost.append(name)
            continue
        out.append({'name': e['name'], 'short': short or e['short'], 'code': code, 'ref': int(e['needs_ref']),
                    'params': [[p[0], int(p[1]), p[2]] for p in e['params']], 'from': e['from'], **({'expr': 1} if e['expr'] else {})})
    return out, lost


def main():
    data = gamedata.find_data_dir()
    game = os.path.dirname(os.path.normpath(data))
    with open(os.path.join(HERE, '..', 'app', 'scriptfuncs.json'), encoding='utf-8') as f:
        base = json.load(f)
    core = core_commands(Dll(os.path.join(game, 'nvse_1_4.dll')), base['console'])
    log, _order = from_log(os.path.join(game, 'nvse.log'))
    plug, lost = plugin_commands(game, log)
    taken = {e['name'].lower() for e in base['script']}
    cmds = [e for e in core + plug if e['name'].lower() not in taken]
    kinds = len(base['param_kinds'])
    for e in cmds:
        if not e.get('expr') and any(p[0] >= kinds for p in e['params']):
            e['expr'] = 1                       # (a parameter kind the game hasn't: only xNVSE's own compiler reads it)
    out = os.path.join(HERE, '..', 'app', 'extfuncs.json')
    with open(out, 'w', encoding='utf-8') as f:
        json.dump({'commands': cmds}, f, separators=(',', ':'))
    plain = sum(1 for e in cmds if not e.get('expr'))
    print("%d commands: %d FOLab can compile, %d that need xNVSE's own expression compiler" % (len(cmds), plain, len(cmds) - plain))
    for src in sorted({e['from'] for e in cmds}):
        print('  %-12s %d' % (src, sum(1 for e in cmds if e['from'] == src)))
    if lost:
        print('in nvse.log but in no plugin DLL here: %s' % ', '.join(lost[:20]))


if __name__ == '__main__':
    main()
