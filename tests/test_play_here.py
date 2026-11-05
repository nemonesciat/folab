import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
"""Play here's test plugin: the marker, the quest and the hand-compiled script, read back as the game would load it."""
import struct
import gamedata, playtest, tes4


def check(what, ok):
    print(('PASS ' if ok else 'FAIL ') + what)


gd = gamedata.GameData()
cell = next(c for c in gd.interiors if gd.edid(c) == '2EOVault21')
path = os.path.join(os.environ['FOLAB_HOME'], 'FOLab Test.esp')
playtest.write_test_plugin(gd, cell, [1416, 1032, 7972, 1.57], path, 'Vault 21')
gd2 = gamedata.GameData(plugins=list(gamedata.OFFICIAL) + [path])
me = len(gd2.plugins) - 1
quests = [f for f, (i, r) in gd2.forms.items() if i == me and r.tag == 'QUST']
scripts = [f for f, (i, r) in gd2.forms.items() if i == me and r.tag == 'SCPT']
check('one quest and one script', len(quests) == 1 and len(scripts) == 1)
q, s = gd2.fields(quests[0]), gd2.fields(scripts[0])
check('quest starts with the game and runs the script', q['DATA'][0] & 1 and gd2.to_global(me, struct.unpack('<I', q['SCRI'])[0]) == scripts[0])
check('quest script, compiled size as its header says', struct.unpack_from('<H', s['SCHR'], 16)[0] == 1 and struct.unpack_from('<I', s['SCHR'], 8)[0] == len(s['SCDA']))
i, rec = gd2.forms[scripts[0]]
scro = [struct.unpack('<I', d)[0] for t, d in tes4.iter_subrecords(gd2.plugins[i].data(rec)) if t == 'SCRO']
marker = gd2.to_global(me, scro[1])
check('ref 1 is the player, ref 2 the marker', scro[0] == 0x14 and marker in gd2.ref_cell)
r = next(r for r in gd2.refs(cell) if r['ref'] == marker)
check('marker in Vault 21, persistent, where asked', gd2.cell_refs[cell][marker][1].flags & tes4.PERSISTENT and [round(v) for v in r['pos']] == [1416, 1032, 7972])
check('marker is an XMarkerHeading', gd2.describe(r['base'])[1] == 'XMarkerHeading')
check('message compiled in', b'FOLab: Play here (Vault 21)' in s['SCDA'])
# the statements are the bytes the game's own compiler gives (from the game's VMS30LegionRaiderAmbushScript and
# TheTopsSmallScript: GameMode block, if/set on a local, ShowWarning)
code = playtest.compiled_script(b'Small Fry at The Tops!').hex()
check('if done == 0 / set done to 1 as the game compiles them', '16000d0003000900207301002030203d3d1500070073010002002031' in code)
check('ShowWarning as the game compiles it', 'b9111c0001001600536d616c6c204672792061742054686520546f7073210000' in code)
check('player.MoveTo marker', '1c0001009e10050001007202' in code)
for p in gd2.plugins:
    p.close()
