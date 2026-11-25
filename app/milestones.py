"""Skill-milestone perks (docs/waikiki-speech-science.md K4, K5; the user, 25 Nov 2026: "Perks you get for hitting skill
milestones ... let's design a complete system and then build it. no more what if").

**The quest FOLabMilestones** watches the thirteen skills (GetPermanentActorValue on the player, a second a look). The first
time a skill reaches 50 or 75 it gives that milestone's perk (AddPerk) and shows a message saying what it does. At 100 a
message with two buttons offers a choice of two perks (GetButtonPressed). Each milestone once (the quest's variables).
One milestone a look, so messages never stack.

**The perks** (`PERKS`): PERK records of the mod's own, not playable (they're given, so the level-up list never shows them),
shown on the Pip-Boy's perks page. Each is one of:
- **an entry point** (`EP`): the game's own way. nv-rs runs BGSEntryPoint::HandleEntryPoint at the exe's sites (barter's buy
  price, 0x11, in bartermenu.rs; damage, AP cost, healing, carry weight, run speed...), read from its source 25 Nov 2026,
  not yet seen run with one of FOLab's. Laid out as the game's: PRKE 2, DATA (point, function, filter tabs: the counts the
  game's own perks and nv-rs's call sites use), PRKC + CTDA for a filter (LaserCommander's shape), EPFT 1, EPFD, PRKF.
  The entry points' numbers were read from the exe's own name strings and checked against the game's perks that use them.
- **an ability** (`AB`): a SPEL of the mod's own with game effects (IncreaseSkillSneak, IncreaseUnarmedDamage...), each with
  its conditions (in the island's world, swimming, at night, health low).
- **a hook** (`HOOK`): the use it boosts asks HasPerk in its own lines or script. Those for uses already in the mod are
  added by `milestonehooks.py`; the rest come with the K2 uses they boost.

    plan(gd, pr)       {'rows', 'skipped'}
    apply(pr, gd, P)   one Undo
"""
import json
import struct

import recordio

LABEL = 'Skill-milestone perks'
QUEST, SCRIPT = 'FOLabMilestones', 'FOLabMilestonesScript'
ISLAND = 'FOLabWaikiki'
GETPERMAV, GETINWORLDSPACE, ISINLIST, ISWEAPONSKILLTYPE, ISSWIMMING, GETCURRENTTIME, GETHEALTHPCT = 495, 310, 372, 109, 185, 18, 431
SET, ADD, MULT = 1, 2, 3
# entry point: (number, filter tabs)
EPS = {'damage': (0, 3), 'crit': (1, 3), 'apcost': (3, 2), 'limb': (6, 3), 'tohit': (8, 3), 'heal': (12, 1), 'buy': (17, 2),
       'carry': (22, 1), 'hackbonus': (30, 1), 'jury': (48, 1), 'runspeed': (42, 1), 'knockdown': (52, 2)}
LISTS = {'guns': ('FOLabIslandGuns', ()), 'melee': ('FOLabIslandMelee', ())}       # (filled from the mod's own weapons by equip type)
GUN_TYPES, MELEE_TYPES = (0, 2), (3,)      # (WEAP ETYP: big guns, small guns; melee)
AV = {'Barter': 32, 'EnergyWeapons': 34, 'Explosives': 35, 'Lockpick': 36, 'Medicine': 37, 'MeleeWeapons': 38, 'Repair': 39,
      'Science': 40, 'Guns': 41, 'Sneak': 42, 'Speech': 43, 'Survival': 44, 'Unarmed': 45}
SHOWN = {'EnergyWeapons': 'Energy Weapons', 'MeleeWeapons': 'Melee Weapons'}
ISL = ('island',)            # (a condition on the perk's owner: in the island's world)


def EP(point, func, value, owner=(), weapon=None, skill=None):
    return {'kind': 'ep', 'point': point, 'func': func, 'value': value, 'owner': owner, 'weapon': weapon, 'skill': skill}


def AB(*effects):
    """effects: (game MGEF editor ID, magnitude, (condition names...))"""
    return {'kind': 'ab', 'effects': effects}


