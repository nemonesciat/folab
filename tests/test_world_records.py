"""Regions, map markers, encounter zones, cell details, patrols and encounter spots: written to a plugin and read back, links
re-pointed to its master list. Nothing goes near the real game."""
import os
import struct
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import espwrite
import gamedata
import project
import tes4
import worldrec as R


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % detail if detail else ''))


G = gamedata.GameData()
W = next(w for w in G.worlds() if G.edid(w) == 'WastelandNV')
wk = G.key(W)
grid = G.grid(W)
pr = project.Project.create('World Records')

# some cells, from a part of the world that has them all
xy = next(k for k in sorted(grid, key=lambda k: (abs(k[0]), abs(k[1]))) if all((k[0] + d, k[1]) in grid for d in range(3)))
cells = [[xy[0] + d, xy[1]] for d in range(3)]
keys = [G.key(grid[tuple(c)]) for c in cells]

# a form of a DLC, so numbering matters: the plugin's masters won't line up with the load order's
weather = next(f for f, (i, r) in G.forms.items() if r.tag == 'WTHR')
sound = next(f for f, (i, r) in G.forms.items() if r.tag == 'SOUN')
stat = next(f for f, (i, r) in G.forms.items() if r.tag == 'STAT' and i == 0 and 'rock' in G.describe(f)[3].lower())
dlc = next((f for f, (i, r) in G.forms.items() if r.tag == 'WTHR' and i > 2), weather)

# --- a region ---
ops, rk = R.region_save(G, pr, {'world': wk, 'region': {'edid': 'FOLabDust', 'color': '#a07040', 'priority': 60,
                        'weathers': [{'key': G.key(weather), 'chance': 70}, {'key': G.key(dlc), 'chance': 30}],
                        'sounds': [{'key': G.key(sound), 'flags': 0, 'chance': 40}],
                        'objects': [{'key': G.key(stat), 'density': 5.0, 'slope_max': 40, 'radius': 64, 'size_var': 0.2, 'sink': 4.0}]}})
pr.apply('New region', ops)
check('a region gets a key of the mod\'s', rk.startswith('+') and pr.records[rk]['type'] == 'REGN')
pr.apply('Paint region', R.region_paint(G, pr, {'world': wk, 'key': rk, 'add': cells}))
check('painting puts it on each cell', all(rk in R.regions_of(G, pr, k) for k in keys))
listed = next(r for r in R.regions_list(G, pr, W) if r['key'] == rk)
check('the list knows its cells', sorted(map(tuple, listed['cells'])) == sorted(map(tuple, cells)), str(listed['cells']))
r = R.region_read(G, pr, rk)
check('it reads back as fields', r['edid'] == 'FOLabDust' and r['color'] == '#a07040' and len(r['weathers']) == 2 and len(r['sounds']) == 1 and len(r['objects']) == 1 and r['priority'] == 60, str(r['priority']))
check('… weather and objects by key', r['weathers'][0]['key'] == G.key(weather) and r['objects'][0]['key'] == G.key(stat) and r['objects'][0]['density'] == 5.0)
check('the outline of a row of cells is a box', [set(l) for l in R.outline(cells)] == [{(xy[0] * 4096.0, xy[1] * 4096.0), ((xy[0] + 3) * 4096.0, xy[1] * 4096.0), ((xy[0] + 3) * 4096.0, (xy[1] + 1) * 4096.0), (xy[0] * 4096.0, (xy[1] + 1) * 4096.0)}], str(R.outline(cells)))
check('a square of cells with a hole has two loops', len(R.outline([(x, y) for x in range(3) for y in range(3) if (x, y) != (1, 1)])) == 2)
check('squares only touching at a corner don\'t cross', len(R.outline([(0, 0), (1, 1)])) == 2)
check('the Scatter brush can use its objects', [o['key'] for o in R.scatter_set(G, pr, W, *cells[0])] == [G.key(stat)])
# a game's region painted too
gr = next(x for x in R.regions_list(G, pr, W) if not x['mine'] and x['cells'])
pr.apply('Paint', R.region_paint(G, pr, {'world': wk, 'key': gr['key'], 'add': [cells[0]]}))
check('a cell can be in two regions', set(R.regions_of(G, pr, keys[0])) >= {rk, gr['key']})
pr.apply('Unpaint', R.region_paint(G, pr, {'world': wk, 'key': rk, 'remove': [cells[2]]}))
check('Ctrl takes a cell out, and its area shrinks', rk not in R.regions_of(G, pr, keys[2]) and len(next(x for x in R.regions_list(G, pr, W) if x['key'] == rk)['cells']) == 2)

