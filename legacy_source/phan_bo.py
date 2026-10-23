import json, collections, os, random
import pandas as pd

BASE = os.path.dirname(os.path.abspath(__file__))

def load(path):
    txt = open(path, encoding="utf-8").read().strip()
    if txt.startswith("["):                       # file là một mảng JSON
        return json.loads(txt)
    return [json.loads(l) for l in txt.splitlines() if l.strip()]   # JSONL

splits = {s: load(os.path.join(BASE, "data", "json", f"{s}.json"))
          for s in ["train", "dev", "test"]}

# ---- Bước 1: in các loại lỗi trong train ----
print("=" * 60)
print("CÁC LOẠI LỖI TRONG TRAIN")
for k, v in collections.Counter(x["error_type"] for x in splits["train"]).most_common():
    print(f"{v:6d} | {k}")

# ---- Bước 2: gộp nhãn (đã sửa đúng tên) ----
MAP = {
    "Subject-Verb Agreement": "SVA",
    "Number": "NNUM",
    "Infinitives": "VFORM",
    "Gerund": "VFORM",
    "Participle": "VFORM",
}
types = {x["error_type"] for x in splits["train"]}
missing = [k for k in MAP if k not in types]
assert not missing, f"Tên không có trong dữ liệu: {missing}"

def err_pos(x):                    # vị trí token lỗi trong câu sai
    n = len(x["source"])
    return [i for i in x["correction_index"] if i < n]

def is_substitution(x):            # đúng 1 token sai -> 1 token đúng, không có [NONE]
    n = len(x["source"])
    src = [x["source"][i] for i in x["correction_index"] if i < n]
    tgt = [x["target"][i - n - 1] for i in x["correction_index"] if i > n]
    return len(src) == 1 and len(tgt) == 1 and "[NONE]" not in src + tgt

# ---- Bước 3: bảng phân bố ----
rows = []
for s, data in splits.items():
    total_tokens = sum(len(x["source"]) for x in data)
    kept = [x for x in data if x["error_type"] in MAP]
    for t in ["SVA", "VFORM", "NNUM"]:
        xs = [x for x in kept if MAP[x["error_type"]] == t]
        err_tok = sum(len(err_pos(x)) for x in xs)
        rows.append({
            "split": s, "loai": t, "so_mau": len(xs),
            "%_trong_3_loai": round(100 * len(xs) / max(len(kept), 1), 1),
            "mau_thay_the_1_1": sum(is_substitution(x) for x in xs),
            "token_loi": err_tok,
            "tong_token": total_tokens,
            "%_token_loi": round(100 * err_tok / total_tokens, 3),
        })
df = pd.DataFrame(rows)
print("=" * 60)
print("BẢNG PHÂN BỐ")
print(df.to_string(index=False))
df.to_csv(os.path.join(BASE, "phan_bo_3_loai.csv"), index=False)
print("Đã lưu phan_bo_3_loai.csv")

try:
    import matplotlib.pyplot as plt
    df.pivot(index="split", columns="loai", values="so_mau") \
      .loc[["train", "dev", "test"]].plot.bar(rot=0)
    plt.title("So mau 3 loai loi theo split")
    plt.ylabel("So mau")
    plt.tight_layout()
    plt.savefig(os.path.join(BASE, "phan_bo_3_loai.png"), dpi=150)
    print("Đã lưu phan_bo_3_loai.png")
except ImportError:
    print("Chưa có matplotlib: chạy  python3 -m pip install matplotlib")

# ---- Bước 4: từ đứng trước và token lỗi (train) ----
prev = collections.defaultdict(collections.Counter)
word = collections.defaultdict(collections.Counter)
for x in splits["train"]:
    if x["error_type"] in MAP:
        t = MAP[x["error_type"]]
        for i in err_pos(x):
            prev[t][x["source"][i - 1].lower() if i > 0 else "<s>"] += 1
            word[t][x["source"][i].lower()] += 1
print("=" * 60)
for t in ["SVA", "VFORM", "NNUM"]:
    print(f"\n{t}\n  từ trước: {prev[t].most_common(10)}\n  token lỗi: {word[t].most_common(10)}")

# ---- Bước 5: xem 5 mẫu VFORM không phải thay thế 1-1 ----
random.seed(0)
ns = [x for x in splits["train"]
      if MAP.get(x["error_type"]) == "VFORM" and not is_substitution(x)]
print("=" * 60)
print("5 MẪU VFORM KHÔNG PHẢI THAY THẾ 1-1")
for x in random.sample(ns, 5):
    print("SAI :", " ".join(x["source"]))
    print("ĐÚNG:", " ".join(x["target"]))
    print("LOẠI:", x["error_type"], "\n")