"""The An questline's stage 4, By Order of the Palace (the user, 25 Nov 2026: "at the end you shake down the great nobility on
direct orders from the palace"; the Ship-King met in person at the grand palace; betraying the palace an ending of its own;
it may touch the Vault, the houses selling people up the chain; finishing it for the palace, the Huáng accept you fully).
After anquest (stages 1-3) and palacebuild (the palace on Mōkapu).

- **The summons:** once the earls are dealt with for the palace, Fang Jun sends you to the palace on Mōkapu.
- **The Ship-King** [proposal: the Chuanwang, the founder's heir], standing before the throne in the Hall of Supreme
  Peace with two palace guards, gives you his order: bring the Duke of Kāneʻohe to heel. The founder's will is sealed at
  the freighter's shrine: the elder there (huangstanding's FOLabHuangElder01) seals the order, and the Sealed Order is
  yours to show.
- **The Duke of Kāneʻohe** [proposal: the Song house], at his hall with his engineer and his strongbox. Ways:
  - persuade him with the sealed order (Speech `D_SPEECH`, eased for an Asian player character and Island Tongue);
  - shame him with the Vault-Tec receipt under his own seal (his house sells people up the chain to the Vault: in his
    strongbox, Lockpick `D_LOCK`);
  - buy him with a seat at court (Barter `D_BARTER`);
  - his engineer cuts the estate's generator (Science `D_SCI`) or blows his storehouse (Explosives `D_BOOM`): then he
    submits without a check;
  - kill him;
  - or stand with the houses against the palace (the betrayal).
- **Endings:** back to the Ship-King. The Duke brought in line or dead: the palace accepts you fully, you join the Huáng
  (FOLabHuangFaction) as a guest of the palace whose name the elders write in the clan register, Huáng fame and face.
  The betrayal: the palace (its guards and the Ship-King, FOLabAnPalaceFaction) turns on you, Huáng infamy, pirate fame,
  the houses pay; the Huáng never accept you.

    plan(gd, pr)       {'rows', 'skipped', 'spots'}
    apply(pr, gd, P)   one Undo
"""
import json
import math

import recordio

import anquest as AQ

LABEL = "The An questline: By Order of the Palace"
Q4 = 'FOLabAnByOrder'
VOICE = [Q4, AQ.COURT]
ZH = {}
D_SPEECH, D_BARTER, D_LOCK, D_SCI, D_BOOM = 75, 65, 75, 70, 70
PALACE_FACTION = ('FOLabAnPalaceFaction', 'The An Palace')
ELDER = 'FOLabHuangElder01'
THRONE = 'FOLabAnThroneHall'

