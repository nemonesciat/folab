"""The An dynasty's questline, stages 1 to 3 (the user, 25 Nov 2026: the Huáng are open to you now; their landed nobility
back the pirates because the slave trade fattens their plantations, at the cost of the realm and its government; you bring
them into line "by killing, bribing, blackmailing or persuading"; it climbs from a minor official and a minor landowner to
the great nobility; every stage has several ways through; an Asian player character starts easier; plans and answers in the
shared notes, huang-politics-proposals.md). Stage 4 (the Duke of Kāneʻohe on the Ship-King's order, at the grand palace)
waits for the palace's site.

The ladder is the old Zhou ranks [proposal]: Baron (nan) Tan, Viscount (zi) Gao, three Earls (bo), later the Duke (gong).
A magistrate's clerk, Fang Jun [proposal], hires you for all three, at the Waimānalo courtyards. He speaks broken English
(he deals with outsiders); the nobles, their people and the tenants speak Mandarin, shown as pinyin with the meaning in
brackets, spoken in Mandarin (huangland's way: `ZH`).

**FOLabAnCourt** (start enabled): Fang Jun's lines that hire you for each stage and hear how it went; its script meets you
once: an Asian player character gets `ASIAN_FACE` of the Huáng's face (repstanding) and Fang Jun hires them outright
(others pass Speech `HIRE`, or show they're serious with two Stimpaks). Speech and Barter checks with the Huáng are
`EASIER` easier for an Asian player character, and for Island Tongue (perks.py) where the mod has it.

1. **A Small Account (FOLabAnSmallAccount):** Baron Tan's tenants vanish. Proof: his sick tenant talks (Medicine
   `T_MED`) or his tenant is talked round (Speech `T_TALK`); his tally book from his locked chest (Lockpick `T_LOCK`); the
   night handover on the beach watched unseen (sneaking, within `WATCH` of it, not detected); or Tan himself confesses
   (Speech `T_ACCUSE`). Endings: Tan handed to the clerk (palace), Tan blackmailed into paying the palace (Speech
   `T_BLACK`), Tan dead, or Tan's bribe taken and the clerk told he's clean (the nobles).
2. **The Grain Book (FOLabAnGrainBook):** Viscount Gao of Kailua under-reports and pays the pirates in maize. Proof: his
   steward's books audited (Science `G_SCI` or Barter `G_BARTER`) or the steward bribed (Stimpaks); a tenant (Speech, or
   Repair `G_REPAIR` on her well pump, or Medicine on her child); the pirates' night pickup on the beach broken (all
   dead). Pressure: his still wrecked (Explosives `G_BOOM`). Endings: Gao pays the palace (persuaded with proof, Speech
   `G_PERSUADE` or no check once his still is wrecked; or blackmailed with Tan's book), Gao falls (proof to the clerk),
   Gao dead, or his bribe (the nobles).
3. **The Earls' Compact (FOLabAnEarlsCompact):** three earls at Kāneʻohe mean to let pirates take the palace's grain
   store at the Border Post. Ways: beat the raid at night (all raiders dead); Liu Wei reads where they'll come from
   (Survival `E_SURV`) so you hit their camp by day; split the earls (Earl Wei, Speech `E_SPEECH`; Earl Xu, Barter
   `E_BARTER`); steal the compact from Earl Wei's chest (Lockpick `E_LOCK`) and give it to the clerk; kill all three; or
   tell Earl He you'll look away (the nobles).

The palace's endings: Huáng fame (FOLabRepHuang) and face (repstanding) and the clerk's pay; the nobles': their goods and
a count in FOLabAnCourt.nobles [proposal: stage 4 reads it; pirate fame for each]. Refs are switched on and off by the
quests' own scripts; stage and line scripts only set variables (scripts name refs, stages don't).

    plan(gd, pr)       {'rows': [...], 'skipped': [...]}: every person and thing's spot, with what it's clear of
    apply(pr, gd, P)   one Undo (records and refs, then quests and lines compiled against them)
"""
import json
import math

import recordio

LABEL = 'The An dynasty: the clerk, the baron, the viscount and the earls'
COURT, Q1, Q2, Q3 = 'FOLabAnCourt', 'FOLabAnSmallAccount', 'FOLabAnGrainBook', 'FOLabAnEarlsCompact'
VOICE = [COURT, Q1, Q2, Q3]
NAMES = {Q1: 'A Small Account', Q2: 'The Grain Book', Q3: "The Earls' Compact"}
ZH = {}                                 # (a shown line's words -> the pinyin said: voicelines reads it)

# checks
HIRE, EASIER, ASIAN_FACE = 40, 15, 5
T_MED, T_TALK, T_LOCK, T_ACCUSE, T_BLACK, WATCH = 45, 50, 50, 60, 50, 900.0
G_SCI, G_BARTER, G_REPAIR, G_MED, G_TALK, G_BOOM, G_PERSUADE, G_BRIBE = 50, 50, 45, 45, 50, 50, 60, 3
E_SURV, E_SPEECH, E_BARTER, E_LOCK = 50, 60, 55, 75
SKILLS = {'Barter': (32, 'AVBarter'), 'Explosives': (35, 'AVExplosives'), 'Lockpick': (36, 'AVLockpick'),
          'Medicine': (37, 'AVMedicine'), 'Repair': (39, 'AVRepair'), 'Science': (40, 'AVScience'),
          'Speech': (43, 'AVSpeech'), 'Survival': (44, 'AVThrowing')}
EASED = ('Speech', 'Barter')            # (the checks an Asian player character and Island Tongue make easier)
FN = {'GetActorValue': 14, 'GetItemCount': 47, 'GetStage': 58, 'GetIsRace': 69, 'GetIsID': 72, 'GetQuestVariable': 79,
      'HasPerk': 449}
TONGUE = 'FOLabPerkIslandTongue'
FACE = 5                                # (the Huáng's face for a palace ending: repstanding)
NIGHT = (22, 4)
RAIDERS, BUYERS = 4, 3
PAY = {'palace': [('ALCH', 'Stimpak', 3), ('ALCH', 'WaterPurified', 2)], 'nobles': [('ALCH', 'Stimpak', 5), ('ALCH', 'WaterPurified', 3)]}

# where (spots are worked out round these by plan; distances clear of other things in CLEAR)
WAIMANALO_GIVER = 'FOLabHuangSilkGiverREF'   # (the Waimānalo courtyards: Lin Meihua's ref)
LIU_WEI = 'FOLabHuangGuard09'
CLEAR = {'door': 450.0, 'marker': 1500.0, 'named': 700.0, 'person': 300.0}
QUIET = 1500.0                          # (the beach handover, the pickup, the raiders' camp: this far from anyone)

