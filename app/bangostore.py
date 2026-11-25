"""Baron Tan's house store and his bango tags (money.py's tags; the user's money decision, 25 Nov 2026; the house and the
clue agreed with the An questline's session: "Tan's house, yes ... a tag with his number left where one was sold points
back at him").

- **The store** (a Huáng storekeeper of his own, Zhanggui [proposal: "shopkeeper"], by Tan's hall in Waimānalo): sells
  staples to the house's farmers from a buried merchant chest (`STOCK`). "Let's trade." in kala, "Pay in bango tags."
  at `money.RATES['bango']` (money.trade_in: the tags spend only here). "What are these tags?" tells what they are.
- **The clue:** tags numbered as the model shows (No 147) lie on the sand where Tan's man meets the pirate buyer
  (FOLabAnHandoverRef), a few are in Tan's locked chest beside his tally book, and his sick tenant carries some. Shown a
  tag, the storekeeper may say whose number it was ("[Speech 40] This tag was on the beach. Whose number?"): a farmer of
  Tan's who "ran". No stage reads the tags (the quest's proof is anquest's).
- **Where** (`_keeper_spot`): over a navmesh round the courtyard before Tan's hall, `DOOR_CLEAR` from every door,
  `PEOPLE_CLEAR` from Tan and the tenant, clear of anyone standing; tags on the sand by lootplace.Seat (on the land,
  never in water).

    plan(gd, pr)       {'rows', 'skipped'}
    apply(pr, gd, P)   one Undo (VOICE, VOICE_ONLY: the new lines)
"""
import json
import math

import recordio

LABEL = "Baron Tan's house store and bango tags"
VOICE = ['FOLabMoney']
VOICE_ONLY = set()
TAN, TENANT, CHEST, HANDOVER = 'FOLabAnBaronTanRef', 'FOLabAnTanTenantRef', 'FOLabAnTanChestRef', 'FOLabAnHandoverRef'
KEEPER = ('FOLabTanStorekeeper', 'Zhanggui')
STORE_CHEST = 'FOLabTanStoreChest'
STOCK = [('NVFreshMaize', 8), ('NVFreshBananaYuccaFruit', 6), ('Flour', 3), ('WaterPurified', 6), ('NVHealingPowder', 2)]
DOOR_CLEAR, PEOPLE_CLEAR, OTHERS_CLEAR = 450.0, 300.0, 200.0
SAND_TAGS, CHEST_TAGS, TENANT_TAGS = 2, 6, 3
SAND_FROM = (140.0, 260.0)               # (tags lie this far from the handover marker, on the sand)
CLUE_SPEECH = 40
WORDS = {
    'hello': "Baron Tan's store. Tags, or kala.",
    'trade': "Let's trade.", 'trade_yes': "Look. Rice is gone. Maize, flour, water.",
    'tags': "Pay in bango tags.", 'tags_yes': "Tags. Five kala each, in this store. Nowhere else.",
    'what': "What are these tags?",
    'what_yes': "Bango. Every worker has a number. Baron pays the farmers in tags. Tags buy here. Outside this wall, a tag is nothing.",
    'clue': "This tag was on the beach. Whose number?",
    'clue_yes': "...One four seven. Wen. East field. Baron says he ran. Ran where? Into the sea? Do not say I told you.",
    'clue_no': "Many tags. Many numbers. Buy something, or go.",
}


def _refs(pr, edids):
    out = {}
    for ck, c in pr.cells.items():
        for rk, r in (c.get('refs') or {}).items():
            if r.get('edid') in edids and not r.get('removed'):
                out[r['edid']] = (ck, rk, r)
    return out


