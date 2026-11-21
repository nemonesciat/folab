# Voiced dialogue in FOLab: plan

For the user's okay before the big build. Written 20 Nov 2026.

The voice plan agreed: quests start silent; small talk reuses the game's own lines; main characters may get human
voice actors; synthesized voices are fine, but never cloned from the game's actors for anything released.

## What a voiced line is, to the game

Read from the game's files and fnv_decomp's names (`TESResponse::BuildResponseFileName`, `BuildQuestTopicName`,
`VFDialogue::BuildVoiceFilePath`, `BuildLipPath`):

    Data\Sound\Voice\<plugin>\<voice type>\<quest>_<topic>_<info id>_<response>.ogg   (and .lip beside it)

- `<plugin>`: the file the INFO comes from (Waikiki.esp for the mod's own lines).
- `<voice type>`: the editor ID of the speaker's voice type (the NPC's VTCK; an INFO's own speaker wins).
- `<quest>_<topic>`: the quest's and topic's editor IDs. If together they're over 25 letters, the quest is cut to 10
  and the topic to 15 (plus whatever the quest didn't use).
- `<info id>`: the INFO's form ID without its load-order byte, 8 hex digits.
- `<response>`: the response number (TRDT), from 1. One file per response of the INFO.
- The game's voices are Ogg Vorbis, mono, 24,000 a second (all 300 checked). The .lip has the same name.

In FOLab: the files go in `projects/<mod> assets/sound/voice/<plugin>/...`, and from there the way every other
asset goes (Save copies them to the build, install / MO2 / nv-rs get them with the plugin). The line's TRDT stays as it
is; the words in NAM1 are what's spoken and what's subtitled.

## Part 1: lip files (done, proven)

`app/lipwrite.py` reads and writes .lip files and makes one from timed speech sounds.

- Format: a 12-byte header (1, size + 16, packed flag), then zero runs packed (a 0 and a count). Inside: number of
  frames, a starting frame (how far back the face starts easing in; the game's files put it about 4 frames before the
  first sound), and per frame 16 mouth shapes (Aah, BigAah, BMP, ChJSh, DST, Eee,
  Eh, FV, I, K, N, Oh, OohQ, R, Th, W) and 17 face movements (blinks, brows, looks, squints, head turns). 30 frames a
  second.
- Proof: every .lip in the game and its DLC (see the result line at the end of this file) read and written back
  byte for byte. Run `py -3 app/lipwrite.py` to recheck.
- `from_timeline([(sound, start, end), ...])` turns speech sounds (ARPAbet, or IPA as synthesizers speak) into mouth
  shapes, each rising and falling into the next. Blinks and head movement can be added later (the game's own files have
  them; the mouth is what matters first).
- nv-rs: its port has the game's .lip reading, unpacking and playing (`lipsynchanim.rs`, `run_004d5930.rs`), so it
  should move faces as the original does. Not yet seen working there: the test line will show it.

Human voices (later): a recording needs its sounds lined up to the audio. The way to do it is a forced aligner
given the words (Montreal Forced Aligner, MIT licence, gives ARPAbet with times), its output straight into
`from_timeline`. Not built now.

## Part 2: synthesized voices

### Engine: Kokoro (recommended)

- Kokoro-82M, weights under Apache 2.0, 54 voices in 8 languages (about 20 American and British English). No voice is
  a clone of a named person; the training data was mixed narration, some public datasets and some audio from
  commercial speech services. Fine for a released mod under its licence. We say in the mod's credits that the voices are
  Kokoro's.
- It speaks at 24,000 a second, mono: exactly the game's own voices.
- It works out how long each sound lasts before it speaks it (its duration output), so the lip file comes from the
  same numbers as the voice. No guessing from the audio.
- Turning text into sounds: Kokoro's own phonemizer (misaki) with espeak-ng for words it doesn't know. espeak-ng is
  GPL, but it only runs on the developer's machine; its output (the audio) isn't covered.

Not Piper: each Piper voice has its own licence and dataset; several English ones come from datasets meant for
research only, and Piper itself is now GPL. Usable voice by voice, but Kokoro is cleaner.

Not xVASynth or any voice cloned from the game's actors, for anything released.

### Where it runs: a build step, not in FOLab.exe (for now)

Kokoro needs onnxruntime (about 50 MB) and numpy; Ogg encoding needs soundfile (libsndfile). FOLab.exe's own
Python carries none of them. So, as with `garmentprint`, `app/voicegen.py` runs from the developer's Python:
`py -3 app/voicegen.py <mod> [character]`. Once it proves itself, the packages can go into FOLab.exe's Python
(it would grow by roughly 70 MB plus the user's model).

FOLab downloads nothing. The user downloads by hand, as with xNVSE:
- `kokoro-v1.0.onnx` (about 310 MB) and `voices-v1.0.bin` (about 27 MB) from kokoro-onnx's release page.
FOLab finds them in Downloads and copies them to `models/kokoro/` under its home.

### Voices per character

Kept with the mod, in `project.voices` (in Undo like other settings):

    {"by_npc":   {"<NPC key>": {"voice": "am_michael", "speed": 0.95, "pitch": 0}},
     "by_type":  {"<voice type key>": {...}}}

An NPC's own setting wins, then its voice type's, then a default by the voice type's sex. Pitch is a small shift done
after speaking (Kokoro has no pitch control of its own). Two characters sharing a voice type share its folder, so
characters that should sound different need voice types of their own; the Voice panel offers to make one.

### In the dialogue editor (after the test line)

- "Voice this line": speaks the line's words with its speaker's voice, writes the .ogg and .lip, plays it back.
- "Voice every line for this character".
- A line whose words change after voicing is marked out of date.
- Lines with no file stay silent, as now.

## Built so far (20 Nov 2026, after the user's okay)

- `app/voicegen.py`: Kokoro speaks a line with its sound timings, the .lip is made from those timings, the .ogg (Vorbis,
  mono, 24 kHz, every line to the same loudness) and .lip written at `voice_path`. Pitch in semitones (spoken slower,
  played faster). Run from the developer's Python: kokoro-onnx 0.6.1, onnxruntime 1.32, soundfile 0.14 installed there.
- The model: kokoro-onnx's **model-files-v1.1** release's `kokoro-v1.0.onnx` (325,505,369 bytes) reports durations;
  the older model-files-v1.0 one of the same name does not. `find_model` refuses one without them.
- The naming rule checked on the game: worked out for every FalloutNV.esm line, it names 28,723 of the 28,808 voice files
  the game ships; the rest are recordings of lines the game dropped (64) or later moved or cut short (21)
  (`tests/test_voicegen.py`).
- The test plugin: `D:\FOLab-voice\home\build\FOLab Voice Test.esp` and its assets.

## The test line

**Heard in nv-rs, 20 Nov 2026:** the user heard Voice Tester's Kokoro greeting at Waikiki's start and saw his mouth
move. Not yet tried in the original game.

A scratch plugin on D: (not Waikiki), one NPC with a voice type of its own and one greeting, voiced and lip-synced,
put into nv-rs and MO2 for the user to hear and watch. Then the beachcomber quest's lines, agreed with that session
first.

## Needs the user's okay

1. Kokoro as the engine.
2. Downloading for the developer's Python: onnxruntime, kokoro-onnx, soundfile (pip), and the two model files (about
   340 MB, which the user can download instead).
3. The voices kept as above.

## Result of the lip proof

20 Nov 2026, `py -3 app/lipwrite.py`:

    DeadMoney - Main.bsa: 2558, Fallout - Voices1.bsa: 52581, HonestHearts - Main.bsa: 2263,
    LonesomeRoad - Main.bsa: 1123, OldWorldBlues - Main.bsa: 2177
    60702 lip files, 0 differ

`tests/test_lipwrite.py` checks a sample of them and a lip made from timed sounds.

## In FOLab (20 Nov 2026, the user's choices: inside FOLab.exe, no GPL)

- The dialogue editor's line has a Voice part: the speaker's voice (28 English Kokoro voices), speed, pitch, "Hear this
  voice", "Use it for" the character, "Voice this line", "Voice every line for" them, each response's state (voiced, words
  changed, not voiced) and Play.
- No GPL anywhere in FOLab: kokoro-onnx loads espeak-ng and phonemizer (GPL), so FOLab runs Kokoro itself and turns words
  into sounds with its own `g2p.py` (the CMU Pronouncing Dictionary, BSD-style; Hawaiian spelling; English spelling rules for
  the rest). Unusual words may come out oddly: tell me which.
- FOLab.exe's Python carries numpy, onnxruntime and soundfile (about 45 MB in the zip). The model is still the user's
  download, found in Downloads.
