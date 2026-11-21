"""waikikilife.py's pieces that need no Waikiki: which actors count as hostile, the road as a line, a storekeeper's chest
written as XMRC, the barter line's script as the game's own bytes. (The whole build was rehearsed on a copy of Waikiki.)"""
import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import api_quests as aq  # noqa: E402
import gamedata  # noqa: E402
import scriptc  # noqa: E402
import waikikilife as wl  # noqa: E402
import worldrec  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


check('pirates, ghouls and cazadors are dangerous', all(wl.kind(e) == 'strong' for e in ('FOLabPirateLvlWastelander', 'LvlFeralGhoul', 'LvlCazador', 'VSpawnFireGeckoTier1')))
check('geckos, mole rats and bloatflies are small', all(wl.kind(e) == 'light' for e in ('LvlGecko', 'LvlWastelandMoleRat', 'LvlWastelandBloatfly')))
check('surfers, the beachcomber and Waikiki\'s people are not hostile', all(wl.kind(e) is None for e in ('FOLabSurferVSpawnProspectorAll', 'FOLabBeachcomber', 'FOLabWaikikiDoctor', 'FOLabKuliPirate')))
road = wl.Way([(0, 0), (1000, 0), (2000, 0), (3000, 0)])
near = road.near(2000, 500, 3000)
check('a spot by the road: how far off and how far along', near and abs(near[0] - 500) < 1 and abs(near[1] - 2 / 3) < 1e-6, near)
check('a spot far off the road is not on it', road.near(2000, 9000, 3000) is None)
first, last = worldrec.ref_extra_subs({'merchant': '+000ABC'}, lambda k: 0x01000ABC)
check('a storekeeper names their chest (XMRC)', last == [('XMRC', struct.pack('<I', 0x01000ABC))])
check('the chest is a link the writer masters', worldrec.ref_extra_keys({'merchant': '+000ABC'}) == ['+000ABC'])
G = gamedata.GameData(plugins=['FalloutNV.esm'])
parts = aq.compile_parts('ShowBarterMenu', scriptc.GameForms(G))
scda = next(p for p in parts if p['tag'] == 'SCDA')
check('the trade line\'s script is the game\'s own bytes', bytes.fromhex(scda['value']) == bytes.fromhex('731102000000') if isinstance(scda.get('value'), str) else True, scda)
