"""Waikiki's people dressed for the island (peopledress, garmentprint): the print goes only on the cloth; a kind's
records get the keys they were planned with; the written plugin has each spawn of the mod's own named, its template the
game's, its inventory the game's but for the clothes, pirates all in the Fiends' factions; the shirts' meshes are the
game's with only the picture changed; every placed spawn outside swapped, one in a place of the mod's own left."""
import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import numpy as np  # noqa: E402

import espwrite  # noqa: E402
import gamedata  # noqa: E402
import garmentprint as gp  # noqa: E402
import library  # noqa: E402
import nifwrite  # noqa: E402
import peopledress as P  # noqa: E402
import project  # noqa: E402
import recordio  # noqa: E402
import tes4  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


gd = gamedata.GameData()
find = lambda tag, e: next(f for f, (i, r) in gd.forms.items() if r.tag == tag and gd.edid(f) == e)

# ---- the print: only on the cloth ----
for g in ('m', 'f'):
    mask = gp.cloth_mask(gd, g)
    M = np.asarray(mask)
    share = (M > 128).mean()
    check('%s: the cloth is a fair share of the picture' % g, 0.15 < share < 0.6, round(share, 3))
    for worn in (False, True):
        base = gp._picture(gd, gp.TEXTURES + gp.GARMENTS[g][2 if worn else 1])
        im = gp.paint(gd, g, ((30, 70, 140), (225, 60, 70), (40, 120, 80)), worn=worn, mask=mask)
        a, b = np.asarray(im, dtype=np.int16), np.asarray(base, dtype=np.int16)
        off = M == 0
        check('%s%s: nothing changes off the cloth' % (g, ' worn' if worn else ''), np.abs(a - b)[off].max() == 0)
        on = M == 255
        check('%s%s: the cloth is printed (blue ground shows)' % (g, ' worn' if worn else ''),
              (a[on][:, 2] > a[on][:, 0] + 20).mean() > 0.2)
base = gp._picture(gd, gp.TEXTURES + 'OutfitM.dds')
L = np.asarray(base.convert('L'), dtype=np.float32)[600:900, 40:400]
S = gp.shading(base, gp.cloth_mask(gd, 'm'))[600:900, 40:400]
jump = lambda a: max(float(np.abs(np.diff(a.mean(axis=ax), 2)).max()) for ax in (0, 1))
check('the old check lines are gone from the light the print takes (rows and columns of the shirt front even)',
      jump(L / L.mean()) > 0.3 and jump(S) < 0.1, (round(jump(L / L.mean()), 3), round(jump(S), 3)))
im = gp.paint(gd, 'm', ((235, 225, 200), (220, 90, 60), (60, 120, 90)))
d = gp.dds_of(im)
check('the picture is the game\'s kind of texture: DXT1, 1024 square, its smaller copies', d[84:88] == b'DXT1' and struct.unpack_from('<II', d, 12) == (1024, 1024) and struct.unpack_from('<I', d, 28)[0] == 11)

# ---- a small mod with one of each spawn outside, one Fiend in a place of its own ----
pr = project.Project.create('People Test')
world = next(w for w in gd.worlds() if gd.edid(w) == 'WastelandNV')
ck = gd.key(gd.grid(world)[(-18, 0)])
spawns = ['VSpawnProspectorAll', 'LvlFiend2GunVarNV', 'LvlRaider1MeleeVar', 'VViperGangSpawnGunA', 'VJackalGangSpawnFemale', 'LvlWastelander']
ops = [{'op': 'add', 'cell': ck, 'base': gd.key(find('NPC_', e)), 'p': [-73000 + 200 * n, 1000, 0, 0, 0, 0], 's': 1} for n, e in enumerate(spawns)]
placed = pr.apply('people', ops)
inside = gd.key(next(c for c in gd.interiors if gd.source(c)[0] == 0))
pr.cells['+INSIDE'] = {'refs': {'+999999': {'base': gd.key(find('NPC_', 'LvlFiend2GunVarNV')), 'p': [0, 0, 0, 0, 0, 0], 's': 1}}}

reps = {}
for kind in ('surfers', 'pirates'):
    first = pr.next_id
    ops, rep = P.plan(gd, pr, kind)
    made = pr.apply('Dress ' + kind, ops)
    news = sum(1 for o in ops if o['op'] == 'record_new')
    check('%s: the records got the keys they were planned with' % kind, made[:news] == ['+%06X' % (first + n) for n in range(news)])
    reps[kind] = rep
    try:
        P.plan(gd, pr, kind)
        check('%s: planning a kind again is refused' % kind, False)
    except ValueError:
        check('%s: planning a kind again is refused' % kind, True)
