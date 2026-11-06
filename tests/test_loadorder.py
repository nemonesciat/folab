import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import struct, time, json, shutil

HOME = os.environ['FOLAB_HOME']
FAKE = os.path.join(HOME, 'fake game', 'Data')
LOCAL = os.path.join(HOME, 'fake local')
os.makedirs(FAKE)
os.makedirs(LOCAL)
REAL_LOCAL = os.environ.get('LOCALAPPDATA', '')
os.environ['LOCALAPPDATA'] = LOCAL              # (never the real plugins.txt)
import install, loadorder, plugintree, tes4


def check(what, ok, extra=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' ' + str(extra) if extra != '' and not ok else ''))


def sub(tag, data):
    return struct.pack('<4sH', tag.encode(), len(data)) + data


def plugin(name, masters, records, esm=False, when=None):
    """A small plugin in the fake Data folder. records: (type, form ID, subrecord bytes)."""
    head = sub('HEDR', struct.pack('<fiI', 1.34, len(records), 0x900)) + sub('CNAM', b'test\0')
    for m in masters:
        head += sub('MAST', m.encode() + b'\0') + sub('DATA', b'\0' * 8)
    tree = plugintree.Plugin.empty(head, 1 if esm else 0)
    for tag, fid, data in records:
        top = tree.top(tag)
        top.kids.append(plugintree.Rec.new(tag, 0, fid, data))
    path = os.path.join(FAKE, name)
    with open(path, 'wb') as f:
        f.write(tree.bytes())
    if when:
        os.utime(path, (when, when))
    return path


def write_txt(lines):
    os.makedirs(os.path.join(LOCAL, 'FalloutNV'), exist_ok=True)
    with open(install.plugins_txt(), 'w', encoding='cp1252', newline='\r\n') as f:
        f.write('\n'.join(lines) + '\n')


edid = lambda s: sub('EDID', s.encode() + b'\0')
T0 = 1200000000
plugin('FalloutNV.esm', [], [('MISC', 0x000900, edid('Base') + sub('DATA', struct.pack('<if', 5, 1.0))),
                             ('MISC', 0x000901, edid('Other') + sub('DATA', struct.pack('<if', 6, 1.0)))], esm=True, when=T0)
plugin('DeadMoney.esm', ['FalloutNV.esm'], [], esm=True, when=T0 + 100)
m = lambda v: edid('Base') + sub('DATA', struct.pack('<if', v, 1.0))
plugin('Alpha.esp', ['FalloutNV.esm'], [('MISC', 0x000900, m(10))], when=T0 + 500)
plugin('Bravo.esp', ['FalloutNV.esm'], [('MISC', 0x000900, m(20)), ('MISC', 0x000901, edid('Other') + sub('DATA', struct.pack('<if', 6, 1.0)))], when=T0 + 600)
plugin('Same.esp', ['FalloutNV.esm'], [('MISC', 0x000901, edid('Other') + sub('DATA', struct.pack('<if', 6, 1.0)))], when=T0 + 650)
plugin('Lib.esm', ['FalloutNV.esm'], [('MISC', 0x010800, edid('LibThing'))], esm=True, when=T0 + 200)
plugin('Needy.esp', ['FalloutNV.esm', 'Lib.esm'], [], when=T0 + 700)
plugin('Lost.esp', ['FalloutNV.esm', 'GoneMod.esm'], [], when=T0 + 800)
plugin('Off.esp', ['FalloutNV.esm'], [], when=T0 + 900)
write_txt(['# This file is used by the game', 'FalloutNV.esm', 'DeadMoney.esm', 'Alpha.esp', 'Bravo.esp', 'Same.esp', 'Needy.esp', 'Lost.esp', 'Vanished.esp'])

times0 = {f: os.path.getmtime(os.path.join(FAKE, f)) for f in os.listdir(FAKE)}
with open(install.plugins_txt(), 'rb') as f:
    txt0 = f.read()

# ---------- reading changes nothing ----------
r = loadorder.read(FAKE, 'Alpha.esp')
names = [x['name'] for x in r['rows']]
row = {x['name']: x for x in r['rows']}
print('  order:', names)
check('reading changes no file', txt0 == open(install.plugins_txt(), 'rb').read() and
      times0 == {f: os.path.getmtime(os.path.join(FAKE, f)) for f in os.listdir(FAKE)})