HOOK = {'kind': 'hook'}

# skill: [(at, editor ID tail, name, what it does, effect)]; two at 100: the choice
PERKS = {
    'Barter': [
        (50, 'MarketDay', 'Market Day', "Island traders know you. On the island everything you buy costs 15% less.", EP('buy', MULT, 0.85, ISL)),
        (75, 'ContractHand', 'Contract Hand', "Your trade contracts pay a quarter more.", HOOK),
        (100, 'TongbaoBaron', 'Tongbao Baron', "The money changer gives you his best rate both ways: ten kala a tongbao.", HOOK),
        (100, 'SmugglersPurse', "Smuggler's Purse", "Patrols never catch you on a smuggling run.", HOOK)],
    'Repair': [
        (50, 'SaltAndRust', 'Salt and Rust', "Island salvage teaches you to make do: you can repair a weapon or armour with similar items, not only the same.",
         EP('jury', SET, 1.0)),
        (75, 'Shipwright', 'Shipwright', "Boats are mended with one part fewer, and the ferry carries you for nothing.", HOOK),
        (100, 'GunnersMate', "Gunner's Mate", "You know the Missouri's guns as her crew did: putting them right needs one part fewer.", HOOK),
        (100, 'TinkersPay', "Tinker's Pay", "Every repair job pays you double.", HOOK)],
    'Medicine': [
        (50, 'NoniCure', 'Noni Cure', "You know the island's own remedies: on the island, everything that heals you heals 15% more.", EP('heal', MULT, 1.15, ISL)),
        (75, 'IslandDoctor', 'Island Doctor', "You can talk the sick through a fever: cures need no medicine.", HOOK),
        (100, 'KahunaLaau', "Kahuna La'au", "Once a day, when your health falls under a quarter, the old healing comes back to you whole.", {'kind': 'script'}),
        (100, 'FieldSurgeon', 'Field Surgeon', "Everything that heals you heals a quarter more.", EP('heal', MULT, 1.25))],
    'Survival': [
        (50, 'Trailwise', 'Trailwise', "You pack like a Ko'olau porter: on the island you carry 25 more.", EP('carry', ADD, 25.0, ISL)),
        (75, 'SeaLegs', 'Sea Legs', "You swim a quarter faster.", AB(('IncreaseSpeedMult', 25, ('swimming',)))),
        (100, 'ChildOfTheIsland', 'Child of the Island', "The island keeps you: outdoors there, +15 Damage Resistance and +20 radiation resistance.",
         AB(('IncreaseDamageResistance', 15, ('island',)), ('IncreaseRadiationResistance', 20, ('island',)))),
        (100, 'CastawayHeart', "Castaway's Heart", "Alone and hurt, you mend: outdoors on the island you heal a point a second while under half health.",
         AB(('RestoreHealth', 1, ('island', 'hurt'))))],
    'Science': [
        (50, 'Tinkerer', 'Tinkerer', "One part fewer for generators, maintenance panels and fixing jobs.", HOOK),
        (75, 'SignalMan', 'Signal Man', "You decode the Huang's numbers by ear: no need for the Radar Dome.", HOOK),
        (100, 'VaultTecMind', 'Vault-Tec Mind', "Terminals open to you as to their makers: +15 Science when hacking.", EP('hackbonus', ADD, 15.0)),
        (100, 'SalvageKing', 'Salvage King', "Robots you bring down always leave a Sensor Module.", HOOK)],
    'Speech': [
        (50, 'TalkStory', 'Talk Story', "People tell you one more thing: an extra rumour wherever rumours are heard.", HOOK),
        (75, 'WordOnTheWater', 'Word on the Water', "What you do travels: each side's opinion of you moves half again as much.", HOOK),
        (100, 'SilverTongue', 'Silver Tongue', "The hardest talk is a little easier: the island's 95 checks ask 85 of you.", HOOK),
        (100, 'KahunasVoice', "Kahuna's Voice", "You speak as the court does: its people's Speech checks are 15 easier.", HOOK)],
    'Lockpick': [
        (50, 'QuietHands', 'Quiet Hands', "Picking a lock in sight of a side's people costs you nothing with them.", HOOK),
        (75, 'CageBreaker', 'Cage Breaker', "The tribute cages open to you without a check.", HOOK),
        (100, 'MasterKey', 'Master Key', "Running doesn't give you away while you work at locks and in the dark.", HOOK),
        (100, 'StrongroomGhost', 'Strongroom Ghost', "The court's strongrooms never raise the alarm on you.", HOOK)],
    'Explosives': [
        (50, 'FishermansCharge', "Fisherman's Charge", "A charge thrown into the sea brings up fish.", HOOK),
        (75, 'Sapper', 'Sapper', "Clearing a blocked way with a charge never hurts you.", HOOK),
        (100, 'BigBang', 'Big Bang', "Your explosives hit a quarter harder.", EP('damage', MULT, 1.25, skill='Explosives')),
        (100, 'DemolitionPay', 'Demolition Pay', "Blasting jobs pay you double.", HOOK)],
    'Sneak': [
        (50, 'NightWalker', 'Night Walker', "On the island at night you are 15 better at sneaking.", AB(('IncreaseSkillSneak', 15, ('island', 'night')))),
        (75, 'ShadowTrader', 'Shadow Trader', "Smuggling runs are never stopped.", HOOK),
        (100, 'GhostOfWaikiki', 'Ghost of Waikiki', "The court's guards never hail you.", HOOK),
        (100, 'TideWalker', 'Tide Walker', "In the water you are 25 better at sneaking.", AB(('IncreaseSkillSneak', 25, ('swimming',))))],
    'Guns': [
        (50, 'PiratesEye', "Pirate's Eye", "The island's own guns (the Chinese and Japanese rifles and pistols) do 10% more damage in your hands.",
         EP('damage', MULT, 1.1, weapon='guns')),
        (75, 'SteadyDeck', 'Steady Deck', "On the island you hit 10% more often in V.A.T.S. with any gun.", EP('tohit', MULT, 1.1, ISL, skill='Guns')),
        (100, 'ReefSharpshooter', 'Sharpshooter of the Reef', "The island's own guns score critical hits 10% more often.", EP('crit', ADD, 10.0, weapon='guns')),
        (100, 'GunsmithsFriend', "Gunsmith's Friend", "Every gun you fire does 5% more damage, the island's 15%.", EP('damage', MULT, 1.05, skill='Guns'))],
    'EnergyWeapons': [
        (50, 'Sunpower', 'Sunpower', "On the island by day, energy weapons do 10% more damage.", EP('damage', MULT, 1.1, ('island', 'day'), skill='EnergyWeapons')),
        (75, 'VaultCharge', 'Vault Charge', "Any generator charges your drained cells one and a half for one.", HOOK),
        (100, 'Overcharge', 'Overcharge', "Energy weapons do 15% more damage.", EP('damage', MULT, 1.15, skill='EnergyWeapons')),
        (100, 'CellMerchant', 'Cell Merchant', "Pirate traders take your cells at five kala, not four.", HOOK)],
    'MeleeWeapons': [
        (50, 'KoaHand', 'Koa Hand', "The island's clubs and blades do 10% more damage in your hands.", EP('damage', MULT, 1.1, weapon='melee')),
        (75, 'LuaStance', 'Lua Stance', "Melee attacks cost 20% fewer Action Points.", EP('apcost', MULT, 0.8, skill='MeleeWeapons')),
        (100, 'KahunasChampion', "Kahuna's Champion", "+5 melee damage with any weapon.", AB(('IncreaseMeleeDamage', 5, ()))),
        (100, 'LeiomanoMaster', 'Leiomano Master', "The island's clubs and blades score critical hits 15% more often.", EP('crit', ADD, 15.0, weapon='melee'))],
    'Unarmed': [
        (50, 'LuaFist', 'Lua Fist', "+3 unarmed damage.", AB(('IncreaseUnarmedDamage', 3, ()))),
        (75, 'Riptide', 'Riptide', "On the island your unarmed blows knock people down more often.", EP('knockdown', ADD, 0.15, ISL, skill='Unarmed')),
        (100, 'BigKahuna', 'Big Kahuna', "+6 unarmed damage and +5 Damage Resistance.", AB(('IncreaseUnarmedDamage', 6, ()), ('IncreaseDamageResistance', 5, ()))),
        (100, 'BoneBreaker', 'Bone Breaker', "Your unarmed blows do half again as much damage to limbs.", EP('limb', MULT, 1.5, skill='Unarmed'))],
}
ICON_FROM = {'Barter': 'Negotiator', 'Repair': 'JuryRigging', 'Medicine': 'Medic', 'Survival': 'Survivalist', 'Science': 'Hacker',
             'Speech': 'TerrifyingPresence', 'Lockpick': 'Infiltrator', 'Explosives': 'DemolitionExpert', 'Sneak': 'SilentRunning',
             'Guns': 'Commando', 'EnergyWeapons': 'LaserCommander', 'MeleeWeapons': 'Slayer', 'Unarmed': 'ParalyzingPalm'}


