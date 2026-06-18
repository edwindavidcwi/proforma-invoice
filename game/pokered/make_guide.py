#!/usr/bin/env python3
# Builds the "Parent & Teacher Pack" -- a friendly, printable HTML guide + the
# full categorized question bank -- for a parent/child who don't know the game.
# Questions are pulled from tools_gen_quiz (the source of truth), so the bank is
# always exact. Visuals are original CSS + emoji only (no copyrighted art).
#
#   python3 make_guide.py --sample   # small preview (Grade 1, 3 subjects)
#   python3 make_guide.py            # full pack (all grades + subjects)
import sys, html, tools_gen_quiz as T

SAMPLE = "--sample" in sys.argv

# subject -> (emoji, accent colour, what it teaches)
SUBJ = {
    "English":           ("\U0001F524", "#2563eb", "Opposites, plurals, past-tense words, and rhyming."),
    "Science & Nature":  ("\U0001F43E", "#16a34a", "Animals & their babies, the body, weather, nature facts."),
    "General Knowledge": ("\U0001F30D", "#9333ea", "Days, months, counting, and everyday facts."),
    "Shapes & Colors":   ("\U0001F537", "#ea580c", "Shape sides, mixing colours, corners and angles."),
    "Math":              ("➕",     "#dc2626", "Adding, subtracting, times tables, halves & fractions."),
    "Real Life":         ("\U0001F550", "#0d9488", "Telling time (with a clock!), calendar, measuring, money."),
}
ORDER = ["Math", "English", "Real Life", "Science & Nature", "General Knowledge", "Shapes & Colors"]

CSS = """
:root{--ink:#1f2937;--soft:#6b7280;--line:#e5e7eb;--cream:#fffdf7}
*{box-sizing:border-box}
body{margin:0;font-family:"Comic Sans MS","Chalkboard SE","Segoe UI Rounded","Segoe UI",system-ui,sans-serif;
  color:var(--ink);background:linear-gradient(160deg,#fef3c7,#dbeafe 55%,#ede9fe);line-height:1.5}
.wrap{max-width:920px;margin:0 auto;padding:18px}
.cover{background:linear-gradient(135deg,#1e3a8a,#6d28d9);color:#fff;border-radius:24px;padding:34px 28px;
  text-align:center;box-shadow:0 12px 30px rgba(0,0,0,.18)}
.cover h1{font-size:40px;margin:.1em 0}
.cover p{font-size:18px;opacity:.95;margin:.3em 0}
.badgeRow{margin-top:14px}
.badgeRow span{display:inline-block;background:rgba(255,255,255,.18);border-radius:999px;padding:6px 13px;margin:4px;font-size:15px}
.card{background:#fff;border-radius:18px;padding:14px 18px;margin:12px 0;box-shadow:0 6px 18px rgba(0,0,0,.08)}
h2{font-size:23px;margin:.1em 0 .4em}
h2 .e{font-size:27px;vertical-align:-2px;margin-right:6px}
.lead{font-size:16px;margin:.3em 0}
.tip{background:#ecfdf5;border-left:6px solid #10b981;border-radius:10px;padding:9px 14px;margin:8px 0;font-size:15px}
.note{background:#fff7ed;border-left:6px solid #f59e0b;border-radius:10px;padding:9px 14px;margin:8px 0;font-size:15px}
.steps{counter-reset:s;list-style:none;padding:0;margin:0}
.steps li{position:relative;padding:7px 0 7px 48px;font-size:15px;border-bottom:1px dashed var(--line)}
.steps li:last-child{border-bottom:0}
.steps li::before{counter-increment:s;content:counter(s);position:absolute;left:0;top:8px;width:36px;height:36px;
  background:#6d28d9;color:#fff;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:18px;font-weight:700}
/* mock Game Boy quiz screen */
.gb{max-width:330px;margin:14px auto;background:#0b3d2e;border-radius:16px;padding:14px;box-shadow:0 8px 20px rgba(0,0,0,.25)}
.gbscreen{background:#e8f5d0;border:3px solid #20351f;border-radius:8px;padding:12px 10px;color:#20351f;
  font-family:"Courier New",monospace;font-weight:700}
.gbq{font-size:16px}
.gbgap{height:14px}
.gbgrid{display:grid;grid-template-columns:1fr 1fr;gap:6px 10px;font-size:15px}
.gbcur::before{content:"▶ "}
.gbcaption{color:#cbd5e1;font-size:13px;text-align:center;margin-top:8px;font-family:system-ui}
/* controls */
.pad{display:flex;gap:30px;align-items:center;justify-content:center;flex-wrap:wrap;margin:10px 0}
.dpad{position:relative;width:108px;height:108px}
.dpad div{position:absolute;background:#374151;width:36px;height:36px}
.dpad .u{left:36px;top:0;border-radius:6px 6px 0 0}.dpad .d{left:36px;bottom:0;border-radius:0 0 6px 6px}
.dpad .l{left:0;top:36px;border-radius:6px 0 0 6px}.dpad .r{right:0;top:36px;border-radius:0 6px 6px 0}
.dpad .c{left:36px;top:36px}
.btns{display:flex;gap:14px}
.rb{width:54px;height:54px;border-radius:50%;background:#be123c;color:#fff;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:20px;box-shadow:0 3px 0 #7f1d1d}
.keymap{font-size:15px}
.keymap b{display:inline-block;min-width:74px}
/* question bank -- compact cards flowed into responsive columns, but every
   detail kept readable: clear answer pills, the full hint, the clock note */
.subhead{display:flex;align-items:center;gap:9px;font-size:20px;font-weight:700;margin:14px 0 8px;padding:7px 13px;border-radius:11px;color:#fff;break-after:avoid}
.qlist{columns:360px;column-gap:16px}
/* Math: short numeric items -> denser grid + tighter cards */
.qlist.compact{columns:210px;column-gap:12px}
.qlist.compact .q{padding:6px 9px;margin:0 0 7px}
.qlist.compact .qt{font-size:15px}
.q{break-inside:avoid;border:1px solid var(--line);border-radius:12px;padding:8px 11px;margin:0 0 9px;background:var(--cream)}
.qt{font-size:16px;font-weight:700}
.clk{display:block;background:#ccfbf1;color:#0f766e;border-radius:7px;padding:2px 8px;font-size:12.5px;margin-top:3px}
.opts{margin:6px 0 3px;line-height:2}
.opt{display:inline-block;background:#eef2f7;color:#374151;border-radius:999px;padding:3px 11px;margin:0 5px 2px 0;font-size:14px}
.opt.ok{background:#16a34a;color:#fff;font-weight:700}
.hint{color:var(--soft);font-style:italic;font-size:13.5px}
/* adventure walkthrough */
.gymtable{width:100%;border-collapse:collapse;font-size:14.5px;margin-top:8px}
.gymtable th,.gymtable td{text-align:left;padding:6px 9px;border-bottom:1px solid var(--line);vertical-align:top}
.gymtable th{background:#eef2f7;font-size:13px;text-transform:uppercase;letter-spacing:.03em;color:#475569}
.gymtable td:first-child,.gymtable td:nth-child(2){font-weight:700;white-space:nowrap}
.gymtable tr:last-child td{border-bottom:0}
.win{color:#15803d;font-weight:700}
.badgecol{white-space:nowrap;color:#b45309;font-weight:700}
.typetip{display:flex;flex-wrap:wrap;gap:8px;margin-top:6px}
.typetip span{background:#f1f5f9;border-radius:999px;padding:5px 12px;font-size:15px}
/* starter picker cards */
.starters{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px;margin-top:10px}
.starter{border-radius:14px;padding:12px 14px;color:#fff;box-shadow:0 4px 10px rgba(0,0,0,.1)}
.starter h4{margin:.2em 0;font-size:19px}
.starter p{margin:.3em 0;font-size:14.5px;line-height:1.45}
.starter .lvl{display:inline-block;background:rgba(255,255,255,.22);border-radius:999px;padding:2px 10px;font-size:13px;margin-bottom:4px}
.starter.bulb{background:linear-gradient(135deg,#15803d,#16a34a)}
.starter.char{background:linear-gradient(135deg,#b91c1c,#ea580c)}
.starter.squi{background:linear-gradient(135deg,#1d4ed8,#0ea5e9)}
/* city journey blocks */
.cities{display:flex;flex-direction:column;gap:10px;margin-top:10px}
.city{background:#f8fafc;border-left:6px solid #6d28d9;border-radius:12px;padding:12px 16px}
.city.gym{background:#fffbeb;border-left-color:#f59e0b}
.city.rocket{background:#fef2f2;border-left-color:#dc2626}
.city.elite{background:#eef2ff;border-left-color:#4f46e5}
.city h3{margin:.05em 0 .35em;font-size:18px;color:#1e3a8a;display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.city.gym h3{color:#92400e}
.city.rocket h3{color:#991b1b}
.city.elite h3{color:#3730a3}
.city .stage{background:#1e3a8a;color:#fff;font-size:12px;padding:2px 9px;border-radius:999px;font-weight:700;letter-spacing:.02em}
.city.gym .stage{background:#b45309}
.city.rocket .stage{background:#b91c1c}
.city.elite .stage{background:#4338ca}
.city ul{margin:5px 0;padding-left:22px}
.city ul li{margin:3px 0;font-size:15px;line-height:1.45}
.city .catch{margin-top:6px;font-size:14px;color:#374151;background:#ecfeff;border-radius:8px;padding:6px 11px}
.city .catch b{color:#0e7490}
.city .battletip{margin-top:6px;font-size:14px;background:#dcfce7;border-radius:8px;padding:6px 11px;color:#14532d}
.city .warn{margin-top:6px;font-size:14px;background:#fee2e2;border-radius:8px;padding:6px 11px;color:#7f1d1d}
/* type-effectiveness grid */
.typegrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:10px;margin-top:10px}
.typecard{border-radius:12px;padding:10px 14px;color:#fff;font-size:14.5px;line-height:1.5}
.typecard b{font-size:16px;display:block;margin-bottom:3px}
.typecard small{display:block;opacity:.95;font-size:13px;margin-top:4px}
/* HM list */
.hmlist{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:10px;margin-top:8px}
.hm{background:#f0f9ff;border-left:5px solid #0284c7;border-radius:10px;padding:10px 13px}
.hm b{color:#075985;font-size:15.5px}
.hm p{margin:3px 0;font-size:14px;color:#374151;line-height:1.4}
/* Elite Four */
.elite4{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:10px;margin-top:10px}
.efcard{background:#eef2ff;border-radius:12px;padding:11px 14px;border-left:5px solid #6366f1}
.efcard b{font-size:16px;color:#3730a3;display:block}
.efcard .uses{display:inline-block;background:#fff;color:#1e293b;border-radius:999px;padding:2px 9px;font-size:13px;margin-top:3px}
.efcard p{margin:5px 0 0;font-size:14px;color:#374151;line-height:1.45}
.gradehd{font-size:27px;margin:22px 0 2px;text-align:center}
.count{color:var(--soft);text-align:center;margin-bottom:6px;font-size:14px}
.foot{text-align:center;color:#6b7280;font-size:14px;margin:26px 0}
/* Print: clean black-on-white workbook. Each grade starts a fresh page, each
   subject starts a fresh page, and a question never splits across a page.
   The ✓ keeps the correct answer obvious even on a black-and-white printer. */
@media print{
  @page{margin:14mm}
  body{background:#fff;color:#000;line-height:1.45}
  .wrap{max-width:100%;padding:0}
  .card,.cover{box-shadow:none}
  .cover{background:#fff;color:#000;border:2px solid #000;border-radius:0}
  .cover h1{font-size:30px}
  .badgeRow span{background:#fff;border:1px solid #000;color:#000}
  .card{border:1px solid #999;border-radius:0;margin:10px 0;padding:12px 14px;break-inside:avoid}
  .tip,.note{background:#fff;border-left:4px solid #000}
  .gb{background:#fff;border:1px solid #000}
  .gbscreen{background:#fff}
  .gradehd{break-before:page;border-bottom:3px solid #000;padding-bottom:4px}
  /* a fresh page per grade is plenty; subjects flow to keep the page count down */
  .subhead{break-after:avoid;color:#000 !important;background:#fff !important;border:1px solid #000}
  .qlist{columns:2;column-gap:14px}
  .qlist.compact{columns:3;column-gap:12px}
  .q{break-inside:avoid;background:#fff;border:1px solid #bbb}
  .opt{background:#fff;border:1px solid #999;color:#000}
  .opt.ok{background:#fff !important;color:#000 !important;border:2px solid #000;font-weight:700;text-decoration:underline}
  .hint{color:#333}
  .clk{background:#fff;border:1px solid #000;color:#000}
  /* don't waste a page: the first grade follows the bank intro, not a blank sheet */
  .gradehd:first-of-type{break-before:auto}
}
"""

