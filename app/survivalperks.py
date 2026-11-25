"""More Survival perks (docs/waikiki-speech-science.md K3, K5; the user, 25 Nov 2026: "More perks to survival ... let's go with
all of those"). Six perks taken at level-up as the game's are (playable, a Survival requirement and a level), beside
perks.py's Storm-Wise and Reef Diver:

| Perk | Needs | What it does | How |
|---|---|---|---|
| Reef Fisher | Survival 40, level 6 | two fish a catch at FOLab's fishing spots | the spots' script (surffish) made again, asking HasPerk |
| Wrack Reader | Survival 50, level 8 | the storm's wrack: told the moment it's on the sand, and its finds hold more | quest FOLabSurvivalPerks: a message when stormafter's parent switches on; a Survival roll on each find opened |
| Wild Medicine | Survival 55, level 10 | healing poultices at any campfire from Broc Flower, Xander Root and water | a recipe (Honest Hearts' poultice's layout) with HasPerk |
| Shark Sense | Survival 60, level 10 | in the water, +3 Perception (what swims shows on the compass sooner) | an ability, while swimming |
| Koʻolau Legs | Survival 70, level 12 | outdoors on the island, 10% faster | an ability, in the island's world |
| Sun and Salt | Survival 85, level 14 | outdoors on the island, out of a fight, a point of health back a second | an ability, in the island's world and not in combat |

The Survival milestone perks (Trailwise, Sea Legs, Child of the Island, Castaway's Heart) are milestones.py's.

    plan(gd, pr)       {'rows', 'skipped'}
    apply(pr, gd, P)   one Undo
"""
import json

import recordio

LABEL = 'More Survival perks'
QUEST, SCRIPT = 'FOLabSurvivalPerks', 'FOLabSurvivalPerksScript'
SURVIVAL, GETPERMAV = 44, 495
ISINCOMBAT = 289
PERKS = {   # key: (editor ID, name, Survival, level, what it says, effect)
    'fisher': ('FOLabPerkReefFisher', 'Reef Fisher', 40, 6, "You know where the reef fish feed. Each catch at a fishing spot brings in two.", 'hook'),
    'wrack': ('FOLabPerkWrackReader', 'Wrack Reader', 50, 8,
              "You read the sea's leavings. You know the moment a storm has thrown its wrack up on the sand, and you find more in it.", 'hook'),
    'medicine': ('FOLabPerkWildMedicine', 'Wild Medicine', 55, 10,
                 "You can make healing poultices at any campfire from Broc Flower, Xander Root and clean water.", 'recipe'),
    'shark': ('FOLabPerkSharkSense', 'Shark Sense', 60, 10, "In the water your senses sharpen: +3 Perception.",
              (('IncreasePerception', 3, ('swimming',)),)),
    'legs': ('FOLabPerkKoolauLegs', "Ko'olau Legs", 70, 12, "Ridge paths made you quick: outdoors on the island you move 10% faster.",
             (('IncreaseSpeedMult', 10, ('island',)),)),
    'sun': ('FOLabPerkSunAndSalt', 'Sun and Salt', 85, 14,
            "The island mends you: outdoors there, out of a fight, you get a point of health back every second.",
            (('RestoreHealth', 1, ('island', 'calm')),)),
}
ICON_FROM = 'Survivalist'
FISH_SCRIPT, FISH = 'FOLabFishingSpotScript', 'FOLabRawReefFish'
WRACK_PARENT, WRACK_FIND = 'FOLabStormWrack', 'FOLabWrack'     # (stormafter's finds: CONT 'FOLabWrack' + the game's container)
RECIPE_FROM, RECIPE = 'NVDLC02RecipeHealingPoultice', ('FOLabRecipeWildPoultice', 'Healing Poultice (island herbs)')
RECIPE_IN = [('BrocFlower', 1), ('XanderRoot', 1), ('WaterPurified', 1)]
RECIPE_OUT = ('NVDLC02HealingPoultice', 1)
WRACK_WORDS = "Wrack Reader: the storm has thrown its wrack up on the sand. The beaches will be worth walking."
WRACK_DAYS = 3
WRACK_EXTRA = [('Stimpak', 1), ('SpareParts', 2), ('Caps001', 15)]     # (one of these from a find opened, at Survival odds)


