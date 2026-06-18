# Quiz Quest v3 — Plan: the same game, rebuilt to be auditable, editable & limitless

A modern rebuild of the **exact same game we have now** (the Pokémon Red quiz
adventure) — same maps, same look, same feel — but in modern code that we can
**audit deeply, edit easily, fill with unlimited questions/teaching content, and
upgrade element-by-element** (nicer trees, nicer characters) over time.

**Status: PLAN ONLY — awaiting approval. No game code yet.**

---

## 0. The lesson from the last attempt (this is the whole point)

The earlier rebuild's *engine and audit harness worked great* — thousands of
playthroughs in seconds. What made it "really bad" was the **graphics**: I drew
my own simple art and it looked nothing like the game you love.

**So the #1 rule of v3:** it must look **exactly like the game now from day one**.
We achieve that by **reusing the real game's own art and maps** — the tilesets,
sprites, and map layouts already living in `game/pokered/` — instead of drawing
anything new. Faithful by construction. *Then* we can make individual elements
nicer, one at a time, without touching the game logic.

---

## 1. What you asked for, mapped to the design

| Your goal | How v3 delivers it |
|---|---|
| "Exactly as it is" | Loads the **real** pokered maps/tiles/sprites → identical look & feel |
| "Each element identified… make trees & characters better" | An **Asset Registry**: every tile, tree, building, and character is a named, separate, swappable file. Start faithful; replace any one with HD art later — no code change |
| "Audit this game" | Logic split from graphics → a headless harness runs **thousands of full playthroughs/sec**, checking crashes, soft-locks, completability, balance, and content |
| "Edit as we want, simply" | Maps, dialogue, battles, **questions, and teaching content** are plain **data files** (JSON/CSV) a non-coder can edit; an optional in-browser editor |
| "Lots of memory… as many questions/teaching as we want" | No cartridge limit — content is effectively **unlimited** (thousands of questions, rich text, images, read-aloud) |
| "Latest coding language, better way" | **TypeScript** (typed, refactor-safe, testable), runs in any browser + the existing Windows/Android wrappers |

---

## 2. Architecture — four clean layers

The key idea that makes auditing and editing possible: **separate everything**.

```
┌───────────────────────────────────────────────────────────────┐
│ 1) LOGIC CORE  (pure TypeScript, no graphics, deterministic)    │
│    rules: movement, battles, the quiz, items, scripts, save.    │
│    seedable RNG → every playthrough reproducible & auditable.   │
├───────────────────────────────────────────────────────────────┤
│ 2) CONTENT  (plain data: maps, dialogue, creatures, QUESTIONS,  │
│    teaching sheets) — edit a file, the game updates. Unlimited. │
├───────────────────────────────────────────────────────────────┤
│ 3) ASSET REGISTRY  (every visual element = one named file:      │
│    tree.png, player_walk.png, pewter_gym.json …) — swap any     │
│    one to upgrade it. Starts as faithful pokered art.           │
├───────────────────────────────────────────────────────────────┤
│ 4) RENDERER  (draws the state with the current assets; full     │
│    colour, scalable, smooth) — contains NO rules.               │
└───────────────────────────────────────────────────────────────┘
        ▲ same logic core ▲                 ▲ swap assets freely ▲
   ┌─────────────┐                     ┌──────────────────────────┐
   │ AUDIT (Node)│ thousands of runs   │ GAME (browser): renderer +│
   │ headless    │ → crash/softlock/   │ input + audio + read-aloud│
   │             │ completion/balance  │                          │
   └─────────────┘                     └──────────────────────────┘
```

Because the **same logic core** powers both the game and the audit, anything the
audit proves is true of the game your child actually plays.

---

## 3. The Asset Registry — "each element identified, upgrade trees & characters"

This is the part you specifically asked for. Every drawable thing is a separate,
named asset listed in a manifest, e.g.:

```
assets/
  tiles/   grass.png  path.png  tree.png  water.png  ledge.png  flower.png …
  buildings/  pokemon_center.png  gym.png  house.png  mart.png …
  characters/ player.png  nurse.png  professor.png  brock.png … (walk frames)
  creatures/  001.png  004.png  007.png … (the 151)
  ui/  textbox.png  font.png  hp_bar.png …
  manifest.json   ← maps every game element to its file + size + frames
```

- **Day one:** each file is the *faithful* version (extracted from the real
  game) → looks exactly like now.
