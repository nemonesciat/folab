"""Waikiki's traits (docs/waikiki-traits.md; the user, 25 Nov 2026: "I like those, let's see about adding them in").

Eighteen PERK records of the mod's own laid out as the game's traits (DATA: trait 1, level 1, one rank, playable), picked
two at the new game's trait screen (newgame's ShowTraitMenu, as the game's own VCG04 revision opens it). The game's
traits are overridden as not playable, all but Wild Wasteland.

How each works (`TRAITS`):
- **ab**: an ability (a SPEL of the mod's own, game effects at a magnitude with conditions: swimming, night by the night
  lights' DUSK and DAWN, the weather through the global FOLabTraitSky), given by the perk (PRKE 1) as the game's Small
  Frame and Four Eyes are. nv-rs runs abilities.
- **ep**: a perk entry point laid out as milestones' (prices, damage, healing). Not yet seen run in nv-rs (the Market Day
  console test settles it).
- **s**: the quest FOLabTraits (start enabled, a second a look). Once a trait of these is had (so after the trait
  screen) it sets the starting standings ONCE (`given`): each side's hidden score in FOLabNameOnWater is SET to the
  trait's value, never added (a save's standings are never stacked), with fame or infamy on the side's REPU
  (AddReputation, the game's step 4 of 5 for liked and hated, 3 for disliked); factions turned (SetEnemy, SetAlly);
  money, gear. Every look after: the weather global, the talk and threat globals the parley lines ask, the dives, the
  catchers' bounty, the collectors' week, Soft Touch's ceiling on dread.
- **talk**: the parley's Speech checks (persuade, plead, a yielded pirate joining) ask the global FOLabTraitTalk, your
  Speech, 15 more with Soft Touch; intimidation asks FOLabTraitThreat, your Speech, 100 with Dread Name, 0 with Soft
  Touch; the soft choices (plead, let them go, part) ask FOLabTraitDread 0, so Dread Name closes them.
- Iron Gut: the Raw Reef Fish's radiation asks HasPerk 0. Two Tongues: the money changer's better rate (FOLabMoney's
  `better`, what a Barter haggle wins) set at the start.

    plan(gd, pr)       {'rows', 'skipped'}
    ops(gd, pr, P)     (ops, report): one Undo
"""
import copy
import json
import struct

import recordio

LABEL = "Waikiki's traits"
QUEST, SCRIPT = 'FOLabTraits', 'FOLabTraitsScript'
ISLAND = 'FOLabWaikiki'
NAMES = 'FOLabNameOnWater'
STORM = 'FOLabStormQuest'
MONEY = 'FOLabMoney'
GLOBALS = {'sky': 'FOLabTraitSky', 'talk': 'FOLabTraitTalk', 'threat': 'FOLabTraitThreat', 'dread': 'FOLabTraitDread'}
GETAV, GETGLOBAL, GETINFACTION, ISSWIMMING, GETCURRENTTIME, HASPERK, ISINLIST = 14, 74, 71, 185, 18, 449, 372
SPEECH = 43
DUSK, DAWN = 19.0, 6.0          # (nightlights')
SOFT_EASE, DREAD_THREAT = 15, 100
BOUNTY = 15                     # (kala the court pays for each catcher killed, Sold and Escaped)
DEBT_KALA, DEBT_EVERY, DEBT_TURNS = 300, 7, 2
LIKED, HATED, DISLIKED = 4, 4, 3    # (AddReputation's step: the game's five settings, tiny to massive)
SCORE = {'liked': 40, 'disliked': -30, 'hated': -60, 'feared': 60, 'soft': -40, 'warmer': 20}
SOFT_CEILING = 14               # (repstanding's neutral band: Soft Touch's dread never rises past it)
DIVE = 45.0
SPELL, MASKS = 'VMS15WaterBreathingActual', ('VMS15Rebreather', 'FOLabRebreather')
PIRATE_CAMPS = 'FiendsFactionNV'
VANILLA = ('BuiltToDestroy', 'FastShot', 'FourEyes', 'GoodNatured', 'HeavyHanded', 'Kamikaze', 'LooseCannon', 'SmallFrame',
           'TriggerDiscipline', 'NVDLC03TraitClaustrophobia', 'NVDLC03TraitEarlyBird', 'NVDLC03TraitHoarder',
           'NVDLC03TraitHotBlooded', 'NVDLC03TraitLogansLoophole', 'NVDLC03TraitSkilled')     # (Wild Wasteland stays)
TALK_TOPICS = ('FOLabParleyPersuade', 'FOLabParleyPlead', 'FOLabParleyYieldJoin')
THREAT_TOPICS = ('FOLabParleyIntimidate',)
SOFT_TOPICS = ('FOLabParleyPlead', 'FOLabParleyYieldGo', 'FOLabParleyYieldPart')
SET, ADD, MULT = 1, 2, 3
EPS = {'damage': (0, 3), 'heal': (12, 1), 'buy': (17, 2)}


def AB(*effects):
    """(game MGEF editor ID, magnitude, condition names)"""
    return ('ab', effects)


