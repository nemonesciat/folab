"""FOLab's backups folder kept from filling the drive.

Everything FOLab copies before changing something goes into <home>/backups: the old plugin and plugins.txt each Put in
game (install._backup, one 107 MB Waikiki.esp a time), MO2's lists (mo2write), load orders (loadorder.take_backup), game
settings (gameini), old copies moved out of the game (copies), and the copies of a mod made before a big job ("<mod>
before <job> MMDD-HHMM"). Nothing ever deleted them: 13 GB in FOLab.exe's home on 20 Nov 2026, with C: nearly full.

Each entry is put in a kind by its name with the time taken out ('plugins.txt', 'Waikiki before ...'). The rules, per
kind: keep the newest KEEP, and the newest of each day for DAYS days; then, over all of them, the oldest go until the
folder is under the size cap. The newest of every kind always stays, and so does anything newer than FRESH (a copy may
still be being written).

Automatic tidying (after each backup FOLab makes itself) only touches the kinds FOLab makes on its own, whose copies are
many and alike (AUTO: replaced files, MO2's lists, load orders, game settings). Copies of a mod made before a job, and old
copies moved out of the game, go only when the user asks on the Backups card, which shows first what would go. Entries
without a time in their name (`<plugin> distant land`, which Take out restores from) are never touched.
"""
import os
import re
import shutil
import threading
import time
import json

import project

KEEP = 5
DAYS = 7
CAP_GB = 10.0
FRESH = 3600.0

# (the times FOLab and its users write into names)
_FULL = re.compile(r'(\d{4})-(\d{2})-(\d{2}) (\d{2})(\d{2})(\d{2})?(?: \d{1,2})?')    # 2026-11-20 074510 [2]
_SHORT = re.compile(r'(?<!\d)(\d{2})(\d{2})-(\d{2})(\d{2})$')                          # ... 1120-1253
_PAREN = re.compile(r' \(\d+\)$')

AUTO = ('file', 'load order', 'game settings')


def folder():
    return os.path.join(project.HOME, 'backups')


def settings():
    """The rules as the user set them on the card (folab_settings.json), else the defaults."""
    try:
        with open(os.path.join(project.HOME, 'folab_settings.json'), encoding='utf-8') as f:
            s = json.load(f)
    except (OSError, ValueError):
        s = {}
    return {'keep': int(s.get('backups_keep', KEEP)), 'days': int(s.get('backups_days', DAYS)),
            'cap_gb': float(s.get('backups_cap_gb', CAP_GB)), 'auto': bool(s.get('backups_auto', True))}


def classify(name, now=None):
    """(kind, label, family, when) for an entry's name; when is None for one with no time in its name (never pruned).
    family: 'file' (a file FOLab replaced), 'load order', 'game settings', 'mod' (a copy of a mod before a job),
    'moved' (old copies moved out of the game), 'other'."""
    now = now or time.time()
    base = _PAREN.sub('', name)
    m = _FULL.search(base)
    when = None
    if m:
        y, mo, d, h, mi, s = (int(g) if g else 0 for g in m.groups())
        try:
            when = time.mktime((y, mo, d, h, mi, s, 0, 0, -1))
        except (OverflowError, ValueError):
            when = None
        rest = (base[:m.start()] + base[m.end():]).strip()
    else:
        m = _SHORT.search(base)
        if m:
            mo, d, h, mi = (int(g) for g in m.groups())
            year = time.localtime(now).tm_year
            try:
                when = time.mktime((year, mo, d, h, mi, 0, 0, 0, -1))
                if when > now + 86400:                   # (December's copy read in January)
                    when = time.mktime((year - 1, mo, d, h, mi, 0, 0, 0, -1))
            except (OverflowError, ValueError):
                when = None
            rest = base[:m.start()].strip()
        else:
            rest = base
    low = rest.lower()
    if when is None:
        return rest, rest, 'other', None
    if low.endswith('load order.json'):
        return 'load order', 'Load orders', 'load order', when
    if low.startswith('game settings'):
        return 'game settings', 'Game settings', 'game settings', when
    if ' old copies' in low or 'loose files from data' in low:
        return rest, rest, 'moved', when
    if ' before ' in ' ' + low or low.startswith('before '):
        mod = rest.split(' before ')[0] if ' before ' in rest else rest
        k = mod + ' before ...'
        return k, '%s before a big job' % mod, 'mod', when
    if m and m.re is _FULL and m.start() == 0:           # '<time> Waikiki.esp': a file Put in game replaced
        return 'file', rest, 'file', when
    return rest, rest, 'other', when


def _size(path):
    if os.path.isfile(path):
        try:
            return os.path.getsize(path)
        except OSError:
            return 0
    n = 0
    for root, _dirs, files in os.walk(path):
        for f in files:
            try:
                n += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass
    return n