def esc(s): return html.escape(str(s))

def question_html(q):
    clk = ""
    if getattr(q, "clock", 0):
        clk = f'<span class="clk">\U0001F550 a clock showing {q.clock} o’clock is drawn on screen</span>'
    opts = [f'<span class="opt ok">✓ {esc(q.correct)}</span>']
    for a in q.answers:
        if a != q.correct:
            opts.append(f'<span class="opt">{esc(a)}</span>')
    return (f'<div class="q"><div class="qt">{esc(q.text)}{clk}</div>'
            f'<div class="opts">{"".join(opts)}</div>'
            f'<div class="hint">\U0001F4A1 {esc(q.hint)}</div></div>')

def subject_block(grade, subject):
    emoji, color, _ = SUBJ[subject]
    qs = [q for q in T.banks[grade] if T.subject_of[(grade, q.text)] == subject]
    if not qs:
        return ""
    h = f'<div class="subhead" style="background:{color}"><span>{emoji}</span> {esc(subject)} <span style="font-weight:400;font-size:14px">({len(qs)})</span></div>'
    # Math answers are short (numbers) -> pack denser (more, narrower columns).
    cls = "qlist compact" if subject == "Math" else "qlist"
    return h + f'<div class="{cls}">' + "".join(question_html(q) for q in qs) + '</div>'

def adventure_html():
    # Factual Pokémon Red progression, written kid-simple (no copyrighted text/art).
    # The journey is broken into ~30 short city/route cards so a kid can read one
    # at a time and know exactly what to do next.
    return (_intro_card() + _starter_card() + _journey_card()
          + _gymtable_card() + _typechart_card() + _hms_card()
          + _legendaries_card() + _elite_card() + _tips_card() + _grade_note_card())