def EP(point, value, owner=(), weapon=None):
    return ('ep', {'point': point, 'value': value, 'owner': owner, 'weapon': weapon})


# tail: (name, kind, what it says, [effects])
TRAITS = {
    # mild
    'IslandRaised': ('Island Raised', 'mild', "You grew up on the island's shores and trails. +5 Survival, +5 Sneak.",
                     [AB(('IncreaseSkillSurvival', 5, ()), ('IncreaseSkillSneak', 5, ()))]),
    'StrongSwimmer': ('Strong Swimmer', 'mild', "You swim a third faster, and each time you go under you can stay down 45 seconds without air.",
                      [AB(('IncreaseSpeedMult', 30, ('swimming',))), ('s', 'dive')]),
    'FixersHands': ("Fixer's Hands", 'mild', "You were the one people brought broken things to. +5 Repair, +5 Lockpick.",
                    [AB(('IncreaseSkillRepair', 5, ()), ('IncreaseSkillLockpick', 5, ()))]),
    'NightFisher': ('Night Fisher', 'mild', "You fished by lantern light. From dusk to dawn: +1 Perception, +5 Sneak.",
                    [AB(('IncreasePerception', 1, ('night',)), ('IncreaseSkillSneak', 5, ('night',)))]),
    'TwoTongues': ('Two Tongues', 'mild', "You speak the Huang's language as well as the island's. The Huang start out thinking better of you, "
                   "and Qianshang the money changer gives you his better rate from the first day.", [('s', 'twotongues')]),
    'KalaSense': ('Kala Sense', 'mild', "You know what things are worth in kala, tongbao and cells. +10 Barter.",
                  [AB(('IncreaseSkillBarter', 10, ()))]),
    # bonus with a catch
    'CaptainsKin': ("Captain's Kin", 'catch', "Your family served the Kahuna's ships. The court and the Kahuna's people start out liking you. "
                    "The pirates start out hating you, and their road crews attack you on sight.", [('s', 'captainskin')]),
    'RaisedOnTheBoats': ('Raised on the Boats', 'catch', "You grew up on the pirates' boats. The pirates start out liking you, let you walk "
                         "into their camps, and their traders sell to you for less. The court starts out disliking you and its guards watch you.",
                         [EP('buy', 0.85, owner=('pirate trader',)), ('s', 'boats')]),
    'DreadName': ('Dread Name', 'catch', "Your name frightens people. The pirates start out fearing you and threats always work, but you can "
                  "never plead or show mercy, and merchants charge you 15% more.", [EP('buy', 1.15), ('s', 'dread')]),
    'SoftTouch': ('Soft Touch', 'catch', "People trust you. Talking your way past trouble is 15 easier, but threats never work, the pirates take "
                  "you for easy prey, and they never come to fear you.", [('s', 'soft')]),
    'StormTouched': ('Storm-Touched', 'catch', "You were born in a hurricane. In squalls and storms: +2 Strength, +2 Endurance, +15 Action "
                     "Points. In fair weather: -1 Agility, -1 Luck.",
                     [AB(('IncreaseStrength', 2, ('stormy',)), ('IncreaseEndurance', 2, ('stormy',)), ('IncreaseActionPoints', 15, ('stormy',)),
                         ('ReduceAgility', 1, ('fair',)), ('ReduceLuck', 1, ('fair',)))]),
    'ReefFighter': ('Reef Fighter', 'catch', "You learned to fight with the island's own weapons. Its clubs, leiomano and blades do 25% more "
                    "damage in your hands. -10 Guns.", [EP('damage', 1.25, weapon='melee'), AB(('ReduceSkillGuns', 10, ()))]),
    'IronGut': ('Iron Gut', 'catch', "You can eat anything. Raw reef fish gives you no radiation, but Stimpaks and every other kind of healing "
                "heal you 25% less.", [EP('heal', 0.75), ('s', 'fish')]),
    'LightTraveller': ('Light Traveller', 'catch', "You travel light and fast. +15 Action Points, 10% faster, but you carry 50 less.",
                       [AB(('IncreaseActionPoints', 15, ()), ('IncreaseSpeedMult', 10, ()), ('ReduceCarryWeight', 50, ()))]),
    # extreme
    'SoldAndEscaped': ('Sold and Escaped', 'extreme', "You were sold to the catchers and got away. +2 Perception, +2 Agility. The catchers attack "
                       "you on sight wherever they find you, and the court pays you a bounty of 15 kala for each one you kill.",
                       [AB(('IncreasePerception', 2, ()), ('IncreaseAgility', 2, ())), ('s', 'escaped')]),
    'KahunasDebt': ("Kahuna's Debt", 'extreme', "The Kahuna paid for your start: you begin with 300 kala and good gear. Every week his "
                    "collectors come for a quarter of your kala. Refuse and the court turns against you; refuse twice and the "
                    "collectors attack you.", [('s', 'debt')]),
    'Outcast': ('Outcast of Every Shore', 'extreme', "Nobody claims you, so you learned everything yourself. 3 more S.P.E.C.I.A.L. points to "
                "spend and one more tag skill, chosen right after this screen. Every side starts out disliking you.", [('s', 'outcast')]),
    'HalfDrowned': ('Half-Drowned', 'extreme', "You were pulled from the sea after too long under, and something changed. You can breathe "
                    "underwater, and the sea's radiation hardly touches you. -2 Endurance.",
                    [AB(('WaterBreathing', 1, ()), ('IncreaseRadiationResistance', 100, ('swimming',)), ('ReduceEndurance', 2, ()))]),
}
ICON_FROM = {'mild': 'SmallFrame', 'catch': 'GoodNatured', 'extreme': 'WildWasteland'}


