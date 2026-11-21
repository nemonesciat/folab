"""FOLab's own words to sounds (g2p.py): dictionary words in Kokoro's letters with stress and the American flap, endings
the dictionary hasn't, Hawaiian names read as Hawaiian, numbers and years said, initialisms spelt, abbreviations not
taken for sentence ends; every sound it writes is in Kokoro's table and has a mouth shape; nothing GPL is loaded."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import g2p  # noqa: E402
import lipwrite  # noqa: E402
import voicegen  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (ascii(detail),) if detail != '' else ''))


P = g2p.phonemes
check('hello', P('hello') == 'həlˈO', P('hello'))
check('butter has the flap', P('butter') == 'bˈʌɾəɹ', P('butter'))
check('short words unstressed in a sentence', P('the sea') == 'ðə sˈi', P('the sea'))
check('an ending the dictionary hasn\'t', P('beachcombers').endswith('z') and 'ˈiʧ' in P('beachcombers'), P('beachcombers'))
check('Hawaiian: stress on the second-to-last vowel', P('Waimanalo') == 'wˌImɑnˈɑlO', P('Waimanalo'))
check('the okina is a stop', P('ʻIolani').startswith('ʔ'), P('ʻIolani'))
check('a year', P('2077') == P('twenty seventy seven'), P('2077'))
check('a count', P('12 caps') == P('twelve caps'))
check('an initialism spelt out', P('NCR') == 'ˈɛn ˈsi ˈɑɹ', P('NCR'))
check('Mr. is not a sentence end', '.' not in P('Mr. Smith'), P('Mr. Smith'))
check('punctuation kept for Kokoro', P('Yes, go.') == 'jˈɛs, ɡˈO.', P('Yes, go.'))
check('an unknown English word still says something', P('zorbleflax') != '', P('zorbleflax'))

vocab = json.load(open(os.path.join(os.path.dirname(g2p.__file__), 'kokorovocab.json'), encoding='utf-8'))
text = ('Aloha, stranger. The sea brought you, so the sea can feed you. Judge, church, thinking, measure, joy, button, bird, '
        'sing! Kuliouou, Hanauma Bay, Kamehameha; Mr. Jones paid 3.5 caps in 2077 for the NCR\'s "Pip-Boy" -- really?')
s = P(text)
check('every sound is in Kokoro\'s table', all(c in vocab for c in s), sorted({c for c in s if c not in vocab}))
merged = voicegen.merge_marks([(c, 0, 1) for c in s])
odd = sorted({p for p, _a, _b in merged if p.strip() and p not in ',.!?;:"()—…“”' and lipwrite.shape_of(p) is None})
check('every sound has a mouth shape', not odd, odd)
check('nothing GPL loaded', not [m for m in sys.modules if m.split('.')[0] in ('phonemizer', 'espeakng_loader', 'kokoro_onnx')])