# Mandarin lines: (English shown, pinyin said). Kept short: a subtitle and its Mandarin stay one response.
M = {
    'tan_hi': ("Who are you? My land has no work for you.", "Nǐ shì shéi? Wǒ de dì méiyǒu nǐ de huó."),
    'tan_accuse': ("[SUCCEEDED] ...Yes. The pirates pay well. Every lord does it.", "Shì. Hǎidào gěi de duō. Měi gè lǎoye dōu zhèyàng."),
    'tan_accuse_no': ("[FAILED] Lies. Get off my land.", "Húshuō. Gǔn chūqù."),
    'tan_black': ("[SUCCEEDED] Enough! I will pay the palace its share. Keep quiet.", "Gòu le! Wǒ gěi gōngtíng jiāo. Nǐ bié shuō."),
    'tan_black_no': ("[FAILED] Who would believe a barbarian?", "Shéi huì xiāngxìn mánzi?"),
    'tan_bribe': ("Take this. Tell the clerk my land is clean.", "Ná zhe. Gàosù shūlì wǒ de dì gānjìng."),
    'tenant_hi': ("Leave me. I am sick.", "Bié guǎn wǒ. Wǒ bìng le."),
    'tenant_med': ("[SUCCEEDED] The fever eases. My brother was sold. At night, on the beach.", "Shāo tuì le. Wǒ gēge bèi mài le. Yèlǐ, zài hǎitān."),
    'tenant_med_no': ("[FAILED] It still burns. Go away.", "Háishì tàng. Zǒu ba."),
    'tenant_talk': ("[SUCCEEDED] They take the ones in debt. To the pirates' boats.", "Qiànzhài de rén bèi dài zǒu. Shàng hǎidào de chuán."),
    'tenant_talk_no': ("[FAILED] I know nothing. Nothing.", "Wǒ shénme dōu bù zhīdào."),
    'gao_hi': ("A barbarian in my hall. Speak quickly.", "Mánzi jìn wǒ de táng. Kuài shuō."),
    'gao_pay': ("[SUCCEEDED] Very well. The palace will have its grain.", "Hǎo ba. Gōngtíng huì yǒu liángshí."),
    'gao_pay_no': ("[FAILED] The palace is weak. I owe it nothing.", "Gōngtíng ruò. Wǒ bù qiàn tā."),
    'gao_ruined': ("My still is gone... Fine. The palace gets its share.", "Wǒ de jiǔfáng méi le. Hǎo, gōngtíng ná tā de."),
    'gao_book': ("Tan's book... Burn it, and the palace gets its grain.", "Tán de zhàngběn... Shāo le tā, gōngtíng ná liáng."),
    'gao_bribe': ("Here. Tell the clerk my books are true.", "Gěi nǐ. Gàosù shūlì wǒ de zhàng méi wèntí."),
    'stew_hi': ("The Viscount's books are not for you.", "Zǐjué de zhàng bú shì gěi nǐ kàn de."),
    'stew_sci': ("[SUCCEEDED] The weights... yes, they are false. Take this page.", "Chèng... duì, shì jiǎ de. Ná zhè yè."),
    'stew_sci_no': ("[FAILED] The weights are true. Go.", "Chèng shì zhēn de. Zǒu."),
    'stew_barter': ("[SUCCEEDED] You count well. Half the maize goes to the boats.", "Nǐ suàn de hǎo. Yíbàn yùmǐ shàng chuán."),
    'stew_barter_no': ("[FAILED] The numbers add up. You are wrong.", "Shùzì méi cuò. Nǐ cuò le."),
    'stew_bribe': ("For medicine... Here, the true page.", "Wèile yào... Gěi, zhēn de nà yè."),
    'still_hi': ("Careful. The still is hot.", "Xiǎoxīn. Jiǔ zào hěn rè."),
    'still_boom': ("[SUCCEEDED] The valve! Run! ...It's ruined.", "Fá! Kuài pǎo! ...Huǐ le."),
    'still_boom_no': ("[FAILED] Don't touch that. Get away from it.", "Bié pèng. Líkāi."),
    'gten_hi': ("The well pump is broken again.", "Shuǐbèng yòu huài le."),
    'gten_fix': ("[SUCCEEDED] Water! I'll tell you: the maize goes to the pirates.", "Yǒu shuǐ le! Wǒ gàosù nǐ: yùmǐ gěi hǎidào."),
    'gten_fix_no': ("[FAILED] Still broken.", "Háishì huài de."),
    'gten_med': ("[SUCCEEDED] My child sleeps. The Viscount feeds the pirates.", "Háizi shuì le. Zǐjué yǎng hǎidào."),
    'gten_med_no': ("[FAILED] She's no better.", "Tā méi hǎo."),
    'gten_talk': ("[SUCCEEDED] Every month, a boat. Our maize goes aboard.", "Měi gè yuè yī tiáo chuán. Yùmǐ shàng chuán."),
    'gten_talk_no': ("[FAILED] I farm. I see nothing.", "Wǒ zhòng dì. Wǒ shénme yě méi kàn jiàn."),
    'wei_hi': ("The palace sends a barbarian? It must be desperate.", "Gōngtíng pài mánzi lái? Tā zhēn méi bànfǎ le."),
    'wei_split': ("[SUCCEEDED] The pirates would turn on us too... The compact is off.", "Hǎidào yě huì fǎn yǎo wǒmen... Méngyuē zuòfèi."),
    'wei_split_no': ("[FAILED] The pirates keep their word. The palace never has.", "Hǎidào shǒu xìn. Gōngtíng cóng bù."),
    'xu_hi': ("Speak of trade, or don't speak.", "Tán shēngyì, bùrán bié shuō."),
    'xu_buy': ("[SUCCEEDED] The palace pays better? Then I'm out. The raid is off.", "Gōngtíng gěi de gèng duō? Nà wǒ bù gàn le."),
    'xu_buy_no': ("[FAILED] The palace has nothing to pay with.", "Gōngtíng méiyǒu qián."),
    'he_hi': ("Sit. We can be friends, barbarian.", "Zuò. Wǒmen kěyǐ zuò péngyǒu, mánzi."),
    'he_look': ("Wise. Take this, and be far from the Border Post at night.", "Cōngmíng. Ná zhe, wǎnshàng líkāi biānjiè."),
}
# Fang Jun's broken English, and the player's words (English)
W = {
    'fang_hi': "You. Barbarian. You want work? Palace work.",
    'fang_asian': "Huang face. Good. The palace can use you. Listen.",
    'hire': "What work?",
    'hire_yes': "[SUCCEEDED] Good. You talk proper. Listen.",
    'hire_no': "[FAILED] You talk too much. Bring two stimpak, show you serious.",
    'hire_pay': "Here. Two stimpaks.",
    'hire_paid': "Good. Now listen.",
    'job1': "Baron Tan, west of the courtyards. His tenants vanish. Find out where. Bring me proof.",
    'job2': "Viscount Gao, in Kailua. His grain book lies. Pirates eat our maize. Bring him in line.",
    'job3': "Three earls at Kane'ohe. A compact. They let pirates take the palace grain at the Border Post. Stop it.",
    'fang_wait': "You did good. The palace hears your name. Wait for word.",
    'proof1': "Tan sells his tenants to the pirates. Here's the proof.",
    'proof1_yes': "Enough. The Shouwei take him tonight. Here, your pay.",
    'clean1': "Tan's land is clean.",
    'clean1_yes': "Clean? ...Fine. Then nothing. Go.",
    'dead1': "Tan dead. Messy. But done. Here.",
    'paid1': "Tan pays the palace now? Ha. Good work. Here.",
    'proof2': "Gao feeds the pirates. Here's the proof.",
    'proof2_yes': "Then Gao falls. The Shouwei go to Kailua. Your pay.",
    'clean2': "Gao's books are true.",
    'clean2_yes': "True. ...If you say. Go.",
    'done2': "Gao done. The palace eats again. Here.",
    'compact': "The earls' compact. Their seals are on it.",
    'compact_yes': "Their own seals! The earls are finished. Here.",
    'done3': "The grain is safe. The earls learn. Here.",
    'accuse': "You sell your tenants to the pirates.",
    'black': "Pay the palace its share, or the clerk hears everything.",
    'bribe1': "What's it worth to you if I tell the clerk you're clean?",
    'treat': "Let me see that fever.",
    'ask': "Where did your neighbours go?",
    'g_pay': "Pay the palace, or lose everything.",
    'g_book': "Tan's book names you.",
    'g_bribe': "What's it worth if the clerk hears your books are true?",
    'audit': "Your weights are false.",
    'count': "These numbers don't add up.",
    'pay_stew': "Three stimpaks for the true page.",
    'wreck': "That valve looks loose. Let me see.",
    'pump': "Let me fix that pump.",
    'child': "Let me look at your child.",
    'ask2': "Where does the maize go?",
    'split': "The pirates will turn on you next.",
    'buy': "The palace will pay more than the pirates.",
    'look': "I could be far from the Border Post at night.",
    'surv': "Where will they come from?",
    'surv_yes': "[SUCCEEDED] The gully north of the post. They camp there by day. Hit them first.",
    'surv_no': "[FAILED] Could be anywhere. We wait at the post.",
    'liu_hi': "The Border Post. The grain store. We watch.",
}
SAID_BY = {'tan': 'Baron Tan', 'tenant': "Tan's Tenant", 'man': "Tan's Man", 'gao': 'Viscount Gao', 'steward': "Gao's Steward",
           'distiller': "Gao's Distiller", 'gtenant': "Gao's Tenant", 'wei': 'Earl Wei', 'xu': 'Earl Xu', 'he': 'Earl He',
           'fang': 'Fang Jun'}
EDIDS = {'fang': 'FOLabAnClerkFang', 'tan': 'FOLabAnBaronTan', 'tenant': 'FOLabAnTanTenant', 'man': 'FOLabAnTanMan',
         'gao': 'FOLabAnViscountGao', 'steward': 'FOLabAnGaoSteward', 'distiller': 'FOLabAnGaoDistiller',
         'gtenant': 'FOLabAnGaoTenant', 'wei': 'FOLabAnEarlWei', 'xu': 'FOLabAnEarlXu', 'he': 'FOLabAnEarlHe'}
NOBLE = ('tan', 'gao', 'wei', 'xu', 'he')


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
except Exception:                       # (g2pzh unavailable at import: filled when the step runs)
    pass