def _intro_card():
    return """
  <div class="card">
    <h2><span class="e">\U0001F5FA️</span>Your Pokémon adventure</h2>
    <p class="lead">You are a young trainer starting out in your home town. Your big quest:
    travel across the land, earn <b>8 gym badges</b>, and become the <b>Pokémon Champion</b>! 🏆
    Along the way you catch and train Pokémon &mdash; and every move you make is powered by
    answering a <b>school question</b>.</p>
    <div class="tip">\U0001F49A You can't lose for good. If your Pokémon faint, you wake up safe at the last town with <b>full health</b> and <b>no money lost</b>. So it's always safe to explore!</div>
    <div class="tip">\U0001F4BE <b>Save often!</b> Press <b>Start</b> &rarr; <b>SAVE</b>. The game does not save by itself.</div>
  </div>"""

def _starter_card():
    return """
  <div class="card">
    <h2><span class="e">\U0001F95A</span>Pick your starter Pokémon</h2>
    <p class="lead">Professor Oak lets you pick <b>one</b> of three little Pokémon to start. Each one is good &mdash; here's what's easy or tricky about each:</p>
    <div class="starters">
      <div class="starter bulb">
        <h4>\U0001F33F Bulbasaur</h4>
        <span class="lvl">Easiest start \U0001F49A</span>
        <p>A friendly plant-dinosaur. <b>Strong</b> against the <b>first 2 gyms</b> (Rock + Water). Great pick for new players!</p>
        <p><b>Grows into:</b> Ivysaur → Venusaur</p>
      </div>
      <div class="starter char">
        <h4>\U0001F525 Charmander</h4>
        <span class="lvl">Hard start \U0001F525</span>
        <p>A fire-lizard with a flame on its tail. <b>Weak</b> against the first 2 gyms. But late in the game it becomes <b>super strong</b>!</p>
        <p><b>Grows into:</b> Charmeleon → Charizard 🐉</p>
      </div>
      <div class="starter squi">
        <h4>\U0001F422 Squirtle</h4>
        <span class="lvl">Balanced \U0001F44D</span>
        <p>A tiny turtle that shoots water. <b>Strong</b> against the first gym (Brock). A safe, all-round pick.</p>
        <p><b>Grows into:</b> Wartortle → Blastoise</p>
      </div>
    </div>
    <div class="note"><b>Our pick for Ethan:</b> \U0001F33F <b>Bulbasaur</b> &mdash; the first few hours feel really easy and he'll see lots of quick wins.</div>
  </div>"""

