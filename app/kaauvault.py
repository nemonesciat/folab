"""The Vault in Kaʻau Crater, inside: a generated layout over the game's vault kit, laid by kitplan and dressed by kitlife.

What the user decided (docs/waikiki-story-plan.md, 19 Nov 2026) and only that, unless `proposed` asks for more: the island's
one vault, still sealed and running on its own reactor (full power, comfort, security), the deepest thing in it; its
workshops keep the Pip-Boys working; it recharges power cells and pays in them, in medicine and in guns; its founding
families are an aristocracy, and its young grow up in comfort; its people eat the people it buys. The lore notes'
proposals (docs/waikiki-lore-additions.md: cold storage far too large, a "protein reclamation" plant, a medical wing built
like a butcher's) and anything not written down (where the bought people are kept) are `PROPOSED` rooms, left out unless
asked for. docs/waikiki-vault-plan.md is the plan and its open questions.

    program(size, rng, proposed=False)      the rooms, as kitplan Specs (each with its own `name`)
    make(game, kits, size, seed, store, cache, survey, proposed=False)   a walked, dressed layout (kitplan.vault_place)
    ops(...)                                the same as changes for a mod (never applied here)

Each room keeps its own name (`o['name']`): kitlife lays scenes and finds by that name (STORY) before its furnishing
purpose, so a founders' suite is dressed as a bedroom of the rich and the feast hall as a dining hall."""
import kitlife
import kitplan as P

STORY_KEY = 'kaau'
# rooms: (name, furnished as, width, depth, wing, on the main route, decided or proposed)
ROOMS = [
    ('the door landing', 'entrance', (4, 5), (4, 4), None, True, 'decided'),
    ('the atrium', 'atrium', None, None, None, True, 'decided'),
    ("a founders' suite", 'quarters', (4, 5), (4, 4), 'families', False, 'decided'),
    ('the schoolroom', 'classroom', (4, 5), (3, 4), 'families', False, 'decided'),
    ('the feast hall', 'mess', (6, 7), (5, 6), 'families', False, 'decided'),
    ('the Pip-Boy workshop', 'workroom', (4, 6), (4, 5), 'works', False, 'decided'),
    ('the cell charging room', 'workroom', (4, 5), (3, 4), 'power', False, 'decided'),
    ('the armoury', 'store', (3, 4), (3, 4), 'works', False, 'decided'),
    ('the clinic', 'clinic', (4, 5), (3, 4), 'works', False, 'decided'),
    ("the families' council", 'office', (4, 5), (3, 4), 'council', False, 'decided'),
    ('the reactor', 'reactor', (6, 8), (6, 7), 'power', False, 'decided'),
    # proposed only (lore notes), or not written down at all
    ('the cold store', 'store', (4, 6), (4, 5), 'power', False, 'proposed'),
    ('the reclamation plant', 'workroom', (5, 6), (4, 5), 'power', False, 'proposed'),
    ('the holding rooms', 'store', (3, 4), (3, 4), 'works', False, 'proposed'),
]
SUITES = 3              # (founders' suites at size 1; one more for every two of the dial)
SEED_APART = 101       # (vault_place tries seed, seed + 1...: seeds one apart would share their tries)

# what each room has in it, over what kitdress stands there: scenes of the game's own things (kitlife's form)
SCENES = {
    'suite': [('NVbedqueen01', 0, 70, None, None), ('TLPainting01', 0, 118, 2, 'wall'), ('NVCandlestick', 70, 30, 0, None), ('RugSmall01', 0, -10, 0, None)],
    'dressing room': [('TLPainting03', -60, 118, 2, 'wall'), ('Footlocker01HouseholdNV', 50, 84, None, None), ('Wine', 50, 84, 0, 1), ('RugSmall02', 0, -10, 0, None)],
    'banquet': [('NVULBanquetTable01', 0, 30, None, None), ('Plate01', -40, 30, 0, 0), ('Plate01', 40, 30, 0, 0), ('Wine', 0, 30, 0, 0), ('NVCandlestick', -10, 36, 0, 0)],
    'sideboard': [('Table01', 0, 60, None, None), ('Wine', -20, 60, 0, 0), ('Wine', 10, 60, 0, 0), ('Plate01', 30, 64, 0, 0), ('TLPainting02', 0, 118, 2, 'wall')],
    'lessons, kept': [('ChalkboardDirty01', 0, 118, 2, 'wall'), ('BenchMuseumStatic01', 0, -20, None, None), ('BookGeneric01', 40, -20, 0, 1), ('Globe00', 70, 70, 0, None)],
    'pip-boy bench': [('WorkBench', 0, 84, 2, None), ('ScrapElectronics', -30, 70, 0, 0), ('SpareParts', 30, 70, 0, 0), ('ComputerRack01', 90, 90, 2, None)],
    'charging': [('ComputerRack01', -60, 90, 2, None), ('ComputerRack01', 0, 90, 2, None), ('DrainedMicrofusionCell', 60, 40, 0, None), ('DrainedSmallEnergyCell', 40, 30, 0, None),
                 ('LootAmmoBoxMicroFusionCellsLock', 70, 80, None, None)],
    'gun racks': [('ToolCabinetMetal', -60, 84, 2, None), ('ReloadingBench', 40, 84, 2, None), ('LootAmmoBoxGenericLockNV', 80, 50, None, None)],
    'surgery': [('OperatingTableR01', 0, 50, None, None), ('SurgicalCart01', 70, 70, None, None), ('SurgicalTray01', 70, 70, 0, 1), ('SurgicalCartR01', -70, 70, None, None)],
    'council table': [('NVULBanquetTable02', 0, 40, None, None), ('ChairVaultStatic', -50, 0, 0, None), ('ChairVaultStatic', 50, 0, 0, None), ('TLPainting04', 0, 118, 2, 'wall')],
    'cold room': [('VLootFridgeClosed01Empty', -60, 90, 2, None), ('VLootFridgeClosed01Empty', 10, 90, 2, None), ('RaiderCorpseDressingChain', 70, 100, 0, None),
                  ('SurgicalTrayBloody01', -20, 30, 0, None)],
    'reclamation': [('NVGrinderWorkbench', 0, 84, 2, None), ('BigPot', -70, 70, 0, None), ('Vault87Blood02', 0, 20, 0, None), ('SurgicalBonesaw01', 40, 60, 0, None)],
    'held': [('NVBedrollL', -30, 40, None, None), ('Bucket01', 70, 70, 0, None), ('TinCan01', 30, -20, 0, None)],
}
STORY = {'given': True, 'kept': True, 'said': "Ka'au Crater's Vault: full power, the founding families' comfort, and what it runs on.",
         "a founders' suite": ('suite', 'dressing room'), 'the schoolroom': ('lessons, kept',), 'the feast hall': ('banquet', 'sideboard', 'banquet'),
         'the Pip-Boy workshop': ('pip-boy bench', 'charging'), 'the cell charging room': ('charging',), 'the armoury': ('gun racks',),
         'the clinic': ('surgery',), "the families' council": ('council table',), 'the reactor': ('charging',),
         'the cold store': ('cold room', 'cold room'), 'the reclamation plant': ('reclamation',), 'the holding rooms': ('held', 'held'),
         'the atrium': ('sideboard',), 'the door landing': (),
         'finds': {'the armoury': ('LootGunCabinetNVGunsLocked', 'LootAmmoBoxGenericLockNV'), 'the clinic': ('LootFirstAidKitLockNV', 'NVLootMedicalCabinet'),
                   'the cell charging room': ('LootAmmoBoxMicroFusionCellsLock', 'LootAmmoBoxPowerCellsRNDLock'), "a founders' suite": ('GenericSafeFloor01', 'Footlocker01HouseholdNV'),
                   'the Pip-Boy workshop': ('VLootStashToolboxAbandonedHi',)}}