M = {
    'king_hi': ("So you are the barbarian the clerks speak of. Kneel, or stand. Either way, listen.", "Nǐ jiùshì shūlì shuō de mánzi. Guì huò zhàn, tīng zhe."),
    'king_order': ("The Duke of Kane'ohe sells my people. Bring him to heel. The elders seal it.", "Gōngjué mài wǒ de rénmín. Ràng tā fúcóng. Zhǎnglǎo gài yìn."),
    'king_wait': ("The Duke still defies me. Go.", "Gōngjué hái zài kàngmìng. Qù."),
    'king_done': ("Done. You are the palace's guest now. Your name goes in the register.", "Wánchéng le. Nǐ shì gōngtíng de kèrén. Míngzì rù pǔ."),
    'king_betrayed': ("You sold me to the houses. Guards!", "Nǐ bǎ wǒ mài gěi le háomén. Wèibīng!"),
    'guard_hi': ("The palace. Mind your manners, barbarian.", "Gōngtíng. Zhùyì lǐmào, mánzi."),
    'elder_seal': ("The founder's seal, on the king's word. Carry it with care.", "Shǐzǔ de yìn, gài zài wáng de mìnglìng shàng. Xiǎoxīn ná zhe."),
    'duke_hi': ("A barbarian, with the palace's stink on him. Say what you came to say.", "Yī gè mánzi, yī shēn gōngtíng de wèidào. Shuō ba."),
    'duke_speech': ("[SUCCEEDED] ...The founder's own seal. Very well. My house will answer to the palace.", "Shǐzǔ de yìn. Hǎo ba. Wǒ jiā tīng gōngtíng de."),
    'duke_speech_no': ("[FAILED] Seals are wax. The pirates pay in medicine. Go home.", "Yìn shì là. Hǎidào gěi yào. Huí qù ba."),
    'duke_receipt': ("Where did you... Burn it. Burn it, and my house kneels to the palace.", "Nǐ cóng nǎlǐ... Shāo le tā. Wǒ jiā xiàng gōngtíng guìxià."),
    'duke_barter': ("[SUCCEEDED] A seat at court, and my debts forgiven? Then I am the king's man.", "Cháotíng de zuòwèi, zhài yě miǎn le? Nà wǒ shì wáng de rén."),
    'duke_barter_no': ("[FAILED] The palace has nothing I want.", "Gōngtíng méiyǒu wǒ yào de."),
    'duke_ruined': ("My power, my stores... gone. Tell the king I yield.", "Wǒ de diàn, wǒ de cāngkù... méi le. Gàosù wáng, wǒ fú le."),
    'duke_join': ("Good. The houses remember their friends. Take this, and tell the king nothing.", "Hǎo. Háomén jì de péngyǒu. Ná zhe, shénme yě bié gàosù wáng."),
    'eng_hi': ("The Duke's generator. Don't touch anything.", "Gōngjué de fādiànjī. Bié luàn pèng."),
    'eng_sci': ("[SUCCEEDED] The governor's shot. That's... the whole estate's dark.", "Tiáojiéqì huài le. Zhěng gè zhuāngyuán dōu hēi le."),
    'eng_sci_no': ("[FAILED] You don't know what you're doing. Get out.", "Nǐ bù dǒng. Chūqù."),
    'eng_boom': ("[SUCCEEDED] Run! ...The storehouse. Everything he had in it.", "Kuài pǎo! ...Cāngkù. Tā suǒyǒu de dōngxī."),
    'eng_boom_no': ("[FAILED] Put that down before you kill us both.", "Fàng xià, bùrán wǒmen dōu huì sǐ."),
}
W = {
    'fang_call': "The palace calls you. Mokapu. The Ship-King himself. Go.",
    'seal': "The king bids you seal his order.",
    'speech': "The founder's seal. The king's word. Answer to the palace.",
    'receipt': "Your seal is on this Vault-Tec receipt. People, sold up the mountain.",
    'barter': "The palace offers a seat at court, and your debts forgiven.",
    'yield': "Your power and your stores are gone. Yield.",
    'join': "I'll stand with the houses, not the palace.",
    'report': "The Duke answers to the palace now.",
    'report_dead': "The Duke of Kane'ohe is dead.",
    'cut': "Your generator's governor looks worn. Let me see.",
    'boom': "That storehouse would burn nicely.",
}
SAID_BY = {'king': 'The Ship-King', 'guard': 'Palace Guard', 'duke': "Duke of Kane'ohe", 'eng': "The Duke's Engineer"}
EDIDS = {'king': 'FOLabAnShipKing', 'guard': 'FOLabAnPalaceGuard', 'duke': 'FOLabAnDuke', 'eng': 'FOLabAnDukeEngineer'}


def shown(k):
    import huangland
    english, pinyin = M[k]
    tag = ''
    for t in ('[SUCCEEDED] ', '[FAILED] '):
        if english.startswith(t):
            tag, english = t, english[len(t):]
    return tag + huangland.shown(english, pinyin)


def _zh():
    for k, (_e, pinyin) in M.items():
        ZH[shown(k)] = pinyin


try:
    _zh()
except Exception:
    pass


def _throne(pr):
    """(x, y, z, cell) of the throne hall the palace step stood, or None."""
    key = AQ._mod_key(pr, THRONE, 'STAT')
    for ck, c in pr.cells.items():
        for rk, r in (c.get('refs') or {}).items():
            if r.get('base') == key and not r.get('removed') and r.get('p'):
                return r['p'][0], r['p'][1], r['p'][2], ck
    return None


