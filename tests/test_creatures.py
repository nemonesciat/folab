"""Waikiki's island animals (sharklurk.py, islandbeasts.py, creaturepaint.py, creaturesites.py), from the game's files; nothing
goes near the game. Needs numpy and PIL (the pictures: a build step, as the Vespid)."""
import math
import os
import struct
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import gamedata
import nif
import nifwrite
import outfitjoin
import creaturesites as CS
import islandbeasts as IB
import sharklurk as SL


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % detail if detail else ''))


import numpy as np
import browse
import project
import server
G = server.GD = gamedata.GameData()
server.BR = browse.Browse(G, lambda: server.PR)
server.PR = project.Project.create('Creature Test')

# ---------- the Sharklurk ----------
files = SL.files(G, 'test')
body = files[SL.BODY % 'test']
tex = {(t['block'], t['slot']): t['path'] for t in nifwrite.textures_in(body)}
check('the body is the lakelurk\'s with our picture and glow', any(p.endswith('sharklurk\\body.dds') for p in tex.values())
      and any(s == 2 and p.endswith('sharklurk\\body_g.dds') for (b, s), p in tex.items()), str(sorted(set(tex.values())))[:200])
check('… its own normal map (the face flattened), the gore caps kept', any(p.endswith('sharklurk\\body_n.dds') for p in tex.values())
      and not any(p.lower().endswith('lakekurk_n.dds') for p in tex.values()) and any('meatcapgore' in p.lower() for p in tex.values()))
check('… the normal map keeps its shine (DXT5)', files[SL.TEX % ('test', 'body_n')][84:88] == b'DXT5')
lurk = nif.mesh_from_nif(G.read_file(SL.BODY_GAME), placed=False)
ours = nif.mesh_from_nif(body, placed=False)
check('… the same shapes and corners (same skeleton, same moves)', [len(s['p']) for s in lurk] == [len(s['p']) for s in ours])
check('pictures: body and glow DXT1', files[SL.TEX % ('test', 'body')][84:88] == b'DXT1' and files[SL.TEX % ('test', 'body_g')][84:88] == b'DXT1')

fin = files[SL.FIN % 'test']
check('the fin: nothing empty for the game to draw', outfitjoin.empty_parts(fin) == [], str(outfitjoin.empty_parts(fin)))
check('… every triangle drawn from its partition', all(k > 0 for _n, k in outfitjoin.drawn(fin)), str(outfitjoin.drawn(fin)))
n = nif.Nif(fin)
check('… skinned to Bip01 Spine2, triangle lists as the game\'s skinned shapes', 'Bip01 Spine2' in n.strings
      and 'NiTriShape' in n.types and 'NiTriStrips' not in n.types and 'BSDismemberSkinInstance' in n.types)
R, T, part = SL.spine_bind(G)
check('… bound as the body binds that bone (its own skin data), on the torso partition', abs(sum(R[k][k] for k in range(3))) > 0.5 and part[1] == 0, '%s %s' % (T, part))
fs = SL.fin_shapes(G, 'test')[0]
P = np.array(fs['p']).reshape(-1, 3)
line = SL.back_line(G)
root = P[:, 1].max()
inside = []
for zz in range(int(SL.FIN_TOP + min(dz for dz, _o in SL.FIN_TRAIL)), int(SL.FIN_TOP) + 1):
    ys = [y for y, z in line if abs(z - zz) < 1.0]
    if ys:
        inside.append(min(ys) < root - 0.5)
check('… rooted inside the skin at every height along its base (no light under it from any side)', inside and all(inside), '%d of %d' % (sum(inside), len(inside)))
check('… up the spine, standing well out behind', 80 < P[:, 2].min() < P[:, 2].max() < 130 and P[:, 1].min() < root - 25)
got = nif.mesh_from_nif(fin, placed=False)[0]
import creaturepaint as cp
lurk_data = G.read_file(SL.BODY_GAME)
raw = np.array(got['p']).reshape(-1, 3)
# (where the game puts it: its bone's bind applied to the raw corners, back through the body's own bind of that bone)
check("… in the game it stands where it was made: its raw corners are the body's (the lakelurk's shape sits at -13.8, +30.4, which the bones ignore)",
      np.allclose(cp.from_skin(lurk_data, raw), P, atol=0.01) and not np.allclose(raw, P, atol=1.0))
