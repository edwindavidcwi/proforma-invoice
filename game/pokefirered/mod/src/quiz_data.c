// Educational "Quiz Battle" mod for Pokemon FireRed -- question banks.
//
// To add or change a question: edit the arrays below. Keep question text short
// (it shares a battle window) and answers short (they sit in a small list).
// Strings use the _() macro so the build encodes them with the game font.
// Re-run `make modern` afterwards.

#include "global.h"
#include "quiz_battle.h"

// ---- Grade 1: add/sub within 10, counting ---------------------------------
static const struct QuizQuestion sGrade1[] =
{
    { _("2 plus 3?"),      { _("4"),  _("5"),  _("6")  }, 1, 3 },
    { _("7 minus 4?"),     { _("1"),  _("2"),  _("3")  }, 2, 3 },
    { _("Count: 1 2 3.."), { _("3"),  _("4"),  _("2")  }, 0, 3 },
    { _("6 plus 1?"),      { _("6"),  _("7"),  _("8")  }, 1, 3 },
};

// ---- Grade 2: add/sub within 100, place value -----------------------------
static const struct QuizQuestion sGrade2[] =
{
    { _("14 plus 8?"),     { _("20"), _("21"), _("22") }, 2, 3 },
    { _("30 minus 12?"),   { _("18"), _("19"), _("20") }, 0, 3 },
    { _("Tens in 40?"),    { _("3"),  _("4"),  _("5")  }, 1, 3 },
    { _("5 plus 5 plus 5"),{ _("10"), _("12"), _("15") }, 2, 3 },
};

// ---- Grade 3: multiplication and division facts ---------------------------
static const struct QuizQuestion sGrade3[] =
{
    { _("6 x 7?"),         { _("36"), _("42"), _("48") }, 1, 3 },
    { _("24 / 4?"),        { _("4"),  _("5"),  _("6")  }, 2, 3 },
    { _("8 x 5?"),         { _("40"), _("45"), _("35") }, 0, 3 },
    { _("Half of 18?"),    { _("8"),  _("9"),  _("10") }, 1, 3 },
};

// ---- Grade 4: multi-digit x, decimals, fractions --------------------------
static const struct QuizQuestion sGrade4[] =
{
    { _("12 x 12?"),       { _("124"),_("134"),_("144")}, 2, 3 },
    { _("Half of 1.0?"),   { _("0.5"),_("0.2"),_("5.0")}, 0, 3 },
    { _("144 / 12?"),      { _("11"), _("12"), _("13") }, 1, 3 },
    { _("2/4 is the same"),{ _("1/3"),_("1/4"),_("1/2")}, 2, 3 },
};

// ---- Grade 5: decimal ops, order of operations, rounding ------------------
static const struct QuizQuestion sGrade5[] =
{
    { _("0.6 plus 0.7?"),  { _("1.2"),_("1.3"),_("0.13")},1, 3 },
    { _("2 plus 3 x 4?"),  { _("20"), _("24"), _("14") }, 2, 3 },
    { _("3/4 plus 1/4?"),  { _("1"),  _("4/8"),_("2")  }, 0, 3 },
    { _("Round 4.7"),      { _("4"),  _("5"),  _("6")  }, 1, 3 },
};

const struct QuizGrade gQuizGrades[5] =
{
    { sGrade1, ARRAY_COUNT(sGrade1) },
    { sGrade2, ARRAY_COUNT(sGrade2) },
    { sGrade3, ARRAY_COUNT(sGrade3) },
    { sGrade4, ARRAY_COUNT(sGrade4) },
    { sGrade5, ARRAY_COUNT(sGrade5) },
};
