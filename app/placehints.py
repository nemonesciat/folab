"""Hints to two new places (the cave session, 26 Nov 2026: the Workshop asked for "a hint or two pointing there"), in the
Ridge Bunker hints' manner, decided lore only (docs/waikiki-decisions.md, "Makapu'u Sea Cave", "The Pali Tunnels").

**Makapu'u Sea Cave** (seacave.py: a door at the foot of the windward sea cliffs north of Makapu'u point, reached only by
wading or swimming; a flooded gallery, two sharklurks, a cache up a ramp whose owners are not said):
- the Waimanalo district office's terminal (loreterminals' FOLabLoreWaimanaloOffice): "Notice, 08-19-2077", the fishermen's
  warning to keep boats off the cliffs past the cove where boats used to put in: a hole at the waterline. Shows its marker.
- a fisher's note in a tackle box on the shore south of it (`NOTE_FROM` the mouth, on land with a navmesh): "somebody used
  to put in at night ... something big in the water in there now". Taking it shows its words and the marker (quest
  `SEA_QUEST`'s script).

**The Pali Tunnels** (tunnelplace.py: the leeward portal above the Pali Checkpoint, a bulkhead and service door; the
pre-war martial-law checkpoint inside; the windward portal fallen in):
- the Pali Checkpoint's terminal (FOLabLorePali): "Orders, 10-23-2077 0335", close the tunnels, bulkhead down, service
  door only, the windward portal reporting cars backed up through both bores (the civil defense log: warning 0322,
  detonations 0347). Shows "Pali Tunnels".
- the Kailua Post Office's terminal (FOLabLoreKailuaPost): "Notice: Pali Highway closed", windward mail round by the
  coast road. Shows "Pali Tunnels, windward portal".

Each part goes in when its place's marker is in the mod and is left out (said so) when not, so this runs after the sea cave
step, the tunnel step, or both, and again after the other: a part already in is skipped. The markers get editor IDs
(`ref_set`, persistent) so the scripts can name them. A terminal entry is spliced in before the terminal's own cache item
(`splice`), whatever entries other steps put there (lore pointers, valley leads, wreck hints).

    plan(gd, pr)       {'parts', 'skipped', 'spots'}
    apply(pr, gd, P)   one Undo; nothing voiced
"""
import json
import math
import re

import recordio

LABEL = 'Hints to the sea cave and the Pali Tunnels'
SEA_QUEST, SEA_SCRIPT = 'FOLabSeaCaveLead', 'FOLabSeaCaveLeadScript'
MARKERS = {   # part: [(marker name, editor ID given)]
    'sea': [("Makapu'u Sea Cave", 'FOLabSeaCaveMarkerREF')],
    'pali': [('Pali Tunnels', 'FOLabPaliTunnelsMarkerREF'), ('Pali Tunnels, windward portal', 'FOLabPaliWindwardMarkerREF')],
}
ENTRIES = {   # part: [(loreterminals site, title, words, marker index)]
    'sea': [('waimanalo_offices', 'Notice, 08-19-2077', """
  Posted again at the fishermen's asking: keep boats off the cliffs north of
  Makapuu point. Past the cove where the boats used to put in there's a hole in
  the cliff at the waterline. The sea runs in and out of it. Two boys from the
  beach waded in after a drifting skiff in June. One came out.""", 0)],
    'pali': [('pali_checkpoint', 'Orders, 10-23-2077 0335', """
  Close the tunnels. Bulkhead down on the leeward portal; the service door is
  the only way through. Nobody through without papers.
  Windward portal reports cars backed up through both bores, people on foot.
  Hold the road.""", 0),
             ('kailua_post', 'Notice: Pali Highway closed', """
  By order of Martial Law Command the Pali Highway is closed at the tunnels
  from 10-23-2077. The windward portal is under guard.
  Mail for town goes round by the coast road until further notice.""", 1)],
}
NOTE = ('FOLabSeaCaveNote', "Fisher's Note", 'FOLabSeaCaveTackleBox', 'Tackle Box')
NOTE_WORDS = ("Don't take a boat north past the point. {dist} {dir} of here there's a hole in the foot of the cliff, right at "
              "the waterline. Somebody used to put in there at night. You wade up a shelf out of the sea to get in. Something "
              "big lives in the water inside now. Whatever they kept is still up the back.")
