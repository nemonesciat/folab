"""Perks of the island (perks.py) in a small mod of its own: stand-ins for a robot (robots.py's record) and the elder's
hold check (a pass and a fail line at Speech 85, with voice files on disk); one Undo makes the five perks (skill and
level asked), the robots' death script, the Reef Diver quest, and the check lines copied first for Kahuna's Ear (a prompt
saying what a pass gives) and Island Tongue (the check 15 easier), their voice files copied from the originals'.
Written and read back."""
import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import api_quests as aq  # noqa: E402
import browse  # noqa: E402
import espwrite  # noqa: E402
import factionfolk as ff  # noqa: E402
import gamedata  # noqa: E402
import health  # noqa: E402
import library  # noqa: E402
import perks as PK  # noqa: E402
import project  # noqa: E402
import questrec as qr  # noqa: E402
import robots as R  # noqa: E402
import server  # noqa: E402
import tes4  # noqa: E402
from activity import _new_key  # noqa: E402
from kuliouquest import _person  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


G = server.GD = gamedata.GameData()
server.BR = browse.Browse(G, lambda: server.PR)
pr = server.PR = project.Project.create('Perk Test')
server.edit('the court', [{'op': 'record_new', 'record': ff._faction(G, *ff.FACTIONS['court'])}])
rk, ek, qk, tk = _new_key(pr), _new_key(pr), _new_key(pr), _new_key(pr)
quest = qr.quest_record({'edid': 'FOLabHuangStanding', 'name': '', 'flags': {'start_enabled': True}, 'priority': 50, 'delay': 5.0,
                         'stages': [], 'objectives': []})
pr.apply('stand-ins', [{'op': 'record', 'key': rk, 'record': R.robot_record(G, pr, 'crazed')},
                       {'op': 'record', 'key': ek, 'record': _person(G, pr, 'FOLabHuangElder01', 'FOLabHuangElder01', 'NVProspectorMale')},
                       {'op': 'record', 'key': qk, 'record': quest},
                       {'op': 'record', 'key': tk, 'record': qr.topic_record({'edid': 'FOLabHuangStandingHold', 'name': 'Show me what the ship carries.',
                                                                              'priority': 50.0, 'kind': 0, 'flags': {'top_level': True},
                                                                              'quests': [{'quest': qk, 'links': []}]})}])
speech = G.key(next(f for f, (i, r) in G.forms.items() if r.tag == 'AVIF' and G.edid(f) == 'AVSpeech'))
lines = []
for words, op in (('[SUCCEEDED] Here is the key.', '>='), ('[FAILED] The hold stays closed.', '<')):
    l = aq.new_line_plain(G, pr, tk, qk, ek, words, conditions=[PK._cond(14, op, 85, 43, 0, 1)])
    l['skill'] = speech
    lines.append(aq._compiled_line(G, pr, l))
made = pr.apply('the hold check', [{'op': 'record_new', 'record': r} for r in lines])
infos = [k for k, r in pr.records.items() if r.get('type') == 'INFO']
folder = os.path.join(library.assets_dir(pr), 'sound', 'voice', 'perk test.esp', 'maleadult04')
os.makedirs(folder, exist_ok=True)
for k in infos:
    for ext in ('.ogg', '.lip'):
        open(os.path.join(folder, 'folabhuang_folabhuangstand_%08x_1%s' % (int(k.lstrip('+'), 16) & 0xFFFFFF, ext)), 'wb').write(b'x')
rows, skipped = PK.plan(G, pr)
R_ = {r['what']: r for r in rows}
check('the two check lines found, the robot found', R_['ear']['lines'] == 2 and R_['salvager']['robots'] == [rk], R_['ear']['lines'])
undo0 = len(pr.undo_stack)
rep = PK.apply(pr, G, (rows, skipped))
check('one Undo', len(pr.undo_stack) == undo0 + 1)
check('six copies: Kahuna\'s Ear, Island Tongue and both, for each line', rep['copies'] == 6, rep['copies'])
check('the copies\' voice files copied, none missing', rep['voice']['files'] == 12 and not rep['missing'], (rep['voice'], rep['missing']))
check('made again, it refuses', not PK.plan(G, pr)[0])
os.makedirs(project.BUILD_DIR, exist_ok=True)
out = os.path.join(project.BUILD_DIR, 'Perk Test.esp')
espwrite.write(G, pr, out)
g = gamedata.GameData(plugins=list(gamedata.OFFICIAL) + [out])
i = len(g.plugins) - 1
mine = {tes4.zstr(g.fields(f).get('EDID', b'')): f for f, (n, r) in g.forms.items() if n == i}
for k, (edid, name, skill, least, level, _icon, _words) in PK.PERKS.items():
    d = list(tes4.iter_subrecords(g.plugins[i].data(g.forms[mine[edid]][1])))
    ctda = next(v for t, v in d if t == 'CTDA')
    data = next(v for t, v in d if t == 'DATA')
    check('%s: %s %d, level %d' % (name, skill, least, level), struct.unpack('<H', ctda[8:10])[0] == 495
          and struct.unpack('<I', ctda[12:16])[0] == skill and struct.unpack('<f', ctda[4:8])[0] == least and data[1] == level)
src = lambda e: dict(tes4.iter_subrecords(g.plugins[i].data(g.forms[mine[e]][1])))['SCTX']
check('Salvager: robots leave parts with the perk', b'HasPerk FOLabPerkSalvager' in src(PK.SALVAGE_SCRIPT) and b'ScrapElectronics 2' in src(PK.SALVAGE_SCRIPT))
robot = dict(tes4.iter_subrecords(g.plugins[i].data(g.forms[mine['FOLabRobotCrazedBellhop']][1])))
check('the robot runs it', struct.unpack('<I', robot['SCRI'])[0] & 0xFFFFFF == mine[PK.SALVAGE_SCRIPT] & 0xFFFFFF)
reef = src(PK.REEF_SCRIPT)
check('Reef Diver: water breathing for a dive, never off while a rebreather is worn', b'IsSwimming' in reef
      and b'AddSpell VMS15WaterBreathingActual' in reef and b'GetEquipped VMS15Rebreather == 0' in reef)
prompts, easier = [], 0
for f, (n, r) in g.forms.items():
    if n == i and r.tag == 'INFO':
        d = list(tes4.iter_subrecords(g.plugins[n].data(r)))
        p = [v for t, v in d if t == 'RNAM']
        prompts += p
        vals = [struct.unpack('<f', v[4:8])[0] for t, v in d if t == 'CTDA' and struct.unpack('<H', v[8:10])[0] == 14]
        if 70.0 in vals:
            easier += 1
check('Kahuna\'s Ear: the prompt says what a pass gives', prompts.count(b'Show me what the ship carries. (the hold key)\x00') == 4, prompts)
check('Island Tongue: the check at 70 (both its sets, both lines)', easier == 4, easier)
h = health.check_file(g, out)
bad = [(x['kind'], x['count']) for x in h['groups'] if x['sev'] == 'error']
check('the plugin passes health', not bad, bad)
