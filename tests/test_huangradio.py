"""The Huang's numbers and the hold's watch (huangradio.py) in a small mod of its own, from a given plan (the real plan
reads the freighter's places): stand-ins for the Huang's faction, reputation and face score, the hold key, the Shouwei's
armour, a radar terminal, two game rooms for the hold and the house (a stove, a door to the deck and a hatch); one Undo
makes the watchman (a face nobody has, his two meals before staying put, his script), the hatch picked at Hard and opened
from inside, the decoding item with its note, and his two lines in Mandarin, subtitled. The bulletin's pinyin reads and
its tune is made. Written and read back."""
import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import api_scripts  # noqa: E402
import browse  # noqa: E402
import espwrite  # noqa: E402
import factionfolk as ff  # noqa: E402
import g2pzh  # noqa: E402
import gamedata  # noqa: E402
import health  # noqa: E402
import huangradio as HR  # noqa: E402
import piratedeal as PD  # noqa: E402
import project  # noqa: E402
import questrec as qr  # noqa: E402
import recordio  # noqa: E402
import server  # noqa: E402
import terminals  # noqa: E402
import tes4  # noqa: E402
from activity import _new_key  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


G = server.GD = gamedata.GameData()
server.BR = browse.Browse(G, lambda: server.PR)
pr = server.PR = project.Project.create('Numbers Test')
key = lambda e, tag: G.key(next(f for f, (i, r) in G.forms.items() if r.tag == tag and G.edid(f) == e))


def copy_as(tag, src, edid):
    rec = recordio.load(G, G.from_key(key(src, tag)))
    rec['src'] = ''
    recordio.set_field(rec, 'EDID', edid, label='Editor ID')
    return rec
server.edit('stand-ins', [{'op': 'record_new', 'record': ff._faction(G, *ff.FACTIONS['huang'])},
                          {'op': 'record_new', 'record': PD._rep_record(G, 'FOLabRepHuang', 'The Huang', 'RepNVBoomer')},
                          {'op': 'record_new', 'record': copy_as('ARMO', 'ArmorLeatherReinforced', 'FOLabHuangLamellar')},
                          {'op': 'record_new', 'record': copy_as('KEYM', 'VFSSupplyKey', 'FOLabFreighterHoldKey')}])
nq, ns = _new_key(pr), _new_key(pr)
nquest = qr.quest_record({'edid': 'FOLabNameOnWater', 'script': ns, 'name': '', 'flags': {'start_enabled': True}, 'priority': 50,
                          'delay': 5.0, 'stages': [], 'objectives': []})
c = api_scripts.scripts().compile('scn FOLabNameOnWaterScript\nshort huang\nBegin GameMode\nset huang to huang\nEnd\n', ns, 'quest', {nq: nquest})
pr.apply('the face score', [{'op': 'record', 'key': ns, 'record': api_scripts.scripts()._record_of(c, 'FOLabNameOnWaterScript')},
                            {'op': 'record', 'key': nq, 'record': nquest}])
t_ops, t_keys = terminals.ops(G, pr, terminals.plan('Terminal: FOLabRadarDomeTerminal\nName: Radar\nModel: desk\nLock: none\n'
                                                    'Welcome:\n  RADAR\n== Read the log\nSays: Nothing.\n'))
pr.apply('terminal', t_ops)
hold, house = key('CrimsonCaravanBarracks01', 'CELL'), key('SharecropperBarracks01', 'CELL')
world = next(w for c_, w in G.ext_cells.items() if G.edid(w) == 'WastelandNV')
deck = G.key(G.grid(world)[(-18, 0)])
ks = {n: _new_key(pr) for n in ('stove', 'to_deck', 'to_house', 'hatch')}
lock = {'lock': {'level': 255, 'key': next(k for k, r in pr.records.items() if recordio.field(r, 'EDID') == 'FOLabFreighterHoldKey'), 'leveled': False}}
pr.apply('rooms', [{'op': 'place', 'cell': house, 'key': ks['stove'], 'ref': {'base': key('CookStove', 'FURN'), 'p': [0.0, 0, 0, 0, 0, 0], 's': 1.0}},
                   {'op': 'place', 'cell': hold, 'key': ks['to_deck'], 'ref': {'base': key('UtlDoor01', 'DOOR'), 'p': [0.0, 0, 0, 0, 0, 0], 's': 1.0,
                                                                              'props': dict(lock)}},
                   {'op': 'place', 'cell': deck, 'key': ks['hatch'], 'ref': {'base': key('UtlDoor01', 'DOOR'), 'p': [-18 * 4096.0 + 100, 100, 9000, 0, 0, 0],
                                                                            's': 1.0, 'props': dict(lock)}}])
