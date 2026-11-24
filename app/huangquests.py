"""Three small quests of the Huáng's (the user's yes, 22 Nov 2026, to the drafts "Silk for Waikiki", "Pests in the Maize",
"Oil for the Gate Guns"; "maybe some speak english and offer some quests, too"). sidequests' shape: someone asks, you do
it, you come back, they give you something; the quest's own script moves every step (StartConversation when you come near,
MenuMode 1009 heard, GetItemCount / GetDead), no line carries a script, no caps.

The askers are three of the Huáng already standing (faces of their own, never one twice), given names of their own in pinyin
(`NAMES`): a Nongmin woman of the courtyards who deals with Waikiki's traders, a Nongmin farmer in the fields, a Shouwei
officer at the courtyards' gate. They speak plain English (they deal with outsiders); the rest of the Huáng Mandarin.

- **Silk for Waikiki** (`SILK`): Lin Meihua gives you a bundle of Huáng silk for Linda Moreno, Waikiki's trader (the silk
  trade goes through her). Linda takes it and gives you a crate of trade goods; Lin Meihua takes that and gives you silk
  clothes of the Huáng's (the gown, or the changshan for a man) and three stimpaks.
- **Pests in the Maize** (`PESTS`): Zhou Lan says creatures are getting into the rows; five of the quest's own (geckos and
  small mantises, placed off and switched on when she asks) are in her field. Kill them, come back: maize from the field and
  ammunition.
- **Oil for the Gate Guns** (`OIL`): Liu Wei says their guns at the gates need care; bring him two Weapon Repair Kits
  (the game's). Sixty 5.56mm rounds, what their rifles take.

`ops(gd, pr, land)` gives (ops, report) for one Undo, keys taken as planned; `lines_to_voice(report)` the lines to voice
once applied; `run_through(source, spec)` plays a quest's script through, frame by frame, on stormsched's interpreter, and
says what stages it reached and what you were given."""
import json
import math

import recordio

NAMES = {'silk': 'Lin Meihua', 'pests': 'Zhou Lan', 'oil': 'Liu Wei'}
ASK_NEAR, BACK_NEAR = 300, 300
RETRY, TRIES, FAR = 6, 3, 1500
LINDA_NPC, LINDA_REF = 'FOLabWaikikiTrader', 'FOLabWaikikiTraderREF'

SILK = {
    'key': 'silk', 'quest': 'FOLabHuangSilk', 'name': 'Silk for Waikiki', 'script': 'FOLabHuangSilkScript',
    'giver_ref': 'FOLabHuangSilkGiverREF', 'topics': ('FOLabSilk1Ask', 'FOLabSilk2Deliver', 'FOLabSilk3Back'),
    'items': {'silk': ('FOLabHuangSilkBundle', 'Bundle of Huang Silk', 'VRRCMisfitsDrugs', 1),
              'goods': ('FOLabHuangTradeGoods', 'Crate of Trade Goods', 'BoxCase556mm', 4)},
    'reward': [('Stimpak', 3)], 'reward_by_sex': ('FOLabSilkGown', 'FOLabChangshan'),
    'words': {
        'ask': "You came through the gate, so the guards allow you. Good. Our silk goes to Waikiki through Linda Moreno, "
               "the trader. Take this bundle to her. She will give you goods in return. Bring them back to me.",
        'deliver': "Silk from the Huang? Good, I've been waiting on it. Here's their side of the deal. Take this crate back to them.",
        'back': "The goods from Linda. Thank you. This is for you: silk of ours, and medicine.",
    },
    'stages': [(10, "Lin Meihua, of the Huang's courtyards, asked me to take a bundle of their silk to Linda Moreno, the trader "
                    "in Waikiki, and bring back what Linda gives in return.", False),
               (20, "Linda Moreno took the silk and gave me a crate of trade goods for the Huang.", False),
               (100, "I brought the trade goods to Lin Meihua. She gave me Huang silk clothes and medicine.", True)],
    'objectives': [(10, "Take the silk to Linda Moreno in Waikiki", 'linda'), (20, "Bring the trade goods to Lin Meihua", 'giver')],
}
PESTS = {
    'key': 'pests', 'quest': 'FOLabHuangPests', 'name': 'Pests in the Maize', 'script': 'FOLabHuangPestsScript',
    'giver_ref': 'FOLabHuangPestsGiverREF', 'topics': ('FOLabPests1Ask', None, 'FOLabPests3Back'),
    'pests': [('LvlGecko', 'FOLabMaizePest1'), ('LvlGecko', 'FOLabMaizePest2'), ('LvlGecko', 'FOLabMaizePest3'),
              ('VSpawnTier1GiantMantisSmall', 'FOLabMaizePest4'), ('VSpawnTier1GiantMantisSmall', 'FOLabMaizePest5')],
    'field_ref': 'FOLabMaizePestField',
    'reward': [('NVFreshMaize', 6), ('Ammo10mm', 40)],
    'words': {
        'ask': "Creatures are getting into the rows. Geckos, and the big insects. They eat the maize. Kill them, and I'll pay "
               "you from the harvest.",
        'back': "The rows are quiet again. Here: maize from the field, and rounds we won't need.",
    },
    'stages': [(10, "Zhou Lan, a farmer of the Huang's, says creatures are getting into her maize. She wants them killed.", False),
               (20, "I killed the creatures in the Huang's maize.", False),
               (100, "I told Zhou Lan her rows are clear. She paid me in maize and ammunition.", True)],
    'objectives': [(10, "Kill the creatures in the Huang's maize", 'field'), (20, "Go back to Zhou Lan", 'giver')],
}
OIL = {
    'key': 'oil', 'quest': 'FOLabHuangOil', 'name': 'Oil for the Gate Guns', 'script': 'FOLabHuangOilScript',
    'giver_ref': 'FOLabHuangOilGiverREF', 'topics': ('FOLabOil1Ask', None, 'FOLabOil3Back'),
    'need': ('NVRepairKit', 2),
    'reward': [('Ammo556mm', 60)],
    'words': {
        'ask': "Our guns at the gates need care, and we run short of what keeps them working. Bring me two weapon repair "
               "kits. You'll be paid in rounds.",
        'back': "Two kits. Good. The guns will hold. Take these rounds: they fit our rifles, and maybe yours.",
    },
    'stages': [(10, "Liu Wei, a Shouwei officer at the Huang's gate, wants two weapon repair kits for their guns.", False),
               (20, "I have two weapon repair kits for Liu Wei.", False),
               (100, "I gave Liu Wei two weapon repair kits. He paid me in 5.56mm rounds.", True)],
    'objectives': [(10, "Find two weapon repair kits", None), (20, "Bring the repair kits to Liu Wei", 'giver')],
}
SPECS = {'silk': SILK, 'pests': PESTS, 'oil': OIL}


