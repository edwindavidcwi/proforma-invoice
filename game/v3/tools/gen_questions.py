#!/usr/bin/env python3
# Reuses the existing 771-question bank (game/pokered/tools_gen_quiz.py) as an
# ES module the v3 engine + audit + browser game all import.  python3 gen_questions.py
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..", "..", "pokered")))
import tools_gen_quiz as T

out = []
for g in (1, 2, 3, 4, 5):
    for q in T.banks[g]:
        out.append({"grade": g, "subject": T.subject_of[(g, q.text)], "text": q.text,
                    "answers": list(q.answers), "correct": q.correct,
                    "hint": q.hint, "clock": int(getattr(q, "clock", 0) or 0)})
dst = os.path.join(HERE, "..", "engine", "questions.js")
os.makedirs(os.path.dirname(dst), exist_ok=True)
with open(dst, "w", encoding="utf-8") as f:
    f.write("// AUTO-GENERATED from game/pokered/tools_gen_quiz.py -- the 771-question bank.\n")
    f.write("export const QUESTIONS = " + json.dumps(out, ensure_ascii=False, separators=(",", ":")) + ";\n")
print("wrote engine/questions.js (%d questions)" % len(out))