- **Any time after:** want nicer trees? Replace `tiles/tree.png` with a better
  drawing of the same size. Nicer hero? Replace `characters/player.png`. The
  game picks it up automatically — **no code changes, no risk to logic**.
- Supports **higher-resolution** art too (e.g. 2× tiles) via the manifest, so we
  can gradually go HD element-by-element while keeping the exact layout.

This turns "make the trees and characters better" into a safe, incremental art
task, fully decoupled from the game's rules.

---

## 4. Content & editing — unlimited, simple

- **Questions:** one human-friendly file (or spreadsheet/CSV) — `grade, subject,
  question, correct answer, wrong answers, hint`. Add as many as you like; the
  771 we have import directly. No memory limit.
- **Teaching content (Learn Hub):** simple data + optional images, also
  unlimited.
- **Maps / dialogue / battles:** data files (the faithful ones to start), so the
  world can be tweaked without touching code.
- **Optional in-browser editor** later: a "Parent Studio" page to add questions
  and edit teaching sheets with no files at all.
- A `validate` step (part of the audit) checks every question (one correct
  answer, has a hint, fits on screen) the moment you save.

---

## 5. The audit system (deep, automatic)

`npm run audit` runs the logic core headlessly and checks, over **thousands of
full and adversarial playthroughs** (random, "always wrong", "never heal", …):

- **no crash**, **no soft-lock** (incl. a struggling child who can't answer)
- **always completable** — every gym/badge/gate reachable; no dead-ends
- **save integrity** — save↔load is exact; corrupt saves never crash
- **balance & ease** — difficulty curve, reading load, steps-to-progress
- **content validity** — every question/teaching entry well-formed
- every failure prints a **seed** to reproduce it exactly.

It gates the build (like today's 16-check suite, but for the whole game), and is
fast because there's no emulator — just the rules.

*Honest limit:* a full RPG's total state space is effectively infinite, so
nothing can literally test "every" combination — but this gives near-complete,
reproducible confidence, far beyond what the current cartridge allows.

---

## 6. How it stays "exactly as it is"

- Uses the **real maps, tilesets, sprites** from `game/pokered/` → identical look.
- Renders at the authentic Game-Boy grid by default (optional crisp scaling /
  later HD per the Asset Registry).
- Same controls, same flow, same gyms/story, same kid-friendly rules (hint+retry,
  full heal, no money loss, the 5-question Poké Ball catch, Indian-Rupee money,
  read-aloud, Learn Hub, Report Card).
- v1 (the current game) **stays untouched and playable** the entire time; we only
  switch over once v3 looks and feels right to you.

---

## 7. Milestones (each one playable + audited; faithful look from #1)

1. **Foundation + faithful slice** — logic core, asset registry, the audit
   harness, and **one real town + a quiz-battle rendered with the real art**, so
   you can confirm on day one that it looks exactly like now.
2. **Battle system** — full battles, the quiz integration, items, the 5-question
   catch, read-aloud.
3. **First gym arc** — several real maps, an NPC trainer, a gym + badge + a gate;
   the audit grows to prove that whole arc is completable.
4. **Full world** — all towns/routes/gyms → the league → credits.
5. **Content tools** — the simple question/teaching editor + the Learn Hub.
6. **Polish & art upgrades** — start swapping in nicer trees/characters via the
   Asset Registry; package into the Windows/Android wrappers.

---

## 8. Honest scope & risks

- **This is the largest thing we've planned.** A faithful full remake of the
  whole adventure is a multi-stage, multi-month effort. Milestones keep it
  playable and reviewable throughout, and **milestone 1 proves the look** before
  we commit to the rest.
- **Extracting/loading the real assets** (maps, tiles, sprites) is real work but
  well-understood (the data is all there in `game/pokered/`).
- **Personal/family use**, like the current game: it reuses the open-source
  pokered assets and the Pokémon world for your child — not for sale or public
  release. (If we ever wanted to publish, we'd swap to fully original art/names —
  which the Asset Registry makes easy.)

---

## 9. The one risk worth repeating
The reason to do it this way — real art first, every element swappable — is so
v3 **never** looks "really bad" like the last attempt. We lock in the authentic
look from milestone 1, and only improve from there.

---

## What happens next (after you approve this plan)
I build **Milestone 1**: the engine, the asset registry loading the real art, the
audit harness, and a faithful one-town quiz-battle slice you can open in your
browser and compare side-by-side with the current game. If it looks right, we
continue; if not, we adjust before going further.