# ---------- the scripts ----------

def _talk(who, topic, near, then):
    return ['\t\tif asked == 1 && talked == 1'] + ['\t\t\t' + x for x in then] + [
        '\t\telseif asked == 1',
        '\t\t\tset since to since + GetSecondsPassed',
        '\t\t\tif since > %d' % RETRY,
        '\t\t\t\tset asked to 0',
        '\t\t\tendif',
        '\t\telseif player.GetDistance %s > %d' % (who, FAR),
        '\t\t\tset tries to 0',
        '\t\telseif tries < %d && %s' % (TRIES, near),
        '\t\t\tset asked to 1',
        '\t\t\tset talked to 0',
        '\t\t\tset since to 0',
        '\t\t\tset tries to tries + 1',
        '\t\t\t%s.StartConversation PlayerREF %s' % (who, topic),
        '\t\tendif']


def script_source(spec):
    """`state`: 0 waiting for you near the asker, 2 doing it, 3 back to the asker, 9 done; `asked` a talk asked for,
    `talked` it was shown (MenuMode)."""
    q, giver = spec['quest'], spec['giver_ref']
    ask, deliver, back = spec['topics']
    o = lambda n: 'SetObjectiveDisplayed %s %d 1' % (q, n)
    done = lambda n: 'SetObjectiveCompleted %s %d 1' % (q, n)
    reset = ['set asked to 0', 'set tries to 0']
    on_ask, step, step_talk, have, take = [], None, None, '', []
    if spec['key'] == 'silk':
        silk, goods = spec['items']['silk'][0], spec['items']['goods'][0]
        on_ask = ['player.AddItem %s 1' % silk]
        step_talk = (LINDA_REF, deliver, 'player.GetDistance %s < %d && player.GetItemCount %s > 0' % (LINDA_REF, ASK_NEAR, silk),
                     ['player.RemoveItem %s 1 1' % silk, 'player.AddItem %s 1' % goods])
        have = ' && player.GetItemCount %s > 0' % goods
        take = ['player.RemoveItem %s 1 1' % goods]
    elif spec['key'] == 'pests':
        on_ask = ['%s.Enable' % e for _b, e in spec['pests']]
        step = ' && '.join('%s.GetDead' % e for _b, e in spec['pests'])
    else:
        item, n = spec['need']
        step = 'player.GetItemCount %s >= %d' % (item, n)
        have = ' && player.GetItemCount %s >= %d' % (item, n)
        take = ['player.RemoveItem %s %d 1' % (item, n)]
    advance = ['SetStage %s 20' % q, done(10), o(20), 'set state to 3']
    L = ['scn ' + spec['script'], '',
         "; Made by FOLab (huangquests.py): a quest of the Huang's. See its notes.",
         'short state', 'short asked', 'short talked', 'short tries', 'float since', '',
         'begin GameMode', '',
         '\tif state == 9',
         '\t\treturn',
         '\tendif',
         '\tif %s.GetDead' % giver,
         '\t\tset state to 9',
         '\t\treturn',
         '\tendif',
         '\tif state == 0']
    L += _talk(giver, ask, 'player.GetDistance %s < %d' % (giver, ASK_NEAR),
               on_ask + ['SetStage %s 10' % q, o(10), 'set state to 2'] + reset)
    L += ['\tendif', '', '\tif state == 2']
    if step_talk:
        who, topic, near, then = step_talk
        L += _talk(who, topic, near, then + advance + reset)
    else:
        L += ['\t\tif ' + step] + ['\t\t\t' + x for x in advance + reset] + ['\t\tendif']
    L += ['\t\treturn', '\tendif', '', '\tif state == 3']
    reward = ['player.AddItem %s %d' % (e, n) for e, n in spec['reward']]
    if spec.get('reward_by_sex'):
        f, m = spec['reward_by_sex']
        reward = ['if player.GetIsSex Female', '\tplayer.AddItem %s 1' % f, 'else', '\tplayer.AddItem %s 1' % m, 'endif'] + reward
    L += _talk(giver, back, 'player.GetDistance %s < %d%s' % (giver, BACK_NEAR, have),
               take + reward + [done(20), 'SetStage %s 100' % q, 'set state to 9', 'CompleteQuest %s' % q])
    L += ['\tendif', '', 'end', '',
          'begin MenuMode', '',
          '\tif MenuMode 1009 && asked == 1',
          '\t\tset talked to 1',
          '\tendif', '', 'end', '']
    return '\r\n'.join(L)