# The cities/routes get rendered as a single big card so the column layout in
# print can keep them together without forcing a page break per stop.
JOURNEY_STOPS = [
    ("\U0001F3E0", "Pallet Town", "Stop 1 · Your home", None, [
        "Walk up to <b>Professor Oak's lab</b>.",
        "Pick your starter Pokémon (see above).",
        "Your <b>rival</b> battles you right away &mdash; if you lose, that's OK, you heal up.",
        "Pop next door &mdash; <b>Daisy</b> (rival's sister) gives you a free <b>Town Map</b> \U0001F5FA️ so you can see where you are.",
    ], "Nothing wild here &mdash; head north!", None, None),

    ("\U0001F33E", "Route 1 → Viridian City", "Stop 2 · Your first journey", None, [
        "Walk through tall grass &mdash; that's where wild Pokémon hide. Press <b>A</b> on a Poké Ball to catch one!",
        "In <b>Viridian City</b>, the Pokémart clerk gives you <b>Oak's Parcel</b>.",
        "Walk back to <b>Pallet</b> and hand it to Oak. He gives you the <b>Pokédex</b>!",
        "Return to Viridian and buy <b>Poké Balls</b> (to catch) and <b>Potions</b> (to heal).",
    ], "Pidgey \U0001F426, Rattata \U0001F400", None, None),

    ("\U0001F41B", "Route 2 → Viridian Forest → Pewter City", "Stop 3 · The bug forest", None, [
        "Head north through the forest. Bug Catcher trainers will challenge you &mdash; great practice!",
        "Look out for a wild ⚡ <b>Pikachu</b> &mdash; rare but possible.",
        "Pick up free Poké Balls on the ground (look for ! marks).",
        "Out of the forest → you reach <b>Pewter City</b>.",
    ], "Caterpie \U0001F41B, Weedle \U0001F41B, Pikachu ⚡ (rare!)", None, None),

    ("\U0001FAA8", "Pewter Gym — Brock", "GYM 1 · Boulder Badge \U0001F3C5", "gym", [
        "Brock uses <b>Rock</b>-type Pokémon: Geodude and Onix.",
        "<b>How to win easily:</b> use \U0001F33F <b>Grass</b> moves (Bulbasaur!) or \U0001F4A7 <b>Water</b> moves. They do <b>4× damage</b>!",
        "Don't use ⚡ Electric &mdash; it can't hurt Rock at all.",
        "Win → you get <b>Badge 1: Boulder Badge</b> and the move <b>TM34 Bide</b>.",
    ], None, "✨ The Pewter <b>Museum of Science</b> is fun to walk through (free if you go in the side door).", None),

    ("\U0001F319", "Route 3 → Mt. Moon → Route 4", "Stop 4 · The cave full of Zubats", None, [
        "On Route 3 you'll fight lots of trainers. Get strong before the cave!",
        "Inside <b>Mt. Moon</b>: lots of wild Zubat and Geodude. <b>Try to catch a Clefairy</b> ⭐ &mdash; it's rare and cute.",
        "Team Rocket grunts are here &mdash; the bad guys! Defeat them.",
        "At the end you must choose <b>one</b> fossil: <b>Helix</b> (becomes Omanyte) or <b>Dome</b> (becomes Kabuto). You can only ever have one!",
        "Pop out into <b>Route 4</b> → <b>Cerulean City</b>.",
    ], "Zubat \U0001F987, Geodude \U0001FAA8, Clefairy ⭐ (rare!), Paras \U0001F344", "\U0001F4A1 Pick whichever fossil sounds cooler &mdash; you can revive it later on Cinnabar Island.", None),

    ("\U0001F4A7", "Cerulean Gym — Misty", "GYM 2 · Cascade Badge \U0001F3C5", "gym", [
        "Misty uses <b>Water</b>-type Pokémon: Staryu and Starmie.",
        "<b>How to win easily:</b> \U0001F33F <b>Grass</b> moves or ⚡ <b>Electric</b> moves. Pikachu finally shines!",
        "Avoid \U0001F525 Fire moves &mdash; water snuffs them out.",
        "Win → <b>Badge 2: Cascade Badge</b> and <b>TM11 BubbleBeam</b>.",
    ], None, None, None),

    ("\U0001F309", "Nugget Bridge → Bill's House", "Stop 5 · The 5-trainer bridge", None, [
        "Just north of Cerulean is <b>Nugget Bridge</b>: beat 5 trainers in a row to win a <b>gold Nugget</b> (worth 5000!).",
        "At the end, your <b>Rival</b> battles you again.",
        "Keep going &mdash; you'll reach <b>Bill's House</b>. He's stuck as a Pokémon!",
        "Help Bill (just press the buttons he asks) → he gives you the <b>SS Anne Ticket</b> for a big cruise ship!",
    ], "Bellsprout \U0001F33F, Oddish \U0001F33F, Abra \U0001F52E (super rare!)", None, None),

    ("\U0001F6A2", "SS Anne — the cruise ship", "Stop 6 · The big boat", None, [
        "Show your ticket at <b>Vermilion City</b> dock. The ship has lots of trainers &mdash; great for levelling up!",
        "Find the <b>Captain's room</b> at the back. Talk to him → he gives you the move <b>HM01 Cut</b> ✂️.",
        "<b>Teach Cut</b> to a Pokémon → now you can chop little trees and open new paths!",
    ], None, "\U0001F4A1 Don't leave the ship until you have Cut &mdash; the ship sails away soon!", None),

    ("⚡", "Vermilion Gym — Lt. Surge", "GYM 3 · Thunder Badge \U0001F3C5", "gym", [
        "Lt. Surge uses <b>Electric</b>-type Pokémon: Voltorb, Pikachu, Raichu.",
        "<b>How to win easily:</b> use \U0001F30B <b>Ground</b> moves &mdash; electric can't hit ground Pokémon at all!",
        "Catch a <b>Diglett</b> or <b>Sandshrew</b> for this fight (Diglett's Cave is right outside!).",
        "<b>Trash-can puzzle:</b> first find the right trash can, then find the second one right next to it. Wrong = reset!",
        "Win → <b>Badge 3: Thunder Badge</b> and <b>TM24 Thunderbolt</b>.",
    ], None, "✨ In Vermilion, the <b>Pokémon Fan Club President</b> gives you a free <b>Bike Voucher</b> &mdash; trade it in Cerulean for a free <b>Bicycle</b> \U0001F6B2!", None),

    ("\U0001F526", "Route 9 → Rock Tunnel", "Stop 7 · The dark cave", None, [
        "<b>Rock Tunnel is pitch black!</b> You need the move <b>HM05 Flash</b> \U0001F526 to see.",
        "Get Flash from <b>Oak's Aide</b> on Route 2 (he checks how many Pokémon you've caught &mdash; needs about 10).",
        "Teach Flash, then walk through the tunnel. Lots of trainers and wild Pokémon!",
        "Come out the south side → <b>Lavender Town</b>.",
    ], "Geodude \U0001FAA8, Onix \U0001FAA8, Machop \U0001F94A, Cubone \U0001F480", None, "Skipping Flash makes the cave super hard &mdash; one step at a time blind!"),

    ("\U0001F47B", "Lavender Town → Pokémon Tower", "Stop 8 · The ghost tower", None, [
        "Lavender Town has a <b>tall scary tower</b> with Ghost Pokémon. But you can't see them yet!",
        "You'll come back here later with a <b>Silph Scope</b> to see the ghosts.",
        "For now, just visit and head west toward Celadon.",
    ], None, None, "Going up the tower without the Silph Scope &mdash; you'll get blocked!"),

    ("\U0001F300", "Route 7 → Celadon City", "Stop 9 · The big shopping city", None, [
        "Celadon is the <b>biggest city</b>. It has a huge <b>Department Store</b> \U0001F3EC &mdash; lots of items, healing, and TMs!",
        "There are <b>vending machines</b> at the top of the store &mdash; buy <b>Fresh Water</b>, <b>Soda Pop</b>, <b>Lemonade</b>. Save one!",
        "The <b>Game Corner</b> 🎰 has slot machines &mdash; and a <b>secret Team Rocket hideout</b> behind a poster!",
        "Talk to the man in the Celadon Mansion's apartment → he gives you a free <b>Eevee</b> 🦊!",
    ], "Eevee 🦊 (gift!), Vulpix \U0001F98A, Growlithe \U0001F415", None, None),

    ("\U0001F33F", "Celadon Gym — Erika", "GYM 4 · Rainbow Badge \U0001F3C5", "gym", [
        "Erika uses <b>Grass</b>-type Pokémon: Victreebel, Tangela, Vileplume.",
        "<b>How to win easily:</b> \U0001F525 <b>Fire</b>, \U0001F985 <b>Flying</b>, or 🐛 <b>Bug</b> moves &mdash; all are very strong vs Grass!",
        "Win → <b>Badge 4: Rainbow Badge</b> and <b>TM21 Mega Drain</b>.",
    ], None, None, None),

    ("\U0001F977", "Rocket Hideout (under Game Corner)", "Stop 10 · Bust the bad guys", "rocket", [
        "In the Game Corner, look for a poster on the wall &mdash; press A on it → secret stairs!",
        "Fight your way down 4 floors of Rocket grunts.",
        "Boss fight: <b>Giovanni</b> (round 1) &mdash; uses Ground Pokémon. Use Water or Grass.",
        "Win → you get the <b>Silph Scope</b> 👻 (lets you see ghosts) and the <b>Lift Key</b>.",
    ], None, None, None),

    ("\U0001F47B", "Pokémon Tower (Lavender)", "Stop 11 · Save Mr. Fuji", None, [
        "Climb the tower with the Silph Scope. You can now <b>see ghost Pokémon</b> &mdash; lots of <b>Gastly</b> and <b>Haunter</b>!",
        "Try to catch one &mdash; ghosts are awesome.",
        "Near the top: a sad <b>Marowak ghost</b> blocks the way. Beat her in a battle.",
        "Defeat the Rocket grunts at the top, save kindly <b>Mr. Fuji</b>.",
        "He gives you the <b>Poké Flute</b> \U0001F3B5 &mdash; wakes up sleeping Snorlax!",
    ], "Gastly 👻, Haunter 👻, Cubone \U0001F480", None, None),

    ("\U0001F62A", "Wake the Snorlax", "Stop 12 · The big sleepy lump", None, [
        "Two huge sleeping <b>Snorlax</b> 🐻 block the roads &mdash; one on Route 12 (south of Lavender), one on Route 16 (west of Celadon).",
        "Walk up to one, press A, choose <b>Poké Flute</b> from your bag.",
        "Snorlax wakes up and battles you! It's a tough fight &mdash; or try to catch it!",
        "Now the road is open!",
    ], "Snorlax 🐻 (one-of-a-kind)", "\U0001F4A1 Try to catch Snorlax! It's huge and very strong &mdash; one of the best Pokémon in the game.", None),

    ("\U0001F33A", "Routes 12-15 → Fuchsia City", "Stop 13 · The Safari Zone city", None, [
        "Long walk south through tall grass and forests &mdash; lots of trainers and Pokémon.",
        "Reach <b>Fuchsia City</b> &mdash; home of the famous <b>Safari Zone</b> \U0001F992!",
        "<b>Safari Zone:</b> pay 500 coins, get 30 special Poké Balls + 600 steps. Catch <b>rare</b> Pokémon: Tauros, Chansey, Scyther, Pinsir, Dratini, Kangaskhan!",
        "<b>Important hidden items in Safari Zone:</b> find <b>HM03 Surf</b> \U0001F30A (Area 3 secret house) and the <b>Gold Teeth</b> (Area 3 grass).",
        "Bring the Gold Teeth to the <b>Warden</b> (next to the Pokémon Center) → he gives you <b>HM04 Strength</b> \U0001F4AA!",
    ], "Tauros \U0001F404, Dratini \U0001F432, Scyther \U0001F993, Kangaskhan \U0001F999, Chansey \U0001F495", "\U0001F4A1 Surf lets you travel on water. Strength pushes giant boulders. Both unlock new areas!", None),

    ("☠️", "Fuchsia Gym — Koga", "GYM 5 · Soul Badge \U0001F3C5", "gym", [
        "Koga uses <b>Poison</b>-type Pokémon: Koffing, Muk, Weezing.",
        "<b>How to win easily:</b> \U0001F52E <b>Psychic</b> moves or \U0001F30B <b>Ground</b> moves &mdash; both are very strong!",
        "The gym is full of <b>invisible walls</b> &mdash; bump into them to find the path.",
        "Win → <b>Badge 5: Soul Badge</b> and <b>TM06 Toxic</b>.",
    ], None, None, None),

    ("\U0001F3D9️", "Saffron City → Silph Co.", "Stop 14 · Tower full of bad guys", "rocket", [
        "Saffron's gates were blocked by a thirsty guard! Bring a <b>Fresh Water / Soda / Lemonade</b> from Celadon vending machines &mdash; give him a drink → he steps aside.",
        "Team Rocket has taken over the <b>Silph Co. building</b> (11 floors of bad guys!).",
        "Find the <b>Card Key</b> on floor 5 to open locked doors.",
        "A man on the 7th floor gives you <b>Lapras</b> 💙 &mdash; a powerful Water/Ice Pokémon!",
        "Top floor: beat your <b>Rival</b>, then beat <b>Giovanni round 2</b>.",
        "Win → the Silph president gives you the <b>Master Ball</b> &mdash; catches any Pokémon, never misses! Save it for Mewtwo!",
    ], "Lapras 💙 (gift!)", "\U0001F4A1 Don't use the Master Ball on a normal Pokémon &mdash; save it for the strongest!", None),

    ("\U0001F52E", "Saffron Gym — Sabrina", "GYM 6 · Marsh Badge \U0001F3C5", "gym", [
        "Sabrina uses <b>Psychic</b>-type Pokémon: Kadabra, Alakazam, Mr. Mime, Venomoth.",
        "<b>How to win easily:</b> 🐛 <b>Bug</b> moves are super strong (Pinsir, Scyther, Beedrill!).",
        "The gym has <b>teleporter tiles</b> on the floor &mdash; step on them to jump rooms. Try each one to find the path.",
        "Win → <b>Badge 6: Marsh Badge</b> and <b>TM46 Psywave</b>.",
    ], None, None, None),

    ("\U0001F310", "Routes 19-20 → Seafoam Islands → Cinnabar", "Stop 15 · Surf to the south", None, [
        "From Fuchsia, head south and <b>Surf</b> on the water!",
        "<b>Seafoam Islands:</b> a cave with water inside. Use <b>Strength</b> to push boulders into the water current to stop it.",
        "Deep inside: catch the legendary ice-bird <b>Articuno</b> ❄️!",
        "Out the other side → swim south to <b>Cinnabar Island</b> 🌋.",
    ], "Articuno ❄️ (legendary!), Seel \U0001F9AD, Krabby \U0001F980, Tentacool \U0001F419", None, None),

    ("\U0001F3DA️", "Cinnabar Island → Pokémon Mansion", "Stop 16 · The burning mansion", None, [
        "On Cinnabar there's a <b>Lab</b> that revives fossils (give them your fossil from Mt. Moon!).",
        "The <b>Pokémon Mansion</b> is creepy and locked. Find <b>switches</b> on each floor (read the journals → hints about <b>Mewtwo</b>!).",
        "Find the <b>Secret Key</b> on the basement floor.",
        "Take it to Blaine's gym &mdash; the door is now open!",
    ], "Growlithe \U0001F415, Ponyta \U0001F40E, Magmar \U0001F525, Grimer \U0001F9A0", None, None),

    ("\U0001F525", "Cinnabar Gym — Blaine", "GYM 7 · Volcano Badge \U0001F3C5", "gym", [
        "Blaine uses <b>Fire</b>-type Pokémon: Growlithe, Ponyta, Rapidash, Arcanine.",
        "<b>How to win easily:</b> \U0001F4A7 <b>Water</b> moves are perfect (Squirtle, Lapras!). \U0001F30B <b>Ground</b> or 🪨 <b>Rock</b> also work great.",
        "The gym has trivia doors (the mod's quiz takes care of these!).",
        "Win → <b>Badge 7: Volcano Badge</b> and <b>TM38 Fire Blast</b>.",
    ], None, None, None),

    ("\U0001F30B", "Viridian Gym — Giovanni", "GYM 8 · Earth Badge \U0001F3C5", "gym", [
        "Fly or bike back to <b>Viridian City</b> &mdash; the gym is finally open!",
        "Giovanni is the <b>Team Rocket boss</b>! He uses <b>Ground/Rock</b> Pokémon: Rhyhorn, Dugtrio, Nidoking, Nidoqueen, Rhydon.",
        "<b>How to win easily:</b> \U0001F4A7 <b>Water</b>, \U0001F33F <b>Grass</b>, \U0001F9CA <b>Ice</b>, or 🥊 <b>Fighting</b> moves.",
        "Win → <b>Badge 8: Earth Badge</b> and <b>TM27 Fissure</b>. Giovanni quits Team Rocket!",
        "Now you can go to <b>Victory Road</b> and the <b>Pokémon League</b>!",
    ], None, "\U0001F4A1 Before Victory Road: level your team to about <b>50</b>. Get plenty of Potions, Revives, Full Heals!", None),

    ("\U0001F308", "Route 23 → Victory Road", "Stop 17 · The final mountain", None, [
        "Show all 8 badges to the guards on Route 23 → they let you pass.",
        "<b>Victory Road</b> is a giant cave puzzle: use <b>Strength</b> to push boulders onto floor switches to open doors.",
        "Lots of strong wild Pokémon and trainers!",
        "<b>Legendary catch:</b> deep inside, you'll find <b>Moltres</b> 🔥 the legendary fire-bird!",
        "Out the top → <b>Indigo Plateau</b>!",
    ], "Moltres 🔥 (legendary!), Onix \U0001FAA8, Machoke \U0001F94A, Marowak \U0001F480", "\U0001F4A1 <b>Save right before each Elite Four fight!</b> There are NO Pokémon Centers inside &mdash; only one big save spot at the entrance.", None),
]