WANT = {'entrance', 'atrium', 'reactor', 'quarters', 'mess', 'workroom'}


def _register():
    kitlife.SCENES.update(SCENES)
    kitlife.STORIES[STORY_KEY] = STORY


_register()


def program(size, rng, proposed=False):
    """The rooms for a dial of 1 to 10, as kitplan Specs. Every wing starts down a flight; the reactor is last and deepest."""
    size = max(1, min(10, int(size)))
    out, seen = [], set()
    for name, purpose, w, h, wing, main, kind in ROOMS:
        if kind == 'proposed' and not proposed:
            continue
        if purpose == 'atrium':
            a = (7 + size // 3, 9 + size // 3), (6 + size // 3, 8 + size // 3)
            out.append(P.Spec(purpose, a[0], a[1], True, fam='roomu', shape='box', tall=(a[1], (3, 4 + size // 3)), name=name))
            continue
        n = SUITES + size // 2 if purpose == 'quarters' else 1
        for _ in range(n):
            s = P.Spec(purpose, w, h, main, fam='roomu' if main else 'room', wing=wing, name=name,
                       whole='overseer' if purpose == 'office' else None, stairs=purpose in ('office', 'reactor'))
            out.append(s)
    # the reactor last, at the end of the power wing: what's laid last is furthest along, and every way on goes down
    out.sort(key=lambda s: s.purpose == 'reactor')
    for s in out[2:]:
        if s.whole:
            continue
        s.down = True
        if s.wing and s.wing not in seen:
            seen.add(s.wing)
            s.stairs = True
    return out


def make(game, kits, size, seed, store, cache, survey=None, proposed=False):
    """A walked, dressed layout: kitplan.vault_place's {'plan', 'made', 'items', 'walk', ...} or None."""
    return P.vault_place(game, kits, size, seed * SEED_APART, store, cache, survey, program=lambda sz, rng: program(sz, rng, proposed),
                         story=STORY_KEY, want=WANT, better=reactor_deepest)


def reactor_deepest(g):
    """(1 if the reactor is the deepest room, how near it is to that): what a layout of the Vault wants most."""
    plan = g['plan']
    low = min(c[2] for c in plan.squares())
    r = [o for o in plan.rooms() if o['purpose'] == 'reactor']
    if not r:
        return (0, -99)
    at = min(c[2] for c in r[0]['cells'])
    return (1 if at == low else 0, low - at)


def ops(game, kits, size, seed, at, store, cache, survey=None, proposed=False):
    """As changes for a mod ({'ops', 'start', 'said', 'plan'} or {'note'}): for a copy, never applied here."""
    name = 'dungeons' + chr(92) + 'vault'
    ts = P.tiles_for(game, kits, name, store, survey)
    best = make(game, kits, size, seed, store, cache, survey, proposed)
    if not best:
        return {'note': 'No layout passed the walk this time: try another seed.'}
    origin = (float(at[0]), float(at[1]), float(at[2]))
    out = P._with_key(game, P._report(ts, best['plan'], best['made'], origin, 'a', best['items']), seed)
    out['said'] = ' '.join(s for s in (STORY['said'], out['said'], kitlife.locks_said(best['plan'])) if s)
    return P._keep(store, ts, best, origin, out)
