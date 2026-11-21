import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
"""What says Mojave at a glance, out of the places a city borrows from the game (townbuild.MOJAVE_SHOWN, mojave_free,
mojave_out; the user, 20 Nov 2026: "Mojave things out"), and the Strip's far walls that the room-varying swaps took for
posters put back (roomvary.mend). A copy made now leaves them out; a place made before has them taken out, one Undo.
Never starts the game."""
import gamedata, project, roomvary, townbuild


def check(what, ok):
    print(('PASS ' if ok else 'FAIL ') + what)


gd = gamedata.GameData()
by_edid = {}
for f, (i, r) in gd.forms.items():
    by_edid.setdefault(gd.edid(f), f)

# ---------- the pure parts ----------
check('an NCR poster, a Legion flag, a Caesar bedroll and a Strip wall are Mojave at a glance',
      all(townbuild.mojave_free(gd, by_edid[e]) is None for e in ('NCRPoster07', 'NVLegionFlagSTATICNoSound', 'NVBedrollCaesarRol', 'NVStripWallImposter01')))
check('a desk and a shelf are not',
      all(townbuild.mojave_free(gd, by_edid[e]) == by_edid[e] for e in ('DeskOfficeMetalEMPTY', 'MetalShelf02') if e in by_edid))
box = townbuild.mojave_free(gd, by_edid['NovacMetalBox01DinoSouvenir'])
check("Novac's dinosaur souvenir box becomes the same box for a household",
      box is not None and gd.edid(box) == 'MetalBox01Household' and gd.describe(box)[3] == gd.describe(by_edid['NovacMetalBox01DinoSouvenir'])[3])
check('the swaps never bring a far wall in for a poster', by_edid['NVStripWallImposter01'] not in roomvary.Swaps(gd).info)

# ---------- a copy of an NCR camp's building ----------
place = townbuild.grand_inside(gd, 'CampForlornHope01')
check('a game place with NCR posters', bool(place))
pr = project.Project.create('Mojave Out')
ops, kept, _ = townbuild.inside_ops(gd, place, 'ma', 'FOLabMojaveA', 'Camp')
pr.apply('A camp', ops)
key = next(k for k, r in pr.records.items() if k.startswith('+') and r.get('type') == 'CELL')
shown = [ch['base'] for ch in pr.cells[key]['refs'].values() if 'base' in ch and townbuild.mojave_free(gd, gd.from_key(ch['base'])) != gd.from_key(ch['base'])]
check('a copy made now leaves them out: %s' % shown, not shown and kept > 20)
# (a place made before: the posters were copied)
cell = gd.from_key(place['cell'])
posters = [r for r in gd.refs(cell) if r['base'] in gd.forms and 'NCRPoster' in gd.edid(r['base'])]
pr.apply('As made before', [{'op': 'add', 'cell': key, 'base': gd.key(r['base']), 'p': [round(v, 4) for v in list(r['pos']) + list(r['rot'])], 's': 1.0}
                            for r in posters])
out, count = townbuild.mojave_out(gd, pr)
check('mojave_out finds the posters: %s' % count, sum(count.values()) == len(posters) == len(out) and all(o['op'] == 'remove' for o in out))
pr.apply('Mojave out', out)
check('and a second look finds none', townbuild.mojave_out(gd, pr)[0] == [])
pr.undo()
check('one Undo puts them back', len(townbuild.mojave_out(gd, pr)[0]) == len(posters))
