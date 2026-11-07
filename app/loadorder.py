"""The game's load order: which plugins it loads, and in what order.

New Vegas loads the plugins listed in %LOCALAPPDATA%\\FalloutNV\\plugins.txt. Their order isn't that list's: it goes by
the files' modified times, masters (.esm, or the master flag) first, oldest first; when two change the same thing the
one loaded last wins. So reordering here means giving files new dates, as every mod manager for this game does: the
contents of a file are never touched, and neither are the game's own files' dates. Everything here only reads until
save() is asked for; save() keeps a copy of plugins.txt and of every date first (restore() puts them back).

FOLab's own test helper (playtest.py) is left as it stands."""
import json
import os

import time

import gamedata
import install
import recdiff
import loadout
import tes4

OFFICIAL = {n.lower() for n in gamedata.OFFICIAL}
BASE = 'falloutnv.esm'
HELPER = 'folab test.esp'
TOO_MANY = 130          # (past about this many the game grows unstable, however good the mods)
STEP = 2                # seconds between two plugins given new dates (the coarsest clock a disk may keep)
PARENTS = {'CELL', 'WRLD', 'DIAL'}
LIMIT = 2000


def backups_dir():
    return install.BACKUPS


def _txt_lines():
    lo = loadout.current()
    return lo.active() if lo else install._lines()


def active_names(lines=None):
    return [l.strip() for l in (_txt_lines() if lines is None else lines) if l.strip() and not l.lstrip().startswith('#')]


def _header(path):
    pf = tes4.PluginFile(path)
    try:
        return dict(pf.header)
    finally:
        pf.close()


def scan_files(data_dir):
    """{lower name: row} for every plugin in the Data folder."""
    out = {}
    lo = loadout.current()
    at = lo.order_of() if lo else {}
    for fn in loadout.plugin_names(data_dir):
        p = loadout.plugin_path(data_dir, fn)
        row = {'name': fn, 'official': fn.lower() in OFFICIAL, 'mtime': os.path.getmtime(p), 'size': os.path.getsize(p), 'found': True}
        try:
            h = _header(p)
            row.update(esm=bool(h['flags'] & 1) or fn.lower().endswith('.esm'), masters=h['masters'], author=h['author'], description=h['description'], records=h['records'])
        except (ValueError, OSError) as e:
            row.update(esm=fn.lower().endswith('.esm'), masters=[], author='', description='', records=0, error=str(e))
        if lo:
            row.update(order=at[fn.lower()], mod=lo.who(fn))      # (a loadout's order is its profile's, not the files' dates)
        out[fn.lower()] = row
    return out


def _rank(row):
    """Where the game puts a plugin: masters first, oldest first; the game's own master before everything."""
    return (row['name'].lower() != BASE, not row['esm'], row.get('order', row['mtime']), row['name'].lower())


def in_game_order(rows):
    return sorted(rows, key=_rank)


def problems(rows):
    """Each row's troubles, given the rows in load order. A row is on if 'active'."""
    on = [r['name'].lower() for r in rows if r['active']]
    at = {n: i for i, n in enumerate(on)}
    have = {r['name'].lower(): r for r in rows}
    for r in rows:
        r['problems'] = []
        if not r['found']:
            if r['active']:
                r['problems'].append('It\'s on the list, but there\'s no such file in Data.')
            continue
        if r.get('error'):
            r['problems'].append('FOLab can\'t read it: %s' % r['error'])
        if not r['active']:
            continue
        for m in r['masters']:
            low = m.lower()
            if low not in have or not have[low]['found']:
                r['problems'].append('Needs %s, which isn\'t in Data. The game won\'t start with this on.' % m)
            elif low not in at:
                r['problems'].append('Needs %s, which is switched off. The game won\'t start with this on.' % m)
            elif at[low] > at[r['name'].lower()]:
                r['problems'].append('Needs %s, which loads after it.' % m)
    return rows