rows = [{'hold': hold, 'house': house, 'to_house': None, 'to_deck': ks['to_deck'], 'hatch': (deck, ks['hatch']), 'stove': ks['stove'],
         'spot': (100.0, 100.0, 4.0, 0.0), 'station': None, 'terminal': t_keys['FOLabRadarDomeTerminal']}]
check('the bulletin is pinyin FOLab reads', bool(g2pzh.sounds(HR.BULLETIN)))
tune = HR.signal()
check('the tune: about three seconds', 2.5 < len(tune) / 24000 < 3.6, len(tune) / 24000)
undo0 = len(pr.undo_stack)
o, rep, lines = HR.ops(G, pr, (rows, []))
pr.apply(HR.LABEL, o)
import api_quests as aq  # noqa: E402
pr.apply(HR.LABEL, [{'op': 'record_new', 'record': aq._compiled_line(G, pr, l)} for l in lines], merge=True)
check('one Undo', len(pr.undo_stack) == undo0 + 1)
check('the hatch picked at Hard, its key kept', pr.cells[deck]['refs'][ks['hatch']]['props']['lock']['level'] == HR.HATCH_LOCK
      and pr.cells[deck]['refs'][ks['hatch']]['props']['lock'].get('key'))
check('the hold\'s side opens freely', not (pr.cells[hold]['refs'][ks['to_deck']].get('props') or {}).get('lock'))
check('the stove kept loaded (his meals\' target)', pr.cells[house]['refs'][ks['stove']].get('persistent'))
os.makedirs(project.BUILD_DIR, exist_ok=True)
out = os.path.join(project.BUILD_DIR, 'Numbers Test.esp')
espwrite.write(G, pr, out)
g = gamedata.GameData(plugins=list(gamedata.OFFICIAL) + [out])
i = len(g.plugins) - 1
mine = {tes4.zstr(g.fields(f).get('EDID', b'')): f for f, (n, r) in g.forms.items() if n == i}
subs = lambda e: list(tes4.iter_subrecords(g.plugins[i].data(g.forms[mine[e]][1])))
watch = subs(HR.WATCH)
packs = [struct.unpack('<I', v)[0] & 0xFFFFFF for t, v in watch if t == 'PKID']
check('his meals first, then staying put', packs[:2] == [mine['FOLabHoldWatchMeal12'] & 0xFFFFFF, mine['FOLabHoldWatchMeal18'] & 0xFFFFFF]
      and len(packs) == 3, packs)
psdt = [dict(subs(e))['PSDT'] for e in ('FOLabHoldWatchMeal12', 'FOLabHoldWatchMeal18')]
check('meals at noon and six, an hour each', [(struct.unpack('<b', p[3:4])[0], struct.unpack('<i', p[4:8])[0]) for p in psdt] == [(12, 1), (18, 1)])
check('a face nobody else has', rep['face'] and all(r.get('copied_from') != rep['face'] for k, r in pr.records.items()
                                                    if r.get('type') == 'NPC_' and recordio.field(r, 'EDID') != HR.WATCH))
src = dict(subs(HR.SCRIPT))['SCTX']
check('caught in the hold without the key: infamy, face, his words', b'GetInCell CrimsonCaravanBarracks01' in src
      and b'GetItemCount FOLabFreighterHoldKey == 0' in src and b'AddReputation FOLabRepHuang 0 1' in src
      and b'StartConversation player FOLabHoldWatchCaught' in src and b'FOLabNameOnWater.huang' in src)
term = subs('FOLabRadarDomeTerminal')
tsrc = b''.join(v for t, v in term if t == 'SCTX')
check('the terminal decodes at Science 70, adding the note', b'Analyse the Haixin Dongtai numbers\x00' in [v for t, v in term if t == 'ITXT']
      and b'Science >= 70' in tsrc and b'AddNote FOLabHaixinNumbersNote' in tsrc)
check('the note says the hold watch\'s hours', b'noon to one and six to seven' in dict(subs('FOLabHaixinNumbersNote')).get('TNAM', b'')
      or any(b'noon to one' in v for t, v in subs('FOLabHaixinNumbersNote')))
said = [v for f, (n, r) in g.forms.items() if n == i and r.tag == 'INFO' for t, v in tes4.iter_subrecords(g.plugins[n].data(r)) if t == 'NAM1']
check('his lines in pinyin with the meaning in brackets', any(b'Zei! Chuqu! (Thief! Out of the hold!)' in v for v in said), said)
check('their Mandarin kept for the voice', HR.ZH.get(HR.shown('caught')) == HR.SAY['caught'][1])
h = health.check_file(g, out)
bad = [(x['kind'], x['count']) for x in h['groups'] if x['sev'] == 'error']
check('the plugin passes health', not bad, bad)
