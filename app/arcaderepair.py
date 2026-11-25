"""Repair at the Kilauea's arcade (docs/waikiki-speech-science.md K2; the user's yes, 25 Nov 2026, via the Workshop):
some machines are broken, Repair 55 fixes one, Repair 85 rigs one to pay better until the court notices.

All in the arcade's one object script (arcadeset's FOLabKilaueaArcadeScript, on every cabinet, bank and pachinko machine).
An object script's variables belong to each placed machine, so each one keeps its own state:
- The first time you use a machine, it is broken `BROKEN` times in 100 (`state` 1); otherwise it works (2).
- **Broken:** a message box (`MSGS`):
  - With Repair `FIX` and one Scrap Electronics, or the Tinkerer perk (FOLabPerkTinkerer: no part), "[Repair 55] Fix it"
    or "Leave it". Fixing takes the part (not with Tinkerer) and the machine works from then on.
  - With the skill but no part, it says what it takes. Without the skill, it says it is beyond you for now.
- **Working, with Repair `RIG`:** "Play", "[Repair 85] Rig it to pay better" or "Leave it", until you play it once
  (`offered`). A rigged machine (3) is played without asking.
- **Playing:** the game's slot menu on the arcade's casino, as before. The script notes your kala (Caps001) when the menu
  opens. When you are back in play with a different count, that session is over:
  - At a rigged machine, a session that came out ahead pays `BONUS` per cent more (at most `BONUS_MOST`).
  - Then, `NOTICE` times in 100, a court steward has been watching. The court's score drops `CAUGHT` (repstanding's
    `bump`), you gain one infamy with the court (FOLabRepCourt), and the machine is put right (2).
  - The slot menu shows only the money after each spin, never a win by itself, so a "win" here is a session that ended up.

Nothing is voiced: these are message boxes, which the game shows as words only.

    ops(gd, pr)    (ops, report): the messages and the script compiled again in place, one Undo (`LABEL`)
"""
import arcadeset as A
import repstanding as RS

LABEL = "Repair at the Kilauea's arcade"
BROKEN = 30             # (in 100, a machine broken when first used)
FIX, RIG = 55, 85
BONUS, BONUS_MOST = 50, 100
NOTICE, CAUGHT = 15, 5
PART = 'ScrapElectronics'
TINKERER = 'FOLabPerkTinkerer'
REP = 'FOLabRepCourt'
REPAIR = 39             # (the Repair actor value, as GetActorValue reads it: skillcheck.SKILLS)
DEAD = "The machine is dead: a dark screen and a smell of burnt wiring. Somewhere inside, swallowed tokens rattle."
# editor ID: (words, buttons); no buttons is a box with one OK
MSGS = {
    'FOLabArcadeFixMsg': (DEAD, ['[Repair %d] Fix it (one Scrap Electronics)' % FIX, 'Leave it']),
    'FOLabArcadeFixFreeMsg': (DEAD, ['[Repair %d] Fix it' % FIX, 'Leave it']),
    'FOLabArcadeNoPartMsg': (DEAD + " [Repair %d] You could fix it with a piece of scrap electronics." % FIX, []),
    'FOLabArcadeNoSkillMsg': (DEAD + " [Repair %d] Fixing it is beyond you for now." % FIX, []),
    'FOLabArcadeFixedMsg': ("The screen flickers, the lights come up, and the machine plays its little tune.", []),
    'FOLabArcadeRigMsg': ("The machine hums along, as honest as a church. A few twists inside and it would pay better, "
                          "until somebody noticed.", ['Play', '[Repair %d] Rig it to pay better' % RIG, 'Leave it']),
    'FOLabArcadeRiggedMsg': ("A wire moved, a spring bent. It will pay better now.", []),
    'FOLabArcadeCaughtMsg': ("A court steward has been watching the machine. He opens it, puts it right, and writes down "
                             "your name.", []),
}


def message(edid, words, buttons):
    subs = [{'tag': 'EDID', 'label': 'Editor ID', 'kind': 'z', 'value': edid},
            {'tag': 'DESC', 'label': 'Description', 'kind': 'z', 'value': words},
            {'tag': 'FULL', 'label': 'Name', 'kind': 'z', 'value': A.CASINO_NAME},
            {'tag': 'INAM', 'label': 'Icon', 'kind': 'F', 'value': ''},
            {'tag': 'DNAM', 'label': 'Flags', 'kind': 'struct', 'fields': [{'name': 'Flags', 'code': 'I', 'value': 1}]}]
    subs += [{'tag': 'ITXT', 'label': 'Button text', 'kind': 'z', 'value': b} for b in buttons]
    return {'type': 'MESG', 'flags': 0, 'src': '', 'subs': subs}


