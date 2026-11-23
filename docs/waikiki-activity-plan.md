# Waikiki: people doing things (plan, 21-22 Nov 2026)

The user, 21 Nov 2026 evening: "the world needs a lot more activity now that it is starting to look good".
Built overnight on a copy on D: (`D:\FOLab-activity`); **nothing in Waikiki or any game folder until the user picks in
the morning.**

## Rules kept

- Only the groups the story already has (`docs/waikiki-story-plan.md`): the Kahuna's Waikiki (locals, the court's
  fighters), the Huáng settlers, the pirates, the valley people (Kuliʻouʻou, Niu). No new group without asking.
- Only clothes proven in game: the Hawaiian shirt with trousers (and its khaki and denim ones), board shorts, a
  woman's printed dress, the boater and lauhala (skinned, drawing since 21 Nov), sunglasses, the Huáng and court pieces,
  the pirates' gear, the game's own clothes. **Never the joined shirt-and-shorts.**
- Everyone stands on the navmesh (`factionfolk._on_mesh`), never in water or a doorway. Hostiles keep out of Waikiki
  and away from the start, as `waikikilife` and `worldlife` already do.
- **Counted:** people within the 5 x 5 cells round each busy spot, against the game's busiest places (Freeside's gate
  ~25 people in its loaded cells), and draws (`drawcount`) where markers and props are added. Idle markers draw nothing.

## How the game makes people busy

A person with a sandbox package wanders within its radius and uses what is there: chairs, benches, bedrolls, and the
**idle markers**. An idle marker is an invisible spot that plays a task animation for whoever stands at it. The game
has 220 of them. The ones used here: `DefaultRakingMarker`, `DefaultWateringPlantMarker`, `DefaultYardworkMarker`
(farm work), `DefaultShopkeeperIdleMarker` and `DefaultShoppingIdleMarker` (market), `DefaultRepairFloorIdleMarker`
(crouched mending: nets on piers, boats), `DefaultRepairItemsIdleMarker`, `DefaultSmokingIdleMarker`,
`DefaultFireBarrelIdleMarker`, `DefaultGuardMarker`, `DefaultHumanIdleMarker`, `DefaultStandingArmsFoldedIdleMarker`.
None are placed on Waikiki today, so its 1,428 actors only stand or wander. Patrols are heading markers in a ring
(`worldrec.patrol_ops`: XPRD wait, XLKR to the next) walked with the game's Patrol package.

## What goes where (from the survey, `D:\FOLab-activity\places.json`)

| Activity | Where (exists today) | Who | How |
|---|---|---|---|
| Market | the fruit stalls, lei stands, shave-ice carts and bamboo market stalls (103) | a seller at each cluster, 1-2 buyers | shopkeeper marker behind the stall, shopping markers in front; sandbox 256 |
| Fishing and nets | the harbour piers (dock pieces, 927) and the boats beside them | Waikiki locals | mending markers at the pier ends, standing markers at the edge facing the sea |
| Pirates at their boats | boats by pirate-held hotels (Koko Marina, Hawaiʻi Kai, the Kāhala) | pirates (the mod's own) | repair and yardwork markers between boat and crates; sandbox 512 |
| Huáng farming | the maize rows (470) near the courtyards | Nongmin | raking, watering, yardwork markers in the rows; their sandbox widened to reach |
| Guard patrols | between the court's lookouts round Waikiki, between the Huáng gate towers | Court Fighters, Shouwei | `patrol_ops` rings, 10 s at each tower |
| Kids | round the hotels' lawns and the Huáng courtyards | the game's child spawns in its kids' clothes | sandbox 512, no weapons |
| Evenings round fires | fire barrels and campfires in camps and courtyards | whoever lives there | fire-barrel and smoking markers |
| Wildlife | ground kinds where the census finds fewer than `worldlife.WILD_EVERY` | `worldlife.IN_THE_WILD` by ground kind and tier | `worldlife.wildlife`, only where thin |
| Road encounters (few) | the coast road and the ridge roads, away from towns | a pair of travellers (locals) walking between two road markers; a pirate press gang on the dangerous stretch; a dead traveller with a find | patrol rings of two; `lootplace` for the find |

## Order and checks

1. Survey (done): places and who already stands where.
2. Build `app/activity.py`: one ops function per row above, each a separate Undo so the user can pick.
3. Rehearse on the copy: every person on the navmesh, people counts and draws per spot, health 0 errors.
4. Pictures per area (where markers and people stand) for the morning.
5. Waits for the user's pick; then the story session's queue, one install on their word.

## Open, for the user

- Kids: the game's child spawns wear the game's kids' clothes. Should they?
- How many: the plan aims at about the game's busiest (20-30 people in the cells round a busy spot). More costs frame
  rate: Waikiki is already draw-bound.