def perk_edid(tail):
    return 'FOLabPerk' + tail


def _mod_key(pr, edid, tag=None):
    return next((k for k, r in pr.records.items() if (tag is None or r.get('type') == tag) and r.get('subs') and recordio.field(r, 'EDID') == edid), None)


def _game(gd, tag, edid):
    return next((f for f, (_i, r) in gd.forms.items() if r.tag == tag and gd.edid(f) == edid), None)


def _cond(fn, op, value, p1=0, p2=0, run=0, orr=False):
    return {'or': orr, 'use_target': False, 'op': op, 'fn': fn, 'p1': p1, 'p2': p2, 'run': run, 'ref': '', 'value': float(value)}


def _named(name, world):
    """A condition by name (on whoever it's asked of: the perk's owner, or the ability's bearer)."""
    if name == 'island':
        return [_cond(GETINWORLDSPACE, '=', 1, world)]
    if name == 'swimming':
        return [_cond(ISSWIMMING, '=', 1)]
    if name == 'night':
        return [_cond(GETCURRENTTIME, '>=', 20, orr=True), _cond(GETCURRENTTIME, '<', 5)]
    if name == 'day':
        return [_cond(GETCURRENTTIME, '>=', 6), _cond(GETCURRENTTIME, '<', 19)]
    if name == 'hurt':
        return [_cond(GETHEALTHPCT, '<', 0.5)]
    raise ValueError(name)


