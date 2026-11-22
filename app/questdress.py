"""Waikiki's quest people in the island's clothes (the user, 21 Nov 2026: "could we see about giving these quests npcs newer
clothes"): the beachcomber (castawayquest), Kuliʻouʻou's seven (kuliouquest), the doctor (waikikilife, sidequests).
Only clothes that draw in game: the Hawaiian shirt with trousers (its six khaki and denim ones are texture-only), the
board shorts, a woman's printed dress (the shirt's record, worn by a woman), the boater and lauhala hats, sunglasses, the
pirates' salvaged boarding armour, the game's head wraps. Nothing joined (outfitjoin's shirt-and-shorts is shelved).

Each person keeps their own inventory (guns, caps, food, chems), less the clothes lists they wore as prospectors
(`GONE`: the prospector armour and hat lists; the doctor's surfer lists), plus the fixed pieces in `WEARS`. A person still
using a template's inventory (0x100) is given their own first, as sidequests does. The Makapuʻu gate guard already wears
the Huáng lamellar: left as he is.

    ops(gd, pr)    (ops, report): one 'record' op per person, the whole NPC_ replaced. One Undo (apply)."""
import json

import recordio

WEARS = {
    'FOLabBeachcomber': ['FOLabBoardShortsCream', 'FOLabLauhala', 'GlassesShades'],
    'FOLabKuliCatcher': ['FOLabOldHawaiianShirtBlack', 'HeadWrap01'],
    'FOLabKuliCatcher2': ['FOLabOldHawaiianShirtNavy', 'HeadWrap03'],
    'FOLabKuliStranger': ['FOLabHawaiianShirtKhakiCream', 'FOLabBoater'],
    'FOLabKuliFather': ['FOLabHawaiianShirtDenimRed', 'FOLabLauhala'],
    'FOLabKuliSon': ['FOLabBoardShortsBlue'],
    'FOLabKuliPirate': ['FOLabSalvageArmor', 'HeadWrap02'],
    'FOLabKuliWoman': ['FOLabHawaiianShirtBlue', 'FOLabLauhala'],
    'FOLabWaikikiDoctor': ['FOLabHawaiianShirtCream', 'GlassesShades'],
}
GONE = {'LL2Tier2ArmorProspector', 'LL0ClothesHeadProspector50',
        'FOLabSurferBodyList', 'FOLabSurferHeadList', 'FOLabSurferEyesList'}


def _edids(pr):
    return {(recordio.field(r, 'EDID') or ''): k for k, r in pr.records.items()}


def _item_key(gd, pr, mine, edid):
    if edid in mine:
        return mine[edid]
    f = next((f for f, (_i, r) in gd.forms.items() if r.tag in ('ARMO', 'LVLI') and gd.edid(f) == edid), None)
    if f is None:
        raise ValueError('neither the mod nor the game has %s' % edid)
    return gd.key(f)


def _item_of(s):
    return next((f['value'] for f in s.get('fields', []) if f.get('name') == 'Item' or f.get('code') == 'F'), None)


def ops(gd, pr):
    import sidequests
    mine = _edids(pr)
    out, rep = [], {}
    for person, wears in WEARS.items():
        k = mine.get(person)
        if not k:
            raise ValueError('the mod has no %s' % person)
        npc = json.loads(json.dumps(pr.records[k]))
        name_of = lambda key: (recordio.field(pr.records[key], 'EDID') if key in pr.records else gd.edid(gd.from_key(key)))
        before = [name_of(_item_of(s)) for s in npc['subs'] if s['tag'] == 'CNTO']
        keep = []
        for s in npc['subs']:
            if s['tag'] == 'CNTO' and name_of(_item_of(s)) in GONE:
                continue
            if s['tag'] == 'COED' and keep and keep[-1]['tag'] == 'CNTO' and name_of(_item_of(keep[-1])) in GONE:
                continue
            keep.append(s)
        npc['subs'] = keep
        items = [_item_key(gd, pr, mine, e) for e in wears]
        have = {_item_of(s) for s in npc['subs'] if s['tag'] == 'CNTO'}
        sidequests._with_items(gd, npc, [i for i in items if i not in have])
        after = [name_of(_item_of(s)) for s in npc['subs'] if s['tag'] == 'CNTO']
        out.append({'op': 'record', 'key': k, 'record': npc})
        rep[person] = {'key': k, 'took_out': [e for e in before if e in GONE], 'wears': wears, 'carries': len(after)}
    return out, rep


def apply(server):
    o, rep = ops(server.GD, server.PR)
    server.edit("Quest people in the island's clothes", o)
    return rep
