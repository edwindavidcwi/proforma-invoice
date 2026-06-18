// Headless verification of the in-game Learn Hub (LEARNHUB_JS in build_player.py).
// The Learn Hub is the menu panel that carries the Pokemon Red walkthrough plus
// the learning reference sheets (times tables, addition, telling time, etc.).
// We can't see it render in Node, but we CAN run the module against a minimal DOM
// stub and assert on the HTML it generates -- in particular that:
//   * all six tabs are built (Adventure / Times Tables / Math / Real Life / Words / Shapes)
//   * the multiplication grid computes correct products (e.g. 12x12=144, 7x8=56)
//   * the addition grid computes correct sums (e.g. 10+10=20)
//   * a single times-table fact is right
//   * the walkthrough content is present (all 8 gyms, the journey, the HMs)
//   * the "Open Learn Hub" button is added into the menu
//
// Run:  node test_learnhub.js
const fs = require("fs"), path = require("path"), vm = require("vm");

let failures = 0;
function check(name, cond, detail) {
  console.log(`${cond ? "PASS" : "FAIL"}  ${name}${cond || !detail ? "" : "\n      " + detail}`);
  if (!cond) failures++;
}

const py = fs.readFileSync(path.join(__dirname, "build_player.py"), "utf8");
const m = py.match(/LEARNHUB_JS = r"""([\s\S]*?)"""/);
if (!m) { console.error("could not find LEARNHUB_JS in build_player.py"); process.exit(2); }

// ---- minimal DOM stub: enough for build() to run and for us to capture HTML ----
function makeEl() {
  return {
    _html: "", className: "", id: "",
    set innerHTML(v) { this._html = String(v); },
    get innerHTML() { return this._html; },
    firstChild: null,
    appendChild() {}, insertBefore() {},
    addEventListener() {},
    setAttribute() {}, getAttribute() { return null; },
    classList: { add() {}, remove() {}, toggle() {}, contains() { return false; } },
    querySelector() { return makeEl(); },
    querySelectorAll() { return []; },
  };
}

let overlay = null;           // the #pqLearn element we append to body
let menuButtonHTML = "";      // innerHTML of the menu card that hosts the open button
const host = makeEl();
host.insertBefore = function (node) { menuButtonHTML = node._html; };

const sandbox = { console, setInterval: () => 0, clearInterval: () => {}, Math };
sandbox.window = {};
sandbox.document = {
  readyState: "complete",
  body: { appendChild(el) { overlay = el; } },
  createElement() { return makeEl(); },
  getElementById(id) {
    if (id === "pqLearn") return null;     // not built yet -> build proceeds
    if (id === "menu_body") return host;   // so the open-button branch runs
    return makeEl();                        // close button, open button, etc.
  },
  addEventListener() {},
};
vm.createContext(sandbox);
vm.runInContext(m[1], sandbox);

// ---- assertions on the generated Learn Hub HTML ----
check("module exposed window.__learnhub", !!sandbox.window.__learnhub);
check("overlay was appended to the page", overlay !== null);

const H = overlay ? overlay._html : "";

// six tabs
["Adventure", "Times Tables", "Math", "Real Life", "Words", "Shapes"].forEach(function (t) {
  check("tab present: " + t, H.indexOf(t) !== -1);
});

// multiplication grid correctness (data cells carry the product as their text)
check("times 12x12 = 144", H.indexOf('data-r="12" data-c="12">144<') !== -1);
check("times 7x8 = 56",   H.indexOf('data-r="7" data-c="8">56<') !== -1);
check("times 9x6 = 54",   H.indexOf('data-r="9" data-c="6">54<') !== -1);
check("times 1x1 = 1",    H.indexOf('data-r="1" data-c="1">1<') !== -1);
// single-table picker buttons exist (1x .. 12x)
check("times-table picker has 12x button", H.indexOf('data-n="12">12×<') !== -1);

// addition grid correctness (plain <td>) -- 10+10=20 is the bottom-right cell
check("addition grid built (header '+')", H.indexOf("<th>+</th>") !== -1);
check("addition 10+10 = 20 cell", H.indexOf("<td>20</td>") !== -1);
check("doubles 9+9 = 18", H.indexOf("9+9 = <b>18</b>") !== -1);

// walkthrough content: all 8 gym leaders + journey + HMs
["Brock", "Misty", "Lt. Surge", "Erika", "Koga", "Sabrina", "Blaine", "Giovanni"].forEach(function (l) {
  check("gym leader listed: " + l, H.indexOf(l) !== -1);
});
check("journey mentions Pallet Town", H.indexOf("Pallet Town") !== -1);
check("journey mentions becoming Champion", H.indexOf("Champion") !== -1);
check("HM Cut + where to find it", H.indexOf("Cut") !== -1 && H.indexOf("SS Anne") !== -1);
check("type tip Water beats Fire", /Water[\s\S]*beats Fire/.test(H));

// real-life: clock faces drawn as SVG + money + calendar
check("telling-time clock drawn as <svg>", H.indexOf("<svg") !== -1);
check("money: Indian Rupees (paise)", H.indexOf("100 paise") !== -1 && H.indexOf("₹") !== -1);
check("calendar: 12 months", H.indexOf("12 months") !== -1);

// words + shapes
check("opposites: big <-> small", H.indexOf("small") !== -1);
check("plurals: child -> children", H.indexOf("children") !== -1);
check("shapes: triangle has 3 sides", /Triangle[\s\S]*3 sides/.test(H));
check("colours: red + blue = purple", /Red \+ Blue[\s\S]*Purple/.test(H));

// the menu gets an open button
check("menu open button added", menuButtonHTML.indexOf("Open Learn Hub") !== -1);

console.log(failures === 0 ? "\nALL LEARN-HUB CHECKS PASSED" : `\n${failures} CHECK(S) FAILED`);
process.exit(failures === 0 ? 0 : 1);
