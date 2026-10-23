import json, os, collections, random
import pandas as pd
import nltk

for pkg in ["averaged_perceptron_tagger_eng", "averaged_perceptron_tagger"]:
    nltk.download(pkg, quiet=True)

SPLIT = "dev"   # báo cáo: "dev". Muốn xem lỗi để sửa luật: đổi sang "train"
SHOW = 8        # số ví dụ lỗi in ra
BASE = os.path.dirname(os.path.abspath(__file__))
TYPES = ["SVA", "VFORM", "NNUM"]
MAP = {"Subject-Verb Agreement": "SVA", "Number": "NNUM",
       "Infinitives": "VFORM", "Gerund": "VFORM", "Participle": "VFORM"}

def load(path):
    txt = open(path, encoding="utf-8").read().strip()
    if txt.startswith("["):
        return json.loads(txt)
    return [json.loads(l) for l in txt.splitlines() if l.strip()]

splits = {s: load(os.path.join(BASE, "data", "json", f"{s}.json"))
          for s in ["train", "dev", "test"]}

def err_pos(x):
    n = len(x["source"])
    return [i for i in x["correction_index"] if i < n]

def is_substitution(x):
    n = len(x["source"])
    src = [x["source"][i] for i in x["correction_index"] if i < n]
    tgt = [x["target"][i - n - 1] for i in x["correction_index"] if i > n]
    return len(src) == 1 and len(tgt) == 1 and "[NONE]" not in src + tgt

def build(data):
    """Trả về [(tokens, nhãn từng token)] và số mẫu 3 loại bị loại (không phải thay thế 1-1)."""
    sents, dropped = [], 0
    for x in data:
        t = MAP.get(x["error_type"])
        if t and not is_substitution(x):
            dropped += 1
            continue
        keep = [i for i, tok in enumerate(x["source"]) if tok != "[NONE]"]
        toks = [x["source"][i] for i in keep]
        gold = ["O"] * len(toks)
        if t:
            gold[keep.index(err_pos(x)[0])] = t
        sents.append((toks, gold))
    return sents, dropped

# ---------------- LUẬT ĐƠN GIẢN (dùng POS) ----------------
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

def rule_predict(toks):
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

# ---------------- ĐÁNH GIÁ ----------------
def prf(tp, fp, fn, beta=0.5):
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * p * r / (p + r) if p + r else 0.0
    b2 = beta ** 2
    f05 = (1 + b2) * p * r / (b2 * p + r) if b2 * p + r else 0.0
    return p, r, f1, f05

def report(name, sents, preds):
    rows, T = [], collections.Counter()
    for t in TYPES:
        tp = fp = fn = 0
        for (_, gold), pred in zip(sents, preds):
            for g, q in zip(gold, pred):
                tp += (g == t and q == t); fp += (q == t and g != t); fn += (g == t and q != t)
        T.update(tp=tp, fp=fp, fn=fn)
        rows.append((name, t, tp + fn, *prf(tp, fp, fn)))
    rows.append((name, "MICRO 3 loai", T["tp"] + T["fn"], *prf(T["tp"], T["fp"], T["fn"])))
    tp = fp = fn = 0                                  # chỉ phát hiện, bỏ qua loại
    for (_, gold), pred in zip(sents, preds):
        for g, q in zip(gold, pred):
            tp += (g != "O" and q != "O"); fp += (g == "O" and q != "O"); fn += (g != "O" and q == "O")
    rows.append((name, "CHI PHAT HIEN", tp + fn, *prf(tp, fp, fn)))
    acc = sum(g == q for (_, gl), pl in zip(sents, preds) for g, q in zip(gl, pl)) / sum(len(gl) for _, gl in sents)
    clean = [p for (_, gl), p in zip(sents, preds) if all(g == "O" for g in gl)]
    fa_sent = sum(any(l != "O" for l in p) for p in clean)
    fa_tok = sum(l != "O" for p in clean for l in p)
    print(f"\n[{name}] accuracy token = {acc:.4f}")
    print(f"[{name}] câu không có lỗi 3 loại: {len(clean)} | bị báo sai >=1 token: {fa_sent} "
          f"({100*fa_sent/len(clean):.1f}%) | {100*fa_tok/len(clean):.1f} token báo sai / 100 câu")
    return rows

def show_errors(sents, preds, k):
    fps, fns = [], []
    for (toks, gold), pred in zip(sents, preds):
        for i, (g, q) in enumerate(zip(gold, pred)):
            if q != "O" and g != q: fps.append((toks, i, g, q))
            if g != "O" and g != q: fns.append((toks, i, g, q))
    random.seed(0)
    fmt = lambda toks, i: " ".join(toks[max(0, i-6):i]) + " [[" + toks[i] + "]] " + " ".join(toks[i+1:i+7])
    print("\n--- BÁO SAI (dự đoán loại lỗi nhưng gold khác) ---")
    for toks, i, g, q in random.sample(fps, min(k, len(fps))):
        print(f"  dự đoán {q} | gold {g}: {fmt(toks, i)}")
    print("\n--- BỎ SÓT / SAI LOẠI (gold có lỗi nhưng dự đoán khác) ---")
    for toks, i, g, q in random.sample(fns, min(k, len(fns))):
        print(f"  gold {g} | dự đoán {q}: {fmt(toks, i)}")

# ---------------- CHẠY ----------------
print("Kiểm tra tagger:", nltk.pos_tag("She go to school every day".split()))
sents, dropped = build(splits[SPLIT])
train_sents, _ = build(splits["train"])
n_gold = collections.Counter(g for _, gl in sents for g in gl if g != "O")
print(f"\nTập {SPLIT}: {len(sents)} câu | loại {dropped} mẫu 3 loại không phải thay thế 1-1 | token gold: {dict(n_gold)}")

maj = [["O"] * len(toks) for toks, _ in sents]
rule = [rule_predict(toks) for toks, _ in sents]

rows = report("Da so lop (toan O)", sents, maj) + report("Luat POS", sents, rule)
df = pd.DataFrame(rows, columns=["he_thong", "nhan", "so_gold", "P", "R", "F1", "F0.5"]).round(3)
print("\n", df.to_string(index=False))
df.to_csv(os.path.join(BASE, f"baseline_{SPLIT}.csv"), index=False)

# Sàn của bước phân loại: biết trước vị trí lỗi, luôn đoán loại phổ biến nhất ở train
cnt = collections.Counter(g for _, gl in train_sents for g in gl if g != "O")
mt = cnt.most_common(1)[0][0]
print(f"\nBiết vị trí lỗi, luôn đoán '{mt}': đúng {100 * n_gold[mt] / sum(n_gold.values()):.1f}% token lỗi")

show_errors(sents, rule, SHOW)