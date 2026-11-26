"""Medicine's and Survival's uses (docs/waikiki-speech-science.md K2, K5; the user, 25 Nov 2026: "the uses for every skill ...
let's go with all of those"). In the quest FOLabWorkCare.

**Medicine**
- **A fever at the Holdouts** ("Someone here looks sick."): the Holdouts' trader's people.
  - "[Medicine 55] Let me see to them." With 2 Stimpaks, or none with Island Doctor (Medicine 75): cured. +5 with the
    court, good karma.
  - "[Barter 40] I can get you medicine. For a price." Sell them 3 Stimpaks for 120 kala: bad karma, -2 with the court.
  - Under 55: they can't be helped by you yet.
- **The Flotilla's wounds** ("[Medicine 40] Your crew's wounds need seeing to."): the Quartermaster gives 15 cells for 2
  Stimpaks, every 3 days; +2 with the pirates.
- **The condemned in the cages** ("[Medicine 40] Let me see to you."): each tithe once, a Stimpak; good karma, -1 with the
  court.
- The Bishop Museum's ghoul curator waits for the museum (not in the mod).

**Survival**
- **Over the ridge** ("[Survival 55] I know a way over the ridge they won't watch."): a drifter the catchers want slips away
  by your directions (they go: Disable). Good karma, -3 with the court. Each once.
- **Cooking** (campfire recipes asking Survival): Fish and Maize Stew (Survival 25: a Raw Reef Fish, a Fresh Maize) and
  Luau Plate (Survival 55: Grilled Reef Fish, Banana Yucca, Fresh Maize, Purified Water), foods of the mod's own.
- **The cliff trail's turnings** ("[Survival 70] The cliff trail has turnings you can't see from below."): Liu Wei, who
  knows the Huáng's way up, marks Kaʻau Crater on your map (decided: the settlers' back way up the cliffs to the Vault).

    plan(gd, pr)       {'rows', 'skipped'}
    apply(pr, gd, P)   one Undo (VOICE)
"""
import json

import recordio

LABEL = "Medicine's and Survival's uses"
QUEST, SCRIPT = 'FOLabWorkCare', 'FOLabWorkCareScript'
VOICE = [QUEST]
GETAV, GETITEMCOUNT, GETQUESTVAR, HASPERK, GETISID = 14, 47, 79, 449, 72
MEDICINE, SURVIVAL, BARTER = 37, 44, 32
HOLDOUTS, QM, LIU = 'FOLabPowerTraderTheHoldouts', 'FOLabFlotillaQuartermaster', ('ref', 'FOLabHuangOilGiverREF')
TITHES = ('FOLabTithe01', 'FOLabTithe02')
DRIFTERS = ('FOLabCatchDrifter01', 'FOLabCatchDrifter02', 'FOLabCatchDrifter03', 'FOLabCatchDrifter04')
CRATER_MARKER = 'FOLabMarkerKaauCraterREF'
FOODS = [   # (editor ID, name, like (game food), health, Survival, [ingredients])
    ('FOLabFishMaizeStew', 'Fish and Maize Stew', 'NVCookCookFiendStew', 25, 25, [('FOLabRawReefFish', 1), ('NVFreshMaize', 1)]),
    ('FOLabLuauPlate', 'Luau Plate', 'NVCookCookFiendStew', 45, 55,
     [('FOLabGrilledReefFish', 1), ('NVFreshBananaYuccaFruit', 1), ('NVFreshMaize', 1), ('WaterPurified', 1)]),
]
RECIPE_FROM = 'RecipeCookCooksFiendStew'
WORDS = {
    'sick': "Someone here looks sick.",
    'sick_med': "[Medicine 55] Let me see to them.", 'sick_sell': "[Barter 40] I can get you medicine. For a price.",
    'cured': "[SUCCEEDED] The fever's breaking. You didn't have to do that. We won't forget it.",
    'cured_talk': "[SUCCEEDED] Just by talking us through it... you know your work. Thank you.",
    'nomeds': "You'd need two stimpaks to bring that fever down.",
    'cantcure': "[FAILED] You don't know what you're looking at. Please, just go.",
    'sold': "[SUCCEEDED] A hundred and twenty kala. ...It's what we had. Hand them over.",
    'nosell': "You haven't got them to sell.",
    'sick_done': "They're on the mend now.",
    'sick_hello': "Fever's been through half the place. Nobody here knows what to do.",
    'wounds': "Your crew's wounds need seeing to.",
    'wounds_yes': "[SUCCEEDED] Stitched clean. The captain pays for that. Cells.",
    'wounds_need': "Come back with two stimpaks, then.",
    'wounds_later': "They're patched for now. Come back in a few days.",
    'wounds_no': "[FAILED] You'll kill them. Leave it.",
    'condemned': "Let me see to you.",
    'condemned_yes': "[SUCCEEDED] ...Why? They'll still take me. ...Thank you.",
    'condemned_need': "You've nothing to give.",
    'condemned_no': "[FAILED] You don't know how. Leave me be.",
    'ridge': "I know a way over the ridge they won't watch.",
    'ridge_yes': "[SUCCEEDED] ...Up the gully, keep the wind on my face. I'm gone. I won't forget you.",
    'ridge_no': "[FAILED] That way? They'd have me in an hour.",
    'cliff': "The cliff trail has turnings you can't see from below.",
    'cliff_yes': "[SUCCEEDED] You have good eyes. Yes. Up the crater. I say no more.",
    'cliff_no': "[FAILED] Trail is trail. Go home.",
}


