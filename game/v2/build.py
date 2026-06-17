#!/usr/bin/env python3
# Bundles the v2 logic core + browser front-end into ONE self-contained
# QuizQuest.html (double-click to play, fully offline) -- the same delivery
# model as v1. The exact same core/engine.js is what the audit harness runs in
# Node, so what's proven by `npm run audit` is true of this file too.
#
# Zero build tools: the ES modules are concatenated (imports/exports stripped)
# into a single classic <script>, in dependency order.
#   python3 build.py            ->  QuizQuest.html
import os, re

HERE = os.path.dirname(os.path.abspath(__file__))
ORDER = ["core/questions.js", "core/engine.js", "web/main.js"]  # dependency order


def strip_modules(src):
    src = re.sub(r'(?m)^\s*import\b[\s\S]*?;', '', src)          # remove (multi-line) imports
    src = re.sub(r'(?m)^\s*export\s*\{[^}]*\};\s*$', '', src)    # remove `export { ... };`
    src = re.sub(r'(?m)^export\s+', '', src)                     # strip `export ` prefix
    return src


def bundle():
    parts = []
    for rel in ORDER:
        with open(os.path.join(HERE, rel), encoding="utf-8") as f:
            parts.append("/* ===== %s ===== */\n%s" % (rel, strip_modules(f.read())))
    return "(function(){\n" + "\n\n".join(parts) + "\n})();"


CSS = r"""
*{box-sizing:border-box}
body{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;
  background:linear-gradient(160deg,#0e2838,#071620);
  font-family:"Segoe UI Rounded","SF Pro Rounded","Comic Sans MS",system-ui,sans-serif;
  -webkit-user-select:none;user-select:none;color:#26303a}
#qq{width:min(96vw,460px)}
#topbar{display:flex;align-items:center;gap:8px;padding:10px 12px;border-radius:16px 16px 0 0;
  background:linear-gradient(135deg,#4f46e5,#7c3aed);color:#fff}
#topbar .logo{font-weight:800;font-size:18px;text-shadow:0 1px 2px rgba(0,0,0,.2)}
#topbar .grow{flex:1}
#topbar .tb{background:rgba(255,255,255,.22);border:0;color:#fff;border-radius:10px;
  padding:8px 11px;font:700 13px/1 inherit;cursor:pointer}
#topbar .tb.off{opacity:.5;text-decoration:line-through}
#stage{position:relative;background:#0b1418;line-height:0;overflow:hidden}
#cv{display:block;width:100%;height:auto;image-rendering:pixelated;background:#cde4b0}
#overlay{position:absolute;inset:0;display:flex;align-items:flex-end;justify-content:center;
  pointer-events:none;padding:10px}
#overlay .box{pointer-events:auto;width:100%;background:#fffdf8;border-radius:16px;
  padding:13px 15px;box-shadow:0 8px 26px rgba(0,0,0,.45);animation:pop .15s ease}
@keyframes pop{from{transform:translateY(10px);opacity:.6}to{transform:none;opacity:1}}
.box p{margin:0 0 10px;font-size:17px;line-height:1.4;font-weight:700;color:#26303a}
.box p.q{font-size:18px}
.clk{display:inline-block;background:#e0f2f1;color:#0d9488;border-radius:8px;padding:1px 8px;font-size:13px}
.hint{margin:8px 0 0!important;font-size:14px!important;font-weight:600!important;color:#b4690e!important}
.opts{display:flex;flex-wrap:wrap;gap:8px}
.opts.grid{display:grid;grid-template-columns:1fr 1fr}
.opt{flex:1 1 auto;min-height:48px;border:3px solid #e7e0cf;background:#fff;border-radius:13px;
  padding:10px 12px;font:800 16px/1.1 inherit;color:#26303a;cursor:pointer;transition:transform .06s}
.opt:active{transform:scale(.96)}
.opt.ans{border-color:#cdd7e3}
.opt small{display:block;font-size:11px;font-weight:600;color:#7c6f55;margin-top:3px}
.opt.next,.opt.msgbtn{background:linear-gradient(180deg,#5be39a,#16a34a);color:#04261a;border:0}
#pad{display:flex;align-items:center;justify-content:space-between;padding:14px 16px 18px;
  background:#0e2838;border-radius:0 0 16px 16px}
.dpad{position:relative;width:132px;height:132px}
.dpad .d{position:absolute;width:44px;height:44px;border:0;border-radius:10px;background:#33506f;color:#cfe2ee;font-size:16px;cursor:pointer}
.dpad .u{left:44px;top:0}.dpad .dn{left:44px;top:88px}.dpad .l{left:0;top:44px}.dpad .r{left:88px;top:44px}
.dpad .d:active{background:#22405a}
.ab{display:flex;gap:14px}
.rb{width:62px;height:62px;border-radius:50%;border:0;font:800 22px/1 inherit;color:#fff;cursor:pointer;
  background:linear-gradient(180deg,#ff7a59,#e23b3b);box-shadow:0 4px 0 #a52121}
.rb.b{background:linear-gradient(180deg,#7aa0ff,#3b5be2);box-shadow:0 4px 0 #21307f}
.rb:active{transform:translateY(3px);box-shadow:none}
"""

HTML = """<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no, viewport-fit=cover">
<title>Quiz Quest</title><style>%s</style></head><body>
<noscript>Please enable JavaScript to play.</noscript>
<script>
/* last-resort guard: never let a stray error freeze the game */
window.addEventListener('error',function(e){try{console.error('caught',e.error||e.message)}catch(x){}});
window.addEventListener('unhandledrejection',function(e){try{console.error('caught',e.reason)}catch(x){}if(e&&e.preventDefault)e.preventDefault();});
</script>
<script>
%s
</script>
</body></html>
"""


def main():
    doc = HTML % (CSS, bundle())
    out = os.path.join(HERE, "QuizQuest.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(doc)
    print("wrote %s (%.0f KB)" % (out, len(doc) / 1024))


if __name__ == "__main__":
    main()
