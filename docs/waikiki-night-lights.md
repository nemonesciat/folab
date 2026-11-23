# Waikiki at night: lights, and a reason for power

The user, 21 Nov 2026: "especially the ideas with lights. tiki torches, lanterns, strings of lanterns or lights, etc. a
reason for power to be useful".

## Built tonight (lights only, no new story)

`app/nightlights.py`. FOLab's own pieces (set `night`), each in a lit version and a day twin:

- **Fire** (anywhere): tiki torches whose flame burns only at night, fire pits (lava-stone ring, coals that glow, a fire
  at night), paper lanterns hung under eaves (red, white, amber), oil lamps (hurricane lamps), lantern posts (a bamboo
  post with an oil lamp on an arm), strings of paper lanterns on poles or hung between huts.
- **Power** (only where there is power): strings of bulbs on dressed poles with their cable run down one pole, and a
  small petrol generator nearby to run them.

Where they go:

| Place | Power? | What |
| --- | --- | --- |
| The Royal Hawaiian (the Kahuna's court), the Moana, the Kilauea | yes | generator, 6 strings of bulbs, 4 lantern posts each |
| FOLab's other hotels (Makai Tower and the rest) | no | a string of paper lanterns, 3 torches |
| Tiki bars | no | paper lanterns at the eaves, a string of paper lanterns |
| Bamboo village: huts, cookhouses, market stalls | no | lanterns at the eaves, a torch by each hut door, paper strings along the cookhouse and between huts, a fire pit by each cookhouse |
| Squatters', refugee and settlers' camps | no | fire pit, 3 torches, 2 lantern posts |
| Raider camps | no | fire pit, a torch |
| The Ala Wai harbour's piers | no | lantern posts on the planking |

On at dusk, off by day: everything lit, and every real light, is a child of one marker, `FOLabNightLights`. A
start-game quest's script turns the marker on from 19:00 to 06:00 and off by day. The day twins are its children the
opposite way, so by day you see the same lanterns unlit, with no lights to pay for.

Budget: no two real lights within 900 units of each other (the world's own lights count), at most 4 new ones in a cell,
and at most 90 new draws in a cell. A lit piece without a real light of its own still glows. There are no far models:
the pieces are too small for the far view, like the game's own lamps.

Not yet seen in either game. In nv-rs, the enable parent's "opposite" flag and the script's Enable/Disable on a
persistent marker are what to watch. If the twins both show, or neither shows, that is the cause.

## How power could matter in play (ideas to pick from)

None of these are built. Each one is small and uses only what is above.

1. **Fix the generator, light the camp.** A settlement's generator stands broken (a `dppGeneratorBroken`-like look, or
   ours with a part missing). Repairing it (a Repair check, or bringing a part) switches on that camp's strings of
   bulbs. The camp's people say thanks, sell at better prices, or stay open at night. One enable parent per camp, set
   by the quest.
2. **Fuel as trade.** Generators eat fuel: a camp with power buys fuel cans (an item of the mod's own, or Fission
   Batteries and Energy Cells as the game's currency of power). A trader at the Kahuna's court pays well for them.
   With no fuel delivered for a week, the court's lights fall back to torches (a GameDaysPassed check in the same
   script).
3. **The court's light as a sign of power.** Only the Kahuna's court and the hotels he allows have electric light: a
   line or two from the court's people saying so, and a marker on the map that only shows at night. This is lore
   colour, so it needs the user's say before it is written.
4. **The Vault's trade in power cells.** When the Ka'au vault is in, its trader sells power cells and small
   generators. Placing a generator by a hut (a craft recipe or a placeable item) lights it.
5. **Night is dangerous; light is safe.** Lit camps keep the wildlife away at night: no hostile spawns within the
   lights' reach of a lit camp while it is lit. This uses the same enable parent on the camp's encounter markers,
   the opposite way.
6. **Sabotage.** Pirates cut a powered place's cable at night. A short quest: find the cut (a cable piece by a pole),
   fix it, and the lights come back.

Pick one or two and say which. Each is one Undo on top of the night lights.
