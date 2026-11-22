# Radio chatter: talk between the songs

Plan and prototype, 21 Nov 2026. Nothing here is in Waikiki or in FOLab.exe yet. The bulletins below are **drafts for
the user to approve**. They say nothing the mod's quests don't already say.

## What the user gets

A station of the mod's own plays a few songs, then says something, then plays a few more. What it says is one of its
talk lines, picked at random from the ones that fit right now:

- **Always-true lines**, such as the station's name, which can be said any time.
- **Bulletins** that wait until the player has done something: reached a stage of a quest, finished a quest, found a
  place on the map, or killed someone. Each bulletin can be limited to a few airings, so old news stops.

Both stations talk (the user, 21 Nov 2026: "narration for both"):
- **Haixin Dongtai talks in Mandarin**, as the user said it should.
- **Radio Atoll talks in English.**

English lines are voiced with Chatterbox where it's installed, otherwise Kokoro. Mandarin lines are voiced with
Kokoro's Chinese voices. Each line's .lip is made the same way as for the dialogue lines.

## How the game does it

Read from Radio New Vegas's own records.

- Mr. New Vegas's lines are chained topics. A greeting leads to a news intro, then a story, then a sign-off, then a
  song intro, then songs. The game moves from one to the next through each line's choices, and a few quest variables
  decide which branch is open. Three songs later the chain runs dry and the station starts again with a greeting.
