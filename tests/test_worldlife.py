"""Life for a world (worldlife.py): its own weather, water and sound as a region over every cell; zones that get harder with
distance from the start; markers; who stands at camps and in the open, none of them hostile near the start; a settlement.
All as ops the project takes, and a plugin the writer makes of them."""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import espwrite  # noqa: E402
import gamedata  # noqa: E402
import health  # noqa: E402
import project  # noqa: E402
import roadgen  # noqa: E402
import worldlife  # noqa: E402
import worldrec  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


gd = gamedata.GameData()
world = next(w for w in gd.worlds() if gd.edid(w) == 'WastelandNVmini')
grid = gd.grid(world)
g = roadgen.Ground(gd, None, world)
cells = sorted(grid)
mid = cells[len(cells) // 2]
start = [mid[0] * 4096.0 + 2048, mid[1] * 4096.0 + 2048]
pr = project.Project.create('Alive')
import land  # noqa: E402
flat = float(round(g.at((mid[0] + 2) * 4096.0, (mid[1] + 2) * 4096.0) / 8) * 8)
lops = []
for dx in (1, 2):
    for dy in (1, 2):
        form = land.decode(gd, gd.land_at(world, mid[0] + dx, mid[1] + dy), {})
        form['h'] = [flat] * 1089
        lops.append({'op': 'land', 'cell': gd.key(grid[(mid[0] + dx, mid[1] + dy)]), 'land': form})
pr.apply('level', lops)
g = roadgen.Ground(gd, pr, world)
L = worldlife.Life(gd, pr, world, start, seed=3)
L.air('TestAir', [('NVDLC02ZionValleyWeather', 70), ('NVDLC02ZVRainWeather', 30), ('NoSuchWeather', 5)], 'AudioExtDesertDefaultLake', 'NVDLC02Water', 'NVDLC02ZionPeaceful')
L.zones('Test')
far = max(cells, key=lambda k: max(abs(k[0] - mid[0]), abs(k[1] - mid[1])))
fx, fy = far[0] * 4096.0 + 2048, far[1] * 4096.0 + 2048
L.marker(fx, fy, 'The Far Place', 'military')
L.people([[start[0] + 300, start[1], 'raiders'], [fx, fy, 'raiders'], [start[0] + 600, start[1], 'camp'], [fx + 900, fy, 'nosuch']])
L.wildlife(lambda x, y: 'grass')
hx, hy = (mid[0] + 2) * 4096.0, (mid[1] + 2) * 4096.0      # (the middle of the ground levelled for it below)
ok = L.settlement('Haven', hx, hy)
ops, rep = L.done()
check('it says what it did', all(k in rep for k in ('air', 'zones', 'markers', 'people', 'wildlife', 'actors')), sorted(rep))
made = pr.apply('Life', ops)
regions = [k for k, r in pr.records.items() if r['type'] == 'REGN']
zones = [k for k, r in pr.records.items() if r['type'] == 'ECZN']
check('one region and three zones are made', len(regions) == 1 and len(zones) == 3, (len(regions), len(zones)))
d = worldrec.region_read(gd, pr, regions[0])
check('the region has the weathers the game has, by chance, and the sounds of the one named', [w['chance'] for w in d['weathers']] == [70, 30] and len(d['sounds']) > 10
      and d['weathers'][0]['name'] == 'NVDLC02ZionValleyWeather', (d['weathers'], len(d['sounds'])))
infos = [pr.cellinfo.get(gd.key(c)) or {} for c in grid.values()]
check('every cell is in it, with the water and the music', all(regions[0] in i.get('XCLR', []) and gd.edid(gd.from_key(i['XCWT'])) == 'NVDLC02Water'
                                                               and gd.edid(gd.from_key(i['XCMO'])) == 'NVDLC02ZionPeaceful' for i in infos), len(infos))
level = lambda k: next(s for s in pr.records[pr.cellinfo[gd.key(grid[k])]['XEZN']]['subs'] if s['tag'] == 'DATA')
lv = lambda k: next(f['value'] for f in level(k)['fields'] if f.get('name') == 'Min level')
check('the start is the easiest zone, the far side harder', lv(mid) == 1 and lv(far) > lv(mid), (lv(mid), lv(far)))
check('no cell is easier than one nearer the start', all(lv(a) <= lv(b) for a in cells for b in cells
                                                         if max(abs(a[0] - mid[0]), abs(a[1] - mid[1])) < max(abs(b[0] - mid[0]), abs(b[1] - mid[1]))))
refs = [r for c in pr.cells.values() for r in c['refs'].values()]
markers = [r for r in refs if (r.get('extra') or r).get('marker') or r.get('marker')]
names = sorted((r.get('marker') or (r.get('extra') or {}).get('marker'))['name'] for r in markers)
check('the places are named on the map', names == ['Haven', 'The Far Place'], names)
actors = [r for r in refs if gd.forms[gd.from_key(r['base'])][1].tag in ('NPC_', 'CREA')]
edid = lambda r: gd.edid(gd.from_key(r['base']))
hostile = [r for r in actors if any(w in edid(r).lower() for w in ('raider', 'fiend', 'jackal', 'viper', 'ghoul', 'gecko', 'mantis', 'cazador', 'lurk', 'scorpion', 'dog', 'molerat', 'coyote', 'nightstalker', 'bloatfly'))]
near = [r for r in hostile if math.hypot(r['p'][0] - start[0], r['p'][1] - start[1]) < worldlife.SAFE - 400]
check('raiders stand at the far camp, none at the one by the start', any(math.hypot(r['p'][0] - fx, r['p'][1] - fy) < 600 for r in hostile) and not near, (len(hostile), len(near)))
check('prospectors keep their camp by the start', any('prospector' in edid(r).lower() and math.hypot(r['p'][0] - start[0] - 600, r['p'][1] - start[1]) < 600 for r in actors))
check('there is life in the open', rep['wildlife']['groups'] >= 1 and len(hostile) >= 3, rep['wildlife'])
check('everyone stands on the ground', all(abs(r['p'][2] - g.at(r['p'][0], r['p'][1]) - 4.0) < 0.2 for r in actors), len(actors))
check('a settlement stands with its people and its walls', ok and rep['settlement']['folk'] >= 6 and rep['settlement']['things'] >= 20, rep.get('settlement'))
check('and nothing hostile is put near it', not any(math.hypot(r['p'][0] - hx, r['p'][1] - hy) < 1500 for r in hostile))
path = pr.plugin_path()
n = espwrite.write(gd, pr, path)
h = health.check_file(gd, path)
check('the writer makes a plugin of it with nothing wrong', n > 1000 and h['summary']['error'] == 0, h['summary'])
