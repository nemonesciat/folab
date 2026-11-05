import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
"""Inventories and levelled lists: entries added to a character's inventory (after its COED-carrying ones, before
AIDT) and to a levelled list, a new item of the mod's own among them, read back from the written plugin."""
import struct
import gamedata, project, espwrite, recordio, tes4


def check(what, ok):
    print(('PASS ' if ok else 'FAIL ') + what)


gd = gamedata.GameData()
find = lambda tag, e: next(f for f, (i, r) in gd.forms.items() if r.tag == tag and gd.edid(f) == e)
sunny, ll, gun = find('NPC_', 'GSSunnySmiles'), find('LVLI', 'Ammo10mm75'), find('WEAP', 'WeapNV357Revolver')
pr = project.Project.create('Inventory Test')
g = recordio.load(gd, gun); recordio.set_field(g, 'EDID', 'FOLabInvGun')
mine = pr.apply('gun', [{'op': 'record_new', 'record': g}])[0]
n = recordio.load(gd, sunny)
at = max(i for i, s in enumerate(n['subs']) if s['tag'] in ('CNTO', 'COED')) + 1
n['subs'].insert(at, {'tag': 'CNTO', 'label': 'Item', 'kind': 'struct', 'fields': [
    {'name': 'Item', 'code': 'F', 'value': mine}, {'name': 'Count', 'code': 'i', 'value': 2}]})
l = recordio.load(gd, ll)
l['subs'].append({'tag': 'LVLO', 'label': 'Entry', 'kind': 'struct', 'fields': [
    {'name': 'Level', 'code': 'h', 'value': 20}, {'pad': '0000'}, {'name': 'Item', 'code': 'F', 'value': mine},
    {'name': 'Count', 'code': 'h', 'value': 1}, {'pad': '0000'}]})
pr.apply('lists', [{'op': 'record', 'key': gd.key(sunny), 'record': n}, {'op': 'record', 'key': gd.key(ll), 'record': l}])
path = pr.plugin_path(); espwrite.write(gd, pr, path)
gd2 = gamedata.GameData(plugins=list(gamedata.OFFICIAL) + [path]); me = len(gd2.plugins) - 1
def subs(fid):
    i, r = gd2.source(fid); return i, list(tes4.iter_subrecords(gd2.plugins[i].data(r)))
i, s = subs(sunny)
tags = [t for t, d in s]
cn = [struct.unpack('<Ii', d) for t, d in s if t == 'CNTO']
check('Sunny comes from the mod', i == me)
check('three things carried, the new gun x2 last', len(cn) == 3 and gd2.edid(gd2.to_global(me, cn[-1][0])) == 'FOLabInvGun' and cn[-1][1] == 2)
check('entries stay before AIDT, COED kept', tags.index('AIDT') > max(k for k, t in enumerate(tags) if t == 'CNTO') and 'COED' in tags)
i, s = subs(ll)
lv = [struct.unpack('<hHIhH', d) for t, d in s if t == 'LVLO']
check('list has its old entry and the new one at level 20', len(lv) == 2 and lv[1][0] == 20 and gd2.edid(gd2.to_global(me, lv[1][2])) == 'FOLabInvGun')
check('the old entry keeps its bytes', lv[0] == struct.unpack('<hHIhH', dict(tes4.iter_subrecords(gd.plugins[0].data(gd.forms[ll][1])))['LVLO']))
for p in gd2.plugins:
    p.close()
