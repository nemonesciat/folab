"""Words to speech sounds for Kokoro, FOLab's own (no GPL parts: espeak-ng and phonemizer are GPL, so FOLab.exe carries
neither). American English, in the sound letters Kokoro was trained on (misaki's American set): IPA, with one letter for
each gliding vowel (A as in "day", I "my", O "go", W "now", Y "boy"), the flap ɾ ("butter"), ˈ and ˌ for stress just
before the stressed vowel.

Where a word's sounds come from, in order:
1. the CMU Pronouncing Dictionary (cmudict.dict beside this file; its licence in cmudict-LICENSE.txt: BSD-style,
   Carnegie Mellon University), its first pronunciation;
2. the word less an ending the dictionary has the rest of ('s, s, es, ed, ing, er, ly), the ending's sound added;
3. a Hawaiian word (only Hawaiian letters, ʻokina and kahakō included): read by Hawaiian spelling, stress on the
   second-to-last vowel, every other one before it lightly;
4. two dictionary words joined (sunbather, beachcomber);
5. English spelling rules (`_spell`): rough, but always something.
Numbers are said as words. `phonemes(text)` keeps the punctuation Kokoro reads for pauses and tone."""
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
_DICT = {}

VOWELS = {'AA': 'ɑ', 'AE': 'æ', 'AH': 'ʌ', 'AO': 'ɔ', 'AW': 'W', 'AY': 'I', 'EH': 'ɛ', 'ER': 'ɜɹ', 'EY': 'A', 'IH': 'ɪ',
          'IY': 'i', 'OW': 'O', 'OY': 'Y', 'UH': 'ʊ', 'UW': 'u'}
UNSTRESSED = {'AH': 'ə', 'ER': 'əɹ', 'IH': 'ɪ'}
CONSONANTS = {'B': 'b', 'CH': 'ʧ', 'D': 'd', 'DH': 'ð', 'F': 'f', 'G': 'ɡ', 'HH': 'h', 'JH': 'ʤ', 'K': 'k', 'L': 'l',
              'M': 'm', 'N': 'n', 'NG': 'ŋ', 'P': 'p', 'R': 'ɹ', 'S': 's', 'SH': 'ʃ', 'T': 't', 'TH': 'θ', 'V': 'v',
              'W': 'w', 'Y': 'j', 'Z': 'z', 'ZH': 'ʒ'}
# short words said without stress in running speech
WEAK = {'a', 'an', 'the', 'to', 'of', 'and', 'or', 'but', 'for', 'at', 'in', 'on', 'from', 'with', 'as', 'by', 'is',
        'are', 'was', 'were', 'be', 'been', 'am', 'it', 'its', 'he', 'she', 'we', 'they', 'you', 'him', 'her', 'them',
        'us', 'me', 'my', 'your', 'our', 'their', 'his', 'that', 'than', 'then', 'can', 'could', 'would', 'should',
        'will', 'shall', 'do', 'does', 'did', 'have', 'has', 'had', 'not', 'so', 'if', 'up'}
PUNCT = set(',.!?;:—…"“”()')


def _load():
    if _DICT:
        return _DICT
    with open(os.path.join(HERE, 'cmudict.dict'), encoding='utf-8') as f:
        for line in f:
            line = line.split('#', 1)[0].strip()
            if not line:
                continue
            word, *phones = line.split()
            if '(' in word:              # a second pronunciation: the first is kept
                continue
            _DICT[word] = phones
    return _DICT


def arpabet(word):
    """The dictionary's sounds for a word, or None."""
    return _load().get(word.lower())


