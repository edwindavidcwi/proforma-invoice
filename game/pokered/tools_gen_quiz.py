#!/usr/bin/env python3
"""Generate engine/battle/quiz_data.asm with a large, correct question bank.

Every question has: text (<=18 chars), 3 answers (<=9 chars each), the correct
index, and a method hint (<=18 chars). Numeric questions get auto distractors;
fraction/decimal/rounding questions are hand-authored. The on-screen answer
order is randomized at runtime by the engine, so the data order is fine.
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "engine", "battle", "quiz_data.asm")

ALLOWED = set("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz "
              "-/x.:?!")

def ok(s, n):
    assert all(c in ALLOWED for c in s), f"bad char in {s!r}"
    assert len(s) <= n, f"too long ({len(s)}>{n}): {s!r}"
    return s

class Q:
    def __init__(self, text, correct, distractors, hint):
        self.text = ok(text, 18)
        self.hint = ok(hint, 18)
        ans = [str(correct)] + [str(d) for d in distractors]
        for a in ans:
            ok(a, 9)
        assert len(set(ans)) == len(ans), f"dup answers {ans} for {text!r}"
        self.answers = ans          # answers[0] is the correct one
        self.correct = str(correct)

def num(text, correct, hint, distractors=None):
    """A whole-number question; auto distractors = correct +/- 1 (or +1,+2)."""
    if distractors is None:
        c = int(correct)
        distractors = [c - 1, c + 1] if c >= 1 else [c + 1, c + 2]
    return Q(text, correct, distractors, hint)

banks = {1: [], 2: [], 3: [], 4: [], 5: []}

# ---------------- Grade 1: add/sub within ~20, counting, doubles ----------
seen = set()
for a in range(1, 10):
    for b in range(1, 10):
        if a + b <= 10 and (a, b, '+') not in seen and len(banks[1]) < 40:
            seen.add((a, b, '+'))
            banks[1].append(num(f"{a} plus {b}?", a + b, f"Count on from {a}"))
for a in range(3, 11):
    for b in range(1, a):
        banks[1].append(num(f"{a} - {b}?", a - b, f"{b} less than {a}"))
for a in range(2, 6):
    banks[1].append(num(f"{a} plus {a}?", a + a, f"Double of {a}"))
banks[1] += [
    num("Next: 1 2 3 ?", 4, "Count by 1"),
    num("Next: 3 4 5 ?", 6, "Count by 1"),
    num("Next: 2 4 6 ?", 8, "Skip count by 2"),
    num("Next: 5 6 7 ?", 8, "Count by 1"),
    num("1 more than 9?", 10, "Count on 1"),
]

# ---------------- Grade 2: add/sub within 100, place value ----------------
g2_pairs = [(14, 8), (23, 9), (36, 7), (45, 6), (28, 14), (52, 19), (33, 27),
            (40, 35), (17, 18), (60, 25)]
for a, b in g2_pairs:
    if a + b <= 99:
        banks[2].append(num(f"{a} plus {b}?", a + b, "Add tens then ones"))
for a, b in [(30, 12), (50, 25), (62, 17), (45, 19), (80, 36), (74, 8), (90, 45)]:
    banks[2].append(num(f"{a} - {b}?", a - b, "Tens then ones"))
for t in (2, 3, 4, 5, 6, 7, 8, 9):
    banks[2].append(num(f"Tens in {t}0?", t, f"{t}0 is {t} tens"))
for a in (6, 7, 8, 9):
    banks[2].append(num(f"{a} plus {a}?", a + a, f"Double of {a}"))
for n in (4, 5, 6):
    banks[2].append(num(f"Add three {n}s", n * 3, f"{n} plus {n} plus {n}"))

# ---------------- Grade 3: x and / facts, halves -------------------------
for a in range(2, 10):
    for b in range(2, 10):
        if a <= b and len(banks[3]) < 40:
            banks[3].append(num(f"{a} x {b}?", a * b, f"{a} groups of {b}"))
for a, b in [(24, 4), (36, 6), (42, 7), (48, 8), (54, 9), (63, 9), (40, 5), (56, 8)]:
    banks[3].append(num(f"{a} / {b}?", a // b, f"{b} x what is {a}"))
for n in (10, 12, 14, 16, 18, 20):
    banks[3].append(num(f"Half of {n}?", n // 2, f"Split {n} in two"))

# ---------------- Grade 4: bigger x and /, fractions, decimals -----------
for a, b in [(11, 11), (12, 12), (13, 11), (11, 9), (12, 8), (15, 6), (14, 5), (11, 7)]:
    banks[4].append(num(f"{a} x {b}?", a * b, f"Break {b} apart"))
for a, b in [(144, 12), (100, 4), (121, 11), (90, 6), (96, 8), (132, 12)]:
    banks[4].append(num(f"{a} / {b}?", a // b, f"{b} x what is {a}"))
banks[4] += [
    Q("2/4 equals?", "1/2", ["1/3", "1/4"], "Top and bottom /2"),
    Q("3/6 equals?", "1/2", ["1/3", "2/6"], "Both halve to 1/2"),
    Q("3/4 of 8?", 6, [5, 7], "8 /4 then x3"),
    Q("1/2 of 10?", 5, [4, 6], "Split 10 in two"),
    Q("Half of 1.0?", "0.5", ["0.2", "5.0"], "1.0 split in two"),
    Q("Half of 5.0?", "2.5", ["2.0", "3.0"], "5.0 split in two"),
    Q("0.5 plus 0.5?", "1.0", ["0.5", "1.5"], "Two halves make 1"),
]

# ---------------- Grade 5: order of ops, decimals, fractions, rounding ---
for a, b, c in [(2, 3, 4), (5, 2, 3), (1, 6, 2), (4, 4, 2), (7, 2, 5)]:
    banks[5].append(num(f"{a} plus {b} x {c}?", a + b * c, "Times before plus"))
for a, b, c in [(10, 2, 3), (20, 3, 4), (15, 2, 2), (12, 1, 5)]:
    banks[5].append(num(f"{a} - {b} x {c}?", a - b * c, "Times first"))
banks[5] += [
    Q("0.6 plus 0.7?", "1.3", ["1.2", "0.13"], "Add tenths 6 and 7"),
    Q("0.4 plus 0.5?", "0.9", ["0.8", "1.0"], "Add the tenths"),
    Q("0.8 plus 0.3?", "1.1", ["1.0", "0.11"], "Add tenths 8 and 3"),
    Q("3/4 plus 1/4?", "1", ["4/8", "2"], "Add tops: 3 plus 1"),
    Q("1/2 plus 1/4?", "3/4", ["1/4", "2/4"], "1/2 is 2/4"),
    Q("2/5 plus 1/5?", "3/5", ["3/10", "1/5"], "Add tops: 2 plus 1"),
    Q("Round 4.7?", 5, [4, 6], ".5 or more goes up"),
    Q("Round 5.5?", 6, [5, 7], ".5 rounds up"),
    Q("Round 3.2?", 3, [4, 2], "Under .5 stays"),
    Q("Round 8.9?", 9, [8, 10], "Close to 9"),
]

# ---------------- Other subjects (mixed into each grade, grade-scaled) ----
def add(g, text, correct, distractors, hint):
    banks[g].append(Q(text, correct, distractors, hint))

# English / words
add(1, "Opposite of big?", "small", ["tall", "fat"], "Tiny not big")
add(1, "Opposite of hot?", "cold", ["warm", "wet"], "Think of ice")
add(1, "Many cat?", "cats", ["cat", "cates"], "Add s")
add(1, "Opposite of up?", "down", ["top", "in"], "Not up is down")
add(1, "Rhymes with cat?", "hat", ["dog", "sun"], "Ends in -at")
add(1, "Apple starts?", "A", ["B", "P"], "A is first")
add(2, "Opposite of fast?", "slow", ["quick", "run"], "Not fast")
add(2, "Many baby?", "babies", ["babys", "baby"], "y to ies")
add(2, "Past of run?", "ran", ["runned", "runs"], "run to ran")
add(2, "Opposite of happy?", "sad", ["glad", "mad"], "Feeling down")
add(2, "Rhymes with star?", "car", ["sun", "cat"], "Ends in -ar")
add(3, "Plural of mouse?", "mice", ["mouses", "mouse"], "mouse to mice")
add(3, "Opposite of empty?", "full", ["open", "soft"], "Not empty")
add(3, "Past of go?", "went", ["goed", "gone"], "go to went")
add(4, "Plural of child?", "children", ["childs", "childes"], "Not childs")
add(4, "Opp of old?", "new", ["big", "wet"], "Fresh and new")
add(4, "Past of buy?", "bought", ["buyed", "buys"], "buy to bought")
add(5, "Plural of leaf?", "leaves", ["leafs", "leaf"], "f to ves")
add(5, "Opp of brave?", "afraid", ["bold", "strong"], "Not brave")
add(5, "Past of teach?", "taught", ["teached", "teachs"], "teach to taught")

# Science & Nature
add(1, "Baby of a dog?", "puppy", ["kitten", "calf"], "Dogs: puppies")
add(1, "Baby of a cat?", "kitten", ["puppy", "cub"], "Cats: kittens")
add(1, "Cow says?", "moo", ["baa", "woof"], "Moo!")
add(1, "Legs on a dog?", 4, [2, 6], "Count: 4")
add(1, "We breathe?", "air", ["water", "sand"], "In the air")
add(2, "Legs on a spider?", 8, [6, 4], "Spiders: 8")
add(2, "Bees make?", "honey", ["milk", "web"], "Sweet honey")
add(2, "Baby of a frog?", "tadpole", ["puppy", "chick"], "Tadpole!")
add(2, "Birds lay?", "eggs", ["milk", "cubs"], "Eggs in nests")
add(3, "Sun rises in?", "east", ["west", "north"], "E for sunrise")
add(3, "Plants need?", "sun", ["dark", "snow"], "Sunlight")
add(3, "Ice melts to?", "water", ["steam", "snow"], "Melts to water")
add(4, "Planet we live?", "Earth", ["Mars", "Sun"], "Our home")
add(4, "Insect legs?", 6, [8, 4], "Insects: 6")
add(4, "Blood is?", "red", ["blue", "green"], "Red blood")
add(5, "Star at center?", "Sun", ["Moon", "Mars"], "The Sun")
add(5, "Largest planet?", "Jupiter", ["Mars", "Earth"], "Giant Jupiter")

# General Knowledge
add(1, "Days in a week?", 7, [5, 10], "Seven days")
add(1, "Colors in rainbow", 7, [5, 3], "Seven colors")
add(1, "How many fingers?", 10, [8, 12], "Ten fingers")
add(2, "Months in a year?", 12, [10, 7], "Twelve")
add(2, "Days in weekend?", 2, [1, 3], "Sat and Sun")
add(2, "Hours in a day?", 24, [12, 10], "Twenty four")
add(3, "Seasons in year?", 4, [2, 3], "Four seasons")
add(3, "Minutes in hour?", 60, [30, 100], "Sixty")
add(4, "Days in a year?", 365, [360, 100], "365 days")
add(4, "Seconds in min?", 60, [100, 30], "Sixty")
add(5, "Years in decade?", 10, [5, 100], "Ten years")
add(5, "Years in century", 100, [10, 50], "One hundred")

# Shapes & Colors
add(1, "Sides on triangle", 3, [4, 5], "Tri means 3")
add(1, "Sides on square?", 4, [3, 5], "Four sides")
add(1, "Red and blue make", "purple", ["green", "pink"], "Purple!")
add(2, "Sides on hexagon?", 6, [5, 8], "Hexa means 6")
add(2, "Blue and yellow?", "green", ["purple", "orange"], "Green!")
add(2, "A ball is a?", "circle", ["square", "star"], "Round is circle")
add(3, "Sides on pentagon", 5, [6, 4], "Penta means 5")
add(3, "Red and yellow?", "orange", ["green", "purple"], "Orange!")
add(3, "Sides on octagon?", 8, [6, 10], "Octa means 8")
add(4, "Angles in triangle", 3, [4, 2], "Three angles")
add(4, "A cube has faces?", 6, [4, 8], "Six faces")
add(5, "Right angle deg?", 90, [45, 180], "Ninety deg")
add(5, "Circle degrees?", 360, [180, 90], "360 round")


def emit():
    L = []
    w = L.append
    w("; ============================================================================")
    w("; Quiz Battle - question banks (grades 1-5)")
    w("; ----------------------------------------------------------------------------")
    w("; GENERATED by tools_gen_quiz.py -- edit that script and re-run it, then `make`.")
    w("; Font has NO =,+,% ; use words (\"plus\") and  - / x . : ? !  only.")
    w("; Question text <= 18 chars, each answer <= 9, each hint <= 18.")
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
        if g < 5:
            w(f"\tdb (Grade{g+1}Questions - Grade{g}Questions) / 14")
        else:
            w(f"\tdb (QuestionsEnd - Grade5Questions) / 14")
    w("")
    # entry tables
    for g in range(1, 6):
        w(f"Grade{g}Questions::")
        for i, q in enumerate(banks[g], 1):
            p = f"G{g}Q{i}"
            # data order: correct first (index 0), then distractors; engine rotates
            a = [f"{p}A", f"{p}B", f"{p}C"]
            w(f"\tquizq {p}, 0, 3, {a[0]}, {a[1]}, {a[2]}, {a[2]}, {p}H")
    w("QuestionsEnd::")
    w("")
    # strings
    w("; ---- strings ----")
    for g in range(1, 6):
        w(f"; Grade {g}")
        for i, q in enumerate(banks[g], 1):
            p = f"G{g}Q{i}"
            w(f'{p}: db "{q.text}@"')
            w(f'{p}A: db "{q.answers[0]}@"')
            w(f'{p}B: db "{q.answers[1]}@"')
            w(f'{p}C: db "{q.answers[2]}@"')
            w(f'{p}H: db "{q.hint}@"')
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
    return "\n".join(L)

text = emit()
with open(OUT, "w") as f:
    f.write(text)
total = sum(len(v) for v in banks.values())
print("wrote", OUT)
print("counts:", {g: len(v) for g, v in banks.items()}, "total", total)