# --- a zone ---
ops, zk = R.zone_save(G, pr, {'zone': {'edid': 'FOLabZone', 'level': 12, 'flags': 1, 'owner': ''}})
pr.apply('New zone', ops)
pr.apply('Paint zone', R.zone_paint(G, pr, {'world': wk, 'key': zk, 'add': cells[:2]}))
z = next(x for x in R.zones_list(G, pr, W) if x['key'] == zk)
check('a zone: lowest level, its cells', z['level'] == 12 and z['flags'] == 1 and sorted(map(tuple, z['cells'])) == sorted(map(tuple, cells[:2])), str(z))
pr.apply('Unpaint', R.zone_paint(G, pr, {'world': wk, 'key': zk, 'remove': [cells[1]]}))
check('… taken off a cell', len(next(x for x in R.zones_list(G, pr, W) if x['key'] == zk)['cells']) == 1)
g_zone = next(x for x in R.zones_list(G, pr, W) if not x['mine'])
faction = next(f for f, (i, r) in G.forms.items() if r.tag == 'FACT')
ops, zk2 = R.zone_save(G, pr, {'zone': {'edid': 'FOLabOwned', 'level': 3, 'owner': G.key(faction), 'rank': 1, 'flags': 0}})
pr.apply('Owned', ops)
check('a zone with an owner', R.zone_read(G, pr, zk2)['owner'] == G.key(faction))

# --- a marker ---
at = [(xy[0] + 1.5) * 4096, (xy[1] + 0.5) * 4096, 1000.0]
marker = pr.apply('Marker', [R.marker_op(G, W, at, 'Dust Town', 5)])[0]
check('a marker is listed', [m['name'] for m in R.markers_list(G, pr, W)] == ['Dust Town'])

# --- cell details ---
music = next(f for f, (i, r) in G.forms.items() if r.tag == 'MUSC')
inside = next(c for c in sorted(G.interiors) if 'XCLL' in G.fields(c))
ik = G.key(inside)
d0 = R.cell_details(G, pr, ik)
check('a place\'s details are read from the game', 'XCLL' in d0['info'] and d0['info']['XCLL']['ambient'].startswith('#'), str(d0['info'].get('XCLL')))
light = dict(d0['info']['XCLL'], ambient='#102030', near=64.0)
pr.apply('Details', [R.cell_ops(G, pr, ik, {'XCMO': G.key(music), 'XOWN': G.key(faction), 'XCLL': light, 'FULL': 'Renamed Place'}),
                     R.cell_ops(G, pr, keys[1], {'XCMO': G.key(music)})])
d1 = R.cell_details(G, pr, ik)
check('… and changed', d1['info']['XCMO'] == G.key(music) and d1['info']['FULL'] == 'Renamed Place' and d1['info']['XCLL']['ambient'] == '#102030')
pr.undo()
check('Undo takes the lot back', ik not in pr.cellinfo and 'XCMO' not in (pr.cellinfo.get(keys[1]) or {}))
pr.redo()
check('Redo brings it back', ik in pr.cellinfo)