def read(data_dir, mod=None):
    files = scan_files(data_dir)
    lines = _txt_lines()
    active = {n.lower() for n in active_names(lines)}
    rows = []
    for low, row in files.items():
        rows.append(dict(row, active=low in active or low == BASE, mine=bool(mod and low == mod.lower()), helper=low == HELPER))
    for n in active_names(lines):
        if n.lower() not in files:
            rows.append({'name': n, 'official': n.lower() in OFFICIAL, 'mtime': float('inf'), 'size': 0, 'found': False, 'esm': n.lower().endswith('.esm'),
                         'masters': [], 'author': '', 'description': '', 'records': 0, 'active': True, 'mine': False, 'helper': False})
    rows = problems(in_game_order(rows))
    for r in rows:
        if r['mtime'] == float('inf'):
            r['mtime'] = 0
    n = 0
    for r in rows:
        if r['active'] and r['found']:
            r['slot'] = '%02X' % n
            n += 1
    notes = []
    if n > TOO_MANY:
        notes.append('%d plugins are on. New Vegas tends to crash when it\'s loading many more than about %d, however good they are.' % (n, TOO_MANY))
    lo = loadout.current()
    if lo:
        notes.append('This is the MO2 profile %s, read only: change it in MO2.' % lo.title)
    elif not os.path.isfile(install.plugins_txt()):
        notes.append('The game hasn\'t written its list of plugins yet: run its launcher once. Saving here makes the list.')
    return {'rows': rows, 'plugins_txt': os.path.join(lo.folder, 'plugins.txt') if lo else install.plugins_txt(), 'loadout': lo.title if lo else None, 'data': data_dir, 'on': n, 'notes': notes, 'backups': backups()}


# ---------- a change, at the user's asking ----------

def backups():
    d = backups_dir()
    if not os.path.isdir(d):
        return []
    out = [f for f in os.listdir(d) if f.endswith(' load order.json')]
    return sorted(out, reverse=True)[:30]


def take_backup(data_dir):
    """A copy of plugins.txt and of every plugin's date, in FOLab's backups folder. Returns its name."""
    d = backups_dir()
    os.makedirs(d, exist_ok=True)
    n = 0
    while True:                     # (two in one second still sort in the order they were taken)
        name = '%s %02d load order.json' % (time.strftime('%Y-%m-%d %H%M%S'), n)
        if not os.path.exists(os.path.join(d, name)):
            break
        n += 1
    txt = install.plugins_txt()
    data = {'taken': time.time(), 'plugins_txt': _read_raw(txt), 'times': {r['name']: r['mtime'] for r in scan_files(data_dir).values()}}
    with open(os.path.join(d, name), 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=1)
    return name


def _read_raw(path):
    try:
        with open(path, encoding='cp1252', errors='surrogateescape', newline='') as f:
            return f.read()
    except OSError:
        return None


def check_order(files, order):
    """The order the game will really use: the game's own master first, masters before plugins, the rest as asked."""
    names = [n for n in order if n.lower() in files]
    seen = {n.lower() for n in names}
    # (a file the request didn't mention stays, at its own date's place at the end of its kind)
    rest = [r['name'] for r in in_game_order(files.values()) if r['name'].lower() not in seen]
    names += rest
    official = [n for n in names if n.lower() in OFFICIAL]
    official.sort(key=lambda n: _rank(files[n.lower()]))    # (the game's own files keep their order: their dates aren't ours)
    masters = [n for n in names if n.lower() not in OFFICIAL and files[n.lower()]['esm']]
    plugins = [n for n in names if n.lower() not in OFFICIAL and not files[n.lower()]['esm']]
    return official + masters + plugins


def _dates(files, final):
    """{name: new date} giving the order, moving as few files as possible."""
    out = {}
    last = -1.0
    plugins = False
    for n in final:
        r = files[n.lower()]
        if not r['esm'] and not plugins:    # (plugins sort only among themselves: no need to pass the masters' dates)
            plugins, last = True, -1.0
        if r['official']:
            last = max(last, r['mtime'])
        elif r['mtime'] > last:
            last = r['mtime']
        else:
            last = float(int(last) + STEP)
            out[n] = last
    return out


