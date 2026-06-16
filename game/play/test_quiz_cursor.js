// Headless verification harness for the Quiz Battle Red build, using binjgb's
// debug API (read/write memory, set PC, run). Two checks:
//
//   1. Cursor alignment: call the REAL PlaceMenuCursor (home bank, always
//      mapped) with the quiz's menu setup and confirm the cursor lands on the
//      same rows the answers are drawn on (9,11,13,15). Clearing
//      BIT_DOUBLE_SPACED_MENU (the fix) gives the 2-row step the answers use;
//      SETTING it (the old code) misaligns onto rows 9,10,11,12.
//   2. Boot stability: the modded ROM boots and the screen advances (no crash).
//
// The cursor checks run in the early intro state (no active menu) so the game's
// own per-frame menu loop can't race with our injected calls.
//
// Run:  node test_quiz_cursor.js [path/to/pokered.gbc]
const fs = require("fs"), path = require("path");
const Binjgb = require("./vendor/binjgb.js");

const ROM = process.argv[2] || path.join(__dirname, "..", "pokered", "pokered.gbc");
const TICKS_PER_FRAME = 70224;

// Read symbol addresses from pokered.sym next to the ROM, so the harness never
// breaks when unrelated code shifts a routine's address (e.g. a new menu item).
const SYM = ROM.replace(/\.gb[c]?$/, ".sym");
const _sym = {}, _bank = {};
for (const line of fs.readFileSync(SYM, "utf8").split("\n")) {
  const m = line.trim().match(/^([0-9a-fA-F]+):([0-9a-fA-F]+)\s+(\S+)$/);
  if (m) { _sym[m[3]] = parseInt(m[2], 16); _bank[m[3]] = parseInt(m[1], 16); }
}
const S = (n) => { if (_sym[n] === undefined) throw new Error("missing symbol " + n); return _sym[n]; };
const BANK = (n) => { if (_bank[n] === undefined) throw new Error("missing symbol " + n); return _bank[n]; };
const PlaceMenuCursor = S("PlaceMenuCursor");
const wTileMap = S("wTileMap"), SCREEN_W = 20;
const wTopMenuItemY = S("wTopMenuItemY"), wTopMenuItemX = S("wTopMenuItemX"), wCurrentMenuItem = S("wCurrentMenuItem");
const wTileBehindCursor = S("wTileBehindCursor"), wMaxMenuItem = S("wMaxMenuItem"), wLastMenuItem = S("wLastMenuItem");
const wMenuCursorLocation = S("wMenuCursorLocation"), hUILayoutFlags = S("hUILayoutFlags");
const BIT_DOUBLE_SPACED_MENU = 1; // bit index 1 -> mask 0x02

let failures = 0;
const check = (name, cond, detail) => {
  console.log(`${cond ? "PASS" : "FAIL"}  ${name}${detail ? "  (" + detail + ")" : ""}`);
  if (!cond) failures++;
};