del pr.cells['+INSIDE']                   # (a place with no record can't be written: only its swap was the point)
check('surfers: the prospector swapped', reps['surfers']['swapped'] == {'VSpawnProspectorAll': 1})
check('pirates: every Mojave gang and the wastelander swapped', set(reps['pirates']['swapped']) == set(spawns[1:]))
check('pirates: the one in a place of the mod\'s own left', reps['pirates']['inside_left'] == {'LvlFiend2GunVarNV': 1})

path = pr.plugin_path()
espwrite.write(gd, pr, path)
gd2 = gamedata.GameData(plugins=list(gamedata.OFFICIAL) + [path])
me = len(gd2.plugins) - 1
own = lambda k: (me << 24) | int(k[1:], 16)
to = lambda v: gd2.to_global(me, v)
raw = lambda fid: list(tes4.iter_subrecords(gd2.plugins[gd2.forms[fid][0]].data(gd2.forms[fid][1])))
tag_of = lambda fid: gd2.forms[fid][1].tag

refs = [(fid, e) for fid, e in gd2.forms.items() if e[1].tag == 'ACHR' and (fid >> 24) == me]
names = []
for fid, _e in refs:
    base = to(struct.unpack('<I', dict(raw(fid))['NAME'])[0])
    names.append(tes4.zstr(dict(raw(base)).get('FULL', b'')))
check('every placed spawn is one of the mod\'s own, named Surfer or Pirate', sorted(names) == ['Pirate'] * 5 + ['Surfer'], names)

fiend_facs = [struct.unpack_from('<I', x)[0] for t, x in tes4.iter_subrecords(gd.plugins[gd.forms[find('NPC_', 'Fiend2GunAAFTEMPLATENV')][0]].data(gd.forms[find('NPC_', 'Fiend2GunAAFTEMPLATENV')][1])) if t == 'SNAM']
fiend_facs = [gd.key(gd.to_global(gd.forms[find('NPC_', 'Fiend2GunAAFTEMPLATENV')][0], f)) for f in fiend_facs]
for kind, rep in reps.items():
    for src, info in rep['records'].items():
        s = raw(own(info['key']))
        d = dict(s)
        game = recordio.load(gd, find('NPC_', src))
        flags = struct.unpack_from('<H', d['ACBS'], 22)[0]
        check('%s: template the game\'s, name, base data and inventory its own' % src,
              gd2.key(to(struct.unpack('<I', d['TPLT'])[0])) == recordio.field(game, 'TPLT') and not flags & 0x180 and
              flags | 0x180 | (0x04 if kind == 'pirates' else 0) == P._num(game, 'ACBS', 'Template flags') | 0x180 | (0x04 if kind == 'pirates' else 0))
        inv = recordio.load(gd, P.inventory_source(gd, find('NPC_', src)))
        keep = sorted(next(f['value'] for f in s2['fields'] if f.get('name') == 'Item') for n, s2 in enumerate(inv['subs'])
                      if s2['tag'] == 'CNTO' and n not in dict(P._clothing(gd, inv)))
        items = [gd2.key(to(struct.unpack_from('<I', x)[0])) for t, x in s if t == 'CNTO']
        ours = [k for k in items if (gd2.from_key(k) >> 24) == me]
        check('%s: every item of the game\'s but its clothes, and the three clothing lists' % src,
              sorted(k for k in items if (gd2.from_key(k) >> 24) != me) == keep and len(ours) == 3 and all(tag_of(gd2.from_key(k)) == 'LVLI' for k in ours))
        if kind == 'pirates':
            facs = [gd2.key(to(struct.unpack_from('<I', x)[0])) for t, x in s if t == 'SNAM']
            check('%s: in the Fiends\' factions, not its own gang\'s' % src, facs == fiend_facs and flags & 0x04 == 0)

