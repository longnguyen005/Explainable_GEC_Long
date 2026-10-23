"""
tune_ml.py - chỉnh LogReg và k-NN trên dev để vượt mốc luật POS (micro F0.5 = 0.139).

Đặt file này cạnh baseline_ml.py (trong thư mục Explainable_GEC) rồi chạy:
    python3 tune_ml.py

- Lần đầu chạy chậm (gán POS cho cả train); nhãn POS được lưu vào pos_cache_*.pkl nên các lần
  sau nhanh hơn. Sửa hàm feature_strings() thoải mái, không cần xóa cache.
- Tham số (C, ngưỡng, k) chọn trên dev. Vì vậy số F0.5 trên dev sau khi chỉnh là số "đã
  tối ưu trên dev", không phải ước lượng khách quan. Số báo cáo cuối cùng phải lấy từ test,
  chạy ĐÚNG MỘT LẦN bằng cách đặt FINAL_TEST = True sau khi đã chốt tham số.
"""
import json, os, pickle, ssl
from array import array
from collections import Counter
import numpy as np
import pandas as pd
import scipy.sparse as sp
import nltk
from sklearn.linear_model import LogisticRegression
from sklearn.decomposition import TruncatedSVD
from sklearn.preprocessing import normalize
from sklearn.neighbors import NearestNeighbors

try:                                  # sửa lỗi SSL khi tải NLTK trên macOS
    ssl._create_default_https_context = ssl._create_unverified_context
except AttributeError:
    pass
for pkg in ["averaged_perceptron_tagger_eng", "averaged_perceptron_tagger"]:
    nltk.download(pkg, quiet=True)

# ===================== CẤU HÌNH =====================
FINAL_TEST = False        # True = chạy test một lần với tham số đã chọn trên dev
MOCMOC = 0.139            # mốc luật POS (micro F0.5 trên dev)
BASE = os.path.dirname(os.path.abspath(__file__))
TYPES = ["SVA", "VFORM", "NNUM"]
MAP = {"Subject-Verb Agreement": "SVA", "Number": "NNUM",
       "Infinitives": "VFORM", "Gerund": "VFORM", "Participle": "VFORM"}
TAUS = np.round(np.arange(0.05, 0.96, 0.05), 2)   # các ngưỡng thử

# ===================== DỮ LIỆU (giống baseline_ml.py) =====================
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
    sents = []
    for x in data:
        t = MAP.get(x["error_type"])
        if t and not is_substitution(x):
            continue
        keep = [i for i, tok in enumerate(x["source"]) if tok != "[NONE]"]
        toks = [x["source"][i] for i in keep]
        gold = ["O"] * len(toks)
        if t:
            gold[keep.index(err_pos(x)[0])] = t
        sents.append((toks, gold))
    return sents

# ===================== ĐẶC TRƯNG (phong phú hơn baseline_ml.py) =====================
def feature_strings(tokens, tags):
    """Mỗi token -> danh sách chuỗi đặc trưng nhị phân dạng 'ten=giatri'. Chỉ dùng câu sai."""
    low = [t.lower() for t in tokens]
    n = len(tokens)
    W = lambda i: low[i] if 0 <= i < n else "<PAD>"
    P = lambda i: tags[i] if 0 <= i < n else "<PAD>"
    out = []
    for i in range(n):
        f = [f"w={W(i)}", f"pos={P(i)}", f"suf2={low[i][-2:]}", f"suf3={low[i][-3:]}",
             f"pre2={low[i][:2]}"]
        if tokens[i][:1].isupper():
            f.append("cap")
        if low[i].isdigit():
            f.append("digit")
        for d in (-3, -2, -1, 1, 2, 3):                       # cửa sổ ±3 từ và POS
            f.append(f"w{d}={W(i + d)}")
            f.append(f"p{d}={P(i + d)}")
        f.append(f"w-1|w={W(i - 1)}|{W(i)}")                  # bigram từ
        f.append(f"w|w+1={W(i)}|{W(i + 1)}")
        f.append(f"p-1|p={P(i - 1)}|{P(i)}")                  # bigram POS
        f.append(f"p|p+1={P(i)}|{P(i + 1)}")
        f.append(f"p-2|p-1|p={P(i - 2)}|{P(i - 1)}|{P(i)}")
        for d in (-4, -3, -2, -1):                            # túi từ bên trái (mạo từ, số lượng từ)
            f.append("ctxL=" + W(i + d))
        for d in range(1, 5):                                 # chủ ngữ gần nhất bên trái (cho SVA)
            j = i - d
            if j >= 0 and (tags[j].startswith("NN") or tags[j] == "PRP"):
                f.append(f"subj_w={low[j]}")
                f.append(f"subj_p={tags[j]}")
                break
        out.append(f)
    return out

