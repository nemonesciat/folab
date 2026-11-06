# Characters

*People and creatures in plain fields, what they do, who they side with, and filling a place with them.*

## Characters and creatures

Kinds on the left, everyone of that kind in the middle (yours first), one on the right.

- **＋ New character** starts from one of the game's plain people (townsperson, merchant, guard, outlaw…) or creatures. It leaves out their script and their town's own packages.
- **＋ New one from this** copies anyone the game has. A copy keeps everything, a script included: a quest character's script may expect that quest.
- **Saving a game character** changes them everywhere. A new one of your own is only where you put it: **Place it** takes you to the World page.

The tabs:

- **Who**: name, race, class, voice, level, how they fight. Tick **Follows the player's level** for a level that's a multiple of the player's (the game keeps it as ×1000). **Template** takes parts from another character or a levelled list; tick which parts. With a list, each one placed is picked by the player's level.
- **Stats and skills**: S.P.E.C.I.A.L., health, skills. With **Stats worked out from class and level** on, the game ignores these numbers.
- **Behaviour**: aggression, confidence, helping others, mood; their AI packages, top first; their factions and ranks.
- **Carries**: the same list as the Create page. The box on the right shows what FOLab reckons they'd wear.
- **Looks** (people only): face, hair, eyes, height.

The figure on the right turns, with the race's body and what they wear. It shows the race's plain head, not their face, and it doesn't hold their weapon.

## Faces

Choose one of the game's **presets**, or **copy a face** from anyone. FOLab copies the face numbers as they are, with the hair and eyes. It can't shape a face yet.

The game keeps a painted face file for each of its characters, named after the record's ID. FOLab can't make those files yet, so:

- A **new character** has none, and the face may come out dark or not match the neck in game. A hat or helmet hides it; the GECK's face export can make the file.
- A **game character whose face or race you change** keeps the old painted file, which no longer matches.
- A **face from another race or sex** will look wrong: face numbers mean different things on different heads.

The Looks tab warns of each of these when it applies.

## AI packages

What someone does, where, when and to whom. **＋ New package** starts from one of the game's own:

| Template | What it does | Needs |
|---|---|---|
| Sandbox here | Stays round their spot: sits, eats, sleeps, chats | |
| Wander round here | Walks about near their spot | |
| Patrol | Walks a path of patrol markers | A link to the first marker, which FOLab can't make yet (use the GECK) |
| Sleep at night | To bed from 10 at night for 8 hours | A bed near their spot; put it above the others |
| Guard | Stands at their spot and sees off anyone who comes near | |
| Stand ready | Stays at their spot, weapon out | |
| Follow the player | Stays close behind the player | |

The game runs the first package in the list that applies right now, so one for a set time goes above an all-day one. Someone only walks about in a place with a navmesh (Kit tab on the World page).

Conditions and scripts in the game's packages are kept as they are; see them in Browse.

## Factions

Ranks with their titles, how the faction gets on with others (a liking, and how they act in a fight), the reputation it moves, and who's in it. Add someone to a faction on their Behaviour tab.

## Levelled lists

**Character lists** and **Creature lists** open on the Create page. The game never places a list itself: it places a character whose **Template** is the list.

## Populate a place

Open a place on the World page (or look at a square outside), then **Populate a place** here. **Suggest who** finds the game's places most like this one, by the building pieces they're made of and the words in their name (outside, the squares round it), takes one as the model and proposes its group, as many as the game would have for this much floor. **Try another group** picks again.

Only those the game means to be many: levelled ones, ones it places more than once, or one of several with the same name. Never its one-of-a-kind characters, its dead, or anyone with a script of their own.

- **How hard**: for levelled ones, how far up their list they go.
- **Highest level** leaves out anyone fixed above it.
- **Levelled** makes a list of everyone fixed, and one to stand for it.
- **People live here** makes each person a copy of your own with a Sandbox package here, and sleep at night if there's a bed.

**Place them** is one step: Undo takes it all back, the new records too. They stand on the navmesh, or on a floor worked out from the place's pieces, or outside on the ground. A place with no navmesh needs one before they'll walk about.
