import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
"""Give it to me in game: the test plugin's quest adds a game item and one of the mod's own, once, without moving you.
Read back as the game would load it; nothing starts the game."""
import struct
import gamedata, playtest, project, recordio, espwrite, tes4


def check(what, ok):
    print(('PASS ' if ok else 'FAIL ') + what)


gd = gamedata.GameData()
w = next(f for f, (i, r) in gd.forms.items() if r.tag == 'WEAP' and gd.edid(f) == 'WeapNV357Revolver')
# a mod with a new weapon of its own, saved, so the test plugin can name it
pr = project.Project.create('Give Test')
rec = recordio.load(gd, w)
recordio.set_field(rec, 'EDID', 'FOLabGiveGun')
made = pr.apply('new gun', [{'op': 'record_new', 'record': rec}])
mod = pr.plugin_path(); espwrite.write(gd, pr, mod)
path = os.path.join(os.environ['FOLAB_HOME'], 'FOLab Test.esp')
playtest.write_test_plugin(gd, None, None, path, give=[(gd.key(w), 1, 'WeapNV357Revolver'), (made[0], 3, 'FOLabGiveGun')],
                           mod=os.path.basename(mod))
gd2 = gamedata.GameData(plugins=list(gamedata.OFFICIAL) + [mod, path])
me, mine = len(gd2.plugins) - 1, len(gd2.plugins) - 2
check('masters: the game, then the mod', tes4.PluginFile(path).header['masters'][-1] == os.path.basename(mod))
scripts = [f for f, (i, r) in gd2.forms.items() if i == me and r.tag == 'SCPT']
check('one script, no marker', len(scripts) == 1 and not any(i == me and r.tag == 'REFR' for f, (i, r) in gd2.forms.items()))
i, srec = gd2.forms[scripts[0]]
subs = list(tes4.iter_subrecords(gd2.plugins[i].data(srec)))
s = dict(subs)
scro = [gd2.to_global(me, struct.unpack('<I', d)[0]) for t, d in subs if t == 'SCRO']
check('refs: player, the game gun, the mod gun', scro[0] == 0x14 and scro[1] == w and gd2.forms[scro[2]][0] == mine
      and gd2.edid(scro[2]) == 'FOLabGiveGun')
check('ref count in the header', struct.unpack_from('<I', s['SCHR'], 4)[0] == 3)
code = s['SCDA'].hex()
# player.AddItem <ref> <n>, as the game's own Hull20GaAddScript compiles "Player.AddItem Hull20Ga 25"
check('AddItem as the game compiles it', '1c0001000210' + '0a000200720200' + '6e01000000' in code and
      '1c0001000210' + '0a000200720300' + '6e03000000' in code)
check('no MoveTo', '9e10' not in code)
check('if skips all four statements', '16000d000400' in code)
check('the source says the same', b'player.AddItem FOLabGiveGun 3' in s['SCTX'])
for p in gd2.plugins:
    p.close()
