"""FOLab's backups kept from filling the drive (backups.py): kinds by name, the rules (newest few, one a day, a size cap),
automatic tidying only of FOLab's own automatic kinds, entries without a time never touched, deleting nothing outside
the folder. A fake backups folder in the scratch home throughout."""
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import backups  # noqa: E402
import install  # noqa: E402
import project  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


NOW = time.mktime((2026, 11, 20, 20, 0, 0, 0, 0, -1))
d = backups.folder()
os.makedirs(d, exist_ok=True)


def made(name, size=1000, folder=False):
    p = os.path.join(d, name)
    if folder:
        os.makedirs(p, exist_ok=True)
        p = os.path.join(p, 'Mod.json')
    with open(p, 'wb') as f:
        f.write(b'x' * size)


def stamp(days_ago, hours_ago=0.0):
    return time.strftime('%Y-%m-%d %H%M%S', time.localtime(NOW - days_ago * 86400 - hours_ago * 3600))


# ---- kinds by name
k = backups.classify('2026-11-20 074510 Waikiki.esp', NOW)
check('a replaced plugin is a file kind', k[2] == 'file' and k[1] == 'Waikiki.esp', k)
k = backups.classify('2026-11-20 074510 2 Waikiki.esp', NOW)
check('two in one second still the same kind', k[2] == 'file' and k[1] == 'Waikiki.esp', k)
check('load orders', backups.classify('2026-11-20 074510 00 load order.json', NOW)[2] == 'load order')
check('game settings', backups.classify('game settings 2026-11-20 074510 (2)', NOW)[2] == 'game settings')
k = backups.classify('Waikiki before the loot 1120-1448', NOW)
check('a mod before a job, by its short time', k[2] == 'mod' and k[0] == 'Waikiki before ...' and
      time.localtime(k[3])[:5] == (2026, 11, 20, 14, 48), k)
k = backups.classify('Waikiki before far trees 1231-2300', time.mktime((2027, 1, 2, 9, 0, 0, 0, 0, -1)))
check("December's copy read in January is last year's", time.localtime(k[3]).tm_year == 2026, k)
check('moved-out copies', backups.classify('Waikiki.esp old copies 2026-11-18 101010', NOW)[2] == 'moved')
check('no time, never tidied', backups.classify('Waikiki distant land', NOW)[3] is None)

# ---- the rules
for i in range(12):                                     # a replaced plugin every 2 hours over a day, then old ones
    made('%s Waikiki.esp' % stamp(0, 2 + i * 2), 100)
for days in (2, 3, 4, 10, 20):
    made('%s Waikiki.esp' % stamp(days), 100)
made('%s modlist.txt' % stamp(0, 5), 10)
for i, job in enumerate(['grass', 'loot', 'clubs', 'hats', 'towers', 'bamboo', 'trees']):
    made('Waikiki before %s %s' % (job, time.strftime('%m%d-%H%M', time.localtime(NOW - (i + 2) * 3600))), 500, folder=True)
made('Waikiki distant land', 50, folder=True)
made('%s Fresh.esp' % stamp(0, 0.2), 100)
made('%s Fresh.esp' % stamp(0, 0.1), 100)

rules = {'keep': 5, 'days': 7, 'cap_gb': 100.0, 'auto': True}
gone, kept = backups.plan(rules, now=NOW)
g = {e['name'] for e in gone}
plugins = [e for e in kept if e['kind'] == 'file:waikiki.esp']
check('newest 5 plugins kept, one a day for a week, older ones go',
      len(plugins) == 5 + 4 and not any(stamp(10) in n or stamp(20) in n for n in (e['name'] for e in plugins)),
      sorted(e['name'] for e in plugins))
check('the only modlist kept', not any('modlist' in n for n in g))
mods = [e for e in kept if e['family'] == 'mod']
check('mod copies: newest 5 of one day kept', len(mods) == 5, len(mods))
check('no time in its name: never goes', 'Waikiki distant land' not in g)
check('copies from the last hour stay', not any('Fresh' in n for n in g))

gone_a, _ = backups.plan(rules, only_auto=True, now=NOW)
check('by itself only the automatic kinds go', gone_a and all(e['family'] in backups.AUTO for e in gone_a))

# the cap: tiny, so everything that may go goes, but never the newest of a kind
gone_c, kept_c = backups.plan(dict(rules, cap_gb=0.000001), now=NOW)
newest = {}
for e in backups.entries(NOW):
    if e['when'] is not None and (e['kind'] not in newest or e['when'] > newest[e['kind']]['when']):
        newest[e['kind']] = e
check('under the cap the newest of each kind still stays', all(n['name'] in {e['name'] for e in kept_c} for n in newest.values()))

# ---- deleting
outside = os.path.join(project.HOME, 'not a backup.txt')
with open(outside, 'w') as f:
    f.write('keep me')
freed = backups.delete(['..\\not a backup.txt', os.path.join('..', 'not a backup.txt')])
check('nothing outside the backups folder is deleted', os.path.isfile(outside) and freed == 0)
before = len(os.listdir(d))
freed = backups.delete([e['name'] for e in gone])
check('the planned ones deleted, the size counted', len(os.listdir(d)) == before - len(gone) and freed > 0, (before, len(gone), freed))
check('folders deleted whole', not any(os.path.exists(os.path.join(d, e['name'])) for e in gone))

# ---- the page
p = backups.page(NOW)
check('page: kinds, total, rules, drive', p['kinds'] and p['total'] > 0 and p['rules']['keep'] == backups.KEEP and p['drive'])

# ---- automatic, after install's own backup; switched off by the setting
for i in range(9):
    made('%s Other.esp' % stamp(i + 30), 100)
src = os.path.join(project.HOME, 'Other.esp')
with open(src, 'wb') as f:
    f.write(b'y' * 100)
install._backup(src)
for _ in range(100):                                    # (the tidy runs in the background)
    if backups._busy.acquire(blocking=False):
        backups._busy.release()
        if len([n for n in os.listdir(d) if n.endswith('Other.esp')]) <= 6:
            break
    time.sleep(0.05)
left = [n for n in os.listdir(d) if n.endswith('Other.esp')]
check('a new backup tidies its kind by itself', len(left) == 5, sorted(left))

with open(os.path.join(project.HOME, 'folab_settings.json'), 'w') as f:
    json.dump({'backups_auto': False}, f)
for i in range(9):
    made('%s Third.esp' % stamp(i + 30), 100)
src = os.path.join(project.HOME, 'Third.esp')
with open(src, 'wb') as f:
    f.write(b'z' * 100)
install._backup(src)
time.sleep(0.5)
check('switched off: nothing tidied by itself', len([n for n in os.listdir(d) if n.endswith('Third.esp')]) == 10)