# ---------- a run-through ----------

class _Return(Exception):
    pass


class Play:
    """What a quest's script sees, played by a player who does each step when it is asked of them."""

    def __init__(self, spec):
        self.spec = spec
        self.at = None                  # (the ref the player stands by)
        self.items, self.dead, self.on = {}, set(), set()
        self.stage, self.shown, self.completed, self.talks, self.done = 0, set(), set(), [], False
        self.pending = None

    def call(self, name, args, ref):
        n = name.lower()
        if n == 'return':
            raise _Return()
        if n == 'getdistance':
            return 100.0 if self.at == args[0] else 5000.0
        if n == 'getitemcount':
            return self.items.get(args[0], 0)
        if n == 'additem':
            self.items[args[0]] = self.items.get(args[0], 0) + int(float(args[1]))
            return 0
        if n == 'removeitem':
            self.items[args[0]] = self.items.get(args[0], 0) - int(float(args[1]))
            return 0
        if n == 'getdead':
            return 1 if (ref or '').lower() in self.dead else 0
        if n == 'enable':
            self.on.add((ref or '').lower())
            return 0
        if n == 'startconversation':
            self.talks.append((ref, args[1]))
            self.pending = ref
            return 0
        if n == 'setstage':
            self.stage = max(self.stage, int(float(args[1])))
            return 0
        if n == 'setobjectivedisplayed':
            self.shown.add(int(float(args[1])))
            return 0
        if n == 'setobjectivecompleted':
            self.completed.add(int(float(args[1])))
            return 0
        if n == 'completequest':
            self.done = True
            return 0
        if n == 'getsecondspassed':
            return 0.25
        if n == 'getissex':
            return 1 if args[0].lower() == 'female' else 0
        raise ValueError('the run-through doesn\'t know %s' % name)


def run_through(source, spec, frames=400):
    """Plays the script: the player goes to whoever the quest wants next, does what it asks (kills the pests, finds the
    kits), and each talk asked for is shown the next frame. Returns the Play."""
    import stormsched
    for k, v in {'getdistance': 1, 'getitemcount': 1, 'additem': 2, 'removeitem': 3, 'setstage': 2, 'setobjectivedisplayed': 3,
                 'setobjectivecompleted': 3, 'startconversation': 2, 'completequest': 1, 'getissex': 1}.items():
        stormsched._ARGS.setdefault(k, v)
    game_mode = source.split('begin MenuMode')[0]
    s = stormsched.Script(game_mode)
    g = Play(spec)
    for _ in range(frames):
        state = int(s.vars.get('state', 0))
        if state == 0 or state == 3:
            g.at = spec['giver_ref']
        elif state == 2:
            if spec['key'] == 'silk':
                g.at = LINDA_REF
            elif spec['key'] == 'pests':
                g.at = None
                g.dead |= {e.lower() for _b, e in spec['pests'] if e.lower() in g.on}
            else:
                g.at = None
                g.items[spec['need'][0]] = spec['need'][1]
        if g.pending and int(s.vars.get('asked', 0)) == 1:
            s.vars['talked'] = 1            # (MenuMode 1009: the talk is on screen)
            g.pending = None
        try:
            s.frame(g)
        except _Return:
            pass
        if g.done:
            break
    return g