def _journey_card():
    body = []
    for emoji, name, stage, kind, steps, catch, tip, warn in JOURNEY_STOPS:
        cls = "city"
        if kind: cls += " " + kind
        body.append(f'<div class="{cls}">')
        body.append(f'<h3><span class="stage">{esc(stage)}</span><span>{emoji} {esc(name)}</span></h3>')
        body.append('<ul>' + ''.join(f'<li>{s}</li>' for s in steps) + '</ul>')
        if catch:
            body.append(f'<div class="catch"><b>Pokémon you might catch here:</b> {catch}</div>')
        if tip:
            body.append(f'<div class="battletip">{tip}</div>')
        if warn:
            body.append(f'<div class="warn">⚠️ {warn}</div>')
        body.append('</div>')
    return f"""
  <div class="card">
    <h2><span class="e">\U0001F45F</span>The complete journey &mdash; stop by stop</h2>
    <p class="lead">Follow these in order. Each stop tells you <b>exactly what to do</b>, the Pokémon you might catch, and the best tip for that part of the game.</p>
    <div class="cities">{''.join(body)}</div>
  </div>"""

def _gymtable_card():
    leaders = [
        ("Pewter City",   "Brock",     "Rock \U0001FAA8",   "Grass \U0001F33F or Water \U0001F4A7 moves",   "1 · Boulder"),
        ("Cerulean City", "Misty",     "Water \U0001F4A7",  "Grass \U0001F33F or Electric ⚡",               "2 · Cascade"),
        ("Vermilion City","Lt. Surge", "Electric ⚡",       "Ground \U0001F30B moves",                       "3 · Thunder"),
        ("Celadon City",  "Erika",     "Grass \U0001F33F",  "Fire \U0001F525, Flying \U0001F985, or Bug 🐛", "4 · Rainbow"),
        ("Fuchsia City",  "Koga",      "Poison ☠️",        "Psychic \U0001F52E or Ground \U0001F30B",       "5 · Soul"),
        ("Saffron City",  "Sabrina",   "Psychic \U0001F52E","Bug 🐛 moves",                                  "6 · Marsh"),
        ("Cinnabar Is.",  "Blaine",    "Fire \U0001F525",   "Water \U0001F4A7, Ground, or Rock 🪨",          "7 · Volcano"),
        ("Viridian City", "Giovanni",  "Ground \U0001F30B", "Water \U0001F4A7, Grass \U0001F33F, or Ice 🧊", "8 · Earth"),
    ]
    rows = "".join(
        f'<tr><td>{esc(c)}</td><td>{esc(l)}</td><td>{t}</td>'
        f'<td class="win">{w}</td><td class="badgecol">{b}</td></tr>'
        for c, l, t, w, b in leaders)
    return f"""
  <div class="card">
    <h2><span class="e">\U0001F3C5</span>The 8 Gyms at a glance</h2>
    <p class="lead">Quick reference: every leader and the easiest way to beat them.</p>
    <table class="gymtable">
      <tr><th>City</th><th>Leader</th><th>Uses</th><th>To win, use…</th><th>Badge</th></tr>
      {rows}
    </table>
  </div>"""

