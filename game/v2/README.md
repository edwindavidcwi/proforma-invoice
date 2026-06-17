# Quiz Quest v2 — engine + audit harness + playable slice

A modern, fully-auditable rebuild of the educational monster-battler (see
`PLAN.md`). This first drop is **Milestone 1 + 2**: the deterministic logic
core, the headless audit harness, and a playable HD-colour vertical slice.

Original world & creatures (Sunny Town; Sprigling / Flarepup / Dripling …) —
faithful in *mechanics* to the classic, our own art/names, personal/family use.

## Play it
Open **`QuizQuest.html`** in any browser (double-click — fully offline).
Walk with **arrows/WASD**, **Z/Enter** = A, **X** = B, **1–6** pick a quiz
answer; on touch, use the on-screen pad. Talk to the Professor (face them, press
A) to get a starter, then walk in the tall grass for a quiz-battle. Answer right
to attack; a wrong answer gives a hint and a retry. Read-aloud is on by default.

## Audit it (the point of the rebuild)
```
npm run audit        # or: node audit/harness.mjs
```
Runs **thousands of full playthroughs** (random + adversarial: "always wrong",
"always right", "always flee") through the *same* logic core the game uses, in a
fraction of a second, and checks:
- no crash, no soft-lock (incl. a struggling child who never answers correctly)
- the slice is always completable (no dead-ends)
- save → load round-trips exactly; corrupt saves never crash (start fresh)
- every quiz answer key is exact; shuffled options still point at the right one
- battles always terminate; runs are fully reproducible from their seed

## Build the single file
```
python3 tools/gen_questions.py   # refresh core/questions.js from the 771-bank
python3 build.py                 # bundle -> QuizQuest.html
```

## Layout
```
core/engine.js     pure rules: world, battle, quiz, save (no DOM) — audited
core/questions.js  the 771-question bank (generated from v1's source of truth)
audit/harness.mjs  headless playthrough auditor (Node)
web/main.js        rendering + input + read-aloud (no rules live here)
build.py           inlines core + web into QuizQuest.html
```
The hard split between **logic** (core) and **rendering** (web) is what lets the
audit prove things about the exact game the child plays.
