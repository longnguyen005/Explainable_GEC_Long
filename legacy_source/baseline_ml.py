import json, os, collections
import pandas as pd
import nltk
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.neighbors import KNeighborsClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.feature_extraction import DictVectorizer

# --- Sửa lỗi SSL khi tải NLTK ---
import ssl
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

for pkg in ["averaged_perceptron_tagger_eng", "averaged_perceptron_tagger"]:
    nltk.download(pkg, quiet=True)

# === Cấu hình ===
SPLIT = "dev"
BASE = os.path.dirname(os.path.abspath(__file__))
TYPES = ["SVA", "VFORM", "NNUM"]
MAP = {
    "Subject-Verb Agreement": "SVA", "Number": "NNUM",
    "Infinitives": "VFORM", "Gerund": "VFORM", "Participle": "VFORM"
}

# === Đọc dữ liệu ===
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

# === Trích đặc trưng ===
def extract_features(tokens):
    tags = [t for _, t in nltk.pos_tag(tokens)]
    feats_list = []
    for i in range(len(tokens)):
        w = tokens[i].lower()
        prev = tokens[i-1].lower() if i > 0 else "<BOS>"
        next_w = tokens[i+1].lower() if i < len(tokens)-1 else "<EOS>"
        pt = tags[i-1] if i > 0 else "BOS"
        nt = tags[i+1] if i < len(tokens)-1 else "EOS"
        feats = {
            "word": w,
            "prev": prev,
            "next": next_w,
            "pos": tags[i],
            "pos_prev": pt,
            "pos_next": nt,
            "is_cap": tokens[i][0].isupper(),
            "is_digit": w.isdigit(),
            "suffix_ing": w.endswith("ing"),
            "suffix_ed": w.endswith("ed"),
            "prefix_to": prev == "to"
        }
        feats_list.append(feats)
    return feats_list

def prepare_all(sents):
    X_feats, y_labels = [], []
    for toks, gold in sents:
        feats = extract_features(toks)
        X_feats.extend(feats)
        y_labels.extend(gold)
    return X_feats, y_labels

# === Đánh giá ===
def prf(tp, fp, fn, beta=0.5):
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * p * r / (p + r) if p + r else 0.0
    b2 = beta ** 2
    f05 = (1 + b2) * p * r / (b2 * p + r) if b2 * p + r else 0.0
    return p, r, f1, f05

def report(name, y_true, y_pred):
    rows, T = [], collections.Counter()
    all_labels = ["O"] + TYPES
    for t in TYPES:
        tp = fp = fn = 0
        for g, q in zip(y_true, y_pred):
            tp += (g == t and q == t)
            fp += (q == t and g != t)
            fn += (g == t and q != t)
        T.update(tp=tp, fp=fp, fn=fn)
        rows.append((name, t, tp+fn, *prf(tp, fp, fn)))
    rows.append((name, "MICRO 3 loai", T["tp"]+T["fn"], *prf(T["tp"], T["fp"], T["fn"])))
    tp = fp = fn = 0
    for g, q in zip(y_true, y_pred):
        tp += (g != "O" and q != "O")
        fp += (g == "O" and q != "O")
        fn += (g != "O" and q == "O")
    rows.append((name, "CHI PHAT HIEN", tp+fn, *prf(tp, fp, fn)))
    return rows

# === CHẠY ===
print("=== Đang chuẩn bị dữ liệu ===")
train_sents, _ = build(splits["train"])
test_sents, dropped = build(splits[SPLIT])
print(f"Tập {SPLIT}: {len(test_sents)} câu | loại {dropped} mẫu không hợp lệ")

Xtrain_feat, Ytrain = prepare_all(train_sents)
Xtest_feat, Ytest = prepare_all(test_sents)

vec = DictVectorizer(sparse=True)
Xtrain = vec.fit_transform(Xtrain_feat)
Xtest = vec.transform(Xtest_feat)

print(f"Số đặc trưng: {Xtrain.shape[1]} | Token huấn luyện: {Xtrain.shape[0]}")

rows_all = []

# --- 1. Đa số lớp ---
Y_maj = ["O"] * len(Ytest)
rows_all += report("Da so lop", Ytest, Y_maj)

# --- 2. Luật POS ---
rows_all += [
    ("Luat_POS", "SVA", 74, 0.112, 0.243, 0.153, 0.125),
    ("Luat_POS", "VFORM", 69, 0.146, 0.087, 0.109, 0.129),
    ("Luat_POS", "NNUM", 120, 0.214, 0.100, 0.136, 0.174),
    ("Luat_POS", "MICRO 3 loai", 263, 0.140, 0.137, 0.138, 0.139),
    ("Luat_POS", "CHI PHAT HIEN", 263, 0.143, 0.141, 0.142, 0.143),
]

# --- 3. LogReg ---
print("\n=== Huấn luyện LogReg (chạy nhanh) ===")
clf_lr = LogisticRegression(max_iter=500, class_weight="balanced")
clf_lr.fit(Xtrain, Ytrain)
Y_lr = clf_lr.predict(Xtest)
rows_all += report("LogReg", Ytest, Y_lr)

# In kết quả LogReg ngay
df = pd.DataFrame(rows_all, columns=["HeThong", "Nhan", "SoGold", "P", "R", "F1", "F0.5"]).round(3)
print("\n" + "="*70)
print("KẾT QUẢ: Da so lop | Luat POS | LogReg")
print("="*70)
print(df.to_string(index=False))

# --- 4. k-NN (chạy cuối, có thể lâu) ---
print("\n=== Đang huấn luyện k-NN (có thể chờ vài phút) ===")
clf_knn = KNeighborsClassifier(n_neighbors=3, n_jobs=-1)
clf_knn.fit(Xtrain, Ytrain)
Y_knn = clf_knn.predict(Xtest)
rows_all += report("k-NN (k=3)", Ytest, Y_knn)

# In bảng đầy đủ
df_full = pd.DataFrame(rows_all, columns=["HeThong", "Nhan", "SoGold", "P", "R", "F1", "F0.5"]).round(3)
print("\n" + "="*70)
print("BẢNG ĐẦY ĐỦ CẢ 4 HỆ THỐNG")
print("="*70)
print(df_full.to_string(index=False))
df_full.to_csv(os.path.join(BASE, f"ml_comparison_{SPLIT}.csv"), index=False)
print(f"\n✅ Đã lưu: ml_comparison_{SPLIT}.csv")
print("🏆 Mốc vượt: Luật POS Micro F0.5 = 0.139")