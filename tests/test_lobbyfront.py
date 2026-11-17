"""The hotels with lobbies as the town sees them (hotelinside's 'seen from outside'): each closed piece shows its lobby
through glass on its ground floor, lit (something there glows), while what stops you stays the block it always was (a
solid box the full height of the block, the lobby's own parts solid nowhere), and from afar its ground floor is the lit
band (the far model draws the skin with its far picture, the near model draws none of it)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import historicset as hs  # noqa: E402
import hotelinside as hi  # noqa: E402
import modelmake  # noqa: E402
import modelsets  # noqa: E402
import towerset  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


BLOCKS = {'royal_hawaiian': [hs.RH_W, hs.RH_D, hs.RH_FLOORS * modelsets.FLOOR], 'moana': [hs.MO_W, hs.MO_D, hs.MO_FLOORS * modelsets.FLOOR]}
for piece in ('royal_hawaiian', 'moana', 'kilauea'):
    desc = modelsets.PIECES[piece]['describe']()
    looks = desc['looks']
    # (a building with its trees has its looks named '0_...': modelsets.combine)
    bare = lambda n: n.split('_', 1)[1] if n and n[:1].isdigit() and n[1:2] == '_' else n
    drawn = set()
    for p in desc['parts']:
        drawn |= {p.get('look'), p.get('cap_look')} | set((p.get('faces') or {}).values())
    named = {bare(n): n for n in drawn if n}
    glass = {'rhl_glass', 'kil_clear'} & set(named)
    lit = {b for b, n in named.items() if looks[n].get('glow')}
    check('%s: its lobby shows through glass, lit' % piece, glass and {'rhl_inside_lit', 'lobby_lamp'} & lit or (piece == 'kilauea' and glass and 'kil_slots' in lit),
          (sorted(glass), sorted(lit)))
    shown = [p for p in desc['parts'] if bare(p.get('look')) in set(hi.LIT.values()) | {'rhl_glass', 'kil_clear', 'kil_slots', 'lobby_lamp'}]
    check('%s: nothing of the lobby is solid' % piece, shown and not any(p.get('solid', True) for p in shown), len(shown))
    if piece in BLOCKS:
        whole = [p for p in desc['parts'] if p.get('shape') == 'box' and p.get('size') == BLOCKS[piece] and p.get('at') == [0, 0, 0]]
        check('%s: what stops you is the whole block, as before, drawn by nothing but its roof' % piece,
              len(whole) == 1 and whole[0].get('solid', True) and all(v is None for f, v in whole[0]['faces'].items() if f != 'top'), len(whole))
    far = modelsets.far_of(desc)
    skins = [n for b, n in named.items() if b in ('rh_hide_front', 'mo_hide_front', 'kil_hide')]
    far_tex = {far['looks'][n]['tex'] for n in skins}
    check('%s: from afar its ground floor is the lit band, near it is cut away' % piece,
          far_tex and all('far_' in t for t in far_tex) and all(looks[n]['tex'].endswith('clear.dds') and looks[n]['alpha'] for n in skins),
          sorted(far_tex))
    m = modelmake.make(desc)
    check('%s: within what a building may be' % piece, m['triangles'] <= modelmake.MOST_BUILDING, m['triangles'])

# (the way up: each lobby's lift stands in a frame of the lobby's own, on a wall: the game's lift door is two thin leaves
# made round their middle, and stood on the floor without a frame it read as nothing, 17 Nov 2026)
LIFTS = {'royal_hawaiian': ('royal_hawaiian_open', [('lift', 0.0)], hi.FLOOR_TOP), 'moana': ('moana_open', [('lift', 0.0)], hi.FLOOR_TOP),
         'kilauea': ('kilauea_open', [('lift', 0.0), ('lookout', hi.KIL_DECK)], hi.KIL_FLOOR)}
for hotel, (piece, doors, top) in LIFTS.items():
    spec = {d[0]: d for d in hi.VIEWS[hotel]['doors']}
    for open_piece in (piece, hi.VIEWS[hotel]['closed']):
        desc = modelsets.PIECES[open_piece]['describe']()
        for name, _z in doors:
            if open_piece == hi.VIEWS[hotel]['closed'] and name == 'lookout':
                continue                    # (the Kilauea's deck is only open in its small world)
            _n, _e, dx, dy, dz, _face = spec[name]
            frame = [p for p in desc['parts'] if p.get('shape') == 'box' and abs(p['at'][0] - dx) < 200 and abs(p['at'][1] - dy) < 200
                     and abs(p['at'][2] - (top + dz)) < 260 and (p['size'][2] > 150 or p['size'][0] > 250)]
            check('%s: the %s in %s stands in a frame' % (hotel, name, open_piece), len(frame) >= 3, len(frame))
rh = modelsets.PIECES['royal_hawaiian_open']['describe']()
bank = [p for p in rh['parts'] if p.get('shape') == 'box' and p.get('size', [0])[0] == hi.BANK]
check('the Royal Hawaiian\'s lifts stand on a solid bank, not in front of its windows',
      len(bank) == 1 and bank[0].get('solid', True) and abs(bank[0]['at'][0] - (hs.RH_W / 2.0 - hi.WALL - hi.BANK / 2.0)) < 1, len(bank))
