"""Lights back on, and power cells (docs/waikiki-speech-science.md section J, systems 9 and 6; decided power: the ridge
settlements have wind and scraps of solar, a little, mostly fire; the Vault recharges cells and pays the pirates in
them, so anyone wanting light depends on it).

At each of `SITES` (ridge settlements), a broken generator (an activator on night lights' generator model) stands by the
settlement:
- **Unfixed:** it needs Science 55 and 2 Scrap Electronics. Fixed, it switches on that place's lights (two strings of
  bulbs and a lantern post with their lights, under a persistent marker placed off: their enable parent), a trader (her
  merchant chest buried, "Let's trade." by ShowBarterMenu) and a bedroll for you.
- **Fixed:** using it gives a menu (a message with buttons; GetButtonPressed). "Charge drained cells" turns the game's
  Drained Microfusion Cells and Drained Small Energy Cells into charged ones, one for one; at Science 75, one and a half.
  It's a way not to hang on the Vault.

**Where:** on a navmesh near the settlement's marker (factionfolk's search: not inside a building, clear of anyone
standing), clear of doors and the trail's signposts (secretcaches' rules), the lights round the generator.

    plan(gd, pr)       {'rows': [...], 'skipped'}
    apply(pr, gd, P)   one Undo (VOICE: the traders' lines)
"""
import math
import re

import recordio

LABEL = 'Lights back on, and power cells'
VOICE = ['FOLabGenerators']
QUEST = 'FOLabGenerators'
SITES = ('The Tanks', 'The Holdouts', 'Loa Gate')
FIX_SCIENCE, BONUS_SCIENCE = 55, 75
PARTS = ('ScrapElectronics', 2)
CELLS = [('DrainedMicrofusionCell', 'AmmoMicroFusionCell'), ('DrainedSmallEnergyCell', 'AmmoSmallEnergyCell')]
LIGHTS = [('pole_bulbs_600', 600.0, 0.0), ('pole_bulbs_600', -600.0, 0.0), ('lantern_post', 0.0, 500.0)]
TRADER_FROM, CHEST_FROM = 'FOLabWaikikiLocal', 'VendorContainerChet'
BED = 'NVBedrollR'
GEN_MODEL = 'folab\\night\\generator.nif'    # (night lights' generator: its model is in the mod's files, no record of it there)
GEN_BOUNDS = (-70, -45, 0, 70, 45, 95)
WORDS = {'broken': "The generator's dead. Somebody who knows electrics could bring it back (Science 55), with 2 Scrap Electronics.",
         'fixed': "The generator coughs, catches and runs. Lights come on round the settlement.",
         'menu': "The generator hums. Drained cells can be charged off it.",
         'charge': 'Charge drained cells', 'leave': 'Leave it',
         'charged': "The cells take the charge.",
         'hello': "Power's back. So I'm open. What do you need?", 'trade': "Let's trade.", 'trade_yes': "Have a look."}


def _mod_key(pr, edid, tag=None):
    return next((k for k, r in pr.records.items() if (tag is None or r.get('type') == tag) and recordio.field(r, 'EDID') == edid), None)


def _short(s):
    return re.sub(r'[^A-Za-z]', '', s)


def _piece(pr, name):
    """The mod's STAT of night lights' piece (by its model's file name)."""
    for k, r in pr.records.items():
        if r.get('type') == 'STAT':
            m = (recordio.field(r, 'MODL') or '').lower().replace('/', '\\')
            if m.endswith('night\\%s.nif' % name.lower()):
                return k
    return None


