"""Hints to the Ridge Bunker (the Workshop, 26 Nov 2026: the second cave's door is high on a ridge face, 16.7 km from the nearest
marker, "nobody will find it without a pointer"; "one or two hints that lead there, in the Up the valleys manner").

Two hints, keeping to the bunker's own duty log (armybunker.TERMINAL: 22-27 Oct 2077, "Road crew did not come up again"):
- **The H-3 Checkpoint's terminal** (loreterminals' FOLabLoreH3): an entry, "Supply run, 10-21-2077", the checkpoint's truck
  taking stores to the Ridge Storage Site, south-east of the post, the door high in the rock face. Its item script shows the
  bunker's map marker.
- **A delivery chit** in a supply crate lower on the ridge (`CHIT`): what was signed for, the road crew due back on the 22nd to
  finish the steps. Taking it shows its words and the bunker's marker (quest FOLabBunkerLead's script).

The bunker's marker (armybunker's, "Ridge Bunker") has no editor ID: this step gives its ref one (`MARKER_EDID`, made persistent)
so the scripts can name it. Run after the bunker step (it refuses without the marker).

    plan(gd, pr)       {'rows', 'skipped', 'spots'}
    apply(pr, gd, P)   one Undo; nothing voiced
"""
import json
import math

import recordio

LABEL = 'Hints to the Ridge Bunker'
QUEST, QSCRIPT = 'FOLabBunkerLead', 'FOLabBunkerLeadScript'
MARKER_NAME, MARKER_EDID = 'Ridge Bunker', 'FOLabRidgeBunkerMarkerREF'
TERMINAL_SITE = 'h3_checkpoint'
CHIT = ('FOLabBunkerChit', 'Delivery Chit', 'FOLabBunkerSupplyCrate', 'Army Supply Crate')
CRATE_ITEMS = [('WaterPurified', 2), ('Ammo556mm', 20)]
CHIT_FROM = (1200.0, 2500.0, 4000.0)   # (the crate this far from the bunker's door, lower down)
CHIT_LOWER, CHIT_LOWEST = 600.0, 1500.0   # (this far below the door: about where the door's path starts, a climb of ~920)
DIRS = ['north', 'north-east', 'east', 'south-east', 'south', 'south-west', 'west', 'north-west']

ENTRY = ('Supply run, 10-21-2077', """
  Truck up the ridge road with stores for the Ridge Storage Site: rations, water,
  batteries. End of the road, then on foot. The site's door is in the rock face,
  high up, south-east of this post. Road crew still cutting the last steps.""")
CHIT_WORDS = ("Delivery chit, U.S. Army, 10-21-2077. Ridge Storage Site: ration crates x20, water drums x6, batteries x12, signed for "
              "at the door. Road crew back on the 22nd to finish the steps up the face. The site is {dist} {dir} of here, up the ridge.")


