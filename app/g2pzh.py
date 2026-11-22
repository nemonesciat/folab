"""Mandarin, written in pinyin, to the sound letters Kokoro (v1.0) reads, and to mouth shapes for the .lip.

FOLab's own rules, written from what Kokoro's Chinese voices were trained on (the misaki library's v1.0 Mandarin rules:
one letter or letter pair per initial, the final's vowel carrying the tone as an arrow): no dictionary of characters,
since FOLab's Chinese lines are written in pinyin anyway (the game's fonts have no Chinese characters, so pinyin is what
shows on screen).

Input: pinyin words separated by spaces, syllables run together or apart, tones as numbers (hai3xin1) or marks
(hǎixīn); a syllable with no tone is neutral. Punctuation , . ! ? ; : is kept as a pause.

    sounds('Hai3xin1 dong4tai4.')   ->  'xai↓ɕi→n tʊ↘ŋtʰai↘.'
    shown('Hǎixīn dòngtài')         ->  'Haixin dongtai'   (what the game can print: cp1252 has no ǎ, ī)"""
import re
import unicodedata

INITIALS = {'b': 'p', 'p': 'pʰ', 'm': 'm', 'f': 'f', 'd': 't', 't': 'tʰ', 'n': 'n', 'l': 'l', 'g': 'k', 'k': 'kʰ', 'h': 'x',
            'j': 'ʨ', 'q': 'ʨʰ', 'x': 'ɕ', 'zh': 'ꭧ', 'ch': 'ꭧʰ', 'sh': 'ʂ', 'r': 'ɻ', 'z': 'ʦ', 'c': 'ʦʰ', 's': 's'}
# finals: (before the tone, after it); the tone goes after the vowel that carries it, before a final n or ŋ
FINALS = {'a': ('a', ''), 'ai': ('ai', ''), 'an': ('a', 'n'), 'ang': ('a', 'ŋ'), 'ao': ('au', ''), 'e': ('ɤ', ''), 'ei': ('ei', ''),
          'en': ('ə', 'n'), 'eng': ('ə', 'ŋ'), 'i': ('i', ''), 'ia': ('ja', ''), 'ian': ('jɛ', 'n'), 'iang': ('ja', 'ŋ'), 'iao': ('jau', ''),
          'ie': ('je', ''), 'in': ('i', 'n'), 'iou': ('jou', ''), 'ing': ('i', 'ŋ'), 'iong': ('jʊ', 'ŋ'), 'ong': ('ʊ', 'ŋ'), 'ou': ('ou', ''),
          'u': ('u', ''), 'uei': ('wei', ''), 'ua': ('wa', ''), 'uai': ('wai', ''), 'uan': ('wa', 'n'), 'uen': ('wə', 'n'),
          'uang': ('wa', 'ŋ'), 'ueng': ('wə', 'ŋ'), 'uo': ('wo', ''), 'o': ('wo', ''), 'ü': ('y', ''), 'üe': ('ɥe', ''),
          'üan': ('ɥɛ', 'n'), 'ün': ('y', 'n')}
ALONE = {'er': ('ɚ', ''), 'o': ('ɔ', ''), 'ê': ('ɛ', ''), 'm': ('m', ''), 'n': ('n', ''), 'ng': ('ŋ', '')}
TONES = {1: '→', 2: '↗', 3: '↓', 4: '↘', 5: ''}
# y- and w- spellings, and the short forms pinyin writes, as the finals they stand for
SPELT = {'yi': 'i', 'ya': 'ia', 'yan': 'ian', 'yang': 'iang', 'yao': 'iao', 'ye': 'ie', 'yin': 'in', 'ying': 'ing', 'you': 'iou',
         'yong': 'iong', 'yu': 'ü', 'yue': 'üe', 'yuan': 'üan', 'yun': 'ün', 'wu': 'u', 'wa': 'ua', 'wo': 'uo', 'wai': 'uai',
         'wei': 'uei', 'wan': 'uan', 'wen': 'uen', 'wang': 'uang', 'weng': 'ueng'}