def from_arpabet(phones, weak=False):
    """ARPAbet (stress digits on vowels) to Kokoro's sound letters, with stress marks and the American flap."""
    out = []
    n = len(phones)
    for i, p in enumerate(phones):
        base, stress = p.rstrip('012'), p[len(p.rstrip('012')):]
        if base in VOWELS:
            s = int(stress or 0)
            if weak:
                s = 0
            sound = VOWELS[base] if s else UNSTRESSED.get(base, VOWELS[base])
            out.append(('ˈ' if s == 1 else 'ˌ' if s == 2 else '') + sound)
        else:
            c = CONSONANTS.get(base, '')
            # t or d between a vowel and an unstressed vowel is a flap in American speech ("butter", "ladder")
            if base in ('T', 'D') and 0 < i < n - 1:
                before, after = phones[i - 1], phones[i + 1]
                if (before.rstrip('012') in VOWELS or before in ('R',)) and after.rstrip('012') in VOWELS and after.endswith('0'):
                    c = 'ɾ'
            out.append(c)
    return ''.join(out)


# ---------- words the dictionary hasn't ----------

ENDINGS = [("'s", ['Z']), ("s'", ['Z']), ('ies', ['IY0', 'Z']), ('es', ['IH0', 'Z']), ('s', ['Z']), ('ed', ['D']),
           ('ing', ['IH0', 'NG']), ('er', ['ER0']), ('ers', ['ER0', 'Z']), ('ly', ['L', 'IY0'])]
VOICELESS = {'P', 'T', 'K', 'F', 'TH'}


def _with_ending(word):
    for end, add in ENDINGS:
        if word.endswith(end) and len(word) > len(end) + 2:
            stem = word[:-len(end)]
            for s in (stem, stem + 'e', stem[:-1] if len(stem) > 2 and stem[-1] == stem[-2] else None,
                      stem[:-1] + 'y' if end == 'ies' else None):
                ph = arpabet(s) if s else None
                if ph:
                    last = ph[-1].rstrip('012')
                    if add == ['Z'] and last in VOICELESS:
                        add = ['S']
                    if add == ['Z'] and last in ('S', 'Z', 'SH', 'ZH', 'CH', 'JH'):
                        add = ['IH0', 'Z']
                    if add == ['D'] and last in VOICELESS | {'S', 'SH', 'CH'}:
                        add = ['T']
                    if add == ['D'] and last in ('T', 'D'):
                        add = ['IH0', 'D']
                    return ph + add
    return None


HAWAIIAN = set("aeiouhklmnpwʻ'āēīōū")
H_VOWEL = {'a': 'ɑ', 'e': 'ɛ', 'i': 'i', 'o': 'O', 'u': 'u'}
H_DIPH = {'ai': 'I', 'ae': 'I', 'ao': 'W', 'au': 'W', 'ei': 'A', 'oi': 'Y', 'ou': 'O'}
H_LONG = {'ā': 'a', 'ē': 'e', 'ī': 'i', 'ō': 'o', 'ū': 'u'}


def is_hawaiian(word):
    w = word.lower()
    if not w or set(w) - HAWAIIAN or len(w) < 3:
        return False
    # every consonant followed by a vowel, never two consonants together, ends in a vowel
    plain = ''.join(H_LONG.get(c, c) for c in w if c not in "ʻ'")
    return plain[-1] in 'aeiou' and not re.search('[hklmnpw][hklmnpw]', plain)


def _hawaiian(word):
    """Hawaiian spelling read as Hawaiian, stress on the second-to-last vowel sound."""
    w = word.lower()
    units = []                 # (sound, is a vowel)
    i = 0
    while i < len(w):
        c = w[i]
        if c in "ʻ'":
            units.append(('ʔ', False))
            i += 1
            continue
        if c in H_LONG:
            units.append((H_VOWEL[H_LONG[c]], True))
            i += 1
            continue
        if c in H_VOWEL:
            two = w[i:i + 2]
            if two in H_DIPH:
                units.append((H_DIPH[two], True))
                i += 2
            else:
                units.append((H_VOWEL[c], True))
                i += 1
            continue
        units.append(({'w': 'w'}.get(c, c), False))
        i += 1
    # the same vowel twice running is two syllables, an ʻokina between them that the spelling left out (Kuliʻouʻou)
    for n in range(len(units) - 1, 0, -1):
        if units[n][1] and units[n - 1][1] and units[n][0] == units[n - 1][0]:
            units.insert(n, ('ʔ', False))
    vowels = [n for n, (_s, v) in enumerate(units) if v]
    main = vowels[-2] if len(vowels) >= 2 else vowels[-1] if vowels else None
    out = []
    for n, (s, v) in enumerate(units):
        if v and n == main:
            s = 'ˈ' + s
        elif v and main is not None and n < main and (vowels.index(main) - vowels.index(n)) % 2 == 0:
            s = 'ˌ' + s
        out.append(s)
    return ''.join(out)