def _raw(tag, data):
    return {'tag': tag, 'label': tag, 'kind': 'raw', 'value': data.hex()}


def entry_subs(gd, eff, world, lists):
    """A perk's entry-point entry as the game lays one out."""
    import questrec as qr
    point, tabs = EPS[eff['point']]
    subs = [{'tag': 'PRKE', 'label': 'Entry', 'kind': 'struct', 'fields': [{'name': 'Type', 'code': 'B', 'value': 2},
                                                                           {'name': 'Rank', 'code': 'B', 'value': 0}, {'name': 'Priority', 'code': 'B', 'value': 0}]},
            _raw('DATA', bytes((point, eff['func'], tabs)))]
    owner = [c for n in eff['owner'] for c in _named(n, world)]
    weapon = []
    if eff['weapon']:
        weapon.append(_cond(ISINLIST, '=', 1, lists[eff['weapon']]))
    if eff['skill']:
        weapon.append(_cond(ISWEAPONSKILLTYPE, '=', 1, AV[eff['skill']]))
    for tab, conds in ((0, owner), (1, weapon)):
        if conds:
            subs.append({'tag': 'PRKC', 'label': 'Condition runs on', 'kind': 'struct', 'fields': [{'name': 'Who', 'code': 'b', 'value': tab}]})
            subs += [qr.condition_sub(c) for c in conds]
    subs += [{'tag': 'EPFT', 'label': 'Entry value type', 'kind': 'struct', 'fields': [{'name': 'Type', 'code': 'B', 'value': 1}]},
             _raw('EPFD', struct.pack('<f', eff['value'])),
             {'tag': 'PRKF', 'label': 'Marker', 'kind': 'struct', 'fields': []}]
    return subs