def get_tags(name, sents):
    """Gán POS (chậm) và lưu cache, vì đây là bước tốn thời gian nhất."""
    path = os.path.join(BASE, f"pos_cache_{name}.pkl")
    if os.path.exists(path):
        return pickle.load(open(path, "rb"))
    print(f"  gán POS cho {name} ({len(sents)} câu) ...")
    tags = [[t for _, t in nltk.pos_tag(toks)] for toks, _ in sents]
    pickle.dump(tags, open(path, "wb"))
    return tags

def iter_feats(sents, tags_all):
    for (toks, _), tags in zip(sents, tags_all):
        yield from feature_strings(toks, tags)

def fit_vocab(sents, tags_all, min_count=3):
    """Bỏ đặc trưng xuất hiện < min_count lần trên train (giảm nhiễu, tiết kiệm bộ nhớ)."""
    cnt = Counter()
    for fs in iter_feats(sents, tags_all):
        cnt.update(fs)
    return {f: i for i, f in enumerate(sorted(f for f, c in cnt.items() if c >= min_count))}

def to_matrix(sents, tags_all, vocab):
    indptr, indices = array("q", [0]), array("i")
    for fs in iter_feats(sents, tags_all):
        indices.extend(vocab[f] for f in fs if f in vocab)
        indptr.append(len(indices))
    m = sp.csr_matrix((np.ones(len(indices), dtype=np.float32),
                       np.frombuffer(indices, dtype=np.int32).copy(),
                       np.frombuffer(indptr, dtype=np.int64).copy()),
                      shape=(len(indptr) - 1, len(vocab)))
    m.sum_duplicates()
    m.data[:] = 1.0
    return m

def labels(sents):
    return np.array([g for _, gl in sents for g in gl])

# ===================== ĐÁNH GIÁ =====================
def prf05(tp, fp, fn):
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f = 1.25 * p * r / (0.25 * p + r) if (0.25 * p + r) else 0.0
    return p, r, f

def micro(yt, yp):                        # micro 3 loại, không tính nhãn O
    tp = int(((yt == yp) & (yt != "O")).sum())
    fp = int(((yp != "O") & (yt != yp)).sum())
    fn = int(((yt != "O") & (yt != yp)).sum())
    return prf05(tp, fp, fn)

def table(name, yt, yp):
    rows = []
    for t in TYPES:
        tp = int(((yt == t) & (yp == t)).sum())
        fp = int(((yp == t) & (yt != t)).sum())
        fn = int(((yt == t) & (yp != t)).sum())
        rows.append((name, t, tp + fn, *prf05(tp, fp, fn)))
    rows.append((name, "MICRO 3 loai", int((yt != "O").sum()), *micro(yt, yp)))
    return rows

# ===================== GIẢI MÃ THEO NGƯỠNG =====================
def decode_lr(proba, classes, tau):
    classes = np.array(classes)
    iO = list(classes).index("O")
    p_err = 1.0 - proba[:, iO]                       # xác suất "có lỗi 3 loại"
    q = proba.copy()
    q[:, iO] = -1
    best = classes[q.argmax(axis=1)]                 # loại lỗi có xác suất cao nhất
    return np.where(p_err >= tau, best, "O")

def decode_knn(lab, k, tau):
    lab = lab[:, :k]
    cnt = np.stack([(lab == t).sum(axis=1) for t in TYPES], axis=1)
    best = np.array(TYPES)[cnt.argmax(axis=1)]
    frac = cnt.sum(axis=1) / k                       # tỉ lệ láng giềng là lỗi
    return np.where(frac >= tau, best, "O")

# ===================== CHẠY =====================
print("=== Chuẩn bị dữ liệu ===")
train_sents, dev_sents = build(splits["train"]), build(splits["dev"])
tags_tr, tags_dev = get_tags("train", train_sents), get_tags("dev", dev_sents)
vocab = fit_vocab(train_sents, tags_tr)
Xtr, Xdev = to_matrix(train_sents, tags_tr, vocab), to_matrix(dev_sents, tags_dev, vocab)
ytr, ydev = labels(train_sents), labels(dev_sents)
print(f"Số đặc trưng: {Xtr.shape[1]} | token train: {Xtr.shape[0]} | token dev: {Xdev.shape[0]}")

# ---------- LogReg: chỉnh C (L2) + ngưỡng xác suất ----------
print("\n=== LogReg: chỉnh C và ngưỡng xác suất trên dev (không dùng class_weight='balanced') ===")
best_lr = {"f": -1.0}
for C in [0.1, 0.3, 1.0, 3.0]:
    clf = LogisticRegression(C=C, max_iter=300)      # L2 mặc định
    clf.fit(Xtr, ytr)
    proba = clf.predict_proba(Xdev)
    loc = {"f": -1.0}
    for tau in TAUS:
        p, r, f = micro(ydev, decode_lr(proba, clf.classes_, tau))
        if f > loc["f"]:
            loc = dict(C=C, tau=float(tau), p=p, r=r, f=f)
    print(f"  C={C:<5} tốt nhất tại ngưỡng {loc['tau']:.2f}: P={loc['p']:.3f} R={loc['r']:.3f} F0.5={loc['f']:.3f}")
    if loc["f"] > best_lr["f"]:
        best_lr = {**loc, "clf": clf, "proba": proba}
