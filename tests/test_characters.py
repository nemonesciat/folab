import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
"""The Characters page's records: a new character from a template with inventory, a faction and an AI package; packages'
location and target unions; faces; factions; Populate. Everything reads back from the written plugin with links
re-pointed and bytes laid out as the schema says."""
import json
import struct

import api_characters as ac
import browse
import espwrite
import gamedata
import populate
import project
import recordio
import schema
import tes4


def check(what, ok):
    print(('PASS ' if ok else 'FAIL ') + what)


gd = gamedata.GameData()
pr = project.Project.create('Characters Test')
br = browse.Browse(gd, lambda: pr)
find = lambda tag, e: next(f for f, (i, r) in gd.forms.items() if r.tag == tag and gd.edid(f) == e)


def edit(label, ops):
    return {'made': pr.apply(label, ops)}


# ---- every package's unions decode and encode back exactly, and a form means a form ----
recs, stats = schema.checkall(gd, ['PACK'])
for tag in ('PLDT', 'PLD2', 'PTDT', 'PTD2', 'PKDD', 'PKE2'):
    check('every %s in the game (%d) encodes back byte for byte' % (tag, stats['PACK'][tag][0]), stats['PACK'][tag][1] == 0 and stats['PACK'][tag][0] > 0)
bad = 0
for f, (i, r) in gd.forms.items():
    if r.tag != 'PACK':
        continue
    for t, d in tes4.iter_subrecords(gd.plugins[i].data(r)):
        if t in ('PLDT', 'PLD2', 'PTDT', 'PTD2'):
            s = schema.decode_sub('PACK', t, d)
            kind, v = struct.unpack_from('<iI', d)
            is_link = s['fields'][1]['code'] == 'F'
            gl = gd.to_global(i, v)
            if is_link and v and gl not in gd.forms and gl not in gd.ref_cell and v != 0x14:
                bad += 1
            if not is_link and v and t in ('PLDT', 'PLD2'):
                bad += 1
check('a union only reads as a link when it names a form (the player, 0x14, is made by the game)', bad == 0)

# ---- a new character from a template, with a faction, inventory and a package ----
tpl = ac.templates(gd)
check('the templates are all in the game', len(tpl['NPC_']) == len(ac.TEMPLATES['NPC_']) and len(tpl['CREA']) == len(ac.TEMPLATES['CREA']))
town = next(t for t in tpl['NPC_'] if t['label'] == 'Townsperson')
made = ac.new_character(gd, pr, br, edit, {'from': town['key'], 'name': 'Dusty Rhodes'})['made'][0]
rec = pr.records[made]
check('it has a name and an editor ID of its own', recordio.field(rec, 'FULL') == 'Dusty Rhodes' and recordio.field(rec, 'EDID') == 'FOLabDustyRhodes')
check('it comes with no script', not ac.one(rec, 'SCRI'))
check('its packages are only the game\'s general ones, none of its town\'s', ac.subs_of(rec, 'PKID') and all(recordio.field(ac.get_record(gd, pr, s['value']), 'EDID').startswith('Default') for s in ac.subs_of(rec, 'PKID')))

gun = find('WEAP', 'WeapNV357Revolver')
ncr = find('FACT', 'NCRFactionNV')
mine_fact = ac.new_faction(gd, pr, br, edit, {'name': 'Dust Devils'})['made'][0]
pack = ac.new_package(gd, pr, br, 'sandbox', 'Dusty Hangs Out', {'radius': 300})
pkey = edit('package', [{'op': 'record_new', 'record': pack}])['made'][0]
sleep = ac.new_package(gd, pr, br, 'sleep', 'Dusty Sleeps')
skey = edit('package', [{'op': 'record_new', 'record': sleep}])['made'][0]
follow = ac.new_package(gd, pr, br, 'follow', 'Dusty Follows')
fkey = edit('package', [{'op': 'record_new', 'record': follow}])['made'][0]

rec = json.loads(json.dumps(rec))
rec['subs'] = [s for s in rec['subs'] if s['tag'] not in ('PKID', 'CNTO', 'COED', 'SNAM')]
for fact, rank in ((gd.key(ncr), 2), (mine_fact, 0)):
    ac.insert(rec, {'tag': 'SNAM', 'label': 'Faction', 'kind': 'struct', 'fields': [{'name': 'Faction', 'code': 'F', 'value': fact}, {'name': 'Rank', 'code': 'b', 'value': rank}, {'pad': '000000'}]})