sk = cp.skin_of(lurk_data)
R2, T2, _s = sk['binds'][sk['names'].index(SL.SPINE)]
body_raw = np.array(sk['verts']).reshape(-1, 3)
check("… bound as the body's own spine corners are (the same raw space)", np.allclose((np.array(R2) @ raw.T).T + T2, (np.array(R) @ raw.T).T + T, atol=1e-4)
      and abs(body_raw[:, 1].min() - raw[:, 1].max()) < 60)

# the snout and the mouth
shaped = nif.mesh_from_nif(body, placed=False)
front0 = max(y for s in lurk if 'gore' not in s['tex'].lower() for y, z in zip(s['p'][1::3], s['p'][2::3]) if z > 134)
front1 = max(y for s in shaped if 'gore' not in s['tex'].lower() for y, z in zip(s['p'][1::3], s['p'][2::3]) if z > 134)
check('the snout points out: the face reaches further forward (%.1f -> %.1f)' % (front0, front1), front1 - front0 > 3.0)
low0 = [p for s in lurk for k, p in enumerate(zip(s['p'][0::3], s['p'][1::3], s['p'][2::3])) if p[2] < 131]
low1 = [p for s in shaped for k, p in enumerate(zip(s['p'][0::3], s['p'][1::3], s['p'][2::3])) if p[2] < 131]
check('… nothing at or under the mouth moved', low0 == low1)
gone = SL.back_spines(G.read_file(SL.BODY_GAME))
check('the spikes down the back of the head and neck found (patches on the middle line)', sum(len(v) for v in gone.values()) >= 100, sum(len(v) for v in gone.values()))
bn = nif.Nif(body)
left = {tuple(sorted(t)) for i, tt in gone.items() for t in [bn.block(bn.block(i)['data'])['tris'][k:k + 3] for k in range(0, len(bn.block(bn.block(i)['data'])['tris']), 3)] if not (t[0] == t[1] == t[2])}
check('… and none of them drawn', not any(t in gone[i] for i in gone for t in left))
moved = [i for i, (a, b) in enumerate(zip(lurk, shaped)) if a['p'] != b['p']]
orig_drawn = dict(outfitjoin.drawn(G.read_file(SL.BODY_GAME)))
spine_n = {nif.Nif(G.read_file(SL.BODY_GAME)).block(i)['name']: len(v) for i, v in SL.back_spines(G.read_file(SL.BODY_GAME)).items()}
check("… the same corners and skin; what it draws is the lakelurk's less the spikes, nothing empty",
      [len(s['i']) for s in lurk] == [len(s['i']) for s in shaped] and outfitjoin.empty_parts(body) == []
      and all(k == orig_drawn[nm] - spine_n.get(nm, 0) for nm, k in outfitjoin.drawn(body)), '%s %s' % (outfitjoin.drawn(body), spine_n))

K = {'meat': '+000800', 'tooth': '+000801', 'teeth': '+000802', 'death': '+000803'}
recs = dict(SL.records(G, 'test', K))
f = {s['tag']: s for s in recs['sharklurk']['subs']}
sonic = {G.key(SL._game(G, 'WEAP', SL.SONIC[0])), G.key(SL._game(G, 'AMMO', SL.SONIC[1]))}
cnto = [s['fields'][0]['value'] for s in recs['sharklurk']['subs'] if s['tag'] == 'CNTO']
check('the Sharklurk bites only: no sonic weapon, no its ammo', not sonic & set(cnto), str(cnto))
check('… its body and fin in its model list, its own death list', f['NIFZ']['value'] == 'folabtest_sharklurk.nif\0folabtest_sharkfin.nif\0'
      and f['INAM']['value'] == '+000803' and f['FULL']['value'] == 'Sharklurk')