def _compound(word):
    d = _load()
    for cut in range(len(word) - 3, 2, -1):
        a, b = word[:cut], word[cut:]
        if a in d and (b in d or _with_ending(b)):
            pb = d.get(b) or _with_ending(b)
            # the second part loses its main stress to the first
            return d[a] + [p.replace('1', '2') for p in pb]
    return None


# English spelling to ARPAbet, a small set of rules: longest match first, left to right
_RULES = [
    ('tch', ['CH']), ('igh', ['AY1']), ('ough', ['AO1']), ('augh', ['AO1']), ('tion', ['SH', 'AH0', 'N']),
    ('sion', ['ZH', 'AH0', 'N']), ('ture', ['CH', 'ER0']), ('ph', ['F']), ('sh', ['SH']), ('ch', ['CH']),
    ('th', ['TH']), ('wh', ['W']), ('ck', ['K']), ('ng', ['NG']), ('qu', ['K', 'W']), ('kn', ['N']), ('wr', ['R']),
    ('ee', ['IY1']), ('ea', ['IY1']), ('oo', ['UW1']), ('ou', ['AW1']), ('ow', ['OW1']), ('ai', ['EY1']),
    ('ay', ['EY1']), ('oa', ['OW1']), ('oi', ['OY1']), ('oy', ['OY1']), ('au', ['AO1']), ('aw', ['AO1']),
    ('ie', ['IY1']), ('ei', ['EY1']), ('ey', ['EY1']), ('ue', ['UW1']), ('ew', ['UW1']),
    ('ar', ['AA1', 'R']), ('er', ['ER0']), ('ir', ['ER1']), ('or', ['AO1', 'R']), ('ur', ['ER1']),
    ('a', ['AE1']), ('e', ['EH1']), ('i', ['IH1']), ('o', ['AA1']), ('u', ['AH1']), ('y', ['IH0']),
    ('b', ['B']), ('c', ['K']), ('d', ['D']), ('f', ['F']), ('g', ['G']), ('h', ['HH']), ('j', ['JH']), ('k', ['K']),
    ('l', ['L']), ('m', ['M']), ('n', ['N']), ('p', ['P']), ('r', ['R']), ('s', ['S']), ('t', ['T']), ('v', ['V']),
    ('w', ['W']), ('x', ['K', 'S']), ('z', ['Z']),
]


def _spell(word):
    w = re.sub('[^a-z]', '', word.lower())
    out, i = [], 0
    magic = len(w) > 3 and w.endswith('e') and w[-2] not in 'aeiouy' and w[-3] in 'aeiou'
    if magic:
        w = w[:-1]
    long_of = {'a': 'EY1', 'e': 'IY1', 'i': 'AY1', 'o': 'OW1', 'u': 'UW1'}
    while i < len(w):
        if w[i] == 'c' and i + 1 < len(w) and w[i + 1] in 'eiy':
            out.append('S')
            i += 1
            continue
        if w[i] == 'y' and i == len(w) - 1 and i > 0:
            out.append('IY0')
            i += 1
            continue
        for k, v in _RULES:
            if w.startswith(k, i):
                if magic and len(k) == 1 and k in long_of and i == len(w) - 2:
                    v = [long_of[k]]
                out.extend(v)
                i += len(k)
                break
        else:
            i += 1
    # one main stress: the first stressed vowel keeps it, the rest are unstressed
    seen = False
    for n, p in enumerate(out):
        if p[-1:] in '12':
            out[n] = p[:-1] + ('0' if seen else '1')
            seen = True
    return out