check('the game\'s master first, masters before plugins', names[:3] == ['FalloutNV.esm', 'DeadMoney.esm', 'Lib.esm'])
check('plugins by date', names.index('Alpha.esp') < names.index('Bravo.esp') < names.index('Off.esp'))
check('on and off from plugins.txt', row['Alpha.esp']['active'] and not row['Off.esp']['active'])
check('your mod is marked', row['Alpha.esp']['mine'])
check('a master switched off is a problem', any('switched off' in p for p in row['Needy.esp']['problems']))
check('a master that isn\'t there is a problem', any('GoneMod.esm' in p for p in row['Lost.esp']['problems']))
check('a listed plugin with no file is a problem', row['Vanished.esp']['problems'] and not row['Vanished.esp']['found'])

# ---------- a change: dates and the list, a backup first ----------
order = ['FalloutNV.esm', 'DeadMoney.esm', 'Lib.esm', 'Bravo.esp', 'Alpha.esp', 'Same.esp', 'Needy.esp', 'Lost.esp', 'Off.esp']
active = [x['name'] for x in r['rows'] if x['active']] + ['Off.esp']
out = loadorder.save(FAKE, order, active)
check('saved with a backup', out['changed'] and out['backup'] in loadorder.backups())
again = loadorder.read(FAKE)
names2 = [x['name'] for x in again['rows']]
check('the new order is what the game would load', names2.index('Bravo.esp') < names2.index('Alpha.esp'), names2)
check('switched on', {x['name']: x for x in again['rows']}['Off.esp']['active'])
for f in ('FalloutNV.esm', 'DeadMoney.esm'):
    check('%s keeps its date' % f, os.path.getmtime(os.path.join(FAKE, f)) == times0[f])
listed = loadorder.active_names()
check('plugins.txt keeps its comment', open(install.plugins_txt(), encoding='cp1252').readline().startswith('#'))
check('plugins.txt lists them', [n for n in listed if n != 'Vanished.esp'][:3] == ['FalloutNV.esm', 'DeadMoney.esm', 'Bravo.esp'], listed)
check('saving the same again writes nothing', not loadorder.save(FAKE, names2, [x['name'] for x in again['rows'] if x['active']])['changed'])
# (the real file was never in play)
check('the real plugins.txt wasn\'t the one used', not REAL_LOCAL or not install.plugins_txt().startswith(REAL_LOCAL))

# masters first, whatever was asked
out = loadorder.save(FAKE, ['Bravo.esp', 'Lib.esm', 'FalloutNV.esm', 'DeadMoney.esm', 'Alpha.esp'], listed)
check('a master can\'t be put after a plugin', out.get('order', [''])[:3] == ['FalloutNV.esm', 'DeadMoney.esm', 'Lib.esm'] or
      [x['name'] for x in loadorder.read(FAKE)['rows']][:3] == ['FalloutNV.esm', 'DeadMoney.esm', 'Lib.esm'])

# ---------- fix master order ----------
plugin('MasterLast.esm', ['FalloutNV.esm', 'Lib2.esm'], [], esm=True, when=T0 + 300)
plugin('Lib2.esm', ['FalloutNV.esm'], [], esm=True, when=T0 + 400)
cur = loadorder.read(FAKE)
check('a master loading after what needs it is a problem', cur and any('loads after' in p for x in cur['rows'] if x['name'] == 'MasterLast.esm' for p in (x['problems'] or [])) or
      not {x['name']: x for x in cur['rows']}['MasterLast.esm']['active'])
fixed = loadorder.sorted_for_masters(FAKE, [x['name'] for x in cur['rows']], [x['name'] for x in cur['rows'] if x['active']] + ['MasterLast.esm'])
check('sorting puts masters first', fixed['order'].index('Lib2.esm') < fixed['order'].index('MasterLast.esm'), fixed['order'])
check('switching on brings masters', 'Lib2.esm' in fixed['active'])
loadorder.save(FAKE, fixed['order'], fixed['active'])
cur = loadorder.read(FAKE)
check('and saved, no problem left there', not {x['name']: x for x in cur['rows']}['MasterLast.esm']['problems'])

# ---------- conflicts ----------
c = loadorder.conflicts(FAKE)
print('  conflicts:', c['rows'])
rows = {x['edid']: x for x in c['rows']}
check('two mods saying different things conflict', 'Base' in rows and set(rows['Base']['mods']) == {'Alpha.esp', 'Bravo.esp'})
check('two mods saying the same thing don\'t', 'Other' not in rows)
wins = rows['Base']['wins']
order_now = [x['name'] for x in cur['rows']]
check('the one loaded last wins', wins == max(['Alpha.esp', 'Bravo.esp'], key=order_now.index))
w = loadorder.who_wins(FAKE, rows['Base']['key'])
print('  who wins:', w)
check('every copy listed, the last the winner', [x['plugin'] for x in w['copies']][-1] == wins and w['copies'][-1]['wins'])
check('the difference from the one before is shown', any('Value' in str(ch) or ch['label'] for ch in w['copies'][-1]['changes']))