check('… the lakelurk\'s skeleton and water breathing kept', f['MODL']['value'].lower() == 'creatures\\mirelurkking\\skeleton.nif'
      and G.edid(G.from_key(f['SPLO']['value'])) == 'LakelurkWaterBreathing')
lv = [s for s in recs['death']['subs'] if s['tag'] == 'LVLO']
items = [(next(x['value'] for x in s['fields'] if x.get('name') == 'Item'), next(x['value'] for x in s['fields'] if x.get('name') == 'Count')) for s in lv]
check('its death list: shark meat every time, the teeth list once', items == [('+000800', SL.MEAT_EACH), ('+000802', 1)], str(items))
pct = next(x['value'] for s in recs['teeth']['subs'] if s['tag'] == 'LVLD' for x in s['fields'] if x.get('name') == 'Percent')
check('… a tooth %d kills in 100' % SL.TOOTH_CHANCE, pct == 100 - SL.TOOTH_CHANCE)
check('shark meat and tooth named, the tooth on the game\'s tooth model', [s['value'] for s in recs['meat']['subs'] if s['tag'] == 'FULL'] == ['Shark Meat']
      and [s['value'] for s in recs['tooth']['subs'] if s['tag'] == 'MODL'] == [SL.TOOTH_MODEL])
check('the tooth\'s model is in the game', G.read_file('meshes\\' + SL.TOOTH_MODEL) is not None)

# ---------- the fillers ----------
for kind, k in IB.KINDS.items():
    fl = IB.files(G, kind, 'test')
    b = fl[IB.body_path(kind, 'test')]
    game = nif.mesh_from_nif(G.read_file(k['body']), placed=False)
    mine = nif.mesh_from_nif(b, placed=False)
    check('%s: the game\'s body, same shapes and corners' % kind, [len(s['p']) for s in game] == [len(s['p']) for s in mine])
    paths = {t['path'] for t in nifwrite.textures_in(b)}
    want = {IB.TEX % ('test', kind, ours) for ours in k['pics'].values()}
    check('… its pictures named in the body', want <= paths, str(sorted(paths))[:200])
    check('… each a texture', all(fl[p][:4] == b'DDS ' for p in want))
    rec = CS._beast(G, kind, 'test')
    tags = {s['tag'] for s in rec['subs']}
    fv = {s['tag']: s for s in rec['subs']}
    check('… its record: own body, name, no game drops, no poison, respawns', fv['NIFZ']['value'] == '\0'.join(p.rsplit('\\', 1)[1] for p in IB.body_paths(kind, 'test')) + '\0'
          and fv['FULL']['value'] == k['name'] and 'INAM' not in tags and 'EITM' not in tags and 'TPLT' not in tags
          and next(x['value'] for x in fv['ACBS']['fields'] if x.get('name') == 'Flags') & CS.RESPAWN)
rat = IB.files(G, 'mongoose', 'test')[IB.TEX % ('test', 'mongoose', 'body')]
check('the mongoose keeps the rat\'s fur cut-outs (alpha)', rat[84:88] == b'DXT5')

