"""Waikiki's people of its own (factionfolk): enough of the game's ordinary faces for every group without one used twice;
a person is the face's record with its look by template (traits only), its own name, level, faction, outfit, weapon and
ammunition and package, not unique; the captain is the mod's pirate with the Officer's Coat and a Pip-Boy in place of its
body list; the stores' and the Huáng's containers gain what they should; written, each person reads back as made."""
import json
import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))

import espwrite  # noqa: E402
import factionfolk as FF  # noqa: E402
import gamedata  # noqa: E402
import peopledress as P  # noqa: E402
import project  # noqa: E402
import recordio  # noqa: E402
import tes4  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


gd = gamedata.GameData()
find = lambda tag, e: next(f for f, (i, r) in gd.forms.items() if r.tag == tag and gd.edid(f) == e)

pool = FF.faces(gd)
need = {}
for g in FF.GROUPS.values():
    for n in range(g['count']):
        sex = g['sexes'][n % len(g['sexes'])]
        need[(g['races'], sex)] = need.get((g['races'], sex), 0) + 1
have = {k: sum(len(pool.get((r, k[1]), [])) for r in k[0]) for k in need}
check('enough of the game\'s faces for every group', all(have[k] >= need[k] for k in need), {k[1] + '/' + k[0][0]: (need[k], have[k]) for k in need})

pr = project.Project.create('Folk Test')
# the mod's own things the people wear and carry, as the real mod has them (copies of game records, renamed)
made = {}
for edid, tag, base in [('FOLabHuangLamellar', 'ARMO', 'ArmorNVCLVeteran'), ('FOLabChangshan', 'ARMO', 'OutfitVeronicaRobes'),
                        ('FOLabSilkGown', 'ARMO', 'OutfitVeronicaRobes'), ('FOLabOfficialsRobe', 'ARMO', 'OutfitElderMcNamara'),
                        ('FOLabAhuula', 'ARMO', 'ArmorNVCLPraetorian'), ('FOLabMahiole', 'ARMO', 'CowboyHat04'),
                        ('FOLabKoaArmor', 'ARMO', 'NVDLC04ArmorMarkedMenTribal'), ('FOLabOfficersCoat', 'ARMO', 'BountyHunterDuster'),
                        ('FOLabWeapTYPE81', 'WEAP', 'WeapNVAssaultCarbine'), ('FOLabWeapTYPE79', 'WEAP', 'Weap10mmSubmachineGun'),
                        ('FOLabWeapQSZ92', 'WEAP', 'WeapNV9mmPistol'), ('FOLabWeapLeiomano', 'WEAP', 'WeapNVMachete'),
                        ('FOLabWeapMaul', 'WEAP', 'WeapSledgehammer'), ('FOLabWeapNewa', 'WEAP', 'WeapLeadPipe'),
                        ('FOLabWeapHoe', 'WEAP', 'WeapLeadPipe')]:
    rec = recordio.load(gd, find(tag, base))
    rec['src'] = ''
    rec['subs'] = [s for s in rec['subs'] if s['tag'] not in ('SCRI', 'EITM')]
    recordio.set_field(rec, 'EDID', edid)
    made[edid] = pr.apply('x', [{'op': 'record_new', 'record': rec}])[0]
clubs = pr.apply('x', [{'op': 'record_new', 'record': P._lvli(gd, 'FOLabClubsCourt', 0, [(made['FOLabWeapLeiomano'], 1)])}])[0]
body = pr.apply('x', [{'op': 'record_new', 'record': P._lvli(gd, 'FOLabPirateBodyList', 0, [(gd.key(find('ARMO', 'ArmorLeather')), 1)])}])[0]
pirate = recordio.load(gd, find('NPC_', 'LvlFiend2GunVarNV'))
pirate['src'] = ''
recordio.set_field(pirate, 'EDID', 'FOLabPirateLvlFiend2GunVarNV')
pirate['subs'] = [s for s in pirate['subs'] if s['tag'] != 'CNTO']
cnto = P._sub('NPC_', 'CNTO', struct.pack('<Ii', 0, 1))
FF._set_link(cnto, body)
pirate['subs'].append(cnto)
pr.apply('x', [{'op': 'record_new', 'record': pirate}])
for edid, base in [('FOLabWaikikiGunsmithChest', 'VendorContainerGunRunnerHQ'), ('FOLabWaikikiTraderChest', 'VendorContainerChet'),
                   ('FOLabNVDuffleBagRandomLootHuang', 'NVDuffleBagRandomLoot'), ('FOLabFootlocker01HospitalHuang', 'Footlocker01Hospital')]:
    rec = recordio.load(gd, find('CONT', base))
    rec['src'] = ''
    recordio.set_field(rec, 'EDID', edid)
    pr.apply('x', [{'op': 'record_new', 'record': rec}])

