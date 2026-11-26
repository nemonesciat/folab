"""Lockpick's and Explosives' uses (docs/waikiki-speech-science.md K2, K5; the user, 25 Nov 2026: "the uses for every skill
... let's go with all of those"). In the quest FOLabWorkLocks.

**Lockpick**
- **The court's strongroom** (the Royal Hawaiian's court floors): its floor safe Hard (Lockpick 70: the game's 75), its
  locker cabinets Average (55: the game's 50); all the court's (owned). The safe holds the court's purse (`PURSE`). Opening
  any of them rings the court's alarm once (court -5, court infamy) unless you have Strongroom Ghost.
- **The Huáng's storehouses** (`STORES` of the bamboo storehouses, nearest the Huáng's towns first): a store chest on each
  one's floor, Easy (40: the game's 25), the Huáng's. Quiet Hands: opening one makes it yours to take from (SetOwnership),
  so no one cries thief.
- The tribute cages (heldwatch's, already in) and safes by tier (lootplace's, already in).

**Explosives**
- **Rubble over caches** (`CACHES`): heaps of rubble under the ruined freeway, each over a cache. "[Explosives 55] Set a
  charge" with Dynamite, C-4 or a frag grenade: the heap is blown away (it hurts if you're close, not with Sapper) and the
  cache is there. The Court Watchman pays a bounty for each heap cleared (Demolition Pay: double): the court wants its
  roads open.
- **Fisherman's Charge:** at a fishing spot, crouched, with the perk and a stick of dynamite: four fish.
- The Missouri's flooded magazines are K1's (the quests session); the Flotilla's boats wait for their own (not separate
  things in the mod).

    plan(gd, pr)       {'rows', 'skipped'}
    apply(pr, gd, P)   one Undo (VOICE)
"""
import json
import math

import recordio

LABEL = "Lockpick's and Explosives' uses"
QUEST, SCRIPT = 'FOLabWorkLocks', 'FOLabWorkLocksScript'
VOICE = [QUEST]
GETAV, GETITEMCOUNT, GETQUESTVAR = 14, 47, 79
EXPLOSIVES = 35
COURT_FLOORS = 'FOLabRoyalHawaiianFloor'
SAFE, LOCKER = 'GenericSafeFloor01', 'LockerCabinet02'
SAFE_LOCK, LOCKER_LOCK, STORE_LOCK = 75, 50, 25
PURSE = [('Caps001', 150), ('Stimpak', 2)]
STORE_FROM, STORE_ITEMS = 'Footlocker01HouseholdNV', [('NVFreshMaize', 4), ('FOLabTongbao', 6), ('WaterPurified', 2)]
STORES = 4
STORE_PIECE = 'FOLabBambooStorehouse'
TOWNS = ('Kailua', "Kane'ohe", "Makapu'u Gate")
HEAP, CACHE_FROM = 'FOLabRubbleHeapLowA', 'LootAmmoBoxGenericNV'
CACHE_ITEMS = [('WeapNVDynamite', 2), ('Caps001', 40), ('Stimpak', 1)]
CACHES, CACHE_NEAR, CACHE_APART = 4, ('OverpassSectionLo01', 'FOLabRubbleHeapA', 'FOLabRubbleHeapB'), 4000.0   # (by the fallen freeway first, then the big heaps)
CHARGES = ('WeapNVDynamite', 'WeapNVC4PlasticExplosive', 'WeapGrenadeFrag')
BLAST = 'GrenadeFragExplosion'
BOUNTY = 20
FISH_SCRIPT = 'FOLabFishingSpotScript'
WORDS = {
    'alarm': "A bell rings somewhere in the court. Someone will know the strongroom was opened.",
    'rubble': "Rubble chokes the way here. Something's under it.",
    'charge': "Set a charge", 'leave': 'Leave',
    'blown': "The charge brings the rubble down and away. There's something underneath.",
    'nocharge': "You need dynamite, C-4 or a grenade to set a charge.",
    'noskill': "You'd bring the whole lot down on yourself. (Explosives 55)",
    'bounty': "About the rubble I've cleared.",
    'bounty_yes': "The court thanks you. Roads open again. Here, for each one.",
    'bounty_none': "Clear some rubble first, then we'll talk.",
    'fishblast': "The charge thumps under the water. Fish float up.",
}