# ---------- where ----------

def _ref_of_npc(pr, edid, near=None):
    npc = next((k for k, r in pr.records.items() if r.get('type') == 'NPC_' and recordio.field(r, 'EDID') == edid), None)
    best = None
    for ck, c in pr.cells.items():
        if ck.startswith('+'):
            continue
        for rk, r in c.get('refs', {}).items():
            if r.get('base') == npc and r.get('p') and not r.get('removed'):
                d = math.hypot(r['p'][0] - near[0], r['p'][1] - near[1]) if near else 0.0
                if best is None or d < best[0]:
                    best = (d, ck, rk, npc, r['p'])
    return best


def givers(gd, pr, land):
    """{quest: (cell, ref, npc key, p)}: a Nongmin woman nearest the courtyards' middle, a farmer, the Shouwei nearest the
    courtyards' gate."""
    mid = land.middle
    out = {}
    pick = lambda stem, sex: min((b for b in (_ref_of_npc(pr, '%s%02d' % (stem, n), mid) for n in range(1, 13)) if b
                                  and (pr.records[b[3]].get('subs') and _female(pr.records[b[3]]) == (sex == 'F'))),
                                 key=lambda b: b[0], default=None)
    for q, stem, sex in (('silk', 'FOLabHuangFolk', 'F'), ('pests', 'FOLabHuangFarmer', 'F'), ('oil', 'FOLabHuangGuard', 'M')):
        b = pick(stem, sex)
        if b is None:
            raise ValueError('no %s to ask for %s' % (stem, q))
        out[q] = b[1:]
    return out


def _female(rec):
    import factionfolk as ff
    return bool(ff._num(rec, 'ACBS', 'Flags') & 0x1)


# ---------- the records ----------

def _persistent(edid):
    import newgame
    return {'type': 'REFR', 'flags': newgame.PERSISTENT, 'subs': [{'tag': 'EDID', 'label': 'Editor ID', 'kind': 'z', 'value': edid}]}