# no world: the spots are given (one per person, in an empty cell of the Mojave)
world = find('WRLD', 'WastelandNV')
spots = {k: [(1000.0 + 300 * n, 2000.0, 100.0, 0.0) for n in range(g['count'])] for k, g in FF.GROUPS.items()}
spots['captain'] = [(1000.0, 3000.0, 100.0, 0.0)] * 3
ops, rep = FF.ops(gd, pr, {'spots': spots, 'world': world})
first = pr.next_id
pr.apply('folk', ops)
want = sum(g['count'] for g in FF.GROUPS.values())
check('a record for each person, two factions, the clothes list, the captain', rep['records'] == want + 4, rep['records'])
check('everyone placed', rep['placed'] == want + 3 and not rep['short'], (rep['placed'], rep['short']))
recs = {k: r for k, r in pr.records.items() if r.get('type') == 'NPC_' and (recordio.field(r, 'EDID') or '').startswith(('FOLabHuang', 'FOLabKahuna', 'FOLabCourt'))}
tpl = [recordio.field(r, 'TPLT') for r in recs.values()]
check('every face the game\'s and used once', len(tpl) == want and len(set(tpl)) == want and all(not t.startswith('+') for t in tpl))
check('looks by template only (traits), not unique', all(FF._num(r, 'ACBS', 'Template flags') == FF.USE_TRAITS and not FF._num(r, 'ACBS', 'Flags') & 0x20 for r in recs.values()))
guard = next(r for r in recs.values() if recordio.field(r, 'EDID') == 'FOLabHuangGuard01')
items = [next(f['value'] for f in s['fields'] if f.get('code') == 'F') for s in guard['subs'] if s['tag'] == 'CNTO']
check('a Shouwei: lamellar, a Type 81 and its ammunition, the Huáng faction',
      recordio.field(guard, 'FULL') == 'Shouwei' and made['FOLabHuangLamellar'] in items and made['FOLabWeapTYPE81'] in items and len(items) == 3
      and [next(f['value'] for f in x['fields'] if f.get('code') == 'F') for x in guard['subs'] if x['tag'] == 'SNAM'] == [rep['factions']['huang']], items)
folk = [r for r in recs.values() if recordio.field(r, 'EDID').startswith('FOLabHuangFolk')]
female = lambda r: FF._num(recordio.load(gd, gd.from_key(recordio.field(r, 'TPLT'))), 'ACBS', 'Flags') & 1
worn = lambda r: [next(f['value'] for f in s['fields'] if f.get('code') == 'F') for s in r['subs'] if s['tag'] == 'CNTO']
check('Nongmin: men in the changshan, women in the silk gown',
      folk and all(made['FOLabSilkGown' if female(r) else 'FOLabChangshan'] in worn(r) for r in folk))
cap = pr.records[rep['captain']]
ci = [next(f['value'] for f in s['fields'] if f.get('code') == 'F') for s in cap['subs'] if s['tag'] == 'CNTO']
check('the captain: the coat and a Pip-Boy, the pirates\' body list gone', made['FOLabOfficersCoat'] in ci and gd.key(find('ARMO', 'PipBoyNPC')) in ci and body not in ci, (ci, made['FOLabOfficersCoat'], body))
gun = next(k for k, r in pr.records.items() if recordio.field(r, 'EDID') == 'FOLabWaikikiGunsmithChest')
check('the gunsmith sells the court\'s clubs', clubs in [next(f['value'] for f in s['fields'] if f.get('code') == 'F') for s in pr.records[gun]['subs'] if s['tag'] == 'CNTO'])
check('the stores and the Huáng\'s containers changed', all(v != 'not in the mod' for v in rep['trade'].values()), rep['trade'])
try:
    FF.ops(gd, pr, {'spots': spots, 'world': world})
    check('a second time refused', False)
except ValueError:
    check('a second time refused', True)

path = pr.plugin_path()
espwrite.write(gd, pr, path)
gd2 = gamedata.GameData(plugins=list(gamedata.OFFICIAL) + [path])
me = len(gd2.plugins) - 1
k = next(k for k, r in recs.items() if recordio.field(r, 'EDID') == 'FOLabHuangGuard01')
d = dict(tes4.iter_subrecords(gd2.plugins[gd2.forms[(me << 24) | int(k[1:], 16)][0]].data(gd2.forms[(me << 24) | int(k[1:], 16)][1])))
check('written: the Shouwei\'s template is the game\'s face, its name its own', tes4.zstr(d['FULL']) == 'Shouwei'
      and struct.unpack('<I', d['TPLT'])[0] == gd.from_key(recordio.field(guard, 'TPLT')))