# ---------- back as it was ----------
first = sorted(loadorder.backups())[0]
loadorder.restore(FAKE, first)
check('restore: plugins.txt back', txt0 == open(install.plugins_txt(), 'rb').read())
check('restore: dates back', all(abs(os.path.getmtime(os.path.join(FAKE, f)) - t) < 1 for f, t in times0.items()))
check('restore keeps a copy of how things were', len(loadorder.backups()) >= 2)

# ---------- a Data folder with no list yet ----------
os.remove(install.plugins_txt())
n = loadorder.read(FAKE)
check('no plugins.txt: read says so', any('launcher' in x for x in n['notes']))
check('only ever the fake folder', os.path.dirname(os.path.dirname(install.plugins_txt())) == LOCAL)

# ---------- a master of another mod is loaded under the plugin ----------
import adopt
got = adopt.extra_masters(FAKE, os.path.join(FAKE, 'Needy.esp'))
check('another mod a plugin needs is loaded under it', [os.path.basename(p) for p in got] == ['Lib.esm'], got)

# ---------- merging: every link keeps pointing at the same thing (the real game's files, read only) ----------
os.environ.pop('FOLAB_NV_DATA', None)
import copy
import espwrite, formlinks, gamedata, health, masterlist, merge, project, recordio
gd = gamedata.GameData()
hh_src = os.path.join(gd.data_dir, 'HonestHearts.esm')


def spelled_links(path, skip=()):
    """{(owning file, object ID): (type, cell's (file, ID) or None, [(file, ID) of each link])} for a plugin."""
    pf = tes4.PluginFile(path)
    m = [x.lower() for x in pf.header['masters']]
    me = os.path.basename(path).lower()
    own = len(m)
    sp = lambda v: (m[v >> 24] if v >> 24 < own else me if v >> 24 == own else '?', v & 0xFFFFFF)
    out = {}
    for rec, groups in pf.walk():
        cell = next((sp(l) for gt, l, _o in reversed(groups) if gt in formlinks.LABEL_IS_FORM), None)
        subs = list(tes4.iter_subrecords(pf.data(rec)))
        out[sp(rec.formid)] = (rec.tag, cell, [sp(v) for _n, _o, v in formlinks.values(rec.tag, subs, own)])
    pf.close()
    return out


def carried(old_name, new_name, renum):
    """How the old plugin's spelling of a form should read in the new one."""
    old_low, new_low = old_name.lower(), new_name.lower()
    return lambda k: (new_low, renum.get(k[1], k[1])) if k[0] == old_low else k


# a mod with its own records linking each other, and a place with things in it
by_tag = lambda tag: next(f for f, (i, r) in gd.forms.items() if r.tag == tag and f >> 24 == 0)
pr = project.Project.create('Mine')
w = copy.deepcopy(recordio.load(gd, by_tag('WEAP')))
a = copy.deepcopy(recordio.load(gd, by_tag('AMMO')))
recordio.set_field(a, 'EDID', 'MineAmmo')
recordio.set_field(w, 'EDID', 'MineGun')
[k_ammo] = pr.apply('a', [{'op': 'record_new', 'record': a}])
recordio.set_field(w, 'NAM0', k_ammo, kind='F', label='Ammo')
[k_gun] = pr.apply('w', [{'op': 'record_new', 'record': w}])
# (the other mod: saved by the same writer, so its object IDs collide with these)
other = project.Project.create('Theirs')
a2 = copy.deepcopy(recordio.load(gd, by_tag('AMMO')))
w2 = copy.deepcopy(recordio.load(gd, by_tag('WEAP')))
recordio.set_field(a2, 'EDID', 'TheirAmmo')
recordio.set_field(w2, 'EDID', 'TheirGun')
[k2_ammo] = other.apply('a', [{'op': 'record_new', 'record': a2}])
recordio.set_field(w2, 'NAM0', k2_ammo, kind='F', label='Ammo')
other.apply('w', [{'op': 'record_new', 'record': w2}])
changed = recordio.load(gd, by_tag('MISC'))
changed['subs'][0]['value'] = 'TheirEdit'
other.apply('m', [{'op': 'record', 'key': gd.key(by_tag('MISC')), 'record': changed}])
theirs_path = os.path.join(HOME, 'Theirs.esp')
espwrite.write(gd, other, theirs_path)
mine_edit = recordio.load(gd, by_tag('MISC'))
mine_edit['subs'][0]['value'] = 'MineEdit'
pr.apply('m', [{'op': 'record', 'key': gd.key(by_tag('MISC')), 'record': mine_edit}])