def word_sounds(word):
    w = word.lower().strip("'")
    if not w:
        return ''
    weak = w in WEAK
    ph = arpabet(w)
    if ph:
        return from_arpabet(ph, weak and len(ph) <= 4)
    if is_hawaiian(word):
        return _hawaiian(word)
    ph = _with_ending(w) or _compound(w) or _spell(w)
    return from_arpabet(ph)


# ---------- numbers ----------

_ONES = 'zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen'.split()
_TENS = 'twenty thirty forty fifty sixty seventy eighty ninety'.split()


def number_words(n):
    if n < 20:
        return _ONES[n]
    if n < 100:
        return _TENS[n // 10 - 2] + ('' if n % 10 == 0 else ' ' + _ONES[n % 10])
    if n < 1000:
        return _ONES[n // 100] + ' hundred' + ('' if n % 100 == 0 else ' ' + number_words(n % 100))
    for size, name in ((10 ** 9, 'billion'), (10 ** 6, 'million'), (1000, 'thousand')):
        if n >= size:
            return number_words(n // size) + ' ' + name + ('' if n % size == 0 else ' ' + number_words(n % size))
    return str(n)


def _say_number(m):
    s = m.group(0).replace(',', '')
    if '.' in s:
        a, b = s.split('.', 1)
        return number_words(int(a or 0)) + ' point ' + ' '.join(_ONES[int(c)] for c in b)
    n = int(s)
    if 1100 <= n <= 2099 and n % 100 and len(s) == 4 and not 2000 <= n < 2010:     # a year: twenty seventy-seven
        return number_words(n // 100) + ' ' + (('oh ' + _ONES[n % 100]) if n % 100 < 10 else number_words(n % 100))
    return number_words(n)


ABBREV = {'mr': 'mister', 'mrs': 'missus', 'ms': 'miz', 'dr': 'doctor', 'st': 'saint', 'jr': 'junior', 'sr': 'senior',
          'vs': 'versus', 'etc': 'et cetera', 'ok': 'okay', 'ncr': 'N C R', 'usa': 'U S A', 'pip-boy': 'pip boy'}
LETTERS = {c: s for c, s in zip('abcdefghijklmnopqrstuvwxyz', 'A bi si di i ɛf ʤi Aʧ I ʤA kA ɛl ɛm ɛn O pi kju ɑɹ ɛs ti ju vi dʌbəlju ɛks wI zi'.split())}


def phonemes(text):
    """A line's words as Kokoro's sound letters: words apart by spaces, the punctuation Kokoro reads kept."""
    text = text.replace('’', "'").replace('‘', "'").replace('--', '—')
    text = re.sub(r'\b(Mr|Mrs|Ms|Dr|St|Jr|Sr|vs|etc)\.', r'\1', text, flags=re.I)     # (not the end of a sentence)
    text = re.sub(r'\d[\d,]*(\.\d+)?', _say_number, text)
    out = []
    for tok in re.findall(r"[A-Za-zĀāĒēĪīŌōŪūʻ'\-]+|[,.!?;:—…\"“”()]", text):
        if tok in PUNCT:
            if out and out[-1] == ' ':
                out.pop()
            out.append(tok)
            out.append(' ')
            continue
        low = tok.lower()
        if low in ABBREV:
            words = ABBREV[low].split()
        else:
            words = [w for w in tok.split('-') if w]
        for w in words:
            if len(w) == 1 and w.isupper() and w != 'I' and w.lower() in LETTERS:
                out.append('ˈ' + LETTERS[w.lower()])
            elif w.isupper() and len(w) <= 4 and not arpabet(w) and not is_hawaiian(w):
                out.append(' '.join('ˈ' + LETTERS[c] for c in w.lower() if c in LETTERS))    # an initialism: N C R
            else:
                out.append(word_sounds(w))
            out.append(' ')
    return ''.join(out).strip()


if __name__ == '__main__':
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    print(phonemes(' '.join(sys.argv[1:]) or 'Aloha, stranger. The sea brought you, so the sea can feed you.'))
