# Waikiki: the next quests (plan, 21 Nov 2026; nothing built yet)

The user asked to "plan more quests". Built so far: "What the Sea Brought In" (castawayquest.py) and "The First Place on
the Way" at Kuliouou (kuliouquest.py). Everything below comes from `waikiki-story-plan.md`, cited by its section in
brackets. Where that plan is silent, an idea is marked **[proposed]** and waits for the user's yes. Each quest is built
the way `waikiki-quest-recipe.md` describes: one builder module, one Undo, the quest's own script moves every step,
silent lines, a test with a stand-in mod, and a rehearsal on a D: copy. **No caps** as rewards until Waikiki's money is
decided. Rewards come from FOLab's own gear: the clubs, the armour (`waikiki-armour-ideas.md`), the blades, and the
QLZ-87.

## The main line, after Kuliouou

**3. "The Road Past Niu"** [The first place on the way; the coast road's order]. **[proposed]**
- Starts when Kuliouou ends.
- Objectives: "Follow the coast road to Waikiki". The script marks Niu and then the Kāhala Hotel's land gate on the way.
- At the Kāhala trade ground, pirates and the Kahuna's men trade under each other's noses ("where the two sides meet and
  trade"). One line from a pirate at the gate: he knows the Pip-Boy and looks too long. This is the first sign the pirates
  know you ("Why the pirates attack you anyway").
- Ends at Waikiki's edge, when one of the locals already there greets you.
- New people: one pirate at the gate. Nothing else new.

**4. "Tribute Day"** [Waikiki: the court, the tribute going out; Tribute day; the seats].
- At the Royal Hawaiian you see the tribute yard (already built: crates, water, barrels) and the Kahuna's collectors
  bringing a valley's tribute in. Among it are people, who are sent on to the Natatorium's cages.
- **[decided, the user, 21 Nov 2026: "The Pip-Boy does it"]** The Pip-Boy gets you an audience. The court takes you for a captain's kin, as Kuliouou did. The Kahuna
  wants to know whose you are. "It was just given to me" isn't believed here either.
- **[decided, the user, 21 Nov 2026: "Kahuna sends you"]** He sends you to the Captain to be looked over. This sets up step 5 without the Kahuna saying anything
  he doesn't know ("The Kahuna and the truth": he only guesses).
- New people: the Kahuna, two collectors, a guard or two at the porch.
- Gear on them: the court's leiomano, and the Ali'i Feather Cloak and Mahiole on his guard.

**5. "The Captain's Ship"** [The ship; the Missouri aground; The Captain's bluff].
- You go aboard by the Natatorium's steps, the pier and the stair tower (already built) and meet the Captain on the
  quarterdeck.
- He knows more than the Kahuna about the runaway's Pip-Boy and doesn't say. He can look guilty ("both lose if the
  truth gets out") but isn't the answer.
- **[proposed]** The quest ends with the Captain sending you to the Kāhala Hotel with a message for the pirates. That
  leads into step 6.
- New people: the Captain, a few crew in military gear ("the Missouri will have military gear").

Steps 6 (the pirates: the Kāhala, the slave road up Pālolo) and 7 (the Vault) wait until 3 to 5 have been played. The
endings' triggers are still open in the story plan.

## Side quests that use what's in the world now

| Quest | Giver, place | What you do | Reward | Status |
|---|---|---|---|---|
| **The doctor's stock** | Waikiki's doctor, by the Royal Hawaiian | Her stimpaks are Vault medicine ("who has Vault medicine tells you who's selling people"). She asks you to bring medical supplies from a ruin on the road, so she depends less on the trade. | a first aid kit's levelled list | [proposed] |
| **A gun that fires** | Waikiki's gunsmith | Bring back a part from a pirate wreck at Koko Marina. He builds the QLZ-87 from it. | the QLZ-87 and its 25mm grenades | [proposed] |
| **Fish for the grocer** | Waikiki's grocer | Waikiki has no farmland ("lives off the valleys"). Carry a load from Mānoa, the Kahuna's breadbasket, past the toll post on the freeway. | food, and the grocer's goodwill | [proposed] |
| **Through Makapuʻu Gate** | the Huáng's guard at Makapuʻu Gate | The Pip-Boy, their "mandate of heaven", lets you walk Waimānalo; you are never fully accepted. Walk the road of gates to the ship's ramp and back without trouble. | a Huáng blade; the Lamellar Armor later, once trusted | [proposed]; uses only [The settlers and the trade] |
| **Press gang on the coast** | a local by the road (Niu) | A pirate press gang works the coast road ("people with routines"). Drive it off, or avoid it. | Salvaged Boarding Armor from the gang | [proposed] |
| **The Captain's bluff** | found aboard the Missouri | Find out her big guns can't fire. Who you tell changes the balance. | none; it is the storyline's hook | [decided storyline], details open |
| **Taxes due** | the Kahuna's collectors | Bring the Holdouts back to tribute (Rising with a side). | Koa Fighting Armor | [decided] as a task; details open |

New people stay few. Each side quest uses someone already standing in the world (the four storekeepers, the locals, the
Kuliouou people), or one person at a place already built.

## Questions for the user, one at a time

1. ~~How you get in to see the Kahuna.~~ Answered: the Pip-Boy gets you an audience (21 Nov 2026).
2. ~~Who sends whom.~~ Answered: the Kahuna sends you to the Captain (21 Nov 2026).
3. ~~Which side quests first.~~ Answered: the doctor's stock and Through Makapuʻu Gate (21 Nov 2026).
4. Still open from the story plan: which valley stops paying (proposed: the Tanks), and Waikiki's money.

## Built (21 Nov 2026)

The Doctor's Stock and Through Makapuʻu Gate: `app/sidequests.py`, `tests/test_sidequests.py` (17 pass). Rehearsed on a copy of
Waikiki: one Undo each, nothing wrong in health of their own. The trunk stands by the road at (22528, -23092); the guard
outside Makapuʻu Gate, the goal at the last gate by the ship. The doctor's reward: five stimpaks and two goes of the first
aid box's healing list. Not yet in Waikiki or seen in game.

## Build order, once agreed

1. "The Road Past Niu".
2. "Tribute Day" (the Kahuna and the collectors placed, with their gear).
3. "The Captain's Ship".
4. The side quests, one module each.

Each is rehearsed on a D: copy and goes into Waikiki only on the user's go, through the story session.
