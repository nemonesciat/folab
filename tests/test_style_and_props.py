import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
"""Suggestions and palettes learnt from the game's places; a placed thing's owner, lock and enable parent, in the bytes the
game's own records use and read back from a written plugin."""
import json
import struct

import espwrite, gamedata, project, refprops, stylesurvey, tes4


def check(what, ok):
    print(('PASS ' if ok else 'FAIL ') + what)


gd = gamedata.GameData()
data = stylesurvey.read(gd)
s = stylesurvey.Survey(json.loads(json.dumps(data)))          # (as it comes back from the cache)
names = {st['name'] for st in s.styles()}
check('the styles are there, inside and out', {'Casino', 'Vault', 'Office', 'The Mojave'} <= names)
pal = s.palette('Casino')
furn = next(x for x in pal['sections'] if x['id'] == 'furniture')['rows']
check('a casino has its own furniture', len(furn) > 5 and all(r['model'] for r in furn))
items = next(x for x in pal['sections'] if x['id'] == 'items')['rows']
check('and the drinks you\'d expect', any('whiskey' in r['edid'].lower() or 'beer' in r['edid'].lower() for r in items))
shell = next(x for x in s.palette('Vault')['sections'] if x['id'] == 'shell')['rows']
check('a vault\'s walls are vault walls', sum(1 for r in shell if 'vault' in r['model'].lower()) > len(shell) * 0.6)
check('the same things aren\'t in every palette', {r['key'] for r in furn} != {r['key'] for r in next(x for x in s.palette('Vault')['sections'] if x['id'] == 'furniture')['rows']})
check('sets come with their things', pal['sets'] and all(st['count'] >= 3 and len(st['items']) == st['count'] for st in pal['sets']))
st = pal['sets'][0]
check('placed from the lowest point, the first thing in the middle', min(i['p'][2] for i in st['items']) == 0 and st['items'][0]['p'][:2] == [0, 0])
check('all near each other', all(abs(i['p'][0]) <= stylesurvey.NEAR and abs(i['p'][1]) <= stylesurvey.NEAR for i in st['items']))
vault = next(p for p in s.places if p['name'].startswith('Vault 11') and not p['out'])
half = [s.bases[b] for b in list(vault['bag'])[:len(vault['bag']) // 2]]
got = s.suggest(half)
check('a place like a vault is told it\'s like the vaults', sum(1 for l in got['like'] if 'vault' in l['name'].lower()) >= 3)
check('suggestions aren\'t what it already has', not set(r['key'] for r in got['rows']) & set(half))
check('from every section', len({r['sec'] for r in got['rows']}) >= 3)
empty = s.suggest([])
check('an empty place gets what the game uses most', empty.get('empty') and empty['rows'])
outs = next(p for p in s.places if p['out'] and len(p['bag']) > 20)
o = s.suggest([s.bases[b] for b in list(outs['bag'])[:10]], True, skip_id=outs['id'])
check('outside learns from outside', o['rows'] and all(' near cell ' in l['name'] for l in o['like']))
chair = s.key_of and next(k for k, i in s.key_of.items() if s.near.get(str(i)))
check('goes with: what stands near', s.goes_with(chair) and all('n' in r for r in s.goes_with(chair)))

# --- the bytes of the settings, against every game ref holding them ---
keys = lambda i: (lambda k: k)
checked = {'XLOC': 0, 'XOWN': 0, 'XESP': 0, 'XRNK': 0}
bad = []
for c, refs in gd.cell_refs.items():
    for rfid, (i, rec) in refs.items():
        if rec.tag == 'NAVM':
            continue
        f = gd.plugins[i].fields(rec)
        if not any(k in f for k in checked):
            continue
        p = refprops.of_game(gd, rfid)
        back = {k: gd.to_global(i, 0) for k in ()}
        link = lambda key: struct.unpack('<I', struct.pack('<I', gd.from_key(key)))[0]
        # (in load-order numbering, so what the game's file says is put through to_global the same way)
        norm = lambda v: gd.to_global(i, v) if v else 0
        if 'XOWN' in f:
            checked['XOWN'] += 1
            if link(p['owner']) != norm(struct.unpack('<I', f['XOWN'])[0]):
                bad.append(('XOWN', rfid))
        if 'XRNK' in f:
            checked['XRNK'] += 1
            subs, _fl = refprops.apply([('XOWN', f['XOWN'])], {'rank': p['rank']}, 0, link)
            if dict(subs)['XRNK'] != f['XRNK']:
                bad.append(('XRNK', rfid))
        if 'XLOC' in f and len(f['XLOC']) == 20:
            checked['XLOC'] += 1
            mine = refprops.encode_lock(p['lock'], link)
            x = f['XLOC']
            # (the spare bytes hold whatever was in memory when the game's tools wrote them: only the meanings compare)
            if not (mine[0] == x[0] and struct.unpack_from('<I', mine, 4)[0] == norm(struct.unpack_from('<I', x, 4)[0]) and mine[8] == x[8] and len(mine) == 20):
                bad.append(('XLOC', rfid))
        if 'XESP' in f:
            checked['XESP'] += 1
            mine = refprops.encode_parent(p['parent'], link)
            x = f['XESP']
            if not (len(mine) == len(x) and struct.unpack_from('<I', mine)[0] == norm(struct.unpack_from('<I', x)[0]) and mine[4] == x[4]):
                bad.append(('XESP', rfid))
check('every game ref\'s owner, rank, lock and enable parent encodes as the game has it (%s)' % checked, all(checked.values()) and not bad)
if bad:
    print(bad[:5])
a_lock = next(r for c, refs in gd.cell_refs.items() for r, e in refs.items() if e[1].tag == 'REFR' and 'XLOC' in gd.plugins[e[0]].fields(e[1]))
check('the object window\'s reader agrees', refprops.of_game(gd, a_lock)['lock']['level'] == gd.plugins[gd.cell_refs[gd.ref_cell[a_lock]][a_lock][0]].fields(gd.cell_refs[gd.ref_cell[a_lock]][a_lock][1])['XLOC'][0])

# --- in a plugin ---
pr = project.Project.create('Props Test')
cell = next(c for c in gd.interiors if gd.edid(c) == '2EOVault21')
ck = gd.key(cell)
things = gd.refs(cell)
plain = next(r for r in things if r['base'] in gd.forms and gd.forms[r['base']][1].tag == 'CONT' and not r['persistent'])
parent = next(r for r in things if r['ref'] != plain['ref'] and not r['persistent'] and gd.forms.get(r['base'], (0, tes4))[1].tag == 'STAT')
npc = next(f for f, (i, r) in gd.forms.items() if r.tag == 'NPC_' and i == 0)
faction = next(f for f, (i, r) in gd.forms.items() if r.tag == 'FACT' and i == 0)
key = next(f for f, (i, r) in gd.forms.items() if r.tag == 'KEYM' and i == 0)
made = pr.apply('new', [{'op': 'add', 'cell': ck, 'base': gd.key(plain['base']), 'p': [1, 2, 3, 0, 0, 0], 's': 2.0}])
new_key = made[0]
ops = refprops.ops_for(pr, gd, ck, gd.key(plain['ref']), {'owner': gd.key(npc), 'lock': {'level': 75, 'key': gd.key(key), 'leveled': True},
                                                       'parent': {'ref': gd.key(parent['ref']), 'opposite': True}, 'disabled': True})
check('what enables it is kept loaded', any(o['op'] == 'persist' and o['ref'] == gd.key(parent['ref']) for o in ops))
pr.apply('settings', ops)
pr.apply('new one', [{'op': 'props', 'cell': ck, 'ref': new_key, 'props': {'owner': gd.key(faction), 'rank': 2, 'lock': {'level': 255, 'key': ''}}}])
check('merged: as the mod leaves it', refprops.merged(gd, pr, ck, gd.key(plain['ref']))['lock']['level'] == 75)
path = pr.plugin_path()
espwrite.write(gd, pr, path)
gd2 = gamedata.GameData(plugins=list(gamedata.OFFICIAL) + [path])
me = len(gd2.plugins) - 1
i, rec = gd2.cell_refs[gd2.ref_cell[plain['ref']]][plain['ref']]
check('the plugin holds the changed ref', gd2.names[i] == gd2.names[me])
got = refprops.of_game(gd2, plain['ref'])
check('owner', got['owner'] == gd2.key(npc))
check('lock', got['lock'] == {'level': 75, 'key': gd2.key(key), 'leveled': True})
check('enable parent', got['parent'] == {'ref': gd2.key(parent['ref']), 'opposite': True, 'popin': False})
check('starts off', got['disabled'] and rec.flags & 0x800)
tags = [t for t, d in tes4.iter_subrecords(gd2.plugins[i].data(rec))]
check('everything before where it stands, as in the game', tags.index('DATA') == len(tags) - 1 and tags[0] == 'NAME')
i2, prec = gd2.cell_refs[gd2.ref_cell[parent['ref']]][parent['ref']]
check('the parent is persistent in the plugin', gd2.names[i2] == gd2.names[me] and prec.flags & tes4.PERSISTENT)
new_fid = (me << 24) | int(new_key[1:], 16)
nr = refprops.of_game(gd2, new_fid)
check('a new thing has them too', nr['owner'] == gd2.key(faction) and nr['rank'] == 2 and nr['lock']['level'] == 255)
tags = [t for t, d in tes4.iter_subrecords(gd2.plugins[me].data(gd2.cell_refs[gd2.ref_cell[new_fid]][new_fid][1]))]
check('rank right after owner, size and place last', tags.index('XRNK') == tags.index('XOWN') + 1 and tags[-2:] == ['XSCL', 'DATA'])
for p in gd2.plugins:
    p.close()
pr.undo()
check('undo takes them back', 'owner' not in (pr.cells[ck]['refs'].get(new_key, {}).get('props') or {}))
pr.apply('clear', [{'op': 'props', 'cell': ck, 'ref': gd.key(plain['ref']), 'props': {'owner': '', 'lock': None, 'parent': None, 'disabled': False}}])
pr2 = refprops.merged(gd, pr, ck, gd.key(plain['ref']))
check('cleared ones stay cleared', pr2['owner'] == '' and pr2['lock'] is None and pr2['parent'] is None)
subs, fl = refprops.apply([('NAME', b'1234'), ('XOWN', b'abcd'), ('XRNK', b'\1\0\0\0'), ('XLOC', b'x' * 20), ('DATA', b'd')], {'owner': '', 'lock': None}, 0x800, lambda k: 0)
check('and leave no bytes behind', [t for t, d in subs] == ['NAME', 'DATA'] and fl == 0x800)
check('groups are kept with the mod', refprops.groups_save(pr, [{'keys': ['+1', '+2']}]) and refprops.groups_read(pr) == [{'keys': ['+1', '+2']}])