def _cond(fn, op, value, p1=0, p2=0, run=0):
    return {'or': False, 'use_target': False, 'op': op, 'fn': fn, 'p1': p1, 'p2': p2, 'run': run, 'ref': '', 'value': float(value)}


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
    import money
    rep = {'rows': [], 'skipped': []}
    if _mod_key(pr, QUEST, 'QUST'):
        rep['skipped'].append(('all', 'the mod already has %s (Undo first)' % QUEST))
        return rep
    # the court's strongroom
    names = {ck: (recordio.field(pr.records[ck], 'EDID') if (pr.records.get(ck) or {}).get('subs') else '') for ck in pr.cells}
    for ck, c in pr.cells.items():
        if not names.get(ck, '').startswith(COURT_FLOORS):
            continue
        for rk, r in (c.get('refs') or {}).items():
            e = money._edid_of(gd, pr, r.get('base') or '')
            if e in (SAFE, LOCKER) and not r.get('removed'):
                rep['rows'].append({'what': 'strongroom', 'cell': ck, 'ref': rk, 'kind': 'safe' if e == SAFE else 'locker', 'floor': names[ck]})
    safe_floors = {r['floor'] for r in rep['rows'] if r['what'] == 'strongroom' and r['kind'] == 'safe'}
    rep['rows'] = [r for r in rep['rows'] if r['what'] != 'strongroom' or r['floor'] in safe_floors]     # (the strongroom: the safe's floor only)
    if not any(r['what'] == 'strongroom' for r in rep['rows']):
        rep['skipped'].append(('strongroom', 'no safe on the court floors'))
    # the Huáng's storehouses, nearest their towns first: a chest on each one's floor
    import activity
    import factionfolk as ff
    import lootplace
    ctx = activity.Ctx(gd, pr)
    mk = ff._markers(pr)
    towns = [mk[t][1] for t in TOWNS if t in mk]
    stores = sorted(ctx.of(STORE_PIECE), key=lambda p: min((math.hypot(p[0] - t[0], p[1] - t[1]) for t in towns), default=0))
    S = lootplace.Seat(gd, pr, ctx.world)
    box = [-22, -14, 0, 22, 14, 26]
    for p in stores:
        if sum(1 for r in rep['rows'] if r['what'] == 'store') >= STORES:
            break
        got = S.at(p[0], p[1], p[5] if len(p) > 5 else 0.0, box, p[2] + 260, outside=True)
        if got and got[2] > p[2] + 40:                 # (on the storehouse's raised floor, not the ground under it)
            rep['rows'].append({'what': 'store', 'cell': ctx.cell(got[0], got[1]), 'p': list(got), 'over_ground': round(got[2] - p[2])})
    if not any(r['what'] == 'store' for r in rep['rows']):
        rep['skipped'].append(('storehouses', 'no storehouse floor to stand a chest on'))
    # rubble over caches: by the ruined freeway, on open land, clear of roads and doors
    spans = ctx.of(*CACHE_NEAR)
    hbox = [-110, -160, 0, 110, 160, 115]
    for sp in spans:
        if sum(1 for r in rep['rows'] if r['what'] == 'cache') >= CACHES:
            break
        if any(math.hypot(sp[0] - r['p'][0], sp[1] - r['p'][1]) < CACHE_APART for r in rep['rows'] if r['what'] == 'cache'):
            continue
        for d in (500, 800, 1100):
            for a in range(8):
                dx, dy = d * math.cos(a * math.pi / 4), d * math.sin(a * math.pi / 4)
                got = S.at(sp[0] + dx, sp[1] + dy, 0.0, hbox, sp[2] + 50, outside=True)
                if got and abs(got[2] - sp[2]) < 900:
                    rep['rows'].append({'what': 'cache', 'cell': ctx.cell(got[0], got[1]), 'p': list(got)})
                    break
            else:
                continue
            break
        continue
        for dx, dy in ((0, 600), (0, -600), (600, 0), (-600, 0)):
            got = S.at(sp[0] + dx, sp[1] + dy, 0.0, hbox, sp[2] + 50, outside=True)
            if got and abs(got[2] - sp[2]) < 900:
                rep['rows'].append({'what': 'cache', 'cell': ctx.cell(got[0], got[1]), 'p': list(got)})
                break
    if not any(r['what'] == 'cache' for r in rep['rows']):
        rep['skipped'].append(('caches', 'no open ground by the ruined freeway'))
    rep['rows'].append({'what': 'watchman', 'who': _mod_key(pr, 'FOLabKPWatchman', 'NPC_')})
    rep['rows'].append({'what': 'fishing', 'script': bool(_mod_key(pr, FISH_SCRIPT, 'SCPT'))})
    rep['skipped'] += [('magazines', "the Missouri's are K1's (the quests session)"), ('flotilla boats', 'not separate things in the mod: wait')]
    return rep