def _cond(fn, op, value, p1=0, p2=0, run=0, glob=None):
    c = {'or': False, 'use_target': False, 'op': op, 'fn': fn, 'p1': p1, 'p2': p2, 'run': run, 'ref': ''}
    if glob:
        c['global'] = glob
    else:
        c['value'] = float(value)
    return c


def _mod_key(pr, edid, tag=None):
    return next((k for k, r in pr.records.items() if (tag is None or r.get('type') == tag) and r.get('subs') and recordio.field(r, 'EDID') == edid), None)


def _game(gd, edid, tags):
    return next((f for f, (_i, r) in gd.forms.items() if r.tag in tags and gd.edid(f) == edid), None)


def _item(gd, pr, edid):
    k = _mod_key(pr, edid)
    if k:
        return k
    f = _game(gd, edid, ('ALCH', 'MISC', 'AMMO', 'WEAP'))
    return gd.key(f) if f else None


def plan(gd, pr):
    import barterwork
    rep = {'rows': [], 'skipped': []}
    if _mod_key(pr, QUEST, 'QUST'):
        rep['skipped'].append(('all', 'the mod already has %s (Undo first)' % QUEST))
        return rep
    for what, e in (('holdouts', HOLDOUTS), ('qm', QM)):
        k = _mod_key(pr, e, 'NPC_')
        if k:
            rep['rows'].append({'what': what, 'who': k})
        else:
            rep['skipped'].append((what, '%s not in the mod' % e))
    for e in TITHES:
        k = _mod_key(pr, e, 'NPC_')
        if k:
            rep['rows'].append({'what': 'tithe', 'who': k, 'edid': e})
    for e in DRIFTERS:
        k = _mod_key(pr, e, 'NPC_')
        if k:
            rep['rows'].append({'what': 'drifter', 'who': k, 'edid': e})
    liu = barterwork._payer(pr, LIU)
    marker = any(r.get('edid') == CRATER_MARKER for c in pr.cells.values() for r in (c.get('refs') or {}).values())
    if liu and marker:
        rep['rows'].append({'what': 'cliff', 'who': liu})
    else:
        rep['skipped'].append(('cliff', 'Liu Wei or the crater marker not in the mod'))
    missing = [e for _f, _n, _l, _h, _s, ins in FOODS for e, _c in ins if not _item(gd, pr, e)]
    if missing or not _game(gd, RECIPE_FROM, ('RCPE',)):
        rep['skipped'].append(('cooking', 'missing %s' % (missing or RECIPE_FROM)))
    else:
        rep['rows'].append({'what': 'cooking'})
    rep['skipped'].append(('curator', 'waits for the Bishop Museum (not in the mod)'))
    return rep