def _keeper_spot(gd, pr, rep, tan, tenant):
    import activity
    import money
    ctx = activity.Ctx(gd, pr)
    doors, people = [], []
    for ck, c in pr.cells.items():
        if ck.startswith('+'):
            continue
        for _rk, r in (c.get('refs') or {}).items():
            if r.get('removed') or not r.get('p') or not r.get('base'):
                continue
            if math.hypot(r['p'][0] - tan[0], r['p'][1] - tan[1]) > 3000:
                continue
            t = money._type_of(gd, pr, r['base'])
            if t == 'DOOR':
                doors.append(r['p'])
            elif t in ('NPC_', 'CREA', 'LVLN', 'LVLC'):
                people.append(r['p'])
    halls = [p for p in ctx.of('FOLabHuangHall') if math.hypot(p[0] - tan[0], p[1] - tan[1]) < 1500]
    centre = ((tan[0] + halls[0][0]) / 2, (tan[1] + halls[0][1]) / 2) if halls else tan[:2]
    for r in (0, 150, 300, 450, 600, 800):
        for k in range(12 if r else 1):
            a = k * 2 * math.pi / 12
            x, y = centre[0] + r * math.sin(a), centre[1] + r * math.cos(a)
            if any(math.hypot(x - d[0], y - d[1]) < DOOR_CLEAR for d in doors):
                continue
            if math.hypot(x - tan[0], y - tan[1]) < PEOPLE_CLEAR or math.hypot(x - tenant[0], y - tenant[1]) < PEOPLE_CLEAR:
                continue
            if any(math.hypot(x - q[0], y - q[1]) < OTHERS_CLEAR for q in people):
                continue
            s = ctx.spot(x, y, OTHERS_CLEAR)
            if s:
                rz = math.atan2(tan[0] - s[0], tan[1] - s[1])              # (facing the courtyard, toward Tan)
                return {'p': [s[0], s[1], s[2], rz], 'cell': ctx.cell(s[0], s[1]),
                        'from_door': round(min((math.hypot(s[0] - d[0], s[1] - d[1]) for d in doors), default=99999)),
                        'from_tan': round(math.hypot(s[0] - tan[0], s[1] - tan[1])),
                        'from_tenant': round(math.hypot(s[0] - tenant[0], s[1] - tenant[1])),
                        'from_hall': round(math.hypot(s[0] - halls[0][0], s[1] - halls[0][1])) if halls else None}
    rep['skipped'].append(('keeper', 'no clear navmeshed ground round Tan\'s courtyard'))
    return None


def _sand_spots(gd, pr, rep, marker, box):
    import activity
    import lootplace
    ctx = activity.Ctx(gd, pr)
    S = lootplace.Seat(gd, pr, ctx.world)
    out = []
    for r in SAND_FROM:
        for k in range(16):
            a = k * 2 * math.pi / 16 + r / 100.0
            x, y = marker[0] + r * math.sin(a), marker[1] + r * math.cos(a)
            if any(math.hypot(x - q[0], y - q[1]) < 90 for q, _c in out):
                continue
            p = S.at(x, y, a * 1.7, box, marker[2], outside=True)
            if p and abs(p[2] - marker[2]) < 80:
                out.append((p, ctx.cell(p[0], p[1])))
                break
        if len(out) >= SAND_TAGS:
            break
    if len(out) < SAND_TAGS:
        rep['skipped'].append(('sand tags', '%d of %d placed' % (len(out), SAND_TAGS)))
    return out


def plan(gd, pr):
    import money
    rep = {'rows': [], 'skipped': []}
    if money._mod_key(pr, KEEPER[0], 'NPC_'):
        rep['skipped'].append(('all', 'the mod already has %s (Undo first)' % KEEPER[0]))
        return rep
    if not money._mod_key(pr, money.BANGO[0], 'MISC') or not money._mod_key(pr, money.QUEST, 'QUST'):
        rep['skipped'].append(('all', 'the money step is not in the mod'))
        return rep
    R = _refs(pr, (TAN, TENANT, CHEST, HANDOVER))
    missing = [e for e in (TAN, TENANT, CHEST, HANDOVER) if e not in R]
    if missing:
        rep['skipped'].append(('all', 'the An questline\'s refs are missing: %s' % missing))
        return rep
    tan, tenant = R[TAN][2]['p'], R[TENANT][2]['p']
    k = _keeper_spot(gd, pr, rep, tan, tenant)
    if k:
        rep['rows'].append(dict(k, what='keeper'))
    box = [-1, -2, 0, 1, 2, 1]
    for p, cell in _sand_spots(gd, pr, rep, R[HANDOVER][2]['p'], box):
        rep['rows'].append({'what': 'sand tag', 'p': p, 'cell': cell,
                            'from_marker': round(math.hypot(p[0] - R[HANDOVER][2]['p'][0], p[1] - R[HANDOVER][2]['p'][1]))})
    rep['rows'].append({'what': 'chest', 'base': R[CHEST][2]['base']})
    tb = R[TENANT][2]['base']
    shared = sum(1 for c in pr.cells.values() for r in (c.get('refs') or {}).values() if r.get('base') == tb and not r.get('removed'))
    rep['rows'].append({'what': 'tenant', 'base': tb, 'shared_by': shared})
    return rep


