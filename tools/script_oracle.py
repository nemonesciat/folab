"""Compile every script of the game and compare it with the bytes the game's own compiler gave.

    py -3 tools/script_oracle.py [--show N] [--only FalloutNV.esm] [--kind SCPT|INFO|QUST] [--write report.txt]

Prints how many match byte for byte, and groups the rest by why. Reads the game's files, changes nothing."""
import argparse
import collections
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'app'))
import gamedata  # noqa: E402
import scriptc  # noqa: E402
import tes4  # noqa: E402


class Item:
    """One compiled unit in a record: a script, a quest stage's or a dialogue line's result script."""
    __slots__ = ('plugin', 'tag', 'formid', 'edid', 'schr', 'scda', 'sctx', 'vars', 'refs', 'part')

    def __init__(self, plugin, tag, formid, edid, part):
        self.plugin, self.tag, self.formid, self.edid, self.part = plugin, tag, formid, edid, part
        self.schr = self.scda = self.sctx = None
        self.vars, self.refs = [], []


def units(pi, p):
    """Every compiled unit of a plugin. A record's unit starts at each SCHR."""
    name = os.path.basename(p.path)
    for rec, _path in p.walk():
        if rec.tag not in ('SCPT', 'INFO', 'QUST'):
            continue
        cur, part, edid = None, 0, ''
        last_var = None
        for tag, data in tes4.iter_subrecords(p.data(rec)):
            if tag == 'EDID':
                edid = tes4.zstr(data)
            elif tag == 'SCHR':
                if cur is not None:
                    yield cur
                cur = Item(name, rec.tag, rec.formid, edid, part)
                cur.schr = data
                part += 1
            elif cur is None:
                continue
            elif tag == 'SCDA':
                cur.scda = data
            elif tag == 'SCTX':
                cur.sctx = data
            elif tag == 'SLSD':
                last_var = data
            elif tag == 'SCVR' and last_var:
                cur.vars.append((struct.unpack_from('<I', last_var, 0)[0], tes4.zstr(data), bool(last_var[16]),
                                 last_var))
                last_var = None
            elif tag == 'SCRO':
                cur.refs.append(('o', struct.unpack('<I', data)[0]))
            elif tag == 'SCRV':
                cur.refs.append(('v', struct.unpack('<I', data)[0]))
        if cur is not None:
            yield cur


def compare(gd, pi, u, forms):
    """(category, detail)"""
    src = u.sctx
    partial = u.tag != 'SCPT'
    _unused, nrefs, size, nvars, stype, flag = struct.unpack('<IIIIHH', u.schr)
    if not u.scda and not src:
        return 'empty', ''
    if not src:
        return 'no source', ''
    old = [(i, n, f) for i, n, f, _r in u.vars]
    try:
        r = scriptc.compile_script(src, forms, stype, old_vars=old, old_count=nvars, partial=partial, strict=False)
    except scriptc.CompileError as e:
        return 'error: ' + e.message.split('"')[0][:50], str(e) + '  | ' + e.text
    except Exception as e:  # a crash is a bug here
        return 'crash: ' + type(e).__name__, repr(e)
    if not u.scda and not r.data:
        return 'match, source compiles to nothing', ''
    if not u.scda:
        return 'source newer than bytes: game has none', r.data[:40].hex(' ')
    if r.data == u.scda and sameRefs(gd, pi, u, r) and r.var_count == nvars and sameVars(u, r):
        if r.schr() != u.schr:
            return 'same code, other SCHR', '%r vs %r' % (u.schr, r.schr())
        return 'match', ''
    if r.data == u.scda:
        if not sameRefs(gd, pi, u, r):
            return 'same code, other refs', refs_text(gd, pi, u, r)
        if r.var_count != nvars:
            return 'same code, var count', '%d vs %d' % (r.var_count, nvars)
        return 'same code, other vars', '%r vs %r' % (r.vars, old)
    i = next((k for k in range(min(len(r.data), len(u.scda))) if r.data[k] != u.scda[k]), min(len(r.data), len(u.scda)))
    return 'bytes differ', 'at %d of %d/%d\n  game: %s\n  ours: %s\n  refs %s' % (
        i, len(u.scda), len(r.data), u.scda[max(0, i - 24):i + 40].hex(' '), r.data[max(0, i - 24):i + 40].hex(' '),
        refs_text(gd, pi, u, r))


def sameVars(u, r):
    return [(i, n.lower(), f) for i, n, f, _r in u.vars] == [(i, n.lower(), f) for i, n, f in r.vars]


def sameRefs(gd, pi, u, r):
    if len(u.refs) != len(r.refs):
        return False
    for (kind, val), (_n, form, var) in zip(u.refs, r.refs):
        if kind == 'v':
            if var != val:
                return False
        else:
            if var or form is None or gd.to_global(pi, val) != form.fid:
                return False
    return True


def refs_text(gd, pi, u, r):
    a = ['v%d' % v if k == 'v' else '%X' % gd.to_global(pi, v) for k, v in u.refs]
    b = ['v%d' % v if v else '%X(%s)' % (f.fid if f else 0, n) for n, f, v in r.refs]
    return 'game %s\n       ours %s' % (a, b)


def visible_plugins(gd, pi):
    p = gd.plugins[pi]
    names = [m.lower() for m in p.header['masters']]
    return [i for i, n in enumerate(gd.names) if n in names or i == pi]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--show', type=int, default=3)
    ap.add_argument('--only')
    ap.add_argument('--kind')
    ap.add_argument('--write')
    ap.add_argument('--category')
    a = ap.parse_args()
    gd = gamedata.GameData()
    totals = collections.Counter()
    cats = collections.defaultdict(list)
    for pi, p in enumerate(gd.plugins):
        name = os.path.basename(p.path)
        if a.only and a.only.lower() != name.lower():
            continue
        forms = scriptc.GameForms(gd, visible_plugins(gd, pi))
        for u in units(pi, p):
            if a.kind and u.tag != a.kind:
                continue
            cat, detail = compare(gd, pi, u, forms)
            if cat == 'empty':
                cats[cat].append((u, detail))
                continue
            totals[(u.tag, cat.startswith('match'))] += 1
            cats[cat].append((u, detail))
    out = []
    for tag in ('SCPT', 'INFO', 'QUST'):
        good, bad = totals[(tag, True)], totals[(tag, False)]
        if good + bad:
            out.append('%s: %d of %d match (%.1f%%)' % (tag, good, good + bad, 100.0 * good / (good + bad)))
    for cat, items in sorted(cats.items(), key=lambda kv: -len(kv[1])):
        out.append('%6d  %s' % (len(items), cat))
    for cat, items in sorted(cats.items(), key=lambda kv: -len(kv[1])):
        if cat.startswith('match') or cat == 'empty' or (a.category and a.category not in cat):
            continue
        out.append('--- ' + cat)
        for u, detail in items[:a.show]:
            out.append('%s %s %08X %s part %d: %s' % (u.plugin, u.tag, u.formid, u.edid, u.part, detail))
    text = '\n'.join(out)
    print(text.encode('ascii', 'replace').decode('ascii'))
    if a.write:
        with open(a.write, 'w', encoding='utf-8') as f:
            f.write(text)


if __name__ == '__main__':
    main()
