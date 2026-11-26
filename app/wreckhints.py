"""Hints to the sunken wrecks (the Workshop, 26 Nov 2026: hints that lead to loot-and-rewards' big sunken wrecks off the coast,
through terminal entries and notes, markers shown as learned; island lore only).

The wrecks lie off the windward side, so the hints are windward too, each written for what it is:
- **Waimanalo's district office** (loreterminals' FOLabLoreWaimanaloOffice) and **the Windward Mall pharmacy** at Kaneohe
  (FOLabLoreKaneohePharmacy): a new entry each, before the pharmacy's own cache item, naming the wrecks nearest them.
- **A harbour log** (`HARBOUR_TEXT`): a terminal of its own by Kaneohe, the Heeia Kea small-boat harbour's pre-war log.
- **A salvager's notebook** (`NOTEBOOK`): in a satchel by Kailua; taking it pops up its words.
The wrecks' models are said plainly (`PLAIN`: a bomber, a barge, fishing boats): the game's names are never shown.
Each names a wreck by a landmark on the shore and a direction, and its item script (the notebook: the quest script) shows the
wreck's marker on the map (placed hidden over the wreck) and its objective. Swimming within `FOUND` of a wreck completes it.

Built on what is decided: the sea is the pirates'; storms (hurricanes) every few days; the Castaway's boat went down off Koko
Head; nobody but pirates sails far. Pre-war entries are dated 2077, later ones typed long after. No Mojave anything.

The wrecks come from loot-and-rewards' list (`WRECKS_FILE`, rows with 'p' and a 'name' or 'kind'). A terminal is changed only
if it is exactly what loreterminals makes from its text.

    plan(gd, pr)       {'rows', 'skipped', 'spots'}
    apply(pr, gd, P)   one Undo; nothing voiced
"""
import json
import math
import re

import recordio

LABEL = 'Hints to the sunken wrecks'
QUEST, QSCRIPT = 'FOLabWreckLeads', 'FOLabWreckLeadsScript'
WRECKS_FILE = r'D:\FOLab-bonus\sea_plan.json'      # (loot-and-rewards' sea step: report.sites)
FOUND = 900.0                      # (swimming this near a wreck finds it)
MOST = 5
WRECK_NEAR = 3000.0                # (the mod's wreck ref this near the list's spot is the one; WRECKS_FROM_FILE=1 trusts the list: rehearsals)
SOURCES = {                        # source: (where it stands, which wrecks it tells: nearest to this point); both coasts
    'lighthouse': ('terminal', 'lighthouse', (-63274, -59058)),
    'lifeguard': ('terminal', 'makai_lifeguard', (-9696, -31520)),
    'harbour': ('new', 'Ala Wai Boat Harbor', (-83871, -16485)),
    'district': ('terminal', 'waimanalo_offices', (71748, 79422)),
    'pharmacy': ('terminal', 'kaneohe_pharmacy', (-52823, 196536)),
    'notebook': ('note', 'Koko Marina', (88202, -21622)),      # (only if a wreck is left over: one a source first)
}
PLAIN = [(r'B29|Bomber', 'bomber'), (r'barge', 'barge'), (r'Boat01', 'fishing boat'), (r'Boat02', 'skiff'), (r'.', 'wreck')]
HARBOUR_TEXT = """Terminal: FOLabWreckHarbourLog
Name: Harbour Office Terminal
Model: desk
Lock: none
Welcome:
  CITY AND COUNTY OF HONOLULU
  ALA WAI SMALL BOAT HARBOR - HARBOUR MASTER
== Notice to mariners, 10-20-2077
Says:
  Navy traffic has priority in the channel. Pleasure craft keep inside the breakwater.
  Divers: the reef outside is not a playground. Neither is anything sunk on it.
"""
NOTEBOOK = ('FOLabWreckNotebook', "Salvager's Notebook", 'FOLabWreckNotebookSatchel')
DIRS = ['north', 'north-east', 'east', 'south-east', 'south', 'south-west', 'west', 'north-west']


