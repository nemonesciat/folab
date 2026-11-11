"""The mod's own new game (newgame.py): switched on, the plugin has a persistent named marker where you wake, a start game
enabled quest whose script the compiler made (moving you there, the screens chosen, in order), and the Mojave's opening and
the chosen start quests switched off by overrides that change nothing else. Changing it makes it again in place; switching
it off takes it all out; one Undo each."""
import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import api_scripts  # noqa: E402
import espwrite  # noqa: E402
import gamedata  # noqa: E402
import newgame  # noqa: E402
import project  # noqa: E402
import recordio  # noqa: E402
import tes4  # noqa: E402


def check(what, ok):
    print(('PASS ' if ok else 'FAIL ') + what)


gd = gamedata.GameData()
pr = project.Project.create('New Game Test')
sc = api_scripts.Scripts(gd, lambda: pr)


def comp(text, key, extra):
    c = sc.compile(text, key, 'quest', extra)
    return sc._record_of(c, c.name)


def run(body):
    label, ops, _s = newgame.plan(gd, pr, comp, body)
    pr.apply(label, ops)
    return label


writes = 0


def written():
    global writes
    writes += 1
    out = os.path.join(project.BUILD_DIR, 'New Game Test %d.esp' % writes)
    os.makedirs(project.BUILD_DIR, exist_ok=True)
    espwrite.write(gd, pr, out)
    g = gamedata.GameData(plugins=list(gamedata.OFFICIAL) + [out])
    return g, len(g.plugins) - 1


def mine(g, i, tag):
    return {f: r for f, (k, r) in g.forms.items() if k == i and r.tag == tag}


cell = next(f for f, (i, r) in gd.forms.items() if r.tag == 'CELL' and gd.edid(f) == 'GSProspectorSaloonInterior')
ckey = gd.key(cell)
check('names come from the plugin', newgame.names(pr) == {'marker': 'NewGameTestNewGameStart', 'quest': 'NewGameTestNewGame', 'script': 'NewGameTestNewGameScript', 'message': 'NewGameTestNewGameMessage'})

try:
    newgame.plan(gd, pr, comp, {'on': True})
    check('no start spot: says to pick one', False)
except newgame.Problem as e:
    check('no start spot: says to pick one', 'Start a new game here' in str(e))

run({'on': True, 'cell': ckey, 'p': [100.0, 200.0, 30.0, 1.5], 'steps': ['name', 'face', 'special', 'tags', 'traits'], 'hour': 10, 'quiet': ['dlc', 'stash']})
check('one Undo for it all', len(pr.undo_stack) == 1 and pr.undo_stack[0][0] == 'Your own new game')
s = pr.newgame
check('the settings are kept', s['on'] and s['hour'] == 10 and s['cell'] == ckey)
text = api_scripts.source_of(pr.records[s['made']['script']])
order = [text.find(c) for c in ('player.MoveTo NewGameTestNewGameStart', 'GetPlayerName', 'ShowRaceMenu', 'SetSPECIALPoints 40', 'SetTagSkills 3', 'ShowTraitMenu')]
check('the script moves you, then opens the screens in order', all(o > 0 for o in order) and order == sorted(order))
check('it sets the hour', 'set GameHour to 10' in text)
flat = text.replace('\r', '')
check('it leaves a save that has met Doc Mitchell alone (in his house or past it)', 0 < flat.find('if GetQuestRunning VCG01 == 1') < flat.find('if GetStageDone VCG01 200 == 1') < flat.find('set step to 1'))
check("once it is a new game, Doc Mitchell's scene is stopped whenever it starts", flat.find('set step to 1') < flat.find('if GetQuestRunning VCG01 == 1\n\t\tStopQuest VCG01\n\t\tplayer.RemoveScriptPackage'))
check('the white a new game begins in is cleared on arriving', text.count('RemoveImageSpaceModifier WhiteISFX') == 1)
check('a fresh Pip-Boy is handed over only while a screen is open, in the game\'s order; in play only its reset, once worn',
      0 < flat.find('begin MenuMode') < flat.find('player.RemoveItem PipBoy 1 1') < flat.find('player.AddItem PipBoy 1 1')
      < flat.find('player.EquipItem PipBoy\n\t\tplayer.EquipItem PipBoyGlove\n\t\tResetPipboyManager')
      and min(flat.find('EquipItem'), flat.find('AddItem'), flat.find('RemoveItem')) > flat.find('begin MenuMode')
      and 0 < flat.find('if player.GetEquipped PipBoy == 1') < flat.find('ResetPipboyManager') < flat.find('begin MenuMode'))
check('it moves you only once the new game has settled', 'set pause to %s' % newgame.SETTLE in text and text.count('IsPlayerMovingIntoNewSpace == 1') == 2)

