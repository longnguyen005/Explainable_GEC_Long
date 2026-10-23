"""Unchanged POS rules extracted statically from baseline.py; no import side effects."""

import nltk

NONBASE = {"VBZ", "VBD", "VBG", "VBN", "VBP"}

BE = {"is", "are", "was", "were", "am", "be", "been", "being"}

HAVE = {"have", "has", "had", "having"}

TO_PREP = {"forward", "due", "according", "used", "prior", "addicted",
           "committed", "contribute", "contributes", "devoted", "opposed", "object", "key"}

NNS_EXC = {"politics", "economics", "physics", "mathematics", "ethics",
           "news", "series", "means", "species", "athletics"}

PLURAL_Q = {"many", "several", "few", "these", "those", "both", "various", "numerous"}

SING_DET = {"a", "an", "each", "every", "another"}

POSS_DET = {"the", "these", "those", "my", "our", "their", "his", "her", "its", "your"}

UNITS = {"percent", "million", "billion", "hundred", "thousand", "dozen", "per", "cent", "pm", "am"}

def rule_predict(toks, tags=None):
    if tags is None:
        tags = [t for _, t in nltk.pos_tag(toks)]
    low = [t.lower() for t in toks]
    pred = ["O"] * len(toks)
    for i in range(1, len(toks)):
        p, w, pt, t = low[i - 1], low[i], tags[i - 1], tags[i]

        vform = (
            (p == "to" and pt == "TO" and t in NONBASE
             and not (i >= 2 and low[i - 2] in TO_PREP))      # to + động từ không phải nguyên mẫu
            or (pt == "MD" and t in NONBASE)                  # can/will/must + không nguyên mẫu
            or (p in HAVE and t in {"VB", "VBP"})             # have + nguyên mẫu (have go)
            or (p in BE and t in {"VB", "VBP", "VBZ"})        # be + nguyên mẫu / chia ngôi
        )

        sva = False
        if p in {"he", "she", "it"}:
            it_obj = (p == "it" and i >= 2 and
                      (tags[i - 2].startswith("VB") or low[i - 2] in {"let", "make", "help"}))
            sva = (not it_obj) and (t in {"VB", "VBP"} or w in {"are", "am"})
        elif pt in {"NN", "NNP"}:
            sva = (t == "VBP") or w in {"are", "am"}
        elif p == "i":
            sva = w in {"is", "has", "does", "are"}
        elif p in {"you", "we", "they"} or (pt == "NNS" and p not in NNS_EXC):
            sva = w in {"is", "was", "has", "does"}

        nnum = (
            (p in PLURAL_Q and t == "NN")                                         # many reason
            or (pt == "CD" and p not in {"one", "1"} and t == "NN" and w not in UNITS)   # two reason
            or (p in SING_DET and t == "NNS")                                     # a reasons
            or (i >= 3 and low[i - 2] == "of" and low[i - 3] in {"one", "each"}
                and p in POSS_DET and t == "NN")                                  # one of the reason
        )

        if vform:
            pred[i] = "VFORM"
        elif sva:
            pred[i] = "SVA"
        elif nnum:
            pred[i] = "NNUM"
    return pred
