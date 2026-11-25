"""Waikiki's collectibles (collectibles.py) in a small mod of its own: all twenty models closed solids; one Undo makes the
quest that remembers, seven hula dolls and thirteen jade charms (each a MISC with its own model, weightless, and an OnAdd
script raising its SPECIAL by 1 or its skill by 5 once, counting the set, the set's reward at the end), the two rewards,
and places a doll on a real surface (lootplace.Seat) in a game room. Written and read back."""
import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import api_scripts  # noqa: E402
import browse  # noqa: E402
import collectibles as C  # noqa: E402
import espwrite  # noqa: E402
import gamedata  # noqa: E402
import health  # noqa: E402
import lootplace  # noqa: E402
import modelmake  # noqa: E402
import nifmake  # noqa: E402
import project  # noqa: E402
import questrec as qr  # noqa: E402
import robots as R  # noqa: E402
import server  # noqa: E402
import tes4  # noqa: E402
from activity import _new_key  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


M = C.models()
check('twenty models', len(M) == 20)
opened = [(k, modelmake.open_edges(d), nifmake.open_edges(m['shapes'])) for k, (d, m) in M.items()]
check('every one a closed solid', all(not a and not b for _k, a, b in opened), [o for o in opened if o[1] or o[2]][:2])
db, cb = C.doll_box(), C.charm_box()
check('a doll about a hand tall, a charm a few units', 9 <= db[5] - db[2] <= 16 and max(cb[3] - cb[0], cb[4] - cb[1]) <= 10, (db, cb))

G = server.GD = gamedata.GameData()
server.BR = browse.Browse(G, lambda: server.PR)
pr = server.PR = project.Project.create('Collect Test')
# the face score the jade set's reward bumps (repstanding's quest)
nq, ns = _new_key(pr), _new_key(pr)
nquest = qr.quest_record({'edid': 'FOLabNameOnWater', 'script': ns, 'name': '', 'flags': {'start_enabled': True}, 'priority': 50,
                          'delay': 5.0, 'stages': [], 'objectives': []})
c = api_scripts.scripts().compile('scn FOLabNameOnWaterScript\nshort huang\nBegin GameMode\nset huang to huang\nEnd\n', ns, 'quest', {nq: nquest})
pr.apply('the face score', [{'op': 'record', 'key': ns, 'record': api_scripts.scripts()._record_of(c, 'FOLabNameOnWaterScript')},
                            {'op': 'record', 'key': nq, 'record': nquest}])
room = G.key(next(f for f, (i, r) in G.forms.items() if r.tag == 'CELL' and G.edid(f) == 'CrimsonCaravanBarracks01'))
S = lootplace.Seat(G, pr, None)
S.solids.load_round([room])
tris = R._tris(G, pr, room)
spot = next(p for p in (S.at(x, y, 0.0, db, z, outside=False) for x, y, z in tris) if p)
rows = [{'kind': 'hula', 'stat': 'Luck', 'cell': room, 'p': spot, 'on': 'the floor', 'where': 'test', 'door': 999, 'people': 999}]
undo0 = len(pr.undo_stack)
ops, rep = C.ops(G, pr, (rows, []))
pr.apply(C.LABEL, ops)
check('one Undo, twenty items, one placed', len(pr.undo_stack) == undo0 + 1 and rep['items'] == 20 and len(rep['placed']) == 1, rep['placed'])
check('made again, it refuses', bool(C.plan(G, pr)[1]) and not C.plan(G, pr)[0])
os.makedirs(project.BUILD_DIR, exist_ok=True)
out = os.path.join(project.BUILD_DIR, 'Collect Test.esp')
espwrite.write(G, pr, out)
g = gamedata.GameData(plugins=list(gamedata.OFFICIAL) + [out])
i = len(g.plugins) - 1
mine = {tes4.zstr(g.fields(f).get('EDID', b'')): f for f, (n, r) in g.forms.items() if n == i}
sub = lambda e: dict(tes4.iter_subrecords(g.plugins[i].data(g.forms[mine[e]][1])))
doll = sub('FOLabHulaDollLuck')
check('the doll: its own model, named, weightless', b'folab\\collect\\hula_luck.nif' in doll['MODL'].lower()
      and doll['FULL'] == b'Hula Doll - Luck\x00' and struct.unpack('<if', doll['DATA'][:8]) == (0, 0.0), doll.get('DATA'))
check('it runs its own script', struct.unpack('<I', doll['SCRI'])[0] & 0xFFFFFF == mine['FOLabHulaDollLuckScript'] & 0xFFFFFF)
src = sub('FOLabHulaDollLuckScript')['SCTX']
check('picked up once: Luck +1, the count, Island Time at seven', b'Begin OnAdd player' in src and b'player.ModAV Luck 1' in src
      and b'FOLabCollectibles.hula7 == 0' in src and b'>= 7' in src and b'AddSpell FOLabIslandTime' in src)
jsrc = sub('FOLabJadeCharmEnergyWeaponsScript')['SCTX']
check('a charm: its skill +5, Jade Heart at thirteen, Huang face', b'player.ModAV EnergyWeapons 5' in jsrc and b'>= 13' in jsrc
      and b'AddSpell FOLabJadeHeart' in jsrc and b'FOLabNameOnWater.huang' in jsrc)
check('thirteen charms, seven dolls', sum(1 for e in mine if e.startswith('FOLabJadeCharm') and not e.endswith(('Script', 'Msg'))) == 13
      and sum(1 for e in mine if e.startswith('FOLabHulaDoll') and not e.endswith(('Script', 'Msg'))) == 7)
spell = sub('FOLabIslandTime')
check('Island Time: +10 Action Points', struct.unpack('<I', spell['EFIT'][:4])[0] == 10)
placed = [r for c_, rr in g.cell_refs.items() for f, (n, r) in rr.items() if n == i]
check('the doll placed in the room', len(placed) == 1)
check('the models among the mod\'s own files', os.path.isfile(os.path.join(__import__('library').assets_dir(pr), 'meshes', 'folab', 'collect', 'jade_speech.nif')))
h = health.check_file(g, out)
bad = [(x['kind'], x['count']) for x in h['groups'] if x['sev'] == 'error' and x['kind'] != 'mesh']    # (the models are the mod's own files: checked above)
check('the plugin passes health', not bad, bad)