def plan(gd, pr):
    W_ = AQ.Where(gd, pr)
    rows, skipped, S = [], [], {}
    th = _throne(pr)
    if not th:
        return {'rows': [], 'skipped': ['no palace (palacebuild first)'], 'spots': {}}
    x, y, z = th[:3]
    zf = z + 3 * 110 + 20
    S['king'] = (x, y + 120.0, zf)                             # (before the throne, on the hall's floor)
    S['guard0'] = (x - 650.0, y - 300.0, zf)
    S['guard1'] = (x + 650.0, y - 300.0, zf)
    for k in ('king', 'guard0', 'guard1'):
        rows.append({'what': k, 'p': [round(v) for v in S[k]]})
    kane = W_.mk.get("Kane'ohe")
    earls = [p for e, p in W_.named if e.startswith('FOLabAnEarl')]
    hall = None
    if kane:
        hs = [h for h in W_.halls if math.hypot(h[0] - kane[0], h[1] - kane[1]) <= 12000 and all(math.hypot(h[0] - q[0], h[1] - q[1]) >= 2500 for q in earls)]
        hall = max(hs, key=lambda h: min((math.hypot(h[0] - q[0], h[1] - q[1]) for q in W_.people), default=1e9), default=None)
    if hall:
        for k, radii, thing in (('duke', (250, 350, 450, 600, 800, 1000), False), ('eng', (700, 900, 1100, 1300), False), ('box', (300, 450, 600, 800), True)):
            s = W_.near(hall[0], hall[1], radii=radii, thing=thing)
            if s:
                S[k] = s
                rows.append({'what': k, 'p': [round(v) for v in s], 'clear': W_.clear(s, False, thing)[1]})
            else:
                skipped.append(k)
    else:
        skipped += ['duke', 'eng', 'box']
    return {'rows': rows, 'skipped': skipped, 'spots': S, 'world': W_.ctx.world}


def _faction(gd, pr):
    """The palace's own (the Ship-King and his guards), allied to the Huáng, killing them infamy with the Huáng."""
    import factionfolk as ff
    import piratedeal
    fac = ff._faction(gd, *PALACE_FACTION)
    huang = AQ._mod_key(pr, 'FOLabHuangFaction', 'FACT')
    if huang:
        fac['subs'].insert(2, {'tag': 'XNAM', 'label': 'Relation', 'kind': 'struct', 'fields': [
            {'name': 'Faction', 'code': 'F', 'value': huang}, {'name': 'Modifier', 'code': 'i', 'value': 0},
            {'name': 'Group combat reaction', 'code': 'I', 'value': 2}]})
    rep = AQ._mod_key(pr, piratedeal.REPS['huang'][0], 'REPU')
    if rep:
        fac['subs'].append({'tag': 'WMI1', 'label': 'Reputation', 'kind': 'F', 'value': rep})
    return fac