def perk_edid(tail):
    return 'FOLabTrait' + tail


# each trait's own emblem (the user, 25 Nov 2026: "I like it"; docs/waikiki-traits/dds, 256 square, white on alpha)
ICON_DIR = 'interface\\icons\\pipboyimages\\perks\\folab\\'
EMBLEMS = 'docs/waikiki-traits/dds'


def emblem(tail):
    import re
    return 'folab_trait_' + re.sub(r'(?<!^)(?=[A-Z])', '_', tail).lower() + '.dds'


def icon_of(tail):
    return ICON_DIR + emblem(tail)


def _mod_key(pr, edid, tag=None):
    return next((k for k, r in pr.records.items() if (tag is None or r.get('type') == tag) and r.get('subs') and recordio.field(r, 'EDID') == edid), None)


def _game(gd, tag, edid):
    return next((f for f, (_i, r) in gd.forms.items() if r.tag == tag and gd.edid(f) == edid), None)


def _key(gd, pr, tag, edid):
    k = _mod_key(pr, edid, tag)
    if k:
        return k
    f = _game(gd, tag, edid)
    return gd.key(f) if f is not None else None


def _cond(fn, op, value, p1=0, p2=0, run=0, orr=False):
    return {'or': orr, 'use_target': False, 'op': op, 'fn': fn, 'p1': p1, 'p2': p2, 'run': run, 'ref': '', 'value': float(value)}


def _named(name, K):
    if name == 'swimming':
        return [_cond(ISSWIMMING, '=', 1)]
    if name == 'night':
        return [_cond(GETCURRENTTIME, '>=', DUSK, orr=True), _cond(GETCURRENTTIME, '<', DAWN)]
    if name == 'stormy':
        return [_cond(GETGLOBAL, '>=', 2, K['glob']['sky'])]
    if name == 'fair':
        return [_cond(GETGLOBAL, '=', 0, K['glob']['sky'])]
    if name == 'pirate trader':        # (asked of the one the perk's owner deals with: the run-on target)
        return [_cond(GETINFACTION, '=', 1, K['traders_faction'], run=1)]
    raise ValueError(name)


def _raw(tag, data):
    return {'tag': tag, 'label': tag, 'kind': 'raw', 'value': data.hex()}


def _entry(eff, K):
    import questrec as qr
    point, tabs = EPS[eff['point']]
    func = MULT
    subs = [{'tag': 'PRKE', 'label': 'Entry', 'kind': 'struct', 'fields': [{'name': 'Type', 'code': 'B', 'value': 2},
                                                                           {'name': 'Rank', 'code': 'B', 'value': 0}, {'name': 'Priority', 'code': 'B', 'value': 0}]},
            _raw('DATA', bytes((point, func, tabs)))]
    owner = [c for n in eff['owner'] for c in _named(n, K)]
    weapon = [_cond(ISINLIST, '=', 1, K['melee'])] if eff['weapon'] == 'melee' else []
    for tab, conds in ((0, owner), (1, weapon)):
        if conds:
            subs.append({'tag': 'PRKC', 'label': 'Condition runs on', 'kind': 'struct', 'fields': [{'name': 'Who', 'code': 'b', 'value': tab}]})
            subs += [qr.condition_sub(c) for c in conds]
    subs += [{'tag': 'EPFT', 'label': 'Entry value type', 'kind': 'struct', 'fields': [{'name': 'Type', 'code': 'B', 'value': 1}]},
             _raw('EPFD', struct.pack('<f', eff['value'])),
             {'tag': 'PRKF', 'label': 'Marker', 'kind': 'struct', 'fields': []}]
    return subs


def _mgef_av(gd, f):
    import tes4
    n, r = gd.forms[f]
    data = dict((t, v) for t, v in tes4.iter_subrecords(gd.plugins[n].data(r)))['DATA']
    return struct.unpack_from('<i', data, 68)[0]


