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
.card{background:#fff;border-radius:20px;padding:20px 22px;margin:18px 0;box-shadow:0 6px 18px rgba(0,0,0,.08)}
h2{font-size:26px;margin:.2em 0 .5em}
h2 .e{font-size:30px;vertical-align:-2px;margin-right:6px}
.lead{font-size:18px}
.tip{background:#ecfdf5;border-left:6px solid #10b981;border-radius:12px;padding:12px 16px;margin:12px 0;font-size:16px}
.note{background:#fff7ed;border-left:6px solid #f59e0b;border-radius:12px;padding:12px 16px;margin:12px 0}
.steps{counter-reset:s;list-style:none;padding:0;margin:0}
.steps li{position:relative;padding:10px 0 10px 52px;font-size:17px;border-bottom:1px dashed var(--line)}
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
/* question bank */
.subhead{display:flex;align-items:center;gap:10px;font-size:22px;font-weight:700;margin:18px 0 8px;padding:8px 14px;border-radius:12px;color:#fff}
.q{border:1px solid var(--line);border-radius:14px;padding:12px 14px;margin:10px 0;background:var(--cream)}
.qt{font-size:17px;font-weight:700}
.clk{display:inline-block;background:#ccfbf1;color:#0f766e;border-radius:8px;padding:1px 8px;font-size:13px;margin-left:6px}
.opts{margin:8px 0 4px}
.opt{display:inline-block;background:#eef2f7;color:#374151;border-radius:999px;padding:4px 12px;margin:3px 5px 3px 0;font-size:15px}
.opt.ok{background:#16a34a;color:#fff;font-weight:700}
.hint{color:var(--soft);font-style:italic;font-size:14px}
.gradehd{font-size:30px;margin:26px 0 4px;text-align:center}
.count{color:var(--soft);text-align:center;margin-bottom:8px}
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
  .subhead{break-before:page;break-after:avoid;color:#000 !important;background:#fff !important;border:2px solid #000;border-bottom:3px solid #000}
  /* the first subject of a grade rides along on the grade's page (no blank sheet) */
  .card > .subhead:first-child{break-before:auto}
  .q{break-inside:avoid;background:#fff;border:1px solid #bbb}
  .opt{background:#fff;border:1px solid #888;color:#000}
  .opt.ok{background:#fff !important;color:#000 !important;border:2px solid #000;text-decoration:underline}
  .hint{color:#333}
  .clk{background:#fff;border:1px solid #000;color:#000}
  /* don't waste a page: the first grade follows the bank intro, not a blank sheet */
  .gradehd:first-of-type{break-before:auto}
}
"""

def esc(s): return html.escape(str(s))

def question_html(q):
    cls = ""
    clk = ""
    if getattr(q, "clock", 0):
        clk = f'<span class="clk">\U0001F550 a clock showing {q.clock} o’clock is drawn</span>'
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
    h = f'<div class="subhead" style="background:{color}"><span>{emoji}</span> {esc(subject)} <span style="font-weight:400;font-size:15px">({len(qs)})</span></div>'
    return h + "".join(question_html(q) for q in qs)

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
