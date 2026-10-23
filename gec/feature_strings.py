"""Original tune_ml features plus three optional dependency features."""

def feature_strings(tokens, tags, dependency=None):
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
        if dependency is not None and dependency[i]['pos'] in ('VERB', 'AUX'):
            dep = dependency[i]
            f.extend([f"dep_subj_pos={dep['subject_tag']}",
                      f"dep_subj_number={dep['subject_number']}",
                      f"dep_subj_distance={dep['subject_distance']}"])
        out.append(f)
    return out