def ability_record(gd, edid, name, effects, K):
    """A SPEL ability (RexBloodLegion's layout), each effect a game MGEF with its own actor value and conditions."""
    import questrec as qr
    rec = json.loads(json.dumps(recordio.load(gd, _game(gd, 'SPEL', 'RexBloodLegion'))))
    rec['src'] = ''
    efid = next(s for s in rec['subs'] if s['tag'] == 'EFID')
    efit = next(s for s in rec['subs'] if s['tag'] == 'EFIT')
    subs = [s for s in rec['subs'] if s['tag'] not in ('EFID', 'EFIT', 'CTDA')]
    for s in subs:
        if s['tag'] == 'EDID':
            s['value'] = edid
        elif s['tag'] == 'FULL':
            s['value'] = name
    for mgef, mag, conds in effects:
        f = _game(gd, 'MGEF', mgef)
        if f is None:
            raise ValueError('the game has no effect %s' % mgef)
        e1 = dict(json.loads(json.dumps(efid)), value=gd.key(f))
        e2 = json.loads(json.dumps(efit))
        for q in e2['fields']:
            nm = (q.get('name') or '').lower()
            if nm == 'magnitude':
                q['value'] = mag
            elif 'actor' in nm:
                q['value'] = _mgef_av(gd, f)
        subs += [e1, e2] + [qr.condition_sub(c) for n in conds for c in _named(n, K)]
    rec['subs'] = subs
    return rec


def perk_record(tail, name, words, icon, entries):
    subs = [{'tag': 'EDID', 'label': 'Editor ID', 'kind': 'z', 'value': perk_edid(tail)},
            {'tag': 'FULL', 'label': 'Name', 'kind': 'z', 'value': name},
            {'tag': 'DESC', 'label': 'Description', 'kind': 'z', 'value': words}]
    if icon:
        subs.append({'tag': 'ICON', 'label': 'Icon', 'kind': 'z', 'value': icon})
    subs.append({'tag': 'DATA', 'label': 'Data', 'kind': 'struct', 'fields': [
        {'name': 'Trait', 'code': 'B', 'value': 1}, {'name': 'Level', 'code': 'B', 'value': 1},
        {'name': 'Ranks', 'code': 'B', 'value': 1}, {'name': 'Playable', 'code': 'B', 'value': 1},
        {'name': 'Hidden', 'code': 'B', 'value': 0}]})
    return {'type': 'PERK', 'flags': 0, 'src': '', 'subs': subs + entries}


def _glob(edid):
    return {'type': 'GLOB', 'flags': 0, 'src': '', 'subs': [
        {'tag': 'EDID', 'label': 'Editor ID', 'kind': 'z', 'value': edid},
        {'tag': 'FNAM', 'label': 'Type', 'kind': 'struct', 'fields': [{'name': 'Type', 'code': 'B', 'value': ord('s')}]},
        {'tag': 'FLTV', 'label': 'Value', 'kind': 'struct', 'fields': [{'name': 'Value', 'code': 'f', 'value': 0.0}]}]}


def _script_text(pr, key):
    r = pr.records.get(key) or {}
    for s in r.get('subs', []):
        if s['tag'] == 'SCTX':
            v = s.get('value')
            try:
                return bytes.fromhex(v).decode('cp1252', 'replace') if isinstance(v, str) else str(v)
            except ValueError:
                return str(v)
    return ''


def _factions_of(rec):
    out = []
    for s in rec.get('subs', []):
        if s['tag'] == 'SNAM':
            v = s['fields'][0].get('value') if s.get('fields') else s.get('value')
            out.append(str(v))
    return out


def _find(gd, pr):
    """Everything the traits name, found in the mod and the game; missing ones listed."""
    K, missing = {}, []
    for k, (tag, edid) in {'court': ('REPU', 'FOLabRepCourt'), 'pirates': ('REPU', 'FOLabRepPirates'),
                           'huang': ('REPU', 'FOLabRepHuang'), 'guard': ('REPU', 'FOLabRepGuard'),
                           'parley_faction': ('FACT', 'FOLabParleyPirates'), 'catchers_faction': ('FACT', 'FOLabCatchersFaction'),
                           'collectors_faction': ('FACT', 'FOLabCollectorsFaction'), 'traders_faction': ('FACT', 'FOLabPirateTraders'),
                           'camps_faction': ('FACT', PIRATE_CAMPS), 'melee': ('FLST', 'FOLabIslandMelee'),
                           'names': ('QUST', NAMES), 'storm': ('QUST', STORM), 'money': ('QUST', MONEY),
                           'fish': ('ALCH', 'FOLabRawReefFish'), 'spell': ('SPEL', SPELL)}.items():
        K[k] = _key(gd, pr, tag, edid)
        if not K[k]:
            missing.append(edid)
    K['masks'] = [m for m in MASKS if _key(gd, pr, 'ARMO', m)]
    nk = _mod_key(pr, NAMES + 'Script', 'SCPT')
    text = _script_text(pr, nk) if nk else ''
    K['sides'] = [s for s in ('court', 'pirates', 'huang', 'guard') if ('short %s' % s) in text]
    mk = _mod_key(pr, MONEY + 'Script', 'SCPT')
    K['money_better'] = bool(mk and 'short better' in _script_text(pr, mk))
    K['catchers'] = sorted(recordio.field(r, 'EDID') for k, r in pr.records.items()
                           if r.get('type') == 'NPC_' and r.get('subs') and K['catchers_faction'] in _factions_of(r))
    gear = []
    for tag, word in (('ARMO', 'Koa'), ('WEAP', 'Leiomano'), ('ARMO', 'Mahiole')):
        e = next((recordio.field(r, 'EDID') for k, r in sorted(pr.records.items())
                  if r.get('type') == tag and r.get('subs') and word.lower() in (recordio.field(r, 'FULL') or '').lower()), None)
        if e:
            gear.append(e)
    K['gear'] = gear
    return K, missing


