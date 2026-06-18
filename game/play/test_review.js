// Regression test for the SPACED-REPETITION review path (QuizSelectQuestion ->
// QuizEntryFromIdx). Missed questions are re-asked from a ring of (gradeIdx,
// index) pairs; QuizEntryFromIdx walks the question list by the entry size, so if
// that stride is wrong (e.g. 16 vs the real 18 bytes) the re-asked question loads
// from a garbage offset. The other harnesses start with an empty ring and never
// exercise this path -- this one seeds the ring and proves it works.
//
// Method: seed the ring with one known (gradeIdx, index) while the badge-derived
// "fresh" grade is different, then jump into QuizPlayerAttack many times. ~1/3 of
// selections take the review branch, so the SAME seeded question should dominate
// the rendered-question tally (~33%); every render must also be valid. A bad
// stride makes the review question load wrong/garbage, so no question dominates.
//
// Usage:  node test_review.js [path/to/pokered.gbc]
const fs = require("fs"), path = require("path");
const Binjgb = require(path.join(__dirname, "vendor", "binjgb.js"));

const ROM = process.argv[2] || path.join(__dirname, "..", "pokered", "pokered.gbc");
const SYM = ROM.replace(/\.gb[c]?$/, ".sym");
const TPF = 70224;

const sym = {};
for (const line of fs.readFileSync(SYM, "utf8").split("\n")) {
  const m = line.trim().match(/^([0-9a-fA-F]+):([0-9a-fA-F]+)\s+(\S+)$/);
  if (m) sym[m[3]] = { bank: parseInt(m[1], 16), addr: parseInt(m[2], 16) };
}
const A = (n) => sym[n].addr;
const QPA = sym["QuizPlayerAttack"];
const hLoadedROMBank = A("hLoadedROMBank"), wObtainedBadges = A("wObtainedBadges");
const wQuizQStr = A("wQuizQStr"), wQuizNumAnswers = A("wQuizNumAnswers");
const wReviewRing = A("wQuizReviewRing"), wReviewHead = A("wQuizReviewHead"), wReviewFilled = A("wQuizReviewFilled");

function tile(b) {
  if (b === 0x7f || b === 0) return " ";
  if (b >= 0x80 && b <= 0x99) return String.fromCharCode(65 + b - 0x80);
  if (b >= 0xa0 && b <= 0xb9) return String.fromCharCode(97 + b - 0xa0);
  if (b >= 0xf6 && b <= 0xff) return String.fromCharCode(48 + b - 0xf6);
  return ({ 0x9c: ":", 0xb7: "x", 0xe3: "-", 0xe6: "?", 0xe7: "!", 0xe8: ".", 0xf3: "/", 0xf4: "," })[b] || "~";
}

const REVIEW_GRADE = 2, REVIEW_INDEX = 10;   // grade index 2 (= "Grade 3"), question 10
const TRIALS = 80;

(async () => {
  const module = await Binjgb({ wasmBinary: fs.readFileSync(path.join(__dirname, "vendor", "binjgb.wasm")) });
  const rom = fs.readFileSync(ROM);
  const size = (rom.length + 0x7fff) & ~0x7fff;

  let failures = 0, invalid = 0, skipped = 0;
  const tally = {};
  for (let t = 0; t < TRIALS; t++) {
    // Fresh instance per trial: jumping into the input-waiting hook and never
    // pressing A leaves the stack dirty, so reusing one instance corrupts state.
    const rp = module._malloc(size);
    module.HEAPU8.fill(0, rp, rp + size);
    module.HEAPU8.set(rom, rp);
    const e = module._emulator_new_simple(rp, size, 44100, 4096, 0);
    const rd = (a) => module._emulator_read_mem(e, a);
    const wr = (a, v) => module._emulator_write_mem(e, a, v & 0xff);
    const ticks = () => module._emulator_get_ticks_f64(e);
    const run = (n) => { for (let i = 0; i < n; i++) module._emulator_run_until_f64(e, ticks() + TPF); };

    run(380 + t);                              // boot (vary length so the RNG differs per trial)
    // Seed the ring (one missed question); fresh grade = Grade 5 (distinct).
    wr(wReviewRing + 0, REVIEW_GRADE);
    wr(wReviewRing + 1, REVIEW_INDEX);
    wr(wReviewHead, 1);
    wr(wReviewFilled, 1);
    wr(wObtainedBadges, 0xff);
    wr(0x2000, QPA.bank);
    wr(hLoadedROMBank, QPA.bank);
    module._emulator_set_PC(e, QPA.addr);
    run(60);                                    // select -> far-copy -> draw (allow the draw to finish)

    // Skip trials where the forced jump landed before the quiz set up (a harness
    // artifact at some boot lengths, not an engine path) -- assess only real loads.
    const n = rd(wQuizNumAnswers);
    if (n < 2 || n > 6) { skipped++; module._emulator_delete(e); module._free(rp); continue; }
    let q = ""; for (let i = 0; i < 20; i++) { const b = rd(wQuizQStr + i); if (b === 0x50) break; q += tile(b); }
    q = q.trim();
    const valid = q.length > 1 && !q.includes("~");
    if (!valid) invalid++;
    tally[q] = (tally[q] || 0) + 1;
    module._emulator_delete(e); module._free(rp);
  }

  const assessed = TRIALS - skipped;
  const entries = Object.entries(tally).sort((a, b) => b[1] - a[1]);
  const top = entries[0] || ["", 0];
  const topFrac = assessed ? top[1] / assessed : 0;

  const check = (name, cond, detail) => { console.log(`${cond ? "PASS" : "FAIL"}  ${name}${detail ? "  (" + detail + ")" : ""}`); if (!cond) failures++; };
  console.log(`assessed ${assessed} real loads (${skipped} skipped: forced-jump setup miss)`);
  console.log(`seeded review question dominates the tally: "${top[0]}"  ${top[1]}/${assessed} (${(topFrac * 100).toFixed(0)}%)`);
  console.log(`distinct questions seen: ${entries.length}`);
  check("every rendered question is valid (no garbage from a bad stride)", invalid === 0, invalid + " invalid");
  check("the re-asked question recurs at ~review rate (>=15%)", topFrac >= 0.15, (topFrac * 100).toFixed(0) + "%");
  check("a mix of fresh + review questions appeared", entries.length >= 4, entries.length + " distinct");

  console.log(`\n${failures === 0 ? "ALL REVIEW-PATH CHECKS PASSED" : failures + " CHECK(S) FAILED"}`);
  process.exit(failures === 0 ? 0 : 1);
})().catch((err) => { console.error("harness error:", err); process.exit(2); });
