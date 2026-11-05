import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
"""Painting by slope: learnt from the Mojave round Goodsprings (steep ground rockier than flat), laid on a raised
ridge: at most six layers a quarter, untouched ground showing as it did, the new steep slopes in the steep mix."""
import gamedata, land, landshape, autopaint


def check(what, ok):
    print(('PASS ' if ok else 'FAIL ') + what)


gd = gamedata.GameData()
w = next(w for w in gd.worlds() if gd.edid(w) == 'WastelandNV')
model, pics = autopaint.learn(gd, w, -15, 3)
rock = next(k for k in pics if gd.edid(gd.from_key(k)) == 'LRockCanyonRubble01')
check('steep ground is rockier than flat', model[-1].get(rock, 0) > model[0].get(rock, 0))
check('each band\'s mix adds up', all(abs(sum(b.values()) - 1) < 1e-6 for b in model))
cell = gd.grid(w)[(-14, 2)]
L = land.decode(gd, gd.land[cell], {})
old = list(L['h'])
new = [v + (2000 if 10 <= k % 33 <= 22 and 10 <= k // 33 <= 22 else 0) for k, v in enumerate(old)]   # a steep-sided block
q = autopaint.paint(gd, {'h': new, 'q': L['q']}, old, model, pics, lambda gr, gc: 1.0)
check('at most six layers a quarter, every one with a base', all(len(x['layers']) <= 6 and x['bkey'] for x in q))
same = autopaint.shows(L['q'][0], 0), autopaint.shows(q[0], 0)
check('untouched ground shows as it did', all(abs(same[0].get(t, 0) - same[1].get(t, 0)) < 0.02 for t in set(same[0]) | set(same[1])))
# the block's side (gr 10, gc 16 is quarter 0 at r 10, c 16 is quarter 1 ... use quarter 3's corner at the step)
k = (22 - 16) * 17 + (22 - 16) + 1          # quarter 3, just outside the block's corner: steep
check('the new steep side is mostly rock', autopaint.shows(q[3], k).get(rock, 0) > 0.3)
