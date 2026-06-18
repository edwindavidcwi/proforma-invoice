#!/usr/bin/env python3
# Bundles the v3 slice (questions + Game Pack + engine + front-end) into ONE
# offline QuizQuest3.html. The same engine the audit proves is what ships here.
#   python3 build.py
import os, re
HERE = os.path.dirname(os.path.abspath(__file__))
ORDER = ["engine/questions.js", "pack/pallet.pack.js", "engine/engine.js", "web/main.js"]

def strip(src):
    src = re.sub(r'(?m)^\s*import\b[\s\S]*?;', '', src)
    src = re.sub(r'(?m)^\s*export\s*\{[^}]*\};\s*$', '', src)
    src = re.sub(r'(?m)^export\s+', '', src)
    return src

def bundle():
    parts = []
    for rel in ORDER:
        parts.append("/* ===== %s ===== */\n%s" % (rel, strip(open(os.path.join(HERE, rel), encoding="utf-8").read())))
    return "(function(){\n" + "\n\n".join(parts) + "\n})();"

CSS = r"""
*{box-sizing:border-box}
body{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;
 background:linear-gradient(160deg,#0e2838,#071620);
 font-family:"Segoe UI Rounded","Comic Sans MS",system-ui,sans-serif;-webkit-user-select:none;user-select:none}
#qq{width:min(96vw,680px)}
#bar{display:flex;align-items:center;gap:8px;padding:10px 12px;border-radius:14px 14px 0 0;
 background:linear-gradient(135deg,#4f46e5,#7c3aed);color:#fff}
#bar .logo{font-weight:800;font-size:18px}.grow{flex:1}
#bar .tb{background:rgba(255,255,255,.22);border:0;color:#fff;border-radius:10px;padding:8px 11px;font:700 13px/1 inherit;cursor:pointer}
#bar .tb.off{opacity:.5;text-decoration:line-through}
#stage{position:relative;background:#0b1418;line-height:0;display:flex;justify-content:center}
#cv{display:block;image-rendering:pixelated;max-width:100%;height:auto;background:#9bbc0f}
#ov{position:absolute;inset:0;display:flex;align-items:flex-end;justify-content:center;pointer-events:none;padding:10px}
#ov .box{pointer-events:auto;width:100%;background:#fffdf8;border-radius:16px;padding:13px 15px;box-shadow:0 8px 26px rgba(0,0,0,.5);color:#26303a}
.box p{margin:0 0 10px;font-size:18px;font-weight:700}
.clk{display:inline-block;background:#e0f2f1;color:#0d9488;border-radius:8px;padding:1px 8px;font-size:13px}
.hint{margin:8px 0 0!important;font-size:14px!important;color:#b4690e!important}
.opts{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.opt{min-height:48px;border:3px solid #cdd7e3;background:#fff;border-radius:13px;padding:10px;font:800 16px/1.1 inherit;color:#26303a;cursor:pointer}
.opt:active{transform:scale(.96)}
.opt.go{grid-column:1/3;background:linear-gradient(180deg,#5be39a,#16a34a);color:#04261a;border:0}

.log{margin:0 0 6px;font-size:13px!important;color:#5a6b7a!important;font-weight:700}
.run{margin-top:8px;width:100%;min-height:38px;border:0;border-radius:10px;background:#eef2f7;color:#5a6b7a;font:700 14px/1 inherit;cursor:pointer}
#pad{display:flex;align-items:center;justify-content:space-between;padding:14px 18px 18px;background:#0e2838;border-radius:0 0 14px 14px}
.dpad{position:relative;width:132px;height:132px}
.dpad .d{position:absolute;width:44px;height:44px;border:0;border-radius:10px;background:#33506f;color:#cfe2ee;font-size:16px;cursor:pointer}
.dpad .u{left:44px;top:0}.dpad .dn{left:44px;top:88px}.dpad .l{left:0;top:44px}.dpad .r{left:88px;top:44px}
.ab .rb{width:64px;height:64px;border-radius:50%;border:0;font:800 22px/1 inherit;color:#fff;cursor:pointer;background:linear-gradient(180deg,#ff7a59,#e23b3b);box-shadow:0 4px 0 #a52121}
.ab .rb:active{transform:translateY(3px);box-shadow:none}
"""

HTML = """<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<title>Quiz Quest</title><style>%s</style></head><body>
<script>window.addEventListener('error',function(e){try{console.error('caught',e.error||e.message)}catch(x){}});
window.addEventListener('unhandledrejection',function(e){if(e&&e.preventDefault)e.preventDefault();});</script>
<script>
%s
</script></body></html>
"""

def main():
    doc = HTML % (CSS, bundle())
    out = os.path.join(HERE, "QuizQuest3.html")
    open(out, "w", encoding="utf-8").write(doc)
    print("wrote %s (%.0f KB)" % (out, len(doc) / 1024))

if __name__ == "__main__":
    main()