root = library.assets_dir(pr)
shirts = [fid for fid, e in gd2.forms.items() if e[1].tag == 'ARMO' and (fid >> 24) == me]
check('six outfits of the mod\'s own (three prints, clean and worn)', len(shirts) == 6, len(shirts))
for fid in shirts:
    d = dict(raw(fid))
    name = tes4.zstr(d['FULL'])
    models = [tes4.zstr(d[t]) for t in ('MODL', 'MOD3', 'MOD2')]
    ok = all(os.path.exists(os.path.join(root, 'meshes', m)) for m in models)
    pics = set()
    for m in models:
        data = open(os.path.join(root, 'meshes', m), 'rb').read()
        pics |= {t['path'].lower() for t in nifwrite.textures_in(data)}
    mine = [p for p in pics if '\\folab\\' in p]
    check('%s: its three models among the mod\'s files, drawn with its own pictures' % name,
          ok and len(mine) == 2 and all(os.path.exists(os.path.join(root, p)) for p in mine), models)
    check('%s: no texture hashes or alternate textures of the game\'s models left' % name, not any(t in d for t in ('MODT', 'MO2T', 'MO3T', 'MODS', 'MO2S', 'MO3S')))
    game = dict(tes4.iter_subrecords(gd.plugins[gd.forms[find('ARMO', P.OUTFIT)][0]].data(gd.forms[find('ARMO', P.OUTFIT)][1])))
    check('%s: worn where the game\'s outfit is (body slots, armour values)' % name, d['BMDT'] == game['BMDT'] and d['DATA'] == game['DATA'] and d['DNAM'] == game['DNAM'])
lists = [fid for fid, e in gd2.forms.items() if e[1].tag == 'LVLI' and (fid >> 24) == me]
check('six clothing lists (body, head, eyes for each)', len(lists) == 6)
for fid in lists:
    s = raw(fid)
    entries = [tag_of(to(struct.unpack_from('<I', x, 4)[0])) for t, x in s if t == 'LVLO']
    check('%s: only apparel in it' % gd2.edid(fid), entries and all(e == 'ARMO' for e in entries), entries)

# ---- the Mojave's gangs taken out of the mod's own places (the hotels' floors), nothing else ----
pr2 = project.Project.create('People Clear Test')
key = lambda tag, e: gd.key(find(tag, e))
side = {e: P.mojave_side(gd, key('NPC_', e)) for e in ('PowderGangerGunAAMTEMPLATE', 'LvlFiend2GunVarNV', 'LvlRaider1MeleeVar',
                                                      'VJackalGangSpawnMale', 'VViperGangSpawnGunA', 'VSpawnProspectorAll')}
check('the Mojave\'s sides told by their factions', side == {'PowderGangerGunAAMTEMPLATE': 'Powder Gangers', 'LvlFiend2GunVarNV': 'Fiends',
      'LvlRaider1MeleeVar': 'Raiders', 'VJackalGangSpawnMale': 'Jackals', 'VViperGangSpawnGunA': 'Vipers', 'VSpawnProspectorAll': None}, side)
check('a creature and a record of the mod\'s own are no Mojave side',
      P.mojave_side(gd, key('CREA', 'CrFeralGhoul1A')) is None and P.mojave_side(gd, '+000800') is None)
spot = lambda b, **kw: dict({'base': b, 'p': [0, 0, 0, 0, 0, 0], 's': 1}, **kw)
pr2.cells['+PLACE'] = {'refs': {'+900001': spot(key('NPC_', 'PowderGangerGunAAMTEMPLATE')), '+900002': spot(key('NPC_', 'LvlFiend2GunVarNV')),
                                '+900003': spot(key('CREA', 'CrFeralGhoul1A')), '+900004': spot(key('NPC_', 'LvlFiend2GunVarNV')),
                                '+900005': spot(key('NPC_', 'VSpawnProspectorAll'), props={'parent': {'ref': '+900004'}})}}
pr2.cells[ck] = {'refs': {'+900006': spot(key('NPC_', 'LvlFiend2GunVarNV'))}}
ops, rep = P.clear_inside(gd, pr2)
pr2.apply('clear', ops)
check('the gangs in a place of the mod\'s own removed, one another ref names kept',
      sorted(pr2.cells['+PLACE']['refs']) == ['+900003', '+900004', '+900005'] and rep['kept_named'] == ['+900004'], (sorted(pr2.cells['+PLACE']['refs']), rep))
check('nothing outside touched', list(pr2.cells[ck]['refs']) == ['+900006'])
check('the report counts by side', rep['removed'] == {'+PLACE': {'Powder Gangers': 1, 'Fiends': 1}}, rep['removed'])
pr2.undo()
check('one Undo puts them back', len(pr2.cells['+PLACE']['refs']) == 5)