- **A story is a random line whose conditions hold.** Those conditions are what has happened: a quest completed
  (145 of the game's radio lines ask this), someone dead (79), or the story globals that quest scripts set. That is
  why the news follows the player.
- A spoken radio line names no sound. The game finds its voice file by name, as for any dialogue line:
  `sound\voice\<plugin>\<station's voice type>\<quest>_<topic>_<line id>_<n>.ogg`, with a .lip beside it.

## How FOLab does it (radiotalk.py)

FOLab's stations keep every song as a line in the game's RadioHello topic, picked at random, never one of the last
three. Talk goes into the same topic, so nothing about how songs are picked changes:

- The station's script gains one counter: songs played since it last talked.
- Every song adds one to that counter. Songs are held back once it reaches the station's *every* (3 by default).
- Talk lines wait for exactly that moment and set the counter back to 0.
- A bulletin limited to a few airings gets a counter of its own.

The bulletin conditions are written byte for byte as the game writes its own: quest completed, map marker found (run
on the marker, as the game's 28 are) and someone dead. The tests check this.

The station must always have something to say, or it goes quiet when talk is due and there's no news.
`radiotalk.check` warns when every talk line waits on something.

## Mandarin (g2pzh.py)

The game's fonts have no Chinese characters and no tone marks: they are cp1252. So a Mandarin line is written in
pinyin, and three things are kept from it:

- **On screen** (the subtitle, NAM1): the pinyin without tones, such as "Zhe li shi Haixin Dongtai."
- **For the voice** (the response's notes, NAM2, which the game never shows): the pinyin with tone numbers, such as
  "zh:Zhe4 li3 shi4 Hai3xin1 Dong4tai4."
- **For the user** (the response's edits, NAM3, also never shown): the English.

`g2pzh.py` is FOLab's own pinyin-to-sounds step. It writes Mandarin in the sound letters Kokoro's Chinese voices were
trained on, following the rules the Kokoro project's own library uses. It needs no dictionary, because the line is
already pinyin. The tests check it against those rules' own examples (ni hao, shi, zi, ri, chi, zhong, yu, xue, jiu,
gui, lun, jun...). Every sound it gives is one Kokoro has. A line that isn't pinyin is refused.

Kokoro's Chinese voices:
- women: zf_xiaobei, zf_xiaoni, zf_xiaoxiao, zf_xiaoyi;
- men: zm_yunjian, zm_yunxi, zm_yunxia, zm_yunyang.

FOLab's tune widening is not applied to Mandarin, because in Mandarin the pitch is the tones.

Chatterbox's multilingual model would also speak Mandarin, and its code is in the user's Chatterbox folder. Its model
files are not: they would have to be downloaded, which FOLab never does. The user could fetch them, as with Kokoro.

The lips use the nearest English mouth shape for each Mandarin sound (zh, j and q as "ch"; sh and x as "sh"; z and c as
"s"; ü as "oo").

Tests: `tests/test_radiotalk.py` (29 checks) covers:
- the gate on every song;
- the script's variables keeping their numbers;
- the written plugin, read back;
- the voice file paths;
- adding songs later;
- taking the last talk line off, which removes the gate;
- Undo, and removing a station;
- pinyin into Kokoro's sounds, a Mandarin line's three texts, and English given as pinyin refused.

`tests/test_radio.py` still passes unchanged.

## The first drafts, set aside (22 Nov 2026)

The user's verdict on the first drafts: the lines were "blunt and generic", and short clips between songs would break
immersion. Radio Atoll's voice sounded "like a generic female assistant at a kiosk", and Haixin Dongtai's "way too
artificial and clean". Mr. New Vegas works because:
- he is a character;
- a break is a short segment (an opening, a story told with colour, back to the music), not a line;
- there is a lot of it, so it rarely repeats.

So the stations get hosts and whole breaks.

## Radio Atoll's host

The user, 22 Nov 2026: "an eternally tipsy male, middle aged, he's got the sound of sea salt and cigar smoke in his
lungs. his idea of heaven is playing the same radio songs all day for a sleepy beach. voice is smooth and sultry like a
bourbon."

He has no name yet. That is the user's to give, so the drafts never name him.

**A break** is three parts, chained as Radio New Vegas chains its own:
- an opening (always one can be said);
- news, if there is any the player has earned;
- back to the records.

Each part is picked at random from its own list, so breaks rarely come out the same. In the game this is a line in
RadioHello whose choices lead to a news topic of the station's own and then a closing topic. The game takes the first
of a line's choices that has a line that holds, as Radio New Vegas's stories choose a transition or a sign-off.

All drafts below wait for the user's yes. The facts are the quests' own; the colour round them is his manner, not new
lore.

**Openings** (any time):
- "Mm. Still here, still pouring. This is Radio Atoll, and if you can hear me, the beach hasn't swallowed either of us yet."
- "Evening, sleepyheads. Same songs as yesterday, same as tomorrow. That's not a complaint. That's a promise."
- "Radio Atoll. The tide's out, the glass is full, and I'm in no hurry. Neither should you be."
- "You know what I love about this island? Nothing changes. Sun comes up, sun goes down, and I play the same records in between."

**News** (each waits for what the player has done; each aired a few times, then dropped):
- *What the Sea Brought In, stage 20:* "Word from down the coast. Seems the sea coughed somebody up the other night.
  Half drowned, the way I hear it. The beachcomber pulled them out of the surf like a lost bottle, and kept them. The
  sea always gives something back, friends. Usually it's just my empties."
- *Stage 30:* "That stranger the tide brought in? I hear they've taken the coast road, out toward Kuliouou. Brave, or
  foolish. Out here it's usually both. Keep your head down, stranger. And keep the radio on."
- *The Doctor's Stock done:* "Good news, for once. The doctor's supplies made it back off the coast road. Somebody
  carried them the whole way. Now that's a person I'd pour a drink for. Not from the good bottle. But a drink."
- *Through Makapu'u Gate done:* "Somebody walked the settlers' road the whole way out. Gate after gate, all the way to
  that ship and back. On foot. Sober, I'd wager. Can't say I understand it. But I admire it."
- *Kuliouou found:* "Fires burning at Kuliouou again tonight. Could be cooking. Could be something else. I don't go and
  look, and I'd recommend the same."

**Back to the records:**
- "Alright. Enough of me. Here's one you've heard before, and you'll hear again."
- "Pour yourself something. This next one's slow."
- "Back to the records. Same as always. Wouldn't have it any other way."
- "Now hush. Here comes the good part."

**His voice:** three versions are on `D:\FOLab-radio-chatter\listen3.html`, each reading the same break:
- deep and dark;
- deep, a little British;
- rough and low.

Each is played twice, as made and on the radio (`radiofx.air`: an old valve set's band, hiss and crackle). They are
made with Chatterbox at a relaxed setting, copying a slow, low reading of a few sentences in his manner.

## Haixin Dongtai

Who speaks for the Huáng on air, and how, is the user's to say. Their breaks will be written in English first for the
user's yes, then put into Mandarin. The old Mandarin drafts below only show that Mandarin works; their words are set
aside with the rest. Voices to choose from, on the radio, are on the same page.

### The first drafts (set aside)

They use only what the quests themselves say, with no new names or history. Each "waits for" item is a condition the
game can check.

Each "waits for" item is a condition the game can check.

**Haixin Dongtai (Mandarin).** The English column is only for the user; the game shows the plain pinyin.

| Pinyin (what is said) | English | Waits for | Aired at most |
|---|---|---|---|
| Zhè lǐ shì Hǎixīn Dòngtài. Yèlǐ yǒu yīnyuè, yǒu xiāoxi jiù gàosu dàjiā. | This is Haixin Dongtai. Music through the night; when there is news, we tell everyone. | nothing (the always line) | any number |
| Hǎishàng lái le yí ge mòshēngrén. Jiǎn hǎiwù de rén shōuliú le tā. | A stranger came in from the sea. The beachcomber took them in. | What the Sea Brought In, stage 20 | 3 |
| Nàge cóng hǎishàng lái de mòshēngrén, yánzhe hǎi'àn de lù qù le Kùlì'ōu'ōu. | The stranger from the sea has gone along the coast road to Kuliouou. | What the Sea Brought In, stage 30 | 3 |
| Yīshēng de yàopǐn cóng hǎi'àn lù shang sòng huílái le. | The doctor's supplies were brought back from the coast road. | The Doctor's Stock done | 2 |
| Yǒu rén zǒu wán le kāikěnzhě de guānkǒu zhī lù, dào chuán biān yòu huílái le. | Someone walked the settlers' road of gates to the ship and came back. | Through Makapu'u Gate done | 2 |
| Jīnwǎn Kùlì'ōu'ōu yòu diǎn qǐ le huǒ. | Tonight the fires are lit at Kuliouou again. | Kuliouou's map marker found | 2 |

Kuliouou is spoken as the sounds Kù-lì-ōu-ōu, since a Chinese station would say it in its own sounds. "Settlers"
(kāikěnzhě) is a plain word, not a name.

**Radio Atoll (English).**

| Station says | Waits for | Aired at most |
|---|---|---|
| "Radio Atoll. Music through the night, and the news when there is news." | nothing (the always line) | any number |
| "A stranger came in with the tide, and the beachcomber took them in." | What the Sea Brought In, stage 20 (lockbox brought to the beachcomber) | 3 |
| "The stranger from the sea has gone up the coast road to Kuliouou." | What the Sea Brought In, stage 30 | 3 |
| "The doctor's supplies came back from the coast road. Someone carried them all the way." | The Doctor's Stock done | 2 |
| "Somebody walked the settlers' road of gates to the ship and back." | Through Makapu'u Gate done | 2 |
| "There are fires at Kuliouou again tonight." | Kuliouou's map marker found | 2 |

The two stations say the same news for now. Each could have its own slant once the user says what each side would
care about.

## Questions for the user before anything goes into Waikiki

Settled 21 Nov 2026: Haixin Dongtai speaks Mandarin, and both stations talk.

Still open:
1. **The words.** Yes to these drafts, or changes?
2. **Whose voice on each?** The rehearsal used a Kokoro Chinese woman's voice (zf_xiaoxiao) for Haixin Dongtai and a
   woman's blend through Chatterbox for Radio Atoll. Any voice can be chosen, and it is kept per station.
3. ~~How often?~~ Settled 22 Nov 2026: talk every 3 songs.

## Rehearsal on a copy

`D:\FOLab-radio-chatter\` holds a copy of Waikiki's mod file and its own plugin, run with FOLAB_NO_GAME_WRITES:
- `rehearse.py` puts the six drafts on the copy's Haixin Dongtai (4 songs, heard around a spot) and voices them;
- `rehearse.log` is the output.

Results:
- All six went on with no warning.
- All six were voiced with Chatterbox in the blend `am_onyx*0.7+bm_george*0.3`, 2.4 to 5.8 seconds each. That took
  12 minutes on this PC, including loading.
- The .ogg and .lip files are in `home\projects\Waikiki assets\sound\voice\waikiki.esp\maleadult01default\`, named
  `folabradio_radiohello_<line id>_1`. The copy keeps the mod's name, so the folder is "Waikiki assets", but it is on D:.

Second rehearsal (`rehearse2.py`, `rehearse2.log`):
- Haixin Dongtai now has the six Mandarin drafts, voiced by Kokoro's zf_xiaoxiao: 8 files, 2.8 to 5.7 seconds, in 33
  seconds.
- Radio Atoll has the six English drafts, voiced by Chatterbox with af_heart*0.6+bf_emma*0.4, in 12.5 minutes.
- Neither station gave a warning. The files are in the same folder as the first rehearsal's. To hear all twelve:
  `D:\FOLab-radio-chatter\listen.html` (opens in Edge; each line with what it waits for). Nobody has listened to
  them yet.

The user's Waikiki, its stations and its voices were not touched.

## Not proven without the game

- That the game picks a talk line when songs are held back, rather than stopping the station. This is the main risk.
  The fall-back, if it does stop: put talk in a topic of its own that the songs choose into, as Radio New Vegas does.
- That talk lines and bulletins mixed at random give the news often enough: the game picks evenly among the lines that
  hold.
- That a station's voice files play from the radio. Radio New Vegas's do; FOLab's dialogue voices have been heard in
  nv-rs, but not yet in the original game.
- Map marker found as a condition on a radio line. The game uses it 28 times, never on the radio.

## Still to do once the user says yes

- A Talk part on the Radio page: write a line, pick what it waits for, Voice it.
- Routes in `radio.post`.
- Then into FOLab.exe, and onto Waikiki's station only on the user's word.