def ability_record(gd, edid, name, eff, world):
    """A SPEL ability of the mod's own: each effect a game MGEF at a magnitude, with its own conditions (RexBloodLegion's layout)."""
    import questrec as qr
    rec = json.loads(json.dumps(recordio.load(gd, _game(gd, 'SPEL', 'RexBloodLegion'))))
    rec['src'] = ''
    efid = next(s for s in rec['subs'] if s['tag'] == 'EFID')
    efit = next(s for s in rec['subs'] if s['tag'] == 'EFIT')
    head = [s for s in rec['subs'] if s['tag'] not in ('EFID', 'EFIT', 'CTDA')]
    for s in head:
        if s['tag'] == 'EDID':
            s['value'] = edid
        elif s['tag'] == 'FULL':
            s['value'] = name
    subs = head
    for mgef, mag, conds in eff['effects']:
        f = _game(gd, 'MGEF', mgef)
        if f is None:
            raise ValueError('the game has no effect %s' % mgef)
        e1 = dict(json.loads(json.dumps(efid)), value=gd.key(f))
        e2 = json.loads(json.dumps(efit))
        for q in e2['fields']:
            if q.get('name') == 'Magnitude':
                q['value'] = mag
        subs += [e1, e2] + [qr.condition_sub(c) for n in conds for c in _named(n, world)]
    rec['subs'] = subs
    return rec


def perk_record(gd, skill, tail, name, words, entries, icon):
    subs = [{'tag': 'EDID', 'label': 'Editor ID', 'kind': 'z', 'value': perk_edid(tail)},
            {'tag': 'FULL', 'label': 'Name', 'kind': 'z', 'value': name},
            {'tag': 'DESC', 'label': 'Description', 'kind': 'z', 'value': words}]
    if icon:
        subs.append({'tag': 'ICON', 'label': 'Icon', 'kind': 'z', 'value': icon})
    subs.append({'tag': 'DATA', 'label': 'Data', 'kind': 'struct', 'fields': [
        {'name': 'Trait', 'code': 'B', 'value': 0}, {'name': 'Level', 'code': 'B', 'value': 1},
        {'name': 'Ranks', 'code': 'B', 'value': 1}, {'name': 'Playable', 'code': 'B', 'value': 0},
        {'name': 'Hidden', 'code': 'B', 'value': 0}]})
    return {'type': 'PERK', 'flags': 0, 'src': '', 'subs': subs + entries}


def _icons(gd):
    """{skill: a game perk's Pip-Boy picture}: ICON_FROM's, else the first of the game's perks that asks that skill."""
    import tes4
    out, by_av = {}, {}
    for f, (n, r) in sorted(gd.forms.items()):
        if r.tag != 'PERK' or n != 0:
            continue
        subs = list(tes4.iter_subrecords(gd.plugins[n].data(r)))
        icon = next((v.rstrip(b'\0').decode('cp1252') for t, v in subs if t == 'ICON'), '')
        for t, v in subs:
            if t == 'CTDA' and struct.unpack_from('<H', v, 8)[0] == GETPERMAV and icon:
                by_av.setdefault(struct.unpack_from('<I', v, 12)[0], icon)
    for s, e in ICON_FROM.items():
        f = _game(gd, 'PERK', e)
        out[s] = (recordio.field(recordio.load(gd, f), 'ICON') if f else '') or by_av.get(AV[s], '')
    return out