def _cnto(rec, item, n):
    import api_characters as ac
    import factionfolk as ff
    import struct
    s = ff._sub(rec.get('type', 'CONT'), 'CNTO', struct.pack('<Ii', 0, n))
    ff._set_link(s, item)
    ac.insert(rec, s)


def ops(gd, pr, P=None):
    import api_characters as ac
    import api_quests as aq
    import factionfolk as ff
    import huangland
    import huangradio
    import money
    import northfolk
    import questrec as qr
    import skillcheck
    import waikikilife as WL
    from activity import _new_key
    P = P or plan(gd, pr)
    if any(w == 'all' for w, _x in P['skipped']):
        raise ValueError(P['skipped'][0][1])
    rows = P['rows']
    tag = money._mod_key(pr, money.BANGO[0], 'MISC')
    qk = money._mod_key(pr, money.QUEST, 'QUST')
    out, rep = [], {'made': [], 'placed': {}, 'skipped': list(P['skipped'])}

    def record(edid, rec, key=None):
        k = key or _new_key(pr)
        out.append({'op': 'record', 'key': k, 'record': rec})
        rep['made'].append(edid)
        return k
    # the clue: tags in Tan's chest and on his tenant (when the tenant's record is the tenant's own)
    for r in rows:
        if r['what'] == 'chest' and r['base'] in pr.records:
            rec = json.loads(json.dumps(pr.records[r['base']]))
            _cnto(rec, tag, CHEST_TAGS)
            record('FOLabAnTanChest (tags)', rec, r['base'])
        if r['what'] == 'tenant':
            if r['shared_by'] == 1 and r['base'] in pr.records:
                rec = json.loads(json.dumps(pr.records[r['base']]))
                _cnto(rec, tag, TENANT_TAGS)
                record('tenant (tags)', rec, r['base'])
            else:
                rep['skipped'].append(('tenant tags', 'the tenant shares a record with %d others' % (r['shared_by'] - 1)))
    for r in rows:
        if r['what'] == 'sand tag':
            out.append({'op': 'place', 'cell': r['cell'], 'key': _new_key(pr), 'ref': {'base': tag, 'p': list(r['p']), 's': 1.0}})
            rep['placed'].setdefault('sand tags', []).append({'p': [round(v) for v in r['p'][:3]], 'from_marker': r['from_marker']})
    # the storekeeper and his store
    kr = next((r for r in rows if r['what'] == 'keeper'), None)
    keeper = None
    if kr:
        pool, used = huangland.face_pool(gd, pr)
        face, sex = None, 'M'
        for want in (('Asian', 'M'), ('AsianOld', 'M'), ('Asian', 'F'), ('AsianOld', 'F')):
            face = next((f for f in pool.get(want, []) if gd.key(f) not in used), None)
            if face is not None:
                sex = want[1]
                break
        if face is None:
            face, sex = huangradio._spare_face(gd, used)
        if face is None:
            raise ValueError('no Asian face left that nobody in the mod has')
        g = ff.GROUPS['huang_folk']
        items = [(ff._item(gd, pr, e), 1) for e in g['wear'][sex]]
        fac = ff._mod_key(pr, ff.FACTIONS['huang'][0], 'FACT')
        npc = ff.person(gd, pr, face, KEEPER[0], KEEPER[1], dict(g, package=WL.STAY), items, [], fac)
        services = ac.num(recordio.load(gd, money._game(gd, WL.SERVICES_FROM, ('NPC_',))), 'AIDT', 'Services')
        ac.set_num(npc, 'AIDT', 'Services', services)
        ac.set_num(npc, 'ACBS', 'Barter gold', WL.BARTER_GOLD)
        keeper = record(KEEPER[0], npc)
        ckey = record(STORE_CHEST, northfolk.chest(gd, pr, STORE_CHEST, money.TRADE_FROM, STOCK))
        x, y, z, rz = kr['p']
        chest_ref = _new_key(pr)
        out.append({'op': 'place', 'cell': kr['cell'], 'key': chest_ref, 'ref': {'base': ckey, 'p': [x, y, z - 400, 0.0, 0.0, 0.0], 's': 1.0,
                                                                                 'persistent': True}})
        out.append({'op': 'place', 'cell': kr['cell'], 'key': _new_key(pr), 'ref': {'base': keeper, 'p': [x, y, z + 4, 0.0, 0.0, rz], 's': 1.0,
                                                                                    'persistent': True, 'merchant': chest_ref}})
        rep['placed']['keeper'] = {k: kr[k] for k in ('from_door', 'from_tan', 'from_tenant', 'from_hall')}
        rep['placed']['keeper']['p'] = [round(v) for v in kr['p'][:3]]
        rep['placed']['keeper']['face'], rep['placed']['keeper']['sex'] = gd.key(face), sex
    topics = {}
    for k in ('trade', 'tags', 'what', 'clue'):
        topics[k] = record('FOLabTanStore%s' % k.capitalize(), qr.topic_record({
            'edid': 'FOLabTanStore%s' % k.capitalize(), 'name': WORDS[k], 'priority': 50.0, 'kind': 0, 'flags': {'top_level': True},
            'quests': [{'quest': qk, 'links': []}]}))
    lines = []
    if keeper:
        has = lambda n: money._cond(47, '>=', n, tag, 0, 1)
        greeting = gd.key(money._game(gd, 'GREETING', ('DIAL',)))

        def line(topic, words, conds=(), end=''):
            l = aq.new_line_plain(gd, pr, topic, qk, keeper, words, conditions=list(conds))
            if end:
                l['end'] = {'source': end, 'parts': None}
            lines.append(l)
        line(greeting, WORDS['hello'])
        line(topics['trade'], WORDS['trade_yes'], (), 'ShowBarterMenu')
        line(topics['tags'], WORDS['tags_yes'], [has(1)], money.trade_in('bango'))
        line(topics['what'], WORDS['what_yes'])
        lines += skillcheck.check_lines(gd, pr, topics['clue'], qk, keeper, 'Speech', CLUE_SPEECH, WORDS['clue_yes'], WORDS['clue_no'],
                                        conditions=[has(1)])
    rep['lines'] = len(lines)
    rep['keys'] = {'keeper': keeper}
    return out, rep, lines


