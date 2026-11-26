"""K1, the Missouri's guns (missouriguns.py): the parts of the step that need no live mod. The quest's script (the truth known
by the fire control, the block's days, the raid by night, three salvos each landing on its target), the breech's script (Repair
50 / 75 / 95 and the parts), the stages and their consequences, the seals' recipe, the Guard's five lines. The whole step is
rehearsed on a copy of the live mod (its places, crew spots and voicing); this checks what it writes. Nothing near the game."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import gamedata  # noqa: E402
import missouriguns as MG  # noqa: E402
import project  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


q = MG.quest_script()
check('the truth from the fire control terminal', 'if FOLabCaptainsBluff.knows == 1' in q)
check('the breech block comes after its days, to the crate at Alewa Fort', 'GameDaysPassed >= block_day' in q and 'FOLabKalihiCrateRef.Enable' in q)
check('the raid comes by night once the block is fitted; sooner if the charges were bought', 'if night == 1' in q and 'set raid_day to GameDaysPassed\n' in q
      and 'FOLabMissouriRaider5Ref.Enable' in q)
check('three salvos, each three shells on its target', 'set salvos to %d' % MG.SALVOS in q and q.count('FOLabMissouriTargetFlotillaRef.PlaceAtMe NellisArtilleryExplosion') == 3
      and 'FOLabMissouriTargetCraterRef' in q and 'SetStage FOLabMissouriGuns 90' in q)
check('selling the secret comes out with the first salvo', 'if told == 3' in q and 'SetStage FOLabMissouriGuns 88' in q)
b = MG.breech_script({k: 'M%s' % k for k in MG.MESSAGES})
check('the breech: Repair 50 tells the truth, 75 the parts, 95 fires (after the raid, with the seals and three charges)',
      'GetActorValue Repair >= 50' in b and 'GetActorValue Repair >= 75' in b and 'GetActorValue Repair >= 95' in b
      and 'raid_done == 1' in b and 'FOLabDryCharge >= 3' in b and 'RemoveItem FOLabRecoilSeals 1' in b)
check("Gunner's Mate: one part fewer (no seals), only where the mod has the perk", 'HasPerk FOLabPerkGunnersMate' in MG.breech_script({k: 'M%s' % k for k in MG.MESSAGES}, True) and 'HasPerk' not in b)
G = gamedata.GameData()
pr = project.Project.create('Missouri Guns Test')
plain = MG.quest_plain(G, pr, '+000001')
stages = {s['index']: s['entries'][0]['script']['source'] for s in plain['stages']}
check('stages from the truth to the last salvo', sorted(stages) == [10, 20, 30, 40, 42, 45, 50, 55, 60, 70, 72, 74, 76, 80, 82, 84, 86, 88, 90, 92, 94, 96], sorted(stages))
check('telling the Captain first: Guard fame, he breaks with the Kahuna', 'FOLabRepGuard 1 2' in stages[70] and 'FOLabCaptainBroke' in stages[70])
check('a salvo on the court: the court turns on you, broken', 'SetEnemy FOLabKahunaCourtFaction PlayerFaction' in stages[84] and 'FOLabCourtBroken' in stages[84])
check('on the Flotilla, the Kahala, the crater: their globals', 'FOLabFlotillaHit' in stages[80] and 'FOLabKahalaWarned' in stages[82] and 'FOLabVaultShelled' in stages[86])
check('repeatable salvos, start enabled', plain['flags'] == {'start_enabled': True, 'repeat_stages': True})
r = MG._recipe(G, '+000002')
check('the seals: a recipe at Repair 60 of tape, glue and belts', any(f['name'] == 'Level' and f['value'] == 60 for s in r['subs'] if s['tag'] == 'DATA' for f in s['fields'])
      and sum(1 for s in r['subs'] if s['tag'] == 'RCIL') == 3 and any(s['tag'] == 'RCOD' and s['value'] == '+000002' for s in r['subs']))
check('the Guard has five lines on Your Name on the Water', len(MG.SIDE_LINES) == 5 and MG.GUARD_OBJ == 40)
check('no line over 150 characters', all(len(v) <= 150 for v in list(MG.W.values()) + list(MG.GREET.values())), max(len(v) for v in MG.W.values()))
check('the Order: a Captain, 7 Knights in their suits and the racked Haugen suit, 10 Squires, 10 crew',
      len(MG.KNIGHTS) == 7 and len(MG.SQUIRES) == 10 and len([k for k in MG.CREW if k not in MG.KNIGHTS and k not in MG.SQUIRES and k not in ('captain', 'lord', 's1', 's2')]) == 11)
check('Power Armor Training when the guns fire, and when you join', 'AddPerk PowerArmorTraining' in stages[60] and 'AddPerk PowerArmorTraining' in stages[92])
check("a Squire: the Order's faction and combat armour; a Knight: the Haugen suit from the armoury", 'AddToFaction FOLabCaptainsGuardFaction' in stages[92]
      and 'give to 1' in stages[94] and 'FOLabOrderArmouryLockerRef.RemoveAllItems player' in MG.quest_script())
check("a Knight's death makes a Squire heir (any of the seven)", MG.quest_script().count('set heir to 1') == 7)