def _mod_key(pr, edid, tag=None):
    return next((k for k, r in pr.records.items() if (tag is None or r.get('type') == tag) and recordio.field(r, 'EDID') == edid), None)


def _cond(fn, op, value, p1=0, p2=0, run=0, orr=False):
    return {'or': orr, 'use_target': False, 'op': op, 'fn': FN.get(fn, fn), 'p1': p1, 'p2': p2, 'run': run, 'ref': '', 'value': float(value)}


def _vars(srec):
    out, last = {}, None
    for sub in srec['subs']:
        if sub['tag'] == 'SLSD':
            last = next(f['value'] for f in sub['fields'] if f.get('name') == 'Index')
        elif sub['tag'] == 'SCVR' and last is not None:
            out[sub['value'].lower()] = last
    return out


# ---------- where ----------
class Where:
    """Spots for everyone, worked out round the Huáng's own places in the mod: the Waimānalo courtyards (Lin Meihua),
    Kailua's and Kāneʻohe's halls (by their map markers), the Border Post."""

    def __init__(self, gd, pr):
        import activity
        self.gd, self.pr = gd, pr
        self.ctx = activity.Ctx(gd, pr)
        self.mk = {n: p for n, (_c, p) in self.ctx.mk.items()}
        self.people = list(self.ctx.sp.taken)
        self.named, self.halls = [], []
        grid = gd.grid(self.ctx.world)
        keys = {gd.key(c) for c in grid.values()}
        for ck, c in pr.cells.items():
            if ck not in keys:
                continue
            for rk, r in (c.get('refs') or {}).items():
                if r.get('removed') or not r.get('p'):
                    continue
                if r.get('edid'):
                    self.named.append((r['edid'], tuple(r['p'][:3])))
                b = r.get('base', '')
                if b in pr.records and (recordio.field(pr.records[b], 'EDID') or '').startswith(('FOLabSettlerHall', 'FOLabHuangHall')):
                    self.halls.append(tuple(r['p'][:3]))
        self.giver = next((p for e, p in self.named if e == WAIMANALO_GIVER), None)
        self.liu = next((rk for c in pr.cells.values() for rk, r in (c.get('refs') or {}).items()
                         if not r.get('removed') and r.get('base') == _mod_key(pr, LIU_WEI, 'NPC_')), None)
        self.taken = []

    def doors(self, x, y):
        import robots
        return robots._outside_doors(self.gd, self.pr, self.ctx.grid, {'a': (x, y)})

    def clear(self, s, quiet=False, thing=False):
        x, y = s[0], s[1]
        d = lambda pts: min((math.hypot(x - p[0], y - p[1]) for p in pts), default=1e9)
        out = {'door': d(self.doors(x, y)), 'marker': d(self.mk.values()), 'named': d([p for _e, p in self.named]),
               'person': d(self.people), 'ours': d([t for t in self.taken if t != s])}
        ok = (out['door'] >= (250.0 if thing else CLEAR['door']) and out['named'] >= CLEAR['named'] and out['ours'] >= 160
              and out['person'] >= (QUIET if quiet else CLEAR['person']) and (not quiet or out['marker'] >= CLEAR['marker']))
        return ok, {k: round(v) for k, v in out.items()}

    def near(self, x, y, radii=(200, 300, 450, 600, 800), quiet=False, thing=False):
        for r in radii:
            for t in range(12):
                a = (t + 0.37 * r / 100.0) * 2 * math.pi / 12
                s = self.ctx.spot(x + r * math.sin(a), y + r * math.cos(a))
                if s and self.clear(s, quiet, thing)[0]:
                    self.taken.append(s)
                    return s
        return None

    def hall_near(self, p, far_from=(), apart=1500.0, within=None):
        """The hall nearest p that's apart from far_from; within: of the halls that near p, the one farthest from anyone
        standing (a noble's hall of his own, not the elder's or the trader's)."""
        if within:
            hs = [h for h in self.halls if math.hypot(h[0] - p[0], h[1] - p[1]) <= within]
            return max(hs, key=lambda h: min((math.hypot(h[0] - q[0], h[1] - q[1]) for q in self.people), default=1e9), default=None)
        hs = [h for h in self.halls if all(math.hypot(h[0] - q[0], h[1] - q[1]) >= apart for q in far_from)]
        return min(hs, key=lambda h: math.hypot(h[0] - p[0], h[1] - p[1]), default=None)

    def shore(self, p, reach=(2000.0, 24000.0)):
        """A quiet spot on the sand near p (stormafter's shore points), on a navmesh, clear of everyone."""
        import stormafter
        if not hasattr(self, '_shore'):
            self._shore = stormafter.shore_points(self.gd, self.pr, self.ctx.world, step=256)
        pts = sorted((s for s in self._shore if reach[0] <= math.hypot(s[0] - p[0], s[1] - p[1]) <= reach[1]),
                     key=lambda s: math.hypot(s[0] - p[0], s[1] - p[1]))
        for s in pts[::2][:1500]:
            got = self.near(s[0], s[1], radii=(60, 200), quiet=True)
            if got:
                return got
        return None


def plan(gd, pr):
    """{'rows': [{'what', 'p', 'clear'}], 'skipped': [...], 'spots': {name: (x, y, z)}}."""
    W_ = Where(gd, pr)
    rows, skipped, S = [], [], {}
    if not W_.giver:
        return {'rows': [], 'skipped': ['no Waimanalo courtyards (%s)' % WAIMANALO_GIVER], 'spots': {}}

    def put(name, s, quiet=False):
        if s is None:
            skipped.append(name)
            return None
        S[name] = s
        rows.append({'what': name, 'p': [round(v) for v in s], 'clear': W_.clear(s, quiet, 'chest' in name)[1]})
        return s
    g = W_.giver
    office = W_.hall_near((g[0] - 2000, g[1] - 2000), far_from=[g], apart=2500)
    tan_hall = W_.hall_near((g[0] - 4000, g[1] + 1500), far_from=[g, office or g], apart=3000)
    if office:
        put('fang', W_.near(*office[:2]))
    if tan_hall:
        put('tan', W_.near(*tan_hall[:2]))
        put('tan_chest', W_.near(tan_hall[0], tan_hall[1], radii=(250, 350, 500, 650), thing=True))
        put('tenant', W_.near(tan_hall[0], tan_hall[1], radii=(900, 1200, 1500)))
    shore = W_.shore(tan_hall or g)
    put('handover', shore, quiet=True)
    if shore:
        put('buyer', W_.near(shore[0], shore[1], radii=(150, 250), quiet=True), quiet=True)
    kailua = W_.mk.get('Kailua')
    gao_hall = W_.hall_near(kailua, within=9000.0) if kailua else None
    if gao_hall:
        put('gao', W_.near(*gao_hall[:2]))
        put('steward', W_.near(gao_hall[0], gao_hall[1], radii=(400, 550, 700, 900, 1100)))
        put('distiller', W_.near(gao_hall[0], gao_hall[1], radii=(800, 1000, 1200)))
        put('gtenant', W_.near(gao_hall[0], gao_hall[1], radii=(1500, 1800, 2200)))
        pick = W_.shore(gao_hall, reach=(2500.0, 32000.0)) or W_.shore(kailua, reach=(1500.0, 32000.0))
        put('pickup', pick, quiet=True)
        for n in range(BUYERS):
            if pick:
                put('pirate%d' % n, W_.near(pick[0], pick[1], radii=(150, 250, 350), quiet=True), quiet=True)
    kane = W_.mk.get("Kane'ohe")
    earl_hall = W_.hall_near(kane, within=9000.0) if kane else None
    if earl_hall:
        for k in ('wei', 'xu', 'he'):
            put(k, W_.near(*earl_hall[:2], radii=(250, 350, 450, 600, 800, 1000)))
        put('compact_chest', W_.near(earl_hall[0], earl_hall[1], radii=(300, 450, 600, 800), thing=True))
    post = W_.mk.get('Border Post')
    if post:
        store = put('store', W_.near(post[0], post[1], radii=(700, 900, 1100)))
        if store:
            for n in range(RAIDERS):
                put('raider%d' % n, W_.near(store[0], store[1], radii=(250, 350, 450)))
        camp = W_.near(post[0], post[1] + 3000, radii=(0, 400, 800, 1200), quiet=True)
        put('camp', camp, quiet=True)
    return {'rows': rows, 'skipped': skipped, 'spots': S, 'world': W_.ctx.world, 'liu': W_.liu}


