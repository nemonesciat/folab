"""Night lights (nightlights.py): every lit piece builds and glows only where it should, its day twin is the same model
with nothing glowing and no flames, a string reaches from hook to hook whatever the gap, hung pieces hang under their
hook, the dusk switch compiles and makes the marker, script and quest as the mod's next three things, and every lit
thing placed is the marker's child (the day twins the opposite way)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import api_scripts  # noqa: E402
import browse  # noqa: E402
import gamedata  # noqa: E402
import modelsets  # noqa: E402
import nif  # noqa: E402
import nightlights as N  # noqa: E402
import project  # noqa: E402
import server  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


modelsets._all_sets()
lit = [k for k in modelsets.PIECES if k.startswith('night_') and not k.endswith('_day')]
check('every fixed piece is registered', all('night_' + k in modelsets.PIECES for k in N.FIXED))
bad, glowless, twins = [], [], []
for k in lit:
    m = modelsets.build(k)
    sh = nif.mesh_from_nif(m['nif'])
    if not sh or m['triangles'] > 4000:
        bad.append(k)
    glows = [s for s in sh if s.get('glow')]
    if k[6:] not in N.UNLIT and k[6:] not in N.FLAMES and not glows:
        glowless.append(k)
    if k + '_day' in modelsets.PIECES:
        d = modelsets.build(k + '_day')
        dsh = nif.mesh_from_nif(d['nif'])
        if any(s.get('glow') for s in dsh) or d['box'][5] > m['box'][5] + 0.5 or [round(v) for v in d['box'][:2]] != [round(v) for v in m['box'][:2]] and 'torch' not in k and 'fire' not in k:
            twins.append(k)
check('every lit piece builds, under 4,000 triangles', not bad, bad)
check("every lit piece has something glowing (a torch's light is the game's fire)", not glowless, glowless)
cut = sorted(k for k in modelsets.PIECES if k.startswith('night_') for v in modelsets.PIECES[k]['describe']()['looks'].values() if v.get('alpha'))
check("nothing in the set is see-through (flames are the game's fire: drawn cards showed bars along their tops)", not cut, cut)
check('every day twin glows nowhere and is no bigger', not twins, twins)
check('the generator has no twin (nothing on it glows)', 'night_generator_day' not in modelsets.PIECES)
drawn = []
for k in modelsets.PIECES:
    m = modelsets.build(k) if modelsets.fires_of(k) else None
    if m and any(s.get('alpha') and 'flame' in (s.get('tex') or '').lower() for s in nif.mesh_from_nif(m['nif'])):
        drawn.append(k)
check("no piece of any set draws a flame (the game's fire stands at its spots)", not drawn and modelsets.fires_of('tiki_torch_lit') == [(0.0, 0.0, 180.0, 0.35)], drawn)
check("torches and fire pits burn with the game's own fire", set(N.FLAMES) == {'torch', 'fire_pit'}
      and all(e == 'FXFireSmall01' and 0.3 <= row[-1] <= 1 for rows in N.FLAMES.values() for e, *row in rows), N.FLAMES)
for k in ('night_paper_lantern_red', 'night_oil_lamp'):
    b = modelsets.build(k)['box']
    check(k + ' hangs under its hook', abs(b[5]) < 0.5 and b[2] < -40, b)

for L, dz in ((240, 0), (655, 37), (1180, -90)):
    key, L2, dz2 = N.string_piece('paper', L, dz)
    b = modelsets.build(key)['box']
    check('a string %d long, %d up reaches its far hook' % (L, dz), abs(b[3] - L2) < 3 and abs(b[0]) < 3 and abs(max(0, dz2) - b[5]) < 3, b)
    check('  and sags under both hooks', b[2] < min(0, dz2) - 10, (b[2], N.sag_of(L2)))

# the switch, against a fresh mod
G = server.GD = gamedata.GameData()
server.BR = browse.Browse(G, lambda: server.PR)
pr = server.PR = project.Project.create('Night Test')
api_scripts.setup(lambda: server.GD, lambda: server.PR, lambda: server.BR, lambda: server.state())
cell = next(G.key(c) for c in G.grid(next(f for f, (_i, r) in G.forms.items() if r.tag == 'WRLD' and G.edid(f) == 'WastelandNV')).values())
nid = pr.next_id
ops, mk = N.switch_ops(G, pr, cell, (0.0, 0.0, 0.0))
check('the marker is the next thing made', mk == '+%06X' % nid and ops[0]['op'] == 'add', mk)
check('the marker is persistent, disabled and named', ops[0]['extra'] == {'persistent': True, 'edid': N.MARKER, 'props': {'disabled': True}})
check('then the script, then the quest', [o['op'] for o in ops[1:]] == ['record_new', 'record_new'] and ops[1]['record']['type'] == 'SCPT' and ops[2]['record']['type'] == 'QUST')
src = N.script_source()
check('the script turns the marker on at dusk and off at dawn', 'GameHour >= 19 || GameHour < 6' in src and N.MARKER + '.Enable' in src and N.MARKER + '.Disable' in src)
made = server.edit('night switch', ops)['made']
check('applied, the marker is where switch_ops said', any(mk in (c.get('refs') or {}) for c in pr.cells.values()), made)


class _L(N.Lighter):
    """A Lighter with no world: only what put does with the marker."""
    def __init__(self):
        self.gd, self.pr, self.marker = G, pr, mk
        self.grid = {(0, 0): G.from_key(cell)}
        self.ops, self.first, self.keys, self.draws_of = [], [], {}, {}
        self.cell_lights, self.cell_draws, self.by, self.lit, self.unlit = {}, {}, {}, 0, 0
        self.light_key = {G.edid(f): G.key(f) for f, (_i, r) in G.forms.items() if r.tag == 'LIGH' and G.edid(f) in ('FireBrightOrange', 'LamplightWarm')}
        self.lights = []
        self.fire_key, self.flames = N.fire_keys(G), 0


L = _L()
L.put('night_torch', 100, 100, 0, 0, foot=False)
L.put('night_torch', 300, 100, 0, 0, foot=False)            # (its light too near the first's: no light)
adds = [o for o in L.ops if o['op'] == 'add']
par = [(o['extra'].get('props') or {}).get('parent') for o in adds]
check("a torch is its lit self, its day twin, the game's fire and its light", len(adds) == 7, len(adds))
check("lit pieces, fires and lights are the marker's children, the twins the opposite way",
      all(p and p['ref'] == mk for p in par) and [p['opposite'] for p in par] == [False, True, False, False, False, True, False], par)
fires = [o for o in adds if o['base'] == L.fire_key['FXFireSmall01']]
check("the fire burns in the torch's cup, small", len(fires) == 2 and fires[0]['p'][2] == 180 and fires[0]['s'] == 0.35, fires[:1])
# (a mod with its night lights already: flame_fix adds the fire to every lit torch, once)
server.edit('torches', L.first + L.ops[:2])
tops, _info = modelsets.put(pr, 'tiki_torch_lit')
server.edit('a beach torch', tops + [{'op': 'add', 'cell': cell, 'base': '$model_tiki_torch_lit', 'p': [500.0, 0.0, 10.0, 0.0, 0.0, 1.0], 's': 2.0}])
fx, frep = N.flame_fix(G, pr)
night_fx = [o for o in fx if o.get('extra')]
beach_fx = [o for o in fx if not o.get('extra')]
check('flame_fix adds a fire to a night torch that has none, under the marker', len(night_fx) == 1 and frep['torch'] == 1 and night_fx[0]['extra']['props']['parent']['ref'] == mk, frep)
check('and to a torch that burns all day, with no parent, scaled with it', len(beach_fx) == 1 and beach_fx[0]['s'] == 0.7 and beach_fx[0]['p'][2] == 370.0, beach_fx)
server.edit('fires', fx)
check('and nothing the second time', N.flame_fix(G, pr)[0] == [], N.flame_fix(G, pr)[1])
check('no second light within LIGHT_APART', L.lit == 1 and L.unlit == 1, (L.lit, L.unlit))
