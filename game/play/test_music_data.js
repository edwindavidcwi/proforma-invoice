// Sanity-check the captured music loops (vendor/music_data.js): every track
// must gunzip to exactly `frames` bytes of REAL audio (not silence / not a
// failed capture stuck near the 128 mid-rail), and the loop lengths must be
// sane. Catches a broken render before it ships.
//
// Run:  node test_music_data.js
const fs = require("fs"), path = require("path"), zlib = require("zlib"), vm = require("vm");

const DATA_JS = path.join(__dirname, "vendor", "music_data.js");
let failures = 0;
const check = (name, cond, detail) => {
  console.log(`${cond ? "PASS" : "FAIL"}  ${name}${detail ? "  (" + detail + ")" : ""}`);
  if (!cond) failures++;
};

const sandbox = { window: {} };
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(DATA_JS, "utf8"), sandbox);
const DATA = sandbox.window.__MUSIC_DATA;

check("music_data.js exposes window.__MUSIC_DATA", !!DATA);
check("sample rate is sane", DATA.rate >= 8000 && DATA.rate <= 48000, "rate=" + DATA.rate);

const EXPECT = ["town", "route", "centre", "cave", "wild", "trainer", "boss", "rival", "victory"];
check("all expected tracks present", EXPECT.every((t) => DATA.tracks[t]),
      "got " + Object.keys(DATA.tracks).join(","));

for (const [name, t] of Object.entries(DATA.tracks)) {
  const raw = Buffer.from(t.b64, "base64");
  let pcm;
  try { pcm = zlib.gunzipSync(raw); } catch (e) { check(name + ": gunzips", false, e.message); continue; }
  check(`${name}: gunzips to declared frame count`, pcm.length === t.frames,
        `${pcm.length} vs ${t.frames}`);
  const secs = t.frames / DATA.rate;
  check(`${name}: loop length is sane`, secs >= 1.0 && secs <= 35.0, secs.toFixed(2) + "s");

  // Real audio: meaningful spread around the 128 mid-rail and decent peak level.
  let min = 255, max = 0, sum = 0;
  for (let i = 0; i < pcm.length; i++) { const v = pcm[i]; if (v < min) min = v; if (v > max) max = v; sum += v; }
  const mean = sum / pcm.length;
  let varsum = 0;
  for (let i = 0; i < pcm.length; i++) { const d = pcm[i] - mean; varsum += d * d; }
  const std = Math.sqrt(varsum / pcm.length);
  check(`${name}: not silent / not a failed capture`, std > 6, "std=" + std.toFixed(1));
  check(`${name}: has real dynamic range`, (max - min) > 60, "range=" + (max - min));
}

console.log(`\n${failures === 0 ? "ALL MUSIC-DATA CHECKS PASSED" : failures + " CHECK(S) FAILED"}`);
process.exit(failures === 0 ? 0 : 1);
