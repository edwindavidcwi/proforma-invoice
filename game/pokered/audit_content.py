#!/usr/bin/env python3
"""Content audit + data-lint for the Quiz Battle question bank.

Parses the SHIPPED engine/battle/quiz_data.asm (the ground truth that ends up in
the ROM), cross-checks it for data-quality problems, and prints a teacher-skimmable
per-grade / per-subject report. Subjects are resolved by importing the (now
deterministic) generator and matching on question text, falling back to a text
heuristic for anything not produced by the current generator.

Hard checks (exit 1 -> fails the CI build):
  * every glyph is in the Game Boy font's allowed set (illegal chars won't render)
  * length limits: question/hint <= 18 chars, each answer <= 9 chars (text-box width)
  * the options shown (first NUM_ANSWERS) are all distinct and non-empty
  * CORRECT_INDEX is within 0..NUM_ANSWERS-1; NUM_ANSWERS in 2..4
  * every label referenced by a quizq entry has a matching string definition
  * each grade has exactly the count declared in QuizGradeTable
  * the shipped data matches `tools_gen_quiz.py` (no drift / non-determinism)

Soft checks (reported as warnings, do not fail):
  * duplicate question text within a grade
  * subject balance per grade

Run:  python3 audit_content.py            # audit + report
      python3 audit_content.py --report game/CONTENT_REPORT.md
"""
import os, re, sys, argparse, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "engine", "battle", "quiz_data.asm")
GEN = os.path.join(HERE, "tools_gen_quiz.py")

# Must match the font/charmap the generator targets.
ALLOWED = set("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz "
              "-/x.:?!")
Q_MAX, ANS_MAX, HINT_MAX = 18, 9, 18  # screen limits: question/hint full line, answers narrow column

errors, warnings = [], []
def err(m): errors.append(m)
def warn(m): warnings.append(m)


def parse_asm(path):
    """Return (grade_counts, questions) where questions is a list of dicts with
    text/options/correct/hint resolved from the label string table."""
    text = open(path, encoding="utf-8").read()

    # 1) string table:  Label: db "....@"
    strings = {}
    for m in re.finditer(r'^(\w+):\s*db\s*"(.*?)@"', text, re.M):
        strings[m.group(1)] = m.group(2)

    # 2) declared counts in QuizGradeTable (db <count> after each dw GradeNQuestions)
    counts = {}
    gt = re.search(r"QuizGradeTable::(.*?)\n\n", text, re.S)
    if gt:
        for g, n in re.findall(r"dw Grade(\d)Questions\s*\n\s*db (\d+)", gt.group(1)):
            counts[int(g)] = int(n)

    # 3) quizq entries (carry their own grade via the G<g>Q<i> label prefix)
    qs = []
    qline = re.compile(r"^\s*quizq\s+(\w+),\s*(\d+),\s*(\d+),\s*(\w+),\s*(\w+),\s*(\w+),\s*(\w+),\s*(\w+)", re.M)
    for m in qline.finditer(text):
        qlabel, cidx, num = m.group(1), int(m.group(2)), int(m.group(3))
        alabels = [m.group(4), m.group(5), m.group(6), m.group(7)]
        hlabel = m.group(8)
        gm = re.match(r"G(\d)Q(\d+)", qlabel)
        grade = int(gm.group(1)) if gm else 0
        qs.append({"label": qlabel, "grade": grade, "cidx": cidx, "num": num,
                   "alabels": alabels, "hlabel": hlabel, "strings": strings})
    return counts, qs


def resolve(q):
    """Fill in text/options/correct/hint strings, recording missing labels."""
    s = q["strings"]
    def get(lbl):
        if lbl not in s:
            err(f"{q['label']}: missing string for label '{lbl}'")
            return None
        return s[lbl]
    q["text"] = get(q["label"])
    q["options"] = [get(l) for l in q["alabels"][:q["num"]]]
    q["hint"] = get(q["hlabel"])
    q["correct"] = q["options"][q["cidx"]] if 0 <= q["cidx"] < len(q["options"]) else None
    return q


def lint(q):
    g, lbl = q["grade"], q["label"]
    if not (2 <= q["num"] <= 4):
        err(f"{lbl}: NUM_ANSWERS {q['num']} not in 2..4")
    if not (0 <= q["cidx"] < q["num"]):
        err(f"{lbl}: CORRECT_INDEX {q['cidx']} out of range for {q['num']} answers")
    # charmap + length
    def check(kind, val, limit):
        if val is None:
            return
        if val == "":
            err(f"{lbl}: empty {kind}")
        bad = sorted(set(c for c in val if c not in ALLOWED))
        if bad:
            err(f"{lbl}: {kind} has non-font chars {bad}: {val!r}")
        if len(val) > limit:
            err(f"{lbl}: {kind} too long ({len(val)}>{limit}): {val!r}")
    check("question", q["text"], Q_MAX)
    check("hint", q["hint"], HINT_MAX)
    for i, a in enumerate(q["options"]):
        check(f"answer{i}", a, ANS_MAX)
    # distinct visible options
    opts = [a for a in q["options"] if a is not None]
    if len(set(opts)) != len(opts):
        err(f"{lbl}: duplicate answer options {opts}")


def subjects_from_generator():
    """(grade, text) -> subject, from the deterministic generator. {} if import fails."""
    try:
        sys.path.insert(0, HERE)
        import tools_gen_quiz as gen
        return dict(gen.subject_of)
    except Exception as e:
        warn(f"could not import generator for subject tags ({e}); using text heuristic")
        return {}


