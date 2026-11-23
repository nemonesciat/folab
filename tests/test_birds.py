"""birds: Waikiki's birds are the game's Raven with FOLab's own pictures: each body is the Raven's mesh with only its
picture path changed, each record the Raven's with its body, name, scale and script; the bird script and the roosts'
quest script compile; every part of the Raven's picture is named; flocks keep apart and sit in their own places."""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import birds  # noqa: E402

OK = []


def check(name, cond, info=''):
    OK.append(bool(cond))
    print(('ok  ' if cond else 'FAIL') + ' ' + name + (' (%s)' % (info,) if info and not cond else ''))


check('part_of: wings, bill, tail, legs where the Raven has them',
      birds.part_of(0, 20, 10) == 'wing' and birds.part_of(10, 0, 9) == 'bill' and birds.part_of(-12, 0, 8) == 'tail'
      and birds.part_of(0, 1, 2) == 'leg' and birds.part_of(0, 0, 11) == 'body')
for k, (_n, scale, cols) in birds.KINDS.items():
    check(k + ': a colour for every part (or one it falls back to)',
          all(p in cols or birds.FALLBACK.get(p) in cols or birds.FALLBACK.get(birds.FALLBACK.get(p, '')) in cols
              for p in ('wing', 'bill', 'head', 'ring', 'tail', 'leg', 'vent', 'belly', 'body')))
    check(k + ': smaller than the Raven', 0 < scale < 2.5)
qs = birds.quest_script(3)
check('the roosts script names each roost once in its test', all(qs.count('%s.GetDisabled' % (birds.ROOST % n)) == 1 for n in (1, 2, 3)))
check('the bird script flies off before the flight ends (6.4 s)', 0 < birds.FLIGHT < 6.4)

if '--no-game' not in sys.argv:
    import gamedata
    import nif
    import nifwrite
    import scriptc
    gd = gamedata.GameData()
    try:
        import numpy  # noqa: F401
        have_numpy = True
    except ImportError:
        have_numpy = False
    raven = gd.read_file(birds.RAVEN_BODY)
    if have_numpy:
        labs = birds.labels(gd)
        check('the picture: every part named', {'wing', 'bill', 'head', 'tail', 'leg', 'body'} <= set(labs), sorted(labs))
        made = birds.files(gd, 'test')
        for k in birds.KINDS:
            body = made[birds.BODY % ('test', k)]
            s = nif.mesh_from_nif(body, placed=False)
            check(k + ': one shape, the Raven\'s 345 vertices, its own picture',
                  len(s) == 1 and len(s[0]['p']) == 345 * 3 and s[0]['tex'] == birds.TEX % ('test', k), (len(s), s[0]['tex']))
            old = birds.raven_picture_path(raven)
            check(k + ': nothing but the path changed', body == nifwrite.retexture(raven, {old: birds.TEX % ('test', k)})
                  and len(body) - len(raven) == len(birds.TEX % ('test', k)) - len(old))
            tex = made[birds.TEX % ('test', k)]
            check(k + ': picture DXT5, 512 square', tex[84:88] == b'DXT5' and tex[12:20] == b'\0\2\0\0\0\2\0\0', tex[84:88])
    rec = birds.creature(gd, 'iiwi', '+000001', 'test')
    f = {s['tag']: s for s in rec['subs']}
    check('the record: the Raven\'s skeleton, our body, script and scale',
          f['MODL']['value'].lower() == 'creatures\\nvraven\\skeleton.nif' and f['NIFZ']['value'] == 'folabtest_iiwi.nif\0'
          and f['SCRI']['value'] == '+000001' and f['BNAM']['fields'][0]['value'] == birds.KINDS['iiwi'][1], f['NIFZ']['value'])
    check('the record: no fight in it (the Raven\'s aggression 0)', f['AIDT']['fields'][0]['value'] == 0)
    forms = scriptc.GameForms(gd)
    c = scriptc.compile_script(birds.bird_script(), forms, scriptc.SCRIPT_OBJECT)
    check('the bird script compiles', len(c.data) > 100 and c.name == birds.SCRIPT)
    print('done' if all(OK) else 'FAILED')
sys.exit(0 if all(OK) else 1)