# ---------- where they live (a made-up island: sea to the south, a valley, a town, a door) ----------
lay = CS.Lay()
lay.x0, lay.y0 = -20480.0, -20480.0
nx = ny = 161
X = lay.x0 + np.arange(nx)[None, :] * CS.STEP + np.zeros((ny, 1))
Y = lay.y0 + np.arange(ny)[:, None] * CS.STEP + np.zeros((1, nx))
H = np.where(Y > 0, Y * 0.06, Y * 0.3).astype(np.float32)    # (sea level 0 at y 0: land north, a reef's drop south)
H += np.where((np.abs(X - 8000) < 1800) & (Y > 6000), -250.0 * np.cos((X - 8000) / 1800 * math.pi / 2), 0).astype(np.float32)
lay.h = H
lay.sea = 0.0
lay.markers = [('Hanauma Bay', -12000.0, 800.0, 50.0), ("Town Squatters' Camp", 4000.0, 6000.0, 300.0)]
lay.spots = [(m[1], m[2], 'marker ' + m[0]) for m in lay.markers] + [(-4000.0, -2000.0, 'door +000123')]
lay.roads, lay.built, lay.taro, lay.wet = [(0.0, 9000.0)], [], [(8000.0, 12000.0)], []
lay.start, lay.middle = (-12000.0, 900.0), (30000.0, 900.0)
wasteland = next(w for w in G.worlds() if G.edid(w) == 'WastelandNV')
lay.cells = {k: G.key(c) for k, c in G.grid(wasteland).items() if -5 <= k[0] < 5 and -5 <= k[1] < 5}   # (game cells, for the edit)
S = CS.all_sites(lay)
g = CS.Grid(lay)
check('sites for every kind on the made-up island', all(S[k] for k in CS.KEEP), str({k: len(v) for k, v in S.items()}))
sh = [m for r in S['sharklurk'] for m in r['members']]
check('sharklurks in the reef water (80-450 deep), near the shore', all(CS.DEPTH[0] <= -lay.at(x, y) <= CS.DEPTH[1] for x, y, _z, _t in sh), str(sh[:3]))
check('… past the start\'s reach and not in Waikiki\'s surf', all(math.hypot(x - lay.start[0], y - lay.start[1]) >= CS.SHARK_START_OFF
      and math.hypot(x - lay.middle[0], y - lay.middle[1]) >= CS.SHARK_SURF for x, y, _z, _t in sh))
cr = [m for r in S['crab'] for m in r['members']]
check('crabs on the shore, just over the water', all(8 <= lay.at(x, y) <= CS.CRAB_TOP for x, y, _z, _t in cr))
every = [(k, m) for k in CS.KEEP for r in S[k] for m in r['members']]
check('nothing within its reach of the door or a marker', all(math.hypot(x - a, y - b) >= CS.KEEP[k][w.split(' ')[0]] for k, (x, y, _z, _t) in every
      for a, b, w in lay.spots), '')
check('nothing on the road', all(math.hypot(x, y - 9000.0) >= CS.ROAD_OFF for _k, (x, y, _z, _t) in every))
td = [m for r in S['toad'] for m in r['members']]
check('toads by the taro or on the valley floor', all(math.hypot(x - 8000, y - 12000) < CS.TARO_NEAR or g.valley()[g.cell(x, y)[1], g.cell(x, y)[0]] >= CS.VALLEY
      for x, y, _z, _t in td), str(td[:3]))
check('groups spaced (breadcrumbs, not scatter)', all(math.hypot(a['x'] - b['x'], a['y'] - b['y']) >= CS.APART[k]
      for k in CS.KEEP for i, a in enumerate(S[k]) for b in S[k][i + 1:]))
o, rep = CS.ops(G, server.PR, lay, slug='test')
adds = [x for x in o if x['op'] == 'add']
news = [x for x in o if x['op'] == 'record_new']
check('one step: eight records and every animal placed', len(news) == 8 and len(adds) == rep['animals'] > 0, '%d %d' % (len(news), len(adds)))
check('… each animal its kind\'s record, in a cell of the world', all(a['base'] in rep['keys'][4:] and a['cell'] in lay.cells.values() for a in adds))
made = server.edit(CS.STEP_LABEL, o)['made']
check('the keys as reserved', made[:len(rep['keys'])] == rep['keys'], '%d %s %s' % (len(made), made[-3:], rep['keys'][-3:]))
try:
    CS.ops(G, server.PR, lay, slug='test')
    check('doing it again is refused', False)
except ValueError:
    check('doing it again is refused', True)