def _typechart_card():
    # The simplified type chart kids actually need (matchups that come up in Red).
    cards = [
        ("\U0001F525 Fire",     "linear-gradient(135deg,#ea580c,#dc2626)", "Burns <b>Grass</b> 🌿, <b>Bug</b> 🐛, <b>Ice</b> 🧊", "Hurts itself against: Water, Rock, Ground"),
        ("\U0001F4A7 Water",    "linear-gradient(135deg,#0ea5e9,#1d4ed8)", "Splashes <b>Fire</b> 🔥, <b>Rock</b> 🪨, <b>Ground</b> 🌋", "Hurts itself against: Grass, Electric"),
        ("\U0001F33F Grass",    "linear-gradient(135deg,#16a34a,#15803d)", "Grows over <b>Water</b> 💧, <b>Rock</b> 🪨, <b>Ground</b> 🌋", "Hurts itself against: Fire, Flying, Bug, Ice, Poison"),
        ("⚡ Electric",         "linear-gradient(135deg,#facc15,#eab308)", "Zaps <b>Water</b> 💧, <b>Flying</b> 🦅", "Doesn't hit <b>Ground</b> at all!"),
        ("\U0001F30B Ground",   "linear-gradient(135deg,#a16207,#854d0e)", "Quakes <b>Fire</b> 🔥, <b>Electric</b> ⚡, <b>Rock</b> 🪨, <b>Poison</b> ☠️", "Can't hit <b>Flying</b> Pokémon"),
        ("\U0001F985 Flying",   "linear-gradient(135deg,#7c3aed,#5b21b6)", "Swoops <b>Grass</b> 🌿, <b>Bug</b> 🐛, <b>Fighting</b> 🥊", "Hurts itself against: Electric, Rock, Ice"),
        ("\U0001F52E Psychic",  "linear-gradient(135deg,#ec4899,#be185d)", "Mind-blasts <b>Fighting</b> 🥊, <b>Poison</b> ☠️", "Hurts itself against: Bug"),
        ("🐛 Bug",              "linear-gradient(135deg,#84cc16,#4d7c0f)", "Bites <b>Grass</b> 🌿, <b>Psychic</b> 🔮", "Hurts itself against: Fire, Flying, Rock"),
        ("🧊 Ice",              "linear-gradient(135deg,#22d3ee,#0e7490)", "Freezes <b>Grass</b> 🌿, <b>Ground</b> 🌋, <b>Flying</b> 🦅, <b>Dragon</b> 🐉", "Hurts itself against: Fire, Water, Rock"),
        ("🥊 Fighting",         "linear-gradient(135deg,#b91c1c,#7f1d1d)", "Punches <b>Normal</b>, <b>Rock</b> 🪨, <b>Ice</b> 🧊", "Doesn't hit <b>Ghost</b> at all!"),
        ("🪨 Rock",             "linear-gradient(135deg,#6b7280,#374151)", "Smashes <b>Fire</b> 🔥, <b>Flying</b> 🦅, <b>Bug</b> 🐛, <b>Ice</b> 🧊", "Hurts itself against: Water, Grass, Ground, Fighting"),
        ("\U0001F47B Ghost",    "linear-gradient(135deg,#581c87,#3b0764)", "Spooks <b>Ghost</b> 👻, <b>Psychic</b> 🔮", "Doesn't hit <b>Normal</b> at all!"),
    ]
    cells = "".join(
        f'<div class="typecard" style="background:{bg}"><b>{name}</b>Strong against: {strong}<small>{weak}</small></div>'
        for name, bg, strong, weak in cards)
    return f"""
  <div class="card">
    <h2><span class="e">⚔️</span>Type cheat-sheet (what beats what)</h2>
    <p class="lead">Pick a move whose type is <b>strong</b> against the enemy's type and you do <b>2× or 4× damage</b>. The colour cards below are the easy ones to remember:</p>
    <div class="typegrid">{cells}</div>
    <div class="tip">\U0001F4A1 <b>Easy starter rule:</b> Water beats Fire 🔥, Fire beats Grass 🌿, Grass beats Water 💧. Always have one of each on your team!</div>
  </div>"""

def _hms_card():
    hms = [
        ("HM01 Cut ✂️",      "Chops down little trees that block paths.", "<b>SS Anne</b> &mdash; the Captain gives it to you after he's seasick (Vermilion City dock)."),
        ("HM02 Fly \U0001F985", "Lets you instantly fly to any town you've been to!", "<b>Route 16</b> &mdash; in a small house just west of Celadon City (wake Snorlax first)."),
        ("HM03 Surf \U0001F30A", "Lets you ride your Water Pokémon across the sea.", "<b>Safari Zone</b> &mdash; secret house in Area 3 (the far corner of the Safari Zone)."),
        ("HM04 Strength \U0001F4AA", "Pushes giant boulders around (needed in Seafoam, Victory Road).", "<b>Fuchsia City Warden</b> &mdash; bring him the <b>Gold Teeth</b> from the Safari Zone."),
        ("HM05 Flash \U0001F526", "Lights up dark caves so you can see!", "<b>Oak's Aide</b> on Route 2 &mdash; he wants you to have caught about <b>10</b> different Pokémon first."),
    ]
    cells = "".join(
        f'<div class="hm"><b>{name}</b><p>{what}</p><p>📍 <b>Get it from:</b> {where}</p></div>'
        for name, what, where in hms)
    return f"""
  <div class="card">
    <h2><span class="e">\U0001F31F</span>The 5 Special Moves (HMs) &mdash; how to find each</h2>
    <p class="lead">HMs are special moves that don't just work in battle &mdash; they work <b>on the world</b> too. Teach them to your Pokémon to unlock new paths!</p>
    <div class="hmlist">{cells}</div>
  </div>"""

