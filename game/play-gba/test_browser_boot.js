// Browser-path regression test for the baked single-file player.
//
// Unlike a core-only test, this loads the GENERATED .html exactly as a browser
// would -- every inline <script> block in order -- under a minimal DOM/canvas/
// rAF/clock shim, then drives the emulator and checks that it renders nonzero
// pixels. It exists because a top-level throw in one bundled glue file
// (XAudioJS/swfobject.js) once aborted the whole script and surfaced only as
// "this.initializeVSync is not a function" in real browsers -- invisible to a
// core-only test. Run after building:
//
//     python3 build_player.py --out /tmp/player.html
//     node test_browser_boot.js /tmp/player.html
//
const fs = require("fs"), vm = require("vm");

const htmlPath = process.argv[2] || "/tmp/FireRedQuiz.html";
const html = fs.readFileSync(htmlPath, "utf8");
const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]);
console.log("loading:", htmlPath, "| inline <script> blocks:", scripts.length);

let lastImage = null;
const ctx2d = {
  canvas: { width: 240, height: 160 },
  createImageData: (w, h) => ({ width: w, height: h, data: new Uint8ClampedArray(w * h * 4) }),
  getImageData: (x, y, w, h) => ({ width: w, height: h, data: new Uint8ClampedArray(w * h * 4) }),
  putImageData: function (img) { lastImage = img; },
  drawImage: () => {}, setTransform: () => {}, fillRect: () => {}, clearRect: () => {},
  fillText: () => {}, save: () => {}, restore: () => {}, scale: () => {}, translate: () => {},
};
const makeCanvas = () => ({
  width: 240, height: 160, style: {},
  getContext: () => ctx2d, addEventListener: () => {}, removeEventListener: () => {},
  setAttribute: () => {}, appendChild: () => {},
  getBoundingClientRect: () => ({ left: 0, top: 0, width: 240, height: 160 }),
});
const elements = {};
["emulator_target", "overlay", "overlay_msg", "btnSound", "btnFullscreen"].forEach(id => elements[id] = makeCanvas());

let rafQueue = [], coreCb = null, CLK = 1000;
const win = {};
win.window = win; win.self = win; win.console = console;
win.navigator = { userAgent: "Mozilla/5.0 (Linux; Android) Chrome", vendor: "Google" };
win.location = { href: "file:///x.html" };
win.Date = { now: () => CLK }; win.performance = { now: () => CLK };
win.setInterval = (fn) => { coreCb = fn; return 1; };
win.clearInterval = () => {}; win.setTimeout = () => 0; win.clearTimeout = () => {};
win.requestAnimationFrame = (cb) => { rafQueue.push(cb); return rafQueue.length; };
win.cancelAnimationFrame = () => {};
win.AudioContext = undefined; win.webkitAudioContext = undefined; // exercise muted/fallback path
win.atob = (s) => Buffer.from(s, "base64").toString("binary");
win.Uint8Array = Uint8Array; win.Float32Array = Float32Array; win.Int32Array = Int32Array;
win.document = {
  getElementById: (id) => elements[id] || null,
  getElementsByTagName: () => [makeCanvas()],
  createElement: () => makeCanvas(),
  addEventListener: (ev, cb) => { if (ev === "DOMContentLoaded") win.__domready = cb; },
  removeEventListener: () => {}, body: { appendChild: () => {} }, head: { appendChild: () => {} },
  hidden: false, title: "",
};
win.addEventListener = (ev, cb) => { if (ev === "DOMContentLoaded") win.__domready = cb; };
win.removeEventListener = () => {};
vm.createContext(win);

for (let i = 0; i < scripts.length; i++) {
  try { vm.runInContext(scripts[i], win, { filename: `script[${i}]` }); }
  catch (e) { console.log("FAIL: top-level throw in script[" + i + "] ->", e.message); process.exit(1); }
}
console.log("all script blocks executed with no top-level throw");

if (win.__domready) win.__domready();      // fire DOMContentLoaded -> boot()
let frames = 0;
for (let step = 0; step < 4000; step++) {
  CLK += 17;                                // advance ~1 frame of wall-clock
  try { if (coreCb) coreCb(); } catch (e) { console.log("FAIL: core step threw ->", e.message); process.exit(1); }
  const drain = rafQueue.splice(0);         // bounded: rAFKeepAlive re-queues, so snapshot
  for (const cb of drain) { frames++; try { cb(CLK); } catch (e) { console.log("FAIL: rAF threw ->", e.message); process.exit(1); } }
}
let nz = 0; if (lastImage) for (const v of lastImage.data) if (v !== 0) nz++;
console.log("rAF frames pumped:", frames, "| nonzero pixel bytes in last frame:", nz);
if (nz > 0) { console.log("RESULT: PASS (boots & renders via the real browser script path)"); process.exit(0); }
console.log("RESULT: FAIL (no pixels rendered)"); process.exit(1);