# --- patrol, encounter ---
npc = next(f for f, (i, r) in G.forms.items() if r.tag == 'NPC_' and i == 0 and 'PKID' in G.fields(f))
pts = [[at[0], at[1], 1000.0], [at[0] + 1000, at[1], 1000.0], [at[0] + 1000, at[1] + 5000, 1000.0]]
ops, patrol = R.patrol_ops(G, pr, {'world': wk, 'points': pts, 'base': G.key(npc), 'name': 'Dust Walk', 'wait': 7})
pr.apply('Patrol', ops)
check('a patrol: package, walker, a ring of markers', pr.records[patrol['package']]['type'] == 'PACK' and pr.records[patrol['actor']]['type'] == 'NPC_' and len(patrol['markers']) == 3)
walker = pr.records[patrol['actor']]
check('… its package is first on the walker', next(s for s in walker['subs'] if s['tag'] == 'PKID')['value'] == patrol['package'])
choices = R.encounter_choices(G, pr)
check('who can stand at a spot: leveled ones first', choices[0].get('leveled') and any(not c.get('leveled') for c in choices), str(choices[0]))
enc = pr.apply('Encounter', R.encounter_ops(G, pr, {'world': wk, 'p': [at[0], at[1] - 400, 1000.0], 'base': choices[0]['key'], 'count': 4, 'zone': zk}))
check('an encounter spot: four actors in the zone', len(enc) == 4 and all(any(e in c['refs'] and c['refs'][e].get('zone') == zk for c in pr.cells.values()) for e in enc))

# --- a road ---
import math
import navgen
import roadgen
for d in ((1, 0, 0), (0, 1, 0), (-3, 2, 0.5), (1, -4, -0.8), (0.2, 0.1, 0)):
    rx, ry, rz = roadgen.turn_along(*d)
    M = navgen._turn(rx, ry, rz)
    ln = math.sqrt(sum(c * c for c in d))
    ok = all(abs(M[k][0] - d[k] / ln) < 1e-6 for k in range(3)) and M[2][2] > 0.5
    check('a piece turned along %r lies along it, top up' % (d,), ok, str([round(M[k][0], 3) for k in range(3)]))
g = roadgen.Ground(G, pr, W)
gx, gy = next(k for k in sorted(grid, key=lambda k: abs(k[0] + 8) + abs(k[1] + 8)) if g.at(k[0] * 4096 + 2048, k[1] * 4096 + 2048) is not None and g.at((k[0] + 2) * 4096 + 2048, k[1] * 4096 + 2048) is not None)
ra, rb = [gx * 4096 + 2048.0, gy * 4096 + 2048.0], [(gx + 2) * 4096 + 2048.0, gy * 4096 + 2500.0]
ops, road = roadgen.road_ops(G, pr, W, {'a': ra, 'b': rb, 'settle': True})
adds = [o for o in ops if o['op'] == 'add']
lands = [o for o in ops if o['op'] == 'land']
check('a road: pieces from the game\'s own, along its length', len(adds) >= 8 and all(G.describe(G.from_key(o['base']))[1].startswith('WastelandRoad') for o in adds), '%d pieces, %d long' % (len(adds), road['length']))
gaps = [math.hypot(x['p'][0] - y['p'][0], x['p'][1] - y['p'][1]) for x, y in zip(adds[:-3], adds[1:-2])]
check('… each next to the last, no gaps', max(gaps) <= roadgen.PIECE, str(round(max(gaps))))
dirs = [abs(x['p'][5] - y['p'][5]) % (2 * math.pi) for x, y in zip(adds[:-3], adds[1:-2])]
check('… following the ground, each within a piece of it', all(abs(o['p'][2] - g.at(o['p'][0], o['p'][1])) < 200 for o in adds))
check('… the ground settled under it, whole cells of land', len(lands) >= 3 and all(len(o['land']['h']) == 1089 for o in lands) and all(o['land'].get('q') is not None for o in lands), str(len(lands)))
# (a cell's edge points must agree with the next cell's)
byxy = {G.cell_grid(G.from_key(o['cell'])): o['land']['h'] for o in lands}
bad = 0
for (x, y), h in byxy.items():
    o = byxy.get((x + 1, y))
    if o:
        bad += sum(1 for r in range(33) if abs(h[r * 33 + 32] - o[r * 33]) > 8)