def plan(gd, pr):
    rep = {'rows': [], 'skipped': []}
    if _mod_key(pr, perk_edid('IslandRaised'), 'PERK'):
        rep['skipped'].append(('all', 'the traits are in the mod already (Undo first)'))
        return rep
    K, missing = _find(gd, pr)
    for need in ('names', 'melee', 'court', 'pirates', 'huang'):
        if not K[need]:
            rep['skipped'].append(('all', 'not in the mod: %s' % need))
    for m in missing:
        rep['skipped'].append(('part', 'not found: %s' % m))
    topics = {k: recordio.field(r, 'EDID') for k, r in pr.records.items() if r.get('type') == 'DIAL' and r.get('subs')}
    lines = {t: sorted(k for k, r in pr.records.items() if r.get('type') == 'INFO' and topics.get(r.get('topic')) == t)
             for t in set(TALK_TOPICS + THREAT_TOPICS + SOFT_TOPICS)}
    vanilla = [v for v in VANILLA if _game(gd, 'PERK', v) is not None]
    rep['rows'] += [{'what': 'traits', 'traits': [perk_edid(t) for t in TRAITS]},
                    {'what': 'found', 'sides': K['sides'], 'catchers': len(K['catchers']), 'gear': K['gear'],
                     'money_better': K['money_better'], 'masks': K['masks']},
                    {'what': 'parley lines', 'lines': {t: len(v) for t, v in lines.items()}},
                    {'what': 'game traits not playable', 'traits': vanilla}]
    rep['K'], rep['lines'], rep['vanilla'] = K, lines, vanilla
    return rep


