// Verifies the parent SUBJECT/GRADE PICKER. The setting lives in battery-backed
// SRAM (sQuizFocus, bank 1 $A000): bits 0-2 = forced grade (0=auto, 1-5), bits
// 3-5 = forced subject (0=any, 1-6 = subjectId+1). The engine reads it when a
// fresh question is picked. We write SRAM the same way the ROM accesses it, drive
// QuizPlayerAttack, and confirm the loaded question's grade bank and subject id.
//
// Usage:  node test_picker.js [path/to/pokered.gbc]
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
const wQuizLastSubject = A("wQuizLastSubject");

let failures = 0;
const check = (name, cond, detail) => { console.log(`${cond ? "PASS" : "FAIL"}  ${name}${detail ? "  (" + detail + ")" : ""}`); if (!cond) failures++; };

// Load one fresh question with the given SRAM focus byte + badges; return {grade, subj}.
function load(module, rom, size, focus, badges, bootExtra) {
  const rp = module._malloc(size);
  module.HEAPU8.fill(0, rp, rp + size);
  module.HEAPU8.set(rom, rp);
  const e = module._emulator_new_simple(rp, size, 44100, 4096, 0);
  const rd = (a) => module._emulator_read_mem(e, a);
  const wr = (a, v) => module._emulator_write_mem(e, a, v & 0xff);
  const ticks = () => module._emulator_get_ticks_f64(e);
  const run = (n) => { for (let i = 0; i < n; i++) module._emulator_run_until_f64(e, ticks() + TPF); };
  run(400 + (bootExtra || 0));
  // Write sQuizFocus the way the ROM accesses it: enable SRAM, advanced mode,
  // RAM bank 1, write $A000, then back to simple/disabled.
  wr(0x0000, 0x0a); wr(0x6000, 0x01); wr(0x4000, 0x01);
  wr(0xa000, 0x5a); wr(0xa001, focus);   // magic + packed value
  wr(0x6000, 0x00); wr(0x0000, 0x00);
  wr(wObtainedBadges, badges);
  wr(0x2000, QPA.bank); wr(hLoadedROMBank, QPA.bank);
  module._emulator_set_PC(e, QPA.addr);
  run(45);
  const ok = rd(wQuizNumAnswers) >= 2;
  const r = { grade: bankToGrade[rd(wQuizDataBank)], subj: rd(wQuizLastSubject), ok: ok };
  module._emulator_delete(e); module._free(rp);
  return r;
}

(async () => {
  const module = await Binjgb({ wasmBinary: fs.readFileSync(path.join(__dirname, "vendor", "binjgb.wasm")) });
  const rom = fs.readFileSync(ROM);
  const size = (rom.length + 0x7fff) & ~0x7fff;

  // 1. focus=0 -> auto: grade from badges (0x0f -> grade 3).
  check("focus auto -> badge grade", load(module, rom, size, 0x00, 0x0f).grade === 3);
  // 2. forced grade 2 overrides badges (0xff would be grade 5).
  check("forced grade 2 overrides badges", load(module, rom, size, 0x02, 0xff).grade === 2);
  // 3. forced grade 5 overrides badges (0x00 would be grade 1).
  check("forced grade 5 overrides badges", load(module, rom, size, 0x05, 0x00).grade === 5);
  // 4. forced subject = Math (id 4 -> nibble 5 -> byte 0x28); every real load must be Math.
  let mathOk = true, mg = [], valid = 0;
  for (let i = 0; i < 8; i++) {
    const r = load(module, rom, size, 0x28, 0xff, i * 7);
    if (!r.ok) continue;                 // skip forced-jump setup misses
    valid++; mg.push(r.subj); if (r.subj !== 4) mathOk = false;
  }
  check("forced subject Math -> always Math (id 4)", mathOk && valid >= 3, "subjects=" + mg.join(",") + " (" + valid + " valid)");
  // 5. forced grade 2 + subject English (id 0 -> nibble 1 -> byte 0x0A).
  const r5 = load(module, rom, size, 0x0a, 0xff);
  check("forced grade 2 + subject English", r5.grade === 2 && r5.subj === 0, `grade ${r5.grade}, subj ${r5.subj}`);

  console.log(`\n${failures === 0 ? "ALL PICKER CHECKS PASSED" : failures + " CHECK(S) FAILED"}`);
  process.exit(failures === 0 ? 0 : 1);
})().catch((err) => { console.error("harness error:", err); process.exit(2); });