ac.insert(rec, {'tag': 'CNTO', 'label': 'Item', 'kind': 'struct', 'fields': [{'name': 'Item', 'code': 'F', 'value': gd.key(gun)}, {'name': 'Count', 'code': 'i', 'value': 3}]})
for k in (skey, pkey):
    ac.insert(rec, {'tag': 'PKID', 'label': 'AI package', 'kind': 'F', 'value': k})
for f, v in (('Aggression', 1), ('Confidence', 4), ('Mood', 5), ('Assistance', 2)):
    ac.set_num(rec, 'AIDT', f, v)
ac.set_num(rec, 'ACBS', 'Flags', (ac.num(rec, 'ACBS', 'Flags') | 0x80) & ~0x10)
ac.set_num(rec, 'ACBS', 'Level', 1250)
ac.set_num(rec, 'DATA', 'Strength', 9)
ac.set_num(rec, 'DNAM', 'Guns', 77)
edit('char', [{'op': 'record', 'key': made, 'record': rec}])

# a game package, in a DLC, whose links are numbered by its own file: through the mod and back
dlc = next(f for f, (i, r) in gd.forms.items() if r.tag == 'PACK' and i > 0 and 'PTDT' in gd.fields(f) and struct.unpack_from('<i', gd.fields(f)['PTDT'])[0] == 0 and gd.to_global(i, struct.unpack_from('<I', gd.fields(f)['PTDT'], 4)[0]) in gd.forms)
dlc_key = gd.key(dlc)
edit('dlc', [{'op': 'record', 'key': dlc_key, 'record': recordio.load(gd, dlc)}])

# a patrol: the location as a cell, then near a ref
pl = ac.new_package(gd, pr, br, 'wander', 'Dusty Wanders')
cell = next(iter(c for c in gd.interiors if gd.source(c)[0] == 0))
ac.set_place(pl, 1, gd.key(cell), 700)
pl_key = edit('package', [{'op': 'record_new', 'record': pl}])['made'][0]

path = pr.plugin_path()
espwrite.write(gd, pr, path)
gd2 = gamedata.GameData(plugins=list(gamedata.OFFICIAL) + [path])
me = len(gd2.plugins) - 1
own = lambda k: (me << 24) | int(k[1:], 16)
raw = lambda fid: list(tes4.iter_subrecords(gd2.plugins[gd2.forms[fid][0]].data(gd2.forms[fid][1])))
s = raw(own(made))
tags = [t for t, _d in s]
d = {t: x for t, x in s}
masters = gd2.plugins[me].header['masters']
to = lambda v: gd2.to_global(me, v)
check('the new character is in the plugin, named', gd2.edid(own(made)) == 'FOLabDustyRhodes' and tes4.zstr(d['FULL']) == 'Dusty Rhodes')
factions = [struct.unpack('<IbBH', x) for t, x in s if t == 'SNAM']
check('factions re-pointed: the game\'s and the mod\'s own, with ranks', to(factions[0][0]) == ncr and factions[0][1] == 2 and to(factions[1][0]) == own(mine_fact))
inv = [struct.unpack('<Ii', x) for t, x in s if t == 'CNTO']
check('inventory re-pointed to the master list', len(inv) == 1 and to(inv[0][0]) == gun and inv[0][1] == 3)
pk = [to(struct.unpack('<I', x)[0]) for t, x in s if t == 'PKID']
check('packages in the order given', pk == [own(skey), own(pkey)])
check('entries sit where the game\'s do', tags.index('ACBS') < tags.index('SNAM') < tags.index('CNTO') < tags.index('AIDT') < tags.index('PKID') < tags.index('DATA') < tags.index('FGGS'))
check('the race and class links read', gd2.forms[to(struct.unpack('<I', d['RNAM'])[0])][1].tag == 'RACE' and gd2.forms[to(struct.unpack('<I', d['CNAM'])[0])][1].tag == 'CLAS')
aidt = d['AIDT']
check('AI: aggression, confidence, mood, assistance where the layout says', aidt[0] == 1 and aidt[1] == 4 and aidt[4] == 5 and aidt[14] == 2)
acbs = struct.unpack('<IHHhHHHfhH', d['ACBS'])
check('level follows the player, ×1.25', acbs[0] & 0x80 and not acbs[0] & 0x10 and acbs[3] == 1250)
check('S.P.E.C.I.A.L. and skills at their offsets', d['DATA'][4] == 9 and d['DNAM'][9] == 77)
game = dict(tes4.iter_subrecords(gd.plugins[gd.forms[gd.from_key(town['key'])][0]].data(gd.forms[gd.from_key(town['key'])][1])))
check('the face came through untouched', all(d[t] == game[t] for t in ('FGGS', 'FGGA', 'FGTS')))
for t, x in s:
    check('every subrecord decodes as the schema says (%s)' % t, schema.encode_sub('NPC_', schema.decode_sub('NPC_', t, x)) == x) if t not in ('EDID',) and schema.layout('NPC_', t) else None