print(f"=> LogReg chọn: C={best_lr['C']}, ngưỡng={best_lr['tau']:.2f}, micro F0.5={best_lr['f']:.3f}")
inv = np.array(sorted(vocab, key=vocab.get))
print("\nĐặc trưng có hệ số lớn nhất của mỗi lớp (để giải thích mô hình):")
for ci, c in enumerate(best_lr["clf"].classes_):
    if c != "O":
        print(f"  {c}: {', '.join(inv[np.argsort(-best_lr['clf'].coef_[ci])[:10]])}")

# ---------- k-NN: cosine + SVD + giảm mẫu O + ngưỡng ----------
print("\n=== k-NN: cosine + TruncatedSVD + giảm mẫu O (chọn k và ngưỡng trên dev) ===")
svd = TruncatedSVD(n_components=200, random_state=0)
Ztr = normalize(svd.fit_transform(normalize(Xtr)))
Zdev = normalize(svd.transform(normalize(Xdev)))
rng = np.random.RandomState(0)
idx_err = np.where(ytr != "O")[0]
idx_O = np.where(ytr == "O")[0]
keep = np.concatenate([idx_err, rng.choice(idx_O, size=10 * len(idx_err), replace=False)])
Zk, yk = Ztr[keep], ytr[keep]
print(f"  train k-NN: {len(keep)} token (toàn bộ {len(idx_err)} token lỗi + {10 * len(idx_err)} token O)")
KMAX = 50
nn = NearestNeighbors(n_neighbors=KMAX, metric="cosine", algorithm="brute", n_jobs=-1).fit(Zk)
_, nbr = nn.kneighbors(Zdev)
lab_dev = yk[nbr]
best_knn = {"f": -1.0}
for k in [5, 10, 20, 50]:
    loc = {"f": -1.0}
    for tau in TAUS:
        p, r, f = micro(ydev, decode_knn(lab_dev, k, tau))
        if f > loc["f"]:
            loc = dict(k=k, tau=float(tau), p=p, r=r, f=f)
    print(f"  k={k:<3} tốt nhất tại ngưỡng {loc['tau']:.2f}: P={loc['p']:.3f} R={loc['r']:.3f} F0.5={loc['f']:.3f}")
    if loc["f"] > best_knn["f"]:
        best_knn = loc
print(f"=> k-NN chọn: k={best_knn['k']}, ngưỡng={best_knn['tau']:.2f}, micro F0.5={best_knn['f']:.3f}")

# ---------- Bảng kết quả dev ----------
yp_lr = decode_lr(best_lr["proba"], best_lr["clf"].classes_, best_lr["tau"])
yp_knn = decode_knn(lab_dev, best_knn["k"], best_knn["tau"])
rows = table("LogReg (da chinh)", ydev, yp_lr) + table("k-NN (da chinh)", ydev, yp_knn)
df = pd.DataFrame(rows, columns=["HeThong", "Nhan", "SoGold", "P", "R", "F0.5"]).round(3)
print("\n" + "=" * 70)
print("KẾT QUẢ DEV SAU KHI CHỈNH (tham số chọn trên dev)")
print("=" * 70)
print(df.to_string(index=False))
df.to_csv(os.path.join(BASE, "tuned_dev.csv"), index=False)
for name, f in [("LogReg", best_lr["f"]), ("k-NN", best_knn["f"])]:
    print(f"{name}: micro F0.5 = {f:.3f}  {'VƯỢT' if f > MOCMOC else 'CHƯA vượt'} mốc luật POS ({MOCMOC})")

# ---------- Test: chạy đúng một lần ----------
if FINAL_TEST:
    print("\n=== TEST (chạy một lần với tham số đã chọn trên dev) ===")
    test_sents = build(splits["test"])
    Xte = to_matrix(test_sents, get_tags("test", test_sents), vocab)
    yte = labels(test_sents)
    ypt_lr = decode_lr(best_lr["clf"].predict_proba(Xte), best_lr["clf"].classes_, best_lr["tau"])
    _, nb = nn.kneighbors(normalize(svd.transform(normalize(Xte))))
    ypt_knn = decode_knn(yk[nb], best_knn["k"], best_knn["tau"])
    dft = pd.DataFrame(table("LogReg (test)", yte, ypt_lr) + table("k-NN (test)", yte, ypt_knn),
                       columns=["HeThong", "Nhan", "SoGold", "P", "R", "F0.5"]).round(3)
    print(dft.to_string(index=False))
    dft.to_csv(os.path.join(BASE, "tuned_test.csv"), index=False)
    print("Nhớ chạy luật POS trên test (baseline.py, SPLIT = 'test') để so cùng điều kiện.")