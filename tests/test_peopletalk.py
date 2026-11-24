"""peopletalk: every one of Waikiki's people (the 59 the mod had on 23 Nov 2026) has a unit; lines the game's font prints;
crowds varied; every bark topic a line for each group; a crowd's voice folders found through its levelled list."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'app'))
import peopletalk as PT  # noqa: E402

FAILS = []


def check(what, ok):
    print(('PASS ' if ok else 'FAIL ') + what)
    if not ok:
        FAILS.append(what)


WAIKIKI = """FOLabBeachSurfer FOLabBeachcomber FOLabCourtFighter01 FOLabCourtFighter02 FOLabCourtFighter03 FOLabCourtFighter04
FOLabCourtFighter05 FOLabCourtFighter06 FOLabCourtFighter07 FOLabCourtFighter08 FOLabFlotillaCaptain FOLabFlotillaCaptive01
FOLabFlotillaCaptive02 FOLabFlotillaCaptive03 FOLabFlotillaCaptive04 FOLabFlotillaCaptive05 FOLabFlotillaPenGuard
FOLabFlotillaQuartermaster FOLabKahunaGuard01 FOLabKahunaGuard02 FOLabKahunaGuard03 FOLabKahunaGuard04 FOLabKahunaGuard05
FOLabKahunaGuard06 FOLabKuliCatcher FOLabKuliCatcher2 FOLabKuliFather FOLabKuliPirate FOLabKuliSon FOLabKuliStranger
FOLabKuliWoman FOLabMarketGoer FOLabMarketSeller FOLabPatrolCourt01 FOLabPatrolCourt02 FOLabPierFisher FOLabPirateCaptain
FOLabPirateCaptainAiona FOLabPirateCaptainVega FOLabPirateDockhand FOLabPirateLvlFiend2GunVarNV FOLabPirateLvlFiend2MeleeVarNV
FOLabPirateLvlFiend2RifleVarNV FOLabPirateLvlRaider1GunVar FOLabPirateLvlRaider1MeleeVar FOLabPirateLvlWastelander
FOLabPirateRaider FOLabPirateRoadside FOLabPirateVJackalGangSpawnFemale FOLabPirateVJackalGangSpawnMale
FOLabPirateVViperGangSpawnGunA FOLabPirateVViperGangSpawnGunB FOLabSurferVSpawnProspectorAll FOLabWaikikiDoctor
FOLabWaikikiGrocer FOLabWaikikiGunsmith FOLabWaikikiLocal FOLabWaikikiLocal2 FOLabWaikikiTrader""".split()


class FakePR:
    def __init__(self, edids):
        self.records = {'+%06X' % (0x100 + n): {'type': 'NPC_', 'subs': [{'tag': 'EDID', 'value': e}]} for n, e in enumerate(edids)}


import types  # noqa: E402
sys.modules.setdefault('huangland', types.SimpleNamespace(faction_key=lambda pr: None, is_huang=lambda pr, k, fac=None: False))
PT._edid = lambda pr, k: next((s['value'] for s in (pr.records.get(k) or {}).get('subs', ()) if s['tag'] == 'EDID'), '')
pr = FakePR(WAIKIKI)
us = PT.units(pr)
covered = [PT._edid(pr, k) for u in us for k in u['keys']]
check('every one of the 59 is in exactly one unit', sorted(covered) == sorted(WAIKIKI))
check('every named person in NAMED is one of them', set(PT.NAMED) <= set(WAIKIKI))
for u in us:
    for t in PT.TOPICS:
        lines = u['lines'].get(t) or []
        if not lines or len(lines) < (4 if len(u['keys']) > 3 else 2) or len(set(lines)) != len(lines):
            check('%s: %s has %d different lines' % (u['name'], t, len(set(lines))), False)
check('named people two different lines a topic, big crowds at least four', not FAILS)
texts = [x for u in us for t in PT.TOPICS for x in u['lines'][t]]
texts += [x for b, _m in PT.BARKS.values() for xs in b.values() for x in xs]
check('every line plain ASCII (the game\'s font), at most 80 characters', all(x.isascii() and 0 < len(x) <= 80 for x in texts))
check('no two named people say the same goodbye', len({x for e, (_r, d) in PT.NAMED.items() for x in d['GOODBYE']})
      == sum(len(d['GOODBYE']) for _r, d in PT.NAMED.values()))
for role in ('fighter', 'pirate', 'civil'):
    check('every bark topic has a line for %s' % role, all(PT._bark_lines(role, t) for t in PT.BARKS))
check('bark faces are the game\'s emotions (0-7) and strengths', all(0 <= e <= 7 and 0 < s <= 100 for _b, (e, s) in PT.BARKS.values()))

# a crowd record whose traits come from a levelled list: each voice type in the list, through a nested list
import api_voices as av  # noqa: E402
recs = {
    '+A': {'type': 'NPC_', 'subs': [{'tag': 'TPLT', 'value': '+L'}, {'tag': 'VTCK', 'value': '+VMD'},
                                     {'tag': 'ACBS', 'fields': [{'name': 'Flags', 'value': 0}, {'name': 'Template flags', 'value': 1}]}]},
    '+L': {'type': 'LVLN', 'subs': [{'tag': 'LVLO', 'fields': [{'name': 'Level', 'value': 1}, {'name': 'Reference', 'value': '+B'}]},
                                     {'tag': 'LVLO', 'fields': [{'name': 'Level', 'value': 1}, {'name': 'Reference', 'value': '+L2'}]}]},
    '+L2': {'type': 'LVLN', 'subs': [{'tag': 'LVLO', 'fields': [{'name': 'Level', 'value': 1}, {'name': 'Reference', 'value': '+C'}]}]},
    '+B': {'type': 'NPC_', 'subs': [{'tag': 'VTCK', 'value': '+VM3'}, {'tag': 'ACBS', 'fields': [{'name': 'Flags', 'value': 0}]}]},
    '+C': {'type': 'NPC_', 'subs': [{'tag': 'VTCK', 'value': '+VF2'}, {'tag': 'ACBS', 'fields': [{'name': 'Flags', 'value': 1}]}]},
}
names = {'+VMD': 'MaleAdult01Default', '+VM3': 'MaleAdult03', '+VF2': 'FemaleAdult02'}
av._record = lambda gd, pr, k: recs.get(k)
av.edid = lambda gd, pr, k: names.get(k, '')
import recordio  # noqa: E402
recordio.field = lambda rec, tag: next((s.get('value') for s in rec['subs'] if s['tag'] == tag), None)
got = PT.folders(None, None, ['+A'])
check('a crowd speaks from each voice type its list gives, not its own: %s' % got,
      got == {'maleadult03': False, 'femaleadult02': True})
if FAILS:
    sys.exit(1)
