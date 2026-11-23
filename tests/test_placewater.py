"""placewater: a place copied from a game place for its light keeps none of its water over the floor (22 Nov 2026: 108 of
Waikiki's houses, works places and its cave stood ~6,700 under the water of the Tops' penthouse and the like, and the player
could only walk in them). make_dry puts the water far under; under_water finds the places whose water is over their floor;
health lists them with a fix that makes them dry."""
import copy
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import gamedata  # noqa: E402
import placewater  # noqa: E402
import recordio  # noqa: E402

OK = []


def check(name, cond, info=''):
    OK.append(bool(cond))
    print(('PASS' if cond else 'FAIL') + ' ' + name + (' (%s)' % (info,) if info and not cond else ''))


gd = gamedata.GameData()
suite = next((c for c in gd.interiors if (gd.edid(c) or '') == '2ETopsPresidentialSuite'), None)
check('the game has the Tops\' presidential suite', suite is not None)
rec = recordio.load(gd, suite)
check('its record has water, over 14,000', placewater.flags_of(rec) & placewater.HAS_WATER and placewater.height_of(rec) > 14000,
      placewater.height_of(rec))
dry = placewater.make_dry(copy.deepcopy(rec))
check('a copy made dry keeps the flag', placewater.flags_of(dry) & placewater.HAS_WATER)
check('...with its water far under', placewater.height_of(dry) == placewater.DRY, placewater.height_of(dry))
check('...and nothing else of it changed', [s for s in dry['subs'] if s['tag'] != 'XCLW'] == [s for s in rec['subs'] if s['tag'] != 'XCLW'])

# a place with the flag and no XCLW gets one; a place without the flag is left alone
noh = {'type': 'CELL', 'subs': [{'tag': 'EDID', 'kind': 'z', 'value': 'X'},
                                {'tag': 'DATA', 'kind': 'struct', 'fields': [{'name': 'Flags', 'code': 'B', 'value': 3}]}]}
placewater.make_dry(noh)
check('the flag and no height: a dry height given', placewater.height_of(noh) == placewater.DRY)
plain = {'type': 'CELL', 'subs': [{'tag': 'DATA', 'kind': 'struct', 'fields': [{'name': 'Flags', 'code': 'B', 'value': 1}]}]}
check('no flag: left alone', placewater.make_dry(copy.deepcopy(plain)) == plain)


class P:
    pass


pr = P()
pr.records = {'+000001': copy.deepcopy(rec), '+000002': dry, '+000003': copy.deepcopy(rec)}
pr.records['+000001']['subs'] = [s for s in pr.records['+000001']['subs']]
pr.cells = {'+000001': {'refs': {'+a': {'p': [0, 0, 7372.0, 0, 0, 0]}, '+b': {'p': [0, 0, 7500.0, 0, 0, 0]}}},
            '+000002': {'refs': {'+c': {'p': [0, 0, 7372.0, 0, 0, 0]}}},
            '+000003': {'refs': {'+d': {'p': [0, 0, placewater.height_of(rec) + 100, 0, 0, 0]}}}}
under = placewater.under_water(pr)
check('a copy with the suite\'s water over a floor at 7,372 is under water', [u[0] for u in under] == ['+000001'], under)
ops = placewater.dry_ops(pr, ['+000001'])
check('dry_ops makes it dry', len(ops) == 1 and placewater.height_of(ops[0]['record']) == placewater.DRY)
check('...without touching the mod\'s record before it is applied', placewater.height_of(pr.records['+000001']) > 14000)

import health  # noqa: E402
check('health has the check', 'under_water' in health.KINDS and hasattr(health, 'check_project_water'))
print('%d of %d' % (sum(OK), len(OK)))