data, rep = merge.write_merged(gd, pr, theirs_path)
out_path = os.path.join(HOME, 'Mine.esp')
open(out_path, 'wb').write(data)
got = spelled_links(out_path)
check('collisions renumbered', rep['renumbered'] == 2, rep)
find = lambda edid: next(k for k, v in got.items() if v[0] in ('WEAP', 'AMMO') and k[0] == 'mine.esp' and edid in _edids[k])
pf = tes4.PluginFile(out_path)
_edids = {}
for r, _g in pf.walk():
    _edids[('mine.esp', r.formid & 0xFFFFFF)] = tes4.zstr(dict(reversed(list(tes4.iter_subrecords(pf.data(r))))).get('EDID', b''))
pf.close()
gun = find('TheirGun')
check('their gun still uses their ammo', find('TheirAmmo') in got[gun][2], got[gun][2])
check('my gun still uses my ammo', find('MineAmmo') in got[find('MineGun')][2])
check('both guns are there, not one over the other', find('MineGun') != gun)
misc_low = ('falloutnv.esm', by_tag('MISC') & 0xFFFFFF)
pfo = plugintree.Plugin.read(out_path)
misc_rec = next(r for r, _p, _x in pfo.records() if r.tag == 'MISC' and r.formid >> 24 == 0)
check('where both change a record, mine stays unless asked', b'MineEdit' in misc_rec.data())
data2, rep2 = merge.write_merged(gd, pr, theirs_path, {'all': 'theirs'})
open(out_path, 'wb').write(data2)
pfo = plugintree.Plugin.read(out_path)
check('and theirs when asked', b'TheirEdit' in next(r for r, _p, _x in pfo.records() if r.tag == 'MISC' and r.formid >> 24 == 0).data())

# a whole real plugin's worth: Honest Hearts as if it were a mod
big = os.path.join(HOME, 'HHAsAMod.esm')
shutil.copyfile(hh_src, big)
before = spelled_links(big)
pr2 = project.Project.create('Bigger')
pr2.apply('a', [{'op': 'record_new', 'record': copy.deepcopy(a)}])
data, rep = merge.write_merged(gd, pr2, big)
merged = os.path.join(HOME, 'Bigger.esp')
open(merged, 'wb').write(data)
after = spelled_links(merged)
to = carried('HHAsAMod.esm', 'Bigger.esp', rep['renum'])
wrong_links = wrong_cell = gone = 0
for k, (tag, cell, links) in before.items():
    now = after.get(to(k))
    if now is None:
        gone += 1
        continue
    if tag != 'NAVI' and [to(x) for x in links] != now[2]:
        wrong_links += 1
    if cell is not None and to(cell) != now[1]:
        wrong_cell += 1
print('  merged', len(before), 'records,', rep['renumbered'], 'renumbered')
check('merged: every record came across', gone == 0, gone)
check('merged: every link in every record points at the same thing', wrong_links == 0, wrong_links)
check('merged: everything is in the same place it was', wrong_cell == 0, wrong_cell)
check('merged: one group for each place: reads back as a plugin', len(after) >= len(before))
g2 = gamedata.GameData(plugins=[p.path for p in gd.plugins] + [merged])
look = health.check_file(g2, merged)
n = {x['kind']: x['count'] for x in look['groups']}
check('merged: hardly a dead link, as the game has it', n.get('link', 0) < 30, n)
for p in g2.plugins:
    p.close()
os.remove(big)