def plan(gd, pr):
    import factionfolk as ff
    import robots
    import secretcaches
    import waikikilife as WL
    mk = ff._markers(pr)
    world = gd.ext_cells[gd.from_key(mk['The Royal Hawaiian'][0])] if 'The Royal Hawaiian' in mk else None
    sp = secretcaches._spots_for(gd, pr, gd.key(world))
    posts = [r['p'] for _c, _k, r in secretcaches._outside_refs(gd, pr, lambda r: secretcaches._ed(gd, pr, r.get('base', '')) == secretcaches.TRAIL_POST)]
    rows, skipped = [], []
    for name in SITES:
        if name not in mk:
            skipped.append((name, 'no map marker'))
            continue
        x0, y0 = mk[name][1][:2]
        doors = robots._outside_doors(gd, pr, sp.grid, {'a': (x0, y0)})
        gp, gn = secretcaches._outside(gd, pr, sp, x0, y0, (400, 600, 800, 1000, 1300), doors, posts)
        if not gp:
            skipped.append((name, 'no clear spot for the generator'))
            continue
        got = {'generator': gp}
        for what, radii in (('trader', (250, 350, 450, 600)), ('bed', (300, 450, 600, 800))):
            p, _n = secretcaches._outside(gd, pr, sp, gp[0], gp[1], radii, doors, posts, avoid=[gp] + [v for v in got.values()])
            if p:
                got[what] = p
        lights = []
        for piece, _dx, _dy in LIGHTS:               # (round the generator, on open ground, apart from each other and the rest)
            p, _n = secretcaches._outside(gd, pr, sp, gp[0], gp[1], (350, 500, 650, 800, 1000), doors, posts,
                                          avoid=list(got.values()) + [q for _pc, q in lights])
            if p:
                lights.append((piece, p))
        rows.append({'site': name, 'spots': got, 'lights': lights, 'near': gn})
    return {'rows': rows, 'skipped': skipped, 'world': gd.key(world)}


def _cond(fn, op, value, p1=0, p2=0, run=0):
    return {'or': False, 'use_target': False, 'op': op, 'fn': fn, 'p1': p1, 'p2': p2, 'run': run, 'ref': '', 'value': float(value)}


def _message(edid, words, buttons=()):
    import newgame
    m = newgame._message_record(edid, words)
    m['subs'] += [{'tag': 'ITXT', 'label': 'Button text', 'kind': 'z', 'value': b} for b in buttons]
    return m