def wrecks(path=WRECKS_FILE):
    """The biggest wrecks first (the sea step's band), MOST of them: {'name' (plain), 'model', 'p' (x, y, -depth), 'depth'}."""
    d = json.load(open(path, encoding='utf-8'))
    sites = (d.get('report') or {}).get('sites') or d.get('rows') or [] if isinstance(d, dict) else d
    out = []
    for r in sorted(sites, key=lambda r: -r.get('band', 0)):
        p = r.get('at') or r.get('p')
        if not p:
            continue
        model = r.get('wreck') or r.get('name') or ''
        name = next(n for pat, n in PLAIN if re.search(pat, model, re.I))
        depth = float(r.get('depth') or 0)
        out.append({'name': name, 'model': model, 'p': [float(p[0]), float(p[1]), -depth], 'depth': depth})
    return out[:MOST]


def _dir(frm, to):
    a = math.degrees(math.atan2(to[0] - frm[0], to[1] - frm[1])) % 360
    return DIRS[int((a + 22.5) // 45) % 8]


def _far(d):
    return 'close in' if d < 4000 else 'a short swim' if d < 9000 else 'a long swim' if d < 16000 else 'far out'


def _plain(name):
    return re.sub(r'([a-z])([A-Z])', r'\1 \2', name).replace('_', ' ').strip().lower()


def assign(W, marks):
    """[(source, wreck index)]: every wreck told once, each by the source nearest it (a source tells two at most)."""
    load = {s: 0 for s in SOURCES}
    out = []
    pairs = sorted((math.dist(SOURCES[s][2], w['p'][:2]), s, i) for i, w in enumerate(W) for s in SOURCES)
    told = set()
    for cap in (1, 2):                  # (one wreck a source first, nearest pairs first; then a second where needed)
        for _d, s, i in pairs:
            if i not in told and load[s] < cap:
                load[s] += 1
                told.add(i)
                out.append((s, i))
    return sorted(out, key=lambda t: t[1])


def words(src, w, marks):
    """(title, words), each line of the words wrapped to the terminal's width."""
    import textwrap
    title, said = _words(src, w, marks)
    if src == 'notebook':
        return title, said
    lines = []
    for part in said.split('\n'):
        lines += ['  ' + x for x in textwrap.wrap(part.strip(), 84)]
    return title, '\n'.join(lines)


def _words(src, w, marks):
    """The entry for one wreck: (title, words), named by the nearest map marker on shore and a direction from it."""
    land = min(marks, key=lambda m: math.dist(m[1:3], w['p'][:2]))
    d = math.dist(land[1:3], w['p'][:2])
    where = '%s %s of %s' % (_far(d), _dir(land[1:3], w['p'][:2]), land[0])
    what = _plain(w['name'])
    depth = ''
    if w.get('depth'):
        fathoms = max(2, int(round(w['depth'] * 0.01428 / 1.829)))     # (a game unit is 1.43 cm; a fathom 1.83 m)
        depth = ' About %d fathoms down.' % fathoms
    if src == 'lighthouse':
        return ('Charted hull: the %s' % what, "  Hull on the bottom, %s.%s\n  Marked for shipping. Not marked for divers. Keep off it in a swell." % (where, depth))
    if src == 'lifeguard':
        return ('Incident log: the %s' % what, "  Swimmer pulled out over the %s, %s.%s\n  Said he saw something big down there and wanted to go back. Advised against it." % (what, where, depth))
    if src == 'district':
        return ('Report: the %s' % what, "  Fishermen report a %s on the bottom, %s.%s\n  Nobody from this office is going down to look. Nobody from this office swims." % (what, where, depth))
    if src == 'pharmacy':
        return ('Patient note: the %s' % what, "  Diver treated for the bends after going down on the %s, %s.%s\n  Says he'll go back for what he left down there. Advised him not to." % (what, where, depth))
    if src == 'harbour':
        return ('Notice to mariners: %s' % what, "  Obstruction: the %s, %s.%s\n  Do not anchor over it. Do not dive on it without a second man." % (what, where, depth))
    return ('', "%s on the bottom, %s.%s Got a crate of tins off it on one breath. More down there, too deep for me now. Go at slack water." % (what.capitalize(), where, depth))


def plan(gd, pr):
    import activity
    import loreterminals as LT
    rows, skipped, S = [], [], {}
    if any(r.get('type') == 'QUST' and recordio.field(r, 'EDID') == QUEST for r in pr.records.values()):
        skipped.append('the mod has %s already' % QUEST)
    try:
        W = wrecks()
    except (OSError, ValueError) as e:
        return {'rows': [], 'skipped': ['no wreck list: %s' % e], 'spots': S}
    if len(W) < 3:
        skipped.append('only %d wrecks in the list' % len(W))
    for s, (kind, site, _p) in SOURCES.items():
        if kind == 'terminal' and not LT._term_key(pr, LT.terminals_edid(site)):
            skipped.append('no lore terminal %s' % LT.terminals_edid(site))
    if skipped:
        return {'rows': rows, 'skipped': skipped, 'spots': S}
    ctx = activity.Ctx(gd, pr)
    marks = [(n, p[0], p[1]) for n, (_c, p) in ctx.mk.items() if p]
    from upvalleys import _Clear, _outside_spot
    cl = _Clear(gd, pr, ctx)
    for s, (kind, site, _p) in SOURCES.items():
        if kind in ('new', 'note'):
            if site not in ctx.mk:
                skipped.append('no map marker %s' % site)
                continue
            p = ctx.mk[site][1]
            got = _outside_spot(ctx, cl, p[0], p[1], (300, 450, 600, 800, 1000, 1300), own_marker=p[:2], people=True)
            (S.__setitem__(s, {'world': got, 'near': cl.dist(got[0], got[1])}) if got else skipped.append('no room for the %s' % s))
    # each wreck where the mod stands it (the sea step in already): its model's ref nearest the list's spot
    import os
    if not os.environ.get('WRECKS_FROM_FILE'):
        for w in W:
            near = sorted((math.dist(p[:2], w['p'][:2]), p) for p in ctx.of(w['model']))
            if near and near[0][0] <= WRECK_NEAR:
                w['p'][:2] = [round(near[0][1][0], 1), round(near[0][1][1], 1)]
            else:
                skipped.append('the %s (%s) is not in the mod near %s: run this after the sea step' % (w['name'], w['model'], [round(v) for v in w['p'][:2]]))
        if skipped:
            return {'rows': rows, 'skipped': skipped, 'spots': S}
    S['wrecks'] = W
    S['told'] = assign(W, marks)
    S['words'] = {i: words(src, W[i], marks) for src, i in S['told']}
    for src, i in S['told']:
        rows.append({'wreck': W[i]['name'], 'p': [round(v) for v in W[i]['p']], 'told by': src, 'entry': S['words'][i][0] or 'notebook'})
    return {'rows': rows, 'skipped': skipped, 'spots': S}


def apply(pr, gd, P=None):
    import api_quests as aq
    import api_scripts
    import loreterminals as LT
    import newgame
    import pinkpearl as PP
    import questrec as qr
    import surffish
    import terminals
    import tes4
    import upvalleys as UV
    from activity import _new_key
    P = P or plan(gd, pr)
    if P['skipped']:
        raise ValueError('; '.join(P['skipped']))
    S = P['spots']
    W, told = S['wrecks'], S['told']
    out, rep = [], {'made': []}
    import activity
    ctx = activity.Ctx(gd, pr)
    grid = ctx.grid

    def record(rec, k=None):
        k = k or _new_key(pr)
        out.append({'op': 'record', 'key': k, 'record': rec})
        rep['made'].append(recordio.field(rec, 'EDID'))
        return k

    def place(base, xyz, edid, extra=None):
        k = _new_key(pr)
        x, y, z = xyz
        cell = gd.key(grid[(int(math.floor(x / 4096.0)), int(math.floor(y / 4096.0)))])
        ref = {'base': base, 'p': [round(x, 1), round(y, 1), round(z, 1), 0.0, 0.0, 0.0], 's': 1.0, 'persistent': True, 'edid': edid}
        if extra:
            ref.update(extra)
        out.append({'op': 'place', 'cell': cell, 'key': k, 'ref': ref})
        rep['made'].append(edid)
        return k
    # markers over each wreck, hidden till learnt
    mk_edid = {}
    for i, w in enumerate(W):
        e = 'FOLabWreckMarker%d' % (i + 1)
        mk_edid[i] = e
        place('FalloutNV.esm:000010', w['p'], e, {'marker': {'name': _plain(w['name']).title() + ' Wreck', 'type': 4, 'flags': 2}})
    # the notebook (only if a wreck is left for it): a MISC in a satchel by Koko Marina, its words in a message box
    note_wrecks = [i for s, i in told if s == 'notebook']
    msg = 'FOLabWreckNotebookMsg'
    if note_wrecks:
        misc_like = UV._game_key(gd, UV.MISC_LIKE, 'MISC')[1]
        nb = surffish._copy(gd, 'MISC', misc_like, NOTEBOOK[0], NOTEBOOK[1])
        nb['subs'] = [s for s in nb['subs'] if s['tag'] != 'SCRI']
        nb_key = record(nb)
        body = ' '.join(S['words'][i][1] for i in note_wrecks)
        record(newgame._message_record(msg, "A salvager's notebook, water-stained: " + body))
        import api_characters as ac
        import factionfolk as ff
        import struct
        base = UV._game_key(gd, UV.SATCHEL_LIKE, 'CONT')[0]
        rec = recordio.load(gd, gd.from_key(base))
        rec['src'] = ''
        recordio.set_field(rec, 'EDID', NOTEBOOK[2], label='Editor ID')
        rec['subs'] = [s for s in rec['subs'] if s['tag'] not in ('CNTO', 'COED', 'SCRI')]
        s = ff._sub('CONT', 'CNTO', struct.pack('<Ii', 0, 1))
        ff._set_link(s, nb_key)
        ac.insert(rec, s)
        place(record(rec), S['notebook']['world'], NOTEBOOK[2] + 'REF')
    # the quest: one objective a wreck, shown when told, done when found
    qkey, skey = _new_key(pr), _new_key(pr)
    vars_ = ['told%d' % (i + 1) for i in range(len(W))] + ['found%d' % (i + 1) for i in range(len(W))] + ['nb', 'done']
    L = ['scn %s' % QSCRIPT] + ['short %s' % v for v in vars_] + ['short shown%d' % (i + 1) for i in range(len(W))] + ['', 'Begin GameMode']
    if note_wrecks:
        L += ['\tif nb == 0', '\t\tif player.GetItemCount %s >= 1' % NOTEBOOK[0], '\t\t\tset nb to 1', '\t\t\tShowMessage %s' % msg]
        L += ['\t\t\tShowMap %s' % mk_edid[i] for i in note_wrecks] + ['\t\t\tset told%d to 1' % (i + 1) for i in note_wrecks] + ['\t\tendif', '\tendif']
    for i in range(len(W)):
        n = i + 1
        L += ['\tif told%d == 1' % n, '\t\tif shown%d == 0' % n, '\t\t\tset shown%d to 1' % n, '\t\t\tSetObjectiveDisplayed %s %d 1' % (QUEST, n * 10),
              '\t\tendif', '\tendif']
        L += ['\tif found%d == 0' % n, '\t\tif player.GetDistance %s < %d' % (mk_edid[i], FOUND), '\t\t\tset found%d to 1' % n,
              '\t\t\tSetObjectiveDisplayed %s %d 1' % (QUEST, n * 10), '\t\t\tSetObjectiveCompleted %s %d 1' % (QUEST, n * 10), '\t\tendif', '\tendif']
    L += ['\tif done == 0', '\t\tif %s' % ' && '.join('found%d == 1' % (i + 1) for i in range(len(W))), '\t\t\tset done to 1',
          '\t\t\tSetStage %s 100' % QUEST, '\t\tendif', '\tendif', 'End', '']
    src = '\n'.join(L)
    stub = lambda e: {'type': 'REFR', 'flags': tes4.PERSISTENT, 'subs': [{'tag': 'EDID', 'label': 'Editor ID', 'kind': 'z', 'value': e}]}
    ext = {o['key']: stub(o['ref']['edid']) for o in out if o['op'] == 'place'}
    marker_edids = set(mk_edid.values())
    plain = {'edid': QUEST, 'name': 'Wrecks Off the Coast', 'script': skey, 'flags': {'start_enabled': True}, 'priority': 50, 'delay': 1.0,
             'stages': [UV._stage(100, "I dived on every wreck the old logs told of.", 'CompleteQuest %s\n' % QUEST)],
             'objectives': [{'index': (i + 1) * 10, 'text': 'Dive on the %s' % _plain(w['name']), 'targets': []} for i, w in enumerate(W)],
             'conditions': []}
    qstub = qr.quest_record(dict(plain, stages=[], objectives=[]))
    known = dict(ext)
    known[qkey] = qstub
    known.update({x['key']: x['record'] for x in out if x['op'] == 'record'})
    sc = api_scripts.scripts()
    was = sc.forms.is_map_marker
    sc.forms.is_map_marker = lambda f, was=was: (getattr(f, 'rec', None) is not None and recordio.field(f.rec, 'EDID') in marker_edids) or was(f)
    try:
        c = sc.compile(src, skey, 'quest', known)
    finally:
        sc.forms.is_map_marker = was
    if not hasattr(c, 'subrecords'):
        raise ValueError('%s: %s' % (QSCRIPT, c))
    srec = sc._record_of(c, QSCRIPT)
    out.append({'op': 'record', 'key': skey, 'record': srec})
    out.append({'op': 'record', 'key': qkey, 'record': qstub})
    rep['made'] += [QSCRIPT, QUEST]
    forms = PP._forms(gd, pr, ext, {x['key']: x['record'] for x in out if x['op'] == 'record'})
    full = json.loads(json.dumps(plain))
    errors = aq.compile_quest(full, forms)
    if errors:
        raise ValueError('%s: %s' % (QUEST, errors))
    # terminals: entries on the lore terminals told, and the harbour log of its own
    for e, kr in terminals.mod_forms(gd, pr).own.items():
        forms.own.setdefault(e, kr)
    was2 = forms.is_map_marker
    forms.is_map_marker = lambda f, was=was2: (f.rec is not None and recordio.field(f.rec, 'EDID') in marker_edids) or was(f)

    def entry(i):
        title, said = S['words'][i]
        return {'text': title, 'says': '\n'.join(x.strip() for x in said.strip('\n').split('\n')), 'unlocks': [], 'note': '',
                'script': 'set %s.told%d to 1\nShowMap %s' % (QUEST, i + 1, mk_edid[i])}
    term_ops = []
    for s, (kind, site, _p) in SOURCES.items():
        mine = [i for src, i in told if src == s]
        if not mine:
            continue
        if kind == 'terminal':
            tk = LT._term_key(pr, LT.terminals_edid(site))
            have = pr.records[tk]
            Sx = LT.SITES[site]
            cache_ref = (Sx['cache'][0] + 'REF') if Sx['cache'] else ''
            spec = terminals.plan(LT.text_of(site).replace('{cache}', cache_ref).replace('{HEAD}', LT.HEAD))
            if json.dumps(terminals.records(gd, forms, spec, {})['terminal']['subs'], sort_keys=True) != json.dumps(have['subs'], sort_keys=True):
                raise ValueError('%s is not as loreterminals makes it' % LT.terminals_edid(site))
            at = next((n for n, it in enumerate(spec['items']) if it['unlocks']), len(spec['items']))
            for i in mine:
                spec['items'].insert(at, entry(i))
                at += 1
            new = terminals.records(gd, forms, spec, {})['terminal']
            term_ops.append({'op': 'record', 'key': tk, 'record': dict(have, subs=new['subs'])})
            rep['made'].append(LT.terminals_edid(site) + ' (entries)')
        elif kind == 'new':
            spec = terminals.plan(HARBOUR_TEXT)
            for i in mine:
                spec['items'].append(entry(i))
            t_ops, t_keys = terminals.ops(gd, pr, spec, forms)
            for o in t_ops:
                k = _new_key(pr)
                assert k == t_keys[recordio.field(o['record'], 'EDID')]
                out.append({'op': 'record', 'key': k, 'record': o['record']})
            x, y, z = S[s]['world']
            k = _new_key(pr)
            out.append({'op': 'place', 'cell': gd.key(grid[(int(math.floor(x / 4096.0)), int(math.floor(y / 4096.0)))]), 'key': k,
                        'ref': {'base': t_keys[spec['edid']], 'p': [x, y, z, 0.0, 0.0, 0.0], 's': 1.0}})
            rep['made'].append(spec['edid'])
    pr.apply(LABEL, out)
    pr.apply(LABEL, [{'op': 'record', 'key': qkey, 'record': qr.quest_record(full)}] + term_ops, merge=True)
    rep.update({'wrecks': [(w['name'], w['model'], [round(v) for v in w['p']]) for w in W], 'told': told,
                'entries': {'%d %s' % (i + 1, W[i]['name']): S['words'][i] for i in range(len(W))},
                'at': {k: v['world'] for k, v in S.items() if isinstance(v, dict) and 'world' in v}})
    return rep