# ---------- what ----------
def _game_key(gd, edid, tag):
    import piratedeal
    return gd.key(piratedeal._game(gd, edid, tag))


def _faces(gd, pr):
    import activity
    import huangland
    ctx = activity.Ctx.__new__(activity.Ctx)
    ctx.gd, ctx.pr = gd, pr
    ctx._pool, ctx._used = huangland.face_pool(gd, pr)
    return ctx


def _huang(gd, pr, ctx, edid, name, k, sex, fac, script=None, items=()):
    """A Huáng of the mod's own, a face no one else has; nobles in the silk gown, the clerk in the changshan."""
    import factionfolk as ff
    old = k in ('wei', 'xu', 'he', 'gao')
    g = dict(ff.GROUPS['huang_elder' if old else 'huang_folk'])
    races = ('AsianOld', 'Asian') if old else ('Asian',)
    face = ctx.free_face(races, sex) or ctx.free_face(races, 'F' if sex == 'M' else 'M')
    if face is None:
        raise ValueError('no free Huang face left for %s' % edid)
    wear = []
    for e in (('FOLabSilkGown',) if k in NOBLE else ('FOLabChangshan',) if k in ('fang', 'steward') else ()):
        try:
            wear.append((ff._item(gd, pr, e), 1))
        except Exception:
            pass
    if not wear:
        fem = ff._num(recordio.load(gd, face), 'ACBS', 'Flags') & 0x1
        for e in g['wear']['F' if fem else 'M']:
            try:
                wear.append((ff._item(gd, pr, e), 1))
            except Exception:
                pass
    g['package'] = 'DefaultSandboxEditorLocation256' if k in ('tenant', 'gtenant', 'distiller') else g.get('package')
    rec = ff.person(gd, pr, face, edid, name, g, wear + list(items), [], fac or '')
    if script:
        import api_characters as ac
        ac.insert(rec, {'tag': 'SCRI', 'label': 'Script', 'kind': 'F', 'value': script})
    ff._set_num(rec, 'AIDT', 'Aggression', 0)
    ff._set_num(rec, 'AIDT', 'Confidence', 1 if k not in NOBLE else 2)
    return rec


def _standing(gd, pr):
    """[(key, record, cell, ref, (x, y))]: the Huáng standing in the mod who are nobody in particular (Nongmin and Shouwei
    by name, each placed once, no ref of theirs named by anything, not a quest's giver): the game's Asian faces are all
    worn by now (25 Nov 2026: 13 left, all the game's named characters but one), and a face of FOLab's own has no
    painted face file yet."""
    import huangland as HL
    fac = HL.faction_key(pr)
    refs = {}
    for ck, c in pr.cells.items():
        for rk, r in (c.get('refs') or {}).items():
            if not r.get('removed') and r.get('base', '').startswith('+') and r.get('p'):
                refs.setdefault(r['base'], []).append((ck, rk, r))
    out = []
    for k, rec in pr.records.items():
        if rec.get('type') != 'NPC_' or (recordio.field(rec, 'FULL') or '') not in ('Nongmin', 'Shouwei'):
            continue
        if (recordio.field(rec, 'EDID') or '') in HOUSED or not HL.is_huang(pr, k, fac):
            continue
        rs = refs.get(k, [])
        if len(rs) != 1 or rs[0][2].get('edid') or rs[0][2].get('link'):
            continue
        ck, rk, r = rs[0]
        out.append((k, rec, ck, rk, tuple(r['p'][:2])))
    return _unnamed(pr, out)


# (people other steps want by editor ID: Liu Wei (the earls' stage asks him), and those huanginside houses, each in a home)
HOUSED = {LIU_WEI, 'FOLabHuangElder01', 'FOLabHuangElder02', 'FOLabHuangElder03', 'FOLabHuangFolk01', 'FOLabHuangFolk02',
          'FOLabHuangFolk03', 'FOLabHuangFolk04', 'FOLabHuangFarmer01'}
SMALL_TALK = 'FOLabWaikikiPeople'       # (huangtalk's hellos, goodbyes and idle chatter for every Huáng: they go with the person)


def _unnamed(pr, pool):
    """The pool less anyone something else in the mod names: their record or their ref in any record (a quest's giver, a
    line's speaker, a package's target, a guard or court list) or in any other ref (a link, a door, an enable parent),
    their own small talk (`SMALL_TALK`'s lines) excepted. 25 Nov 2026, the story session: none of the recast may be a
    quest's, guard's or court's, and nothing may expect them where they stood."""
    import re
    if not pool:
        return pool
    want = {p[0] for p in pool} | {p[3] for p in pool}
    pat = re.compile('|'.join(re.escape(k) for k in want))
    talk = _mod_key(pr, SMALL_TALK, 'QUST')
    named = set()
    for k, rec in pr.records.items():
        if rec.get('type') == 'INFO' and talk and recordio.field(rec, 'QSTI') == talk:
            continue
        for m in pat.findall(json.dumps(rec.get('subs', []))):
            if m != k:
                named.add(m)
    for ck, c in pr.cells.items():
        for rk, r in (c.get('refs') or {}).items():
            if r.get('removed'):
                continue
            body = dict(r)
            body.pop('base', None)
            for m in pat.findall(json.dumps(body)):
                if m != rk:
                    named.add(m)
    return [p for p in pool if p[0] not in named and p[3] not in named]


def _recast(gd, pr, pool, k, spot, sex=None):
    """The nearest one of the pool to the spot, as this role (taken out of the pool): (key, the record changed, (cell, ref))
    or None. Nobles and the clerk in a Nongmin's record, never a Shouwei's (a soldier stays a soldier)."""
    import factionfolk as ff
    fit = [p for p in pool if recordio.field(p[1], 'FULL') == 'Nongmin'] or pool
    if sex:                                 # (the role's sex where one stands: a woman's face for a woman's part)
        fem = lambda p: bool(ff._num(p[1], 'ACBS', 'Flags') & 1)
        fit = [p for p in fit if fem(p) == (sex == 'F')] or fit
    if not fit:
        return None
    best = min(fit, key=lambda p: math.hypot(p[4][0] - spot[0], p[4][1] - spot[1]))
    pool.remove(best)
    key, rec, ck, rk, _xy = best
    rec = json.loads(json.dumps(rec))
    recordio.set_field(rec, 'FULL', SAID_BY[k])
    wear = ('FOLabSilkGown',) if k in NOBLE else ('FOLabChangshan',) if k in ('fang', 'steward') else ()
    keys = []
    for e in wear:
        try:
            keys.append(ff._item(gd, pr, e))
        except Exception:
            pass
    if keys:                                # (their clothes swapped for the role's: other ARMO taken out of their things)
        def armour(s):
            if s['tag'] != 'CNTO':
                return False
            item = next((f.get('value') for f in s.get('fields', ()) if f.get('name') == 'Item'), '')
            r = pr.records.get(item) if str(item).startswith('+') else None
            return (r or {}).get('type') == 'ARMO' or (not r and gd_tag(gd, item) == 'ARMO')
        rec['subs'] = [s for s in rec['subs'] if not armour(s)]
        import api_characters as ac
        import sidequests
        for it in keys:
            ac.insert(rec, sidequests._cnto(gd, it, 1))
    return key, rec, (ck, rk)


def gd_tag(gd, key):
    try:
        return gd.forms[gd.from_key(key)][1].tag
    except Exception:
        return ''


def _pirate_base(pr):
    """One of the mod's pirates (a look by a levelled template, so refs of it differ), for the buyers and raiders."""
    best = None
    for k, r in pr.records.items():
        if r.get('type') != 'NPC_':
            continue
        e = recordio.field(r, 'EDID') or ''
        if e.startswith('FOLabPirate') and 'Captain' not in e and 'Child' not in e:
            if recordio.field(r, 'TPLT') and not str(recordio.field(r, 'TPLT')).startswith('+'):
                return k
            best = best or k
    return best


def _item(gd, pr, edid, name, like='JournalGeneric'):
    rec = recordio.load(gd, gd.from_key(_game_key(gd, like, 'MISC')))
    rec['src'] = ''
    rec['subs'] = [s for s in rec['subs'] if s['tag'] not in ('SCRI',)]
    recordio.set_field(rec, 'EDID', edid, label='Editor ID')
    recordio.set_field(rec, 'FULL', name)
    for s in rec['subs']:
        if s['tag'] == 'DATA':
            for f in s.get('fields', ()):
                if f.get('name') == 'Value':
                    f['value'] = 0
    return rec