def _mod_key(pr, edid, tag=None):
    return next((k for k, r in pr.records.items() if (tag is None or r.get('type') == tag) and r.get('subs') and recordio.field(r, 'EDID') == edid), None)


def _game(gd, tag, edid):
    return next((f for f, (_i, r) in gd.forms.items() if r.tag == tag and gd.edid(f) == edid), None)


def plan(gd, pr):
    rep = {'rows': [], 'skipped': []}
    if _mod_key(pr, PERKS['fisher'][0], 'PERK'):
        rep['skipped'].append(('all', 'already in the mod (Undo first)'))
        return rep
    rep['rows'].append({'what': 'fishing', 'script': bool(_mod_key(pr, FISH_SCRIPT, 'SCPT'))})
    parent = any(r.get('edid') == WRACK_PARENT for c in pr.cells.values() for r in (c.get('refs') or {}).values())
    finds = sorted(recordio.field(r, 'EDID') for r in pr.records.values() if r.get('type') == 'CONT' and r.get('subs')
                   and (recordio.field(r, 'EDID') or '').startswith(WRACK_FIND))
    rep['rows'].append({'what': 'wrack', 'parent': parent, 'finds': finds})
    rep['rows'].append({'what': 'recipe', 'from': bool(_game(gd, 'RCPE', RECIPE_FROM))})
    for k, (e, n, s, lv, _w, eff) in PERKS.items():
        rep['rows'].append({'what': 'perk', 'edid': e, 'name': n, 'survival': s, 'level': lv,
                            'how': eff if isinstance(eff, str) else 'ability'})
    for what, ok in (('fishing spots', rep['rows'][0]['script']), ('the storm\'s wrack', parent)):
        if not ok:
            rep['skipped'].append((what, 'not in the mod: its perk waits'))
    return rep


