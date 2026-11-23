"""The Vespid (vespid.py), its hives (hiveset.py) and their scripts (vespidhives.py), from the game's files; nothing goes near
the game. Needs numpy and PIL (the pictures: a build step, as armourset)."""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import gamedata
import hiveset
import nif
import nifmake
import nifwrite
import vespid
import vespidhives as VH


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % detail if detail else ''))


import browse
import project
import server
G = server.GD = gamedata.GameData()
server.BR = browse.Browse(G, lambda: server.PR)
server.PR = project.Project.create('Vespid Test')

# ---------- the Vespid ----------
files = vespid.files(G, 'test')
body = files[vespid.BODY % ('test', 'vespid')]
tex = {(t['block'], t['slot']): t['path'] for t in nifwrite.textures_in(body)}
check('the body is the cazador\'s with our pictures: body, its glow in slot 2, wings', any(p.endswith('vespid_body.dds') for p in tex.values())
      and any(s == 2 and p.endswith('vespid_body_g.dds') for (b, s), p in tex.items()) and any(p.endswith('vespid_wing.dds') for p in tex.values()), str(tex))
check('… the cazador\'s normal maps kept', any(p.lower().endswith('cazadores_n.dds') for p in tex.values()))
caz = nif.mesh_from_nif(G.read_file(vespid.CAZ_BODY), placed=False)
ours = nif.mesh_from_nif(body, placed=False)
check('… the same shapes and corners as the cazador\'s (same skeleton, same moves)', [len(s['p']) for s in caz] == [len(s['p']) for s in ours])
check('pictures: body DXT1, wings with alpha', files[vespid.TEX % ('test', 'vespid_body')][84:88] == b'DXT1' and files[vespid.TEX % ('test', 'vespid_wing')][84:88] == b'DXT5')
rec = vespid.creature(G, 'vespid', 'test', '+000800')
f = {s['tag']: s for s in rec['subs']}
check('the Vespid: named, the cazador\'s poison and skeleton, its own body and death item', f['FULL']['value'] == 'Vespid'
      and f['NIFZ']['value'].startswith('folabtest_vespid.nif') and f['INAM']['value'] == '+000800'
      and G.edid(G.from_key(f['EITM']['value'])) == 'CazadorPoison')
q = vespid.creature(G, 'queen', 'test', None, '+000801')
check('the queen: bigger, a script of her own', [s for s in q['subs'] if s['tag'] == 'BNAM'][0]['fields'][0]['value'] > f['BNAM']['fields'][0]['value']
      and any(s['tag'] == 'SCRI' and s['value'] == '+000801' for s in q['subs']))

# ---------- the hives ----------
for kind in hiveset.KINDS:
    made = hiveset.build(kind)
    check('hive %s: reads back as built (shapes, collision)' % kind, not nifmake.check(made['nif'], made['shapes'], made['solids']),
          str(nifmake.check(made['nif'], made['shapes'], made['solids'])[:3]))
    check('… under a building\'s worth of triangles', made['triangles'] < 22000, made['triangles'])
    crack = [s for s in made['shapes'] if s['tex'] == hiveset.TEX % 'crack']
    paper = [s for s in made['shapes'] if s['tex'] == hiveset.TEX % 'paper']
    check('… the light only from inside: cracks glow, the paper doesn\'t', crack and all(s.get('glow') for s in crack) and paper and not any(s.get('glow') for s in paper))
    check('… a far model', len(made['far']) > 1000 and made['files'][made['mesh'][:-4] + '_lod.nif'] == made['far'])
    mx, my, mz = made['mouth']
    s0 = made['solids'][0]['points']
    check('… its door stands outside the collision', my < min(p[1] for p in s0), '%s %s' % (my, min(p[1] for p in s0)))
h = hiveset.heart()
check('the heart: something solid to activate, chest high', h['box'][5] > 80 and b'bhkConvexVerticesShape' in h['nif'])

# ---------- the scripts compile ----------
import api_scripts
import newgame
import questrec as qr
sc = api_scripts.scripts()
n = 3
extra = {}
k = 0x800
for i in range(n):
    for edid in (VH.LIFE, VH.POOL, VH.FIRE, VH.CACHE):
        extra['+%06X' % k] = {'type': 'REFR', 'flags': newgame.PERSISTENT, 'subs': [{'tag': 'EDID', 'label': 'Editor ID', 'kind': 'z', 'value': edid % (i + 1)}]}
        k += 1
quest = qr.quest_record({'edid': VH.QUEST, 'script': '+000900', 'name': '', 'flags': {'start_enabled': True}, 'priority': 50, 'delay': 2.0, 'stages': [], 'objectives': []})
extra['+000901'] = quest
c = sc.compile(VH.quest_script(n, 1), '+000900', 'quest', extra)
check('the hives\' script compiles', hasattr(c, 'subrecords'), str(c)[:200])
msg = VH._message('FOLabVespidHiveBurnMsg', 'x')
c2 = sc.compile(VH.heart_script('FOLabVespidHiveBurnMsg'), '+000902', 'object', {'+000903': msg})
check('the heart\'s script compiles', hasattr(c2, 'subrecords'), str(c2)[:200])
if hasattr(c, 'subrecords'):
    c3 = sc.compile(VH.queen_script(), '+000904', 'object', dict(extra, **{'+000900': sc._record_of(c, VH.QUEST_SCRIPT)}))
    check('the queen\'s script compiles', hasattr(c3, 'subrecords'), str(c3)[:200])
r = VH.recipe(G)
check('the island antivenom: a Xander root and a broc flower make the game\'s Antivenom', sorted(G.edid(G.from_key(s['value'])) for s in r['subs'] if s['tag'] == 'RCIL') == ['BrocFlower', 'XanderRoot']
      and [G.edid(G.from_key(s['value'])) for s in r['subs'] if s['tag'] == 'RCOD'] == ['NVAntivenom'])
honey, royal = VH.rad_honey(G), VH.royal_jelly(G)
val = lambda r: next(f['value'] for s in r['subs'] if s['tag'] == 'ENIT' for f in s['fields'] if f.get('name') == 'Value')
check('Rad Honey and Glowing Royal Jelly: named, the jelly worth far more', [s['value'] for s in honey['subs'] if s['tag'] == 'FULL'] == ['Rad Honey']
      and [s['value'] for s in royal['subs'] if s['tag'] == 'FULL'] == ['Glowing Royal Jelly'] and val(royal) >= 5 * val(honey))
r = VH.recipe_of(G, 'FOLabRecipeHiveFire', 'Hive Fire', 60, [('+000A01', 1), ('+000A02', 1)], '+000A03')
check('a recipe of the island\'s own: its ingredients and what it makes', [s['value'] for s in r['subs'] if s['tag'] == 'RCIL'] == ['+000A01', '+000A02']
      and [s['value'] for s in r['subs'] if s['tag'] == 'RCOD'] == ['+000A03'])