(async () => {
  const module = await Binjgb({ wasmBinary: fs.readFileSync(path.join(__dirname, "vendor", "binjgb.wasm")) });
  const rom = fs.readFileSync(ROM);
  const size = (rom.length + 0x7fff) & ~0x7fff;
  const romPtr = module._malloc(size);
  module.HEAPU8.fill(0, romPtr, romPtr + size);
  module.HEAPU8.set(rom, romPtr);
  const e = module._emulator_new_simple(romPtr, size, 44100, 4096, 0);
  if (e === 0) throw new Error("emulator_new_simple failed (invalid ROM)");

  const rd = (a) => module._emulator_read_mem(e, a);
  const wr = (a, v) => module._emulator_write_mem(e, a, v & 0xff);
  const getPC = () => module._emulator_get_PC(e);
  const setPC = (a) => module._emulator_set_PC(e, a);
  const ticks = () => module._emulator_get_ticks_f64(e);
  const fbPtr = module._get_frame_buffer_ptr(e), fbSize = module._get_frame_buffer_size(e);
  const fbHash = () => { let h = 2166136261; const b = module.HEAPU8; for (let i = fbPtr; i < fbPtr + fbSize; i += 7) { h = (h ^ b[i]) * 16777619; } return h >>> 0; };
  const runFrames = (n) => { for (let i = 0; i < n; i++) module._emulator_run_until_f64(e, ticks() + TICKS_PER_FRAME); };

  const h0 = fbHash();
  runFrames(150); // reach the intro animation: initialized, but no active menu

  // ---- Check 1: cursor alignment via the real PlaceMenuCursor ----
  const setupMenu = (item, doubleSpacedFlagSet) => {
    wr(wMenuCursorLocation, 0); wr(wMenuCursorLocation + 1, 0); // clear so a stale value can't pass
    wr(wTopMenuItemY, 9); wr(wTopMenuItemX, 1);
    wr(wCurrentMenuItem, item); wr(wLastMenuItem, item);
    wr(wTileBehindCursor, 0x7f); wr(wMaxMenuItem, 3);
    const f = rd(hUILayoutFlags);
    wr(hUILayoutFlags, doubleSpacedFlagSet ? (f | (1 << BIT_DOUBLE_SPACED_MENU)) : (f & ~(1 << BIT_DOUBLE_SPACED_MENU)));
  };
  const callAndReadRow = (item, flagSet) => {
    setupMenu(item, flagSet);
    setPC(PlaceMenuCursor);
    module._emulator_run_until_f64(e, ticks() + 5000); // > enough for the routine
    const loc = rd(wMenuCursorLocation) | (rd(wMenuCursorLocation + 1) << 8);
    return { row: Math.floor((loc - wTileMap) / SCREEN_W), col: (loc - wTileMap) % SCREEN_W };
  };

  console.log("-- flag CLEARED (the fix): answers are drawn on rows 9,11,13,15 --");
  for (let item = 0; item <= 3; item++) {
    const { row, col } = callAndReadRow(item, false);
    check(`answer ${item}: cursor on row ${9 + 2 * item}, col 1`, row === 9 + 2 * item && col === 1, `got row=${row} col=${col}`);
  }

  console.log("\n-- flag SET (the OLD buggy code): cursor steps only 1 row --");
  let mismatchShown = false;
  for (let item = 1; item <= 3; item++) {
    const { row } = callAndReadRow(item, true);
    if (row !== 9 + 2 * item) mismatchShown = true;
    console.log(`   answer ${item}: old code -> row ${row} (answer is on row ${9 + 2 * item}) -> ${row === 9 + 2 * item ? "aligned" : "MISALIGNED"}`);
  }
  check("regression: old (flag-set) code misaligns, confirming the fix is needed", mismatchShown);

  // ---- Check 1b: 2-column setup picks the right cursor column + item count ----
  // QuizSetupColumnCursor reads wQuizNumAnswers + wQuizCol and sets the cursor X
  // (left col -> 1, right col -> 10), top row 9, and the column's item count.
  // leftN = ceil(n/2); rightN = n - leftN.
  console.log("\n-- 2-column answer grid (QuizSetupColumnCursor) --");
  const QuizSetupColumnCursor = S("QuizSetupColumnCursor"), quizBank = BANK("QuizSetupColumnCursor");
  const wQuizNumAnswers = S("wQuizNumAnswers"), wQuizCol = S("wQuizCol"), hLoadedROMBank = S("hLoadedROMBank");
  // The quiz engine lives in a banked ROM section, so map its bank before calling
  // into it. Give the routine a safe place to land: inject a spin loop (jr -2) and
  // point its return address (top of stack) at it, so after `ret` the CPU idles
  // there instead of running garbage that would clobber the vars before we read.
  const SPIN = 0xc6e8;
  const setupCol = (n, col) => {
    wr(0x2000, quizBank); wr(hLoadedROMBank, quizBank);   // map the quiz ROM bank
    wr(SPIN, 0x18); wr(SPIN + 1, 0xfe);                   // jr -2
    const sp = module._emulator_get_SP(e);
    wr(sp, SPIN & 0xff); wr(sp + 1, (SPIN >> 8) & 0xff);
    wr(wQuizNumAnswers, n); wr(wQuizCol, col);
    setPC(QuizSetupColumnCursor);
    module._emulator_run_until_f64(e, ticks() + 600);     // routine runs, then idles in the spin loop
    return { x: rd(wTopMenuItemX), y: rd(wTopMenuItemY), max: rd(wMaxMenuItem) };
  };
  for (const n of [2, 3, 4, 5, 6]) {
    const leftN = (n + 1) >> 1, rightN = n - leftN;
    const L = setupCol(n, 0), R = setupCol(n, 1);
    check(`n=${n}: left column at X=1, Y=9, ${leftN} item(s)`,
          L.x === 1 && L.y === 9 && L.max === leftN - 1, `x=${L.x} y=${L.y} max=${L.max}`);
    check(`n=${n}: right column at X=10, Y=9, ${rightN} item(s)`,
          R.x === 10 && R.y === 9 && R.max === rightN - 1, `x=${R.x} y=${R.y} max=${R.max}`);
  }

  // ---- Check 2: boot stability soak ----
  let aborted = false;
  try { runFrames(1700); } catch (err) { aborted = true; console.log("  abort during run:", err.message || err); }
  check("boot: no crash/abort over ~1850 frames", !aborted);
  check("boot: PC stays in ROM/RAM (not 0x0000)", getPC() !== 0x0000, "PC=0x" + getPC().toString(16));
  check("boot: screen advanced (framebuffer changed)", h0 !== fbHash());

  console.log(`\n${failures === 0 ? "ALL CHECKS PASSED" : failures + " CHECK(S) FAILED"}`);
  process.exit(failures === 0 ? 0 : 1);
})().catch((err) => { console.error("harness error:", err); process.exit(2); });