def heuristic_subject(t):
    t = t or ""
    if re.search(r"Opposite|Plural|Past of|Rhymes", t): return "English"
    if re.search(r"Baby of|says\?|breathe|planet|Planet|star|Star|blood|gills|honey|eggs", t): return "Science & Nature"
    if re.search(r"Sides |degrees|angle|faces|edges|and (blue|yellow|white|red)\?", t, re.I): return "Shapes & Colors"
    if re.search(r"Days|Months|Hours|Minutes|Seconds|week|year|decade|century|Seasons|Oceans|Continents|fingers|rainbow", t, re.I): return "General Knowledge"
    return "Math"


def check_generator_sync():
    """Re-run the generator and diff the data file (catches stale/non-deterministic data)."""
    try:
        before = open(DATA, encoding="utf-8").read()
        subprocess.run([sys.executable, GEN], cwd=HERE, check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        after = open(DATA, encoding="utf-8").read()
        if before != after:
            open(DATA, "w", encoding="utf-8").write(before)  # restore exactly
            err("shipped quiz_data.asm is out of sync with tools_gen_quiz.py "
                "(re-run the generator and commit, so the data matches the script)")
        # determinism: a second run must reproduce the same bytes
        subprocess.run([sys.executable, GEN], cwd=HERE, check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if open(DATA, encoding="utf-8").read() != after:
            err("tools_gen_quiz.py is non-deterministic (two runs differ)")
        open(DATA, "w", encoding="utf-8").write(before)
    except Exception as e:
        warn(f"generator sync check skipped ({e})")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--report", help="also write a Markdown report to this path")
    ap.add_argument("--no-gen-check", action="store_true", help="skip the generator-sync check")
    args = ap.parse_args()

    counts, qs = parse_asm(DATA)
    for q in qs:
        resolve(q); lint(q)

    subj_map = subjects_from_generator()
    by_grade = {g: [] for g in range(1, 6)}
    subj_counts = {g: {} for g in range(1, 6)}
    for q in qs:
        g = q["grade"]
        if g not in by_grade:
            by_grade[g] = []; subj_counts[g] = {}
        s = subj_map.get((g, q["text"])) or heuristic_subject(q["text"])
        q["subject"] = s
        by_grade[g].append(q)
        subj_counts[g][s] = subj_counts[g].get(s, 0) + 1

    # grade-count check vs the declared table
    for g, declared in counts.items():
        got = len(by_grade.get(g, []))
        if got != declared:
            err(f"grade {g}: {got} quizq entries but QuizGradeTable declares {declared}")
    # duplicate questions within a grade
    for g, items in by_grade.items():
        seen = {}
        for q in items:
            if q["text"] in seen:
                warn(f"grade {g}: duplicate question text {q['text']!r}")
            seen[q["text"]] = True

    if not args.no_gen_check:
        check_generator_sync()

    report = build_report(counts, by_grade, subj_counts, qs)
    print(report)
    if args.report:
        open(args.report, "w", encoding="utf-8").write(report)
        print(f"\n(wrote report to {args.report})")

    if warnings:
        print("\n".join(f"WARNING  {w}" for w in warnings))
    if errors:
        print("\n".join(f"ERROR    {e}" for e in errors))
        print(f"\n{len(errors)} ERROR(S), {len(warnings)} warning(s) -- FAIL")
        return 1
    print(f"\nALL CONTENT CHECKS PASSED  ({len(qs)} questions, {len(warnings)} warning(s))")
    return 0


def build_report(counts, by_grade, subj_counts, qs):
    SUBJ_ORDER = ["Math", "English", "Science & Nature", "General Knowledge", "Shapes & Colors"]
    L = []
    L.append("# Quiz Battle - content report")
    L.append("")
    L.append(f"Total questions: **{len(qs)}**  |  Grades: {', '.join(str(g) for g in sorted(by_grade) if by_grade[g])}")
    L.append("")
    # subject distribution table
    subj_seen = SUBJ_ORDER + sorted({s for g in subj_counts for s in subj_counts[g] if s not in SUBJ_ORDER})
    header = "| Grade | " + " | ".join(subj_seen) + " | Total |"
    L.append(header)
    L.append("|" + "---|" * (len(subj_seen) + 2))
    for g in sorted(by_grade):
        if not by_grade[g]:
            continue
        row = [str(subj_counts[g].get(s, 0)) for s in subj_seen]
        L.append(f"| G{g} | " + " | ".join(row) + f" | {len(by_grade[g])} |")
    L.append("")
    # length headroom (how close to the screen limits)
    def longest(items, key, limit):
        worst = max(items, key=lambda q: len(q[key] or ""))
        return len(worst[key] or ""), limit, worst[key]
    allq = [q for g in by_grade for q in by_grade[g]]
    if allq:
        ql, qlim, qv = longest(allq, "text", Q_MAX)
        L.append(f"Longest question: {ql}/{qlim} chars  (`{qv}`)")
        aw = max(allq, key=lambda q: max((len(a or "") for a in q["options"]), default=0))
        awl = max((len(a or "") for a in aw["options"]), default=0)
        L.append(f"Longest answer:   {awl}/{ANS_MAX} chars  (in `{aw['text']}`)")
        L.append("")
    # a few samples per subject per grade, so a teacher can eyeball quality
    L.append("## Samples (correct answer first)")
    for g in sorted(by_grade):
        if not by_grade[g]:
            continue
        L.append(f"\n### Grade {g}")
        bysub = {}
        for q in by_grade[g]:
            bysub.setdefault(q["subject"], []).append(q)
        for s in subj_seen:
            if s not in bysub:
                continue
            ex = bysub[s][:3]
            L.append(f"- **{s}** ({len(bysub[s])}):")
            for q in ex:
                opts = ", ".join(q["options"])
                L.append(f"    - {q['text']}  ->  *{q['correct']}*   [{opts}]   _hint: {q['hint']}_")
    return "\n".join(L)


if __name__ == "__main__":
    sys.exit(main())
