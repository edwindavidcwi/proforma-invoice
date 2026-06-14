#!/usr/bin/env python3
"""Independent answer-key audit for the non-math questions.

Decodes every question + correct answer from the ROM and checks it against a
hand-written key (kept separate from the generator's pools) for the categories
with objective answers: animal babies, plurals, past tense, opposites, and the
fixed science / GK / shapes facts. A mismatch means the data drifted from the
key (a real error) or the answer is genuinely debatable (worth a human look).

Usage: python3 audit_facts.py [rom]
"""
import re, sys, os

ROM = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", "pokered", "pokered.gbc")
SYM = re.sub(r"\.gbc?$", ".sym", ROM)

PUN = {0x7f:' ',0x9c:':',0xb7:'x',0xe3:'-',0xe6:'?',0xe7:'!',0xe8:'.',0xf3:'/',0x75:'.'}
def ch(b):
    if b in PUN: return PUN[b]
    if 0x80<=b<=0x99: return chr(65+b-0x80)
    if 0xa0<=b<=0xb9: return chr(97+b-0xa0)
    if 0xf6<=b<=0xff: return chr(48+b-0xf6)
    return '~'
rom = open(ROM,'rb').read(); sym = {}
for ln in open(SYM):
    m = re.match(r'^([0-9a-fA-F]+):([0-9a-fA-F]+)\s+(\S+)$', ln.strip())
    if m: sym[m.group(3)] = (int(m.group(1),16), int(m.group(2),16))
off = lambda b,a: b*0x4000 + (a-0x4000)
def rd(b,a):
    o=off(b,a); s=''
    while rom[o]!=0x50 and len(s)<=30: s+=ch(rom[o]); o+=1
    return s

# ----- the independent key (written separately from tools_gen_quiz.py) -----
BABY = {"dog":"puppy","cat":"kitten","cow":"calf","sheep":"lamb","horse":"foal",
        "goat":"kid","hen":"chick","frog":"tadpole","bear":"cub","lion":"cub",
        "deer":"fawn","pig":"piglet","duck":"duckling","kangaroo":"joey"}
PLURAL = {"cat":"cats","dog":"dogs","pen":"pens","hat":"hats","cup":"cups","box":"boxes",
          "bus":"buses","fox":"foxes","dish":"dishes","baby":"babies","city":"cities",
          "lady":"ladies","pony":"ponies","man":"men","woman":"women","child":"children",
          "mouse":"mice","foot":"feet","tooth":"teeth","leaf":"leaves","goose":"geese"}
PAST = {"run":"ran","go":"went","eat":"ate","see":"saw","come":"came","give":"gave",
        "take":"took","make":"made","buy":"bought","teach":"taught","sing":"sang",
        "swim":"swam","fly":"flew","draw":"drew","sit":"sat","win":"won","ride":"rode","fall":"fell"}
# opposites that are unambiguous (skip the ones a teacher could argue, e.g. old)
OPP = {"big":"small","hot":"cold","up":"down","in":"out","day":"night","fast":"slow",
       "happy":"sad","full":"empty","open":"shut","wet":"dry","tall":"short","high":"low",
       "good":"bad","light":"dark","clean":"dirty","near":"far","loud":"quiet","win":"lose",
       "rich":"poor","true":"false","weak":"strong","thick":"thin","wide":"narrow",
       "begin":"end","push":"pull","left":"right","first":"last","more":"less","brave":"afraid"}
FACTS = {  # exact question text -> accepted answer(s)
    "Days in a week?":"7","How many fingers?":"10","Colors in rainbow":"7","Eyes on a face?":"2",
    "Legs on a person?":"2","Wheels on a car?":"4","Thumbs on hands?":"2","Months in a year?":"12",
    "Days in weekend?":"2","Hours in a day?":"24","Seasons in year?":"4","Minutes in hour?":"60",
    "Days in Sept?":"30","Weeks in a year?":"52","Hours half day?":"12","Days in a year?":"365",
    "Seconds in min?":"60","Sides of a dice?":"6","Oceans on Earth?":"5","Continents?":"7",
    "Days in leap yr?":"366","Years in decade?":"10","Years in century":"100","Days in 2 weeks?":"14",
    "Minutes half hr?":"30","Hours in 2 days?":"48","Sides on a cube?":"6","Half of a dozen?":"6",
    "Legs on 2 cats?":"8","Months in year?":"12",
    "Cow says?":"moo","Dog says?":"woof","Cat says?":"meow","Bees make?":"honey","Spider legs?":"8",
    "Birds lay?":"eggs","Cows give?":"milk","Insect legs?":"6","Frog baby?":"tadpole","Blood is?":"red",
    "Sun rises in?":"east","Planet we live?":"Earth","Largest planet?":"Jupiter","Red planet?":"Mars",
    "Moon orbits?":"Earth","Water is H?":"H2O","Bee wings?":"2","Heart pumps?":"blood",
    "Red and blue?":"purple","Blue and yellow?":"green","Red and yellow?":"orange",
    "Red and white?":"pink","Black and white?":"grey","Cube has faces?":"6","Right angle deg?":"90",
    "Circle degrees?":"360","Cube has edges?":"12","Triangle angles?":"3",
    "Sides triangle?":"3","Sides square?":"4","Sides pentagon?":"5","Sides hexagon?":"6",
    "Sides rectangle?":"4","Sides octagon?":"8","Sides heptagon?":"7","Sides nonagon?":"9","Sides decagon?":"10",
}

def key_answer(q):
    for pre, table in (("Baby of a ",BABY),("Baby of ",BABY)):
        if q.startswith(pre): return table.get(q[len(pre):-1])
    for pre, table in (("Plural of ",PLURAL),("Many ",PLURAL)):
        if q.startswith(pre): return table.get(q[len(pre):-1])
    if q.startswith("Past of "): return PAST.get(q[8:-1])
    for pre in ("Opposite of ","Opp of "):
        if q.startswith(pre): return OPP.get(q[len(pre):-1])
    return FACTS.get(q)

gto = off(*sym['QuizGradeTable'])
checked = mism = skipped = 0; bad = []
for g in range(1,6):
    e = gto+(g-1)*4; base = rom[e]|(rom[e+1]<<8); cnt = rom[e+2]; bank = rom[e+3]
    for idx in range(cnt):
        eo = off(bank,base)+idx*14
        q = rd(bank, rom[eo]|(rom[eo+1]<<8)); ci = rom[eo+2]
        correct = rd(bank, rom[eo+4+2*ci]|(rom[eo+5+2*ci]<<8))
        exp = key_answer(q)
        if exp is None: skipped += 1; continue
        checked += 1
        if isinstance(exp, str): exp = {exp}
        if correct not in exp:
            mism += 1; bad.append((g, q, correct, exp))

print(f"independently key-checked {checked} non-math answers; {skipped} not in key (rhymes/etc.)")
for g,q,c,e in bad[:40]:
    print(f"  MISMATCH G{g}: {q!r} data={c!r} key={e}")
print("PASS: every keyed answer matches" if mism==0 else f"FAIL: {mism} mismatch(es)")
sys.exit(0 if mism==0 else 1)