sb = {t: x for t, x in raw(own(pkey))}
gsb = gd.fields(find('PACK', 'DefaultSandboxEditorLocation512'))
check('a sandbox package: type and flags as the game\'s own, its radius changed', sb['PKDT'] == gsb['PKDT'] and struct.unpack('<iIi', sb['PLDT']) == (3, 0, 300))
sl = {t: x for t, x in raw(own(skey))}
check('sleep at night: 10pm for 8 hours, near their spot', struct.unpack('<bbBbi', sl['PSDT'])[3:] == (22, 8) and struct.unpack('<iIi', sl['PLDT'])[0] == 3)
fo = {t: x for t, x in raw(own(fkey))}
check('follow: its target is the player', struct.unpack_from('<iI', fo['PTDT']) == (0, 0x14))
wa = {t: x for t, x in raw(own(pl_key))}
a, v, rad = struct.unpack('<iIi', wa['PLDT'])
check('a location in a cell links to the cell', a == 1 and to(v) == cell and rad == 700)
dd = {t: x for t, x in raw(dlc)}
i2 = gd.forms[dlc][0]
d0 = struct.unpack_from('<I', gd.fields(dlc)['PTDT'], 4)[0]
check('a DLC package\'s target is re-pointed to this plugin\'s numbering', gd2.forms[dlc][0] == me and to(struct.unpack_from('<I', dd['PTDT'], 4)[0]) == gd.to_global(i2, d0))
check('so is a faction of the mod\'s own, new', gd2.forms[own(mine_fact)][1].tag == 'FACT' and tes4.zstr(dict(raw(own(mine_fact)))['FULL']) == 'Dust Devils')
for p in gd2.plugins:
    p.close()

# ---- what it looks like ----
lk = ac.look(gd, pr, made)
check('look: a body and a head to draw', any('body' in p['model'].lower() or 'upperbody' in p['model'].lower() for p in lk['parts']) or len(lk['parts']) > 2)
draft = json.loads(json.dumps(pr.records[made]))
armo = find('ARMO', 'OutfitWasteland01')  if any(r.tag == 'ARMO' and gd.edid(f) == 'OutfitWasteland01' for f, (i, r) in gd.forms.items()) else next(f for f, (i, r) in gd.forms.items() if r.tag == 'ARMO' and struct.unpack_from('<I', gd.fields(f).get('BMDT', b'\0\0\0\0'))[0] & 4 and 'MODL' in gd.fields(f))
ac.insert(draft, {'tag': 'CNTO', 'label': 'Item', 'kind': 'struct', 'fields': [{'name': 'Item', 'code': 'F', 'value': gd.key(armo)}, {'name': 'Count', 'code': 'i', 'value': 1}]})
lk2 = ac.look(gd, pr, made, draft)
check('look: unsaved apparel is worn, and takes the body\'s place', lk2['wearing'] and lk2['wearing'][-1]['key'] == gd.key(armo) and 'meshes\\' + tes4.zstr(gd.fields(armo)['MODL']) in [p['model'] for p in lk2['parts']])
rat = find('CREA', 'LvlGiantRat')
check('look: a creature on a levelled template draws its first entry', len(ac.look(gd, pr, gd.key(rat))['parts']) > 0)