check('… the land still meets at cell edges', not bad, str(bad))
under = [o for o in adds if G.key(grid[(int(o['p'][0] // 4096), int(o['p'][1] // 4096))]) in {x['cell'] for x in lands}]
pr.apply('A road', ops)
g2 = roadgen.Ground(G, pr, W)
check('… and lies under the road now', all(g2.at(o['p'][0], o['p'][1]) <= o['p'][2] + 8 for o in adds[:-2]), str(max(g2.at(o['p'][0], o['p'][1]) - o['p'][2] for o in adds[:-2])))
try:
    roadgen.find_way(g, [gx * 4096.0, gy * 4096.0], [gx * 4096.0 + 400000, gy * 4096.0 + 400000])
    check('a very long road is refused', False)
except roadgen.RoadError as e:
    check('a very long road is refused, in words', 'stretches' in str(e))

# --- the plugin ---
out = os.path.join(project.HOME, 'world records.esp')
espwrite.write(G, pr, out)
p = tes4.PluginFile(out)
masters = [m.lower() for m in p.header['masters']]
rows = {}
for rec, path in p.walk():
    rows.setdefault(rec.tag, []).append((rec, path))
own = len(masters) << 24
fid = lambda key: own | int(key[1:], 16) if key.startswith('+') else (masters.index(key.rsplit(':', 1)[0].lower()) << 24) | int(key.rsplit(':', 1)[1], 16)
check('the masters take in what the links need', 'falloutnv.esm' in masters and G.key(dlc).rsplit(':', 1)[0].lower() in masters, str(masters))

REG = next(r for r, _ in rows['REGN'] if r.formid == fid(rk))
subs = list(tes4.iter_subrecords(p.data(REG)))
d = dict(subs)
check('REGN read back: name, colour, world re-pointed', tes4.zstr(d['EDID']) == 'FOLabDust' and d['RCLR'][:3] == bytes((0xa0, 0x70, 0x40)) and struct.unpack('<I', d['WNAM'])[0] == fid(wk))
rdwt = struct.unpack('<6I', d['RDWT'])
check('… weather links re-pointed, chance kept', rdwt[0] == fid(G.key(weather)) and rdwt[3] == fid(G.key(dlc)) and rdwt[1] == 70, str(rdwt))
check('… sounds and objects re-pointed', struct.unpack_from('<I', d['RDSD'])[0] == fid(G.key(sound)) and struct.unpack_from('<I', d['RDOT'])[0] == fid(G.key(stat)))
check('… sections in the game\'s order', [struct.unpack_from('<I', x)[0] for t, x in subs if t == 'RDAT'] == [2, 3, 7])
check('… area: a corner list', 'RPLI' in d and len(d['RPLD']) % 8 == 0 and struct.unpack_from('<I', d['RPLI'])[0] == 1024)
pts_back = struct.unpack('<%df' % (len(d['RPLD']) // 4), d['RPLD'])
check('… the area of two cells', sorted(pts_back[0::2]) == sorted([xy[0] * 4096.0, (xy[0] + 2) * 4096.0] * 2), str(pts_back))
Gameform = next(r for r, _ in rows['CELL'] if r.formid == fid(keys[0]))
cd = list(tes4.iter_subrecords(p.data(Gameform)))
names = [t for t, _x in cd]
xclr = struct.unpack('<%dI' % (len(dict(cd)['XCLR']) // 4), dict(cd)['XCLR'])
check('CELL read back: XCLR has both regions, re-pointed', fid(rk) in xclr and fid(gr['key']) in xclr, str(xclr))
check('… XEZN to the zone', struct.unpack('<I', dict(cd)['XEZN'])[0] == fid(zk))
check('… all else the game\'s, in order', names.index('XCLC') < names.index('XCLR') < names.index('XEZN') and 'XCLW' in names)
c1 = dict(tes4.iter_subrecords(p.data(next(r for r, _ in rows['CELL'] if r.formid == fid(keys[1])))))
check('another cell\'s music re-pointed', struct.unpack('<I', c1['XCMO'])[0] == fid(G.key(music)))
ic = dict(tes4.iter_subrecords(p.data(next(r for r, _ in rows['CELL'] if r.formid == fid(ik)))))
check('a place inside: name, music, owner, its light', tes4.zstr(ic['FULL']) == 'Renamed Place' and struct.unpack('<I', ic['XOWN'])[0] == fid(G.key(faction)) and ic['XCLL'][:3] == bytes((0x10, 0x20, 0x30)) and struct.unpack_from('<f', ic['XCLL'], 12)[0] == 64.0)
z2 = dict(tes4.iter_subrecords(p.data(next(r for r, _ in rows['ECZN'] if r.formid == fid(zk2)))))
check('ECZN read back: owner re-pointed, level', struct.unpack_from('<I', z2['DATA'])[0] == fid(G.key(faction)) and z2['DATA'][5] == 3 and len(z2['DATA']) == 8)

m_rec, m_path = next((r, q) for r, q in rows['REFR'] if r.formid == fid(marker))
ms = list(tes4.iter_subrecords(p.data(m_rec)))
md = dict(ms)
check('a marker read back: map marker base, flags, name, type', struct.unpack('<I', md['NAME'])[0] == 0x10 and md['FNAM'] == b'\x03' and tes4.zstr(md['FULL']) == 'Dust Town' and md['TNAM'] == b'\x05\0' and 'XMRK' in md)
check('… in the game\'s order', [t for t, _x in ms] == ['NAME', 'XMRK', 'FNAM', 'FULL', 'TNAM', 'DATA'], str([t for t, _x in ms]))
pc = G.world_persistent[W]
check('… persistent, in the world\'s persistent cell', m_rec.flags & tes4.PERSISTENT and any(q[0] == tes4.G_CELL_PERSISTENT and (q[1] & 0xFFFFFF) == (pc & 0xFFFFFF) for q in m_path))

mk = [next(r for r, _ in rows['REFR'] if r.formid == fid(k)) for k in patrol['markers']]
ps = [dict(tes4.iter_subrecords(p.data(r))) for r in mk]
check('the patrol\'s markers link in a ring, each waiting as asked', [struct.unpack('<I', q['XLKR'])[0] for q in ps] == [mk[1].formid, mk[2].formid, mk[0].formid] and struct.unpack('<f', ps[0]['XPRD'])[0] == 7.0 and len(ps[0]['SCHR']) == 20)
check('… its markers are XMarkerHeading', struct.unpack('<I', ps[0]['NAME'])[0] == 0x34)
ach = next(r for r, _ in rows['ACHR'] if struct.unpack('<I', dict(tes4.iter_subrecords(p.data(r)))['NAME'])[0] == fid(patrol['actor']))
check('… the walker links to the first', struct.unpack('<I', dict(tes4.iter_subrecords(p.data(ach)))['XLKR'])[0] == mk[0].formid)
wrec = next(r for r, _ in rows['NPC_'] if r.formid == fid(patrol['actor']))
pid = [struct.unpack('<I', x)[0] for t, x in tes4.iter_subrecords(p.data(wrec)) if t == 'PKID']
check('… and its record names the package first, the rest re-pointed', pid[0] == fid(patrol['package']) and all(q >> 24 < len(masters) + 1 for q in pid))
enc_r = [r for tag in ('ACHR', 'ACRE') for r, _ in rows.get(tag, []) if r.formid in [fid(e) for e in enc]]
check('the encounter\'s actors are ACHR or ACRE, in the zone', len(enc_r) == 4 and all(struct.unpack('<I', dict(tes4.iter_subrecords(p.data(r)))['XEZN'])[0] == fid(zk) for r in enc_r))

G2 = gamedata.GameData(plugins=[q.path for q in G.plugins] + [out])
W2 = W
check('loaded with the game, the marker is in the world', any(G2.fields(f).get('FULL') == b'Dust Town\0' for f in G2.cell_refs[G2.world_persistent[W2]] if f in G2.forms and 'XMRK' in G2.fields(f)))
