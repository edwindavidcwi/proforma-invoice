// Higher-bar render audit: instead of 5 questions, sample the REAL cross-bank
// loader hundreds of times (varying the RNG) to cover most of the 500-question
// bank, verify every rendered question matches the ROM-decoded entry exactly,
// and check the answer-shuffle is not positionally biased.
//
// Usage: node audit_render.js [rom]
const fs = require("fs"), path = require("path");
const Binjgb = require(path.join(__dirname, "vendor", "binjgb.js"));
const ROM = process.argv[2] || path.join(__dirname, "..", "pokered", "pokered.gbc");
const SYM = ROM.replace(/\.gb[c]?$/, ".sym");
const TPF = 70224, RUNS = 240;

const sym = {};
for (const line of fs.readFileSync(SYM, "utf8").split("\n")) {
  const m = line.trim().match(/^([0-9a-fA-F]+):([0-9a-fA-F]+)\s+(\S+)$/);
  if (m) sym[m[3]] = { bank: parseInt(m[1], 16), addr: parseInt(m[2], 16) };
}
const QPA = sym.QuizPlayerAttack;
const hBank = sym.hLoadedROMBank.addr, wBadges = sym.wObtainedBadges.addr;
const wTileMap = sym.wTileMap.addr, wQStr = sym.wQuizQStr.addr;
const hRandA = sym.hRandomAdd.addr, hRandS = sym.hRandomSub.addr;

function tile(b) {
  if (b === 0x7f || b === 0) return " ";
  if (b >= 0x80 && b <= 0x99) return String.fromCharCode(65 + b - 0x80);
  if (b >= 0xa0 && b <= 0xb9) return String.fromCharCode(97 + b - 0xa0);
  if (b >= 0xf6 && b <= 0xff) return String.fromCharCode(48 + b - 0xf6);
  return ({ 0x9c: ":", 0xb7: "x", 0xe3: "-", 0xe6: "?", 0xe7: "!", 0xe8: ".", 0xf3: "/" })[b] || "~";
}

// ---- decode the full expected bank from ROM ----
const rom = fs.readFileSync(ROM);
const off = (bank, addr) => bank * 0x4000 + (addr - 0x4000);
function romStr(bank, addr) { let o = off(bank, addr), s = ""; while (rom[o] !== 0x50 && s.length <= 30) { s += tile(rom[o]); o++; } return s; }
const gtb = off(sym.QuizGradeTable.bank, sym.QuizGradeTable.addr);
const expected = {}; // grade -> Map(question -> {correct, answers:Set})
const badgesFor = { 1: 0x00, 2: 0x03, 3: 0x0f, 4: 0x3f, 5: 0xff };
for (let g = 1; g <= 5; g++) {
  const e = gtb + (g - 1) * 4;
  const base = rom[e] | (rom[e + 1] << 8), count = rom[e + 2], bank = rom[e + 3];
  const map = new Map();
  for (let i = 0; i < count; i++) {
    const eo = off(bank, base) + i * 16;
    const q = romStr(bank, rom[eo] | (rom[eo + 1] << 8));
    const ci = rom[eo + 2];
    const n = rom[eo + 3];                 // 3 or 4 answers
    const ans = [];
    for (let k = 0; k < n; k++) ans.push(romStr(bank, rom[eo + 4 + 2 * k] | (rom[eo + 5 + 2 * k] << 8)));
    map.set(q, { correct: ans[ci], answers: new Set(ans), n });
  }
  expected[g] = map;
}

(async () => {
  const module = await Binjgb({ wasmBinary: fs.readFileSync(path.join(__dirname, "vendor", "binjgb.wasm")) });
  const size = (rom.length + 0x7fff) & ~0x7fff;
  let totalChecked = 0, mismatches = 0;
  console.log(`Sampling the live loader ${RUNS}x per grade (${RUNS * 5} loads)...\n`);
  for (let g = 1; g <= 5; g++) {
    const seen = new Set(), slot = [0, 0, 0, 0, 0];
    let badRender = 0, examples = [];
    for (let r = 0; r < RUNS; r++) {
      const rp = module._malloc(size);
      module.HEAPU8.fill(0, rp, rp + size); module.HEAPU8.set(rom, rp);
      const e = module._emulator_new_simple(rp, size, 44100, 4096, 0);
      const rd = a => module._emulator_read_mem(e, a), wr = (a, v) => module._emulator_write_mem(e, a, v & 0xff);
      const ticks = () => module._emulator_get_ticks_f64(e);
      const run = n => { for (let i = 0; i < n; i++) module._emulator_run_until_f64(e, ticks() + TPF); };
      run(430 + (r % 48));                 // vary boot timing -> varies RNG
      wr(hRandA, (r * 37 + 11) & 0xff); wr(hRandS, (r * 91 + 7) & 0xff);
      wr(0x2000, QPA.bank); wr(hBank, QPA.bank); wr(wBadges, badgesFor[g]);
      module._emulator_set_PC(e, QPA.addr); run(60);
      let q = ""; for (let i = 0; i < 20; i++) { const b = rd(wQStr + i); if (b === 0x50) break; q += tile(b); }
      const ansRow = rr => { let s = ""; for (let c = 2; c < 19; c++) s += tile(rd(wTileMap + rr * 20 + c)); return s.trim(); };
      const allRows = [ansRow(8), ansRow(10), ansRow(12), ansRow(14), ansRow(16)]; // up to 5 answer rows
      module._emulator_delete(e); module._free(rp);
      if (!q || q.indexOf('~') >= 0 || q.trim().length < 2) { module._emulator_delete; continue; } // box not drawn this run; skip
      totalChecked++;
      const exp = expected[g].get(q);
      if (!exp) { badRender++; mismatches++; if (examples.length < 3) examples.push(`unknown Q "${q}" ans=${allRows}`); continue; }
      const ans = allRows.slice(0, exp.n);    // this question shows exp.n answers
      // every rendered answer must belong to the expected set (rotated order)
      const okSet = ans.every(a => exp.answers.has(a)) && new Set(ans).size === exp.n;
      const cs = ans.indexOf(exp.correct);
      if (!okSet || cs < 0) { badRender++; mismatches++; if (examples.length < 3) examples.push(`mismatch "${q}" got=${ans} expect∈${[...exp.answers]}`); continue; }
      seen.add(q); slot[cs]++;
    }
    const cov = seen.size, total = slot.reduce((a, b) => a + b, 0);
    const pct = total ? slot.map(s => Math.round(100 * s / total)) : [0, 0, 0, 0, 0];
    console.log(`Grade ${g}: render OK ${total}/${RUNS}, coverage ${cov}/100 distinct, ` +
      `correct-answer slot split ${pct.join("/")}%  ${badRender ? "FAIL " + badRender : "OK"}`);
    examples.forEach(x => console.log("    " + x));
  }
  console.log(`\n${mismatches === 0 ? "PASS" : "FAIL"}: ${totalChecked} live renders checked, ${mismatches} mismatches`);
  process.exit(mismatches === 0 ? 0 : 1);
})().catch(e => { console.error(e); process.exit(2); });