# ---- faces ----
opts = ac.options(gd, pr)
check('the face presets are the game\'s 80', len(opts['presets']) == 80)
other = next(p for p in opts['presets'] if p['label'] == 'Asian woman 6')
race = recordio.field(pr.records[made], 'RNAM')
d3 = ac.copy_face(gd, pr, {'key': made, 'record': pr.records[made], 'from': other['key']})
presetrec = recordio.load(gd, gd.from_key(other['key']))
check('a copied face is the preset\'s numbers exactly', ac.one(d3['record'], 'FGGS')['value'] == ac.one(presetrec, 'FGGS')['value'] and ac.one(d3['record'], 'FGTS')['value'] == ac.one(presetrec, 'FGTS')['value'])
order2 = [s['tag'] for s in d3['record']['subs']]
check('it stays in order, before the size', order2.index('FGGS') < order2.index('NAM6') and order2.index('FGGS') > order2.index('DNAM'))
w = d3['warnings']
female = ac.num(pr.records[made], 'ACBS', 'Flags') & 1
check('a new character is warned about its painted face', any('painted face file' in x for x in w))
if race != other['race']:
    check('a face from another race is warned about', any('Race changed' in x for x in w))
if not female:
    check('a face from the other sex is warned about', any('came from a woman' in x for x in w))
sunny = find('NPC_', 'GSSunnySmiles')
check('a game character has its face file on disk', ac.has_face_file(gd, gd.key(sunny)))
hh = next((f for f, (i, r) in gd.forms.items() if r.tag == 'NPC_' and gd.names[i] == 'honesthearts.esm' and f >> 24 == i and ac.has_face_file(gd, gd.key(f))), None)
check('so has a DLC character', hh is not None)
g = recordio.load(gd, sunny)
ac.set_num(g, 'ACBS', 'Flags', ac.num(g, 'ACBS', 'Flags') ^ 1)
check('changing a game character\'s sex warns of its old face file', any('old face' in x for x in ac.warnings(gd, pr, gd.key(sunny), g)))

# ---- Populate ----
inside = next(c for c in gd.interiors if gd.edid(c) == 'GSProspectorSaloonInterior')
ckey = gd.key(inside)
plan = populate.plan(gd, pr, br, {'cell': ckey, 'who': 'all', 'seed': 3})
check('a plan: someone, learnt from places by name', plan['rows'] and plan['learnt'] and plan['count'] >= 1)
names = {r['edid'].lower() for r in plan['rows']}
sv = populate.survey(gd)
check('no one-of-a-kind characters or dead ones', not any('dead' in n for n in names) and all(r['levelled'] or sv.placed.get(gd.from_key(r['base']), 0) >= 2 or sv.named[r['name'].lower()] >= 3 for r in plan['rows']))
check('Sunny Smiles is never among them', sv.actor(sunny) is None)
before, undo_before = len(pr.cells.get(ckey, {'refs': {}})['refs']), len(pr.undo_stack)
rows = plan['rows'][:3]
for r in rows:
    r['count'] = min(r['count'], 2)
res = populate.apply(gd, pr, br, edit, {'cell': ckey, 'rows': json.loads(json.dumps(rows)), 'live': True, 'seed': 3})
check('one undo step', len(pr.undo_stack) == undo_before + 1)
refs = pr.cells[ckey]['refs']
added = sum(r['count'] for r in rows)
check('as many placed as asked', len(refs) - before == added == res['placed'])
people = [r for r in rows if r['kind'] == 'person']
if people:
    base = next(c['base'] for c in refs.values() if c['base'].startswith('+') and pr.records[c['base']]['type'] == 'NPC_')
    n = pr.records[base]
    check('residents have packages of their own', ac.subs_of(n, 'PKID') and all(pr.records[s['value']]['type'] == 'PACK' for s in ac.subs_of(n, 'PKID')))
    check('and their template no longer gives them packages', not ac.num(n, 'ACBS', 'Template flags') & 0x20)