def script_source(money):
    """The arcade's script with repairing and rigging. money: the stake's editor ID (Caps001, kala)."""
    play = ['set before to player.GetItemCount %s' % money, 'set playing to 1',
            'ShowSlotMachineMenuParams %s 1 25 0' % A.CASINO_EDID]
    L = ['scn %s' % A.SCRIPT_EDID,
         'short state', 'short offered', 'short asked', 'short button', 'short playing', 'long before', 'long n', '',
         'Begin OnActivate',
         'if IsActionRef player == 0', 'return', 'endif',
         'if state == 0', 'if GetRandomPercent < %d' % BROKEN, 'set state to 1', 'else', 'set state to 2', 'endif', 'endif',
         'if state == 1',
         'if player.GetActorValue Repair >= %d' % FIX,
         'if player.HasPerk %s' % TINKERER, 'ShowMessage FOLabArcadeFixFreeMsg', 'set asked to 1',
         'elseif player.GetItemCount %s > 0' % PART, 'ShowMessage FOLabArcadeFixMsg', 'set asked to 1',
         'else', 'ShowMessage FOLabArcadeNoPartMsg', 'endif',
         'else', 'ShowMessage FOLabArcadeNoSkillMsg', 'endif',
         'elseif state == 2 && offered == 0 && player.GetActorValue Repair >= %d' % RIG,
         'ShowMessage FOLabArcadeRigMsg', 'set asked to 2',
         'else'] + play + ['endif', 'End', '',
         'Begin GameMode',
         'if asked',
         'set button to GetButtonPressed',
         'if button == -1', 'return', 'endif',
         'if asked == 1 && button == 0',
         'if player.HasPerk %s == 0' % TINKERER, 'player.RemoveItem %s 1' % PART, 'endif',
         'set state to 2', 'ShowMessage FOLabArcadeFixedMsg',
         'elseif asked == 2 && button == 0',
         'set offered to 1'] + play + [
         'elseif asked == 2 && button == 1',
         'set state to 3', 'ShowMessage FOLabArcadeRiggedMsg',
         'endif',
         'set asked to 0',
         'return',
         'endif',
         'if playing',
         'if GetDistance player > 1000', 'set playing to 0', 'return', 'endif',
         'set n to player.GetItemCount %s' % money,
         'if n == before', 'return', 'endif',
         'set playing to 0',
         'set n to n - before',
         'if n > 0 && state == 3',
         'set n to n * %d / 100' % BONUS,
         'if n > %d' % BONUS_MOST, 'set n to %d' % BONUS_MOST, 'endif',
         'if n > 0', 'player.AddItem %s n' % money, 'endif',
         'if GetRandomPercent < %d' % NOTICE,
         'set state to 2', RS.bump('court', -CAUGHT), 'AddReputation %s 0 1' % REP, 'ShowMessage FOLabArcadeCaughtMsg',
         'endif',
         'endif',
         'endif',
         'End', '']
    return '\n'.join(L)


def ops(gd, pr):
    """(ops, report): the messages, then the arcade's script compiled again in place."""
    import recordio
    import api_quests as aq
    import api_scripts
    edid = {recordio.field(r, 'EDID'): k for k, r in pr.records.items()}
    for need in (A.SCRIPT_EDID, A.CASINO_EDID, RS.QUEST, TINKERER, REP):
        if need not in edid:
            raise ValueError('the mod has no %s yet' % need)
    if any(m in edid for m in MSGS):
        raise ValueError("the mod has the arcade's repairs already")
    _money, money = A._money(gd, pr)
    names = list(MSGS)
    keys = dict(zip(names, aq._reserve(pr, len(names))))
    msgs = {e: message(e, *MSGS[e]) for e in names}
    extra = {keys[e]: msgs[e] for e in names}
    sc = api_scripts.scripts()
    text = script_source(money)
    c = sc.compile(text, edid[A.SCRIPT_EDID], 'object', extra)
    if not hasattr(c, 'subrecords'):
        raise ValueError("the arcade's script does not compile: %s" % (c,))
    old = pr.records[edid[A.SCRIPT_EDID]]
    script = sc._record_of(c, A.SCRIPT_EDID, flags=old.get('flags', 0), src=old.get('src', ''))
    out = [{'op': 'record_new', 'record': msgs[e]} for e in names]
    out.append({'op': 'record', 'key': edid[A.SCRIPT_EDID], 'record': script})
    return out, {'messages': keys, 'script': edid[A.SCRIPT_EDID], 'script_bytes': len(c.data), 'money': money,
                 'vars': [n for _k, n, _i in c.vars], 'text': text}
