# Quiz Battle — an educational Pokémon Red for Ethan

This folder builds a real Game Boy Color ROM of **Pokémon Red** that has been
modified so that battles and helpful characters quietly teach school material
(grades 1–5). The goal is that Ethan **learns while he plays** and never feels
like he's doing worksheets.

It is built on top of [`pret/pokered`](https://github.com/pret/pokered), the
open-source disassembly of Pokémon Red. The unmodified source is vendored in
`pokered/` and pinned (see `PINNED_COMMIT.txt`); our educational changes live in
a small set of files listed below.

## What the game does
- **Attacking** asks a question — a correct answer makes the attack hit.
- **Defending** asks a question — a wrong answer lets the enemy land a hard hit.
- **Using an item** (like a Potion) asks a question scaled to your Pokémon's level.
- **Nurse Joy / Professor Oak / helpers** run no-pressure practice and explain
  the answer when you miss. Each town's nurse teaches that area's difficulty.
- It's **forgiving**: a hint and a retry on the first miss, the party is fully
  **healed after every battle**, and there are **no status effects while walking**.
- Difficulty **grows with your badges** (badge count → school grade) and ramps
  up gently inside each grade.

## How to build the ROM
You need **RGBDS v1.0.1** (the exact version in `pokered/.rgbds-version`) and `make`.

```sh
cd game/pokered
make            # produces pokered.gbc
```

If you see a message about an **sha1 mismatch**, that is expected — we changed
the game on purpose, so it no longer matches the original. The ROM still builds.

### Installing RGBDS v1.0.1 (one time)
RGBDS is the Game Boy assembler. If `rgbasm --version` doesn't say `v1.0.1`:

```sh
git clone --depth 1 --branch v1.0.1 https://github.com/gbdev/rgbds
cd rgbds && make && sudo make install
```
(Needs a C/C++ compiler, `make`, `bison`, `flex`, `pkg-config`, and `libpng`.)

## How to play
- **Easiest:** open `pokered/pokered.gbc` in a browser emulator (e.g. EmulatorJS)
  — nothing to install, works on a tablet.
- **On a computer:** use [mGBA](https://mgba.io/).

## For the parent: editing the questions
All questions live in **`pokered/engine/battle/quiz_data.asm`** and the prompts
in **`pokered/data/text/quiz_text.asm`**. You can change numbers, words, and
choices there, then re-run `make`. Settings like your child's name, how many
retries, and whether typing is allowed are in
**`pokered/engine/battle/quiz_config.asm`**.

## Files we changed/added (the mod)
- `engine/battle/quiz.asm` — the shared quiz screen and answer logic *(added)*
- `engine/battle/quiz_data.asm` — the grade 1–5 question banks *(added)*
- `engine/battle/quiz_config.asm` — parent settings *(added)*
- `engine/battle/core.asm` — battle hooks (attack, defense, item, auto-heal) *(edited)*
- `engine/events/poison.asm` — disables overworld status *(edited)*
- `engine/menus/naming_screen.asm` — typed-spelling prompt *(edited)*
- `data/text/quiz_text.asm` — prompts, praise, explanations *(added)*
- `gfx/` — analog-clock tiles for telling-time questions *(added)*

> The rest of `pokered/` is the unmodified upstream game.