def _legendaries_card():
    return """
  <div class="card">
    <h2><span class="e">✨</span>Legendary Pokémon to find</h2>
    <p class="lead">There are <b>4 super-rare Pokémon</b> in the game &mdash; you only get one chance to catch each! <b>Save right before</b> you find them. (Throw your <b>Master Ball</b> at the strongest one!)</p>
    <ul class="steps">
      <li>❄️ <b>Articuno</b> &mdash; ice-bird, deep inside <b>Seafoam Islands</b>. Use Surf + Strength.</li>
      <li>⚡ <b>Zapdos</b> &mdash; lightning-bird, inside the <b>Power Plant</b> (Route 10 &mdash; Surf from Route 9 near the entrance to Rock Tunnel).</li>
      <li>🔥 <b>Moltres</b> &mdash; fire-bird, deep inside <b>Victory Road</b> on the way to the League.</li>
      <li>🟣 <b>Mewtwo</b> &mdash; the strongest Pokémon in the game! Found in the <b>Cerulean Cave</b> (next to Cerulean City) <b>only after you become Champion</b>. Use the Master Ball!</li>
    </ul>
    <div class="tip">\U0001F4A1 <b>Tip:</b> all four are very strong &mdash; weaken them to a sliver of HP, put them to sleep, then throw Great Balls or Ultra Balls!</div>
  </div>"""

def _elite_card():
    eliters = [
        ("Lorelei \U0001F9CA",  "Ice + Water",   "Use ⚡ <b>Electric</b>, 🥊 <b>Fighting</b>, or 🪨 <b>Rock</b>. Watch out for her Cloyster &mdash; very tough!"),
        ("Bruno \U0001F94A",     "Fighting + Rock","Use \U0001F4A7 <b>Water</b>, \U0001F33F <b>Grass</b>, or \U0001F52E <b>Psychic</b>. Avoid Normal moves!"),
        ("Agatha \U0001F47B",   "Ghost + Poison", "Use \U0001F52E <b>Psychic</b> or \U0001F30B <b>Ground</b>. Her Gengar is fast &mdash; hit hard!"),
        ("Lance \U0001F432",     "Dragon + Flying","Use 🧊 <b>Ice</b> (super effective!) or ⚡ <b>Electric</b>. His Dragonite is the toughest yet."),
        ("Rival (Champion) \U0001F451", "All sorts",     "He has 6 Pokémon including a fully-evolved starter. Bring a balanced team and lots of healing items!"),
    ]
    cells = "".join(
        f'<div class="efcard"><b>{name}</b><span class="uses">Uses: {uses}</span><p>{plan}</p></div>'
        for name, uses, plan in eliters)
    return f"""
  <div class="card">
    <h2><span class="e">\U0001F451</span>The Elite Four &mdash; the final 5 battles</h2>
    <p class="lead">Five battles, <b>back to back</b>, with no Pokémon Center in between! Heal your team to full and stock up on Potions, Revives, and Full Heals before you go in. Bring a team with <b>different types</b>.</p>
    <div class="elite4">{cells}</div>
    <div class="tip">\U0001F3C6 Beat all 5 → you're the <b>Pokémon Champion</b>! Your trainer goes on the <b>Hall of Fame</b>. Now you can catch <b>Mewtwo</b> in the Cerulean Cave!</div>
  </div>"""

def _tips_card():
    return """
  <div class="card">
    <h2><span class="e">\U0001F4A1</span>Useful tips when you get stuck</h2>
    <div class="note"><b>Can't beat a trainer?</b> Walk around in tall grass for a bit &mdash; battling wild Pokémon makes yours <b>level up</b>. Stronger Pokémon = easier wins.</div>
    <div class="note"><b>Can't find where to go?</b> Check the <b>Town Map</b> (Start menu → Map). It shows every place &mdash; press A on a city to see its name.</div>
    <div class="note"><b>Lost in a cave?</b> Most caves have <b>one path</b>. Walk along every wall until you find the next door or ladder.</div>
    <div class="note"><b>Can't pass the sleeping Snorlax?</b> You need the <b>Poké Flute</b> &mdash; finish the Pokémon Tower in Lavender Town first.</div>
    <div class="note"><b>Guard won't let you into Saffron?</b> He's <b>thirsty</b>! Buy a <b>Fresh Water</b>, <b>Soda Pop</b>, or <b>Lemonade</b> from the vending machines at the top of the Celadon Department Store, then talk to him.</div>
    <div class="note"><b>Cave too dark to see?</b> You need <b>HM05 Flash</b> &mdash; get it from Oak's Aide on Route 2 after you've caught about 10 Pokémon.</div>
    <div class="note"><b>Tree in the way?</b> You need <b>HM01 Cut</b> &mdash; get it from the SS Anne Captain in Vermilion City.</div>
    <div class="note"><b>Boulder in the way?</b> You need <b>HM04 Strength</b> &mdash; get it from the Fuchsia Warden (bring the Gold Teeth from the Safari Zone).</div>
    <div class="note"><b>Water in the way?</b> You need <b>HM03 Surf</b> &mdash; find it in the Safari Zone's secret house.</div>
    <div class="note"><b>Out of money?</b> Sell <b>Nuggets</b> 💎 (you get one from Nugget Bridge) or fight a few trainers &mdash; they pay when you win.</div>
    <div class="note"><b>Out of Poké Balls?</b> Buy them at any Pokémart (the blue-roofed shop in every city).</div>
    <div class="note"><b>Stuck on a quiz question?</b> The game gives you a <b>hint</b> after the first wrong answer &mdash; read it carefully and try again!</div>
  </div>"""

def _grade_note_card():
    return """
  <div class="card">
    <h2><span class="e">\U0001F4C8</span>The clever part (a note for Mom &amp; Dad)</h2>
    <div class="note">The further Ethan travels, the more <b>badges</b> he earns &mdash; and the game quietly raises the school <b>grade level</b> of the questions to match:
      <ul style="margin:6px 0">
        <li><b>0–2 badges</b> &rarr; Grade 1 questions</li>
        <li><b>2–4 badges</b> &rarr; Grade 2</li>
        <li><b>4–6 badges</b> &rarr; Grade 3</li>
        <li><b>6–7 badges</b> &rarr; Grade 4</li>
        <li><b>8 badges</b> &rarr; Grade 5</li>
      </ul>
      So <b>just by playing the adventure</b>, Ethan is moving up grades &mdash; it never feels like a test.</div>
    <div class="note"><b>Want to skip ahead?</b> Use <b>☰ Menu → Focus</b> to lock the grade or subject. Pick the level you'd like him to practise today!</div>
    <div class="note"><b>Stuck on a question or two?</b> Talk to <b>Nurse Joy</b> in any Pokémon Center, or <b>Professor Oak</b> &mdash; they give <b>free quiz practice</b> with no battle, and they <b>explain</b> the answer when you miss.</div>
    <div class="note"><b>See progress:</b> <b>☰ Menu → Report Card</b> shows correct/total by subject and grade, and shows badges he's earned.</div>
  </div>"""

