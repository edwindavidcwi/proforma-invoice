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
