# Quests and dialogue

*The Quests page: quests in plain fields, conversations you can read and follow, and a board that shows how a quest moves on.*

## Quests

Yours come first in the list; every quest in the game is below them. **＋ New** makes one of your own, and **Make a copy** starts a new one from any quest (its stages and objectives; its dialogue stays with the original). Changing a game quest keeps the change in your mod.

- **Starts with the game**: the quest runs from the start of a new game, and from the next load of an old save. A quest has to be running for its lines to be said.
- **Stages** are how a quest moves on. A line or a script says `SetStage MyQuest 20`, and stage 20's journal text and script happen. Tick **Completes the quest** on the last one.
- **Objectives** are what the Pip-Boy tells you to do. Scripts show and finish them: `SetObjectiveDisplayed MyQuest 10 1`, `SetObjectiveCompleted MyQuest 10 1`. **Map markers** are placed things with an editor ID.
- **Conditions** read in plain words. Click one to change it: who it's about, what to check, against what. **or the next** means this one or the next is enough.

A script is compiled when you save. If it doesn't compile, nothing is saved and the page says which stage and which line.

## Dialogue

Pick a character to read what they say. It starts at the greeting: click a choice to follow it to their answer, as the game would offer it. Each line says who says it and when, which stage it sets, and whether it ends the conversation.

For a character with nothing to say yet, write the greeting and start. After that, click any line:

- **What they say**. Each part becomes a subtitle of its own, so keep them short. A long line written as a new choice is cut at the ends of sentences.
- **Ends the conversation** closes the dialogue after this line.
- **Said only when**. Conditions, as for quests. A line for a character has "The speaker is …" already.
- **The player's choices**. A new choice makes a topic (what the player says) with the first answer in it. You can also link a topic that's already there.
- **Script after it's said**, with buttons for the quest's stages, so a line can set one in a click.
- **＋ Another line here**: something else they might say at this point. The first line whose conditions hold is the one said, so use ↑ and ↓ to put the most particular first.

**Its dialogue** on a quest shows that quest's lines instead of one character's. Lines for "anyone of this voice type" don't show under a character: they aren't written for that person alone.

### Silent lines

You don't need voice files. A line needs only its words; with no voice file, the game shows them for a time that goes by their length, with no lips moving. The player needs dialogue subtitles on (**General subtitles** or **Dialogue subtitles** in the game's own settings), or they will see nothing.

Your character needs a **voice type** even so (the Create page, Characters): the check tells you if one hasn't got it. To add voices later, put files where the game looks: `Data\Sound\Voice\YourMod.esp\voice type\quest_topic_line_1.ogg`, with a `.lip` beside each.

## Board

Your mod's quests, each as a row of stages from left to right. What moves it on is written between them: a line said (and who says it), or a script. A move that skips stages arcs over them. Moves with no stage to wait for are listed under **Any time**.

Stages in red have nothing that sets them; in amber, nothing leads on from them. Click a stage or a move to go to it.

## Check this quest

On any quest. It reads your mod's lines and scripts (the whole game's too, for a game quest), and lists:

- a quest nothing starts
- stages nothing sets, and stages set that don't exist
- objectives nothing shows or completes
- topics nobody can reach, and choices with nothing to answer them
- scripts that don't compile, such as when something they name has gone
- lines with no words, lines anyone could say, lines too long for a subtitle, characters with no voice type

It reads scripts for what they say in so many words, so a stage set some roundabout way (a variable, for example) can show as "nothing sets it". Click a line in the list to go there.