def quest_source(K):
    """The traits quest: the start once, then every look."""
    P = perk_edid
    G = GLOBALS
    sides = K['sides']
    L = ['scn %s' % SCRIPT, 'short given', 'short outcast', 'short dive', 'float divetime', 'short kills', 'short now', 'short n',
         'short choosing', 'short button', 'short refused', 'float debtday', 'short masked', '', 'Begin GameMode']
    # a debt message waiting for its button
    L += ['\tif choosing', '\t\tset button to GetButtonPressed', '\t\tif button == -1', '\t\t\treturn', '\t\tendif',
          '\t\tset choosing to 0', '\t\tif button == 0', '\t\t\tset n to player.GetItemCount Caps001 / 4', '\t\t\tif n > 0',
          '\t\t\t\tplayer.RemoveItem Caps001 n', '\t\t\tendif', '\t\t\tShowMessage FOLabTraitDebtPaidMsg', '\t\telse',
          '\t\t\tset refused to refused + 1', '\t\t\tAddReputation FOLabRepCourt 0 2']
    if 'court' in sides:
        L += ['\t\t\tset %s.court to %s.court - 15' % (NAMES, NAMES)]
    L += ['\t\t\tif refused >= %d' % DEBT_TURNS]
    if K['collectors_faction']:
        L += ['\t\t\t\tSetEnemy FOLabCollectorsFaction PlayerFaction']
    L += ['\t\t\t\tShowMessage FOLabTraitCourtTurnsMsg', '\t\t\telse', '\t\t\t\tShowMessage FOLabTraitDebtRefusedMsg', '\t\t\tendif',
          '\t\tendif', '\t\treturn', '\tendif']
    # the globals the abilities and the parley lines ask
    if K['storm']:
        L += ['\tset %s to %s.sky' % (G['sky'], STORM)]
    L += ['\tif player.HasPerk %s' % P('SoftTouch'), '\t\tset %s to player.GetActorValue Speech + %d' % (G['talk'], SOFT_EASE),
          '\t\tset %s to 0' % G['threat'], '\telse', '\t\tset %s to player.GetActorValue Speech' % G['talk'],
          '\t\tset %s to player.GetActorValue Speech' % G['threat'], '\tendif',
          '\tif player.HasPerk %s' % P('DreadName'), '\t\tset %s to %d' % (G['threat'], DREAD_THREAT), '\t\tset %s to 1' % G['dread'],
          '\telse', '\t\tset %s to 0' % G['dread'], '\tendif']
    # the start, once: after the trait screen (a trait of these is had only from it)
    L += ['\tif given == 0', '\t\tset n to 0']
    for t in TRAITS:
        L += ['\t\tif player.HasPerk %s' % P(t), '\t\t\tset n to 1', '\t\tendif']
    L += ['\t\tif n == 0', '\t\t\treturn', '\t\tendif', '\t\tset given to 1']
    score = lambda side, v: ['\t\t\tset %s.%s to %d' % (NAMES, side, v)] if side in sides else []
    rep = lambda side, fame, step: ['\t\t\tAddReputation %s %d %d' % (K[side] and {'court': 'FOLabRepCourt', 'pirates': 'FOLabRepPirates',
                                                                                     'huang': 'FOLabRepHuang', 'guard': 'FOLabRepGuard'}[side], fame, step)] if K.get(side) else []
    # (Outcast first, so a trait naming one side sets that side after it)
    L += ['\t\tif player.HasPerk %s' % P('Outcast')]
    for side in ('court', 'pirates', 'huang', 'guard'):
        L += rep(side, 0, DISLIKED) + score(side, SCORE['disliked'])
    L += ['\t\t\tset outcast to 1', '\t\tendif']
    L += ['\t\tif player.HasPerk %s' % P('TwoTongues')] + score('huang', SCORE['warmer']) + \
         (['\t\t\tset %s.better to 1' % MONEY] if K['money_better'] else []) + ['\t\tendif']
    L += ['\t\tif player.HasPerk %s' % P('CaptainsKin')] + rep('court', 1, LIKED) + score('court', SCORE['liked']) + \
         rep('pirates', 0, HATED) + score('pirates', SCORE['hated']) + \
         (['\t\t\tSetEnemy FOLabParleyPirates PlayerFaction'] if K['parley_faction'] else []) + ['\t\tendif']
    L += ['\t\tif player.HasPerk %s' % P('RaisedOnTheBoats')] + rep('pirates', 1, LIKED) + score('pirates', SCORE['liked']) + \
         rep('court', 0, DISLIKED) + score('court', SCORE['disliked']) + \
         (['\t\t\tSetAlly %s PlayerFaction' % PIRATE_CAMPS] if K['camps_faction'] else []) + ['\t\tendif']
    L += ['\t\tif player.HasPerk %s' % P('DreadName')] + score('pirates', SCORE['feared']) + ['\t\tendif']
    L += ['\t\tif player.HasPerk %s' % P('SoftTouch')] + score('pirates', SCORE['soft']) + ['\t\tendif']
    L += ['\t\tif player.HasPerk %s' % P('SoldAndEscaped')] + \
         (['\t\t\tSetEnemy FOLabCatchersFaction PlayerFaction'] if K['catchers_faction'] else []) + ['\t\tendif']
    L += ['\t\tif player.HasPerk %s' % P('KahunasDebt'), '\t\t\tplayer.AddItem Caps001 %d' % DEBT_KALA] + \
         ['\t\t\tplayer.AddItem %s 1' % g for g in K['gear']] + \
         ['\t\t\tplayer.AddItem Stimpak 4', '\t\t\tset debtday to GameDaysPassed + %d' % DEBT_EVERY, '\t\tendif']
    L += ['\t\treturn', '\tendif']
    # Outcast's screens, one a look (a menu stops GameMode, so the next opens when the last one closes)
    L += ['\tif outcast == 1', '\t\tset outcast to 2', '\t\tSetSPECIALPoints 43', '\t\treturn',
          '\telseif outcast == 2', '\t\tset outcast to 3', '\t\tSetTagSkills 4', '\t\treturn', '\tendif']
    # Soft Touch: dread never rises
    if 'pirates' in sides:
        L += ['\tif player.HasPerk %s' % P('SoftTouch'), '\t\tif %s.pirates > %d' % (NAMES, SOFT_CEILING),
              '\t\t\tset %s.pirates to %d' % (NAMES, SOFT_CEILING), '\t\tendif', '\tendif']
    # Strong Swimmer: breath for each dive (Half-Drowned breathes anyway)
    if K['spell']:
        L += ['\tif player.HasPerk %s && player.HasPerk %s == 0' % (P('StrongSwimmer'), P('HalfDrowned')),
              '\t\tset masked to 0']
        for m in K['masks']:
            L += ['\t\tif player.GetEquipped %s' % m, '\t\t\tset masked to 1', '\t\tendif']
        L += ['\t\tif player.IsSwimming', '\t\t\tif dive == 0', '\t\t\t\tset dive to 1', '\t\t\t\tset divetime to %s' % DIVE,
              '\t\t\t\tplayer.AddSpell %s' % SPELL, '\t\t\telseif dive == 1', '\t\t\t\tset divetime to divetime - GetSecondsPassed',
              '\t\t\t\tif divetime <= 0', '\t\t\t\t\tset dive to 2', '\t\t\t\t\tif masked == 0', '\t\t\t\t\t\tplayer.RemoveSpell %s' % SPELL,
              '\t\t\t\t\tendif', '\t\t\t\tendif', '\t\t\tendif', '\t\telse', '\t\t\tif dive == 1 && masked == 0',
              '\t\t\t\tplayer.RemoveSpell %s' % SPELL, '\t\t\tendif', '\t\t\tset dive to 0', '\t\tendif', '\tendif']
    # Sold and Escaped: the court's bounty for each catcher killed
    if K['catchers']:
        L += ['\tif player.HasPerk %s' % P('SoldAndEscaped'), '\t\tset now to 0']
        L += ['\t\tset now to now + GetDeadCount %s' % e for e in K['catchers']]
        L += ['\t\tif now > kills', '\t\t\tset n to (now - kills) * %d' % BOUNTY, '\t\t\tset kills to now',
              '\t\t\tplayer.AddItem Caps001 n', '\t\t\tShowMessage FOLabTraitBountyMsg', '\t\tendif', '\tendif']
    # Kahuna's Debt: the collectors' week
    L += ['\tif player.HasPerk %s && refused < %d' % (P('KahunasDebt'), DEBT_TURNS),
          '\t\tif GameDaysPassed >= debtday && debtday > 0 && player.IsInCombat == 0',
          '\t\t\tset debtday to GameDaysPassed + %d' % DEBT_EVERY, '\t\t\tShowMessage FOLabTraitDebtMsg', '\t\t\tset choosing to 1',
          '\t\tendif', '\tendif', 'End', '']
    return '\n'.join(L)


