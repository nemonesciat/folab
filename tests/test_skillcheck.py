"""Skill checks for any skill (skillcheck.py): every New Vegas skill's AVIF found in the game; a Repair check and a Medicine
check made in a small mod (pass and fail lines with KNAM the skill, GetActorValue >= / < N on the player, the result script
on the pass), written and read back."""
import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import api_quests as aq  # noqa: E402
import browse  # noqa: E402
import espwrite  # noqa: E402
import gamedata  # noqa: E402
import health  # noqa: E402
import project  # noqa: E402
import questrec as qr  # noqa: E402
import server  # noqa: E402
import skillcheck as SK  # noqa: E402
import tes4  # noqa: E402
from activity import _new_key  # noqa: E402
from kuliouquest import _person  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


G = server.GD = gamedata.GameData()
avif = {G.edid(f): f for f, (_i, r) in G.forms.items() if r.tag == 'AVIF'}
check('every skill\'s AVIF is the game\'s', all(e in avif for _av, e, _n in SK.SKILLS.values()),
      [e for _av, e, _n in SK.SKILLS.values() if e not in avif])
check('the tag as the game shows it', SK.tag('MeleeWeapons', 50) == '[Melee Weapons 50]')
server.BR = browse.Browse(G, lambda: server.PR)
pr = server.PR = project.Project.create('Check Test')
qk, tk, nk = _new_key(pr), _new_key(pr), _new_key(pr)
quest = qr.quest_record({'edid': 'FOLabCheckTest', 'name': '', 'flags': {'start_enabled': True}, 'priority': 50, 'delay': 5.0,
                         'stages': [], 'objectives': []})
pr.apply('stand-ins', [{'op': 'record', 'key': qk, 'record': quest},
                       {'op': 'record', 'key': nk, 'record': _person(G, pr, 'FOLabCheckMan', 'FOLabCheckMan', 'NVProspectorMale')},
                       {'op': 'record', 'key': tk, 'record': qr.topic_record({'edid': 'FOLabCheckTopic', 'name': 'Let me fix that.',
                                                                              'priority': 50.0, 'kind': 0, 'flags': {'top_level': True},
                                                                              'quests': [{'quest': qk, 'links': []}]})}])
lines = SK.check_lines(G, pr, tk, qk, nk, 'Repair', 50, "Good as new.", "You made it worse.", on_pass='player.AddItem Stimpak 1')
lines += SK.check_lines(G, pr, tk, qk, nk, 'Medicine', 35, "That's set right.", "Ow. No.")
check('a pass and a fail each', len(lines) == 4 and lines[0]['responses'][0]['text'].startswith('[SUCCEEDED] ')
      and lines[1]['responses'][0]['text'].startswith('[FAILED] '))
pr.apply('checks', [{'op': 'record_new', 'record': aq._compiled_line(G, pr, l)} for l in lines])
os.makedirs(project.BUILD_DIR, exist_ok=True)
out = os.path.join(project.BUILD_DIR, 'Check Test.esp')
espwrite.write(G, pr, out)
g = gamedata.GameData(plugins=list(gamedata.OFFICIAL) + [out])
i = len(g.plugins) - 1
got = []
for f, (n, r) in g.forms.items():
    if n == i and r.tag == 'INFO':
        d = list(tes4.iter_subrecords(g.plugins[n].data(r)))
        knam = next((struct.unpack('<I', v)[0] for t, v in d if t == 'KNAM'), None)
        av = [(struct.unpack('<I', v[12:16])[0], struct.unpack('<f', v[4:8])[0], struct.unpack('<I', v[20:24])[0])
              for t, v in d if t == 'CTDA' and struct.unpack('<H', v[8:10])[0] == 14]
        got.append((g.edid(knam) if knam else None, av, b'AddItem' in b''.join(v for t, v in d if t == 'SCTX')))
check('Repair: KNAM AVRepair, Repair >= / < 50 on the player, the pass\'s script', sorted(x for x in got if x[0] == 'AVRepair') ==
      sorted([('AVRepair', [(39, 50.0, 1)], True), ('AVRepair', [(39, 50.0, 1)], False)]), got)
check('Medicine too', sum(1 for x in got if x[0] == 'AVMedicine' and x[1] == [(37, 35.0, 1)]) == 2)
h = health.check_file(g, out)
bad = [(x['kind'], x['count']) for x in h['groups'] if x['sev'] == 'error']
check('the plugin passes health', not bad, bad)