MARKS = {'̄': 1, '́': 2, '̌': 3, '̀': 4}
_SYL = re.compile(r"(zh|ch|sh|[bpmfdtnlgkhjqxrzcsyw])?(i?[aeiouüv]+(?:ng|n|r)?|ng|n|m|r)(?=[^aeiouüv]|$)([1-5])?", re.I)
# mouth shapes: Mandarin's sounds as the nearest lipwrite knows
LIP = {'ꭧ': 'tʃ', 'ʨ': 'tʃ', 'ʦ': 's', 'ɕ': 'ʃ', 'ʂ': 'ʃ', 'ɻ': 'ɹ', 'ɤ': 'ə', 'ɥ': 'w', 'y': 'u'}


def split(word):
    """[(initial, final, tone)] of one pinyin word."""
    nfd = unicodedata.normalize('NFD', word.lower().replace('v', 'ü'))
    letters, tones = '', {}
    for ch in nfd:
        if ch in MARKS:
            tones[len(letters) - 1] = MARKS[ch]
        elif ch == '̈':
            letters = letters[:-1] + 'ü'
        else:
            letters += ch
    out, at = [], 0
    while at < len(letters):
        m = _SYL.match(letters, at)
        if not m or m.end() == at:
            raise ValueError('%r: no pinyin syllable at %r' % (word, letters[at:]))
        ini, fin, num = m.group(1) or '', m.group(2), m.group(3)
        # a syllable greedy past its end: 'xinan' is xi + nan only by tone marks or an apostrophe; prefer the longer final
        tone = int(num) if num else next((t for p, t in tones.items() if m.start(2) <= p < m.end(2)), 5)
        out.append((ini, fin, tone))
        at = m.end()
        while at < len(letters) and letters[at] in "'’-":
            at += 1
    return out


def syllable(ini, fin, tone):
    """One syllable's sounds."""
    if ini in ('y', 'w'):
        key = SPELT.get(ini + fin)
        if key is None:
            raise ValueError('%s%s is not a pinyin syllable' % (ini, fin))
        ini, fin = '', key
    if ini in ('j', 'q', 'x') and fin.startswith('u'):
        fin = 'ü' + fin[1:]
    fin = {'iu': 'iou', 'ui': 'uei', 'un': 'ün' if ini in ('j', 'q', 'x') else 'uen'}.get(fin, fin)
    if not ini and fin in ALONE:
        v, coda = ALONE[fin]
    elif fin == 'i' and ini in ('zh', 'ch', 'sh', 'r', 'z', 'c', 's'):
        v, coda = 'ɨ', ''
    elif fin in FINALS:
        v, coda = FINALS[fin]
    else:
        raise ValueError('%s%s is not a pinyin syllable' % (ini, fin))
    return INITIALS.get(ini, '') + v + TONES[tone] + coda


def sounds(text):
    """Pinyin text to Kokoro's sound letters: words apart by spaces, punctuation kept."""
    out = []
    for tok in re.findall(r"[^\s,.!?;:]+|[,.!?;:]", text.replace('，', ',').replace('。', '.').replace('？', '?').replace('！', '!')):
        if tok in ',.!?;:':
            if out:
                out[-1] += tok
            continue
        out.append(''.join(syllable(*s) for s in split(tok)))
    return ' '.join(out)


def shown(text):
    """The pinyin as the game can print it: tone marks and numbers off (its fonts are cp1252, which has u-umlaut)."""
    plain = unicodedata.normalize('NFC', ''.join(c for c in unicodedata.normalize('NFD', text) if c not in MARKS))
    return re.sub(r'(?<=[a-zA-Zü])[1-5]', '', plain)


def lip_sound(s):
    """A Mandarin sound as lipwrite's table has its nearest: tones and aspiration dropped."""
    s = s.replace('ʰ', '')
    return LIP.get(s, s)


def numbered(text):
    """The pinyin with tone numbers after each syllable (cp1252-safe, as a record keeps it): 'Hǎixīn' -> 'Hai3xin1'."""
    def word(m):
        w = m.group(0)
        out = []
        for ini, fin, tone in split(w):
            out.append('%s%s%d' % (ini, fin, tone))
        s = ''.join(out)
        return s[:1].upper() + s[1:] if w[:1].isupper() else s
    return re.sub(r"[^\s,.!?;:]+", word, text)
