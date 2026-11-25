"""Waikiki's money (money.py): the three models closed; the Pip-Boy pictures drawn; Caps001 as the mod has it (Kala, the
token's model and picture), the tongbao and bango tag MISC records; the settling quest's script and a trade-in line's script
compile; a small mod with them written, read back and passing health."""
import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import api_quests as aq  # noqa: E402
import api_scripts  # noqa: E402
import browse  # noqa: E402
import espwrite  # noqa: E402
import gamedata  # noqa: E402
import health  # noqa: E402
import modelmake  # noqa: E402
import money as MO  # noqa: E402
import project  # noqa: E402
import questrec as qr  # noqa: E402
import server  # noqa: E402
import tes4  # noqa: E402
from activity import _new_key  # noqa: E402
from kuliouquest import _person  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


M = MO.models()
check('three models, every one closed', len(M) == 3 and all(not modelmake.open_edges(d) for d, _m in M.values()),
      {k: len(modelmake.open_edges(d)) for k, (d, _m) in M.items()})
check('each a mesh and its pictures', all(m['mesh'] in m['files'] and len(m['files']) >= 3 for _d, m in M.values()))
for k in ('kala', 'tongbao', 'bango'):
    px = MO.icon(k)
    shown = sum(1 for i in range(3, len(px), 4) if px[i])
    check('the %s icon: 256 square, a shape on clear' % k, len(px) == 256 * 256 * 4 and 4000 < shown < 40000, shown)
check('rates: tongbao spends better at a Huang shop than the changer pays, and costs more from him',
      MO.CHANGER_BUYS < MO.CHANGER_BETTER < MO.RATES['tongbao'] < MO.CHANGER_SELLS)

G = server.GD = gamedata.GameData()
cell_value = struct.unpack('<i', next(v for t, v in tes4.iter_subrecords(G.plugins[G.forms[MO._game(G, MO.CELL, ('AMMO',))][0]].data(
    G.forms[MO._game(G, MO.CELL, ('AMMO',))][1])) if t == 'DATA')[8:12])[0]
check('pirates take a cell for more than its worth in kala', MO.RATES['cells'] > cell_value, cell_value)
server.BR = browse.Browse(G, lambda: server.PR)
pr = server.PR = project.Project.create('Money Test')
kala = MO.kala_record(G, M['kala'][1])
import recordio  # noqa: E402
check('Caps001 is Kala, with the token and its picture', recordio.field(kala, 'FULL') == 'Kala' and 'kala_token' in recordio.field(kala, 'MODL')
      and recordio.field(kala, 'ICON').endswith('folab_kala.dds') and recordio.field(kala, 'EDID') == 'Caps001')
tong = MO.coin_record(G, 'tongbao', M['tongbao'][1])
data = next(s for s in tong['subs'] if s['tag'] == 'DATA')
vals = {f['name']: f['value'] for f in data['fields']}
check('the tongbao: its name, value and weight', recordio.field(tong, 'FULL') == 'An Tongbao' and vals.get('Value') == MO.TONGBAO[2]
      and abs(vals.get('Weight') - MO.TONGBAO[3]) < 1e-6, vals)
qk, qsk, tk, nk, bk = (_new_key(pr) for _ in range(5))
quest = qr.quest_record({'edid': MO.QUEST, 'script': qsk, 'name': '', 'flags': {'start_enabled': True}, 'priority': 40, 'delay': 0.5,
                         'stages': [], 'objectives': []})
extra = {qk: quest, tk: tong, G.key(MO.CAPS): kala, bk: MO.coin_record(G, 'bango', M['bango'][1])}
sc = api_scripts.scripts()
c = sc.compile(MO.quest_source(), qsk, 'quest', extra)
check('the settling script compiles', hasattr(c, 'subrecords'), c if not hasattr(c, 'subrecords') else '')
ops = [{'op': 'record', 'key': G.key(MO.CAPS), 'record': kala}, {'op': 'record', 'key': tk, 'record': tong}, {'op': 'record', 'key': bk, 'record': extra[bk]},
       {'op': 'record', 'key': qsk, 'record': sc._record_of(c, MO.SCRIPT)}, {'op': 'record', 'key': qk, 'record': quest},
       {'op': 'record', 'key': nk, 'record': _person(G, pr, 'FOLabMoneyMan', 'FOLabMoneyMan', 'NVProspectorMale')}]
topic = _new_key(pr)
ops.append({'op': 'record', 'key': topic, 'record': qr.topic_record({'edid': 'FOLabMoneyTest', 'name': "Let's trade in tongbao.", 'priority': 50.0,
                                                                      'kind': 0, 'flags': {'top_level': True}, 'quests': [{'quest': qk, 'links': []}]})})
pr.apply('records', ops)
lines = []
for kind in ('tongbao', 'cells', 'bango'):
    l = aq.new_line_plain(G, pr, topic, qk, nk, 'Show me.', conditions=[MO._cond(47, '>=', 1, tk, 0, 1)])
    l['end'] = {'source': MO.trade_in(kind), 'parts': None}
    lines.append(l)
try:
    pr.apply('lines', [{'op': 'record_new', 'record': aq._compiled_line(G, pr, l)} for l in lines])
    check('the trade-in scripts compile (tongbao, cells, bango)', True)
except ValueError as e:
    check('the trade-in scripts compile (tongbao, cells, bango)', False, e)
os.makedirs(project.BUILD_DIR, exist_ok=True)
out = os.path.join(project.BUILD_DIR, 'Money Test.esp')
espwrite.write(G, pr, out)
g = gamedata.GameData(plugins=list(gamedata.OFFICIAL) + [out])
i = len(g.plugins) - 1
n, r = g.forms[MO.CAPS]
full = next((v for t, v in tes4.iter_subrecords(g.plugins[n].data(r)) if t == 'FULL'), b'')
check('the built plugin overrides Caps001 as Kala', n == i and full.rstrip(b'\0') == b'Kala', (n, full))
h = health.check_file(g, out)
bad = [(x['kind'], x['count'], [r['text'] for r in x['rows']][:3]) for x in h['groups'] if x['sev'] == 'error' and x['kind'] != 'mesh']    # (the models are the mod's own files)
check('the plugin passes health', not bad, bad)