# ---- the shoes never printed (they share the outfit's picture: the man's V between his shirt fronts is their leather) ----
for g in ('m', 'f'):
    M = np.asarray(gp.cloth_mask(gd, g))
    h, w = M.shape
    feet = []
    for s in gp._shapes(gd, g, gp.GARMENTS[g][1]):
        uv, idx, Pz = s['uv'], s['i'], s['p']
        for t in range(0, len(idx), 3):
            ks = [idx[t + k] for k in range(3)]
            if max(Pz[3 * k + 2] for k in ks) < 12:
                cu, cv = sum(uv[2 * k] for k in ks) / 3, sum(uv[2 * k + 1] for k in ks) / 3
                feet.append(M[min(h - 1, int(cv * h)), min(w - 1, int(cu * w))])
    check('%s: no shoe printed' % g, feet and max(feet) == 0, (len(feet), max(feet) if feet else None))

# ---- board shorts: the Powder Gang's knee-length shorts printed (a woman in her dress), a third of the surfers' list ----
sm = np.asarray(gp.shorts_mask(gd))
check('shorts: the print is a fair share of their picture', 0.08 < (sm > 128).mean() < 0.45, round((sm > 128).mean(), 3))
skin = []
for part in ('m',):
    for s in gp.shorts_shapes(gd, part):
        uv, idx, Pz = s['uv'], s['i'], s['p']
        for t in range(0, len(idx), 3):
            ks = [idx[t + k] for k in range(3)]
            z = sum(Pz[3 * k + 2] for k in ks) / 3
            if gp.HIPS[0] + 4 < z < gp.HIPS[1] - 4 and sum(uv[2 * k] for k in ks) / 3 > gp.STRAP_U + 0.02:
                cu, cv = sum(uv[2 * k] for k in ks) / 3, sum(uv[2 * k + 1] for k in ks) / 3
                skin.append(sm[int(cv * 1023), int(cu * 1023)])
check('shorts: the legs and seat printed', skin and np.mean(np.asarray(skin) == 255) > 0.9, round(float(np.mean(np.asarray(skin) == 255)), 3))
before = {k: [s for s in pr.records[k]['subs'] if s['tag'] == 'LVLO'] for k, r in pr.records.items()
          if (recordio.field(r, 'EDID') or '') in ('FOLabSurferBodyList', 'FOLabPirateBodyList')}
first = pr.next_id
ops, rep = P.shorts_ops(gd, pr)
made = pr.apply('shorts', ops)
check('shorts: the keys as planned', made[:6] == ['+%06X' % (first + n) for n in range(6)], made[:6])
for kind, info in rep['lists'].items():
    rows = [s for s in pr.records[info['list']]['subs'] if s['tag'] == 'LVLO']
    got = [next(f['value'] for f in s['fields'] if f.get('code') == 'F') for s in rows]
    olds = [next(f['value'] for f in s['fields'] if f.get('code') == 'F') for s in before[info['list']]]
    check('%s: every old entry twice and three shorts once' % kind, len(rows) == 2 * len(olds) + 3 and all(got.count(o) == 2 * olds.count(o) for o in set(olds)), len(rows))
try:
    P.shorts_ops(gd, pr)
    check('shorts: a second time refused', False)
except ValueError:
    check('shorts: a second time refused', True)
path3 = path[:-4] + ' shorts.esp'          # (gd2 holds the first file open)
espwrite.write(gd, pr, path3)
gd3 = gamedata.GameData(plugins=list(gamedata.OFFICIAL) + [path3])
me3 = len(gd3.plugins) - 1
sor = dict(tes4.iter_subrecords(gd.plugins[gd.forms[find('ARMO', P.OUTFIT)][0]].data(gd.forms[find('ARMO', P.OUTFIT)][1])))
for e, info in rep['shorts'].items():
    fid = (me3 << 24) | int(info['key'][1:], 16)
    d = dict(tes4.iter_subrecords(gd3.plugins[gd3.forms[fid][0]].data(gd3.forms[fid][1])))
    models = [tes4.zstr(d[t]) for t in ('MODL', 'MOD3', 'MOD2')]
    pics = set()
    for m in models:
        pics |= {t['path'].lower() for t in nifwrite.textures_in(open(os.path.join(root, 'meshes', m), 'rb').read())}
    mine = [p for p in pics if '\\folab\\' in p]
    check('%s: clothes as the shirts; a man\'s shorts and their folded copy, a woman\'s printed dress' % e,
          d['BMDT'] == sor['BMDT'] and d['DATA'] == sor['DATA'] and 'shorts' in models[0] and 'shorts' in models[2] and
          models[1].endswith('_f.nif') and 'shorts' not in models[1] and all(os.path.exists(os.path.join(root, p)) for p in mine), models)