def save(data_dir, order, active):
    """Write the load order: active (names) goes in plugins.txt, order (names) into the files' dates. A copy of how
    things were is kept first. Nothing is written when nothing changes."""
    loadout.refuse_writes('Saving the load order')
    if not order:
        raise ValueError('There\'s no load order to save: nothing was read yet.')     # (never an empty list by accident)
    files = scan_files(data_dir)
    final = check_order(files, order)
    lines = _txt_lines()
    was = active_names(lines)
    want = {n.lower() for n in active} | {BASE}
    helper = [n for n in was if n.lower() == HELPER]
    keep_comments = [l for l in lines if l.lstrip().startswith('#')]
    new_active = [n for n in final if n.lower() in want and n.lower() != HELPER and (n.lower() != BASE or any(x.lower() == BASE for x in was))] + helper
    new_active += [n for n in active if n.lower() not in files and n.lower() in {x.lower() for x in was}]   # (kept: its file may come back)
    dates = _dates(files, final)
    txt_changed = [n.lower() for n in new_active] != [n.lower() for n in was]
    if not txt_changed and not dates:
        return {'changed': False, 'backup': None}
    backup = take_backup(data_dir)
    for n, t in dates.items():
        os.utime(os.path.join(data_dir, files[n.lower()]['name']), (t, t))
    if txt_changed:
        _write_txt(keep_comments + new_active)
    return {'changed': True, 'backup': backup, 'moved': sorted(dates), 'order': final}


def _write_txt(lines):
    path = install.plugins_txt()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='cp1252', errors='replace', newline='\r\n') as f:
        f.write('\n'.join(lines) + '\n')
    os.replace(tmp, path)


def restore(data_dir, name):
    """Put back a load order FOLab kept a copy of (keeping a copy of how things are now first)."""
    loadout.refuse_writes('Putting back a load order')
    path = os.path.join(backups_dir(), os.path.basename(name))
    with open(path, encoding='utf-8') as f:
        data = json.load(f)
    now = take_backup(data_dir)
    for fn, t in data['times'].items():
        p = os.path.join(data_dir, fn)
        if fn.lower() not in OFFICIAL and os.path.isfile(p) and abs(os.path.getmtime(p) - t) > 0.5:
            os.utime(p, (t, t))
    txt = install.plugins_txt()
    if data.get('plugins_txt') is None:
        if os.path.exists(txt):
            os.remove(txt)
    else:
        os.makedirs(os.path.dirname(txt), exist_ok=True)
        with open(txt, 'w', encoding='cp1252', errors='surrogateescape', newline='') as f:
            f.write(data['plugins_txt'])
    return {'backup': now}


def sorted_for_masters(data_dir, order, active):
    """The order with every plugin after its masters, moving as little as possible; and the masters that a switched-on
    plugin needs, switched on."""
    files = scan_files(data_dir)
    final = check_order(files, order)
    pos = {n.lower(): i for i, n in enumerate(final)}
    on = {n.lower() for n in active}
    # (switching on: a plugin that's on brings its masters)
    todo = [n for n in on if n in files]
    while todo:
        for m in files[todo.pop()]['masters']:
            if m.lower() in files and m.lower() not in on:
                on.add(m.lower())
                todo.append(m.lower())
    done, out, stack = set(), [], set()

    def place(low):
        if low in done or low in stack or low not in files:
            return
        stack.add(low)
        for m in sorted(files[low]['masters'], key=lambda m: pos.get(m.lower(), 0)):
            place(m.lower())
        stack.discard(low)
        done.add(low)
        out.append(files[low]['name'])
    for n in final:
        place(n.lower())
    return {'order': check_order(files, out), 'active': [files[n]['name'] for n in on if n in files]}


# ---------- who changes what ----------

_index = {}     # (path, size, date) -> {(owning file, object ID): (type, offset of its record)}


def _forms_of(path):
    st = os.stat(path)
    k = (path, st.st_size, st.st_mtime)
    if k not in _index:
        pf = tes4.PluginFile(path)
        try:
            m = [x.lower() for x in pf.header['masters']]
            me = os.path.basename(path).lower()
            own = len(m)
            forms = {}
            for rec, _g in pf.walk():
                i = rec.formid >> 24
                forms[(m[i] if i < own else me, rec.formid & 0xFFFFFF)] = (rec.tag, rec.offset)
            _index[k] = forms
        finally:
            pf.close()
    return _index[k]