g, i = written()
refs = [(cf, rf) for cf, rs in g.cell_refs.items() for rf in rs if rf >> 24 == i]
check('one thing placed: the marker, in the place', len(refs) == 1 and refs[0][0] == cell)
rf = refs[0][1]
rrec = g.cell_refs[cell][rf]
fl = g.ref_fields(rrec)[1]
check('the marker has its editor ID and is persistent', tes4.zstr(fl.get('EDID', b'')) == 'NewGameTestNewGameStart' and rrec[1].flags & tes4.PERSISTENT)
check('it stands where asked, facing the way asked', [round(v, 2) for v in struct.unpack('<6f', fl['DATA'])] == [100.0, 200.0, 30.0, 0.0, 0.0, 1.5])
qs = [f for f in mine(g, i, 'QUST') if f >> 24 == i]
check('one quest of the mod\'s own', len(qs) == 1)
qf = g.fields(qs[0])
check('it starts with the game', qf['DATA'][0] & 1 == 1)
script = g.to_global(i, struct.unpack('<I', qf['SCRI'])[0])
sf = g.fields(script)
scro = [g.to_global(i, struct.unpack('<I', d)[0]) for t, d in tes4.iter_subrecords(g.plugins[i].data(g.forms[script][1])) if t == 'SCRO']
check('its script names the marker', rf in scro)
check('the script is a quest script', struct.unpack_from('<H', sf['SCHR'], 16)[0] == 1)
vcg = next(f for f, (k, r) in g.forms.items() if r.tag == 'QUST' and g.edid(f) == 'VCG01')
check('the Mojave\'s opening is switched off in the plugin', g.forms[vcg][0] == i and g.fields(vcg)['DATA'][0] & 1 == 0)
game_q = gd.fields(gd.from_key(gd.key(vcg)))
def stages(gg, fid):
    out, cur = {}, None
    for t, d in tes4.iter_subrecords(gg.plugins[gg.forms[fid][0]].data(gg.forms[fid][1])):
        if t == 'INDX':
            cur = out.setdefault(struct.unpack('<h', d[:2])[0], [])
        elif t == 'QOBJ':
            cur = None
        elif cur is not None:
            cur.append((t, d))
    return out


mine_st, game_st = stages(g, vcg), stages(gd, gd.from_key(gd.key(vcg)))
early = [n for n in mine_st if n < newgame.HUSH_BELOW]
check('its stages while the player is in bed do nothing (no code, as the game stores a comment-only stage)',
      0 in early and all(t not in ('SCDA', 'SCRO') and (t != 'SCHR' or struct.unpack_from('<III', d, 4) == (0, 0, 0)) for n in early for t, d in mine_st[n]))
check("the later stages are the game's own, byte for byte", all(mine_st[n] == game_st[n] for n in mine_st if n >= newgame.HUSH_BELOW) and sorted(mine_st) == sorted(game_st))
quiet = [e for k in ('dlc', 'stash') for e in newgame.QUIET[k][2]]
found = [f for f, (k, r) in g.forms.items() if r.tag == 'QUST' and g.edid(f) in quiet]
check('the DLCs\' invitations and pre-order packs are switched off too', found and all(g.forms[f][0] == i and g.fields(f)['DATA'][0] & 1 == 0 for f in found))
masters = [m.lower() for m in g.plugins[i].header['masters']]
check('the packs and DLCs whose quests are off are masters (their quests are theirs)', all(m in masters for m in ('classicpack.esm', 'deadmoney.esm', 'lonesomeroad.esm')))
pack = next(f for f in found if g.edid(f) == 'VPreorderClassic')
check("a pack's quest keeps its script (the pack's other scripts read its variables)", 'SCRI' in g.fields(pack))
check("by default the packs and the DLCs' invitations are left on", newgame.DEFAULT['quiet'] == [])

# ---- changed: made again in place ----
script_key, quest_key = s['made']['script'], s['made']['quest']
run({'steps': ['name', 'traits'], 'quiet': ['dlc'], 'p': [50.0, 60.0, 30.0, 0.0]})
s = pr.newgame
check('the same script and quest, made again', s['made']['script'] == script_key and s['made']['quest'] == quest_key)
text = api_scripts.source_of(pr.records[script_key])
check('only the screens asked for', 'GetPlayerName' in text and 'ShowTraitMenu' in text and 'ShowRaceMenu' not in text and 'SetTagSkills' not in text)
markers = [k for c in pr.cells.values() for k, r in c['refs'].items() if r.get('edid')]
check('still one marker', len(markers) == 1 and markers[0] == s['made']['marker'][1])
stash = newgame.quest_keys(gd, newgame.QUIET['stash'][2])
check('the pre-order packs start again (taken out of the mod)', stash and not any(k in pr.records for k in stash))
check('the DLC invitations stay off', all(k in pr.records for k in newgame.quest_keys(gd, newgame.QUIET['dlc'][2])))
g, i = written()
script = next(f for f in mine(g, i, 'SCPT'))
scro = [g.to_global(i, struct.unpack('<I', d)[0]) for t, d in tes4.iter_subrecords(g.plugins[i].data(g.forms[script][1])) if t == 'SCRO']
mref = [rf for cf, rs in g.cell_refs.items() for rf in rs if rf >> 24 == i]
check('the script names the new marker', len(mref) == 1 and mref[0] in scro)

# ---- the Pip-Boy ----
run({'pipboy': False})
text = api_scripts.source_of(pr.records[script_key])
check('without the Pip-Boy, it is taken off in the first moment', 0 < text.find('player.RemoveItem PipBoy 1 1') < text.find('player.MoveTo') and 'AddItem PipBoy' not in text)

# ---- off: all of it gone ----
run({'on': False})
check('off: nothing of it left', not pr.cells and not pr.records)
check('the settings stay, to switch it on again', pr.newgame['on'] is False and pr.newgame['steps'] == ['name', 'traits'])
pr.undo()
check('Undo brings it back', script_key in pr.records and any(r.get('edid') for c in pr.cells.values() for r in c['refs'].values()))
pr.undo(); pr.undo(); pr.undo()
check('Undo all the way: no new game', not pr.records and not pr.cells and not pr.newgame)

# ---- what the page shows ----
v = newgame.view(gd, pr)
check('the page lists the screens and what can be switched off', [x['id'] for x in v['steps']] == ['name', 'face', 'special', 'tags', 'traits']
      and all(q['found'] > 0 for q in v['quiet']))
check('and where the player\'s record is', v['player'] == gd.key(7))
