"""Hints for the collectibles (hints.py) in a small mod of its own: a stand-in for the collectibles' quest (its found flags
and counts), the Radar Dome's terminal, Zhao Lei and Linda Moreno; one Undo adds the terminal's entry (shown while the Pali
doll isn't found) and their Speech checks (each hint while its item isn't found, the Huang's only once a charm is), with a
fail and a last "nothing new" line each. Every item of the two sets is hinted somewhere. Written and read back."""
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
import hints as H  # noqa: E402
import project  # noqa: E402
import questrec as qr  # noqa: E402
import server  # noqa: E402
import terminals  # noqa: E402
import tes4  # noqa: E402
from activity import _new_key  # noqa: E402
from kuliouquest import _person  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


check('every doll and charm hinted somewhere', not H.covered(), H.covered())
G = server.GD = gamedata.GameData()
server.BR = browse.Browse(G, lambda: server.PR)
pr = server.PR = project.Project.create('Hint Test')
check('nothing without the collectibles', not H.plan(G, pr)[0])
qk, qs = _new_key(pr), _new_key(pr)
quest = qr.quest_record({'edid': 'FOLabCollectibles', 'script': qs, 'name': '', 'flags': {'start_enabled': True}, 'priority': 10,
                         'delay': 60.0, 'stages': [], 'objectives': []})
src = ['scn FOLabCollectiblesScript'] + ['short hula%d' % (i + 1) for i in range(7)] + ['short jade%d' % (i + 1) for i in range(13)] + \
      ['short hulacount', 'short jadecount', 'Begin GameMode', 'set hulacount to hulacount', 'End']
c = api_scripts.scripts().compile('\n'.join(src), qs, 'quest', {qk: quest})
pr.apply('collectibles stand-in', [{'op': 'record', 'key': qs, 'record': api_scripts.scripts()._record_of(c, 'FOLabCollectiblesScript')},
                                   {'op': 'record', 'key': qk, 'record': quest}])
t_ops, t_keys = terminals.ops(G, pr, terminals.plan('Terminal: FOLabRadarDomeTerminal\nName: Radar\nModel: desk\nLock: average\n'
                                                    'Welcome:\n  RADAR\n== Read the log\nSays: Nothing.\n'))
pr.apply('terminal', t_ops)
server.edit('people', [{'op': 'record_new', 'record': _person(G, pr, e, e, 'NVProspectorMale')} for e in ('FOLabMakapuuGuard', 'FOLabWaikikiTrader')])
rows, skipped = H.plan(G, pr)
check('the terminal and the two people found, the rest skipped', sum(1 for r in rows if r['what'] == 'term') == 1
      and sum(1 for r in rows if r['what'] == 'person') == 2 and skipped, len(rows))
undo0 = len(pr.undo_stack)
rep = H.apply(pr, G, (rows, skipped))
check('one Undo', len(pr.undo_stack) == undo0 + 1)
check('one entry, three checks (Zhao Lei two, Linda one), eight lines', rep['entries'] == 1 and rep['checks'] == 3 and rep['lines'] == 8,
      (rep['entries'], rep['checks'], rep['lines']))
check('items without a hint in this small mod are named', rep['uncovered'] and ('hula', 'Endurance') in rep['uncovered'])
os.makedirs(project.BUILD_DIR, exist_ok=True)
out = os.path.join(project.BUILD_DIR, 'Hint Test.esp')
espwrite.write(G, pr, out)
g = gamedata.GameData(plugins=list(gamedata.OFFICIAL) + [out])
i = len(g.plugins) - 1
mine = {tes4.zstr(g.fields(f).get('EDID', b'')): f for f, (n, r) in g.forms.items() if n == i}
term = list(tes4.iter_subrecords(g.plugins[i].data(g.forms[mine['FOLabRadarDomeTerminal']][1])))
check('the entry on the terminal', b'Traffic note, 10-21-2077\x00' in [v for t, v in term if t == 'ITXT'])
cq = mine['FOLabCollectibles'] & 0xFFFFFF
conds = [v for t, v in term if t == 'CTDA']
check('shown while the Pali doll is not found', any(struct.unpack('<H', v[8:10])[0] == 79 and struct.unpack('<I', v[12:16])[0] & 0xFFFFFF == cq
                                                    and struct.unpack('<I', v[16:20])[0] == 6 and struct.unpack('<f', v[4:8])[0] == 0.0 for v in conds))
infos = []
for f, (n, r) in g.forms.items():
    if n == i and r.tag == 'INFO':
        d = list(tes4.iter_subrecords(g.plugins[n].data(r)))
        infos.append((b''.join(v for t, v in d if t == 'NAM1'), [v for t, v in d if t == 'CTDA']))
zhao = [x for x in infos if b'Green charm in hold' in x[0]]
check('Zhao Lei\'s hold hint: Speech 55, only once a charm is found, only while that charm isn\'t',
      len(zhao) == 1 and any(struct.unpack('<H', v[8:10])[0] == 14 and struct.unpack('<f', v[4:8])[0] == 55.0 for v in zhao[0][1])
      and any(struct.unpack('<H', v[8:10])[0] == 79 and struct.unpack('<I', v[16:20])[0] == 22 and v[0] >> 5 == 3 for v in zhao[0][1]))
check('a fail and a "nothing new" each', sum(1 for x in infos if b'[FAILED]' in x[0]) == 3
      and sum(1 for x in infos if x[0].startswith(b'Nothing')) == 2)
h = health.check_file(g, out)
bad = [(x['kind'], x['count']) for x in h['groups'] if x['sev'] == 'error']
check('the plugin passes health', not bad, bad)