def quest_source():
    """One milestone a look: the first skill found past one it hasn't had, its perk and message; at 100 the choice."""
    L = ['scn %s' % SCRIPT, 'short choosing', 'short button', 'short laau', 'float laauday']
    names = list(PERKS)
    for s in names:
        L += ['short %s50' % s.lower()[:8], 'short %s75' % s.lower()[:8], 'short %s100' % s.lower()[:8]]
    L += ['', 'Begin GameMode',
          '\tif choosing']
    L += ['\t\tset button to GetButtonPressed', '\t\tif button == -1', '\t\t\treturn', '\t\tendif']
    for i, s in enumerate(names):
        a, b = [p for p in PERKS[s] if p[0] == 100]
        L += ['\t\tif choosing == %d' % (i + 1), '\t\t\tif button == 0', '\t\t\t\tplayer.AddPerk %s' % perk_edid(a[1]),
              '\t\t\telse', '\t\t\t\tplayer.AddPerk %s' % perk_edid(b[1]), '\t\t\tendif', '\t\tendif']
    L += ['\t\tset choosing to 0', '\t\treturn', '\tendif']
    # Kahuna La'au: once a game day, a full heal when health falls under a quarter
    L += ['\tif player.HasPerk %s' % perk_edid('KahunaLaau'), '\t\tif player.GetHealthPercentage < 0.25 && GameDaysPassed >= laauday',
          '\t\t\tset laauday to GameDaysPassed + 1', '\t\t\tplayer.RestoreActorValue Health 1000', '\t\t\tShowMessage FOLabMilestoneLaauMsg',
          '\t\t\treturn', '\t\tendif', '\tendif']
    for i, s in enumerate(names):
        v = s.lower()[:8]
        for at, tail, _n, _w, _e in PERKS[s]:
            if at == 100:
                continue
            L += ['\tif %s%d == 0 && player.GetPermanentActorValue %s >= %d' % (v, at, s, at), '\t\tset %s%d to 1' % (v, at),
                  '\t\tplayer.AddPerk %s' % perk_edid(tail), '\t\tShowMessage FOLabMilestone%s%dMsg' % (s, at), '\t\treturn', '\tendif']
        L += ['\tif %s100 == 0 && player.GetPermanentActorValue %s >= 100' % (v, s), '\t\tset %s100 to 1' % v,
              '\t\tShowMessage FOLabMilestone%s100Msg' % s, '\t\tset choosing to %d' % (i + 1), '\t\treturn', '\tendif']
    L += ['End', '']
    return '\n'.join(L)


def plan(gd, pr):
    rep = {'rows': [], 'skipped': []}
    if _mod_key(pr, QUEST, 'QUST'):
        rep['skipped'].append(('all', 'the mod already has %s (Undo first)' % QUEST))
        return rep
    kinds = {}
    for k, r in pr.records.items():
        if r.get('type') == 'WEAP' and r.get('subs') and (recordio.field(r, 'EDID') or '').startswith('FOLab'):
            et = next((s['fields'][0]['value'] for s in r['subs'] if s['tag'] == 'ETYP' and s.get('fields')), None)
            kinds[recordio.field(r, 'EDID')] = et
    guns = sorted(e for e, et in kinds.items() if et in GUN_TYPES)          # (by the weapon's own equip type)
    melee = sorted(e for e, et in kinds.items() if et in MELEE_TYPES)
    rep['rows'].append({'what': 'lists', 'guns': guns, 'melee': melee})
    for s, ps in PERKS.items():
        for at, tail, name, _w, eff in ps:
            rep['rows'].append({'what': 'perk', 'skill': s, 'at': at, 'edid': perk_edid(tail), 'name': name, 'kind': eff['kind']})
    return rep