MESSAGES = {
    'FOLabTraitDebtMsg': ("The Kahuna's collectors have found you. They want a quarter of your kala, as agreed.",
                          ('Pay a quarter of my kala', 'Refuse')),
    'FOLabTraitDebtPaidMsg': ("The collectors count your kala, take their quarter and go. They'll be back in a week.", ()),
    'FOLabTraitDebtRefusedMsg': ("The collectors leave without a word. The court will hear of this.", ()),
    'FOLabTraitCourtTurnsMsg': ("You've refused the Kahuna twice. His collectors won't ask again.", ()),
    'FOLabTraitBountyMsg': ("The court pays its bounty on catchers: 15 kala for each one you killed.", ()),
}


def _edit_conditions(rec, change):
    """rec with its CTDA subrecords passed through change(conds) -> conds (they may be replaced and added to)."""
    import questrec as qr
    rec = copy.deepcopy(rec)
    idx = [i for i, s in enumerate(rec['subs']) if s['tag'] == 'CTDA']
    if not idx:
        return None
    conds = [qr.condition_plain(rec['subs'][i]) for i in idx]
    new = change(conds)
    if new is None:
        return None
    subs = [s for i, s in enumerate(rec['subs']) if i not in idx]
    at = idx[0]
    rec['subs'] = subs[:at] + [qr.condition_sub(c) for c in new] + subs[at:]
    return rec


def line_ops(pr, P, K):
    """The parley lines: Speech checks asked of the talk and threat globals, soft choices closed for Dread Name."""
    out, n = [], {'talk': 0, 'threat': 0, 'closed': 0}
    glob = K['glob']
    for topic, keys in sorted(P['lines'].items()):
        for k in keys:
            def change(conds, topic=topic):
                hit = False
                res = []
                for c in conds:
                    if int(c['fn']) == GETAV and str(c.get('p1')).split('.')[0] == str(SPEECH) and topic in TALK_TOPICS + THREAT_TOPICS:
                        c = dict(c, fn=GETGLOBAL, p1=glob['talk' if topic in TALK_TOPICS else 'threat'], p2=0, run=0)
                        c.pop('size', None)
                        c.pop('pads', None)
                        n['talk' if topic in TALK_TOPICS else 'threat'] += 1
                        hit = True
                    res.append(c)
                if topic in SOFT_TOPICS:
                    if res and res[-1].get('or'):
                        raise ValueError('a line ends in an OR condition: %s' % k)
                    res.append(_cond(GETGLOBAL, '=', 0, glob['dread']))
                    n['closed'] += 1
                    hit = True
                return res if hit else None
            rec = _edit_conditions(pr.records[k], change)
            if rec is not None:
                out.append({'op': 'record', 'key': k, 'record': rec})
    return out, n


def fish_op(gd, pr, K, perk):
    """Iron Gut: each radiation effect of the Raw Reef Fish asks HasPerk 0."""
    import questrec as qr
    if not K['fish'] or not str(K['fish']).startswith('+'):
        return None, 0
    rec = copy.deepcopy(pr.records[K['fish']])
    subs, n = [], 0
    pending = False
    for s in rec['subs']:
        if pending and s['tag'] != 'CTDA':
            subs.append(qr.condition_sub(_cond(HASPERK, '=', 0, perk)))
            n += 1
            pending = False
        subs.append(s)
        if s['tag'] == 'EFID':
            f = gd.from_key(s['value']) if not str(s['value']).startswith('+') else None
            pending = f is not None and 'Radiation' in (gd.edid(f) or '')
        elif s['tag'] == 'EFIT' and not pending:
            pass
    if pending:
        subs.append(qr.condition_sub(_cond(HASPERK, '=', 0, perk)))
        n += 1
    rec['subs'] = subs
    return ({'op': 'record', 'key': K['fish'], 'record': rec} if n else None), n