def entries(now=None):
    """Every entry in the backups folder: [{name, kind, label, family, when, size, folder}], newest first."""
    d = folder()
    if not os.path.isdir(d):
        return []
    out = []
    for name in os.listdir(d):
        p = os.path.join(d, name)
        kind, label, family, when = classify(name, now)
        if family == 'file':
            kind = 'file:' + label.lower()
        out.append({'name': name, 'kind': kind, 'label': label, 'family': family, 'when': when,
                    'size': _size(p), 'folder': os.path.isdir(p)})
    out.sort(key=lambda e: -(e['when'] or 0))
    return out


def plan(rules=None, only_auto=False, now=None, items=None):
    """Which entries would go: (gone, kept), lists of entries. only_auto: just the kinds FOLab makes on its own."""
    rules = rules or settings()
    now = now or time.time()
    items = entries(now) if items is None else items
    may = [e for e in items if e['when'] is not None and (not only_auto or e['family'] in AUTO)]
    by_kind = {}
    for e in may:
        by_kind.setdefault(e['kind'], []).append(e)
    keep, gone = set(), []
    for kind, es in by_kind.items():
        es.sort(key=lambda e: -e['when'])
        days = set()
        for i, e in enumerate(es):
            day = time.strftime('%Y-%m-%d', time.localtime(e['when']))
            if i < max(1, rules['keep']) or now - e['when'] < FRESH:
                keep.add(e['name'])
                days.add(day)
            elif now - e['when'] < rules['days'] * 86400 and day not in days:
                keep.add(e['name'])
                days.add(day)
            else:
                gone.append(e)
    # then the size cap, oldest first, over everything that may go, never the newest of a kind
    cap = rules['cap_gb'] * 1024 ** 3
    total = sum(e['size'] for e in items if e['name'] not in {g['name'] for g in gone})
    if total > cap:
        newest = {es[0]['name'] for es in by_kind.values()}
        for e in sorted((e for e in may if e['name'] in keep), key=lambda e: e['when']):
            if total <= cap:
                break
            if e['name'] in newest or now - e['when'] < FRESH:
                continue
            keep.discard(e['name'])
            gone.append(e)
            total -= e['size']
    gone_names = {g['name'] for g in gone}
    return gone, [e for e in items if e['name'] not in gone_names]


def delete(names):
    """Delete these entries of the backups folder (by name, nothing outside it). Returns how many bytes went."""
    d = os.path.normcase(os.path.abspath(folder()))
    freed = 0
    for n in names:
        p = os.path.abspath(os.path.join(d, os.path.basename(n)))
        if os.path.normcase(os.path.dirname(p)) != d or not os.path.exists(p):
            continue
        s = _size(p)
        try:
            if os.path.isdir(p):
                shutil.rmtree(p)
            else:
                os.remove(p)
            freed += s
        except OSError:
            pass
    return freed


def tidy(only_auto=False, rules=None):
    gone, _kept = plan(rules, only_auto=only_auto)
    return {'deleted': [g['name'] for g in gone], 'freed': delete([g['name'] for g in gone])}


_busy = threading.Lock()


def after_backup():
    """Called after FOLab makes a backup of its own: tidies the automatic kinds in the background, if the user lets it."""
    if not settings()['auto'] or not _busy.acquire(blocking=False):
        return

    def work():
        try:
            tidy(only_auto=True)
        except Exception:          # (tidying must never stop the change the backup was made for)
            pass
        finally:
            _busy.release()
    threading.Thread(target=work, daemon=True).start()


def page(now=None):
    """What the Backups card shows: kinds with their entries and sizes, what tidying would delete, the rules, the drive."""
    now = now or time.time()
    items = entries(now)
    rules = settings()
    gone, _ = plan(rules, now=now, items=items)
    auto_gone, _ = plan(rules, only_auto=True, now=now, items=items)
    goes = {g['name'] for g in gone}
    kinds = {}
    for e in items:
        k = kinds.setdefault(e['kind'], {'kind': e['kind'], 'label': e['label'] if e['family'] != 'file' else e['label'],
                                         'family': e['family'], 'size': 0, 'items': []})
        k['size'] += e['size']
        k['items'].append(dict(e, goes=e['name'] in goes))
    try:
        du = shutil.disk_usage(folder() if os.path.isdir(folder()) else project.HOME)
        drive = {'free': du.free, 'total': du.total}
    except OSError:
        drive = None
    return {'folder': folder(), 'rules': rules, 'total': sum(e['size'] for e in items),
            'kinds': sorted(kinds.values(), key=lambda k: -k['size']),
            'would_free': sum(g['size'] for g in gone), 'would_delete': len(gone),
            'auto_would_free': sum(g['size'] for g in auto_gone), 'drive': drive}