def ops(gd, pr, P=None):
    import api_scripts
    import generators
    import questrec as qr
    from activity import _new_key
    P = P or plan(gd, pr)
    if any(w == 'all' for w, _x in P['skipped']):
        raise ValueError(P['skipped'][0][1])
    out, extra, rep = [], {}, {'made': [], 'skipped': list(P['skipped']), 'kinds': {}}

    def record(edid, rec, key=None):
        k = key or _new_key(pr)
        extra[k] = rec
        out.append({'op': 'record', 'key': k, 'record': rec})
        rep['made'].append(edid)
        return k
    world = _mod_key(pr, ISLAND, 'WRLD') or next((gd.key(f) for f, (_i, r) in gd.forms.items() if r.tag == 'WRLD' and gd.edid(f) == ISLAND), None)
    if not world:
        raise ValueError('no %s world' % ISLAND)
    weapons = {recordio.field(r, 'EDID'): k for k, r in pr.records.items() if r.get('type') == 'WEAP' and r.get('subs')}
    lrow = next(r for r in P['rows'] if r['what'] == 'lists')
    lists = {}
    for key, (edid, _w) in LISTS.items():
        items = lrow[key]
        rec = {'type': 'FLST', 'flags': 0, 'src': '', 'subs': [{'tag': 'EDID', 'label': 'Editor ID', 'kind': 'z', 'value': edid}] +
               [{'tag': 'LNAM', 'label': 'Form', 'kind': 'F', 'value': weapons[e]} for e in items]}
        lists[key] = record(edid, rec)
        rep['lists'] = rep.get('lists', {})
        rep['lists'][edid] = len(items)
    icons = _icons(gd)
    perk_keys = {}
    for s, ps in PERKS.items():
        for at, tail, name, words, eff in ps:
            entries = []
            if eff['kind'] == 'ep':
                entries = entry_subs(gd, eff, world, lists)
            elif eff['kind'] == 'ab':
                sk = record(perk_edid(tail) + 'Ability', ability_record(gd, perk_edid(tail) + 'Ability', name, eff, world))
                entries = [{'tag': 'PRKE', 'label': 'Entry', 'kind': 'struct', 'fields': [
                    {'name': 'Type', 'code': 'B', 'value': 1}, {'name': 'Rank', 'code': 'B', 'value': 0}, {'name': 'Priority', 'code': 'B', 'value': 0}]},
                    {'tag': 'DATA', 'label': 'Data', 'kind': 'F', 'value': sk},
                    {'tag': 'PRKF', 'label': 'Marker', 'kind': 'struct', 'fields': []}]
            perk_keys[tail] = record(perk_edid(tail), perk_record(gd, s, tail, name, words, entries, icons.get(s)))
            rep['kinds'][eff['kind']] = rep['kinds'].get(eff['kind'], 0) + 1
    # the messages
    for s, ps in PERKS.items():
        shown = SHOWN.get(s, s)
        for at, tail, name, words, _e in ps:
            if at < 100:
                record('FOLabMilestone%s%dMsg' % (s, at), generators._message('FOLabMilestone%s%dMsg' % (s, at),
                       ('%s %d. New perk: %s. %s' % (shown, at, name, words)).replace('%', ' per cent')))     # (a message's % is a value to fill)
        a, b = [p for p in ps if p[0] == 100]
        record('FOLabMilestone%s100Msg' % s, generators._message('FOLabMilestone%s100Msg' % s,
               ('%s 100. Choose a perk.\n\n%s: %s\n\n%s: %s' % (shown, a[2], a[3], b[2], b[3])).replace('%', ' per cent'), (a[2], b[2])))
    record('FOLabMilestoneLaauMsg', generators._message('FOLabMilestoneLaauMsg', "Kahuna La'au: the old healing comes back to you."))
    # the quest
    qk, qsk = _new_key(pr), _new_key(pr)
    quest = qr.quest_record({'edid': QUEST, 'script': qsk, 'name': '', 'flags': {'start_enabled': True}, 'priority': 30,
                             'delay': 1.0, 'stages': [], 'objectives': []})
    sc = api_scripts.scripts()
    c = sc.compile(quest_source(), qsk, 'quest', dict(extra, **{qk: quest}))
    if not hasattr(c, 'subrecords'):
        raise ValueError('the milestone quest\'s script: %s' % (c,))
    record(SCRIPT, sc._record_of(c, SCRIPT), qsk)
    record(QUEST, quest, qk)
    rep['perks'] = len(perk_keys)
    rep['hooks'] = sorted(perk_edid(t) for s, ps in PERKS.items() for _a, t, _n, _w, e in ps if e['kind'] == 'hook')
    rep['keys'] = {'quest': qk}
    return out, rep


def apply(pr, gd, P=None):
    o, rep = ops(gd, pr, P)
    pr.apply(LABEL, o)
    return rep
