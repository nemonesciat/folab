# Waikiki: making Speech and Science worth taking (ideas to choose from, 25 Nov 2026)

The user, 25 Nov 2026: "We need to add plenty of uses for science and speech skills in this mod. As it stands, they are
all basically worthless right now. Speech should get you through many checks and encounters ... Maybe it could have
recurring utility by allowing you to deal with pirates and huang more effectively ... Science needs similar treatment, we
need many more doors locked behind terminals, and terminals that hold information, some lore based, some with secrets in
the world."

**This is a menu, not a plan.** Nothing here is built. Marks: **[decided]** is lore the user already settled (story
plan, decisions); **[proposal]** is new story or a new person, for the user to keep or strike. Work: **S** small (lines
on someone already standing, a terminal in a room already built), **M** medium (a few new records, a script, a
rehearsal), **L** large (a new place, people, or an engine question to settle first).

## In short

- **Today there are no Speech or Science checks anywhere in Waikiki.** Not one dialogue line asks for Speech, and there
  is not one terminal of the mod's own. The game's own terminals were taken out on purpose (townbuild leaves them out of
  borrowed rooms, the new districts replace those rooms, the Vault drops other vaults' terminals). The ~300 locks the loot
  work added are lockpick locks.
- **Speech** fits the island best as *talking your way through people's routines*: the toll post, the Kāhala trade
  ground, the Huáng gates, collectors and catchers on the roads, and a "standing" with each side that good talk builds and
  lets you spend. Plus one or two checks in every quest that already exists.
- **Science** fits as *the old world's machines that only a few can read*: terminals that open offices, safes and
  armouries in the hard bands; terminals whose logs tell the island's history and point to caches and ways in; and power
  (generators, the Missouri, the Vault) that Science lets you understand or fix.
- **The engine question is answered** (FOLab Skill Proof, the user's run in nv-rs-newest, 25 Nov 2026):
  - in nv-rs the "[Speech n/N]" checks show, the hacking screen works, and result scripts run, on lines and on terminal
    menu items. So Speech checks and terminal locks are wired the game's usual way;
  - one thing didn't work: a quest script watching for a note (GetHasNote) never unlocked its door. FOLab doesn't use
    that route.

## What exists now (checked 25 Nov 2026)

| Thing | Speech | Science |
|---|---|---|
| The opening, What the Sea Brought In, The First Place on the Way | none | none |
| The Doctor's Stock, Through Makapuʻu Gate | none (the gate opens on the Pip-Boy, not Speech) | none |
| Silk for Waikiki, Pests in the Maize, Oil for the Gate Guns | none | none (Oil asks for repair kits) |
| Kahuna Palms (ghoul tower) | none (the watchman gives the keys) | none |
| People's own lines (peopletalk, waikikilife, factionfolk) | none | — |
| Terminals of the mod's own | — | none |
| Locks | — | ~300 by lockpick; keys on finds; the Vault's Council Key |

What FOLab already makes: dialogue lines with conditions (`questrec.py`; a line's condition can be "player's Speech is
at least N"; the line's speech-challenge flag and difficulty are read and written), quest scripts that watch the world
(`scriptc.py`, with `GetActorValue`, `GetHasNote`, `AddNote`, `GetLocked`, `SetFactionReaction`, `AddReputation`,
`RewardXP`, `ShowBarterMenu`), locks and keys on any door, container or terminal (`refprops`), terminal records as data
(`schema.py` TERM: difficulty, menu items, result text, a note shown, sub-menus). What was **missing** on 25 Nov:
- a terminal maker: now `terminals.py`;
- a test that speech-check lines and the hacking screen work in nv-rs: done, they do;
- reputation records for the island's sides: still missing.

## How a check is wired (proven in nv-rs, 25 Nov 2026)

- **Speech** (read from FalloutNV.esm's 538 Speech lines and nv-rs's dialogue menu): a check is a pair of lines under one
  prompt, both carrying the line's skill (KNAM = the Speech skill).
  - The pass line's condition is "GetActorValue Speech >= N, on the player"; the fail line's is "< N".
  - The game writes "[Speech 40/55]" in front of the prompt by itself from those two, and counts "Speech Successes" or
    "Speech Failures".
  - Each line's own result script does what follows: a stage, a reward, a door. The proof showed it running in nv-rs.
- **Science:** a terminal's menu item runs its result script (`<ref>.Unlock`, `SetUnconscious 1` for a robot) and can
  show a note, which lands in the Pip-Boy. Both are proven in nv-rs. The terminal's hacking difficulty and the door's
  lock are fields FOLab writes (`terminals.py`).
- **Not used:** a quest script watching for a note (GetHasNote) didn't unlock the proof's north door, and the cause
  wasn't found.
- **XP:** every pass gives XP (`RewardXP`), as the game does, so a talker levels like a fighter.

## The six tiers (both skills)

The user, 25 Nov: "there should be like 5-6 of them and there should be some 'very hard' speech checks in the game, not
many of course, they have to be special, but having 95+ speech talks you out of or into some wild shit".

| Tier | Skill | Where it's met | What a pass is worth | How many |
|---|---|---|---|---|
| 1 Easy | 25 | Hanauma, Kuliʻouʻou, the coast road's start | a little more: a share, a word, a price | many |
| 2 | 40 | Waikiki, the toll post, the Huáng's gate | a shortcut, a gift, a door opened politely | many |
| 3 | 55 | Kāhala, the ridges, Waimānalo | a fight skipped, a better reward, a place let in | many |
| 4 | 70 | the freeway posts, Loa Gate, Alewa Fort | a faction's men stand down, a secret told | some |
| 5 Hard | 85 | the Flotilla, the Missouri, the Heights, behind the wall | a whole quest step another way | few |
| 6 Very hard | 95+ | one each at the great moments | a quest or a faction turned round (below) | 4–6 in the game |

Science follows the same steps: terminals in tier 1 near the start (few, and nothing locked within the loot plan's `SAFE`),
tier 4–5 in the armouries, the Missouri and the hard band, tier 6 for one or two terminals that change the story (the
Missouri's fire control, the Vault's reactor). The game's own hacking difficulties are five (very easy 0 to very hard
100); a tier-6 terminal is "very hard" with an added script condition of Science 95, so it's met rarely.

### The very hard checks (Speech 95+, rare, each a turn in the story)

All on decided people and places; what they lead to is a **[proposal]** for the user to keep or strike.

1. **The Kahuna, at the audience (Tribute Day) [proposal].** The Pip-Boy gets you in [decided]. Speech 95: you play the
   captain's kin he takes you for so well that he names you to his court on the spot: a title of the court, the
   collectors and guards friendly everywhere, the Royal Hawaiian's upper floors open. (He still only guesses about the
   trade [decided]: you win the showman, not the truth.)
2. **The Captain, on the quarterdeck (The Captain's Ship) [proposal].** Speech 100: you tell him you know the big guns
   can't fire [decided storyline] and talk him into keeping your silence as a deal: he makes you his man ashore. The
   whole "Captain's bluff" storyline goes another way: instead of choosing whom to tell, you hold it over him.
3. **The Flotilla's captain, Io Kanahele [decided name; proposal].** Speech 95, cornered in her cabin: she lets you walk
   off the Flotilla with the pens opened [the pens are decided], rather than fight you to the last deck, because you
   convince her the Vault will drop her once she's no use. The dungeon ends in talk.
4. **The Huáng elders on the freighter [decided: three elders aboard; proposal].** Speech 95 (the one English-speaking
   elder): they show you the secret cliff trail up to the Vault [decided: the settlers know it], which they've shown no
   outsider. The settlers' back way opens to you without a fight or a theft.
5. **A pirate captain with a Pip-Boy [decided: the captains are the Vault's own, never allowed to tell; proposal].**
   Speech 100: he tells you what's at the top of the mountain, breaking the rule he lives by. The most dangerous line in
   the game: if anyone sees him, he's dead, and you're marked.
6. **The Heights' ghouls [decided: they want into the Vault; proposal].** Speech 95: they give you everything their
   families kept from the Vault's builders (the old reservation codes, a mansion's plans) and swear their people to you,
   so whoever holds the Vault later has the Heights behind them.

Pick at most six; the user said they must be special.

---

## Speech

### A. Checks in the quests that already exist (S each, lines on people already standing)

| Where | Check | Pass | Fail |
|---|---|---|---|
| Hanauma, the beachcomber, after the lockbox (What the Sea Brought In) | Speech 25: "Half? I swam for it." | a bigger share: one more duffle-bag roll | his half as now, and a sour line |
| Kuliʻouʻou, Leilani by the fire (The First Place on the Way) | Speech 40: press her on "a captain's people" | she says who Kuliʻouʻou pays each tribute day and where the catchers bring people (a map marker at the pirates' freeway post) | she closes up. **The sale itself stays unstoppable [decided: "You can do nothing about the sale but watch"].** |
| Waikiki, Dr. Albright (The Doctor's Stock) | Speech 40 when you hand the supplies over: "Some of these are worth more than five stimpaks." | 2 more stimpaks and Med-X | as now |
| Makapuʻu Gate guard (Through Makapuʻu Gate) | Speech 55, on the way back: ask to be let further than the ship's ramp | leave to walk the town's courtyards too, and the Lamellar Armor offered for sale later | "the mandate takes you to the ramp, no further" |
| Lin Meihua (Silk for Waikiki) | Speech 55 with Linda Moreno: haggle for the Huáng | a better crate (more goods), Lin Meihua adds a gift | as now |
| Liu Wei (Oil for the Gate Guns) | Speech 40: talk him into one repair kit and your word | quest done with one kit, he's a little short with you later | needs two |
| Kahuna Palms, the court watchman | Speech 55 when you bring the penthouse key back: "People are moving in because of me." | the penthouse's storeroom key as well (a locked closet of the court's, keyed finds) | as now |

### B. Recurring: the pirates (M to L)

What's decided: the pirates are the raider faction, everywhere and disorganised; they meet and trade with the Kahuna's men
at the Kāhala trade ground; those who know the Pip-Boy are told to find you; your reputation outgrows the mark. So Speech
with pirates is about *crews that don't know you yet* and *places where trade is the rule*.

1. **The Kāhala trade ground (M).** Neutral by custom: nobody fights outside the land gate. Speech 40 to get a pirate
   trader to deal with you at all (a barter menu of boat goods, power cells, ammo); Speech 70 to be let in through the
   land gate to the yard and their quartermaster. Fail: sold to at a mark-up, or told to clear off. **[proposal]** a
   pirate trader standing at the trade ground (one new person).
2. **Press gangs on the coast road (M).** A gang stopping travellers [press gangs are in the decided "people with
   routines"]. Speech 55: "I'm buying, not selling" (you pass); Speech 85: you send them after someone else's cart (they
   leave the road for a day). Fail: the fight, as now.
3. **The pirates' freeway post over the Pālolo junction (M).** People are held there before the climb [decided]. Speech
   65: talk the guard into letting you onto the deck "to look at the stock" without a fight; Speech 95: he lets one
   captive go to you "for the Vault's cost", paid in goods. **[proposal]**: the freed one could later turn up in Waikiki
   [the user: "freed captives could end up in Waikiki someday, not important yet"].
4. **The Flotilla (L, later).** A hostile dungeon [decided]. One Speech 85 line at the first gangplank: pass as a buyer
   once, see the pens and the deck before the shooting starts, and the quartermaster's whereabouts (he carries the store's
   key [decided]).
5. **Standing with the pirates (M, needs a reputation record).** Each pass above adds a little "known as a dealer"; at
   enough of it, crews at the Kāhala and Koko Marina stop being hostile on sight and the Crow's Nest will talk. Those who
   know the Pip-Boy still hunt you until the story says otherwise.

### C. Recurring: the Huáng (M)

What's decided: you can get on with them to an extent, never fully accepted; the Pip-Boy is a "mandate of heaven"; lose
standing and you're unwelcome, then hostile. Most speak Mandarin, some plain English, a few broken English.

1. **Standing that Speech can mend (M).** If you trespass (the freighter's hold, a courtyard after dark), a Shouwei
   stops you before turning hostile: Speech 55 to apologise properly and be marched out instead of shot, once each time
   you're caught. Ties straight to the decided "unwelcome, then hostile".
2. **The freighter's hold (M).** The hold stays locked and an elder holds its key [decided]. Speech 85 with the English
   speaking elder (or Zhao Lei's broken English through a check of 95): he opens it to show you their stores, as a guest.
   Fail: he refuses politely; the hold stays a lockpick-or-steal job, and taking from it is stealing [decided].
3. **Trade terms (S).** The Huáng containers already sell clothes (factionfolk's trade lists). Speech 55 with the trading
   courtyard's English speaker: the Lamellar Armor and their guns are offered to you, not only silk.
4. **The Pali and the other checkpoints (M).** Who holds them is still the user's to say; if it's the Huáng, a Speech check
   to pass at night [the Nuʻuanu draft has their gate shut at sunset] instead of going round.

### D. Recurring: the court (S to M)

1. **The toll post on the freeway (S once money is decided).** Speech 40: waved through for nothing as "the Kahuna's
   guest" (the Pip-Boy helps here); fail, pay the toll [decided: the toll post charges a toll, amount when money is
   decided].
2. **Tribute day's collectors (M).** On the day, collectors are on the roads [decided: hide, help or rob them]. Add a
   fourth: Speech 70 to talk them out of taking one family's son or daughter this time. It costs them nothing they'll
   admit; the family gives you something small. Fail: they take them anyway.
3. **Catchers before tribute day (M).** Catchers hunt anyone nobody will miss [decided]. Speech 40 lets the Pip-Boy speak
   for you (they back off at once); at 85 you send them away from a stranger they've cornered.
4. **The Holdouts, "Taxes due" (M).** Bringing them back to tribute [decided as a task]. Speech 85 does it without a
   fight (they pay, grudging); a fail or no check means force. Speech also opens their trapped trails' gate: they show you
   the safe way.

### E. Encounters in the wild (M each, uses worldlife's scene spots)

- **A runaway on the Crest Trail and their hunters [decided: runaways and hunters are a routine].** Speech 55: point the
  hunters the wrong way; the runaway, out of reach of the settlers' handover, tells you one thing about "up there" (a line,
  a rumour, no more than the story allows).
- **The watcher at St. Louis Heights [decided: he sells what he sees].** Speech 55: half his price for the news; 75: he
  tells you who went up the slave road last week (a pointer to the waystation's cages).
- **Loa Gate's market [decided: the den of scum].** Speech gets you past the door crew without paying the "visitor's
  share" (35), and a meeting with whoever runs it (75) **[proposal: the founder's name and what he wants are the user's]**.
- **The Heights [decided: the ghouls want into the Vault].** Speech 70: they tell you why the Vault shut them out, and
  ask you to find a way in (sets up Science below).

---

## Science

### F. Terminals that lock things (the user's "many more doors locked behind terminals")

The rule: a terminal beside or inside each locked thing, its hacking difficulty by loot band; when hacked, a menu item
"Release lock" shows a note, the place's script sees the note and unlocks. A few also have a password on a note
elsewhere (the game's own way), so non-scientists have a second route.

| Where | What it opens | How many | Science | Work |
|---|---|---|---|---|
| The court district's **offices and named places** (the interiors work left these as they were) | the back office, a floor safe, a records room | ~15–20 | 25–55 | M |
| **Clinics** (12 places, loot plan) | the locked medicine store | 12 | 40–55 | S each, M together |
| **Security places** (7, loot plan) | the gun cabinet's cage | 7 | 55 | S each |
| **Kahuna Palms**, manager's office in the lobby | the service stairs as a shortcut to the third floor (an optional way past the second) | 1 | 55 | M |
| **The Kāhala Hotel** armoury (pirates) | the armoury's locked gun cabinets [loot plan: armoury, safe on a key] | 1 | 70 | S |
| **Alewa Fort** | the Kalihi lord's own room | 1 | 85 | M |
| **The Missouri**, Turret Two's magazine and the Pilot House safe [loot plan] | the magazine door; the safe's lock (the key stays in the berthing lockers too) | 2 | 85 | M |
| **Behind the wall / the north**, keyed safes in ruins (loot plan) | a terminal-wired wall safe instead of a key on some | ~8 | 85–95 | S each |
| **The Vault** (holding rooms, armoury, cold store, reclamation plant) | each its own terminal; the council chamber stays on the Council Key | 4–5 | 95–100 | M |

About 50–60 terminals all told, harder away from Hanauma, the hardest in the Vault and on the Missouri. Nothing locked near
the start (the loot plan's `SAFE`).

### G. Terminals that hold entries: lore and secrets

Each entry stays inside what's decided; anything that adds story is marked.

| Where | What the entries say | Secret it points to | Science | Work |
|---|---|---|---|---|
| **The radar dome on Waiʻalae Nui** [decided stop: radar dome, crashed Vertibird with Vault-Tec delivery papers] | the dome's last watch logs; the delivery manifest for "Vault 50, Kaʻau" | **[decided 25 Nov]** a supply cache the Vertibird never delivered, in the dome's store | 55 | M |
| **The Missouri's Pilot House / fire control** ["The Captain's bluff": the big guns can't fire, decided] | maintenance logs: the main battery's state, readings nobody aboard can follow | *the bluff itself*: reading it is how you find out (a quest flag for the storyline) | 85 | M, the storyline's key |
| **The Royal Hawaiian's tribute office** ["The squeeze": the quota rises, decided] | the old hotel's booking system turned tribute ledger: what each valley owes, quota by year | which valley is behind (sets up "A valley stops paying"); who is marked as "sent on" | 55 | M |
| **Alewa Fort** [decided: the Kalihi lord keeps Ground Zero's secrets; may know the guns can't fire] | his scouts' reports past the wall | **[decided 25 Nov]** a salvage cache on the wall's near side his scouts left; a hint he knows about the guns | 85 | M |
| **The Heights' mansions** [decided: paid for the Vault, shut out] | pre-war Vault-Tec reservation letters, "your family's place is assured" | **[decided 25 Nov]** an old service route marked on a mansion's plan: the Vault's back door off the settlers' cliff trail [the back door is decided] | 55 | M |
| **Kahuna Palms** | pre-war hotel notices; the last days of the tower before it closed | the penthouse safe's code (the safe **[decided 25 Nov]**) | 40 | S |
| **The Vault**, from the schoolroom to the council chamber [decided: eaten people, the council, kitchens and cold store, servants] | the schoolroom's lessons (what children are told before they come of age); the clinic's notes; the cold store's stock list; the council minutes | the truth of the trade, read plainly; which ending each discovery leads to stays the user's | 85–100 | L, with the Vault |
| **Pele's Pipe** | — | **none** [decided: no notes, the camp speaks for itself] | — | — |
| **Nuʻuanu visitor centre** (only if the user keeps the Nuʻuanu draft) | the tour's control logs | shut down or retune the projectors [draft's ending] | 70 | L, with that place |

### H. Science beyond terminals (M each)

- **Generators [night-lights idea 1].** A settlement's broken generator: Science 55 to find the fault (the idea had Repair;
  Science reads the wiring, Repair fixes parts: either opens it). Lit, the camp gets its strings of lights, and a trader
  there sells more. Fits decided power: ridges have scraps of wind and solar.
- **Vault power cells [decided: the Vault recharges cells; everyone needing light depends on it].** Science 85 at a
  pirate or court charging bench: you can tell a Vault cell is charged, refuse a dead one in trade, or recharge one
  yourself at the Missouri's solar (a small recipe).
- **The Missouri's searchlight and radio [decided: searchlight, radio, the one working gun].** Science 70 in the Engine
  Room: what she still runs on and what she doesn't; feeds the bluff.
- **The Huáng's gate guns ("Oil for the Gate Guns").** Science 55 as a second way: you tune their sights and Liu Wei needs
  only one kit.
- **The Vault's reactor and back door (L, with the Vault).** Science 95 at the back door's panel opens it from outside (the
  way in that isn't the gear door), Science 100 in the reactor room is one lever toward "Take the Vault's place".

### I. Robots and machines (the user, 25 Nov: "we need to add robots and mechs too, other kinds of tech that science hacking hinges on"; "Robots should be seen on Waikiki as well, maybe as part of the hotel staff and security")

**What the game already gives us** (read from FalloutNV.esm and the DLCs, 25 Nov):
- **Robots, as creatures we can copy:**
  - Mister Handy, Mister Gutsy and Old World Blues' Mister Orderly (one body, three looks);
  - Protectron;
  - eyebots (also Lonesome Road's medical and repair eyebots);
  - Robobrain;
  - Sentry Bot (also Lonesome Road's Army ones);
  - Old World Blues' robo-scorpions;
  - Securitrons, which are Mr. House's Vegas machines: keep them off the island.
- **Turrets:** ceiling turrets (MiniSentryTurret), floor turrets (SentryTurret), Lonesome Road's Mark VI, and Dead Money's
  sentry turret.
- **How the game's own terminals act on them:**
  - shut one down: `SetUnconscious 1`, or `DamageAV BrainCondition 100`;
  - turn it round: `AddToFaction PlayerFaction` or `SetAlly`;
  - calm it: `StopCombat`.

  These are all the game's own commands, so they work in nv-rs without an extender. FOLab's terminal maker writes them
  as a menu item's `Script:`.
- **What needs new models:** only the big war machines (no mech in the game), and the hotel staff's livery if we restyle
  them (a Mister Handy repainted in the court's colours, later). Everything else reuses the game's.

**Science by tier, for machines** (the same six steps as above):

| Tier | Science | What it does to a machine |
|---|---|---|
| 1 | 25 | read a robot's work log on an open terminal; switch off a turret whose terminal isn't locked |
| 2 | 40 | shut down a crazed hotel bot from its floor's terminal; turn off a camp's salvaged turret |
| 3 | 55 | shut down a building's security robots (the bank, built in the step below); turn its turrets off |
| 4 | 70 | turn a building's security to your side: its robots and turrets fight for you there (`AddToFaction PlayerFaction`) |
| 5 | 85 | military machines: wake or stop Sentry Bots and Robobrains; the Missouri's systems; Alewa Fort's salvage |
| 6 | 95+ | the war machines and the great systems (below): rare, each a turn in the story |

**Robots and turrets, by place.** "Built" means it's in the build step below; everything else is a proposal.

| Who or what | Where (decided place) | Side | Science | Speech | Status |
|---|---|---|---|---|---|
| Butler, bellhop, housekeeping and waiter Mister Handys | the Royal Hawaiian's six court floors and the Moana's four [the court holds the hotels] | the court, friendly | 55: a floor terminal turns them off or calls them to you (proposal) | 40: a butler tells you which floors the court keeps closed (proposal) | built: 13 robots |
| Protectron doormen | outside the Royal Hawaiian (2) and the Moana (1); the toll post (1); the court's stores and the Kahuna's floor inside (2) | the court, friendly, unaggressive | 70: their terminal opens the stores' door (proposal) | none: robots don't bargain | built: 6 |
| Court eyebots | over Kalākaua between the Royal Hawaiian and the Moana | the court | 40: send one home | — | built: 2 |
| Security Protectrons | the American Savings Bank, a pre-war bank in Waikiki | hostile (the game's robots) | 55: the bank's security terminal shuts them down (average lock) | — | built: 2 and the terminal |
| Crazed Mister Handys ("Malfunctioning Bellhop") | three ruined hotels: Ala Moana Hotel, Hilton Garden Inn, the Ritz-Carlton | hostile | 40: a floor terminal shuts it down (proposal) | — | built: 3, only where nobody else stands |
| Ceiling turrets | the bank's vault room; the Kāhala Hotel's armoury (pirates on Vault power cells) | the building's owner | 55 off, 70 turned round | — | proposal |
| Army Sentry Bots, lying dead | Alewa Fort's salvage yard [decided: salvage from Pearl Harbor and Ground Zero goes to the ship through the fort] | the fort | 85: one woken stands with the fort's men, or with you | 70 with the Kalihi lord: he lets you try | proposal |
| The Missouri's systems [decided: searchlight, radio, the one working gun, the big guns that can't fire] | fire control, the Pilot House, the Engine Room | the Captain | 85: read the gun logs (the bluff); 95+ below | — | proposal |
| Vault-Tec security in Vault 50 [decided: lit, defended, reactor] | the holding rooms, the armoury, the reactor | the Vault | 85–100: turrets and Protectrons off, or turned on the council | — | proposal, with the Vault |
| A pre-war Army walker, a mech | lying broken across the ruined H-1 at the Pālolo junction, under the pirates' post | wreck | 95+ below | — | proposal, **needs a new model** |

**Very hard Science (95+), for machines** [all proposals; at most two or three, like the Speech ones]:
1. **The Missouri's main battery.** You make one of her big guns fire again. The Captain's bluff becomes true,
   and you decide whose the gun is: his, the Kahuna's, or no one's (you wreck it).
2. **Vault 50's security turned on its council** (with the Vault's endings). Its turrets and Protectrons fight for
   whoever holds the reactor room.
3. **The walker on the H-1** (new model). Woken, it clears the pirates' post over the Pālolo junction, the slave road's
   foot. One shot, not a pet.

**Not on the island:** Securitrons (Mr. House's, the Strip's); robots in Huáng land (they build from what grows back,
the bamboo and thatch work, and power stays their own). Liberty Prime or any named Fallout machine.

**The build step for the robots** (`app/robots.py`; hand-over in the shared notes, `robots-into-waikiki.md`): 26
robots of 8 kinds and the bank's security terminal, one Undo.
- Each robot is a copy of the game's: its script dropped, its side and package set.
- Each one stands on a navmesh, clear of doors and arrivals (300), of anyone standing (220) and of seats and idle
  markers (100).
- Outside, none stands inside a building (indoors).
- Hostile ones go only where nobody else stands.

### J. Speech and Science as systems (the user, 25 Nov 2026: "I like all those ideas ... how would you incorporate them as systems?")

**The rule for talk** (the user: "speech shouldn't be the 'best payoff' necessarily, it can unlock rare interactions
and rewards, it can be easier, but I don't want to emphasize that pacifism is superior"):
- **Talk is easier and opens rare things, but it isn't the best pay.**
- **A fight keeps its own reward:** the gang's loot is all yours, worn (its levelled condition).
- **Talk is a fair choice when you're short of ammo or stimpaks, at a cost to your name.** There is no "talking pays
  best" rule.

#### Foundations

**F1. One check template.** Every check across the mod is built the same way:
- **The lines:** a pass and a fail line (KNAM, GetActorValue >= / < N on the player), wired by result scripts.
- **Retry:** ordinary, or one-time (a quest variable).
- **XP:** by tier.
- **Its kind**, and each kind's cost on the side's hidden score (F2):

| Kind | How it's checked | What it costs or earns |
|---|---|---|
| Persuade or bluff | Speech | keeps your standing (no change) |
| Intimidate | Speech, lower with a big gun out or high Strength (IsWeaponOut, GetActorValue Strength) | earns respect (+score) |
| Pay | goods (a Stimpak, ammo) | costs the goods, and with pirates a little respect (-score) |
| Plead or back down | easy (Speech a tier lower) | marks you (-score, more) |

**F2. Reputation, two kinds per side (replaces the earlier F2; built: `repstanding.py`).**
- **Axis one, liked or hated:** New Vegas's fame and infamy on the three REPU (Court, Pirates, Huang), on the Pip-Boy's
  reputation page.
  - Its titles are the island's: the 16 `sRepTitle...` settings renamed, listed below.
  - nv-rs reads those settings as the exe does (tesreputation.rs).
- **Axis two, how each side sees you:** a hidden score per side, -100 to 100, shown as one line per side in the quest
  "Your Name on the Water".
  - **Pirates:** feared or soft touch.
  - **The court:** favour or suspicion.
  - **The Huang:** face or disgrace.
  - What moves each: winning fights against pirates (GetDeadCount) and intimidating raise the pirates' score; paying and
    pleading lower it. The Kahuna's guest raises the court's. Huang quests and the hold raise face; begging lowers it.
- **The corners** (come with system 1):
  - **Pirates:**
    - respected: tolls waived, captains deal;
    - a friendly mark: favours and "loans" asked of you;
    - nemesis: hunted in bigger groups, small crews scatter;
    - prey: frequent ambushes, sneering lines.
  - **Lighter for the court and the Huang:** prices, guard lines, access.

**F3. Rewards by path (replaces "talking pays best").**
- **Fight:** all the gang's gear, worn.
- **Talk:** an easier way through, and now and then something only talk opens (a secret, a key, a deal).
- **Pay:** you keep your ammo and lose goods.
- No path pays best every time.

#### The systems (each a step of its own, in this order; nv-rs checked by its source, 25 Nov)

| # | System | How | nv-rs |
|---|---|---|---|
| 1 | **Parley on the road** | Pirates, catchers and press gangs start non-hostile at worldlife's scene spots. A trigger has their leader StartConversation ("Hold there!"). The F1 kinds: wave-through, a smaller toll in goods, information. A fail or refusal makes them hostile by result script. They come back as scenes do; the corners of axis two change how many and how they talk | StartConversation proven (the opening); StartCombat and SetEnemy in its source; trigger boxes (OnTriggerEnter) in its source |
| 2 | **Yield and recruit** | Leaders' scripts stop the fight at low health (GetHealthPercentage, StopCombat). A check makes one a follower (SetPlayerTeammate and a follow package) or the crew friendly | StopCombat, SetPlayerTeammate, GetHealthPercentage in its source; **AddScriptPackage and SetAlly not found by name** (as GetHasNote, which failed): a follow package on the record instead, a faction swap instead of SetAlly |
| 3 | **Rumours** | "Heard anything?" on locals, Speech-tiered; a pool of rumours, each told once; ShowMap of a real marker | ShowMap in its source |
| 4 | **Brokering** | Repeatable go-between contracts: the court, the Huang, the dealing pirates. Delivery adds fame with both sides and fills a stash every few days (GameDaysPassed) | standard commands |
| 6 | **Power cells** | A repaired generator's menu turns the game's Drained Microfusion and Drained Small Energy Cells into charged ones, more at higher Science. A way not to hang on the Vault (decided: the Vault recharges cells and pays the pirates in them) | message buttons (GetButtonPressed) in its source |
| 9 | **Lights back on** | A settlement's broken generator (nightlights' idea 1): a Science check and parts switch on its lights (an enable marker), a trader placed off, a safe bed. Shares the generator with 6 | enable parents proven (night lights) |
| 7 | **Rebreather** | A workbench recipe at Science 70 for a mask with Water Breathing (the game's AVWaterBreathing and WaterBreathing effect); seafinds' deep wrecks hold the best loot | recipe menu ported; **the water breathing effect not seen in nv-rs** |
| 8 | **Storm forecasting** | Barometer terminals (terminals.py) read stormsched's due time and ShowMessage the hours left at Science 40+; after a big storm, stormafter's wrack beaches are marked | terminals and ShowMessage proven |
| 10 | **Robots in a fight** | Shut down or turn the mod's hostile robots (SetUnconscious; a faction swap), the bank's first. Activating a hostile actor doesn't run its OnActivate in the game, so it goes through a nearby terminal or a sneaking "maintenance panel" activator beside the robot | **SetUnconscious not found by name**: the bank terminal shows it first |
| 13 | **Perks of our own** | "Kahuna's Ear" (HasPerk conditions show what a check would give), "Salvager" (robots drop parts), two or three more | perk entry points ported |
| 11 | **The Huang's radio** | An encrypted chatter station (radio.py); a radio terminal decodes it at Science 70: a note of patrol times and the freighter hold's watch | radio ported; decoding is a terminal |
| 14 | **Island skill books** | A few BOOK records that teach Speech or Science, hidden behind the checks they help with | book menu ported |

Anything "not found by name" is shown to the user in game first, as FOLab Skill Proof did. A failure is named before the
step goes further.

#### Voices (the user, 25 Nov 2026: "there should be a good variety of generic voices in english and in chinese, and then all unique/important npcs should get their own unique voices")

- **Every named or quest person has a voice no one else has.**
- **Generic people draw from pools:** at least 8 English men, 8 English women, 6 Mandarin men and 4 Mandarin women,
  spread so people together don't sound alike.
- **Every new line is voiced in its own step** (`voicelines.py`). The step's check fails on any line without .ogg/.lip.
- **A changed voice means all that person's lines are spoken again** (`voicevariety.py`).
- **Mandarin voices are Kokoro's eight Chinese voices,** blended, with a constant pitch shift (the tones kept) and a pace
  of their own.
- **The rule is kept in voices.json as `rules`.**

#### Island titles (built: `repstanding.TITLES`; the game's title in brackets)

| Fame \ Infamy | none | some | much | most |
|---|---|---|---|---|
| none | Malihini (Neutral) | Watched (Shunned) | Bad News (Hated) | Island Nightmare (Vilified) |
| some | Welcome Guest (Accepted) | Mixed Plate (Mixed) | Beach Punk (Sneering Punk) | Kind Shark (Merciful Thug) |
| much | Good Friend (Liked) | Kolohe (Smiling Troublemaker) | Wild Card (Unpredictable) | Devil with Aloha (Soft-Hearted Devil) |
| most | Island Legend (Idolized) | Lovable Rascal (Good-Natured Rascal) | Rogue Wave (Dark Hero) | Big Wave (Wild Child) |

**"Your Name on the Water", the five lines per side** (low to high):
- **Pirates:** prey; an easy mark; don't know what to make of you; give you room; fear your name.
- **The court:** watches you closely; wary of you; hardly knows you; looks on you kindly; trusts you near the Kahuna.
- **The Huang:** say you have no face; think little of you; have no opinion of you; say you keep your word; give you face.


### K. More for the other skills: the guns, non-combat uses, perks (for later; the user, 25 Nov 2026)

The user: "There should be a way to fix the guns of the ship with high repair. And other uses for other skills. Maybe uses
for high barter and repair and others that aren't combat oriented. More perks to survival. And skill perks in general.
Perks you get for hitting skill milestones." Written down for later, **not built**. Everything below is a proposal; ★
marks my picks.

#### K1. The Missouri's guns, fixed (a proposal touching decided lore)

The story plan's "Captain's bluff" is agreed: the 16-inch guns are dead, one 5-inch mount works, and whoever finds out
changes the balance. Fixing them turns that over, so the user decides whether it can happen at all.

**The way** (one quest, its stages by skill):
1. **Repair 50** in Turret Two: you see the guns can't fire (the bluff found out, as now).
2. **Repair 75:** what it would take: a breech block, recoil cylinder seals, and dry powder bags (the forward magazines
   are flooded). Science 70 at the fire control terminal works out that one turret could fire.
3. **The parts,** each a trip:
   - a breech block from a wreck at Pearl Harbor, through the Kalihi lord's scouts past the wall;
   - seals made at a workbench (Repair 60);
   - dry charges from the Vault's stores, or bought from the Flotilla, which would rather not see the guns work.
4. **Repair 95:** Turret Two fires. ★ **Three salvos only**: there are only three dry charges, so it stays a card to play,
   not a new power.

**What it changes:**
- **The Captain:** his power is real again. He can thank you, make you his gunner, or decide he no longer needs the
  Kahuna. That's the user's to decide.
- **The court:** the Kahuna's threat stops being a bluff, or becomes the Captain's alone, depending on whom you tell first.
- **The pirates:** the Flotilla finds out once the guns are being fixed. ★ They try to sink or board her before the
  last part comes: a raid on the ship, a story moment of its own.
- **The Kalihi lord:** his leverage (knowing the guns can't fire) is gone. He may slow the parts down, or bargain for
  telling no one.
- **The Vault:** Kaʻau Crater is in the guns' range. The Vault's bargaining (power for people) changes, and an ending
  could turn on a shell aimed at the crater. That's the user's to decide.

**Story moments it opens:**
- one salvo at the Flotilla's anchorage;
- a shot over the Kāhala as a warning;
- the guns turned on the court;
- the secret sold (Barter);
- the guns left as they are, the secret kept.

★ Build it, if at all, as an ending-sized choice on the Waikiki path.

#### K2. Non-combat uses for every skill

Tiers as for Speech: 25 / 40 / 55 / 70 / 85 / 95.

**Barter** ★ (the first of these to build):
- ★ **Haggled pay:** at a quest's reward, "[Barter 40/70] I was promised more." gets +25% or +50% kala. A fail keeps the
  pay but costs a little face.
- ★ **Trade contracts:** a standing order with Linda Moreno, Kailua's Shangren or the Kāhala trader: deliver goods every
  few days for a cut. Barter sets the cut (brokering's shape, with money).
- **Exchange rates:** already in at the Makapuʻu changer (Barter 50: 9 kala a coin). More could come at the pirate traders
  (cells at 5) and a court treasurer (tongbao to kala).
- **Smuggling routes** (Barter 70): carry tongbao or cells between sides that don't trade, for the margin. Caught by a
  patrol: infamy and the goods taken.
- **Passage and information:** cheaper boat trips (boatferry's prices once they're in money), and a rumour's price.

**Repair** ★:
- ★ **Fixing things for people,** a short job each:
  - the Shouwei's gate guns (Huáng face);
  - a Waikiki pier winch (a fisher's family eats);
  - the Tanks' water pump (the valley stops paying, from the other side).
- ★ **The Kilauea's arcade machines** (Repair 55; 85 to rig one): a repaired token machine pays out kala now and then, and
  a rigged one pays better until the court notices.
- **Boats** (Repair 70): mend a wrecked boat at a stop and it joins the ferry. At 85, your own boat at the Waikiki pier.
- **Weapons for people** (Repair 40): mend a guard's or a pirate's gun for pay, or for a favour in a talk later.
- **The Missouri:** the searchlight (40) and the 5-inch mount (75) on the way to K1.

**Lockpick:**
- the court's strongrooms in the Royal Hawaiian (70);
- the tribute cages, to free people (55: already a way through in heldwatch's);
- Huáng storehouses (40);
- the Vault's back door (85);
- safes by tier.

**Medicine:**
- ★ a fever in a valley (55): cure it, or sell the cure;
- the Bishop Museum's ghoul curator (70);
- the Flotilla's surgeon's trade in stimpaks;
- patching the condemned on tribute night (40, a mercy).

**Survival:**
- ★ guide work on the Koʻolau trails (55: lead a family or a runaway over the ridge);
- foraging and cooking recipes at campfires (25 / 55);
- tracking (heldwatch's runaways, the other way round);
- finding the cliff trail's hidden turnings (70).

**Explosives:**
- ★ clearing blocked ways (55: rubble in a tunnel, a fallen freeway span), which opens a short cut or a cache;
- the Missouri's flooded magazines (85, dangerous);
- the Flotilla's boats (70, sabotage).

Already in: **Science** (section J) and **Speech** (everywhere). Sneak, Unarmed and the gun skills stay mostly combat.

#### K3. More Survival perks (beside Storm-Wise and Reef Diver)

| Perk | Needs | What it does | How |
|---|---|---|---|
| ★ **Reef Fisher** | Survival 40 | twice the fish from FOLab's fishing spots | the spots' scripts ask HasPerk |
| ★ **Wild Medicine** | Survival 55 | healing poultices at a campfire from island plants (taro leaf, ti, noni) | a recipe gated by HasPerk |
| ★ **Wrack Reader** | Survival 50 | after a storm, the best of the wrack (stormafter's finds) shows on the map | the wrack's finds get map markers with the perk |
| **Koʻolau Legs** | Survival 70 | +10% speed outdoors in the island's world | an ability with a GetInWorldspace condition (as Island Time) |
| **Shark Sense** | Survival 60 | a message when a sharklurk is near in the water | a quest's GetDistance, with the perk |
| **Castaway** | Survival 85 | food and water you find in the wild heal more | an entry point (below) |

#### K4. Skill-milestone perks

**How it would work:**
- The game doesn't give perks for reaching a skill. Its level-up menu only lists perks whose conditions pass, and each
  costs a pick.
- So a milestone perk is free and given by script, which works without an extender: a quest checks each skill
  (GetPermanentActorValue) every few seconds. When one passes 50, 75 or 100 for the first time, it runs AddPerk and shows
  a message with the perk's name and words. Its own variables keep each milestone to once.
- ★ At 100, a choice instead: a message with two buttons picks one of two perks (GetButtonPressed), as generators' menu
  does.

**What nv-rs allows** (read from its source, 25 Nov 2026, commit cad5b671):
- It ports the game's perk code: `BGSEntryPoint::HandleEntryPoint` (`bgsentrypoint.rs`), called at the game's own sites
  (barter prices, terminals, action points, VATS, damage, health and AP regeneration), and ability and quest perk
  entries (`bgsperk.rs`).
- It also ports the player's perk list (`playercharacter_p3.rs`) and the level-up menu (`levelupmenu.rs`).
- So entry-point perks (prices, Repair's effect on condition, chems' duration) should run there as they do in the game,
  but none of FOLab's has been tried yet. perks.py's five avoided entry points for that reason. A first build should
  prove one (Barter's price) in nv-rs before relying on them.

**One island perk a skill a milestone** (names and effects are proposals; ★ the non-combat ones to build first):

| Skill | 50 | 75 | 100 |
|---|---|---|---|
| ★ Barter | Market Day (better prices at stalls and island traders: entry point) | Contract Hand (trade contracts' cut +25%) | Tongbao Baron (the changer's rate at its best both ways, and a trader's barter gold doubled) |
| ★ Repair | Salt and Rust (weapons and armour wear slower in the island's sea air) | Shipwright (boats mended with fewer parts; the ferry costs nothing) | Gunner's Mate (K1's last stage needs one part less) |
| ★ Medicine | Noni Cure (healing powder heals more) | Island Doctor (fever and poison cured by talking to the sick) | Kahuna Lāʻau (a once-a-day full heal at any campfire) |
| ★ Survival | Trailwise (no fall damage on the Koʻolau trails) | Sea Legs (swim faster) | Child of the Island (hunger and thirst slower in the island's world) |
| ★ Science | Tinkerer (one part fewer at generators and panels) | Signal Man (radio numbers decoded without the dome) | Vault-Tec Mind (the Vault's terminals open a tier easier) |
| ★ Speech | Talk Story (one more answer in rumours) | Word on the Water (fame with every side counts half again) | Silver Tongue (one 95 check a game passes at 85) |
| Lockpick | Quiet Hands (no noise picking) | Cage Breaker (tribute cages open without a check) | Master Key (one lock a day opens) |
| Explosives | Fisherman's Charge (blast fish from the water) | Sapper (clearing blocked ways is safe) | Big Bang (the Missouri's salvos hit harder) |
| Sneak | Night Walker (the Huáng's watch sees less at night) | Shadow Trader (smuggling never caught at 75) | Ghost of Waikiki (court guards don't hail you) |
| Guns, Energy, Melee, Unarmed | one each at 50, 75, 100 | (combat: a damage or speed edge with the island's own weapons) | |

★ The order to build: the milestone quest itself (one script, the 13 skills), then Barter, Repair, Medicine, Survival,
then the rest. About 40 perks in all if every skill gets three: that's a lot, so the user may prefer 50 and 100 only (26).

**For the user to choose, when ready:**
1. May the Missouri's guns be fixed at all? If so, how many salvos, and who learns first?
2. Which K2 uses to build first (my picks: haggled pay, trade contracts, fixing things for people, the arcade machines).
3. Which Survival perks (my picks: Reef Fisher, Wild Medicine, Wrack Reader).
4. Milestone perks: free at 50/75/100, a choice at 100, or only at 50 and 100? Every skill, or the non-combat ones first?

#### K5. The complete system (the user, 25 Nov 2026: "let's design a complete system and then build it. no more what if")

All of K2-K4 is built against this. K1, the guns, is the quests session's and plugs in where marked.

**1. Tiers.**
- The same six as Speech: 25, 40, 55, 70, 85, 95.
- Every check is made one of two ways:
  - with people: `skillcheck.check_lines` (the game's "[Repair 55]" tag, a pass line and a fail line);
  - at things (a machine, a boat, a rubble pile): its activator's script, which reads GetActorValue and shows a message.
- **Retries:** a fail never locks the check, so it can be tried again with more skill. The exception is haggling, which
  is one try per reward.
- **Real locks:** the game's lock levels, by tier: 25 Very Easy, 40 Easy, 55 Average, 70 Hard, 85 and 95 Very Hard.

**2. What a use costs.**
- **Repair:** parts by tier.
  - 25-40: Scrap Metal.
  - 55-70: Scrap Electronics and Scrap Metal.
  - 85-95: a Sensor Module or Fission Battery, and Scrap Electronics.
- **Medicine:** supplies. A Doctor's Bag or Stimpak; Antivenom for stings; Healing Powder for the Huáng.
- **Explosives:** the charge is spent, from the player's Frag Grenades, Dynamite or C-4.
- **Survival:** game hours. Guiding takes the walk, foraging takes an hour.
- **Barter:** nothing but the risk: a failed haggle costs face, and a caught smuggler loses the goods.

**3. What a use pays, by tier, in kala.**
- 25 pays 10-20, 40 pays 25-40, 55 pays 50-80, 70 pays 100-150, 85 pays 200-300, 95 pays a unique thing.
- The Huáng pay the same worth in tongbao (a tenth of it), the pirates in Energy Cells (a quarter).
- Each side pays in its own money (money.py).

**4. Reputation** (repstanding's two axes).
- **Work for a side:** +1 fame with it and +3 on its Name on the Water score. A tier 5 or 6 job gives +2 fame and +5.
- **Work against a side** (caught smuggling, a rigged arcade machine found out, a lock picked in front of its people): +1
  infamy with it and -5 on its score.
- **Who offers what:**
  - trade contracts and repair jobs come from a side at band 2 or more ("hardly knows you" or better);
  - smuggling routes come from the pirates at band 2 or more;
  - nobody offers you work at band 0.
- **The soft-touch axis** (the pirates' score, bands 0-1: prey, an easy mark):
  - pirate prices are a quarter worse;
  - haggling with pirates is a tier harder;
  - passage on a pirate boat costs double.
- **Feared** (pirates' band 4): pirate contracts pay a quarter more, and the toll is waved off (parley, already).
- **The court's favour** (band 3-4) and **the Huáng's face** (band 3-4): a tier off their own jobs' checks (a 70 is
  asked at 55).

**5. The uses** (K2), each a small job of one shape (sidequests' "ask, do, come back, reward"), or a standing service:

| Skill | Uses | Who / where |
|---|---|---|
| Barter | haggled pay (every reward line of the mod's quests: +25% at 40, +50% at 70); trade contracts (three: Linda Moreno, Shangren, the Kāhala trader: a delivery every 3 days, the cut set by Barter); exchange rates (the changer 50, pirate traders 55: cells at 5, a court treasurer 40); smuggling (tongbao and cells between sides: three runs); passage (ferry fares by Barter) | traders, the changer, the ferry |
| Repair | fixing jobs (the Shouwei's gate guns 55, a Waikiki pier winch 25, the Tanks' water pump 70, a court radio 40, a Flotilla boat engine 85); the Kilauea's arcade machines (55 to fix: pays now and then; 85 to rig: pays well until the court finds out); boats (70: a wreck at a stop joins the ferry; 85: a boat of your own at the Waikiki pier); weapons for people (40: a guard's or a pirate's gun mended for pay or a favour) | settlements, the Kilauea, the stops |
| Lockpick | the court's strongrooms (70, the Royal Hawaiian), the tribute cages (55, heldwatch's), Huáng storehouses (40), the Vault's back door (85), safes by tier; picked in sight of a side's people: infamy | the court, Waimānalo, the Vault |
| Medicine | a fever in a valley (55: cure it, or sell the cure); the Bishop Museum's ghoul curator (70); the Flotilla surgeon's stimpak trade (40); patching the condemned on tribute night (40, a mercy) | the Holdouts, Kalihi, the Flotilla, the Natatorium |
| Survival | guide work on the Koʻolau trails (55: a family or a runaway over the ridge); foraging and cooking recipes (25, 55); tracking (heldwatch's runaways, the other way: find them before the catchers); the cliff trail's hidden turnings (70) | the ridges, campfires |
| Explosives | blocked ways cleared (55: rubble in a tunnel, a fallen freeway span: a short cut or a cache); the Missouri's flooded magazines (85, for K1); sabotage of the Flotilla's boats (70) | the freeway, the Missouri, the anchorage |

**6. The perks and what they boost** (K3 and K4). A milestone perk is given free when a skill first reaches 50 or 75. At
100 you choose one of two. Each boosts one or more of the uses above:

| Skill | 50 | 75 | 100: one of |
|---|---|---|---|
| Barter | Market Day: island traders' prices better (an entry point, or a script) | Contract Hand: contracts' cut +25% | Tongbao Baron (the changer's best rate both ways) / Smuggler's Purse (smuggling never caught) |
| Repair | Salt and Rust: weapons and armour wear slower in the island's world | Shipwright: boats mended with one part fewer; ferry free | Gunner's Mate (K1's last stage needs one part fewer) / Tinker's Pay (every repair job pays double) |
| Medicine | Noni Cure: healing powder heals more | Island Doctor: fevers cured by talking to the sick | Kahuna Lāʻau (once a day, a full heal at any campfire) / Field Surgeon (stimpaks heal a quarter more) |
| Survival | Trailwise: no fall damage on the Koʻolau trails | Sea Legs: swim faster | Child of the Island (hunger and thirst slower on the island) / Castaway (wild food and water heal more) |
| Science | Tinkerer: one part fewer at generators, panels and fixing jobs | Signal Man: radio numbers decoded without the dome | Vault-Tec Mind (the Vault's terminals a tier easier) / Salvage King (robots always leave a Sensor Module) |
| Speech | Talk Story: one more rumour | Word on the Water: every side's score moves half again | Silver Tongue (one 95 check a game at 85) / Kahuna's Voice (the court's checks a tier easier) |
| Lockpick | Quiet Hands: picking in sight costs no infamy | Cage Breaker: the tribute cages open without a check | Master Key (one Very Hard lock a day opens) / Strongroom Ghost (the court's strongrooms' alarms don't sound) |
| Explosives | Fisherman's Charge: a charge in the water brings up fish | Sapper: clearing a blocked way is safe | Big Bang (K1's salvos hit harder) / Demolition Pay (blasting jobs pay double) |
| Sneak | Night Walker: the Huáng's watch sees less at night | Shadow Trader: smuggling runs are never stopped | Ghost of Waikiki (court guards never hail you) / Tide Walker (sneaking in water is silent) |
| Guns | Pirate's Eye: +10% damage with the island's rifles (the Chinese and Japanese guns) | Steady Deck: less sway on boats and decks | Sharpshooter of the Reef / Gunsmith's Friend (the island guns wear half as fast) |
| Energy Weapons | Cell Saver: one cell in ten not spent | Vault Charge: drained cells charge one for one at any generator | Overcharge / Cell Merchant (cells trade at 5) |
| Melee Weapons | Koa Hand: +10% damage with the island's clubs and blades | Lua Stance: power attacks cost less AP | Kahuna's Champion / Leiomano Master |
| Unarmed | Lua Fist: +10% unarmed damage | Riptide: a knockdown in the water | Big Kahuna / Bone Breaker |
| Survival (K3, chosen, not milestones) | Reef Fisher (40), Wild Medicine (55), Wrack Reader (50), Koʻolau Legs (70), Shark Sense (60), Castaway (85: also a milestone choice above) | | |

**7. How it's put together.**
- **One quest, FOLabMilestones**, watches the thirteen skills. It gives each perk once, shows a message for it, and
  offers the choice at 100 as a message with two buttons.
- **The perks are PERK records of the mod's own.** Not playable: they're given, so they aren't in the level-up list.
  Each takes one of three shapes:
  - an ability (an actor-value change with conditions, such as GetInWorldspace for the island-only ones);
  - an entry point, once proven in nv-rs (Barter's price first);
  - a HasPerk condition in the use's own lines or script.
- **The jobs:** one quest per family (FOLabWorkBarter, FOLabWorkRepair, FOLabWorkLockpick, FOLabWorkMedicine,
  FOLabWorkSurvival, FOLabWorkExplosives). Each job's ways through and endings are listed in its hand-over (the standing
  rule).
- **Build order:** the milestone quest; K3; K4's perks (the hooks into uses that don't exist yet land with those uses);
  then K2: Barter, Repair, then the rest.
- **Names, pay figures and places are proposals** (this session's), inside what's decided.

---

## By place (where both skills meet)

| Place | Speech | Science |
|---|---|---|
| Hanauma, Kuliʻouʻou | beachcomber's share; Leilani's tribute talk | — (nothing locked near the start) |
| The coast road | press gangs; catchers | — |
| Kāhala Hotel | trade ground; the land gate | the armoury |
| Waikiki and the Royal Hawaiian | the doctor; guards; collectors | the tribute ledger; offices, clinics |
| Kahuna Palms | the watchman's storeroom | the manager's office, hotel notices |
| The Missouri | (with the Captain, when step 5 is made) | fire control (the bluff), magazine, Pilot House safe, engine room |
| The freeway posts | the toll; the pirates' post | — |
| Ridges: Alewa Fort, the Heights, the Watcher, the Holdouts, Loa Gate, radar dome | the Holdouts, the watcher, Loa, the Heights | Alewa Fort's reports, the Heights' letters, the radar dome |
| Waimānalo and the freighter | the gate, the hold, standing | the gate guns |
| The Vault | (later, with the companion and the endings) | every door inside, the back door, the reactor |

## Picks to build first (my order)

0. **The proof (S, first; started 25 Nov at the user's word).** In a test plugin on nv-rs: one Speech check (pass and fail lines on Speech ≥ 25), and one
   terminal whose hacked menu shows a note that a quest script turns into an unlocked door. Settles whether nv-rs shows
   the check and the hacking screen, and how the outcome reaches the script. Everything else waits on this.
1. **A terminal maker in FOLab (M; started 25 Nov at the user's word).** Plain text in, TERM out: pages, a password note, "release lock" tied to a door or
   safe through the script; used by every Science idea.
   **Status, 25 Nov 2026:** both made. The proof was `D:\FOLab-skillproof\out\FOLab Skill Proof.esp`,
   with the user's steps in the shared notes (`skill-proof-try-it.md`); it was run in nv-rs and then taken out. The maker
   is `app/terminals.py` with `tests/test_terminals.py` (32 pass). The user ran the proof the same day: Speech checks,
   hacking, result scripts and notes all work in nv-rs; release by note didn't. So the maker releases locks by the item's
   result script only.
2. **Speech in the seven existing quests (S each, about a day together)** (table A). Cheap, on people already in game,
   and the first thing a talker meets.
3. **Office, clinic and security terminals in the court district (M).** ~35 terminals at Science 25–55 in rooms already
   built: the "many more doors behind terminals" the user asked for, where players go first.
4. **The Kāhala trade ground and the toll post (M).** The recurring pirate and court Speech, on places already built.
5. **The Missouri's fire control terminal (M).** The decided "Captain's bluff" found by Science 85: lore and a storyline
   key at once.
6. **The radar dome's logs and its cache (M).** A decided stop, a Vault-Tec secret, a reward for going there.
7. **Huáng standing you can talk back (M).** The decided "unwelcome, then hostile" with a Speech way back, and the
   freighter's hold by Speech.
8. **The tribute ledger (M).** "The squeeze" readable by Science, and the hook for "A valley stops paying".

## The user's answers (25 Nov 2026)

The user: "some pirates can deal, rep shown in pipboy, retry allowed for some checks."

- **Pirates who deal [decided]:** the Kāhala trade ground and Koko Marina are neutral to you, and you can talk and trade
  there. Pirates everywhere else stay hostile. As the concept map has it, pirates are on the coast and in Kāhala and
  Hawaiʻi Kai, never in the city.
- **Reputation in the Pip-Boy [decided]:** one each for the Kahuna's Court, the pirates and the Huáng, New Vegas's way
  (REPU records, fame and infamy, the Stats page). nv-rs ports the REPU form and the Pip-Boy's reputation list. The
  script commands (AddReputation and the rest) still have to be seen working in game.
- **Retry [decided]:** an ordinary check can be tried again once your skill rises (the pass and fail lines stay offered).
  These can't be retried; a quest variable shuts the choice once it's answered:
  - every 95+ check;
  - any check that decides a fight or a quest's branch (the Holdouts' tribute, the Flotilla's gangplank, the freighter's
    hold, collectors taking a family's child).
  Section A's quest checks are all ordinary except the Makapuʻu guard's (which way the Huáng treat you on their road) and
  Leilani's (once told, it's told).
- **Difficulty [decided]:** the six tiers, with 95+ rare.
- **Money:** still open. Bribes and better prices are paid in goods until the user says.
- **Secrets [decided, the user 25 Nov: "keep all four secrets"]:**
  - the radar dome's undelivered Vertibird cache (pick 6);
  - the Alewa salvage cache, with his scouts' hint about the guns;
  - the Heights' mansion plan showing the service route to the Vault's back door;
  - the Kahuna Palms penthouse safe, its code in the manager's office terminal.
  Each is a step of its own.

**Build order** (the Workshop, 25 Nov): picks 2, 3, 4, 5, 7, 8, all wired by result scripts as the proof showed; each
installed as soon as it passes.

## Built (25 Nov 2026)

Each pick is made, tested and rehearsed on a copy of the live mod (all six in one after another). They're handed to the
story session to install in this order; none is seen in game yet.

| Pick | Module | What | Install step |
|---|---|---|---|
| 2 | `speechchecks.py` | seven Speech checks with the quests' people (25 to 55; Leilani and the gate one-time) | `speech_into_waikiki.py` |
| 3 | `officeterminals.py` | 21 court-district terminals opening locked safes, gun cabinets, medicine lockers (Science 25 / 50) | `skillsteps ... terminals` |
| 4 | `piratedeal.py` | three reputations; pirates at the Kāhala and Koko Marina neutral; two pirate traders (Speech 40 deal); the toll post (Speech 40 or a Stimpak) | `skillsteps ... pirates` (installed) |
| 5 | `missouriterms.py` | Fire Control (Science 75: the Captain's bluff found out) and Ship's Power (50) | `skillsteps ... missouri` |
| 7 | `huangstanding.py` | factions tied to reputations; Huang fame for their quests; Zhao Lei's mend (55); the elder's hold key (85, once; he answers in Mandarin, subtitled) | `skillsteps ... huang` |
| 8 | `tributeledger.py` | the court's tribute ledger (Science 50) | `skillsteps ... ledger` |
| — | `robots.py` | 26 robots and the bank terminal (installed, build 90421a66) | `robots_into_waikiki.py` |
| — | `voicelines.py` | every new line voiced (Chatterbox, each speaker's own voice); a step fails on any unvoiced line | `voice_into_waikiki.py`; inside each step |
| F2 | `repstanding.py` | island titles (16 renamed `sRepTitle` settings) and "Your Name on the Water" (how each side sees you) | `skillsteps ... standing` (before huang) |
| 6 | `secretcaches.py` | the radar dome's Vertibird cargo pod | `skillsteps ... radar` |
| — | `secretcaches.py` | Kahuna Palms' penthouse safe; Alewa's salvage cache and guns hint; the Heights' plan to the Vault's back door | `skillsteps ... kahunapalms`, `alewa`, `heights` |

| J1 | `parley.py` | parley on the road: pirate groups that stop you, five choices | `skillsteps ... parley` |
| J2 | `yieldrecruit.py` | leaders yield at low health; a check recruits one | `skillsteps ... yield` |
| J3 | `rumours.py` | "Heard anything?": eight rumours by Speech tier, each marks its place | `skillsteps ... rumours` |
| J6, J9 | `generators.py` | three settlements' generators (Science 55 and parts): lights, a trader, a bed; drained cells charged | `skillsteps ... generators` |
| J7 | `rebreather.py` | a workbench recipe at Science 70 for the game's Rebreather (water breathing) | `skillsteps ... rebreather` |
| J8 | `barometer.py` | "Read the barometer" on the Radar Dome's and the Missouri's fire control terminals: storm due times at Science 40 | `skillsteps ... barometer` |
| J10 | `robotpanels.py` | a Maintenance Panel by each crazed Mister Handy: Science 50 shut down (loot), 75 reset (XP) | `skillsteps ... panels` |
| J4 | `brokering.py` | three carrying routes (silk, reef, gate): goods both ways, fame with both sides, a share after three runs | `skillsteps ... broker` |
| J14 | `skillbooks.py` | a Speech book in the freighter's hold, a Science book in the Radar Dome's pod | `skillsteps ... books` |

| J13 | `perks.py` | five perks: Kahuna's Ear (check prompts say what a pass gives), Salvager, Storm-Wise, Reef Diver (a minute of water breathing a dive), Island Tongue (the Huang's checks 15 easier) | `skillsteps ... perks` (after huang) |
| J11 | `huangradio.py` | the hold's watchman (meals 12-13, 18-19; caught costs Huang infamy and face), the hatch at Hard, coded numbers on Haixin Dongtai decoded at the Radar Dome (Science 70) | `skillsteps ... numbers` |
| — | `pirateclear.py` | pirates out of Waikiki's lands (the user's decision): 209 removed, parley group 5 moved into pirate land | `skillsteps ... pirateclear` |

All of section J's systems are built.

## Questions still open

1. ~~**Bribes and prices** need money~~ **Settled** (the user, 25 Nov 2026): kala, tongbao and power cells (`money.py`); tolls, bribes and brokering pay in money now.