def voice_of(key, female):
    """A voice of the Huáng's own (Kokoro's Chinese voices speaking English, as Kailua's trader), blended so it's his alone."""
    import huangland
    pool = huangland.ZH_WOMEN if female else huangland.ZH_MEN
    n = int(key.lstrip('+').split(':')[-1], 16)
    a, b = pool[n % len(pool)], pool[(n + 1) % len(pool)]
    return '%s*0.7+%s*0.3' % (a, b)


def set_voice(pr, key, female):
    import api_voices as av
    voices = av.load(pr)
    voices['npc'].setdefault(key, {})['voice'] = voice_of(key, female)
    av.save(pr, voices)


def apply(pr, gd, P=None):
    import api_quests as aq
    o, rep, lines = ops(gd, pr, P)
    pr.apply(LABEL, o)
    keys = set(pr.records)
    pr.apply(LABEL, [{'op': 'record_new', 'record': aq._compiled_line(gd, pr, l)} for l in lines], merge=True)
    VOICE_ONLY.clear()
    VOICE_ONLY.update(k for k in pr.records if k not in keys and pr.records[k].get('type') == 'INFO')
    keeper = rep['keys']['keeper']
    if keeper:
        set_voice(pr, keeper, rep['placed']['keeper']['sex'] == 'F')
    rep['voice'] = keeper and voice_of(keeper, rep['placed']['keeper']['sex'] == 'F')
    rep['voice_lines'] = len(VOICE_ONLY)
    return rep