def _dir(frm, to):
    a = math.degrees(math.atan2(to[0] - frm[0], to[1] - frm[1])) % 360
    return DIRS[int((a + 22.5) // 45) % 8]


def _marker_ref(pr):
    for ck, c in pr.cells.items():
        if ck.startswith('+'):
            continue
        for rk, r in (c.get('refs') or {}).items():
            m = r.get('marker')
            if isinstance(m, dict) and m.get('name') == MARKER_NAME and not r.get('removed') and r.get('p'):
                return ck, rk, r
    return None, None, None


def plan(gd, pr):
    import activity
    import loreterminals as LT
    from upvalleys import _Clear
    rows, skipped, S = [], [], {}
    if any(r.get('type') == 'QUST' and recordio.field(r, 'EDID') == QUEST for r in pr.records.values()):
        skipped.append('the mod has %s already' % QUEST)
    ck, rk, mr = _marker_ref(pr)
    if not mr:
        skipped.append('no "%s" map marker: run this after the bunker step' % MARKER_NAME)
    if not LT._term_key(pr, LT.terminals_edid(TERMINAL_SITE)):
        skipped.append('no lore terminal %s' % LT.terminals_edid(TERMINAL_SITE))
    if skipped:
        return {'rows': rows, 'skipped': skipped, 'spots': S}
    S['marker'] = {'cell': ck, 'ref': rk, 'p': [round(v, 1) for v in mr['p'][:3]], 'edid': mr.get('edid')}
    ctx = activity.Ctx(gd, pr)
    cl = _Clear(gd, pr, ctx)
    door = mr['p']
    best = None
    for r in CHIT_FROM:
        for t in range(16):
            a = t * 2 * math.pi / 16
            x, y = door[0] + r * math.sin(a), door[1] + r * math.cos(a)
            for s in ctx.around(x, y, 4, radii=(0, 200, 400), turns=8):
                below = door[2] - s[2]
                if not (CHIT_LOWER <= below <= CHIT_LOWEST) or not cl.ok(s[0], s[1]):
                    continue
                score = -math.hypot(s[0] - door[0], s[1] - door[1])     # (the nearest such: where the bunker's own path starts up)
                if best is None or score > best[0]:
                    best = (score, s)
    if not best:
        skipped.append('no clear ground below the bunker for the crate')
        return {'rows': rows, 'skipped': skipped, 'spots': S}
    s = best[1]
    S['crate'] = {'world': (round(s[0], 1), round(s[1], 1), round(s[2], 1)), 'near': cl.dist(s[0], s[1]),
                  'from door': round(math.hypot(s[0] - door[0], s[1] - door[1])), 'below door': round(door[2] - s[2])}
    d = S['crate']['from door']
    S['chit'] = CHIT_WORDS.format(dist='a short climb' if d < 2500 else 'a long climb', dir=_dir(s[:2], door[:2]))
    rows.append({'marker': S['marker']['p'], 'crate': S['crate']})
    return {'rows': rows, 'skipped': skipped, 'spots': S}


def apply(pr, gd, P=None):
    import activity
    import api_quests as aq
    import api_scripts
    import api_characters as ac
    import factionfolk as ff
    import loreterminals as LT
    import newgame
    import pinkpearl as PP
    import questrec as qr
    import struct
    import surffish
    import terminals
    import tes4
    import upvalleys as UV
    from activity import _new_key
    P = P or plan(gd, pr)
    if P['skipped']:
        raise ValueError('; '.join(P['skipped']))
    S = P['spots']
    out, rep = [], {'made': []}
    ctx = activity.Ctx(gd, pr)
    grid = ctx.grid

    def record(rec, k=None):
        k = k or _new_key(pr)
        out.append({'op': 'record', 'key': k, 'record': rec})
        rep['made'].append(recordio.field(rec, 'EDID'))
        return k
    # the marker named
    m = S['marker']
    medid = m['edid'] or MARKER_EDID
    if not m['edid']:
        out.append({'op': 'ref_set', 'cell': m['cell'], 'ref': m['ref'], 'set': {'edid': MARKER_EDID, 'persistent': True}})
        rep['made'].append(MARKER_EDID)
    # the chit, in a crate of its own
    misc_like = UV._game_key(gd, UV.MISC_LIKE, 'MISC')[1]
    chit = surffish._copy(gd, 'MISC', misc_like, CHIT[0], CHIT[1])
    chit['subs'] = [s for s in chit['subs'] if s['tag'] != 'SCRI']
    chit_key = record(chit)
    msg = CHIT[0] + 'Msg'
    record(newgame._message_record(msg, S['chit']))
    base = UV._game_key(gd, UV.CHEST_LIKE, 'CONT')[0]
    rec = recordio.load(gd, gd.from_key(base))
    rec['src'] = ''
    recordio.set_field(rec, 'EDID', CHIT[2], label='Editor ID')
    if any(s['tag'] == 'FULL' for s in rec['subs']):
        recordio.set_field(rec, 'FULL', CHIT[3])
    else:
        ac.insert(rec, {'tag': 'FULL', 'label': 'Name', 'kind': 'z', 'value': CHIT[3]})
    rec['subs'] = [s for s in rec['subs'] if s['tag'] not in ('CNTO', 'COED', 'SCRI')]
    for k, n in [(chit_key, 1)] + [(UV._game_item(gd, e), n) for e, n in CRATE_ITEMS]:
        if not k:
            continue
        s = ff._sub('CONT', 'CNTO', struct.pack('<Ii', 0, n))
        ff._set_link(s, k)
        ac.insert(rec, s)
    crate_key = record(rec)
    x, y, z = S['crate']['world']
    out.append({'op': 'place', 'cell': gd.key(grid[(int(math.floor(x / 4096.0)), int(math.floor(y / 4096.0)))]), 'key': _new_key(pr),
                'ref': {'base': crate_key, 'p': [x, y, z, 0.0, 0.0, 0.0], 's': 1.0, 'persistent': True, 'edid': CHIT[2] + 'REF'}})
    rep['made'].append(CHIT[2] + 'REF')
    # the quest: shown when either hint is read, done at the door
    qkey, skey = _new_key(pr), _new_key(pr)
    src = '\n'.join(['scn %s' % QSCRIPT, 'short told', 'short chit', 'short shown', 'short there', '', 'Begin GameMode',
                     '\tif chit == 0', '\t\tif player.GetItemCount %s >= 1' % CHIT[0], '\t\t\tset chit to 1', '\t\t\tset told to 1',
                     '\t\t\tShowMessage %s' % msg, '\t\t\tShowMap %s' % medid, '\t\tendif', '\tendif',
                     '\tif told == 1', '\t\tif shown == 0', '\t\t\tset shown to 1', '\t\t\tSetObjectiveDisplayed %s 10 1' % QUEST, '\t\tendif', '\tendif',
                     '\tif there == 0', '\t\tif player.GetDistance %s < 1200' % medid, '\t\t\tset there to 1',
                     '\t\t\tSetObjectiveDisplayed %s 10 1' % QUEST, '\t\t\tSetObjectiveCompleted %s 10 1' % QUEST, '\t\t\tSetStage %s 100' % QUEST,
                     '\t\tendif', '\tendif', 'End', ''])
    stub = lambda e: {'type': 'REFR', 'flags': tes4.PERSISTENT, 'subs': [{'tag': 'EDID', 'label': 'Editor ID', 'kind': 'z', 'value': e}]}
    ext = {m['ref']: stub(medid)}
    plain = {'edid': QUEST, 'name': 'The Ridge Storage Site', 'script': skey, 'flags': {'start_enabled': True}, 'priority': 50, 'delay': 1.0,
             'stages': [UV._stage(100, "I found the Army's Ridge Storage Site, high in the rock face.", 'CompleteQuest %s\n' % QUEST)],
             'objectives': [{'index': 10, 'text': "Find the Army's Ridge Storage Site", 'targets': [{'target': m['ref'], 'flags': 0, 'conditions': []}]}],
             'conditions': []}
    qstub = qr.quest_record(dict(plain, stages=[], objectives=[]))
    known = dict(ext)
    known[qkey] = qstub
    known.update({o['key']: o['record'] for o in out if o['op'] == 'record'})
    sc = api_scripts.scripts()
    was = sc.forms.is_map_marker
    sc.forms.is_map_marker = lambda f, was=was: (getattr(f, 'rec', None) is not None and recordio.field(f.rec, 'EDID') == medid) or was(f)
    try:
        c = sc.compile(src, skey, 'quest', known)
    finally:
        sc.forms.is_map_marker = was
    if not hasattr(c, 'subrecords'):
        raise ValueError('%s: %s' % (QSCRIPT, c))
    out.append({'op': 'record', 'key': skey, 'record': sc._record_of(c, QSCRIPT)})
    out.append({'op': 'record', 'key': qkey, 'record': qstub})
    rep['made'] += [QSCRIPT, QUEST]
    forms = PP._forms(gd, pr, ext, {o['key']: o['record'] for o in out if o['op'] == 'record'})
    full = json.loads(json.dumps(plain))
    errors = aq.compile_quest(full, forms)
    if errors:
        raise ValueError('%s: %s' % (QUEST, errors))
    # the checkpoint's terminal: the entry before its own crate item
    for e, kr in terminals.mod_forms(gd, pr).own.items():
        forms.own.setdefault(e, kr)
    forms.own[medid.lower()] = (m['ref'], stub(medid))
    was2 = forms.is_map_marker
    forms.is_map_marker = lambda f, was=was2: (f.rec is not None and recordio.field(f.rec, 'EDID') == medid) or was(f)
    tk = LT._term_key(pr, LT.terminals_edid(TERMINAL_SITE))
    have = pr.records[tk]
    Sx = LT.SITES[TERMINAL_SITE]
    cache_ref = (Sx['cache'][0] + 'REF') if Sx['cache'] else ''
    spec = terminals.plan(LT.text_of(TERMINAL_SITE).replace('{cache}', cache_ref).replace('{HEAD}', LT.HEAD))
    if json.dumps(terminals.records(gd, forms, spec, {})['terminal']['subs'], sort_keys=True) != json.dumps(have['subs'], sort_keys=True):
        raise ValueError('%s is not as loreterminals makes it' % LT.terminals_edid(TERMINAL_SITE))
    at = next((n for n, it in enumerate(spec['items']) if it['unlocks']), len(spec['items']))
    spec['items'].insert(at, {'text': ENTRY[0], 'says': '\n'.join(x.strip() for x in ENTRY[1].strip('\n').split('\n')), 'unlocks': [], 'note': '',
                              'script': 'set %s.told to 1\nShowMap %s' % (QUEST, medid)})
    new = terminals.records(gd, forms, spec, {})['terminal']
    pr.apply(LABEL, out)
    pr.apply(LABEL, [{'op': 'record', 'key': qkey, 'record': qr.quest_record(full)},
                     {'op': 'record', 'key': tk, 'record': dict(have, subs=new['subs'])}], merge=True)
    rep['made'].append(LT.terminals_edid(TERMINAL_SITE) + ' (entry)')
    rep.update({'marker': m['p'], 'crate': S['crate'], 'chit': S['chit']})
    return rep