pts = [c['p'] for c in refs.values()]
check('nobody stands on anybody', all((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 > 16 for i, a in enumerate(pts) for b in pts[:i]))
pr.undo()
check('undo takes it all back', len((pr.cells.get(ckey) or {'refs': {}})['refs']) == before and not any(recordio.field(r, 'EDID').startswith('FOLabGSProspector') or 'Prospector Saloon' in recordio.field(r, 'EDID') for r in pr.records.values()))

# levelled: a list of the fixed ones, a creature whose template is the list
crea = find('CREA', 'CrBarkScorpion')
rows = [{'base': gd.key(crea), 'kind': 'creature', 'levelled': False, 'count': 2, 'name': 'Bark Scorpion'}, {'base': gd.key(find('CREA', 'NVCrGiantMantis')), 'kind': 'creature', 'levelled': False, 'count': 1, 'name': 'Giant Mantis'}]
res = populate.apply(gd, pr, br, edit, {'cell': ckey, 'rows': rows, 'levelled': True, 'difficulty': 2, 'seed': 4})
new = [(k, c) for k, c in pr.cells[ckey]['refs'].items() if k.startswith('+')]
check('levelled: three standing, one kind of spawn, hard', res['placed'] == 3 and res['lists'] == 1 and len({c['base'] for k, c in new}) == 1 and all(c.get('xlcm') == 2 for k, c in new))
wrap = pr.records[new[0][1]['base']]
lst = pr.records[ac.one(wrap, 'TPLT')['value']]
check('its template is a creature list, all flags taken from it', lst['type'] == 'LVLC' and ac.num(wrap, 'ACBS', 'Template flags') == 0x3FF)
check('the list is in level order', [ac.num({'subs': [s]}, 'LVLO', 'Level') for s in ac.subs_of(lst, 'LVLO')] == sorted(ac.num({'subs': [s]}, 'LVLO', 'Level') for s in ac.subs_of(lst, 'LVLO')))
espwrite.write(gd, pr, path)
gd2 = gamedata.GameData(plugins=list(gamedata.OFFICIAL) + [path])
me = len(gd2.plugins) - 1
refs2 = [(r.tag, dict(tes4.iter_subrecords(gd2.plugins[i].data(r)))) for rf, (i, r) in gd2.cell_refs[inside].items() if i == me and r.tag in ('ACRE', 'ACHR')]
check('written as creature refs with their difficulty straight after the name', len(refs2) == 3 and all(t == 'ACRE' and struct.unpack('<i', x['XLCM'])[0] == 2 for t, x in refs2))
first = next(rf for rf, (i, r) in gd2.cell_refs[inside].items() if i == me and r.tag == 'ACRE')
order = [t for t, _d in tes4.iter_subrecords(gd2.plugins[me].data(gd2.cell_refs[inside][first][1]))]
check('the ref\'s parts in the game\'s order', order == ['NAME', 'XLCM', 'DATA'])
base = gd2.to_global(me, struct.unpack('<I', dict(tes4.iter_subrecords(gd2.plugins[me].data(gd2.cell_refs[inside][first][1])))['NAME'])[0])
check('the ref names the spawn, and the spawn the list', gd2.forms[base][1].tag == 'CREA' and gd2.forms[gd2.to_global(me, struct.unpack('<I', gd2.fields(base)['TPLT'])[0])][1].tag == 'LVLC')
for p in gd2.plugins:
    p.close()

# outside: the ground, the square's own neighbours
world = next(w for w in gd.worlds() if gd.edid(w) == 'WastelandNV')
square = gd.grid(world).get((-20, 0)) or next(iter(gd.grid(world).values()))
okey = gd.key(square)
oplan = populate.plan(gd, pr, br, {'cell': okey, 'who': 'creatures', 'seed': 1})
check('outside: learnt from the squares round it', oplan['rows'] and oplan['floor'] == 'ground')
check('no DLC people in the Mojave', all(gd.from_key(r['base']) >> 24 == 0 for r in oplan['rows'] + plan['rows']))
import random
sp = populate.spots(gd, pr, okey, 4, random.Random(1))
x, y = gd.cell_grid(square)
check('outside: spots in the square, on the ground', len(sp) == 4 and all(int(s[0] // 4096) == x and int(s[1] // 4096) == y for s in sp))
br.close()
