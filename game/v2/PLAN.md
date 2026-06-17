# Quiz Battle v2 — Design & Architecture Plan

A from-scratch, modern, **fully-auditable** rebuild of the educational
monster-battler for Ethan. Faithful to the classic Game-Boy RPG it's modelled on
(maps, creatures, gyms, progression, battle feel), but written as clean modern
code with **full-colour HD pixel art** and **no Game-Boy hardware limits**.

Status: **PLAN — awaiting approval. No game code written yet.**

---

## 0. Why rebuild (vs. the current ROM mod)

The current game is a mod of a real Game-Boy ROM running in an emulator. That
fought every recent goal: 4 colours, 160×144, 8 KB RAM, tile/charmap text limits,
hand-written assembly, and — critically — **you cannot exhaustively audit a
cycle-accurate hardware emulator**. v2 removes all of that.

| Goal | v1 (ROM in emulator) | v2 (this plan) |
|---|---|---|
| Colour / graphics | 4 shades, tiny tiles | Full-colour HD pixel art, animation |
| Audit "every run in seconds" | impossible (HW emulator) | **thousands of headless playthroughs/sec** |
| Crash / soft-lock / completion proof | manual asm review | automated invariants on every run |
| Memory / size / text limits | severe | effectively none |
| Code quality | GBZ80 assembly | typed, tested, modular |
| Reuse | — | **keeps all 771 questions + Parent Pack** |

---

## 1. Asset & use policy (important, read once)

- We recreate the **game design and mechanics** (maps, creatures, types, moves,
  gyms, story beats, progression curve) — the parts that make it "faithful" and
  that enable deep auditing.
- **All art is newly drawn** HD pixel art and **all audio is newly made or
  omitted** — we do **not** copy sprites, tilesets, or music from the original
  cartridge. (This is also required to get "better graphics".)
- This is a **personal / family** learning tool, exactly like the current ROM
  mod — **not** for sale or public distribution. If we ever wanted to publish it,
  we'd first swap creature/character names and designs to fully original ones.
- The **151 creatures, gyms, and world** are recreated as faithful analogues for
  Ethan's familiarity; names/art are our own renditions, kept private.

---

## 2. Tech stack

- **Language:** TypeScript (typed, refactor-safe, easy to audit).
- **Runtime:** plain web (HTML5 Canvas / WebGL2 via a thin renderer). Runs in any
  browser and inside the **existing Windows (Electron) and Android wrappers** —
  so distribution to Ethan's devices is unchanged.
- **Build:** a single bundler (esbuild/vite) → one self-contained offline file,
  same "double-click to play" experience as today.
- **Tests/audit:** Node-based headless harness (no browser needed) — the logic
  core runs identically in Node and the browser.
- **No external game engine dependency** for the logic (keeps it deterministic &
  auditable); a tiny render layer is the only browser-specific part.

---

## 3. Core architecture — the one idea that makes everything possible

**Hard split between LOGIC and RENDERING.**

```
┌─────────────────────────────────────────────────────────────┐
│  LOGIC CORE  (pure, deterministic, no DOM, no canvas)         │
│   • GameState (immutable-ish snapshot: party, maps, flags,    │
│     inventory, badges, quiz progress, RNG seed)               │
│   • step(state, input) -> { state, events }   ← pure function │
│   • seedable RNG (no Math.random; every run is reproducible)  │
│   • all rules: movement, battle math, types, AI, quiz,        │
│     items, scripts, progression                               │
└───────────────┬───────────────────────────┬─────────────────┘
                │                             │
   ┌────────────▼───────────┐    ┌────────────▼────────────────┐
   │  RENDERER (browser)     │    │  AUDIT HARNESS (Node)        │
   │  draws GameState +      │    │  drives step() with scripted │
   │  plays audio + input    │    │  or random inputs, millions  │
   │  (no rules live here)   │    │  of times, checking invariants│
   └─────────────────────────┘    └──────────────────────────────┘
```

Because the **same pure logic core** powers both the real game and the audit
harness, anything the audit proves is true of the game the child actually plays.

**Determinism rules:** one seedable PRNG threaded through state; no wall-clock or
`Math.random` in logic; every playthrough is identified by `(seed, input
script)` and can be **replayed exactly**. A failing audit run prints its seed →
we reproduce the bug instantly.

---

## 4. The audit system (the headline feature)

A first-class part of the engine from day one, gated in CI. It runs the logic
core with no graphics, so it's astronomically faster than the emulator.

**4.1 What it checks on every simulated run**
- **Crash:** any thrown error / illegal state transition = fail (with seed).
- **Soft-lock:** the player can always make progress; no input leaves the game
  stuck (detected by a watchdog: if N steps pass with no state change and no
  available action, fail).
