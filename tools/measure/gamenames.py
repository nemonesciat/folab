"""The game's functions by address (FalloutNV.exe 1.4.0.525), for reading a measurement: from fnv_decomp's
build/units.json (its names and addresses only; its placeholder names made from addresses are shown as the address).

    names = GameNames()            # reads units.json once
    names.at(0x0086e5b0)           # 'Main::OnIdle'-style name, or None outside any known function
"""
import bisect
import json
import os

UNITS = os.path.join(os.path.expanduser('~'), 'Documents', 'GitHub', 'fnv_decomp', 'build', 'units.json')

_SPECIAL = {'0': '{ctor}', '1': '{dtor}', '2': 'operator new', '3': 'operator delete', '4': 'operator=',
            '_G': '{deleting dtor}', '_E': '{deleting dtor}', '_U': 'operator new[]', '_V': 'operator delete[]'}


def plain(symbol):
    """An MSVC symbol as Class::Name (no arguments). Placeholder FUN_ names come back as None."""
    if not symbol.startswith('?'):
        name = symbol.lstrip('_@')
        return None if name.startswith('FUN_') else name.split('@')[0]
    s = symbol[1:]
    special = None
    if s.startswith('?'):
        for code in ('_G', '_E', '_U', '_V', '0', '1', '2', '3', '4'):
            if s[1:].startswith(code):
                special, s = _SPECIAL[code], s[1 + len(code):]
                break
        else:
            return None
    parts = s.split('@@')[0].split('@')
    if any(p.startswith('FUN_') or p.startswith('FnvCpu_') or p.endswith('_shell') for p in parts):
        return None
    parts = [p for p in parts if p and not p[0].isdigit() and not p.startswith('?') and not p.startswith('fnv_')]
    if not parts:
        return None
    if special:
        cls = parts[0]
        return '%s::%s' % ('::'.join(reversed(parts)), cls if special == '{ctor}' else
                           '~' + cls if special.startswith('{d') else special)
    return '::'.join(reversed(parts))


class GameNames:
    def __init__(self, units=UNITS):
        with open(units, encoding='utf-8') as f:
            data = json.load(f)
        rows = {}
        for unit in data['units']:
            src = os.path.splitext(os.path.basename(unit.get('source', '')))[0]
            for fn in unit.get('functions', []):
                a = int(fn['address'], 16)
                rows[a] = (fn.get('size') or 1, plain(fn.get('symbol', '')), src)
        self.starts = sorted(rows)
        self.rows = [rows[a] for a in self.starts]

    def find(self, address):
        """(start, name or None, source file) of the function holding address, or None."""
        i = bisect.bisect_right(self.starts, address) - 1
        if i < 0:
            return None
        size, name, src = self.rows[i]
        start = self.starts[i]
        return (start, name, src) if address < start + size else None

    def at(self, address):
        hit = self.find(address)
        if not hit:
            return None
        start, name, src = hit
        return name or '%s @%08x' % (src, start)


if __name__ == '__main__':
    n = GameNames()
    named = sum(1 for r in n.rows if r[1])
    print('%d functions, %d with names' % (len(n.starts), named))
    for a in n.starts[::9000]:
        print('%08x %s' % (a, n.at(a)))
