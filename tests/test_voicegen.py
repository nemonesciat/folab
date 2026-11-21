"""Voice file names (voicegen.voice_path): worked out for every line of FalloutNV.esm from its quest, topic, form id and
response number, they name the game's own voice files (all but those whose lines the game no longer has); Kokoro's
length and stress marks fold into their sounds. Kokoro itself is not run here (FOLab.exe's Python hasn't it)."""
import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import bsa  # noqa: E402
import gamedata  # noqa: E402
import questrec  # noqa: E402
import tes4  # noqa: E402
import voicegen as V  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


def main():
    check('short names kept whole', V.cut_name('VCG01', 'GREETING') == 'VCG01_GREETING')
    check('long ones cut 10 and 15', V.cut_name('NVDLC01Elijah', 'NVDLC01EliGreetingTopic') == 'NVDLC01Eli_NVDLC01EliGreet')
    check('a short quest leaves the topic room', V.cut_name('VMS29a', 'VMS29aTopicAboutTheLake') == 'VMS29a_VMS29aTopicAboutThe')
    p = V.voice_path('Waikiki.esp', 'MaleOld01', 'WKQuest', 'GREETING', 0x0200ABCD, 2)
    check('the path as the game builds it', p == os.path.join('sound', 'voice', 'waikiki.esp', 'maleold01', 'wkquest_greeting_0000abcd_2'), p)
    m = V.merge_marks([('h', 0.0, 0.1), ('ˈ', 0.1, 0.15), ('i', 0.15, 0.3), ('ː', 0.3, 0.4), (' ', 0.4, 0.5)])
    check('stress gives its time to the next sound, length to the one before', m == [('h', 0.0, 0.1), ('i', 0.1, 0.4), (' ', 0.4, 0.5)], m)

    G = gamedata.GameData()
    li = questrec.line_index(G)
    a = bsa.Archive(os.path.join(gamedata.find_data_dir(), 'Fallout - Voices1.bsa'))
    files = {p.rsplit('\\', 1)[1][:-4] for p in a.files if p.endswith('.ogg') and '\\falloutnv.esm\\' in p}
    a.close()
    named, ids = set(), set()
    for f, (i, r) in G.forms.items():
        if r.tag != 'INFO' or i != 0:
            continue
        fl = G.fields(f)
        if 'QSTI' not in fl or f not in li.topic_of:
            continue
        ids.add('%08x' % (f & 0xFFFFFF))
        q = G.edid(G.to_global(i, struct.unpack('<I', fl['QSTI'])[0]))
        t = G.edid(li.topic_of[f])
        for tag, d in tes4.iter_subrecords(G.plugins[i].data(r)):
            if tag == 'TRDT':
                named.add(os.path.basename(V.voice_path('x', 'y', q, t, f, d[12])))
    left = files - named
    orphans = [n for n in left if n.split('_')[-2] not in ids]
    # what's left over is recordings of lines the game dropped (64), or later moved to another quest or topic or cut
    # short (21: Julie Farkas's moved from VFreeformFreeside to VMS47, Cass's vending lines lost responses 3-5)
    check('the game\'s voice files are named by the rule', len(files & named) >= 28700 and len(left) - len(orphans) <= 21,
          '%d named, %d left: %d lines the game no longer has, %d moved or cut' % (len(files & named), len(left), len(orphans),
                                                                               len(left) - len(orphans)))


main()
