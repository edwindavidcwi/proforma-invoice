#!/usr/bin/env python3
# Reuses the existing 771-question bank (game/pokered/tools_gen_quiz.py) and
# emits it as an ES module the v2 engine + audit harness + browser game all
# import the same way. Run from game/v2/:  python3 tools/gen_questions.py
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
POKERED = os.path.normpath(os.path.join(HERE, "..", "..", "pokered"))
sys.path.insert(0, POKERED)
import tools_gen_quiz as T  # the source of truth for questions

out = []
for grade in (1, 2, 3, 4, 5):
    for q in T.banks[grade]:
        out.append({
            "grade": grade,
            "subject": T.subject_of[(grade, q.text)],
            "text": q.text,
            # correct answer first (the engine shuffles for display)
            "answers": list(q.answers),
            "correct": q.correct,
            "hint": q.hint,
            "clock": int(getattr(q, "clock", 0) or 0),
        })

dst = os.path.join(HERE, "..", "core", "questions.js")
os.makedirs(os.path.dirname(dst), exist_ok=True)
with open(dst, "w", encoding="utf-8") as f:
    f.write("// AUTO-GENERATED from game/pokered/tools_gen_quiz.py -- do not edit by hand.\n")
    f.write("// Reuses the exact 771-question bank shared with v1 and the Parent Pack.\n")
    f.write("export const QUESTIONS = ")
    json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    f.write(";\n")
print("wrote core/questions.js  (%d questions)" % len(out))