def ops(gd, pr, P=None):
    import api_characters as ac
    import api_scripts
    import milestones as M
    import milestonehooks as H
    import questrec as qr
    from activity import _new_key
    P = P or plan(gd, pr)
    if any(w == 'all' for w, _x in P['skipped']):
        raise ValueError(P['skipped'][0][1])
    R = {r['what']: r for r in P['rows'] if r['what'] != 'perk'}
    out, extra, rep = [], {}, {'made': [], 'skipped': list(P['skipped'])}

    def record(edid, rec, key=None):
        k = key or _new_key(pr)
        extra[k] = rec
        out.append({'op': 'record', 'key': k, 'record': rec})
        rep['made'].append(edid)
        return k
    world = _mod_key(pr, M.ISLAND, 'WRLD') or next((gd.key(f) for f, (_i, r) in gd.forms.items() if r.tag == 'WRLD' and gd.edid(f) == M.ISLAND), None)
    f = _game(gd, 'PERK', ICON_FROM)
    icon = recordio.field(recordio.load(gd, f), 'ICON') if f else ''
    keys = {}
    for k, (edid, name, need, level, words, eff) in PERKS.items():
        entries = []
        if not isinstance(eff, str):
            spec = {'effects': list(eff)}
            sk = record(edid + 'Ability', _ability(gd, edid + 'Ability', name, spec, world))
            entries = [{'tag': 'PRKE', 'label': 'Entry', 'kind': 'struct', 'fields': [
                {'name': 'Type', 'code': 'B', 'value': 1}, {'name': 'Rank', 'code': 'B', 'value': 0}, {'name': 'Priority', 'code': 'B', 'value': 0}]},
                {'tag': 'DATA', 'label': 'Data', 'kind': 'F', 'value': sk},
                {'tag': 'PRKF', 'label': 'Marker', 'kind': 'struct', 'fields': []}]
        rec = M.perk_record(gd, 'Survival', edid[len('FOLabPerk'):], name, words, entries, icon)
        # (taken at level-up: playable, its level, the Survival it asks)
        for s in rec['subs']:
            if s['tag'] == 'DATA' and s.get('kind') == 'struct':
                for q in s['fields']:
                    if q['name'] == 'Playable':
                        q['value'] = 1
                    elif q['name'] == 'Level':
                        q['value'] = level
                break
        at = next(i for i, s in enumerate(rec['subs']) if s['tag'] == 'DATA')
        rec['subs'].insert(at, qr.condition_sub(M._cond(GETPERMAV, '>=', need, SURVIVAL)))
        keys[k] = record(edid, rec)
    sc = api_scripts.scripts()
    refs = {}
    for c in pr.cells.values():
        for rk, r in (c.get('refs') or {}).items():
            if r.get('edid'):
                refs[r['edid'].lower()] = rk
    # Reef Fisher: the fishing spots' script made again
    fk = _mod_key(pr, FISH_SCRIPT, 'SCPT')
    if fk:
        src = H._patched(H._source(pr.records[fk]), [(r'^(\t+)player\.AddItem %s 1$' % FISH,
                                                      r'\1player.AddItem %s 1\n\1if player.HasPerk %s\n\1\tplayer.AddItem %s 1\n\1endif' % (FISH, PERKS['fisher'][0], FISH))])
        c = sc.compile(src, fk, 'object', extra)
        if not hasattr(c, 'subrecords'):
            raise ValueError('the fishing script again: %s' % (c,))
        record(FISH_SCRIPT, sc._record_of(c, FISH_SCRIPT), fk)
    # Wild Medicine: the recipe
    rf = _game(gd, 'RCPE', RECIPE_FROM)
    if rf:
        rec = json.loads(json.dumps(recordio.load(gd, rf)))
        rec['src'] = ''
        subs = []
        for s in rec['subs']:
            if s['tag'] in ('RCIL', 'RCQY', 'RCOD', 'CTDA'):
                continue
            if s['tag'] == 'EDID':
                s['value'] = RECIPE[0]
            elif s['tag'] == 'FULL':
                s['value'] = RECIPE[1]
            elif s['tag'] == 'DATA':
                for q in s['fields']:
                    if q.get('name') == 'Level':
                        q['value'] = PERKS['medicine'][2]
                subs.append(qr.condition_sub(M._cond(449, '=', 1, keys['medicine'], 0, 1)))       # (HasPerk on the player)
            subs.append(s)
        for e, n in RECIPE_IN:
            subs += [{'tag': 'RCIL', 'label': 'Ingredient', 'kind': 'F', 'value': gd.key(_game(gd, 'ALCH', e))},
                     {'tag': 'RCQY', 'label': 'Quantity', 'kind': 'struct', 'fields': [{'name': 'Count', 'code': 'i', 'value': n}]}]
        subs += [{'tag': 'RCOD', 'label': 'Output', 'kind': 'F', 'value': gd.key(_game(gd, 'ALCH', RECIPE_OUT[0]))},
                 {'tag': 'RCQY', 'label': 'Quantity', 'kind': 'struct', 'fields': [{'name': 'Count', 'code': 'i', 'value': RECIPE_OUT[1]}]}]
        rec['subs'] = subs
        record(RECIPE[0], rec)
    else:
        rep['skipped'].append(('recipe', 'the game has no %s' % RECIPE_FROM))
    # Wrack Reader: the storm's wrack told when it comes, and more in its finds
    import generators
    msg = record('FOLabWrackReaderMsg', generators._message('FOLabWrackReaderMsg', WRACK_WORDS))
    del msg
    qk, qsk = _new_key(pr), _new_key(pr)
    quest = qr.quest_record({'edid': QUEST, 'script': qsk, 'name': '', 'flags': {'start_enabled': True}, 'priority': 20,
                             'delay': 5.0, 'stages': [], 'objectives': []})
    L = ['scn %s' % SCRIPT, 'short told', '', 'Begin GameMode']
    if R['wrack']['parent']:
        L += ['\tif %s.GetDisabled == 0' % WRACK_PARENT, '\t\tif told == 0 && player.HasPerk %s' % PERKS['wrack'][0], '\t\t\tset told to 1',
              '\t\t\tShowMessage FOLabWrackReaderMsg', '\t\tendif', '\telse', '\t\tset told to 0', '\tendif']
    L += ['End', '']
    named = dict(extra, **{qk: quest})
    if R['wrack']['parent']:
        named[refs[WRACK_PARENT.lower()]] = {'type': 'REFR', 'flags': 0x400, 'subs': [{'tag': 'EDID', 'label': 'Editor ID', 'kind': 'z', 'value': WRACK_PARENT}]}
    c = sc.compile('\n'.join(L), qsk, 'quest', named)
    if not hasattr(c, 'subrecords'):
        raise ValueError('the survival perks\' script: %s' % (c,))
    record(SCRIPT, sc._record_of(c, SCRIPT), qsk)
    record(QUEST, quest, qk)
    # the wrack's finds: a script on each find's container (OnOpen): with the perk, a Survival roll for one thing more
    finds = [k for k, r in pr.records.items() if r.get('type') == 'CONT' and r.get('subs') and recordio.field(r, 'EDID') in R['wrack']['finds']]
    if finds:
        wk = _new_key(pr)
        # (once a find per WRACK_DAYS: its contents refill after a storm; a Survival-sized chance of one thing more)
        L = ['scn FOLabWrackFindScript', 'float lastday', 'short roll', '', 'Begin OnOpen',
             '\tif IsActionRef player && player.HasPerk %s && GameDaysPassed >= lastday' % PERKS['wrack'][0],
             '\t\tset lastday to GameDaysPassed + %d' % WRACK_DAYS, '\t\tif GetRandomPercent < player.GetActorValue Survival',
             '\t\t\tset roll to GetRandomPercent']
        for n, (item, k) in enumerate(WRACK_EXTRA):
            lo, hi = 100 * n // len(WRACK_EXTRA), 100 * (n + 1) // len(WRACK_EXTRA)
            L += ['\t\t\tif roll >= %d && roll < %d' % (lo, hi), '\t\t\t\tAddItem %s %d' % (item, k), '\t\t\tendif']
        L += ['\t\tendif', '\tendif', 'End', '']
        c = sc.compile('\n'.join(L), wk, 'object', extra)
        if not hasattr(c, 'subrecords'):
            raise ValueError('the wrack find script: %s' % (c,))
        record('FOLabWrackFindScript', sc._record_of(c, 'FOLabWrackFindScript'), wk)
        for k in finds:
            rec = json.loads(json.dumps(pr.records[k]))
            if any(s['tag'] == 'SCRI' for s in rec['subs']):
                rep['skipped'].append((recordio.field(rec, 'EDID'), 'has a script of its own: left'))
                continue
            ac.insert(rec, {'tag': 'SCRI', 'label': 'Script', 'kind': 'F', 'value': wk})
            out.append({'op': 'record', 'key': k, 'record': rec})
        rep['wrack finds'] = len(finds)
    rep['perks'] = {k: v[0] for k, v in PERKS.items()}
    return out, rep


def _ability(gd, edid, name, spec, world):
    import milestones as M
    import questrec as qr
    eff = {'effects': [(mg, mag, tuple(c for c in conds if c != 'calm')) for mg, mag, conds in spec['effects']]}
    rec = M.ability_record(gd, edid, name, eff, world)
    if any('calm' in conds for _m, _g, conds in spec['effects']):
        rec['subs'].append(qr.condition_sub(M._cond(ISINCOMBAT, '=', 0)))        # (out of a fight: on the last effect, Sun and Salt's one)
    return rec


def apply(pr, gd, P=None):
    o, rep = ops(gd, pr, P)
    pr.apply(LABEL, o)
    return rep