def _chest(gd, pr, edid, item_key):
    import api_characters as ac
    import sidequests
    rec = recordio.load(gd, gd.from_key(_game_key(gd, 'Footlocker01Empty', 'CONT')))
    rec['src'] = ''
    rec['subs'] = [s for s in rec['subs'] if s['tag'] not in ('CNTO', 'COED', 'SCRI')]
    recordio.set_field(rec, 'EDID', edid, label='Editor ID')
    ac.insert(rec, sidequests._cnto(gd, item_key, 1))
    return rec


class Built:
    """What ops made, for the lines and the quests."""


def ops(gd, pr, P=None):
    """(ops, report, lines, quests): records and refs (one apply), then the quests and lines to compile against them."""
    import api_quests as aq
    import api_scripts
    import piratedeal
    import questrec as qr
    import repstanding as RS
    import tes4
    from activity import _new_key
    if _mod_key(pr, COURT, 'QUST'):
        raise ValueError('the mod already has %s (Undo first)' % COURT)
    stand_q, stand_s = _mod_key(pr, RS.QUEST, 'QUST'), _mod_key(pr, RS.SCRIPT, 'SCPT')
    if not stand_q or not stand_s:
        raise ValueError('the standing step (repstanding) first')
    P = P or plan(gd, pr)
    S = P['spots']
    need = ['fang', 'tan', 'tan_chest', 'tenant', 'handover', 'buyer', 'gao', 'steward', 'distiller', 'gtenant', 'pickup',
            'wei', 'xu', 'he', 'compact_chest', 'store', 'camp'] + ['raider%d' % n for n in range(RAIDERS)] + \
           ['pirate%d' % n for n in range(BUYERS)]
    missing = [n for n in need if n not in S]
    if missing:
        raise ValueError('no spot for: %s' % ', '.join(missing))
    huang_fac = _mod_key(pr, 'FOLabHuangFaction', 'FACT')
    pirate = _pirate_base(pr)
    if not pirate:
        raise ValueError("the mod has no pirate of its own (FOLabPirate...) for the buyers and raiders")
    world = P['world']
    grid = gd.grid(world if not isinstance(world, str) else gd.from_key(world))
    cell = lambda x, y: gd.key(grid[(int(x // 4096), int(y // 4096))])
    out, rep, named = [], {'made': [], 'skipped': P['skipped']}, {}

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
    ctx = _faces(gd, pr)
    keys = {q: _new_key(pr) for q in VOICE}
    skeys = {q: _new_key(pr) for q in VOICE}
    # items and chests
    book = record(_item(gd, pr, 'FOLabAnTanBook', "Baron Tan's Tally Book"))
    compact = record(_item(gd, pr, 'FOLabAnCompact', "The Earls' Compact"))
    tchest = record(_chest(gd, pr, 'FOLabAnTanChest', book))
    cchest = record(_chest(gd, pr, 'FOLabAnCompactChest', compact))
    # people
    sexes = {'fang': 'M', 'tan': 'M', 'tenant': 'F', 'man': 'M', 'gao': 'M', 'steward': 'M', 'distiller': 'M', 'gtenant': 'F',
             'wei': 'M', 'xu': 'M', 'he': 'F'}
    people = {}
    pool = _standing(gd, pr)
    rep['recast'] = {}
    for k in ('fang', 'tan', 'tenant', 'man', 'gao', 'steward', 'distiller', 'gtenant', 'wei', 'xu', 'he'):
        spot = S['handover' if k == 'man' else k]
        got = _recast(gd, pr, pool, k, spot, sexes[k])
        if got:                             # (one of the Huáng already standing, given the role: their face is theirs alone)
            key, rec, (ck, rk) = got
            out.append({'op': 'remove', 'cell': ck, 'ref': rk})
            out.append({'op': 'record', 'key': key, 'record': rec})
            people[k] = key
            rep['recast'][k] = recordio.field(rec, 'EDID')
        else:
            people[k] = record(_huang(gd, pr, ctx, EDIDS[k], SAID_BY[k], k, sexes[k], huang_fac))
    refs = {}
    for k in ('fang', 'tan', 'tenant', 'gao', 'steward', 'distiller', 'gtenant', 'wei', 'xu', 'he'):
        refs[k] = place(people[k], S[k], EDIDS[k] + 'Ref')
    refs['man'] = place(people['man'], S['handover'], 'FOLabAnTanManRef')
    refs['buyer'] = place(pirate, S['buyer'], 'FOLabAnBuyerRef')
    for n in range(BUYERS):
        refs['pirate%d' % n] = place(pirate, S['pirate%d' % n], 'FOLabAnPickup%dRef' % n)
    for n in range(RAIDERS):
        refs['raider%d' % n] = place(pirate, S['raider%d' % n], 'FOLabAnRaider%dRef' % n)
    xmh = gd.key(piratedeal._game(gd, 'XMarkerHeading', 'STAT'))
    for k in ('handover', 'pickup', 'store', 'camp'):
        refs[k] = place(xmh, S[k], 'FOLabAn%sRef' % k.capitalize())
    refs['tan_chest'] = place(tchest, S['tan_chest'], 'FOLabAnTanChestRef', {'lock': {'level': T_LOCK, 'key': '', 'leveled': False}})
    refs['compact_chest'] = place(cchest, S['compact_chest'], 'FOLabAnCompactChestRef', {'lock': {'level': E_LOCK, 'key': '', 'leveled': False}})
    for n, e in enumerate(('CrateGenericNV', 'NVWaterCrateSqr01', 'CrateLarge01')):      # (the palace's grain store)
        try:
            s = S['store']
            place(gd.key(piratedeal._game(gd, e, 'STAT')), (s[0] + 120 * (n - 1), s[1] + 90, s[2]), 'FOLabAnStore%d' % n)
        except Exception:
            pass
    actors = set(people.values()) | {pirate}
    ext = {o['key']: {'type': 'ACHR' if o['ref']['base'] in actors else 'REFR', 'flags': tes4.PERSISTENT,
                      'subs': [{'tag': 'EDID', 'label': 'Editor ID', 'kind': 'z', 'value': o['ref']['edid']}]}
           for o in out if o['op'] == 'place'}
    B = Built()
    B.keys, B.skeys, B.people, B.refs, B.book, B.compact, B.stand_q, B.stand_s = keys, skeys, people, refs, book, compact, stand_q, stand_s
    B.ext = ext
    return out, rep, B


# ---------- the scripts ----------
def court_script():
    return '\n'.join([
        'scn FOLabAnCourtScript', 'short met', 'short asianpc', 'short nobles', 'short palace', '',
        'Begin GameMode',
        '\tif met == 0', '\t\tif player.GetDistance FOLabAnClerkFangRef < 1500', '\t\t\tset met to 1',
        '\t\t\tif player.GetIsRace Asian == 1', '\t\t\t\tset asianpc to 1', '\t\t\t\t%s' % _bump('huang', ASIAN_FACE),
        '\t\t\tendif', '\t\tendif', '\tendif',
        'End', ''])


def _bump(side, n):
    import repstanding as RS
    return RS.bump(side, n)


def _night(var='night'):
    return ['\tset %s to 0' % var, '\tif GameHour >= %d' % NIGHT[0], '\t\tset %s to 1' % var, '\tendif',
            '\tif GameHour < %d' % NIGHT[1], '\t\tset %s to 1' % var, '\tendif']


def _switch(refs, on):
    return ['\t\t%s.%s' % (r, 'Enable' if on else 'Disable') for r in refs]


def q1_script():
    hand = ['FOLabAnTanManRef', 'FOLabAnBuyerRef']
    L = ['scn FOLabAnSmallAccountScript', 'short night', 'short shown', 'short started', 'short lied', 'short told', 'short arrest', '',
         'Begin GameMode', '\tif started == 0', '\t\tset started to 1'] + _switch(hand, False) + ['\tendif'] + _night()
    # (the handover: on the beach by night while you're on the job)
    L += ['\tif GetStage %s >= 10' % Q1, '\t\tif GetStage %s < 30' % Q1, '\t\t\tif night != shown',
          '\t\t\t\tset shown to night', '\t\t\t\tif night == 1'] + ['\t\t' + s for s in _switch(hand, True)] + \
         ['\t\t\t\telse'] + ['\t\t' + s for s in _switch(hand, False)] + ['\t\t\t\tendif', '\t\t\tendif', '\t\tendif', '\tendif']
    L += ['\tif GetStage %s == 10' % Q1,
          '\t\tif night == 1', '\t\t\tif player.GetDistance FOLabAnTanManRef < %d' % WATCH, '\t\t\t\tif player.IsSneaking == 1',
          '\t\t\t\t\tif FOLabAnTanManRef.GetDetected player == 0', '\t\t\t\t\t\tSetStage %s 20' % Q1,
          '\t\t\t\t\tendif', '\t\t\t\tendif', '\t\t\tendif', '\t\tendif',
          '\t\tif player.GetItemCount FOLabAnTanBook >= 1', '\t\t\tSetStage %s 20' % Q1, '\t\tendif', '\tendif',
          '\tif GetStage %s >= 10' % Q1, '\t\tif GetStage %s < 30' % Q1, '\t\t\tif FOLabAnBaronTanRef.GetDead == 1',
          '\t\t\t\tSetStage %s 34' % Q1, '\t\t\tendif', '\t\tendif', '\tendif',
          '\tif arrest == 1', '\t\tset arrest to 2', '\t\tFOLabAnBaronTanRef.Disable', '\tendif',
          'End', '']
    return '\n'.join(L)


def q2_script():
    pick = ['FOLabAnPickup%dRef' % n for n in range(BUYERS)]
    L = ['scn FOLabAnGrainBookScript', 'short night', 'short shown', 'short started', 'short lied', 'short wrecked', 'short arrest',
         'short beaten', '', 'Begin GameMode', '\tif started == 0', '\t\tset started to 1'] + _switch(pick, False) + ['\tendif'] + _night()
    L += ['\tif GetStage %s >= 10' % Q2, '\t\tif GetStage %s < 30' % Q2, '\t\t\tif beaten == 0', '\t\t\t\tif night != shown',
          '\t\t\t\t\tset shown to night', '\t\t\t\t\tif night == 1'] + ['\t\t\t' + s for s in _switch(pick, True)] + \
         ['\t\t\t\t\telse'] + ['\t\t\t' + s for s in _switch(pick, False)] + ['\t\t\t\t\tendif', '\t\t\t\tendif', '\t\t\tendif', '\t\tendif', '\tendif']
    dead = ' && '.join('%s.GetDead == 1' % r for r in pick)
    L += ['\tif GetStage %s == 10' % Q2, '\t\tif %s' % dead, '\t\t\tset beaten to 1', '\t\t\tSetStage %s 20' % Q2, '\t\tendif', '\tendif',
          '\tif GetStage %s >= 10' % Q2, '\t\tif GetStage %s < 30' % Q2, '\t\t\tif FOLabAnViscountGaoRef.GetDead == 1',
          '\t\t\t\tSetStage %s 34' % Q2, '\t\t\tendif', '\t\tendif', '\tendif',
          '\tif arrest == 1', '\t\tset arrest to 2', '\t\tFOLabAnViscountGaoRef.Disable', '\tendif', 'End', '']
    return '\n'.join(L)


def q3_script():
    raid = ['FOLabAnRaider%dRef' % n for n in range(RAIDERS)]
    earls = ['FOLabAnEarlWeiRef', 'FOLabAnEarlXuRef', 'FOLabAnEarlHeRef']
    L = ['scn FOLabAnEarlsCompactScript', 'short night', 'short shown', 'short started', 'short early', 'short off', 'short moved',
         'short arrest', '', 'Begin GameMode', '\tif started == 0', '\t\tset started to 1'] + _switch(raid, False) + ['\tendif'] + _night()
    # (Liu Wei read the ground: the raiders wait at their camp by day, where you can hit them first)
    L += ['\tif early == 1', '\t\tif moved == 0', '\t\t\tset moved to 1'] + ['\t\t\t%s.MoveTo FOLabAnCampRef' % r for r in raid] + \
         _switch(raid, True) + ['\t\tendif', '\tendif']
    L += ['\tif GetStage %s == 10' % Q3, '\t\tif off == 0', '\t\t\tif early == 0', '\t\t\t\tif night != shown',
          '\t\t\t\t\tset shown to night', '\t\t\t\t\tif night == 1'] + ['\t\t\t' + s for s in _switch(raid, True)] + \
         ['\t\t\t\t\telse'] + ['\t\t\t' + s for s in _switch(raid, False)] + ['\t\t\t\t\tendif', '\t\t\t\tendif', '\t\t\tendif', '\t\tendif',
                                                                          '\tendif']
    L += ['\tif off == 1', '\t\tset off to 2'] + _switch(raid, False) + ['\tendif']
    dead = ' && '.join('%s.GetDead == 1' % r for r in raid)
    edead = ' && '.join('%s.GetDead == 1' % r for r in earls)
    L += ['\tif GetStage %s == 10' % Q3,
          '\t\tif %s' % dead, '\t\t\tSetStage %s 30' % Q3, '\t\tendif',
          '\t\tif %s' % edead, '\t\t\tset off to 1', '\t\t\tSetStage %s 36' % Q3, '\t\tendif', '\tendif',
          '\tif arrest == 1', '\t\tset arrest to 2'] + _switch(earls, False) + ['\tendif', 'End', '']
    return '\n'.join(L)


def _quest_plain(q, key_script, gd, pr, B):
    """The quest's stages and objectives (stage scripts set variables and pay; the quests' own scripts move refs)."""
    import piratedeal
    rep = piratedeal.REPS['huang'][0]
    has_rep = bool(_mod_key(pr, rep, 'REPU'))
    prep = piratedeal.REPS['pirates'][0]
    has_prep = bool(_mod_key(pr, prep, 'REPU'))
    obj = lambda n, on: 'SetObjectiveDisplayed %s %d %d\n' % (q, n, on)
    done = lambda n: 'SetObjectiveCompleted %s %d 1\n' % (q, n)
    pay = lambda side: ''.join('player.AddItem %s %d\n' % (e, k) for _t, e, k in PAY[side])
    palace = lambda: pay('palace') + ('AddReputation %s 1 1\n' % rep if has_rep else '') + _bump('huang', FACE) + '\n' + \
        'set %s.palace to %s.palace + 1\n' % (COURT, COURT)
    nobles = lambda: pay('nobles') + ('AddReputation %s 1 1\n' % prep if has_prep else '') + 'set %s.nobles to %s.nobles + 1\n' % (COURT, COURT)
    killed = lambda: ('AddReputation %s 1 1\n' % rep if has_rep else '') + 'set %s.palace to %s.palace + 1\n' % (COURT, COURT) + \
        ''.join('player.AddItem %s %d\n' % (e, 1) for _t, e, _k in PAY['palace'][:1])

    def stage(n, log, src=''):
        return {'index': n, 'entries': [{'flags': {}, 'conditions': [], 'next': '', 'log': log, 'script': {'source': src, 'parts': None}}]}
    end = lambda: obj(10, 0) + obj(20, 0) + obj(30, 0)
    if q == COURT:
        return {'edid': q, 'name': None, 'script': key_script, 'flags': {'start_enabled': True}, 'priority': 60, 'delay': 1.0,
                'stages': [], 'objectives': [], 'conditions': []}
    if q == Q1:
        stages = [stage(10, "Fang Jun, a magistrate's clerk at the Waimanalo courtyards, hired me for the palace: Baron Tan's tenants "
                            "vanish. Find out where, and bring proof.", obj(10, 1)),
                  stage(20, "I have proof: Baron Tan sells his tenants to the pirates.", done(10) + obj(20, 1)),
                  stage(30, "I gave Fang Jun the proof. The Shouwei took Baron Tan.", end() + 'set %s.arrest to 1\n' % q + palace()),
                  stage(32, "Baron Tan pays the palace its share now, for my silence.", end() + palace()),
                  stage(34, "Baron Tan is dead. Fang Jun called it messy, but done.", end() + killed()),
                  stage(36, "I took Baron Tan's bribe and told Fang Jun his land was clean.", end() + nobles())]
        objectives = [{'index': 10, 'text': "Find out where Baron Tan's tenants go", 'targets': []},
                      {'index': 20, 'text': "Deal with Baron Tan: the clerk, or Tan himself", 'targets': []}]
    elif q == Q2:
        stages = [stage(10, "Fang Jun sent me to Kailua: Viscount Gao's grain book lies, and the pirates eat the palace's maize. "
                            "Bring him in line.", obj(10, 1)),
                  stage(20, "I have proof: Viscount Gao pays the pirates in maize.", done(10) + obj(20, 1)),
                  stage(30, "Viscount Gao pays the palace now.", end() + palace()),
                  stage(32, "I gave Fang Jun the proof. The Shouwei went to Kailua for Viscount Gao.", end() + 'set %s.arrest to 1\n' % q + palace()),
                  stage(34, "Viscount Gao is dead.", end() + killed()),
                  stage(36, "I took Viscount Gao's bribe and told Fang Jun his books were true.", end() + nobles())]
        objectives = [{'index': 10, 'text': "Find proof that Viscount Gao feeds the pirates", 'targets': []},
                      {'index': 20, 'text': "Bring Viscount Gao in line", 'targets': []}]
    else:
        stages = [stage(10, "Fang Jun says three earls at Kane'ohe have a compact with the pirates: a raid on the palace's grain store "
                            "at the Border Post. Stop it.", obj(10, 1)),
                  stage(30, "I beat the raiders at the Border Post. The grain is safe.", end() + palace()),
                  stage(32, "I broke the earls' compact by talking. The raid is off.", end() + 'set %s.off to 1\n' % q + palace()),
                  stage(34, "I gave Fang Jun the earls' compact under their own seals. The earls are finished.",
                        end() + 'set %s.off to 1\nset %s.arrest to 1\nplayer.RemoveItem FOLabAnCompact 1\n' % (q, q) + palace()),
                  stage(36, "The three earls are dead. The raid will never come.", end() + killed()),
                  stage(38, "I told Earl He I'd be far from the Border Post at night. The earls paid me.", end() + 'set %s.off to 1\n' % q + nobles())]
        objectives = [{'index': 10, 'text': "Stop the earls' raid on the palace's grain store", 'targets': []}]
    return {'edid': q, 'name': NAMES[q], 'script': key_script, 'flags': {'start_enabled': True}, 'priority': 55, 'delay': 1.0,
            'stages': stages, 'objectives': objectives, 'conditions': []}


# ---------- the step ----------
def apply(pr, gd, P=None):
    import api_quests as aq
    import api_scripts
    import questrec as qr
    o, rep, B = ops(gd, pr, P)
    sc = api_scripts.scripts()
    plains = {q: _quest_plain(q, B.skeys[q], gd, pr, B) for q in VOICE}
    stubs = {B.keys[q]: qr.quest_record(dict(plains[q], stages=[], objectives=[])) for q in VOICE}
    known = dict(B.ext, **stubs)
    known.update({x['key']: x['record'] for x in o if x['op'] == 'record'})     # (the items and people made above)
    srcs ={COURT: court_script(), Q1: q1_script(), Q2: q2_script(), Q3: q3_script()}
    srecs = {}
    for q in VOICE:                         # (each script sees the others' variables: compiled in order, each added)
        c = sc.compile(srcs[q], B.skeys[q], 'quest', known)
        if not hasattr(c, 'subrecords'):
            raise ValueError('%sScript: %s' % (q, c))
        srecs[q] = sc._record_of(c, '%sScript' % q)
        known[B.skeys[q]] = srecs[q]
    for q in VOICE:
        o.append({'op': 'record', 'key': B.skeys[q], 'record': srecs[q]})
        o.append({'op': 'record', 'key': B.keys[q], 'record': stubs[B.keys[q]]})
        rep['made'] += ['%sScript' % q, q]
    T, lines = _lines(gd, pr, B, srecs)
    o += [{'op': 'record', 'key': k, 'record': r} for k, r in T['records']]
    rep['made'] += [recordio.field(r, 'EDID') for _k, r in T['records']]
    pr.apply(LABEL, o)
    more = []
    for q in VOICE:
        plain = json.loads(json.dumps(plains[q]))
        errors = aq.compile_quest(plain, aq.ModForms(gd, pr))
        if errors:
            raise ValueError('%s: %s' % (q, errors))
        more.append({'op': 'record', 'key': B.keys[q], 'record': qr.quest_record(plain)})
    pr.apply(LABEL, more + [{'op': 'record_new', 'record': aq._compiled_line(gd, pr, l)} for l in lines], merge=True)
    rep.update({'lines': len(lines), 'people': len(B.people), 'refs': len(B.ext),
                'named': sorted(v['subs'][0]['value'] for v in B.ext.values())})
    return rep


def _lines(gd, pr, B, srecs):
    """The topics (records) and lines (plain, compiled after the records are in)."""
    import api_quests as aq
    import questrec as qr
    from activity import _new_key
    G = qr.GREETING
    T, recs = {}, []
    av = {s: gd.key(next(f for f, (i, r) in gd.forms.items() if r.tag == 'AVIF' and gd.edid(f) == e)) for s, (_n, e) in SKILLS.items()}
    asian = gd.key(next(f for f, (i, r) in gd.forms.items() if r.tag == 'RACE' and gd.edid(f) == 'Asian'))
    tongue = _mod_key(pr, TONGUE, 'PERK')
    stim = gd.key(next(f for f, (i, r) in gd.forms.items() if r.tag == 'ALCH' and gd.edid(f) == 'Stimpak'))
    V = {q: _vars(srecs[q]) for q in VOICE}
    qv = lambda q, var, op, v: _cond('GetQuestVariable', op, v, B.keys[q], V[q][var])
    st = lambda q, op, v: _cond('GetStage', op, v, B.keys[q])
    sk = lambda s, op, v: _cond('GetActorValue', op, v, SKILLS[s][0], 0, 1)
    has = lambda item, n=1: _cond('GetItemCount', '>=', n, item, 0, 1)
    lines = []

    def topic(name, words, q):
        if name not in T:
            k = _new_key(pr)
            recs.append((k, qr.topic_record({'edid': 'FOLabAnTopic%s' % name, 'name': words, 'priority': 50.0, 'kind': 0,
                                             'quests': [{'quest': B.keys[x], 'links': []} for x in VOICE]})))
            T[name] = k
        return T[name]

    def line(tp, who, words, conds=(), end='', skill=None, choices=(), q=COURT):
        l = aq.new_line_plain(gd, pr, tp, B.keys[q], B.people.get(who, who), words, conditions=list(conds))
        if skill:
            l['skill'] = av[skill]
        if end:
            l['end'] = {'source': end, 'parts': None}
        l['choices'] = list(choices)
        lines.append(l)

    def check(tp, who, skill, need, passed, failed, on_pass='', on_fail='', conds=(), q=COURT, fail_choices=()):
        """A skill check: pass lines (eased for an Asian player character and Island Tongue on Speech and Barter), then the fail line."""
        line(tp, who, passed, [sk(skill, '>=', need)] + list(conds), on_pass, skill, q=q)
        if skill in EASED:
            line(tp, who, passed, [sk(skill, '>=', need - EASIER), _cond('GetIsRace', '=', 1, asian, 0, 1)] + list(conds), on_pass, skill, q=q)
            if tongue:
                line(tp, who, passed, [sk(skill, '>=', need - EASIER), _cond('HasPerk', '=', 1, tongue, 0, 1)] + list(conds), on_pass, skill, q=q)
        line(tp, who, failed, list(conds), on_fail, skill, choices=fail_choices, q=q)
    setv = lambda q, var, v=1: 'set %s.%s to %d' % (q, var, v)
    stage_to = lambda q, n: 'SetStage %s %d' % (q, n)
    # ---- Fang Jun: hiring, the three jobs, hearing back
    t_hire, t_pay = topic('Hire', W['hire'], COURT), topic('HirePay', W['hire_pay'], COURT)
    fang = 'fang'
    unhired = [st(Q1, '=', 0)]
    line(G, fang, W['fang_asian'] + ' ' + W['job1'], unhired + [_cond('GetIsRace', '=', 1, asian, 0, 1)], stage_to(Q1, 10))
    line(G, fang, W['fang_hi'], unhired, choices=[t_hire])
    check(t_hire, fang, 'Speech', HIRE, W['hire_yes'] + ' ' + W['job1'], W['hire_no'], stage_to(Q1, 10), conds=unhired, fail_choices=[t_pay])
    line(t_pay, fang, W['hire_paid'] + ' ' + W['job1'], unhired + [has(stim, 2)], stage_to(Q1, 10) + '\nplayer.RemoveItem Stimpak 2')
    line(t_pay, fang, W['hire_no'], unhired)
    t_proof1, t_clean1 = topic('Proof1', W['proof1'], COURT), topic('Clean1', W['clean1'], COURT)
    t_proof2, t_clean2 = topic('Proof2', W['proof2'], COURT), topic('Clean2', W['clean2'], COURT)
    t_compact = topic('Compact', W['compact'], COURT)
    line(t_proof1, fang, W['proof1_yes'], [st(Q1, '=', 20)], stage_to(Q1, 30))
    line(t_clean1, fang, W['clean1_yes'], [qv(Q1, 'lied', '=', 1), st(Q1, '<', 30)], stage_to(Q1, 36))
    line(t_proof2, fang, W['proof2_yes'], [st(Q2, '=', 20)], stage_to(Q2, 32))
    line(t_clean2, fang, W['clean2_yes'], [qv(Q2, 'lied', '=', 1), st(Q2, '<', 30)], stage_to(Q2, 36))
    line(t_compact, fang, W['compact_yes'], [st(Q3, '=', 10), has(B.compact)], stage_to(Q3, 34))
    on_job = [t_proof1, t_clean1, t_proof2, t_clean2, t_compact]
    line(G, fang, W['dead1'] + ' ' + W['job2'], [st(Q1, '=', 34), st(Q2, '=', 0)], stage_to(Q2, 10))
    line(G, fang, W['paid1'] + ' ' + W['job2'], [st(Q1, '=', 32), st(Q2, '=', 0)], stage_to(Q2, 10))
    line(G, fang, W['job2'], [st(Q1, '>=', 30), st(Q2, '=', 0)], stage_to(Q2, 10))
    line(G, fang, W['done2'] + ' ' + W['job3'], [st(Q2, '>=', 30), st(Q2, '<', 36), st(Q3, '=', 0)], stage_to(Q3, 10))
    line(G, fang, W['job3'], [st(Q2, '>=', 30), st(Q3, '=', 0)], stage_to(Q3, 10))
    line(G, fang, W['done3'], [st(Q3, '>=', 30), st(Q3, '<', 38)])
    line(G, fang, W['fang_wait'], [st(Q3, '>=', 30)])
    line(G, fang, "What you find? Talk.", [st(Q1, '>=', 10)], choices=on_job)
    # ---- stage 1: Baron Tan, his tenant, his man on the beach
    t_acc, t_blk, t_brb = topic('Accuse', W['accuse'], Q1), topic('Blackmail', W['black'], Q1), topic('Bribe1', W['bribe1'], Q1)
    t_treat, t_ask = topic('Treat', W['treat'], Q1), topic('Ask', W['ask'], Q1)
    open1 = [st(Q1, '>=', 10), st(Q1, '<', 30)]
    line(G, 'tan', shown('tan_hi'), open1, choices=[t_acc, t_blk, t_brb], q=Q1)
    check(t_acc, 'tan', 'Speech', T_ACCUSE, shown('tan_accuse'), shown('tan_accuse_no'), stage_to(Q1, 20), conds=[st(Q1, '=', 10)], q=Q1)
    check(t_blk, 'tan', 'Speech', T_BLACK, shown('tan_black'), shown('tan_black_no'), stage_to(Q1, 32), conds=[st(Q1, '=', 20)], q=Q1)
    line(t_brb, 'tan', shown('tan_bribe'), open1, setv(Q1, 'lied') + '\n' + ''.join('player.AddItem %s %d\n' % (e, k) for _t, e, k in PAY['nobles']), q=Q1)
    line(G, 'tenant', shown('tenant_hi'), open1, choices=[t_treat, t_ask], q=Q1)
    check(t_treat, 'tenant', 'Medicine', T_MED, shown('tenant_med'), shown('tenant_med_no'), stage_to(Q1, 20), conds=[st(Q1, '=', 10)], q=Q1)
    check(t_ask, 'tenant', 'Speech', T_TALK, shown('tenant_talk'), shown('tenant_talk_no'), stage_to(Q1, 20), conds=[st(Q1, '=', 10)], q=Q1)
    # ---- stage 2: Viscount Gao, his steward, his distiller, his tenant
    t_gpay, t_gbook, t_gbrb = topic('GaoPay', W['g_pay'], Q2), topic('GaoBook', W['g_book'], Q2), topic('Bribe2', W['g_bribe'], Q2)
    t_audit, t_count, t_pst = topic('Audit', W['audit'], Q2), topic('Count', W['count'], Q2), topic('PaySteward', W['pay_stew'], Q2)
    t_wreck, t_pump, t_child, t_ask2 = topic('Wreck', W['wreck'], Q2), topic('Pump', W['pump'], Q2), topic('Child', W['child'], Q2), topic('Ask2', W['ask2'], Q2)
    open2 = [st(Q2, '>=', 10), st(Q2, '<', 30)]
    line(G, 'gao', shown('gao_hi'), open2, choices=[t_gpay, t_gbook, t_gbrb], q=Q2)
    line(t_gpay, 'gao', shown('gao_ruined'), [st(Q2, '=', 20), qv(Q2, 'wrecked', '=', 1)], stage_to(Q2, 30), q=Q2)
    check(t_gpay, 'gao', 'Speech', G_PERSUADE, shown('gao_pay'), shown('gao_pay_no'), stage_to(Q2, 30), conds=[st(Q2, '=', 20)], q=Q2)
    line(t_gbook, 'gao', shown('gao_book'), open2 + [has(B.book)], stage_to(Q2, 30) + '\nplayer.RemoveItem FOLabAnTanBook 1', q=Q2)
    line(t_gbrb, 'gao', shown('gao_bribe'), open2, setv(Q2, 'lied') + '\n' + ''.join('player.AddItem %s %d\n' % (e, k) for _t, e, k in PAY['nobles']), q=Q2)
    line(G, 'steward', shown('stew_hi'), [st(Q2, '=', 10)], choices=[t_audit, t_count, t_pst], q=Q2)
    check(t_audit, 'steward', 'Science', G_SCI, shown('stew_sci'), shown('stew_sci_no'), stage_to(Q2, 20), conds=[st(Q2, '=', 10)], q=Q2)
    check(t_count, 'steward', 'Barter', G_BARTER, shown('stew_barter'), shown('stew_barter_no'), stage_to(Q2, 20), conds=[st(Q2, '=', 10)], q=Q2)
    line(t_pst, 'steward', shown('stew_bribe'), [st(Q2, '=', 10), has(stim, G_BRIBE)], stage_to(Q2, 20) + '\nplayer.RemoveItem Stimpak %d' % G_BRIBE, q=Q2)
    line(G, 'distiller', shown('still_hi'), open2 + [qv(Q2, 'wrecked', '=', 0)], choices=[t_wreck], q=Q2)
    check(t_wreck, 'distiller', 'Explosives', G_BOOM, shown('still_boom'), shown('still_boom_no'), setv(Q2, 'wrecked'), conds=open2, q=Q2)
    line(G, 'gtenant', shown('gten_hi'), [st(Q2, '=', 10)], choices=[t_pump, t_child, t_ask2], q=Q2)
    check(t_pump, 'gtenant', 'Repair', G_REPAIR, shown('gten_fix'), shown('gten_fix_no'), stage_to(Q2, 20), conds=[st(Q2, '=', 10)], q=Q2)
    check(t_child, 'gtenant', 'Medicine', G_MED, shown('gten_med'), shown('gten_med_no'), stage_to(Q2, 20), conds=[st(Q2, '=', 10)], q=Q2)
    check(t_ask2, 'gtenant', 'Speech', G_TALK, shown('gten_talk'), shown('gten_talk_no'), stage_to(Q2, 20), conds=[st(Q2, '=', 10)], q=Q2)
    # ---- stage 3: the earls, Liu Wei
    t_split, t_buy, t_look, t_surv = topic('Split', W['split'], Q3), topic('Buy', W['buy'], Q3), topic('Look', W['look'], Q3), topic('Surv', W['surv'], Q3)
    open3 = [st(Q3, '=', 10)]
    line(G, 'wei', shown('wei_hi'), open3, choices=[t_split], q=Q3)
    check(t_split, 'wei', 'Speech', E_SPEECH, shown('wei_split'), shown('wei_split_no'), stage_to(Q3, 32), conds=open3, q=Q3)
    line(G, 'xu', shown('xu_hi'), open3, choices=[t_buy], q=Q3)
    check(t_buy, 'xu', 'Barter', E_BARTER, shown('xu_buy'), shown('xu_buy_no'), stage_to(Q3, 32), conds=open3, q=Q3)
    line(G, 'he', shown('he_hi'), open3, choices=[t_look], q=Q3)
    line(t_look, 'he', shown('he_look'), open3, stage_to(Q3, 38), q=Q3)
    liu = _mod_key(pr, LIU_WEI, 'NPC_')
    if liu:
        line(G, liu, W['liu_hi'], open3 + [qv(Q3, 'early', '=', 0)], choices=[t_surv], q=Q3)
        check(t_surv, liu, 'Survival', E_SURV, W['surv_yes'], W['surv_no'], setv(Q3, 'early'), conds=open3, q=Q3)
    T['records'] = recs
    return T, lines
