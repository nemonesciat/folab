"""Brokering (brokering.py) in a small mod of its own: stand-in people (Linda Moreno, the two pirate traders, Zhao Lei, and
Lin Meihua as a named ref), the three reputations, Silk for Waikiki and the pirate deals' quest with its variables; one Undo
makes the quest FOLabBroker, a sealed package per route and three topics a route, the lines: given when due (a day
against the GameDaysPassed global), not yet, still carrying; taken and paid with fame both sides; the share after steady
runs. Written and read back."""
import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import api_scripts  # noqa: E402
import brokering as BK  # noqa: E402
import browse  # noqa: E402
import espwrite  # noqa: E402
import gamedata  # noqa: E402
import health  # noqa: E402
import piratedeal as PD  # noqa: E402
import project  # noqa: E402
import questrec as qr  # noqa: E402
import server  # noqa: E402
import tes4  # noqa: E402
from activity import _new_key  # noqa: E402
from kuliouquest import _person  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


G = server.GD = gamedata.GameData()
server.BR = browse.Browse(G, lambda: server.PR)
pr = server.PR = project.Project.create('Broker Test')
check('nothing without the reputations', not BK.plan(G, pr)[0])
stand = [{'op': 'record_new', 'record': PD._rep_record(G, e, e, 'RepNVBoomer')} for e in BK.REP.values()]
stand += [{'op': 'record_new', 'record': _person(G, pr, e, e, 'NVProspectorMale')}
          for e in ('FOLabWaikikiTrader', 'FOLabPirateTraderKahala', 'FOLabPirateTraderMarina', 'FOLabMakapuuGuard', 'FOLabLinMeihua')]
stand.append({'op': 'record_new', 'record': qr.quest_record({'edid': 'FOLabHuangSilk', 'name': 'Silk for Waikiki', 'flags': {},
                                                             'priority': 50, 'delay': 5.0, 'stages': [], 'objectives': []})})
server.edit('stand-ins', stand)
dq, ds = _new_key(pr), _new_key(pr)
deals = qr.quest_record({'edid': 'FOLabPirateDeals', 'script': ds, 'name': '', 'flags': {'start_enabled': True}, 'priority': 50,
                         'delay': 5.0, 'stages': [], 'objectives': []})
sc = api_scripts.scripts()
c = sc.compile('scn FOLabPirateDealsScript\nshort dealkahala\nshort dealmarina\nBegin GameMode\nset dealkahala to dealkahala\nEnd\n',
               ds, 'quest', {dq: deals})
lin = next(k for k, r in pr.records.items() if r.get('type') == 'NPC_' and 'FOLabLinMeihua' in str(r['subs'][0]))
room = G.key(next(f for f, (i, r) in G.forms.items() if r.tag == 'CELL' and G.edid(f) == 'CrimsonCaravanBarracks01'))
pr.apply('deals and Lin', [{'op': 'record', 'key': ds, 'record': sc._record_of(c, 'FOLabPirateDealsScript')},
                           {'op': 'record', 'key': dq, 'record': deals},
                           {'op': 'place', 'cell': room, 'key': _new_key(pr),
                            'ref': {'base': lin, 'p': [0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 's': 1.0, 'edid': 'FOLabHuangSilkGiverREF',
                                    'persistent': True}}])
rows, skipped = BK.plan(G, pr)
check('three routes', [r['route'] for r in rows] == ['silk', 'reef', 'gate'] and not skipped, skipped)
check('Lin Meihua found by her ref', rows[0]['from'] == lin)
undo0 = len(pr.undo_stack)
rep = BK.apply(pr, G, (rows, skipped))
check('one Undo, five lines a route', len(pr.undo_stack) == undo0 + 1 and rep['lines'] == 15, rep['lines'])
check('made again, it refuses', bool(BK.plan(G, pr)[1]) and not BK.plan(G, pr)[0])
os.makedirs(project.BUILD_DIR, exist_ok=True)
out = os.path.join(project.BUILD_DIR, 'Broker Test.esp')
espwrite.write(G, pr, out)
g = gamedata.GameData(plugins=list(gamedata.OFFICIAL) + [out])
i = len(g.plugins) - 1
mine = {tes4.zstr(g.fields(f).get('EDID', b'')): f for f, (n, r) in g.forms.items() if n == i}
check('a sealed package a route', all(e in mine for e in ('FOLabBrokerSilk', 'FOLabBrokerReef', 'FOLabBrokerGate')))
check('three topics a route', sum(1 for e in mine if e.startswith('FOLabBroker') and e.endswith(('Ask', 'Deliver', 'Cut'))) == 9)
infos = [(f, r) for f, (n, r) in g.forms.items() if n == i and r.tag == 'INFO']
texts = []
glob_days = G.key(next(f for f, (_i, r) in G.forms.items() if r.tag == 'GLOB' and G.edid(f) == 'GameDaysPassed'))
by_global = 0
for f, r in infos:
    subs = list(tes4.iter_subrecords(g.plugins[i].data(r)))
    sctx = b''.join(v for t, v in subs if t == 'SCTX')
    texts.append(sctx)
    for t, v in subs:
        if t == 'CTDA' and v[0] & 4:            # (compared with a global: the day a load is due)
            by_global += 1
check('fifteen lines', len(infos) == 15, len(infos))
check('due days compared with GameDaysPassed (given, not yet, the share: 3 a route)', by_global == 9, by_global)
paid = [t for t in texts if b'RemoveItem FOLabBrokerSilk' in t]
check('silk taken and paid, fame with the Huang and the court', len(paid) == 1 and b'AddItem Stimpak 2' in paid[0]
      and b'AddReputation FOLabRepHuang 1 1' in paid[0] and b'AddReputation FOLabRepCourt 1 1' in paid[0]
      and b'nextsilk to GameDaysPassed + 3' in paid[0])
check('the pirates pay in cells at the reef', any(b'RemoveItem FOLabBrokerReef' in t and b'AmmoMicroFusionCell 8' in t for t in texts))
check('the share after steady runs', sum(1 for t in texts if b'cut' in t and b'RemoveItem' not in t and b'AddItem' in t) == 3)
h = health.check_file(g, out)
bad = [(x['kind'], x['count']) for x in h['groups'] if x['sev'] == 'error']
check('the plugin passes health', not bad, bad)