BOX_ITEMS = [('WaterPurified', 1)]
NOTE_FROM = (1500.0, 2500.0, 3500.0, 5000.0, 6500.0, 8000.0)   # (the box this far from the cave's mouth, on the shore)
DRY_OVER, SHORE_OVER = 24.0, 250.0                 # (its spot this far over the sea: on the shore, not in the shallows or up the cliff)
SEA_Z = 0.0
DIRS = ['north', 'north-east', 'east', 'south-east', 'south', 'south-west', 'west', 'north-west']


def _dir(frm, to):
    a = math.degrees(math.atan2(to[0] - frm[0], to[1] - frm[1])) % 360
    return DIRS[int((a + 22.5) // 45) % 8]


def _marker_ref(pr, name):
    for ck, c in pr.cells.items():
        for rk, r in (c.get('refs') or {}).items():
            m = r.get('marker')
            if isinstance(m, dict) and m.get('name') == name and not r.get('removed') and r.get('p'):
                return ck, rk, r
    return None, None, None


def _has(pr, etype, edid):
    return any(r.get('type') == etype and recordio.field(r, 'EDID') == edid for r in pr.records.values())


def _items_of(subs):
    """The subs before the first menu item, then each item's subs (an item starts at its ITXT)."""
    head, items = [], []
    for s in subs:
        if s.get('tag') == 'ITXT':
            items.append([s])
        elif items:
            items[-1].append(s)
        else:
            head.append(s)
    return head, items


def _text(item):
    return next((s.get('value') for s in item if s.get('tag') == 'ITXT'), None)


def _unlocks(item):
    return any(s.get('tag') == 'SCTX' and '.unlock' in str(s.get('value', '')).lower() for s in item)


def has_entry(rec, title):
    return any(_text(it) == title for it in _items_of(rec['subs'])[1])


def splice(gd, forms, rec, title, words, script):
    """rec with one more menu item (title, words, script) before its first item that unlocks something (the terminal's own
    cache), else last; the item made by terminals.records as any other."""
    import terminals
    spec = terminals.plan('Terminal: FOLabSpliceItem\nName: x\nModel: desk\nLock: none\nWelcome:\n  x\n== %s\nSays:\n%s\n'
                          % (title, '\n'.join('  ' + x.strip() for x in words.strip('\n').split('\n'))))
    spec['items'][0]['script'] = script
    made = terminals.records(gd, forms, spec, {})['terminal']['subs']
    new_item = _items_of(made)[1][0]
    head, items = _items_of(rec['subs'])
    at = next((n for n, it in enumerate(items) if _unlocks(it)), len(items))
    items.insert(at, new_item)
    return dict(rec, subs=head + [s for it in items for s in it])


def plan(gd, pr):
    import activity
    import loreterminals as LT
    from upvalleys import _Clear
    parts, skipped, S = [], [], {'markers': {}}
    for part, marks in MARKERS.items():
        why = []
        for name, edid in marks:
            ck, rk, r = _marker_ref(pr, name)
            if not r:
                why.append('no "%s" map marker' % name)
                continue
            S['markers'][name] = {'cell': ck, 'ref': rk, 'p': [round(v, 1) for v in r['p'][:3]], 'edid': r.get('edid') or edid,
                                  'named': bool(r.get('edid'))}
        for site, title, _w, _m in ENTRIES[part]:
            k = LT._term_key(pr, LT.terminals_edid(site))
            if not k:
                why.append('no lore terminal %s' % LT.terminals_edid(site))
            elif has_entry(pr.records[k], title):
                why.append('%s has "%s" already' % (LT.terminals_edid(site), title))
        if part == 'sea' and _has(pr, 'QUST', SEA_QUEST):
            why.append('the mod has %s already' % SEA_QUEST)
        if why:
            skipped.append('%s: %s' % (part, '; '.join(why)))
        else:
            parts.append(part)
    if 'sea' in parts:
        mouth = S['markers'][MARKERS['sea'][0][0]]['p']
        ctx = activity.Ctx(gd, pr)
        cl = _Clear(gd, pr, ctx)
        best = None
        for r in NOTE_FROM:
            for t in range(24):
                a = t * 2 * math.pi / 24
                for s in ctx.around(mouth[0] + r * math.sin(a), mouth[1] + r * math.cos(a), 3, radii=(0, 200, 400), turns=8):
                    if not (SEA_Z + DRY_OVER <= s[2] <= SEA_Z + SHORE_OVER) or not cl.ok(s[0], s[1]):
                        continue
                    score = -math.hypot(s[0] - mouth[0], s[1] - mouth[1])     # (the nearest dry, walkable shore to the mouth)
                    if best is None or score > best[0]:
                        best = (score, s)
            if best:
                break
        if not best:
            parts.remove('sea')
            skipped.append('sea: no clear dry shore with a navmesh within %d of the cave' % NOTE_FROM[-1])
        else:
            s = best[1]
            d = round(math.hypot(s[0] - mouth[0], s[1] - mouth[1]))
            S['box'] = {'world': (round(s[0], 1), round(s[1], 1), round(s[2], 1)), 'near': cl.dist(s[0], s[1]),
                        'from mouth': d, 'over sea': round(s[2] - SEA_Z)}
            S['note'] = NOTE_WORDS.format(dist='A short swim' if d < 3000 else 'A long swim', dir=_dir(s[:2], mouth[:2]))
    return {'parts': parts, 'skipped': skipped, 'spots': S}


def apply(pr, gd, P=None):
    import activity
    import api_scripts
    import api_characters as ac
    import api_quests as aq
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
    if not P['parts']:
        raise ValueError('nothing to put in: ' + '; '.join(P['skipped']))
    S = P['spots']
    out, rep = [], {'made': [], 'parts': list(P['parts']), 'left out': list(P['skipped'])}
    stub = lambda e: {'type': 'REFR', 'flags': tes4.PERSISTENT, 'subs': [{'tag': 'EDID', 'label': 'Editor ID', 'kind': 'z', 'value': e}]}
    ext, medids = {}, set()

    def record(rec, k=None):
        k = k or _new_key(pr)
        out.append({'op': 'record', 'key': k, 'record': rec})
        rep['made'].append(recordio.field(rec, 'EDID'))
        return k
    for part in P['parts']:
        for name, _e in MARKERS[part]:
            m = S['markers'][name]
            if not m['named']:
                out.append({'op': 'ref_set', 'cell': m['cell'], 'ref': m['ref'], 'set': {'edid': m['edid'], 'persistent': True}})
                rep['made'].append(m['edid'])
            ext[m['ref']] = stub(m['edid'])
            medids.add(m['edid'])
    later = []
    if 'sea' in P['parts']:
        m = S['markers'][MARKERS['sea'][0][0]]
        misc_like = UV._game_key(gd, UV.MISC_LIKE, 'MISC')[1]
        note = surffish._copy(gd, 'MISC', misc_like, NOTE[0], NOTE[1])
        note['subs'] = [s for s in note['subs'] if s['tag'] != 'SCRI']
        note_key = record(note)
        msg = NOTE[0] + 'Msg'
        record(newgame._message_record(msg, S['note']))
        base = UV._game_key(gd, UV.SATCHEL_LIKE, 'CONT')[0]
        rec = recordio.load(gd, gd.from_key(base))
        rec['src'] = ''
        recordio.set_field(rec, 'EDID', NOTE[2], label='Editor ID')
        if any(s['tag'] == 'FULL' for s in rec['subs']):
            recordio.set_field(rec, 'FULL', NOTE[3])
        else:
            ac.insert(rec, {'tag': 'FULL', 'label': 'Name', 'kind': 'z', 'value': NOTE[3]})
        rec['subs'] = [s for s in rec['subs'] if s['tag'] not in ('CNTO', 'COED', 'SCRI')]
        for k, n in [(note_key, 1)] + [(UV._game_item(gd, e), n) for e, n in BOX_ITEMS]:
            if not k:
                continue
            s = ff._sub('CONT', 'CNTO', struct.pack('<Ii', 0, n))
            ff._set_link(s, k)
            ac.insert(rec, s)
        box_key = record(rec)
        grid = activity.Ctx(gd, pr).grid
        x, y, z = S['box']['world']
        out.append({'op': 'place', 'cell': gd.key(grid[(int(math.floor(x / 4096.0)), int(math.floor(y / 4096.0)))]), 'key': _new_key(pr),
                    'ref': {'base': box_key, 'p': [x, y, z, 0.0, 0.0, 0.0], 's': 1.0, 'persistent': True, 'edid': NOTE[2] + 'REF'}})
        rep['made'].append(NOTE[2] + 'REF')
        qkey, skey = _new_key(pr), _new_key(pr)
        src = '\n'.join(['scn %s' % SEA_SCRIPT, 'short noted', '', 'Begin GameMode', '\tif noted == 0',
                         '\t\tif player.GetItemCount %s >= 1' % NOTE[0], '\t\t\tset noted to 1', '\t\t\tShowMessage %s' % msg,
                         '\t\t\tShowMap %s' % m['edid'], '\t\t\tStopQuest %s' % SEA_QUEST, '\t\tendif', '\tendif', 'End', ''])
        plain = {'edid': SEA_QUEST, 'name': '', 'script': skey, 'flags': {'start_enabled': True}, 'priority': 10, 'delay': 2.0,
                 'stages': [], 'objectives': [], 'conditions': []}
        qstub = qr.quest_record(plain)
        known = dict(ext)
        known[qkey] = qstub
        known.update({o['key']: o['record'] for o in out if o['op'] == 'record'})
        sc = api_scripts.scripts()
        was = sc.forms.is_map_marker
        sc.forms.is_map_marker = lambda f, was=was: (getattr(f, 'rec', None) is not None and recordio.field(f.rec, 'EDID') in medids) or was(f)
        try:
            c = sc.compile(src, skey, 'quest', known)
        finally:
            sc.forms.is_map_marker = was
        if not hasattr(c, 'subrecords'):
            raise ValueError('%s: %s' % (SEA_SCRIPT, c))
        out.append({'op': 'record', 'key': skey, 'record': sc._record_of(c, SEA_SCRIPT)})
        out.append({'op': 'record', 'key': qkey, 'record': qstub})
        rep['made'] += [SEA_SCRIPT, SEA_QUEST]
        full = json.loads(json.dumps(plain))
        errors = aq.compile_quest(full, PP._forms(gd, pr, ext, {o['key']: o['record'] for o in out if o['op'] == 'record'}))
        if errors:
            raise ValueError('%s: %s' % (SEA_QUEST, errors))
        later.append({'op': 'record', 'key': qkey, 'record': qr.quest_record(full)})
    # the terminal entries, each showing its marker
    forms = PP._forms(gd, pr, ext, {o['key']: o['record'] for o in out if o['op'] == 'record'})
    for e, kr in terminals.mod_forms(gd, pr).own.items():
        forms.own.setdefault(e, kr)
    for rk, st in ext.items():
        forms.own[recordio.field(st, 'EDID').lower()] = (rk, st)
    was2 = forms.is_map_marker
    forms.is_map_marker = lambda f, was=was2: (f.rec is not None and recordio.field(f.rec, 'EDID') in medids) or was(f)
    changed = {}
    for part in P['parts']:
        for site, title, words, mi in ENTRIES[part]:
            tk = LT._term_key(pr, LT.terminals_edid(site))
            have = changed.get(tk) or pr.records[tk]
            medid = S['markers'][MARKERS[part][mi][0]]['edid']
            changed[tk] = splice(gd, forms, have, title, words, 'ShowMap %s' % medid)
            rep['made'].append('%s (entry "%s")' % (LT.terminals_edid(site), title))
    pr.apply(LABEL, out)
    pr.apply(LABEL, later + [{'op': 'record', 'key': k, 'record': r} for k, r in changed.items()], merge=True)
    rep['spots'] = {k: v for k, v in S.items()}
    return rep


def check(pr):
    """What is in now: each entry, the note's box, the markers named (for the step's CHECKS)."""
    import loreterminals as LT
    out = {'entries': {}, 'box': None, 'markers': {}}
    for part, ents in ENTRIES.items():
        for site, title, words, mi in ents:
            k = LT._term_key(pr, LT.terminals_edid(site))
            out['entries'][title] = bool(k and has_entry(pr.records[k], title))
    for part, marks in MARKERS.items():
        for name, edid in marks:
            _ck, _rk, r = _marker_ref(pr, name)
            out['markers'][name] = r.get('edid') if r else None
    for c in pr.cells.values():
        for r in (c.get('refs') or {}).values():
            if r.get('edid') == NOTE[2] + 'REF' and not r.get('removed'):
                out['box'] = [round(v) for v in r['p'][:3]]
    return out


def words_ok():
    """Every entry's and the note's words: the game's font (cp1252), terminal lines within 92."""
    bad = []
    for ents in ENTRIES.values():
        for _s, title, words, _m in ents:
            for line in [title] + words.strip('\n').split('\n'):
                try:
                    line.encode('cp1252')
                except UnicodeEncodeError:
                    bad.append(line)
                if len(line.strip()) > 92:
                    bad.append(line)
    try:
        NOTE_WORDS.encode('cp1252')
    except UnicodeEncodeError:
        bad.append(NOTE_WORDS)
    if re.search(r'Mojave|Vegas|NCR|Legion', json.dumps([ENTRIES, NOTE_WORDS])):
        bad.append('a Mojave word')
    return bad