def mods_on(data_dir):
    """Paths of the switched-on plugins that aren't the game's own, in load order."""
    out = []
    for r in read(data_dir)['rows']:
        if r['active'] and r['found'] and not r['official'] and not r['helper'] and not r.get('error'):
            out.append(loadout.plugin_path(data_dir, r['name']))
    return out


def _edid(pf, rec):
    for t, d in tes4.iter_subrecords(pf.data(rec)):
        if t == 'EDID':
            return tes4.zstr(d)
    return ''


def conflicts(data_dir, paths=None):
    """Where two switched-on mods change the same thing and don't say the same about it. Each row: the thing, every
    mod that has it, and the one that wins (loaded last). A cell or world both only carry to reach what's inside isn't
    a conflict; what's inside can be."""
    paths = mods_on(data_dir) if paths is None else paths
    seen = {}
    for p in paths:
        for k, (tag, off) in _forms_of(p).items():
            seen.setdefault(k, []).append((p, tag, off))
    rows, by_mod, total = [], {}, 0
    files = {p: tes4.PluginFile(p) for p in paths}
    try:
        for (owner, low), who in seen.items():
            if len(who) < 2:
                continue
            copies = []
            for p, tag, off in who:
                pf = files[p]
                rec = pf.record_at(off)
                copies.append((p, recdiff.normal(pf, rec), rec.flags & ~tes4.COMPRESSED, rec))
            if all(c[1] == copies[0][1] and c[2] == copies[0][2] for c in copies[1:]):
                continue
            total += 1
            win = os.path.basename(who[-1][0])
            for p, _t, _o in who:
                n = os.path.basename(p)
                s = by_mod.setdefault(n, {'wins': 0, 'loses': 0})
                s['wins' if n == win else 'loses'] += 1
            if len(rows) < LIMIT:
                tag = who[0][1]
                edid = ''
                for c, (p, _t, _o) in zip(copies, who):
                    edid = edid or _edid(files[p], c[3])
                rows.append({'key': '%s:%06X' % (_real_name(owner, data_dir), low), 'type': tag, 'edid': edid, 'parent': tag in PARENTS,
                             'mods': [os.path.basename(p) for p, _t, _o in who], 'wins': win})
    finally:
        for pf in files.values():
            pf.close()
    rows.sort(key=lambda r: (r['parent'], r['type'], r['edid'].lower()))
    return {'rows': rows, 'total': total, 'by_mod': by_mod}


def _real_name(low, data_dir):
    for fn in loadout.plugin_names(data_dir):
        if fn.lower() == low:
            return fn
    return low


def who_wins(data_dir, key, gd=None):
    """Every copy of one form in load order, each with how it differs from the one before: the last one is what the
    game uses."""
    file_name, low = key.rsplit(':', 1)
    owner, low = file_name.lower(), int(low, 16)
    out = []
    prev = None
    if gd is not None and owner in gd.names:
        fid = (gd.names.index(owner) << 24) | low
        e = gd.forms.get(fid)
        if e:
            pf, rec = gd.plugins[e[0]], e[1]
            prev = recdiff.lines(rec.tag, list(tes4.iter_subrecords(pf.data(rec))), lambda v: recdiff.link_text(pf, v))
            out.append({'plugin': os.path.basename(pf.path), 'game': True, 'changes': []})
    for p in mods_on(data_dir):
        at = _forms_of(p).get((owner, low))
        if not at:
            continue
        pf = tes4.PluginFile(p)
        try:
            rec = pf.record_at(at[1])
            now = recdiff.lines(rec.tag, list(tes4.iter_subrecords(pf.data(rec))), lambda v: recdiff.link_text(pf, v))
            out.append({'plugin': os.path.basename(p), 'game': False, 'deleted': bool(rec.flags & tes4.DELETED),
                        'changes': recdiff.diff(prev, now) if prev is not None else [{'label': a, 'old': None, 'new': b} for a, b in now]})
            prev = now
        finally:
            pf.close()
    for c in out:
        c['wins'] = False
    if out:
        out[-1]['wins'] = True
    return {'key': key, 'copies': out}


