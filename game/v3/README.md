# Quiz Quest v3 -- Milestone 1 (faithful slice)

The same game rebuilt as a modern, auditable, editable platform (see PLAN.md).
This first slice is a **walkable Pallet Town drawn from the REAL game's tiles**,
with the quiz loop, plus the headless audit.

## Play
Open **QuizQuest3.html** (double-click, offline). Arrows/WASD walk; Z/Enter = A;
1-4 answer a quiz. Walk in town; a question pops up; answer right to win, a wrong
answer gives a hint + retry. Read-aloud is on.

## Audit (the point of the rebuild)
    npm run audit        # node audit/harness.mjs
Runs thousands of random + adversarial playthroughs through the SAME engine the
game uses, checking: no crash, no soft-lock, quizzes reachable, answer keys
exact, saves round-trip / corrupt saves never crash, reproducible.

## Rebuild
    python3 tools/gen_questions.py   # engine/questions.js (the 771-bank)
    python3 tools/build_pack.py      # pack/pallet.pack.js (real art + map + collision)
    python3 build.py                 # bundle -> QuizQuest3.html

## Layout (the platform)
    engine/   pure rules (no pictures) -- audited
    pack/     a "Game Pack": real map/art/collision as data (swap to make Title 2)
    web/      renderer + input + read-aloud (no rules here)
    audit/    headless playthrough auditor
    tools/    asset + question pipeline