def ops(gd, pr, P=None):
    import piratedeal
    import questrec as qr
    import repstanding as RS
    import tes4
    from activity import _new_key
    if AQ._mod_key(pr, Q4, 'QUST'):
        raise ValueError('the mod already has %s (Undo first)' % Q4)
    if not AQ._mod_key(pr, AQ.Q3, 'QUST'):
        raise ValueError('the An questline (anquest) first')
    P = P or plan(gd, pr)
    S = P['spots']
    missing = [k for k in ('king', 'guard0', 'guard1', 'duke', 'eng', 'box') if k not in S]
    if missing:
        raise ValueError('no spot for: %s' % ', '.join(missing))
    huang_fac = AQ._mod_key(pr, 'FOLabHuangFaction', 'FACT')
    world = P['world']
    grid = gd.grid(world if not isinstance(world, str) else gd.from_key(world))
    cell = lambda x, y: gd.key(grid[(int(x // 4096), int(y // 4096))])
    out, rep, named = [], {'made': [], 'skipped': P['skipped'], 'recast': {}}, {}

    def record(rec, k=None):
        k = k or _new_key(pr)
        out.append({'op': 'record', 'key': k, 'record': rec})
        rep['made'].append(recordio.field(rec, 'EDID'))
        return k

    def place(base, s, edid, props=None):
        k = _new_key(pr)
        ref = {'base': base, 'p': [s[0], s[1], s[2] + 4.0, 0.0, 0.0, 0.0], 's': 1.0, 'persistent': True, 'edid': edid}
        if props:
            ref['props'] = props
        named[k] = edid
        out.append({'op': 'place', 'cell': cell(s[0], s[1]), 'key': k, 'ref': ref})
        return k
    # the palace's own faction (the king and his guards: what the betrayal turns on you)
    import api_characters as ac
    pf = record(_faction(gd, pr))
    receipt = record(AQ._item(gd, pr, 'FOLabAnVaultReceipt', 'Vault-Tec Receipt (Huang seal)'))
    order = record(AQ._item(gd, pr, 'FOLabAnSealedOrder', "The Ship-King's Sealed Order"))
    box = record(AQ._chest(gd, pr, 'FOLabAnDukeStrongbox', receipt))
    pool = AQ._standing(gd, pr)
    ctx = AQ._faces(gd, pr)
    people = {}
    sexes = {'king': 'M', 'guard0': 'M', 'guard1': 'M', 'duke': 'M', 'eng': 'F'}
    for k in ('king', 'guard0', 'guard1', 'duke', 'eng'):
        role = k[:-1] if k.startswith('guard') else k
        if role == 'guard':
            got = _recast_shouwei(gd, pr, pool, S[k])
        elif role in ('king', 'duke') and not _has(pool, 'Nongmin', 'M'):
            got = _recast_shouwei(gd, pr, pool, S[k], 'M')          # (no Nongmin man left: a Shouwei man, out of his armour into silk)
            if got:
                got = (got[0], _silk(gd, pr, got[1]), got[2])
        else:
            got = AQ._recast(gd, pr, pool, 'gao' if role in ('king', 'duke') else 'steward', S[k], sexes[k])
        if got:
            key, rec, (ck, rk) = got
            recordio.set_field(rec, 'FULL', SAID_BY[role])
            out.append({'op': 'remove', 'cell': ck, 'ref': rk})
            out.append({'op': 'record', 'key': key, 'record': rec})
            people[k] = key
            rep['recast'][k] = recordio.field(rec, 'EDID')
        else:
            people[k] = record(AQ._huang(gd, pr, ctx, '%s%s' % (EDIDS[role], k[-1] if role == 'guard' else ''), SAID_BY[role],
                                         'gao' if role in ('king', 'duke') else 'steward', sexes[k], huang_fac))
        if role in ('king', 'guard'):                       # (the palace's own: they turn on a traitor)
            r = next(o['record'] for o in out if o['op'] == 'record' and o['key'] == people[k])
            ac.insert(r, _snam(pr, r, pf))
    refs = {}
    for k in ('king', 'guard0', 'guard1', 'duke', 'eng'):
        refs[k] = place(people[k], S[k], 'FOLabAn%sRef' % {'king': 'ShipKing', 'guard0': 'PalaceGuard0', 'guard1': 'PalaceGuard1',
                                                              'duke': 'Duke', 'eng': 'DukeEngineer'}[k])
    refs['box'] = place(box, S['box'], 'FOLabAnDukeStrongboxRef', {'lock': {'level': D_LOCK, 'key': '', 'leveled': False}})
    actors = set(people.values())
    ext = {o['key']: {'type': 'ACHR' if o['ref']['base'] in actors else 'REFR', 'flags': tes4.PERSISTENT,
                      'subs': [{'tag': 'EDID', 'label': 'Editor ID', 'kind': 'z', 'value': o['ref']['edid']}]}
           for o in out if o['op'] == 'place'}
    B = AQ.Built()
    B.people, B.receipt, B.order, B.pf, B.ext = people, receipt, order, pf, ext
    B.key, B.skey = _new_key(pr), _new_key(pr)
    return out, rep, B


def _snam(pr, rec, fac):
    import copy
    s = next((x for x in rec['subs'] if x['tag'] == 'SNAM'), None)
    if s is None:
        raise ValueError('a palace person has no faction to copy')
    s = copy.deepcopy(s)
    for f in s.get('fields', ()):
        if 'faction' in f.get('name', '').lower():
            f['value'] = fac
    if 'value' in s:
        s['value'] = fac
    return s


def _fem(p):
    import factionfolk as ff
    return bool(ff._num(p[1], 'ACBS', 'Flags') & 1)


def _has(pool, full, sex):
    return any(recordio.field(p[1], 'FULL') == full and _fem(p) == (sex == 'F') for p in pool)


def _silk(gd, pr, rec):
    """A record's armour and weapons taken out of its things, the silk gown in."""
    import api_characters as ac
    import factionfolk as ff
    import sidequests

    def worn(s):
        if s['tag'] != 'CNTO':
            return False
        item = next((f.get('value') for f in s.get('fields', ()) if f.get('name') == 'Item'), '')
        r = pr.records.get(item) if str(item).startswith('+') else None
        tag = (r or {}).get('type') if r else AQ.gd_tag(gd, item)
        return tag in ('ARMO', 'WEAP')
    rec['subs'] = [s for s in rec['subs'] if not worn(s)]
    try:
        ac.insert(rec, sidequests._cnto(gd, ff._item(gd, pr, 'FOLabSilkGown'), 1))
    except Exception:
        pass
    return rec


def _recast_shouwei(gd, pr, pool, spot, sex=None):
    """A Shouwei of the pool (a soldier stays a soldier, but for a man's part no Nongmin is left for), nearest the spot."""
    fit = [p for p in pool if recordio.field(p[1], 'FULL') == 'Shouwei' and (sex is None or _fem(p) == (sex == 'F'))]
    if not fit:
        return None
    best = min(fit, key=lambda p: math.hypot(p[4][0] - spot[0], p[4][1] - spot[1]))
    pool.remove(best)
    key, rec, ck, rk, _xy = best
    return key, json.loads(json.dumps(rec)), (ck, rk)


def q4_script():
    return '\n'.join([
        'scn FOLabAnByOrderScript', 'short started', 'short sealed', 'short receipt', 'short ruined', 'short betrayed', 'short turned', '',
        'Begin GameMode',
        '\tif GetStage %s >= 10' % Q4, '\t\tif GetStage %s < 30' % Q4, '\t\t\tif FOLabAnDukeRef.GetDead == 1',
        '\t\t\t\tSetStage %s 32' % Q4, '\t\t\tendif', '\t\tendif', '\tendif',
        '\tif betrayed == 1', '\t\tif turned == 0', '\t\t\tset turned to 1', '\t\t\tSetEnemy %s PlayerFaction' % PALACE_FACTION[0],
        '\t\tendif', '\tendif',
        'End', ''])


def _plain(gd, pr, B, key_script):
    import piratedeal
    import repstanding as RS
    rep = piratedeal.REPS['huang'][0]
    has_rep = bool(AQ._mod_key(pr, rep, 'REPU'))
    prep = piratedeal.REPS['pirates'][0]
    has_prep = bool(AQ._mod_key(pr, prep, 'REPU'))
    obj = lambda n, on: 'SetObjectiveDisplayed %s %d %d\n' % (Q4, n, on)
    done = lambda n: 'SetObjectiveCompleted %s %d 1\n' % (Q4, n)

    def stage(n, log, src=''):
        return {'index': n, 'entries': [{'flags': {}, 'conditions': [], 'next': '', 'log': log, 'script': {'source': src, 'parts': None}}]}
    end = obj(10, 0) + obj(20, 0) + obj(30, 0)
    join = '\nplayer.AddToFaction FOLabHuangFaction 0\n' if AQ._mod_key(pr, 'FOLabHuangFaction', 'FACT') else '\n'
    accepted = ('AddReputation %s 1 3\n' % rep if has_rep else '') + RS.bump('huang', 15) + join + \
        'set %s.palace to %s.palace + 1\nplayer.AddItem Stimpak 5\n' % (AQ.COURT, AQ.COURT)
    stages = [
        stage(5, "Fang Jun says the palace calls me: the Ship-King himself, at Mokapu.", obj(5, 1)),
        stage(10, "The Ship-King ordered me to bring the Duke of Kane'ohe to heel. The elders at the freighter's shrine are to seal his order.",
              done(5) + obj(10, 1) + obj(20, 1)),
        stage(20, "The elder sealed the Ship-King's order with the founder's seal.", done(10) + 'player.AddItem FOLabAnSealedOrder 1\n'),
        stage(30, "The Duke of Kane'ohe answers to the palace now. The Ship-King will want to hear it.", done(20) + obj(30, 1)),
        stage(32, "The Duke of Kane'ohe is dead. The Ship-King will want to hear it.", obj(20, 0) + obj(30, 1)),
        stage(34, "I stood with the houses against the palace. The Duke paid me, and the palace will remember.",
              end + obj(5, 0) + 'set %s.betrayed to 1\n' % Q4 + ('AddReputation %s 0 3\n' % rep if has_rep else '') + RS.bump('huang', -15) + '\n' +
              ('AddReputation %s 1 2\n' % prep if has_prep else '') + 'player.AddItem Stimpak 6\nplayer.AddItem WaterPurified 4\n' +
              'set %s.nobles to %s.nobles + 1\n' % (AQ.COURT, AQ.COURT)),
        stage(100, "The Ship-King named me a guest of the palace, and the elders write my name in the clan register. The Huang accept me.",
              end + accepted),
    ]
    objectives = [{'index': 5, 'text': "Go to the Ship-King at the palace on Mokapu", 'targets': []},
                  {'index': 10, 'text': "Have the elders at the freighter seal the Ship-King's order", 'targets': []},
                  {'index': 20, 'text': "Bring the Duke of Kane'ohe to heel", 'targets': []},
                  {'index': 30, 'text': "Tell the Ship-King", 'targets': []}]
    return {'edid': Q4, 'name': 'By Order of the Palace', 'script': key_script, 'flags': {'start_enabled': True}, 'priority': 55,
            'delay': 1.0, 'stages': stages, 'objectives': objectives, 'conditions': []}


def apply(pr, gd, P=None):
    import api_quests as aq
    import api_scripts
    import questrec as qr
    from activity import _new_key
    o, rep, B = ops(gd, pr, P)
    plain = _plain(gd, pr, B, B.skey)
    stub = qr.quest_record(dict(plain, stages=[], objectives=[]))
    known = dict(B.ext, **{B.key: stub})
    known.update({x['key']: x['record'] for x in o if x['op'] == 'record'})
    sc = api_scripts.scripts()
    c = sc.compile(q4_script(), B.skey, 'quest', known)
    if not hasattr(c, 'subrecords'):
        raise ValueError('%sScript: %s' % (Q4, c))
    srec = sc._record_of(c, '%sScript' % Q4)
    o += [{'op': 'record', 'key': B.skey, 'record': srec}, {'op': 'record', 'key': B.key, 'record': stub}]
    rep['made'] += ['%sScript' % Q4, Q4]
    T, lines = _lines(gd, pr, B, srec)
    o += [{'op': 'record', 'key': k, 'record': r} for k, r in T]
    rep['made'] += [recordio.field(r, 'EDID') for _k, r in T]
    pr.apply(LABEL, o)
    full = json.loads(json.dumps(plain))
    errors = aq.compile_quest(full, aq.ModForms(gd, pr))
    if errors:
        raise ValueError('%s: %s' % (Q4, errors))
    pr.apply(LABEL, [{'op': 'record', 'key': B.key, 'record': qr.quest_record(full)}] +
             [{'op': 'record_new', 'record': aq._compiled_line(gd, pr, l)} for l in lines], merge=True)
    rep.update({'lines': len(lines), 'people': len(B.people), 'named': sorted(v['subs'][0]['value'] for v in B.ext.values())})
    return rep


def _lines(gd, pr, B, srec):
    import api_quests as aq
    import questrec as qr
    from activity import _new_key
    G = qr.GREETING
    recs, lines, T = [], [], {}
    av = {s: gd.key(next(f for f, (i, r) in gd.forms.items() if r.tag == 'AVIF' and gd.edid(f) == e)) for s, (_n, e) in AQ.SKILLS.items()}
    asian = gd.key(next(f for f, (i, r) in gd.forms.items() if r.tag == 'RACE' and gd.edid(f) == 'Asian'))
    tongue = AQ._mod_key(pr, AQ.TONGUE, 'PERK')
    court = AQ._mod_key(pr, AQ.COURT, 'QUST')
    q3 = AQ._mod_key(pr, AQ.Q3, 'QUST')
    V = AQ._vars(srec)
    qv = lambda var, op, v: AQ._cond('GetQuestVariable', op, v, B.key, V[var])
    st = lambda op, v, q=None: AQ._cond('GetStage', op, v, q or B.key)
    sk = lambda s, op, v: AQ._cond('GetActorValue', op, v, AQ.SKILLS[s][0], 0, 1)
    has = lambda item: AQ._cond('GetItemCount', '>=', 1, item, 0, 1)

    def topic(name, words):
        if name not in T:
            k = _new_key(pr)
            recs.append((k, qr.topic_record({'edid': 'FOLabAnTopic%s' % name, 'name': words, 'priority': 50.0, 'kind': 0,
                                             'quests': [{'quest': B.key, 'links': []}, {'quest': court, 'links': []}]})))
            T[name] = k
        return T[name]

    def line(tp, who, words, conds=(), end='', skill=None, choices=(), q=None):
        l = aq.new_line_plain(gd, pr, tp, q or B.key, who, words, conditions=list(conds))
        if skill:
            l['skill'] = av[skill]
        if end:
            l['end'] = {'source': end, 'parts': None}
        l['choices'] = list(choices)
        lines.append(l)

    def check(tp, who, skill, need, passed, failed, on_pass='', conds=()):
        line(tp, who, passed, [sk(skill, '>=', need)] + list(conds), on_pass, skill)
        if skill in AQ.EASED:
            line(tp, who, passed, [sk(skill, '>=', need - AQ.EASIER), AQ._cond('GetIsRace', '=', 1, asian, 0, 1)] + list(conds), on_pass, skill)
            if tongue:
                line(tp, who, passed, [sk(skill, '>=', need - AQ.EASIER), AQ._cond('HasPerk', '=', 1, tongue, 0, 1)] + list(conds), on_pass, skill)
        line(tp, who, failed, list(conds), '', skill)
    stage = lambda n: 'SetStage %s %d' % (Q4, n)
    P = B.people
    fang = AQ._mod_key(pr, AQ.EDIDS['fang'], 'NPC_') or next((k for k, r in pr.records.items() if r.get('type') == 'NPC_' and recordio.field(r, 'FULL') == 'Fang Jun'), None)
    if fang:                                                # (the summons, after the earls for the palace)
        line(G, fang, W['fang_call'], [st('>=', 30, q3), st('<', 38, q3), st('=', 0)], stage(5), q=B.key)
    king = P['king']
    line(G, king, shown('king_betrayed'), [qv('betrayed', '=', 1)])
    line(G, king, shown('king_order'), [st('=', 5)], stage(10))
    t_rep, t_dead = topic('Report', W['report']), topic('ReportDead', W['report_dead'])
    line(G, king, shown('king_wait'), [st('>=', 10), st('<', 30)])
    line(G, king, shown('king_hi'), [st('>=', 30), st('<', 34)], choices=[t_rep, t_dead])
    line(t_rep, king, shown('king_done'), [st('=', 30)], stage(100))
    line(t_dead, king, shown('king_done'), [st('=', 32)], stage(100))
    line(G, king, shown('king_hi'), [])
    for g in ('guard0', 'guard1'):
        line(G, P[g], shown('guard_hi'), [])
    elder = AQ._mod_key(pr, ELDER, 'NPC_')
    if elder:
        t_seal = topic('Seal', W['seal'])
        line(t_seal, elder, shown('elder_seal'), [st('=', 10)], stage(20))
        line(G, elder, shown('elder_seal'), [st('=', 10)], stage(20))
    duke = P['duke']
    t_sp, t_rc, t_bt, t_yl, t_jn = (topic('DukeSpeech', W['speech']), topic('DukeReceipt', W['receipt']), topic('DukeBarter', W['barter']),
                                    topic('DukeYield', W['yield']), topic('DukeJoin', W['join']))
    open4 = [st('>=', 10), st('<', 30)]
    line(G, duke, shown('duke_hi'), open4, choices=[t_sp, t_rc, t_bt, t_yl, t_jn])
    check(t_sp, duke, 'Speech', D_SPEECH, shown('duke_speech'), shown('duke_speech_no'), stage(30), conds=[st('=', 20), has(B.order)])
    line(t_rc, duke, shown('duke_receipt'), open4 + [has(B.receipt)], stage(30) + '\nplayer.RemoveItem FOLabAnVaultReceipt 1')
    check(t_bt, duke, 'Barter', D_BARTER, shown('duke_barter'), shown('duke_barter_no'), stage(30), conds=open4)
    line(t_yl, duke, shown('duke_ruined'), open4 + [qv('ruined', '=', 1)], stage(30))
    line(t_jn, duke, shown('duke_join'), open4, stage(34))
    eng = P['eng']
    t_cut, t_boom = topic('Cut', W['cut']), topic('Boom', W['boom'])
    line(G, eng, shown('eng_hi'), open4 + [qv('ruined', '=', 0)], choices=[t_cut, t_boom])
    check(t_cut, eng, 'Science', D_SCI, shown('eng_sci'), shown('eng_sci_no'), 'set %s.ruined to 1' % Q4, conds=open4)
    check(t_boom, eng, 'Explosives', D_BOOM, shown('eng_boom'), shown('eng_boom_no'), 'set %s.ruined to 1' % Q4, conds=open4)
    return recs, lines
