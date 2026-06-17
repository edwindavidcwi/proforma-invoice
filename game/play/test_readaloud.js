// Headless verification of the read-aloud TEXT pipeline (READALOUD_JS in
// build_player.py). The speech itself can't be heard in Node, but the parts that
// determine WHAT gets said can be checked:
//   1. decodeAt: reads a '@'-terminated Game Boy string out of (faked) RAM and
//      turns the tile codes back into text.
//   2. speakable: math symbols -> words, '!' dropped, abbreviations expanded.
//   3. buildPrompt: question + choices in the on-screen (rotated) order, gated to
//      real in-battle quiz state.
//
// Run:  node test_readaloud.js
const fs = require("fs"), path = require("path"), vm = require("vm");

let failures = 0;
const check = (name, got, want) => {
  const ok = got === want;
  console.log(`${ok ? "PASS" : "FAIL"}  ${name}${ok ? "" : `\n      got:  ${JSON.stringify(got)}\n      want: ${JSON.stringify(want)}`}`);
  if (!ok) failures++;
};

// Encode JS text into Game Boy tile codes (inverse of the engine's charmap).
function enc(s) {
  const out = [];
  for (const ch of s) {
    let c;
    if (ch === " ") c = 0x7f; else if (ch === ":") c = 0x9c; else if (ch === "-") c = 0xe3;
    else if (ch === "?") c = 0xe6; else if (ch === "!") c = 0xe7; else if (ch === ".") c = 0xe8;
    else if (ch === ",") c = 0xf4; else if (ch === "/") c = 0xf3;
    else if (ch >= "A" && ch <= "Z") c = 0x80 + ch.charCodeAt(0) - 65;
    else if (ch >= "a" && ch <= "z") c = 0xa0 + ch.charCodeAt(0) - 97;
    else if (ch >= "0" && ch <= "9") c = 0xf6 + ch.charCodeAt(0) - 48;
    else throw new Error("unencodable char: " + ch);
    out.push(c);
  }
  out.push(0x50); // '@' terminator
  return out;
}

// Fake RAM + emulator the script reads through window.__emulator.
const RAM = {};
function writeStr(addr, s) { enc(s).forEach((b, i) => { RAM[addr + i] = b; }); }
function writeByte(addr, v) { RAM[addr] = v & 0xff; }
const A_Q = 0xc51a, A_ANS0 = 0xc52e, A_STRIDE = 0x14, A_NUM = 0xdee7, A_ROT = 0xdeea, A_INBATTLE = 0xd057;

// Extract READALOUD_JS from build_player.py and run it in a stubbed browser.
const py = fs.readFileSync(path.join(__dirname, "build_player.py"), "utf8");
const m = py.match(/READALOUD_JS = r"""([\s\S]*?)"""/);
if (!m) { console.error("could not find READALOUD_JS"); process.exit(2); }

const sandbox = {
  setInterval: () => 0, clearInterval: () => {}, console,
  SpeechSynthesisUtterance: function (t) { this.text = t; },
};
sandbox.window = {
  speechSynthesis: { getVoices: () => [], cancel() {}, speak() {}, onvoiceschanged: null },
  __emulator: { module: { _emulator_read_mem: (e, a) => (a in RAM ? RAM[a] : 0) }, e: 1 },
};
sandbox.localStorage = { getItem: () => null, setItem() {} };
sandbox.document = { getElementById: () => null };
vm.createContext(sandbox);
vm.runInContext(m[1], sandbox);
const R = sandbox.window.__readaloud;
if (!R) { console.error("READALOUD_JS did not expose window.__readaloud"); process.exit(2); }

console.log("-- decodeAt (RAM tile codes -> text) --");
writeStr(A_Q, "Cow says?");
check("decode question", R.decodeAt(A_Q), "Cow says?");
writeStr(A_ANS0, "moo");
check("decode answer", R.decodeAt(A_ANS0), "moo");

console.log("\n-- speakable (symbols -> words, no '!', abbreviations) --");
check("multiply", R.speakable("3 x 4?"), "3 times 4?");
check("minus", R.speakable("8 - 3?"), "8 minus 3?");
check("division (spaced)", R.speakable("12 / 4?"), "12 divided by 4?");
check("fraction (tight)", R.speakable("3/4 of 8?"), "3 over 4 of 8?");
check("drops exclamation", R.speakable("CORRECT ANSWER!"), "CORRECT ANSWER");
check("abbrev Sept", R.speakable("Days in Sept?"), "Days in September?");
check("time o'clock", R.speakable("3:00"), "3 oclock");
check("time half past", R.speakable("2:30"), "2 thirty");
check("time quarter to", R.speakable("4:45"), "4 forty five");
check("plain text untouched", R.speakable("Opposite of big?"), "Opposite of big?");

console.log("\n-- buildPrompt (question + choices, gated, rotated order) --");
writeByte(A_INBATTLE, 1); writeByte(A_NUM, 3); writeByte(A_ROT, 0);
writeStr(A_Q, "Cow says?");
writeStr(A_ANS0 + 0 * A_STRIDE, "moo");   // correct (index 0)
writeStr(A_ANS0 + 1 * A_STRIDE, "woof");
writeStr(A_ANS0 + 2 * A_STRIDE, "meow");
check("prompt, rotate 0", R.buildPrompt(), "Cow says? Is it: moo, woof, or meow?");
writeByte(A_ROT, 1);
check("prompt, rotate 1 (display order)", R.buildPrompt(), "Cow says? Is it: woof, meow, or moo?");
writeByte(A_INBATTLE, 0);
check("silent when not in battle", R.buildPrompt(), "");
writeByte(A_INBATTLE, 1); writeByte(A_NUM, 1);
check("silent when <2 answers", R.buildPrompt(), "");

console.log(`\n${failures === 0 ? "ALL READ-ALOUD CHECKS PASSED" : failures + " CHECK(S) FAILED"}`);
process.exit(failures === 0 ? 0 : 1);
