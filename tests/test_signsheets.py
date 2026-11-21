"""signsheets: Waikiki's sign pictures redrawn keep each old picture's size (the models show their panels by region), are
put in place of the sets' own once the sets are loaded, and turn into the game's files; signfont has every letter the
city's signs use; neon sheets carry a glow picture that lights only the tubes."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import modelsets  # noqa: E402
import signfont  # noqa: E402
import signpaint  # noqa: E402

OK = []


def check(name, cond, info=''):
    OK.append(bool(cond))
    print(('PASS' if cond else 'FAIL') + ' ' + name + (' (%s)' % (info,) if info and not cond else ''))


SIZES = {'waikiki/signs': (1024, 512), 'waikiki/motels': (512, 512), 'kiosk_signs': (512, 256), 'hotel/signs': (512, 512),
         'coast/signs': (1024, 1024), 'resort/signs': (1024, 1024), 'resort/kil_signs': (1024, 512), 'resort/tank': (1024, 256),
         'hist/rh_sign': (1024, 128), 'hist/mo_sign': (1024, 128), 'hist/nat_sign': (1024, 128), 'hist/bat_sign': (1024, 128)}

modelsets._all_sets()
import signsheets  # noqa: E402
for key, fn in [(k, getattr(signsheets, n)) for k, n in (('waikiki/signs', 'waikiki_signs'), ('kiosk_signs', 'kiosk'), ('resort/kil_signs', 'kil_signs'))]:
    check(key + ': the sheet in TEXTURES is signsheets\' own', modelsets.TEXTURES[key] is fn)

for key in ('waikiki/signs', 'kiosk_signs', 'resort/kil_signs', 'hist/rh_sign'):
    pic = modelsets.TEXTURES[key]()
    check(key + ': the old picture\'s size', (pic.w, pic.h) == SIZES[key], (pic.w, pic.h))
    check(key + ': solid (no see-through left from a shaped board)', pic.a is None)
    col, nor = pic.files(game=True)
    check(key + ': makes the game\'s pictures', col[:4] == b'DDS ' and nor[:4] == b'DDS ')

kil = modelsets.TEXTURES['resort/kil_signs']()
check('the Kilauea\'s sheet has a glow picture', getattr(kil, 'glow', None) is not None)
if kil.glow:
    w = kil.w
    lit = sum(1 for px in kil.glow.rgb if sum(px) > 60)
    check('only part of it lights (tubes and letters, not the board)', 0.02 < lit / float(w * kil.h) < 0.5, lit / float(w * kil.h))
    check('its glow picture is the game\'s kind of file', signpaint.glow_files(kil.glow)[:4] == b'DDS ')

used = set()
import coastset  # noqa: E402
import resortset  # noqa: E402
import waikikiset  # noqa: E402
for big, small in waikikiset.SIGNS:
    used |= set(big) | set(''.join(small))
used |= set(''.join(coastset.SIGN_LINES)) | set(''.join(resortset.SIGN_LINES))
used |= set('MAHALO MOTOR INN VACANCY SEA BREEZE MOTEL POOL TV KONA KAI COURTS TIKI ROOM COCKTAILS SURF & SNACKS SHAVE ICE COLD DRINKS BOARD RENTAL ALOHA')
used |= set('MAKAI TOWER BLUE LAGOON PINK PEARL HOTEL KAHUNA PALMS KILAUEA CASINO ROYAL HAWAIIAN MOANA WAIKIKI WAR MEMORIAL BATTERY RANDOLPH 1911 STOP 50 CENTS')
missing = sorted(ch for ch in used if ch != ' ' and ch not in signfont.GLYPHS)
check('signfont draws every letter the signs use', not missing, missing)

print('%d of %d' % (sum(OK), len(OK)))
sys.exit(0 if all(OK) else 1)
