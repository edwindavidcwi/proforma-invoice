// Verifies ADAPTIVE DIFFICULTY: the quiz starts from the badge-derived grade,
// then nudges UP one grade on a strong first-try streak and DOWN one grade after
// repeated stumbles (bounded 1..5). The grade is the difficulty axis, so we can
// confirm the nudge by which Grade{n}Questions ROM bank the loaded question came
// from (mapped via pokered.sym, so it survives bank reassignment).
//
// Usage:  node test_adaptive.js [path/to/pokered.gbc]
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
const bankToGrade = {};
for (let g = 1; g <= 5; g++) bankToGrade[sym["Grade" + g + "Questions"].bank] = g;

const hLoadedROMBank = A("hLoadedROMBank"), wObtainedBadges = A("wObtainedBadges");
const wQuizDataBank = A("wQuizDataBank"), wQuizNumAnswers = A("wQuizNumAnswers");
const wQuizStreak = A("wQuizStreak"), wQuizMissRun = A("wQuizMissRun"), wReviewFilled = A("wQuizReviewFilled");

let failures = 0;
const check = (name, got, want) => {
  const ok = got === want;
  console.log(`${ok ? "PASS" : "FAIL"}  ${name}  (got Grade ${got}, want Grade ${want})`);
  if (!ok) failures++;
};

(async () => {
  const module = await Binjgb({ wasmBinary: fs.readFileSync(path.join(__dirname, "vendor", "binjgb.wasm")) });
  const rom = fs.readFileSync(ROM);
  const size = (rom.length + 0x7fff) & ~0x7fff;

  // Load one fresh question with the given badges/streak/missRun and report its grade.
  function gradeFor(badges, streak, missRun) {
    const rp = module._malloc(size);
    module.HEAPU8.fill(0, rp, rp + size);
    module.HEAPU8.set(rom, rp);
    const e = module._emulator_new_simple(rp, size, 44100, 4096, 0);
    const rd = (a) => module._emulator_read_mem(e, a);
    const wr = (a, v) => module._emulator_write_mem(e, a, v & 0xff);
    const ticks = () => module._emulator_get_ticks_f64(e);
    const run = (n) => { for (let i = 0; i < n; i++) module._emulator_run_until_f64(e, ticks() + TPF); };
    run(400);
    wr(wReviewFilled, 0);                 // empty review ring -> always the fresh (adaptive) path
    wr(wQuizStreak, streak);
    wr(wQuizMissRun, missRun);
    wr(wObtainedBadges, badges);
    wr(0x2000, QPA.bank); wr(hLoadedROMBank, QPA.bank);
    module._emulator_set_PC(e, QPA.addr);
    run(40);
    const ok = rd(wQuizNumAnswers) >= 2;
    const grade = bankToGrade[rd(wQuizDataBank)];
    module._emulator_delete(e); module._free(rp);
    return ok ? grade : -1;
  }

  console.log("grade-bank map:", JSON.stringify(bankToGrade));
  // badges -> base grade: 0x00->1, 0x03->2, 0x0f->3, 0x3f->4, 0xff->5
  check("base grade, no streak/struggle", gradeFor(0x03, 0, 0), 2);
  check("hot streak reaches up a grade", gradeFor(0x03, 5, 0), 3);
  check("struggling eases down a grade", gradeFor(0x0f, 0, 4), 2);
  check("streak just under threshold stays put", gradeFor(0x03, 3, 0), 2);
  check("struggle just under threshold stays put", gradeFor(0x0f, 0, 2), 3);
  check("hot streak clamps at Grade 5", gradeFor(0xff, 8, 0), 5);
  check("struggling clamps at Grade 1", gradeFor(0x00, 0, 6), 1);

  console.log(`\n${failures === 0 ? "ALL ADAPTIVE-DIFFICULTY CHECKS PASSED" : failures + " CHECK(S) FAILED"}`);
  process.exit(failures === 0 ? 0 : 1);
})().catch((err) => { console.error("harness error:", err); process.exit(2); });