def guide_html():
    rows = "".join(
        f'<tr><td style="padding:4px 10px"><span style="font-size:20px">{SUBJ[s][0]}</span> <b>{esc(s)}</b></td>'
        f'<td style="padding:4px 10px;color:#374151">{esc(SUBJ[s][2])}</td></tr>' for s in ORDER)
    return f"""
  <div class="card">
    <h2><span class="e">\U0001F31F</span>What is this game?</h2>
    <p class="lead">It looks like a Game Boy adventure, but it's really a <b>learning game</b>. As your child
    plays and battles, the game asks a <b>school question</b> &mdash; answer it right and the move works!
    Get it wrong and it gives a <b>friendly hint</b> and lets you try again. Nobody is ever punished for a mistake.</p>
    <div class="tip">\U0001F49A The goal: Ethan practises reading, maths, and more <b>without it feeling like homework</b>.</div>
  </div>

  <div class="card">
    <h2><span class="e">▶️</span>Getting started</h2>
    <ol class="steps">
      <li>Open <b>Pokemon Quiz</b> (the Windows app, or the app on the phone).</li>
      <li>Press <b>Start</b> (the <b>Enter</b> key, or tap <b>Start</b>) to begin a new game and follow the short intro.</li>
      <li>Walk around with the <b>arrow keys</b>. When a battle begins, choose <b>FIGHT</b> then a move &mdash; that's when a question pops up!</li>
    </ol>
  </div>

  <div class="card">
    <h2><span class="e">❓</span>How a question works</h2>
    <p class="lead">This is what a question looks like on screen:</p>
    <div class="gb"><div class="gbscreen">
      <div class="gbq">Baby of a cow?</div>
      <div class="gbgap"></div>
      <div class="gbgrid"><span class="gbcur">calf</span><span>fawn</span><span>piglet</span><span>cub</span><span>joey</span><span>chick</span></div>
    </div><div class="gbcaption">Move the ▶ arrow to your answer, then press A.</div></div>
    <ol class="steps">
      <li>Read the question at the top (or let the game <b>read it aloud</b> &mdash; see below).</li>
      <li>Use the <b>arrow keys</b> to move the ▶ arrow to the answer you want.</li>
      <li>Press <b>A</b> (the <b>Z</b> key) to choose.</li>
      <li><b>Right answer</b> ✅ &mdash; your move lands and you build a streak. <b>Wrong</b> ❌ &mdash; a hint appears and you try once more.</li>
    </ol>
  </div>

  <div class="card">
    <h2><span class="e">\U0001F3AE</span>The buttons</h2>
    <div class="pad">
      <div class="dpad"><div class="u"></div><div class="d"></div><div class="l"></div><div class="r"></div><div class="c"></div></div>
      <div class="btns"><div class="rb">B</div><div class="rb">A</div></div>
    </div>
    <div class="keymap">
      <p><b>Arrow keys</b> &mdash; move around / choose an answer</p>
      <p><b>Z</b> = A button &mdash; confirm / talk / attack</p>
      <p><b>X</b> = B button &mdash; go back / cancel</p>
      <p><b>Enter</b> = Start &mdash; menus &amp; begin</p>
      <p>On a phone: use the on-screen buttons. Hold <b>Space</b> to fast-forward walking.</p>
    </div>
  </div>

  {adventure_html()}

  <div class="card">
    <h2><span class="e">\U0001F31F</span>Helpful features (tap ☰ Menu)</h2>
    <div class="tip">\U0001F5E3️ <b>Read aloud</b> &mdash; the game speaks each question and the choices out loud, in a friendly voice. Perfect before Ethan can read fast. There's a <b>Voice</b> button to switch the speaker.</div>
    <div class="tip">\U0001F3AF <b>Focus</b> &mdash; choose a <b>Level</b> (grade) and a <b>Subject</b> to practise. Leave it on <b>Auto / Any</b> to let the game pick.</div>
    <div class="tip">\U0001F4CA <b>Report Card</b> &mdash; see how he's doing by subject and grade, which questions he finds tricky, and earn ⭐ <b>badges</b> for mastering a subject.</div>
  </div>

  <div class="card">
    <h2><span class="e">\U0001F468‍\U0001F3EB</span>For the teacher (a note for Mom)</h2>
    <p class="lead">You don't need to know Pokémon at all. Here's the easy way to use it:</p>
    <div class="note">1. In <b>☰ Menu → Focus</b>, set the <b>Level</b> to Ethan's grade and pick a <b>Subject</b> you want to work on today.</div>
    <div class="note">2. Turn on <b>Read aloud</b> so he can hear every question.</div>
    <div class="note">3. Play together &mdash; when he misses one, read the <b>hint</b> with him and let him try again. Praise the streak!</div>
    <div class="note">4. Once a week, open the <b>Report Card</b> to see what to practise next. This question bank below shows every question, so you can pre-teach.</div>
    <table style="margin-top:10px">{rows}</table>
  </div>
"""

def bank_html():
    grades = [1] if SAMPLE else [1, 2, 3, 4, 5]
    subs = ["Math", "English", "Real Life"] if SAMPLE else ORDER
    out = ['<div class="card"><h2><span class="e">\U0001F4DA</span>Question Bank</h2>'
           '<p class="lead">Every question in the game, grouped by grade and subject. The <span class="opt ok" style="padding:1px 10px">✓ green</span> one is the correct answer; the grey ones are the other choices; \U0001F4A1 is the hint the game gives.</p></div>']
    for g in grades:
        out.append(f'<div class="gradehd">\U0001F393 Grade {g}</div>')
        total = len(T.banks[g])
        out.append(f'<div class="count">{total} questions</div>')
        out.append('<div class="card">')
        for s in subs:
            out.append(subject_block(g, s))
        out.append('</div>')
    return "".join(out)

def main():
    tag = " &mdash; SAMPLE" if SAMPLE else ""
    cover = f"""
  <div class="cover">
    <h1>\U0001F31F Pokémon Quiz{tag}</h1>
    <p>Parent &amp; Teacher Pack</p>
    <p style="font-size:15px">A learn-while-you-play game for Ethan &mdash; how to play, plus every question</p>
    <div class="badgeRow"><span>\U0001F524 English</span><span>➕ Math</span><span>\U0001F43E Science</span><span>\U0001F30D Gen. Knowledge</span><span>\U0001F537 Shapes</span><span>\U0001F550 Real Life</span></div>
  </div>"""
    samplenote = ('<div class="note" style="font-size:16px">\U0001F44B <b>This is a sample</b> to approve the look. '
                  'The full pack will include the complete walkthrough above plus <b>all 771 questions</b> across '
                  '<b>Grades 1–5</b> and all six subjects.</div>') if SAMPLE else ''
    body = cover + guide_html() + samplenote + bank_html()
    doc = (f'<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'
           f'<meta name="viewport" content="width=device-width, initial-scale=1">'
           f'<title>Pokemon Quiz - Parent &amp; Teacher Pack{tag}</title><style>{CSS}</style></head>'
           f'<body><div class="wrap">{body}<div class="foot">Made for Ethan \U0001F49B &mdash; print me or open on any phone or computer.</div></div></body></html>')
    out = "ParentPack_SAMPLE.html" if SAMPLE else "ParentPack.html"
    with open(out, "w", encoding="utf-8") as f:
        f.write(doc)
    print("wrote", out, "(%.0f KB)" % (len(doc) / 1024))

if __name__ == "__main__":
    main()