def _cont(gd, pr, from_edid, edid, name, items, script):
    import api_characters as ac
    import factionfolk as ff
    import struct
    rec = json.loads(json.dumps(recordio.load(gd, _game(gd, from_edid, ('CONT',)))))
    rec['src'] = ''
    rec['subs'] = [s for s in rec['subs'] if s['tag'] not in ('SCRI', 'MODT')]
    recordio.set_field(rec, 'EDID', edid, label='Editor ID')
    if name:
        recordio.set_field(rec, 'FULL', name)
    for it, n in items:
        s = ff._sub('CONT', 'CNTO', struct.pack('<Ii', 0, n))
        ff._set_link(s, _item(gd, pr, it))
        ac.insert(rec, s)
    if script:
        ac.insert(rec, {'tag': 'SCRI', 'label': 'Script', 'kind': 'F', 'value': script})
    return rec


def ops(gd, pr, P=None):
    import api_scripts
    import factionfolk as ff
    import generators
    import milestonehooks as H
    import questrec as qr
    import repstanding as RS
    from activity import _new_key
    P = P or plan(gd, pr)
    if any(w == 'all' for w, _x in P['skipped']):
        raise ValueError(P['skipped'][0][1])
    rows = P['rows']
    out, extra, rep = [], {}, {'made': [], 'skipped': list(P['skipped']), 'placed': {}}

    def record(edid, rec, key=None):
        k = key or _new_key(pr)
        extra[k] = rec
        out.append({'op': 'record', 'key': k, 'record': rec})
        rep['made'].append(edid)
        return k
    sc = api_scripts.scripts()

    def script(name, src, kind='object', more=None):
        k = _new_key(pr)
        c = sc.compile(src, k, kind, dict(extra, **(more or {})))
        if not hasattr(c, 'subrecords'):
            raise ValueError('%s: %s' % (name, c))
        return record(name, sc._record_of(c, name), k)
    # the quest
    qk, qsk = _new_key(pr), _new_key(pr)
    quest = qr.quest_record({'edid': QUEST, 'script': qsk, 'name': '', 'flags': {'start_enabled': True}, 'priority': 40,
                             'delay': 60.0, 'stages': [], 'objectives': []})
    c = sc.compile('\n'.join(['scn %s' % SCRIPT, 'short cleared', 'short owed', 'short k', '', 'Begin GameMode', 'End', '']), qsk, 'quest', {qk: quest})
    if not hasattr(c, 'subrecords'):
        raise ValueError('the locks quest script: %s' % (c,))
    srec = sc._record_of(c, SCRIPT)
    record(SCRIPT, srec, qsk)
    record(QUEST, quest, qk)
    extra[qk] = quest
    vi, last = {}, None
    for sub in srec['subs']:
        if sub['tag'] == 'SLSD':
            last = next(f['value'] for f in sub['fields'] if f.get('name') == 'Index')
        elif sub['tag'] == 'SCVR' and last is not None:
            vi[sub['value'].lower()] = last
    court = ff._mod_key(pr, 'FOLabKahunaCourtFaction', 'FACT')
    huang = ff._mod_key(pr, 'FOLabHuangFaction', 'FACT')
    ghost = _mod_key(pr, 'FOLabPerkStrongroomGhost', 'PERK')
    quiet = _mod_key(pr, 'FOLabPerkQuietHands', 'PERK')
    sapper = _mod_key(pr, 'FOLabPerkSapper', 'PERK')
    demo = _mod_key(pr, 'FOLabPerkDemolitionPay', 'PERK')
    fishp = _mod_key(pr, 'FOLabPerkFishermansCharge', 'PERK')
    # the court's strongroom
    strong = [r for r in rows if r['what'] == 'strongroom']
    if strong:
        record('FOLabStrongroomAlarmMsg', generators._message('FOLabStrongroomAlarmMsg', WORDS['alarm']))
        L = ['scn FOLabStrongroomScript', 'short rung', '', 'Begin OnOpen', '\tif IsActionRef player && rung == 0']
        L += ['\t\tif player.HasPerk FOLabPerkStrongroomGhost == 0' if ghost else '\t\tif 1',
              '\t\t\tset rung to 1', '\t\t\tShowMessage FOLabStrongroomAlarmMsg', '\t\t\t' + RS.bump('court', -5),
              '\t\t\tAddReputation FOLabRepCourt 0 1', '\t\tendif', '\tendif', 'End', '']
        sk = script('FOLabStrongroomScript', '\n'.join(L))
        safe = record('FOLabCourtStrongroomSafe', _cont(gd, pr, SAFE, 'FOLabCourtStrongroomSafe', "The Court's Safe", PURSE, sk))
        locker = record('FOLabCourtStrongroomLocker', _cont(gd, pr, LOCKER, 'FOLabCourtStrongroomLocker', '', [], sk))
        for r in strong:
            base, level = (safe, SAFE_LOCK) if r['kind'] == 'safe' else (locker, LOCKER_LOCK)
            out.append({'op': 'swap', 'cell': r['cell'], 'ref': r['ref'], 'base': base})
            props = json.loads(json.dumps(pr.cells[r['cell']]['refs'][r['ref']].get('props') or {}))
            props['lock'] = {'level': level, 'key': '', 'leveled': False}
            if court:
                props['owner'] = court
            out.append({'op': 'props', 'cell': r['cell'], 'ref': r['ref'], 'props': props})
        rep['placed']['strongroom'] = [(r['floor'], r['kind']) for r in strong]
    # the Huáng's storehouses
    stores = [r for r in rows if r['what'] == 'store']
    if stores:
        L = ['scn FOLabHuangStoreScript', '', 'Begin OnOpen', '\tif IsActionRef player']
        L += ['\t\tif player.HasPerk FOLabPerkQuietHands' if quiet else '\t\tif 0', '\t\t\tSetOwnership', '\t\tendif', '\tendif', 'End', '']
        sk = script('FOLabHuangStoreScript', '\n'.join(L))
        chest = record('FOLabHuangStoreChest', _cont(gd, pr, STORE_FROM, 'FOLabHuangStoreChest', 'Storehouse Chest', STORE_ITEMS, sk))
        for r in stores:
            rk = _new_key(pr)
            props = {'lock': {'level': STORE_LOCK, 'key': '', 'leveled': False}}
            if huang:
                props['owner'] = huang
            out.append({'op': 'place', 'cell': r['cell'], 'key': rk, 'ref': {'base': chest, 'p': r['p'], 's': 1.0, 'props': props}})
        rep['placed']['storehouses'] = [{'p': [round(v) for v in r['p'][:3]], 'over_ground': r['over_ground']} for r in stores]
    # rubble over caches
    caches = [r for r in rows if r['what'] == 'cache']
    if caches:
        record('FOLabRubbleMsg', generators._message('FOLabRubbleMsg', WORDS['rubble'], (WORDS['charge'], WORDS['leave'])))
        for k in ('blown', 'nocharge', 'noskill'):
            record('FOLabRubble%sMsg' % k.capitalize(), generators._message('FOLabRubble%sMsg' % k.capitalize(), WORDS[k]))
        charges = [c for c in CHARGES if _item(gd, pr, c)]
        L = ['scn FOLabRubbleCacheScript', 'short menu', 'short button', '', 'Begin OnActivate', '\tif IsActionRef player',
             '\t\tShowMessage FOLabRubbleMsg', '\t\tset menu to 1', '\tendif', 'End', '', 'Begin GameMode', '\tif menu == 0', '\t\treturn', '\tendif',
             '\tset button to GetButtonPressed', '\tif button == -1', '\t\treturn', '\tendif', '\tset menu to 0', '\tif button == 0',
             '\t\tif player.GetActorValue Explosives < 55', '\t\t\tShowMessage FOLabRubbleNoskillMsg', '\t\t\treturn', '\t\tendif']
        for n, ch in enumerate(charges):
            L += ['\t\t%sif player.GetItemCount %s > 0' % ('' if n == 0 else 'else', ch), '\t\t\tplayer.RemoveItem %s 1 1' % ch]
        L += ['\t\telse', '\t\t\tShowMessage FOLabRubbleNochargeMsg', '\t\t\treturn', '\t\tendif']
        L += ['\t\tif player.HasPerk FOLabPerkSapper == 0' if sapper else '\t\tif 1', '\t\t\tPlaceAtMe %s 1' % BLAST, '\t\tendif',
              '\t\tShowMessage FOLabRubbleBlownMsg', '\t\tset %s.cleared to %s.cleared + 1' % (QUEST, QUEST), '\t\tset %s.owed to %s.owed + 1' % (QUEST, QUEST), '\t\tDisable', '\tendif', 'End', '']
        sk = script('FOLabRubbleCacheScript', '\n'.join(L))
        hrec = pr.records.get(_mod_key(pr, HEAP, 'STAT')) or {'subs': []}
        model = recordio.field(hrec, 'MODL') or 'folab\\rubble\\heap_low_a.nif'
        ob = next((s for s in hrec['subs'] if s['tag'] == 'OBND'), None)
        acti = {'type': 'ACTI', 'flags': 0, 'src': '', 'subs': [
            {'tag': 'EDID', 'label': 'Editor ID', 'kind': 'z', 'value': 'FOLabRubbleCache'}] + ([json.loads(json.dumps(ob))] if ob else []) + [
            {'tag': 'FULL', 'label': 'Name', 'kind': 'z', 'value': 'Rubble'},
            {'tag': 'MODL', 'label': 'Model', 'kind': 'z', 'value': model},
            {'tag': 'SCRI', 'label': 'Script', 'kind': 'F', 'value': sk}]}
        heap = record('FOLabRubbleCache', acti)
        box = record('FOLabRubbleCacheBox', _cont(gd, pr, CACHE_FROM, 'FOLabRubbleCacheBox', 'Buried Cache',
                                                  [(i, n) for i, n in CACHE_ITEMS if _item(gd, pr, i)], None))
        rep['placed']['caches'] = []
        for r in caches:
            hk, bk = _new_key(pr), _new_key(pr)
            x, y, z = r['p'][:3]
            out.append({'op': 'place', 'cell': r['cell'], 'key': hk, 'ref': {'base': heap, 'p': [x, y, z, 0.0, 0.0, r['p'][5] if len(r['p']) > 5 else 0.0],
                                                                         's': 1.0, 'persistent': True}})
            out.append({'op': 'place', 'cell': r['cell'], 'key': bk, 'ref': {'base': box, 'p': [x, y, z + 2, 0.0, 0.0, 0.0], 's': 1.0,
                                                                         'props': {'parent': {'ref': hk, 'opposite': True, 'popin': False}}}})
            rep['placed']['caches'].append([round(v) for v in (x, y, z)])
    # Fisherman's Charge: the fishing spots' script with a crouched charge
    fk = _mod_key(pr, FISH_SCRIPT, 'SCPT')
    if fk and fishp:
        record('FOLabFishBlastMsg', generators._message('FOLabFishBlastMsg', WORDS['fishblast']))
        src = H._patched(H._source(pr.records[fk]), [(r'^Begin OnActivate$', 'Begin OnActivate\n\tif IsActionRef player == 1 && player.IsSneaking && '
                                                      'player.HasPerk FOLabPerkFishermansCharge && player.GetItemCount WeapNVDynamite > 0\n'
                                                      '\t\tplayer.RemoveItem WeapNVDynamite 1 1\n\t\tplayer.AddItem FOLabRawReefFish 4\n'
                                                      '\t\tShowMessage FOLabFishBlastMsg\n\t\treturn\n\tendif')])
        c = sc.compile(src, fk, 'object', extra)
        if not hasattr(c, 'subrecords'):
            raise ValueError('the fishing script again: %s' % (c,))
        record(FISH_SCRIPT, sc._record_of(c, FISH_SCRIPT), fk)
    # the court's bounty for cleared rubble
    lines = []
    wm = next((r['who'] for r in rows if r['what'] == 'watchman'), None)
    if wm and caches:
        t = record('FOLabWorkLocksBounty', qr.topic_record({'edid': 'FOLabWorkLocksBounty', 'name': WORDS['bounty'], 'priority': 50.0, 'kind': 0,
                                                           'flags': {'top_level': True}, 'quests': [{'quest': qk, 'links': []}]}))
        more = _cond(GETQUESTVAR, '>', 0, qk, vi['owed'])
        pay = ['set %s.k to %s.owed * %d' % (QUEST, QUEST, BOUNTY)]
        if demo:
            pay += ['if player.HasPerk FOLabPerkDemolitionPay', 'set %s.k to %s.k * 2' % (QUEST, QUEST), 'endif']
        pay += ['player.AddItem Caps001 %s.k' % QUEST, 'set %s.owed to 0' % QUEST, RS.bump('court', 2)]
        lines.append((t, wm, WORDS['bounty_yes'], [more], '\n'.join(pay)))
        lines.append((t, wm, WORDS['bounty_none'], [], ''))
    rep['lines'] = len(lines)
    rep['keys'] = {'quest': qk}
    return out, rep, lines, vi


def apply(pr, gd, P=None):
    import api_quests as aq
    o, rep, lines, vi = ops(gd, pr, P)
    pr.apply(LABEL, o)
    qk = rep['keys']['quest']
    recs = []
    for t, who, words, conds, end in lines:
        l = aq.new_line_plain(gd, pr, t, qk, who, words, conditions=conds)
        if end:
            l['end'] = {'source': end, 'parts': None}
        recs.append({'op': 'record_new', 'record': aq._compiled_line(gd, pr, l)})
    pr.apply(LABEL, recs, merge=True)
    del vi
    return rep
