#!/usr/bin/env python3
"""Generate engine/battle/quiz_data.asm with a large, multi-subject question bank.

Targets ~100 questions per grade with a balanced subject mix (Math, English,
Science & Nature, General Knowledge, Shapes & Colors). Every question has text
(<=18 chars), 3 answers (<=9 chars each), the correct index, and a method hint
(<=18 chars). Each grade's data is emitted into its own ROM bank (floating ROMX
section); the engine copies a chosen question into RAM before showing it.

Font has NO = + % , > characters. Allowed: 0-9 A-Z a-z space - / x . : ? !
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "engine", "battle", "quiz_data.asm")
TARGET = 100

ALLOWED = set("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz "
              "-/x.:?!")

def okstr(s, n):
    return all(c in ALLOWED for c in s) and len(s) <= n

class Bad(Exception):
    pass

class Q:
    def __init__(self, text, correct, distractors, hint):
        text, hint = str(text), str(hint)
        correct = str(correct)
        ans = [correct] + [str(d) for d in distractors]
        if not okstr(text, 18) or not okstr(hint, 18):
            raise Bad()
        for a in ans:
            if not okstr(a, 9):
                raise Bad()
        if len(set(ans)) != len(ans):
            raise Bad()
        self.text, self.hint, self.answers, self.correct = text, hint, ans, correct

def mk(text, correct, distractors, hint):
    try:
        return Q(text, correct, distractors, hint)
    except Bad:
        return None

def num(text, correct, hint, distractors=None):
    c = int(correct)
    if distractors is None:
        distractors = [c - 1, c + 1] if c >= 1 else [c + 1, c + 2]
    return mk(text, correct, distractors, hint)

def pick2(correct, word, candidates):
    out = []
    for c in candidates:
        c = str(c)
        if c != correct and c != word and c not in out and okstr(c, 9):
            out.append(c)
        if len(out) == 2:
            return out
    return None

def _two(c, cands):
    """Pick 2 distinct, non-negative distractors != c from cands (then pad)."""
    out = []
    for d in cands:
        d = int(d)
        if d >= 0 and d != c and d not in out:
            out.append(d)
        if len(out) == 2:
            return out
    i = 1
    while len(out) < 2:
        for d in (c + i, c - i, c + 10 * i):
            if d >= 0 and d != c and d not in out:
                out.append(d)
            if len(out) == 2:
                break
        i += 1
    return out[:2]

def smart(op, a, b, c):
    """Plausible, common-mistake distractors instead of the trivial c +/- 1."""
    if op == '+':   cands = [abs(a - b), c + 1, c + 10, c - 2]   # subtracted; near; place-value
    elif op == '-': cands = [a + b, c + 1, c + 10, c - 1]        # added instead; near
    elif op == 'x': cands = [a * (b - 1), a + b, a * (b + 1), c + 1]  # a group off; added
    elif op == '/': cands = [c + 1, b, c + 2, c - 1]             # near; confuse with divisor
    else:           cands = [c + 1, c + 5, c - 2, c * 2, c + 10]
    return _two(c, cands)

def spread(c):
    """A near miss plus a wider miss (so the 3 options aren't just consecutive)."""
    return _two(c, [c + 1, c + 5, c - 3, c * 2 if c <= 20 else c + 10, c + 10, c - 1])

# ===================== word / fact pools =====================
OPP = [("big","small"),("hot","cold"),("up","down"),("in","out"),("day","night"),
       ("fast","slow"),("happy","sad"),("full","empty"),("open","shut"),("wet","dry"),
       ("tall","short"),("high","low"),("good","bad"),("hard","soft"),("old","new"),
       ("light","dark"),("clean","dirty"),("near","far"),("loud","quiet"),("win","lose"),
       ("rich","poor"),("early","late"),("buy","sell"),("true","false"),("weak","strong"),
       ("thick","thin"),("wide","narrow"),("begin","end"),("push","pull"),("left","right"),
       ("first","last"),("more","less"),("young","old"),("brave","afraid"),("wild","tame")]
OPP_WORDS = [o for _, o in OPP] + [w for w, _ in OPP]

PLURALS = [("cat","cats"),("dog","dogs"),("pen","pens"),("hat","hats"),("cup","cups"),
           ("box","boxes"),("bus","buses"),("fox","foxes"),("dish","dishes"),
           ("baby","babies"),("city","cities"),("lady","ladies"),("pony","ponies"),
           ("man","men"),("woman","women"),("child","children"),("mouse","mice"),
           ("foot","feet"),("tooth","teeth"),("leaf","leaves"),("goose","geese")]

PAST = [("run","ran"),("go","went"),("eat","ate"),("see","saw"),("come","came"),
        ("give","gave"),("take","took"),("make","made"),("buy","bought"),
        ("teach","taught"),("sing","sang"),("swim","swam"),("fly","flew"),
        ("draw","drew"),("sit","sat"),("win","won"),("ride","rode"),("fall","fell")]

RHYME_GROUPS = [["cat","hat","bat","mat","rat"],["star","car","far","jar"],
                ["dog","log","fog"],["sun","fun","run","bun"],["tree","bee","see"],
                ["cake","lake","make","bake"],["ball","wall","tall","fall"],
                ["bell","well","tell"],["king","ring","sing","wing"],
                ["bug","rug","mug","hug"],["nose","rose","hose"],["boat","coat","goat"]]

BABIES = [("dog","puppy"),("cat","kitten"),("cow","calf"),("sheep","lamb"),
          ("horse","foal"),("goat","kid"),("hen","chick"),("frog","tadpole"),
          ("bear","cub"),("lion","cub"),("deer","fawn"),("pig","piglet"),
          ("duck","duckling"),("kangaroo","joey"),("cat","kitten")]
# dict.fromkeys dedupes while preserving order (a plain set is hash-randomized
# per run, which would make the generated distractors non-deterministic).
BABY_WORDS = list(dict.fromkeys(b for _, b in BABIES))

def stable_rot(*parts):
    """A deterministic small offset (0-8) from the given parts. Replaces the
    built-in hash(), which Python randomizes per process (PYTHONHASHSEED) and
    would otherwise make the generated question bank change on every re-run."""
    s = "|".join(str(p) for p in parts)
    return sum(ord(c) for c in s) % 9

# ===================== subject builders (per grade) =====================
def fit(long, short):
    """Use the clearer wording when it fits the 18-char screen, else the short one."""
    return long if okstr(long, 18) else short

def english(g):
    out = []
    win = {1:(0,12),2:(6,20),3:(12,26),4:(18,32),5:(23,35)}[g]
    for w, o in OPP[win[0]:win[1]]:
        d = pick2(o, w, OPP_WORDS[stable_rot(g, w):] + OPP_WORDS)
        if d: out.append(mk(fit(f"Opposite of {w}?", f"Opp of {w}?"), o, d, "The opposite word"))
    pl = {1:PLURALS[:6],2:PLURALS[4:12],3:PLURALS[9:16],4:PLURALS[13:20],5:PLURALS[15:]}[g]
    for s, p in pl:
        d = pick2(p, "", [s, s+"s", s+"es", s+"z"])
        if d: out.append(mk(fit(f"Plural of {s}?", f"Many {s}?"), p, d, "More than one"))
    if g >= 2:
        pa = {2:PAST[:5],3:PAST[4:10],4:PAST[9:14],5:PAST[13:]}.get(g, [])
        for v, pt in pa:
            d = pick2(pt, "", [v+"ed", v+"s", v])
            if d: out.append(mk(f"Past of {v}?", pt, d, "Yesterday word"))
    # rhymes (easy grades)
    if g <= 3:
        for grp in RHYME_GROUPS:
            w, r = grp[0], grp[1]
            others = [x[0] for x in RHYME_GROUPS if x[0] != w]
            d = pick2(r, w, others)
            if d: out.append(mk(fit(f"Rhymes with {w}?", f"Rhymes {w}?"), r, d, "Same end sound"))
    return [q for q in out if q]

def science(g):
    out = []
    # different animals per grade (these used to repeat in every grade)
    babies = {1:BABIES[0:5], 2:BABIES[2:8], 3:BABIES[5:11], 4:BABIES[8:14], 5:BABIES[9:15]}[g]
    for a, b in babies:
        out.append(mk(fit(f"Baby of a {a}?", f"Baby of {a}?"), b, pick2(b, a, BABY_WORDS), "Young animal"))
    facts = {
        1:[("Cow says?","moo",["baa","woof"]),("Dog says?","woof",["moo","oink"]),
           ("Cat says?","meow",["moo","baa"]),("We breathe?","air",["sand","mud"]),
           ("Fish live in?","water",["sand","air"]),("Bird can?","fly",["swim","dig"]),
           ("Legs on a dog?","4",["2","6"]),("Sun gives?","light",["rain","snow"])],
        2:[("Bees make?","honey",["milk","web"]),("Spider legs?","8",["6","4"]),
           ("Birds lay?","eggs",["milk","cubs"]),("Cows give?","milk",["eggs","honey"]),
           ("Snow is?","cold",["hot","dry"]),("Plants need?","sun",["dark","snow"]),
           ("Snail is?","slow",["fast","loud"]),("Bat flies at?","night",["noon","dawn"])],
        3:[("Sun rises in?","east",["west","north"]),("Water freezes to?","ice",["steam","sand"]),
           ("Insect legs?","6",["8","4"]),("Frog baby?","tadpole",["chick","cub"]),
           ("Blood is?","red",["blue","green"]),("Trees give?","oxygen",["smoke","sand"]),
           ("Bee home?","hive",["nest","den"]),("Bird home?","nest",["hive","web"])],
        4:[("Planet we live?","Earth",["Mars","Sun"]),("Star at center?","Sun",["Moon","Mars"]),
           ("We see with?","eyes",["ears","nose"]),("Heart pumps?","blood",["air","water"]),
           ("Water formula?","H2O",["CO2","O2"]),("Closest star?","Sun",["Mars","Moon"]),
           ("Bones make a?","body",["car","tree"]),("Fish breathe with?","gills",["lungs","skin"])],
        5:[("Largest planet?","Jupiter",["Mars","Earth"]),("Red planet?","Mars",["Earth","Sun"]),
           ("Sun is a?","star",["moon","planet"]),("Lungs are for?","air",["food","blood"]),
           ("Moon orbits?","Earth",["Sun","Mars"]),("Speed of?","light",["sound","wind"]),
           ("Ice is frozen?","water",["milk","air"]),("Bee wings?","2",["4","6"])],
    }[g]
    for t in facts:
        out.append(mk(t[0], t[1], t[2], "Nature fact"))
    return [q for q in out if q]

def gk(g):
    facts = {
        1:[("Days in a week?",7,"Seven days"),("How many fingers?",10,"Ten"),
           ("Colors in rainbow?",7,"Seven"),("Eyes on a face?",2,"Two eyes"),
           ("Legs on a person?",2,"Two legs"),("Wheels on a car?",4,"Four"),
           ("Thumbs on hands?",2,"One each")],
        2:[("Months in a year?",12,"Twelve"),("Days in weekend?",2,"Sat Sun"),
           ("Hours in a day?",24,"Twenty four"),("Days in a week?",7,"Seven"),
           ("Half of a dozen?",6,"Dozen is 12"),("Legs on 2 cats?",8,"4 and 4")],
        3:[("Seasons in year?",4,"Four"),("Minutes in hour?",60,"Sixty"),
           ("Days in Sept?",30,"Thirty"),("Weeks in a year?",52,"Fifty two"),
           ("Months in year?",12,"Twelve"),("Hours half day?",12,"Twelve")],
        4:[("Days in a year?",365,"365"),("Seconds in min?",60,"Sixty"),
           ("Sides of a dice?",6,"A cube"),("Oceans on Earth?",5,"Five"),
           ("Continents?",7,"Seven"),("Days in leap yr?",366,"One more")],
        5:[("Years in decade?",10,"Ten"),("Years in century?",100,"Hundred"),
           ("Days in 2 weeks?",14,"7 and 7"),("Minutes half hr?",30,"Thirty"),
           ("Hours in 2 days?",48,"24 and 24"),("Sides on a cube?",6,"A box")],
    }[g]
    return [q for q in (num(t, c, h, spread(c)) for t, c, h in facts) if q]

def shapes(g):
    SIDES = [("triangle",3),("square",4),("pentagon",5),("hexagon",6),
             ("rectangle",4),("octagon",8),("heptagon",7),("nonagon",9),("decagon",10)]
    win = {1:(0,3),2:(0,6),3:(3,8),4:(5,10),5:(6,10)}[g]
    out = []
    for name, s in SIDES[win[0]:win[1]]:
        # Proper wording that still fits the 18-char box: prefer the full
        # "Sides of a hexagon?"; fall back to "Hexagon sides?" for longer names.
        q = f"Sides of a {name}?"
        if not okstr(q, 18):
            q = f"{name.capitalize()} sides?"
        if okstr(q, 18):
            out.append(num(q, s, "Count the sides", spread(s)))
    COLORS = [("Red and blue?","purple",["green","pink"]),
              ("Blue and yellow?","green",["purple","brown"]),
              ("Red and yellow?","orange",["green","blue"]),
              ("Red and white?","pink",["grey","blue"]),
              ("Black and white?","grey",["pink","brown"])]
    cwin = {1:2,2:3,3:4,4:5,5:5}[g]
    for t in COLORS[:cwin]:
        out.append(mk(t[0], t[1], t[2], "Mix colors"))
    extra = {
        4:[("Cube has faces?",6,"Six"),("Right angle deg?",90,"Ninety")],
        5:[("Circle degrees?",360,"Full turn"),("Cube has edges?",12,"Twelve"),
           ("Triangle angles?",3,"Three")],
    }.get(g, [])
    for t in extra:
        out.append(num(t[0], t[1], t[2], spread(t[1])))
    return [q for q in out if q]

# ===================== math builders (large pools) =====================
def math(g):
    out = []
    def U(qs):
        for q in qs:
            if q: out.append(q)
    if g == 1:
        U(num(f"{a} plus {b}?", a+b, f"Count from {a}", smart('+',a,b,a+b)) for a in range(1,10) for b in range(1,10) if a+b<=12)
        U(num(f"{a} - {b}?", a-b, f"{b} less than {a}", smart('-',a,b,a-b)) for a in range(2,13) for b in range(1,a) if a-b<=9)
        U(num(f"{a} plus {a}?", a+a, f"Double {a}", smart('+',a,a,a+a)) for a in range(2,7))
        U([num("Next: 1 2 3 ?",4,"Count by 1",[5,3]),num("Next: 2 4 6 ?",8,"By 2s",[10,7]),
           num("Next: 5 6 7 ?",8,"Count by 1",[9,6]),num("Next: 3 4 5 ?",6,"Count by 1",[7,4])])
    elif g == 2:
        U(num(f"{a} plus {b}?", a+b, "Tens then ones", smart('+',a,b,a+b)) for a in range(11,60,7) for b in range(6,40,9) if a+b<=99)
        U(num(f"{a} - {b}?", a-b, "Tens then ones", smart('-',a,b,a-b)) for a in range(20,95,8) for b in range(7,40,6) if a-b>0)
        U(num(f"Tens in {t}0?", t, f"{t}0 is {t} tens", spread(t)) for t in range(2,10))
        U(num(f"{a} plus {a}?", a+a, f"Double {a}", smart('+',a,a,a+a)) for a in range(6,15))
    elif g == 3:
        U(num(f"{a} x {b}?", a*b, f"{a} groups of {b}", smart('x',a,b,a*b)) for a in range(2,10) for b in range(2,10) if a<=b)
        U(num(f"{a*b} / {b}?", a, f"{b} x what is {a*b}", smart('/',a*b,b,a)) for b in range(2,10) for a in range(2,7))
        U(num(f"Half of {n}?", n//2, f"Split {n}", spread(n//2)) for n in range(10,31,2))
    elif g == 4:
        U(num(f"{a} x {b}?", a*b, "Break it up", smart('x',a,b,a*b)) for a in range(11,16) for b in range(4,10))
        U(num(f"{a*b} / {b}?", a, f"{b} x what is {a*b}", smart('/',a*b,b,a)) for b in (6,8,9,11,12) for a in (9,11,12))
        U([mk("2/4 equals?","1/2",["1/3","1/4"],"Halve both"),mk("3/6 equals?","1/2",["1/3","2/6"],"Halve both"),
           mk("3/4 of 8?",6,[5,7],"8 /4 x3"),mk("1/2 of 10?",5,[4,6],"Split 10"),
           mk("Half of 1.0?","0.5",["0.2","5.0"],"Split 1.0"),mk("0.5 plus 0.5?","1.0",["0.5","1.5"],"Two halves")])
    else:
        U(num(f"{a} plus {b} x {c}?", a+b*c, "Times before plus", _two(a+b*c, [(a+b)*c, a+b+c, a+b*c+1])) for a in (2,5,1,4,7,3) for b in (2,3) for c in (3,4,5) if a+b*c<100)
        U(num(f"{a} - {b} x {c}?", a-b*c, "Times first", _two(a-b*c, [(a-b)*c, a-b-c, a-b*c+1])) for a in (10,20,15,12,18) for b in (2,3) for c in (2,3,4) if a-b*c>0)
        U([mk("0.6 plus 0.7?","1.3",["1.2","0.13"],"Add tenths"),mk("0.4 plus 0.5?","0.9",["0.8","1.0"],"Add tenths"),
           mk("3/4 plus 1/4?","1",["4/8","2"],"Add tops"),mk("1/2 plus 1/4?","3/4",["1/4","2/4"],"1/2 is 2/4"),
           mk("Round 4.7?",5,[4,6],".5 goes up"),mk("Round 5.5?",6,[5,7],".5 goes up"),
           mk("Round 3.2?",3,[4,2],"Under .5"),mk("Round 8.9?",9,[8,10],"Near 9")])
    return out

# ===================== assemble ~100/grade, balanced =====================
def dedupe(qs):
    seen, out = set(), []
    for q in qs:
        if q and q.text not in seen:
            seen.add(q.text); out.append(q)
    return out

banks = {g: [] for g in range(1, 6)}
subject_of = {}  # (grade, question_text) -> subject name; for the content audit
SUBJECT_CAPS = (("English", english, 20), ("Science & Nature", science, 20),
                ("General Knowledge", gk, 20), ("Shapes & Colors", shapes, 20))
for g in range(1, 6):
    tagged = []  # (Q, subject) in emit order, before the final cross-dedupe
    for sname, builder, cap in SUBJECT_CAPS:
        tagged += [(q, sname) for q in dedupe(builder(g))[:cap]]
    need = TARGET - len(dedupe([q for q, _ in tagged]))
    tagged += [(q, "Math") for q in dedupe(math(g))[:max(need, 0)]]
    # Final dedupe keeping the first occurrence (matches the original pipeline),
    # capped at TARGET, while recording each surviving question's subject.
    seen, final = set(), []
    for q, sname in tagged:
        if q.text in seen:
            continue
        seen.add(q.text); final.append(q); subject_of[(g, q.text)] = sname
        if len(final) == TARGET:
            break
    banks[g] = final


def emit():
    L = []
    w = L.append
    w("; ============================================================================")
    w("; Quiz Battle - multi-subject question banks (grades 1-5)")
    w("; ----------------------------------------------------------------------------")
    w("; GENERATED by tools_gen_quiz.py -- edit that script and re-run it, then `make`.")
    w("; Each grade's data lives in its own ROM bank; the engine copies a chosen")
    w("; question into RAM before showing it (see QuizLoadQuestion).")
    w("; ============================================================================")
    w("")
    w("; One question entry (14 bytes):")
    w(";   quizq QUESTION, CORRECT_INDEX(0-3), NUM_ANSWERS(2-4), ANS0, ANS1, ANS2, ANS3, HINT")
    w("MACRO quizq")
    w("\tdw \\1")
    w("\tdb \\2")
    w("\tdb \\3")
    w("\tdw \\4, \\5, \\6, \\7")
    w("\tdw \\8")
    w("ENDM")
    w("")
    w("QuizGradeTable::")
    for g in range(1, 6):
        w(f"\tdw Grade{g}Questions")
        w(f"\tdb {len(banks[g])}")
        w(f"\tdb BANK(Grade{g}Questions)")
    w("")
    w("; ---- result messages (shown via PrintText) ----")
    w("QuizCorrectText::")
    w('\ttext "Great job!"')
    w('\tline "Streak "')
    w("\ttext_ram wStringBuffer")
    w("\tprompt")
    w("")
    w("QuizTryAgainText::")
    w('\ttext "Hint:"')
    w('\tline ""')
    w("\ttext_ram wStringBuffer")
    w('\tcont "Try once more!"')
    w("\tprompt")
    w("")
    w("QuizMissText::")
    w('\ttext "The answer was"')
    w('\tline ""')
    w("\ttext_ram wStringBuffer")
    w('\tcont "Now you know!"')
    w("\tprompt")
    w("")
    for g in range(1, 6):
        w(f'SECTION "Quiz Data G{g}", ROMX')
        w(f"Grade{g}Questions::")
        for i, q in enumerate(banks[g], 1):
            p = f"G{g}Q{i}"
            w(f"\tquizq {p}, 0, 3, {p}A, {p}B, {p}C, {p}C, {p}H")
        for i, q in enumerate(banks[g], 1):
            p = f"G{g}Q{i}"
            w(f'{p}: db "{q.text}@"')
            w(f'{p}A: db "{q.answers[0]}@"')
            w(f'{p}B: db "{q.answers[1]}@"')
            w(f'{p}C: db "{q.answers[2]}@"')
            w(f'{p}H: db "{q.hint}@"')
        w("")
    return "\n".join(L)


if __name__ == "__main__":
    text = emit()
    with open(OUT, "w") as f:
        f.write(text)
    print("wrote", OUT)
    print("counts:", {g: len(v) for g, v in banks.items()}, "total", sum(len(v) for v in banks.values()))