- **Completion / reachability:** from any reachable state, the credits are still
  reachable (graph search over the progression DAG: items→HMs→gates→gyms→league).
- **Save integrity:** save→load round-trips to an identical state; a truncated or
  garbage save loads safely (never crashes).
- **Balance / difficulty:** badge→grade mapping stays in range; battles are
  winnable at expected levels; the quiz difficulty curve is monotonic-ish.
- **Ease-of-use metrics:** average reading load per screen, steps-to-first-win,
  retries-before-progress, % of actions reachable by a 6-year-old's input set.

**4.2 How it covers "every permutation … in seconds" (honestly)**
- **Exhaustive** where the space is small/bounded: the quiz engine (all 771 Qs ×
  answer orders × right/wrong/retry paths), battle damage math, type chart, menu
  navigation, every map transition, every NPC script branch.
- **Massive randomized (Monte-Carlo)**: tens of thousands of full
  start→champion playthroughs per second with random *and* adversarial inputs
  (e.g. "always answer wrong", "flee everything", "never heal"), each checked by
  the invariants above. Seeds make every run reproducible.
- **Property-based tests** (fast-check style): "for all states, …".
- **Reachability graph**: a model of gates/keys/HMs proving no dead-ends.
- **Honest limit:** a full RPG's *combined* state space is effectively infinite,
  so nothing can literally enumerate "every" state. The above gives
  *near-complete, reproducible* confidence — far beyond what's possible today —
  but I won't claim mathematical totality.

**4.3 Output:** a single `npm run audit` produces a report (pass/fail + metrics +
any failing seeds) and gates the build, exactly like today's 16-check suite, but
covering the *whole* game.

---

## 5. Game systems to build (faithful analogues)

Data-driven so content lives in readable JSON/TS (auditable + parent-editable):

- **World & movement:** tile maps, collision, warps, encounters, day/night opt.
- **Scripts/NPCs:** a small event VM (talk, give item, gate on flag/badge, battle).
- **Creatures:** ~151 entries — stats, types, learnsets, evolutions (our renditions).
- **Battles:** turn engine, the type chart, moves, status, AI, catching — with the
  **quiz layer** integrated (a correct answer powers your move; gentle hint+retry).
- **Items & inventory**, **gyms & badges**, **the league/credits**.
- **Progression:** gates that require HMs/badges (the reachability model mirrors
  this exactly).

## 6. Education layer (ported & upgraded from v1)
- **Reuse the 771-question bank as-is** (it's already clean data) + the generator.
- Grade/subject system, **adaptive difficulty**, **hint+retry**, **read-aloud**
  (now with rich text, not charmap-limited), the **Learn Hub**, the **Report
  Card**, and the parent **Focus** picker.
- All the kid-friendly QoL: full heal after battles, no money loss, no
  dead-ends, can't-get-stuck — now **provable** by the audit, not just coded.

## 7. Milestones (each one playable + fully audited before moving on)
1. **Engine skeleton + audit harness** — logic core, seeded RNG, the headless
   runner, CI gate. (Proves the auditing approach on a tiny map.)
2. **Vertical slice** — 1 town + 1 route, walking, an NPC, one full **quiz-battle**
   with HD art, save/load. Playable in the browser. *(This is the first thing you
   try.)*
3. **Battle system complete** — types, moves, AI, items, catching, the full quiz
   integration + read-aloud.
4. **First gym arc** — several maps, a gym, badge, progression gate.
5. **Full world** — all towns/routes/gyms → league → credits.
6. **Polish** — Learn Hub, Report Card, settings, packaging into the Windows/
   Android wrappers.

## 8. Risks & honest notes
- **Scope:** a full faithful adventure is a large, multi-stage build; milestones
  keep it shippable and reviewable throughout.
- **Art:** HD pixel art for ~151 creatures + tiles is significant; we start with a
  small consistent set for the slice and expand. I'll generate placeholder art
  and we refine the style.
- **"Perfect":** the audit makes it *demonstrably* free of crashes/soft-locks/
  dead-ends within the modelled systems — the strongest guarantee practical for a
  game of this size, and far beyond v1.
- **v1 stays available** the whole time; we only switch Ethan over when v2's slice
  is something you're happy with.

---

## 9. What I need from you to start building
After you approve this plan, milestone 1+2 (engine + audit harness + the playable
vertical slice) is the first deliverable. Open questions to confirm when ready:
creature-naming approach (faithful renditions vs. lightly original), and whether
read-aloud voice should match v1.
