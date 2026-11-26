"""The An palace's pieces (palaceset.py): each builds, every part closed (the user: never an incomplete model), the hipped
roofs' sheets mitred at the hips, few enough triangles a shape for the game's strips, walked parts solid. Nothing near the
game."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import modelmake  # noqa: E402
import palaceset as PS  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


for key, (title, fn) in PS.PIECES.items():
    d = fn()
    check('%s: every part closed' % key, not modelmake.open_edges(d), modelmake.open_edges(d)[:3])
    m = modelmake.make(d)
    check('%s: builds, under 32,000 triangles a shape' % key, max(len(s['i']) // 3 for s in m['shapes']) < 32000,
          max(len(s['i']) // 3 for s in m['shapes']))
    check('%s: something to walk on' % key, any(p.get('solid') for p in d['parts']))
t = modelmake.make(PS.tower())
check('the tower is five storeys and its finial over 3,000 up', len(PS.TOWER) == 5 and t['box'][5] > 3000, t['box'])
pts = []
PS.hip(pts, 800, 800, 1000, out=300, rise=400, horn=120)
sheets = [p for p in pts if p['shape'] == 'sheet' and p['look'] == 'tiles']
c0 = sheets[0]['rows'][-1][-1]
near = min(max(abs(a - b) for a, b in zip(c0, q)) for q in (sheets[1]['rows'][-1][0], sheets[1]['rows'][-1][-1]))
check('an eave skirt\'s sides meet at the hips', len(sheets) == 4 and near < 1.0, near)