def ops(gd, pr, P=None):
    import api_scripts
    import generators
    import questrec as qr
    from activity import _new_key
    P = P or plan(gd, pr)
    if any(w == 'all' for w, _x in P['skipped']):
        raise ValueError('; '.join(x for w, x in P['skipped'] if w == 'all'))
    K = dict(P['K'])
    out, extra, rep = [], {}, {'made': [], 'skipped': list(P['skipped'])}

    def record(edid, rec, key=None):
        k = key or _new_key(pr)
        extra[k] = rec
        out.append({'op': 'record', 'key': k, 'record': rec})
        rep['made'].append(edid)
        return k
    K['glob'] = {g: record(e, _glob(e)) for g, e in GLOBALS.items()}
    icons = {}
    for kind, e in ICON_FROM.items():
        f = _game(gd, 'PERK', e)
        icons[kind] = recordio.field(recordio.load(gd, f), 'ICON') if f else ''
    perks, ways = {}, {}
    for tail, (name, kind, words, effs) in TRAITS.items():
        entries, how = [], []
        for eff in effs:
            if eff[0] == 'ab':
                sk = record(perk_edid(tail) + 'Ability', ability_record(gd, perk_edid(tail) + 'Ability', name, eff[1], K))
                entries += [{'tag': 'PRKE', 'label': 'Entry', 'kind': 'struct', 'fields': [
                    {'name': 'Type', 'code': 'B', 'value': 1}, {'name': 'Rank', 'code': 'B', 'value': 0}, {'name': 'Priority', 'code': 'B', 'value': 0}]},
                    {'tag': 'DATA', 'label': 'Data', 'kind': 'F', 'value': sk},
                    {'tag': 'PRKF', 'label': 'Marker', 'kind': 'struct', 'fields': []}]
                how.append('ability')
            elif eff[0] == 'ep':
                if eff[1]['owner'] and not K['traders_faction']:
                    rep['skipped'].append((tail, 'no pirate traders faction: the discount left out'))
                    continue
                entries += _entry(eff[1], K)
                how.append('entry point %s' % eff[1]['point'])
            else:
                how.append('script %s' % eff[1])
        perks[tail] = record(perk_edid(tail), perk_record(tail, name, words, icon_of(tail), entries))
        ways[name] = how
    # the game's traits, not playable (Wild Wasteland stays)
    for v in P['vanilla']:
        f = _game(gd, 'PERK', v)
        rec = copy.deepcopy(recordio.load(gd, f))
        data = next(s for s in rec['subs'] if s['tag'] == 'DATA')
        fld = next((q for q in data.get('fields', []) if q.get('name') == 'Playable'), None)
        if fld is None:
            raise ValueError('%s: no Playable field in DATA' % v)
        fld['value'] = 0
        out.append({'op': 'record', 'key': gd.key(f), 'record': rec})
    rep['not_playable'] = list(P['vanilla'])
    for edid, (words, buttons) in MESSAGES.items():
        record(edid, generators._message(edid, words.replace('%', ' per cent'), buttons))
    qk, qsk = _new_key(pr), _new_key(pr)
    quest = qr.quest_record({'edid': QUEST, 'script': qsk, 'name': '', 'flags': {'start_enabled': True}, 'priority': 30,
                             'delay': 1.0, 'stages': [], 'objectives': []})
    sc = api_scripts.scripts()
    c = sc.compile(quest_source(K), qsk, 'quest', dict(extra, **{qk: quest}))
    if not hasattr(c, 'subrecords'):
        raise ValueError("the traits quest's script: %s" % (c,))
    record(SCRIPT, sc._record_of(c, SCRIPT), qsk)
    record(QUEST, quest, qk)
    lo, rep['parley'] = line_ops(pr, P, K)
    out += lo
    fo, rep['fish_effects'] = fish_op(gd, pr, K, perks['IronGut'])
    if fo:
        out.append(fo)
    else:
        rep['skipped'].append(('IronGut', 'the Raw Reef Fish has no radiation effect of its own to condition'))
    rep['ways'] = ways
    rep['traits'] = len(perks)
    rep['keys'] = {'quest': qk}
    return out, rep


def put_emblems(pr, root=None):
    """The emblems into the mod's own files (textures\\<ICON_DIR>); returns the paths written."""
    import os
    import library
    src = root or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), EMBLEMS)
    out = []
    for tail in TRAITS:
        rel = 'textures\\' + icon_of(tail)
        library._put(library.assets_dir(pr), rel, open(os.path.join(src, emblem(tail)), 'rb').read())
        out.append(rel)
    return out


def icon_ops(pr):
    """For a mod that has the traits already: each trait's ICON set to its emblem."""
    out = []
    for tail in TRAITS:
        k = _mod_key(pr, perk_edid(tail), 'PERK')
        if not k:
            raise ValueError('no %s in the mod' % perk_edid(tail))
        rec = copy.deepcopy(pr.records[k])
        if any(s['tag'] == 'ICON' for s in rec['subs']):
            recordio.set_field(rec, 'ICON', icon_of(tail))
        else:
            at = next(i for i, s in enumerate(rec['subs']) if s['tag'] == 'DESC') + 1
            rec['subs'].insert(at, {'tag': 'ICON', 'label': 'Icon', 'kind': 'z', 'value': icon_of(tail)})
        out.append({'op': 'record', 'key': k, 'record': rec})
    return out


def apply(pr, gd, P=None):
    o, rep = ops(gd, pr, P)
    pr.apply(LABEL, o)
    rep['emblems'] = len(put_emblems(pr))
    return rep