def ops(gd, pr, P=None):
    import api_quests as aq
    import api_scripts
    import questrec as qr
    import repstanding as RS
    import skillcheck
    from activity import _new_key
    P = P or plan(gd, pr)
    if any(w == 'all' for w, _x in P['skipped']):
        raise ValueError(P['skipped'][0][1])
    rows = P['rows']
    out, extra, rep = [], {}, {'made': [], 'skipped': list(P['skipped'])}

    def record(edid, rec, key=None):
        k = key or _new_key(pr)
        extra[k] = rec
        out.append({'op': 'record', 'key': k, 'record': rec})
        rep['made'].append(edid)
        return k
    # the foods and their recipes
    if any(r['what'] == 'cooking' for r in rows):
        rf = recordio.load(gd, _game(gd, RECIPE_FROM, ('RCPE',)))
        food_from = {}
        for edid, name, like, hp, need, ins in FOODS:
            if like not in food_from:
                f = _game(gd, like, ('ALCH',)) or _game(gd, 'NVFreshMaize', ('ALCH',))
                food_from[like] = recordio.load(gd, f)
            rec = json.loads(json.dumps(food_from[like]))
            rec['src'] = ''
            rec['subs'] = [s for s in rec['subs'] if s['tag'] not in ('SCRI', 'MODT')]
            recordio.set_field(rec, 'EDID', edid, label='Editor ID')
            recordio.set_field(rec, 'FULL', name)
            for s in rec['subs']:
                if s['tag'] == 'EFIT':
                    for q in s['fields']:
                        if q.get('name') == 'Magnitude' and q.get('value', 0) and q['value'] > 1:
                            q['value'] = hp
            fk = record(edid, rec)
            r = json.loads(json.dumps(rf))
            r['src'] = ''
            subs = []
            for s in r['subs']:
                if s['tag'] in ('RCIL', 'RCQY', 'RCOD', 'CTDA'):
                    continue
                if s['tag'] == 'EDID':
                    s['value'] = 'FOLabRecipe' + edid[len('FOLab'):]
                elif s['tag'] == 'FULL':
                    s['value'] = name
                elif s['tag'] == 'DATA':
                    for q in s['fields']:
                        if q.get('name') == 'Skill':
                            q['value'] = SURVIVAL
                        elif q.get('name') == 'Level':
                            q['value'] = need
                subs.append(s)
            for e, n in ins:
                subs += [{'tag': 'RCIL', 'label': 'Ingredient', 'kind': 'F', 'value': _item(gd, pr, e)},
                         {'tag': 'RCQY', 'label': 'Quantity', 'kind': 'struct', 'fields': [{'name': 'Count', 'code': 'i', 'value': n}]}]
            subs += [{'tag': 'RCOD', 'label': 'Output', 'kind': 'F', 'value': fk},
                     {'tag': 'RCQY', 'label': 'Quantity', 'kind': 'struct', 'fields': [{'name': 'Count', 'code': 'i', 'value': 1}]}]
            r['subs'] = subs
            record('FOLabRecipe' + edid[len('FOLab'):], r)
    # the quest
    qk, qsk = _new_key(pr), _new_key(pr)
    quest = qr.quest_record({'edid': QUEST, 'script': qsk, 'name': '', 'flags': {'start_enabled': True}, 'priority': 40,
                             'delay': 60.0, 'stages': [], 'objectives': []})
    V = ['fever', 'nextwounds', 'cliff'] + ['t%d' % n for n in range(len(TITHES))]
    src = '\n'.join(['scn %s' % SCRIPT] + ['%s %s' % ('float' if v == 'nextwounds' else 'short', v) for v in V] + ['', 'Begin GameMode', 'End', ''])
    sc = api_scripts.scripts()
    c = sc.compile(src, qsk, 'quest', {qk: quest})
    if not hasattr(c, 'subrecords'):
        raise ValueError('the care script: %s' % (c,))
    srec = sc._record_of(c, SCRIPT)
    record(SCRIPT, srec, qsk)
    record(QUEST, quest, qk)
    vi, last = {}, None
    for sub in srec['subs']:
        if sub['tag'] == 'SLSD':
            last = next(f['value'] for f in sub['fields'] if f.get('name') == 'Index')
        elif sub['tag'] == 'SCVR' and last is not None:
            vi[sub['value'].lower()] = last
    qv = lambda var, op, v: _cond(GETQUESTVAR, op, v, qk, vi[var.lower()])
    days = gd.key(next(f for f, (_i, r) in gd.forms.items() if r.tag == 'GLOB' and gd.edid(f) == 'GameDaysPassed'))
    stim = _item(gd, pr, 'Stimpak')
    doctor = _mod_key(pr, 'FOLabPerkIslandDoctor', 'PERK')
    tk = {}

    def topic(k, words):
        if k not in tk:
            tk[k] = record('FOLabWorkCare%s' % k.capitalize(), qr.topic_record({
                'edid': 'FOLabWorkCare%s' % k.capitalize(), 'name': words, 'priority': 50.0, 'kind': 0, 'flags': {'top_level': True},
                'quests': [{'quest': qk, 'links': []}]}))
        return tk[k]
    lines = []

    def line(t, who, words, conds, end='', skill=None):
        l = aq.new_line_plain(gd, pr, t, qk, who, words, conditions=list(conds))
        if end:
            l['end'] = {'source': end, 'parts': None}
        if skill:
            l['skill'] = skillcheck.skill_key(gd, skill)
        lines.append(l)
    av = lambda n, op, v: _cond(GETAV, op, v, n, 0, 1)
    has = lambda item, n: _cond(GETITEMCOUNT, '>=', n, item, 0, 1)
    R = {}
    for r in rows:
        R.setdefault(r['what'], []).append(r)
    rep['ways'] = {}
    # the fever
    if 'holdouts' in R:
        who = R['holdouts'][0]['who']
        t = topic('sick', WORDS['sick'])
        tm, ts = topic('sickmed', WORDS['sick_med']), topic('sicksell', WORDS['sick_sell'])
        line(t, who, WORDS['sick_done'], [qv('fever', '=', 1)])
        line(t, who, WORDS['sick_hello'], [qv('fever', '=', 0)])
        open_ = qv('fever', '=', 0)
        cure = 'set %s.fever to 1\nRewardKarma 50\n%s\nRewardXP 40' % (QUEST, RS.bump('court', 5))
        if doctor:
            line(tm, who, WORDS['cured_talk'], [open_, av(MEDICINE, '>=', 55), _cond(HASPERK, '=', 1, doctor, 0, 1)], cure, 'Medicine')
        line(tm, who, WORDS['cured'], [open_, av(MEDICINE, '>=', 55), has(stim, 2)], 'player.RemoveItem Stimpak 2\n' + cure, 'Medicine')
        line(tm, who, WORDS['nomeds'], [open_, av(MEDICINE, '>=', 55)])
        line(tm, who, WORDS['cantcure'], [open_, av(MEDICINE, '<', 55)], '', 'Medicine')
        line(ts, who, WORDS['sold'], [open_, av(BARTER, '>=', 40), has(stim, 3)],
             'player.RemoveItem Stimpak 3\nplayer.AddItem Caps001 120\nset %s.fever to 1\nRewardKarma -25\n%s' % (QUEST, RS.bump('court', -2)), 'Barter')
        line(ts, who, WORDS['nosell'], [open_])
        rep['ways']['fever'] = ['cure with Medicine 55 and 2 Stimpaks', 'cure by talk (Island Doctor)', 'sell 3 Stimpaks (Barter 40)', 'leave them']
    if 'qm' in R:
        who = R['qm'][0]['who']
        t = topic('wounds', '[Medicine 40] ' + WORDS['wounds'])
        due = _cond(GETQUESTVAR, '<=', 0, qk, vi['nextwounds'], glob=days)
        line(t, who, WORDS['wounds_yes'], [due, av(MEDICINE, '>=', 40), has(stim, 2)],
             'player.RemoveItem Stimpak 2\nplayer.AddItem AmmoSmallEnergyCell 15\nset %s.nextwounds to GameDaysPassed + 3\n%s' % (QUEST, RS.bump('pirates', 2)), 'Medicine')
        line(t, who, WORDS['wounds_need'], [due, av(MEDICINE, '>=', 40)])
        line(t, who, WORDS['wounds_later'], [av(MEDICINE, '>=', 40)])
        line(t, who, WORDS['wounds_no'], [av(MEDICINE, '<', 40)], '', 'Medicine')
        rep['ways']['flotilla wounds'] = ['2 Stimpaks for 15 cells every 3 days (Medicine 40)', 'or not']
    for n, r in enumerate(R.get('tithe', [])):
        t = topic('condemned', '[Medicine 40] ' + WORDS['condemned'])
        v = 't%d' % n
        line(t, r['who'], WORDS['condemned_yes'], [qv(v, '=', 0), av(MEDICINE, '>=', 40), has(stim, 1)],
             'player.RemoveItem Stimpak 1\nset %s.%s to 1\nRewardKarma 25\n%s' % (QUEST, v, RS.bump('court', -1)), 'Medicine')
        line(t, r['who'], WORDS['condemned_need'], [qv(v, '=', 0), av(MEDICINE, '>=', 40)])
        line(t, r['who'], WORDS['condemned_no'], [qv(v, '=', 0), av(MEDICINE, '<', 40)], '', 'Medicine')
    if R.get('tithe'):
        rep['ways']['the condemned'] = ['a Stimpak each, a mercy (Medicine 40)', 'or not']
    for r in R.get('drifter', []):
        t = topic('ridge', '[Survival 55] ' + WORDS['ridge'])
        line(t, r['who'], WORDS['ridge_yes'], [av(SURVIVAL, '>=', 55)], 'RewardKarma 50\n%s\nDisable' % RS.bump('court', -3), 'Survival')
        line(t, r['who'], WORDS['ridge_no'], [av(SURVIVAL, '<', 55)], '', 'Survival')
    if R.get('drifter'):
        rep['ways']['drifters'] = ['send them over the ridge (Survival 55)', "heldwatch's own ways (take, free, pass off as sick)"]
    if 'cliff' in R:
        who = R['cliff'][0]['who']
        t = topic('cliff', '[Survival 70] ' + WORDS['cliff'])
        line(t, who, WORDS['cliff_yes'], [qv('cliff', '=', 0), av(SURVIVAL, '>=', 70)], 'set %s.cliff to 1\nShowMap %s' % (QUEST, CRATER_MARKER), 'Survival')
        line(t, who, WORDS['cliff_no'], [qv('cliff', '=', 0), av(SURVIVAL, '<', 70)], '', 'Survival')
        rep['ways']['cliff'] = ['Survival 70 marks the crater', "or the rumour at Speech 70"]
    rep['lines'] = len(lines)
    rep['keys'] = {'quest': qk}
    return out, rep, lines


def apply(pr, gd, P=None):
    """The records, then the lines compiled with the crater's marker taken for a map marker (hints.py's way)."""
    import api_quests as aq
    import hints
    import questrec as qr
    o, rep, lines = ops(gd, pr, P)
    pr.apply(LABEL, o)
    marks = {rk: CRATER_MARKER for c in pr.cells.values() for rk, r in (c.get('refs') or {}).items() if r.get('edid') == CRATER_MARKER}
    forms = hints._marker_forms(gd, aq.ModForms(gd, pr), marks)
    recs = []
    for l in lines:
        l.setdefault('begin', None)
        l.setdefault('end', None)
        errors = aq.compile_line(l, forms)
        if errors:
            raise ValueError('a care line: %s' % errors[0])
        recs.append({'op': 'record_new', 'record': qr.info_record(l)})
    pr.apply(LABEL, recs, merge=True)
    return rep