def ops(gd, pr, P=None):
    import json
    import api_characters as ac
    import api_quests as aq
    import api_scripts
    import factionfolk as ff
    import nightlights
    import piratedeal
    import questrec as qr
    import waikikilife as WL
    from activity import _new_key
    if _mod_key(pr, QUEST, 'QUST'):
        raise ValueError('the mod already has %s (Undo first)' % QUEST)
    P = P or plan(gd, pr)
    rows = P['rows']
    if not rows:
        raise ValueError('nowhere to stand a generator: %s' % P['skipped'])
    grid = gd.grid(gd.from_key(P['world']))
    cell = lambda x, y: gd.key(grid[(int(x // 4096), int(y // 4096))])
    out, rep = [], {'made': [], 'sites': {}, 'skipped': P['skipped']}
    sc = api_scripts.scripts()

    def record(k, rec):
        out.append({'op': 'record', 'key': k, 'record': rec})
        rep['made'].append(recordio.field(rec, 'EDID'))
        return k

    msgs = {k: _new_key(pr) for k in ('broken', 'fixed', 'menu', 'charged')}
    record(msgs['broken'], _message('FOLabGeneratorBrokenMsg', WORDS['broken']))
    record(msgs['fixed'], _message('FOLabGeneratorFixedMsg', WORDS['fixed']))
    record(msgs['menu'], _message('FOLabGeneratorMenuMsg', WORDS['menu'], (WORDS['charge'], WORDS['leave'])))
    record(msgs['charged'], _message('FOLabGeneratorChargedMsg', WORDS['charged']))
    extra = {k: out[n]['record'] for n, k in enumerate(msgs.values())}
    gen_model = GEN_MODEL
    # the quest: its topics and the traders' lines
    quest_key, qs_key = _new_key(pr), _new_key(pr)
    quest = qr.quest_record({'edid': QUEST, 'script': qs_key, 'name': '', 'flags': {'start_enabled': True}, 'priority': 41,
                             'delay': 5.0, 'stages': [], 'objectives': []})
    c = sc.compile('scn FOLabGeneratorsScript\nshort powerruns\n\nBegin GameMode\nEnd\n', qs_key, 'quest', {quest_key: quest})
    record(qs_key, sc._record_of(c, 'FOLabGeneratorsScript'))
    record(quest_key, quest)
    trade_topic = _new_key(pr)
    record(trade_topic, qr.topic_record({'edid': 'FOLabGeneratorsTrade', 'name': WORDS['trade'], 'priority': 50.0, 'kind': 0,
                                         'flags': {'top_level': True}, 'quests': [{'quest': quest_key, 'links': []}]}))
    tfrom = _mod_key(pr, TRADER_FROM, 'NPC_')
    services = ac.num(recordio.load(gd, piratedeal._game(gd, WL.SERVICES_FROM, 'NPC_')), 'AIDT', 'Services')
    traders = []
    for row in rows:
        s = _short(row['site'])
        sp = row['spots']
        mkey = _new_key(pr)
        mx, my, mz, _r = sp['generator']
        marker_edid = 'FOLabPower%sMarker' % s
        out.append({'op': 'place', 'cell': cell(mx, my), 'key': mkey, 'ref': {'base': gd.key(piratedeal._game(gd, 'XMarker', 'STAT')),
                    'p': [mx, my, mz + 300, 0.0, 0.0, 0.0], 's': 1.0, 'persistent': True, 'edid': marker_edid, 'props': {'disabled': True}}})
        extra[mkey] = {'type': 'REFR', 'flags': 0x400, 'subs': [{'tag': 'EDID', 'label': 'Editor ID', 'kind': 'z', 'value': marker_edid}]}
        parent = {'ref': mkey, 'opposite': False, 'popin': False}
        # the generator: an activator of the piece's model, its script
        skey, akey = _new_key(pr), _new_key(pr)
        L = ['scn FOLabGenerator%sScript' % s, 'short fixed', 'short menu', 'short button', 'short n', '', 'Begin OnActivate',
             '\tif IsActionRef player == 0', '\t\treturn', '\tendif',
             '\tif fixed == 0',
             '\t\tif player.GetActorValue Science >= %d && player.GetItemCount %s >= %d' % (FIX_SCIENCE, PARTS[0], PARTS[1]),
             '\t\t\tplayer.RemoveItem %s %d' % PARTS, '\t\t\tset fixed to 1', '\t\t\t%s.Enable' % marker_edid,
             '\t\t\tShowMessage FOLabGeneratorFixedMsg', '\t\telse', '\t\t\tShowMessage FOLabGeneratorBrokenMsg', '\t\tendif',
             '\telse', '\t\tShowMessage FOLabGeneratorMenuMsg', '\t\tset menu to 1', '\tendif', 'End', '',
             'Begin GameMode', '\tif menu', '\t\tset button to GetButtonPressed', '\t\tif button == -1', '\t\t\treturn', '\t\tendif',
             '\t\tset menu to 0', '\t\tif button == 0']
        for drained, full in CELLS:
            L += ['\t\t\tset n to player.GetItemCount %s' % drained, '\t\t\tif n > 0', '\t\t\t\tplayer.RemoveItem %s n' % drained,
                  '\t\t\t\tif player.GetActorValue Science >= %d' % BONUS_SCIENCE, '\t\t\t\t\tset n to n + n / 2', '\t\t\t\tendif',
                  '\t\t\t\tplayer.AddItem %s n' % full, '\t\t\tendif']
        L += ['\t\t\tShowMessage FOLabGeneratorChargedMsg', '\t\tendif', '\tendif', 'End', '']
        cc = sc.compile('\n'.join(L), skey, 'object', extra)
        if not hasattr(cc, 'subrecords'):
            raise ValueError('the generator\'s script: %s' % (cc,))
        record(skey, sc._record_of(cc, 'FOLabGenerator%sScript' % s))
        acti = {'type': 'ACTI', 'flags': 0, 'src': '', 'subs': [
            {'tag': 'EDID', 'label': 'Editor ID', 'kind': 'z', 'value': 'FOLabGenerator%s' % s},
            {'tag': 'OBND', 'label': 'Bounds', 'kind': 'struct', 'fields': [{'name': n, 'code': 'h', 'value': v} for n, v in
                                                                             zip(('X1', 'Y1', 'Z1', 'X2', 'Y2', 'Z2'), GEN_BOUNDS)]},
            {'tag': 'FULL', 'label': 'Name', 'kind': 'z', 'value': 'Generator'},
            {'tag': 'MODL', 'label': 'Model', 'kind': 'z', 'value': gen_model},
            {'tag': 'SCRI', 'label': 'Script', 'kind': 'F', 'value': skey}]}
        record(akey, acti)
        out.append({'op': 'place', 'cell': cell(mx, my), 'key': _new_key(pr), 'ref': {'base': akey, 'p': [mx, my, mz, 0.0, 0.0, sp['generator'][3]], 's': 1.0}})
        # the lights, off until it runs
        for piece, (x, y, z, rz) in row['lights']:
            pk = _piece(pr, piece)
            if not pk:
                continue
            out.append({'op': 'place', 'cell': cell(x, y), 'key': _new_key(pr), 'ref': {'base': pk, 'p': [x, y, z, 0.0, 0.0, rz], 's': 1.0,
                                                                                    'props': {'parent': dict(parent)}}})
            for light, lx, ly, lz in nightlights.LIGHTS.get(piece, ()):
                out.append({'op': 'place', 'cell': cell(x, y), 'key': _new_key(pr), 'ref': {
                    'base': gd.key(piratedeal._game(gd, light, 'LIGH')), 'p': [x + lx, y + ly, z + lz, 0.0, 0.0, 0.0], 's': 1.0,
                    'props': {'parent': dict(parent)}}})
        # the trader and her chest, the bedroll: off until it runs
        if 'trader' in sp and tfrom:
            npc = json.loads(json.dumps(pr.records[tfrom]))
            npc['src'] = ''
            recordio.set_field(npc, 'EDID', 'FOLabPowerTrader%s' % s, label='Editor ID')
            recordio.set_field(npc, 'FULL', 'Trader') if any(x['tag'] == 'FULL' for x in npc['subs']) else None
            npc['subs'] = [x for x in npc['subs'] if x['tag'] != 'PKID']
            ac.insert(npc, {'tag': 'PKID', 'label': 'AI package', 'kind': 'F', 'value': gd.key(ac._find(gd, 'PACK', WL.STAY))})
            ac.set_num(npc, 'AIDT', 'Services', services)
            ac.set_num(npc, 'ACBS', 'Barter gold', WL.BARTER_GOLD)
            nk = record(_new_key(pr), npc)
            chest = recordio.load(gd, piratedeal._game(gd, CHEST_FROM, 'CONT'))
            chest['src'] = ''
            recordio.set_field(chest, 'EDID', 'FOLabPowerTrader%sChest' % s, label='Editor ID')
            ck = record(_new_key(pr), chest)
            x, y, z, rz = sp['trader']
            cref = _new_key(pr)
            out.append({'op': 'place', 'cell': cell(x, y), 'key': cref, 'ref': {'base': ck, 'p': [x, y, z - 400, 0.0, 0.0, 0.0], 's': 1.0, 'persistent': True}})
            out.append({'op': 'place', 'cell': cell(x, y), 'key': _new_key(pr), 'ref': {'base': nk, 'p': [x, y, z + 4, 0.0, 0.0, rz], 's': 1.0,
                        'persistent': True, 'merchant': cref, 'props': {'parent': dict(parent)}}})
            traders.append(nk)
        if 'bed' in sp:
            x, y, z, rz = sp['bed']
            out.append({'op': 'place', 'cell': cell(x, y), 'key': _new_key(pr), 'ref': {'base': gd.key(piratedeal._game(gd, BED, 'FURN')),
                        'p': [x, y, z, 0.0, 0.0, rz], 's': 1.0, 'props': {'parent': dict(parent)}}})
        rep['sites'][row['site']] = {'generator': sp['generator'], 'lights': len(row['lights']), 'trader': 'trader' in sp, 'bed': 'bed' in sp,
                                     'near': row['near']}
    # the traders' lines (no goodbye: a closing line's script may not run)
    greeting = gd.key(piratedeal._game(gd, 'GREETING', 'DIAL'))
    lines = []
    for nk in traders:
        lines.append(dict(aq.new_line_plain(gd, pr, greeting, quest_key, nk, WORDS['hello']), begin=None, end=None))
        l = aq.new_line_plain(gd, pr, trade_topic, quest_key, nk, WORDS['trade_yes'])
        l['end'] = {'source': 'ShowBarterMenu', 'parts': None}
        lines.append(l)
    rep['lines'] = len(lines)
    return out, rep, lines


def apply(pr, gd, P=None):
    import api_quests as aq
    o, rep, lines = ops(gd, pr, P)
    pr.apply(LABEL, o)
    pr.apply(LABEL, [{'op': 'record_new', 'record': aq._compiled_line(gd, pr, l)} for l in lines], merge=True)
    return rep
