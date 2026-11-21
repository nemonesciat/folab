# How FOLab builds a gun

Read from the game's own files on 20 Nov 2026 (the Light Machine Gun, Riot Shotgun, Grenade Machinegun and their first-person
animations in `meshes\characters\_1stperson\`). fnv_decomp was not needed.

## What the game does

- **A gun is not skinned.** Its model is a plain tree of named nodes under the root. Nothing is weighted to bones.
- **The animations move parts by name.** Each first-person animation file (`2hareloadi.kf`, `2haattackloop.kf`, ...) holds
  the arm bones *and* keys for weapon parts, found by node name: `##riotClip`, `##riotMechanism`, `##Trigger`, `##Bolt`,
  `##Magazine`, ... One reload animation serves every gun that names its parts that way. A gun that lacks a part the file
  names is fine: the Light Machine Gun has no `##riotshell`, which ReloadI moves.
- **Parts rest at the gun's origin.** Every moving node of the game's guns sits at (0, 0, 0), unturned, its shape placed in
  the gun's frame. The animation's keys are moves from there (ReloadI takes `##riotClip` down 16 and out 11 and back; each
  shot of AttackLoop slides `##riotMechanism` back 9.4). So a part of ours moves right if its shape sits where the game
  gun's part sits.
- **Every node carries an empty transform controller** (`NiTransformController` + `NiTransformInterpolator`, pose unset),
  as the Light Machine Gun has on all seven of its nodes. The animations bind to those.
- **Marker nodes:** `ProjectileNode` (the muzzle; turned so its local y runs forward), `ShellCasingNode` (where the case
  flies from, turned the way it flies), `##SightingNode` (where the eye goes when aiming down the sights; the sight line
  runs forward from it along x).
- **The frame:** x forward, y up, z to the right; the hand's grip at the origin (the trigger about 3-4 ahead of it).
- **The root:** BSFadeNode with BSXFlags 67 (animated, collision, moves) and `Prn` = `Weapon` (the bone it hangs on), one
  loose box of collision on the weapons' layer (as the clubs: `nifmake._held_body`).
- **One model for both views.** The game's guns name the same file as the world model and the first-person static
  (`1stPersonLightMachineGun` names `LightMachineGun.NIF`).
- **The record** (WEAP DNAM) picks the animations: `Animation type` (6 = two-handed automatic), `Reload animation`
  (8 = ReloadI), `Attack animation` (74 = AttackLoop, automatic fire).

## Which game gun to ride on

The parts a reload names decide it. Two-handed automatic guns and what their reloads move:

| reload | moves | game gun |
| --- | --- | --- |
| ReloadE | `##Magazine`, `##Bolt` | assault rifle kind |
| ReloadI | `##riotClip` (a drum or box under the receiver, ahead of the trigger), `##riotMechanism` | Riot Shotgun, Light Machine Gun |
| ReloadG | `##22smgClip`, `##Mechanism`, `##Catch22` | .22 SMG |
| ReloadH | `##127SmgClip`, `##127SmgChargingHandle` | 12.7mm SMG |

The **QLZ-87** (China's 35 mm automatic grenade launcher: stock, pistol grip, drum under the receiver ahead of the grip,
bipod) rides on the **Light Machine Gun**: same layout, automatic fire (AttackLoop), the drum taken off and put back by
ReloadI. The game's own Grenade Machinegun is a minigun-style hip gun (2HandHandle), the wrong hold. What it fires is the
Grenade Machinegun's: its 25mm grenades, projectile, impact, sounds and shell case.

Rifles and pistols later pick their base the same way: find the game gun whose parts lie as ours do, use its part names.

## How it's built (`app/guns.py`, `app/gunmake.py`)

- `gunmake.build_gun(name, parts, marks, mass)` writes the model: parts are `(node name or None, shapes)`; a named part
  gets its own node with an empty controller, the body's shapes hang from the root; marks are the marker nodes.
- `guns.py` holds each gun: its shapes in the base gun's frame, measured against that gun's parts (`BASE_PARTS`, read
  from the game's model by the tests), its own textures, and its records: a WEAP copied from the ride-on gun (animations,
  hold) with the fire gun's ammo, projectile, sounds and numbers laid over, and a 1stPerson STAT naming the same model.
- Tests (`tests/test_guns.py`): each moving part sits where the base gun's does (the drum's middle near the box's, the
  trigger on the trigger), the marker nodes are there, every node has its controller, the record's animations are the
  base's and its ammo the fire gun's.

## Not known yet

- Whether nv-rs plays the parts' keys (it has to, for the game's own guns).
- The Pip-Boy picture: the Grenade Machinegun's for now.
- 35 mm ammo of the mod's own: it fires the game's 25mm grenades for now.