# ---------- a plugin's masters grow: an opened plugin uses something from another file ----------
dm = os.path.join(HOME, 'DMAsAMod.esm')
shutil.copyfile(os.path.join(gd.data_dir, 'DeadMoney.esm'), dm)
old = spelled_links(dm)
name = adopt.adopt(gd, dm)
opened = project.Project.open(name)
g3 = gamedata.GameData(plugins=[p.path for p in gd.plugins] + [opened.source_path()])
me = len(g3.plugins) - 1
hh_i = g3.names.index('honesthearts.esm')
hh_stat = next(f for f, (i, r) in g3.forms.items() if r.tag == 'STAT' and i == hh_i and f >> 24 == hh_i)
own_cell = next(c for c in g3.interiors if c >> 24 == me)
[nk] = opened.apply('add', [{'op': 'add', 'cell': g3.key(own_cell), 'base': g3.key(hh_stat), 'p': [1, 2, 3, 0, 0, 0]}])
grown = os.path.join(HOME, 'Grown', 'DMAsAMod.esm')
os.makedirs(os.path.dirname(grown))
espwrite.write(g3, opened, grown)
pf = tes4.PluginFile(grown)
check('masters grew, in place, the new one last', [x.lower() for x in pf.header['masters']] == ['falloutnv.esm', 'honesthearts.esm'], pf.header['masters'])
own_after = len(pf.header['masters'])
check('header still counts right', pf.header['records'] == plugintree.Plugin.read(grown).count())
pf.close()
now = spelled_links(grown)
bad = sum(1 for k, v in old.items() if k not in now or v[2] != now[k][2] and v[0] != 'NAVI' or v[1] != now[k][1])
check('every link and place of the old plugin unchanged', bad == 0, bad)
new_ref = now[('dmasamod.esm', int(nk[1:], 16))]
check('the new thing\'s base is in the new master', ('honesthearts.esm', hh_stat & 0xFFFFFF) in new_ref[2], new_ref)
for p in g3.plugins:
    p.close()
g4 = gamedata.GameData(plugins=[p.path for p in gd.plugins] + [grown])
f = g4.fields(own_cell & 0xFFFFFF | (len(g4.plugins) - 1) << 24)
check('the game\'s reader finds its own cell after the change', 'EDID' in f or 'DATA' in f)
for p in g4.plugins:
    p.close()

# ---------- the masters nothing uses ----------
tree = plugintree.Plugin.read(grown)
check('every kind of record in a real plugin is known', not masterlist.unknown_types(tree), masterlist.unknown_types(tree))
masterlist.set_masters(tree, ['FalloutNV.esm', 'HonestHearts.esm'])
check('used: both are', masterlist.used_masters(tree) == [True, True])

# ---------- a record copied from an add-on: links in the parts no layout reads come along right ----------
hh_i = gd.names.index('honesthearts.esm')
hh = gd.plugins[hh_i]
pick = None
for rec, _g in hh.walk():
    if rec.tag != 'PACK' or rec.formid >> 24 != 1:
        continue
    subs = list(tes4.iter_subrecords(hh.data(rec)))
    raw = [(n, o, v) for n, o, v in formlinks.values(rec.tag, subs, 1) if v >> 24 == 1 and subs[n][0] in ('CTDA', 'PLDT', 'PTDT')]
    if raw:
        pick = (rec, subs, raw)
        break
check('an add-on record with such a link to test with', pick is not None)
rec, subs, raw = pick
fid = (hh_i << 24) | (rec.formid & 0xFFFFFF)
kept = project.Project.create('Copied')
dm_form = next(f for f, (i, r) in gd.forms.items() if r.tag == 'STAT' and f >> 24 == gd.names.index('deadmoney.esm'))
own_cell = next(c for c in gd.interiors if c >> 24 == 0)
kept.apply('c', [{'op': 'record', 'key': gd.key(fid), 'record': recordio.load(gd, fid)},
                 {'op': 'add', 'cell': gd.key(own_cell), 'base': gd.key(dm_form), 'p': [0, 0, 0, 0, 0, 0]}])
path = os.path.join(HOME, 'Copied.esp')
espwrite.write(gd, kept, path)
pf = tes4.PluginFile(path)
check('the copy has the add-on one place further down its masters', [m.lower() for m in pf.header['masters']].index('honesthearts.esm') == 2, pf.header['masters'])
now = next(r for r, _g in pf.walk() if r.tag == 'PACK')
want = [(m, o, v & 0xFFFFFF) for m, o, v in raw]
got = {(n, o): v for n, o, v in formlinks.values('PACK', list(tes4.iter_subrecords(pf.data(now))), len(pf.header['masters']))}
check('its links in raw parts now say the add-on\'s new place', all(got.get((n, o)) == (2 << 24 | low) for n, o, low in want), (want[:2], list(got.items())[:4]))
pf.close()

check('a listed plugin with no file stays listed when saving', 'Vanished.esp' in listed)
