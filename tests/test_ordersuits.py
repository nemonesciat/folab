"""The Order's suits in the Missouri's colours (ordersuits.py): the pictures painted (haze grey with the picture's own light,
the hull number on the breastplate, the anchor), the models retextured only in their texture paths, the Order's records
pointed at them. Nothing near the game."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import numpy as np  # noqa: E402
import gamedata  # noqa: E402
import ordersuits as O  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


G = gamedata.GameData()
before, after, helm = O.pictures(G)
a, b = np.asarray(before.convert('RGB')).astype(float), np.asarray(after.convert('RGB')).astype(float)
check('same size as the game picture', before.size == after.size, (before.size, after.size))
check('bluer than the game grey-green', (b[..., 2] - b[..., 1]).mean() > (a[..., 2] - a[..., 1]).mean() + 3)
x, y, h = (int(v * after.size[0] / 1024) for v in O.BACK)
spot = b[y - h // 3:y + h // 3, x - h // 2:x + h // 2]
check('the hull number in navy on the pale breastplate', (spot.mean(-1) < 90).mean() > 0.05)
check('lighter than the game suit (polished steel)', b.mean() > a.mean() + 40, (round(a.mean()), round(b.mean())))
trim = O._trim(G, O.SUIT, O.BODY_TEX, after.size[0])
plain = trim.ravel() < 0.05
light = lambda im: np.asarray(im.convert('L')).astype(float).ravel()[plain]
c = np.corrcoef(light(before), light(after))[0, 1]
check("the plates' own light kept off the trim", c > 0.8, round(c, 3))
gilt = trim > 0.5
check('gold edging on the great plates only', 0.01 < gilt.mean() < 0.08 and (b[gilt][:, 0] - b[gilt][:, 2]).mean() > 80,
      round(float(gilt.mean()), 3))
bx, by = (int(v * after.size[0] / 1024) for v in O.PLATES['breastplate'])
check('the breastplate edged', trim[:, :].max() > 0.5 and np.any(O.plates_of(G, O._models(G, O.SUIT)['MODL'], O.BODY_TEX, after.size[0])[by, bx]))
nb, nh = O.normals(G)
check('the plates made to shine (normal map alpha)', nb[..., 3].mean() >= O.SHINE and nh[..., 3].mean() >= O.SHINE,
      (round(float(nb[..., 3].mean())), round(float(nh[..., 3].mean()))))
check('the helmet edged too', np.asarray(helm.convert('RGB')).astype(float).std() > 0 and O._trim(G, O.HELMET, O.HELMET_TEX, helm.size[0]).max() > 0.5)
