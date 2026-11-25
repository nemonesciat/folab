"""A rebreather made at a workbench (rebreather.py) in a small mod of its own: one Undo makes the mask (the game's
Rebreather as an item of the mod's own, its script adding the game's water breathing spell while worn) and a workbench
recipe at Science 70. Written and read back."""
import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import browse  # noqa: E402
import espwrite  # noqa: E402
import gamedata  # noqa: E402
import health  # noqa: E402
import project  # noqa: E402
import rebreather as RB  # noqa: E402
import server  # noqa: E402
import tes4  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


G = server.GD = gamedata.GameData()
server.BR = browse.Browse(G, lambda: server.PR)
pr = server.PR = project.Project.create('Rebreather Test')
rows, skipped = RB.plan(G, pr)
check('the game has all it needs', rows and not skipped, skipped)
undo0 = len(pr.undo_stack)
ops, rep = RB.ops(G, pr, (rows, skipped))
pr.apply(RB.LABEL, ops)
check('one Undo, three records', len(pr.undo_stack) == undo0 + 1 and len(rep['made']) == 3, rep['made'])
check('made again, it refuses', bool(RB.plan(G, pr)[1]))
os.makedirs(project.BUILD_DIR, exist_ok=True)
out = os.path.join(project.BUILD_DIR, 'Rebreather Test.esp')
espwrite.write(G, pr, out)
g = gamedata.GameData(plugins=list(gamedata.OFFICIAL) + [out])
i = len(g.plugins) - 1
mine = {tes4.zstr(g.fields(f).get('EDID', b'')): f for f, (n, r) in g.forms.items() if n == i}
sub = lambda e: dict(tes4.iter_subrecords(g.plugins[i].data(g.forms[mine[e]][1])))
mask, script, recipe = sub(RB.MASK), sub(RB.SCRIPT), sub(RB.RECIPE)
check('the mask runs its own script, not the quest\'s', struct.unpack('<I', mask['SCRI'])[0] & 0xFFFFFF == mine[RB.SCRIPT] & 0xFFFFFF)
check('the mask keeps the Rebreather\'s look and enchantment', b'NVRebreather' in mask['MODL'] and 'EITM' in mask)
check('no quest flag on it', not g.forms[mine[RB.MASK]][1].flags & 0x400)
src = script['SCTX']
check('worn, it breathes as the game\'s', b'AddSpell VMS15WaterBreathingActual' in src and b'GetEquipped FOLabRebreather' in src
      and b'RemoveSpell' in src)
skill, level = struct.unpack('<II', recipe['DATA'][:8])
check('the recipe takes Science 70', (skill, level) == (40, 70), (skill, level))
cat = struct.unpack('<I', recipe['DATA'][8:12])[0]
check('at a workbench', g.edid(cat) == 'WorkbenchRecipes', g.edid(cat))
check('it makes the mask', struct.unpack('<I', recipe['RCOD'])[0] & 0xFFFFFF == mine[RB.MASK] & 0xFFFFFF)
h = health.check_file(g, out)
bad = [(x['kind'], x['count']) for x in h['groups'] if x['sev'] == 'error']
check('the plugin passes health', not bad, bad)