def ops(gd, pr, land, ctx=None):
    """(ops, report) for one Undo: the three quests, their askers named, their things, their lines."""
    import activity
    import api_quests as aq
    import api_scripts
    import questrec as qr
    from castawayquest import _game_form, _named
    for spec in SPECS.values():
        if any(r.get('type') == 'QUST' and recordio.field(r, 'EDID') == spec['quest'] for r in pr.records.values()):
            raise ValueError('the mod already has %s' % spec['quest'])
    ctx = ctx or activity.Ctx(gd, pr)
    key = lambda: activity._new_key(pr)
    who = givers(gd, pr, land)
    linda = _ref_of_npc(pr, LINDA_NPC)
    if linda is None:
        raise ValueError('Linda Moreno (%s) is not placed' % LINDA_NPC)
    out, rep, sc = [], {'quests': {}, 'lines': []}, api_scripts.scripts()
    # Linda's ref named, once
    out.append({'op': 'ref_set', 'cell': linda[1], 'ref': linda[2], 'set': {'edid': LINDA_REF, 'persistent': True}})
    for q, spec in SPECS.items():
        gcell, gref, gnpc, gp = who[q]
        extra = {gref: _persistent(spec['giver_ref']), linda[2]: _persistent(LINDA_REF)}
        # the asker: a name of their own
        rec = json.loads(json.dumps(pr.records[gnpc]))
        full = next((s for s in rec['subs'] if s['tag'] == 'FULL'), None)
        if full is None:
            raise ValueError('%s has no name to change' % recordio.field(rec, 'EDID'))
        full['value'] = NAMES[q]
        out.append({'op': 'record', 'key': gnpc, 'record': rec})
        out.append({'op': 'ref_set', 'cell': gcell, 'ref': gref, 'set': {'edid': spec['giver_ref'], 'persistent': True}})
        targets = {'giver': gref, 'linda': linda[2]}
        for _name, (edid, label, src, _w) in spec.get('items', {}).items():
            k = key()
            item = _named(recordio.load(gd, _game_form(gd, src, 'MISC')), edid, label)
            out.append({'op': 'record', 'key': k, 'record': item})
            extra[k] = item
        if q == 'pests':
            spots = _pest_spots(gd, pr, land, gp, ctx, len(spec['pests']) + 1)
            fx, fy, fz = spots[0]
            fk = key()
            out.append({'op': 'place', 'cell': ctx.cell(fx, fy), 'key': fk,
                        'ref': {'base': ctx.game('STAT', 'XMarkerHeading'), 'p': [fx, fy, fz, 0.0, 0.0, 0.0], 's': 1.0,
                                'persistent': True, 'edid': spec['field_ref']}})
            extra[fk] = _persistent(spec['field_ref'])
            targets['field'] = fk
            for (base, edid), (x, y, z) in zip(spec['pests'], spots[1:]):
                pk = key()
                out.append({'op': 'place', 'cell': ctx.cell(x, y), 'key': pk,
                            'ref': {'base': ctx.game('CREA', base), 'p': [x, y, z + 8, 0.0, 0.0, (x * 0.01) % math.tau], 's': 1.0,
                                    'persistent': True, 'edid': edid, 'props': {'disabled': True}}})
                extra[pk] = _persistent(edid)
        sk, qk = key(), key()
        tk = {t: key() for t in spec['topics'] if t}
        quest = qr.quest_record({'edid': spec['quest'], 'script': sk, 'name': spec['name'], 'flags': {'start_enabled': True},
                                 'priority': 50, 'delay': 0.5,
                                 'stages': [{'index': n, 'entries': [{'flags': {'complete': fin}, 'conditions': [], 'log': log, 'next': ''}]}
                                            for n, log, fin in spec['stages']],
                                 'objectives': [{'index': n, 'text': text, 'targets': ([{'target': targets[t], 'flags': 0, 'conditions': []}] if t else [])}
                                                for n, text, t in spec['objectives']]})
        topics = {t: qr.topic_record({'edid': t, 'name': '', 'priority': 50.0, 'kind': 0, 'quests': [{'quest': qk, 'links': []}]}) for t in tk}
        extra.update({qk: quest})
        extra.update({tk[t]: topics[t] for t in tk})
        src = script_source(spec)
        c = sc.compile(src, sk, 'quest', extra)
        if not hasattr(c, 'subrecords'):
            raise ValueError('%s does not compile: %s' % (spec['script'], c))
        out += [{'op': 'record', 'key': sk, 'record': sc._record_of(c, spec['script'])}, {'op': 'record', 'key': qk, 'record': quest}]
        out += [{'op': 'record', 'key': tk[t], 'record': topics[t]} for t in tk]
        ask, deliver, back = spec['topics']
        for topic, speaker, words in ((ask, gnpc, spec['words']['ask']), (deliver, linda[3], spec['words'].get('deliver')),
                                      (back, gnpc, spec['words']['back'])):
            if not topic:
                continue
            l = aq.new_line_plain(gd, pr, tk[topic], qk, speaker, words, goodbye=True)
            lk = key()
            out.append({'op': 'record', 'key': lk, 'record': qr.info_record(dict(l, begin=None, end=None))})
            rep['lines'].append(lk)
        rep['quests'][q] = {'asker': NAMES[q], 'asker ref': gref, 'script': sk, 'quest': qk, 'source': src}
    return out, rep


def _pest_spots(gd, pr, land, near, ctx, n):
    """A field marker and n-1 spots in the maize nearest `near` (the farmer): open ground with a navmesh."""
    import activity
    import indoors
    maize = []
    for xy, cell in gd.grid(land.world).items():
        if math.hypot((xy[0] + 0.5) * 4096 - near[0], (xy[1] + 0.5) * 4096 - near[1]) > 9000:
            continue
        for _rk, base, p, _s in indoors.placed(gd, pr, gd.key(cell)):
            if indoors._edid(gd, pr, base) in activity.MAIZE:
                maize.append((p[0], p[1]))
    if not maize:
        raise ValueError('no maize near the farmer')
    field = min(activity.clusters(maize, reach=700.0), key=lambda f: min(math.hypot(p[0] - near[0], p[1] - near[1]) for p in f))
    mx, my = sum(p[0] for p in field) / len(field), sum(p[1] for p in field) / len(field)
    got = ctx.around(mx, my, n, radii=(0.1, 250, 450, 650, 850, 1100), turns=10, apart=220.0)
    if len(got) < n:
        raise ValueError('not enough open ground in the field for the pests (%d of %d)' % (len(got), n))
    return got
