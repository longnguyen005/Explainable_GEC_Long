# TỔNG HỢP KẾT QUẢ CHÍNH THỨC CHO BÁO CÁO — NHÓM 2 (GROUP 02)
**Bản triển khai:** `Explainable_GEC_Long` (Đã đồng bộ 100% với `Group02_Long_Report_Pack` ngày 03/11/2026)

Tài liệu này tổng hợp đầy đủ các bảng số liệu, công thức và nhận xét đã đối chiếu chính xác với các file CSV trong [`Group02_Long_Report_Pack/report_tables/`](Group02_Long_Report_Pack/report_tables/) và đầu ra đã lưu của Long.

---

## 1. MỤC 3 TRONG BÁO CÁO: Quy tắc chọn mô hình & Cấu hình đã khóa trên `dev`

- **Quy tắc chọn điểm vận hành trong code ([`gec/models.py`](gec/models.py), [`configs/dev.json`](configs/dev.json)):**
  - **Đối với `LR_base` và `LR_parser` (`select_lr`):**
    1. Lưới tham số: $C \in \{0.1, 0.3, 1.0, 3.0\} \times \tau \in \{0.05, 0.10, \dots, 0.95\}$ ($76$ cấu hình/mô hình).
    2. Trong mỗi giá trị $C$, chọn ngưỡng $\tau$ tối đa hóa **$F_{0.5}$ micro có nhãn (`typed MICRO F0.5`)** trên tập `dev`; nếu hòa điểm thì ưu tiên Precision (`P`) cao hơn rồi đến ngưỡng $\tau$ cao hơn.
    3. Giữa các đại diện tốt nhất của từng $C$ (`per_C_best`), chọn **$C$ nhỏ nhất** (điều chuẩn mạnh nhất) có $F_{0.5}$ thấp hơn mức cực đại không quá **`near_tie_C_margin = 0.005`** (dùng số thực chưa làm tròn).
  - **Đối với `kNN` (`fit_knn`):**
    - Giảm chiều `TruncatedSVD` $200$ chiều (fit trên `train`), chuẩn hóa $L_2$ trước và sau SVD, khoảng cách Cosine trên $42.493$ mẫu (`3.863` token lỗi + `38.630` token `O`, `seed=0`).
    - Lưới tham số: $k \in \{5, 10, 20, 50\} \times \tau \in \{0.05, \dots, 0.95\}$, chọn theo `(-F0.5, -P, k, -tau)`.
- **Cấu hình được chọn và khóa tại [`outputs/dev_run_001/config_locked.json`](outputs/dev_run_001/config_locked.json) (lưới 228 dòng lưu tại [`outputs/dev_run_001/tuning_grid.csv`](outputs/dev_run_001/tuning_grid.csv)):**

| Hệ thống | Tham số được chọn | Ngưỡng $\tau$ | TP (dev) | FP (dev) | FN (dev) | Precision ($P$) | Recall ($R$) | $F_{0.5}$ (`typed` dev) | $F_{0.5}$ (`untyped` dev) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **`All_O`** | — | — | 0 | 0 | 263 | 0.000000 | 0.000000 | **0.000000** | 0.000000 |
| **`POS`** | Luật từ loại | — | 36 | 222 | 227 | 0.139535 | 0.136882 | **0.138996** | 0.142857 |
| **`LR_base`** | `C = 1.0` | `0.45` | 38 | 112 | 225 | 0.253333 | 0.144487 | **0.220162** | 0.231750 |
| **`LR_parser`** | `C = 0.1` | `0.35` | 27 | 55 | 236 | 0.329268 | 0.102662 | **0.228426** | 0.236887 |
| **`kNN`** | `k = 10` | `0.80` | 10 | 79 | 253 | 0.112360 | 0.038023 | **0.080775** | 0.088853 |

*(Lưu ý: Mô hình tham chiếu tạo danh sách 63 FP ở Tuần 9 là `LR_reference_C3_tau065` với `C = 3.0, tau = 0.65`, có `typed` $\text{TP}/\text{FP}/\text{FN} = 28/65/235, F_{0.5} = 0.220472$ và `untyped` $\text{TP}/\text{FP}/\text{FN} = 30/63/233, F_{0.5} = 0.236220$).*

---

## 2. MỤC 4 TRONG BÁO CÁO: Rà soát 63 ca FP của `LR_reference_C3_tau065`

### 2.1. Quy trình & Khai báo phương pháp (`review_status.json`)
- Danh sách 63 ca FP thuộc **mô hình tham chiếu `LR_reference_C3_tau065` trên tập `dev`** ($\text{TP} = 30, \text{FP} = 63$ theo `untyped`, tổng $93$ cảnh báo).
- Nhóm chọn phiếu TV1 làm phiếu chung ([`outputs/dev_run_001/baseline_ref/review_consensus.csv`](outputs/dev_run_001/baseline_ref/review_consensus.csv) và [`Group02_FP63_Consensus.xlsx`](outputs/dev_run_001/baseline_ref/Group02_FP63_Consensus.xlsx)), giữ riêng hai phiếu nguồn.
- **Khai báo minh bạch:** Hai phiếu có sẵn xuất phát từ bản nháp có AI hỗ trợ (`review_forms_filled = true`, `independent_reviews_complete = false`, `disagreements_before_discussion = null`). Sự trùng khớp nhãn giữa hai phiếu không được dùng làm bằng chứng cho hai lượt gán nhãn độc lập ban đầu hay tính hệ số Kappa.

### 2.2. Bảng 3 dòng phân loại 63 ca FP

| Nhóm đọc lỗi | Số ca | Tỷ lệ (/ 63 FP) | Ý nghĩa & Chi tiết |
| :---: | :---: | :---: | :--- |
| **`A`** | **34** | $53.97\%$ | Token được đánh dấu phù hợp ngữ pháp theo cách đọc hiện tại (báo động giả thật sự). |
| **`B`** | **14** | $22.22\%$ | Có thể có lỗi tại token nhưng `gold` không chú thích: gồm **10 ca thuộc 3 nhãn mục tiêu** (`SVA`: 5, `VFORM`: 3, `NNUM`: 2), **3 ca loại `Khác`** ngoài phạm vi và **1 ca `Chưa xác định`** thì. |
| **`C`** | **15** | $23.81\%$ | Mơ hồ / chưa đủ ngữ cảnh để kết luận. |
| **Tổng** | **63** | **$100\%$** | |

### 2.3. Các kịch bản Precision vị trí ($\text{P} = \frac{30 + b}{93}$)

| Cách tính từ nhãn hiện có | Công thức | Precision vị trí |
| :--- | :---: | :---: |
| Theo `gold` ban đầu ($b = 0$) | $30 / 93$ | **$32.26\%$** |
| Kịch bản cộng 10 ca `B` thuộc 3 nhãn (`SVA`/`VFORM`/`NNUM`) | $(30 + 10) / 93 = 40 / 93$ | **$43.01\%$** *(cận trên cộng thêm 15 `C`: $55/93 = 59.14\%$)* |
| Kịch bản cộng toàn bộ 14 ca `B` (gồm cả ngoài phạm vi) | $(30 + 14) / 93 = 44 / 93$ | **$47.31\%$** *(cận trên cộng thêm 15 `C`: $59/93 = 63.44\%$)* |

*(Lưu ý: Không gọi $47.31\%$ là precision benchmark của 3 nhãn; các kịch bản này dùng để phân tích độ nhạy của đánh giá khi thiếu annotation, không thay thế `gold` và không áp sang mô hình cuối).*

---

## 3. MỤC 5 TRONG BÁO CÁO: Thí nghiệm nhánh `LR_parser` & Kiểm tra can thiệp `FP02`

### 3.1. Bảng đối chiếu 3 dòng trên tập `dev` (Từ [`Group02_Long_Report_Pack/report_tables/teacher_comparison_dev_Long.csv`](Group02_Long_Report_Pack/report_tables/teacher_comparison_dev_Long.csv))

| Nhánh mô hình | $C$ | Ngưỡng $\tau$ | `SVA` (TP / FP / FN / $F_{0.5}$) | `VFORM` (TP / FP / FN / $F_{0.5}$) | `NNUM` (TP / FP / FN / $F_{0.5}$) | `MICRO` Typed (TP / FP / FN / $P$ / $R$ / $F_{0.5}$) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **`LR_base_control`** | `1.0` | `0.45` | 12 / 41 / 62 / **0.209790** | 7 / 17 / 62 / **0.212121** | 19 / 54 / 101 / **0.230583** | 38 / 112 / 225 / 0.253333 / 0.144487 / **0.220162** |
| **`LR_parser_control`** *(cùng $C, \tau$)* | `1.0` | `0.45` | 11 / 41 / 63 / **0.195035** | 8 / 37 / 61 / **0.160643** | 19 / 44 / 101 / **0.255376** | 38 / 122 / 225 / 0.237500 / 0.144487 / **0.210410** |
| **`LR_parser_selected`** *(quy tắc chọn)* | `0.1` | `0.35` | 12 / 16 / 62 / **0.322581** | 5 / 15 / 64 / **0.167785** | 10 / 24 / 110 / **0.195312** | 27 / 55 / 236 / 0.329268 / 0.102662 / **0.228426** |

- **Diễn giải tách bạch 2 phép so sánh:**
  1. **So sánh tại cùng điểm quyết định `C = 1.0, tau = 0.45` (`LR_base_control` vs `LR_parser_control`):** Tổng $\text{TP}$ typed giữ nguyên ở $38$, tổng $\text{FP}$ tăng từ $112 \rightarrow 122$; riêng nhãn `SVA`, $\text{TP}$ giảm từ $12 \rightarrow 11$ và $\text{FP}$ giữ nguyên ở $41$ ($F_{0.5}$ giảm từ $0.209790 \rightarrow 0.195035$). Như vậy, **tại cùng điểm quyết định $C=1.0, \tau=0.45$, việc thêm 3 đặc trưng parser không tự làm giảm $\text{FP}$ của `SVA`** (chỉ giảm $\text{FP}$ của `NNUM` từ $54 \rightarrow 44$).
  2. **So sánh cấu hình được chọn (`LR_base` $C=1.0, \tau=0.45$ vs `LR_parser_selected` $C=0.1, \tau=0.35$):** Khi áp dụng quy tắc chọn, `LR_parser` chuyển sang $C = 0.1, \tau = 0.35$ (điều chuẩn $L_2$ mạnh hơn), giúp giảm $\text{FP}$ của `SVA` từ $41 \rightarrow 16$ (giữ $\text{TP} = 12$, nâng $F_{0.5}$ của `SVA` lên $0.322581$). Sự giảm $\text{FP}$ này là hiệu ứng kết hợp của việc thay đổi $C/\tau$ cùng đặc trưng parser, không gán toàn bộ chênh lệch đó riêng cho việc thêm parser.

### 3.2. Kết quả chạy kiểm tra can thiệp đặc trưng tại `FP02` (`scripts/fp02_intervention_dev.py`)
Đã chạy trên mô hình thật `models/lr_parser_C1.0_e0148c2ee98e1443.joblib` ($C = 1.0, \tau = 0.45$) tại bản ghi `dev:001408`, token 3 `realize` (lưu tại [`outputs/fp02_intervention_dev_2026-11-03T201902_0700/fp02_feature_intervention_dev.csv`](outputs/fp02_intervention_dev_2026-11-03T201902_0700/fp02_feature_intervention_dev.csv)):

| Kịch bản (`scenario`) | Chủ ngữ (`tag` / `number` / `dist`) | Đặc trưng thay đổi so với `as_parsed` | $p_{\text{O}}$ | $p_{\text{SVA}}$ | $p_{\text{error}} = 1 - p_{\text{O}}$ | Dự đoán ($\tau = 0.45$) |
| :--- | :---: | :--- | :---: | :---: | :---: | :---: |
| **`as_parsed`** *(Thực tế `spaCy`)* | `NNS` / `Plur` / `-2` (`people`) | `[]` | 0.006980 | 0.987796 | **0.993020** | `SVA` |
| **`manual_people`** | `NNS` / `Plur` / `-2` (`people`) | `[]` *(Trùng hệt `as_parsed`)* | 0.006980 | 0.987796 | **0.993020** | `SVA` |
| **`manual_today`** *(Giả định lấy `today`)* | `NN` / `Sing` / `-1` (`today`) | Đổi sang `NN`, `Sing`, `-1` | 0.010269 | 0.978973 | **0.989731** | `SVA` |

- **Ý nghĩa kết quả can thiệp `FP02`:**
  - Thực tế `spaCy` đã bắt đúng chủ ngữ của `realize` là `people` (`NNS`, `Plur`, khoảng cách `-2`), nên `as_parsed` và `manual_people` hoàn toàn trùng nhau.
  - Sở dĩ ở $C = 1.0, \tau = 0.45$ mô hình vẫn dự đoán `SVA` ($p_{\text{error}} = 0.993020$) là vì: (1) Các đặc trưng cửa sổ cục bộ (`pos=VBP`, `p-1|p=NN|VBP`, `p-1=NN`, `subj_w=today`) vẫn giữ nguyên trong vector đặc trưng với trọng số dương rất lớn cho lớp `SVA`; và (2) Ba đặc trưng `dep_subj_pos=NNS`, `dep_subj_number=Plur`, `dep_subj_distance=-2` được đưa vào độc lập (không ghép chéo với nhãn động từ `VBP` thành cặp kiểm tra hòa hợp `Plur|VBP`), nên bản thân `dep_subj_pos=NNS` và `dep_subj_number=Plur` cũng mang hệ số dương đối với `SVA`.

### 3.3. Phân biệt lỗi gán cây của Parser và giới hạn trích xuất đặc trưng trên 4 ca chẩn đoán
(Chi tiết lưu tại [`outputs/fixed_point_check/parser_limitation_cases.csv`](outputs/fixed_point_check/parser_limitation_cases.csv) và [`outputs/dev_run_001/parser_four_cases.csv`](outputs/dev_run_001/parser_four_cases.csv)):
1. **`FP02` (`dev:001408`, token 3 `realize`, `gold=O`):** *Không phải lỗi của `spaCy`* (`spaCy` lấy đúng `people`, `NNS`, `Plur`, `-2`). Giới hạn nằm ở biểu diễn đặc trưng giữ nguyên `subj_w=today`, `p-1|p=NN|VBP` và không có đặc trưng tương tác giữa số của chủ ngữ với nhãn động từ.
2. **`FP03` (`dev:000644`, token 6 `is`, `gold=O`):** *`spaCy` bắt đúng đầu ngữ chủ ngữ danh động từ* là `learning` (`VBG`, `-3`) thay vì danh từ số nhiều `languages` (`NNS`) đứng cạnh `is`. Tuy nhiên, cách trích xuất hiện tại đọc thuộc tính `Morph.get("Number")` của `VBG` ra rỗng nên gán `dep_subj_number=<UNK>` (có trọng số dương với `SVA`) thay vì quy mệnh đề `VBG` về ngôi thứ 3 số ít (`Sing`).
3. **`FN01` (`dev:001866`, token 39 `is`, `gold=SVA`):** *`spaCy` bắt đúng chủ ngữ đảo nằm bên phải* là `reasons` (`NNS`, `Plur`, khoảng cách `+2` trong *"what is our reasons"*). Xác suất lỗi có tăng từ $0.011861$ (`LR_base`) lên $0.034733$ ($C=1.0$) và $0.069654$ ($C=0.1$), nhưng biên quyết định tổng vẫn âm do ngữ cảnh xung quanh kéo về lớp `O`.
4. **`FN04` (`dev:001892`, token 11 `is`, `gold=SVA`):** *Lỗi phân tích cây trên câu ghép thiếu dấu câu (comma splice)* *"Second is safety , compared to other the chances of accidents is less ."* — `spaCy` gắn động từ `is` thứ hai (token 11) làm `ccomp` của `is` đầu câu và không gắn cạnh con thuộc tập `{nsubj, nsubjpass, expl, csubj, csubjpass}` vào `is` thứ hai, khiến bộ trích xuất trả về `subject_text=<NONE>, dep_subj_number=<UNK>`. Kết quả là `LR_parser` ($p_{\text{error}} = 0.073707$ ở $C=1.0$; $0.150214$ ở $C=0.1$) bỏ sót lỗi mà `LR_base` ($p_{\text{error}} = 0.473200$) bắt được nhờ cụm cục bộ `accidents is`.

---

## 4. MỤC 6 TRONG BÁO CÁO: Kết quả đánh giá trên tập `test` (272 vị trí `gold`)

Đánh giá tập `test` của triển khai Long được thực hiện ngày **03/11/2026** (`2026-11-03T13:19:00+07:00` $\rightarrow$ `13:19:38+07:00`) và lưu tại [`outputs/final_test_cc1e75b079e005f0/`](outputs/final_test_cc1e75b079e005f0/) (`2.364` bản ghi hợp lệ / `2.416` bản ghi gốc, `68.560` token, tổng **`272` lỗi gold**: `SVA = 73`, `VFORM = 76`, `NNUM = 123`).

### Bảng 6A: Kết quả `MICRO` trên tập `test` (Đối chiếu `typed` và `untyped`)

| Hệ thống | Cấu hình đã khóa từ `dev` | Chế độ chấm | TP | FP | FN | Precision ($P$) | Recall ($R$) | $F_1$ | **$F_{0.5}$ (Test)** | $F_{0.5}$ (Dev) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **`All_O`** | Luôn đoán `O` | `typed` | 0 | 0 | 272 | 0.000000 | 0.000000 | 0.000000 | **0.000000** | 0.000000 |
| | | `untyped` | 0 | 0 | 272 | 0.000000 | 0.000000 | 0.000000 | **0.000000** | 0.000000 |
| **`POS`** | Luật từ loại | `typed` | 31 | 217 | 241 | 0.125000 | 0.113971 | 0.119231 | **0.122627** | 0.138996 |
| | | `untyped` | 32 | 216 | 240 | 0.129032 | 0.117647 | 0.123077 | **0.126582** | 0.142857 |
| **`LR_base`** | `C = 1.0, tau = 0.45` | `typed` | **41** | 154 | **231** | 0.210256 | **0.150735** | **0.175589** | **0.194867** | 0.220162 |
| | | `untyped` | **43** | 152 | **229** | 0.220513 | **0.158088** | **0.184154** | **0.204373** | 0.231750 |
| **`kNN`** | `k = 10, tau = 0.80` | `typed` | 14 | 72 | 258 | 0.162791 | 0.051471 | 0.078212 | **0.113636** | 0.080775 |
| | | `untyped` | 14 | 72 | 258 | 0.162791 | 0.051471 | 0.078212 | **0.113636** | 0.088853 |
| **`LR_parser`** | `C = 0.1, tau = 0.35` | `typed` | 27 | **79** | 245 | **0.254717** | 0.099265 | 0.142857 | **0.193966** | **0.228426** |
| | | `untyped` | 27 | **79** | 245 | **0.254717** | 0.099265 | 0.142857 | **0.193966** | **0.236887** |

### Bảng 6B: Kết quả `typed` theo từng nhãn trên tập `test`

| Hệ thống | Nhãn | Gold | TP | FP | FN | Precision ($P$) | Recall ($R$) | $F_1$ | **$F_{0.5}$** |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **`All_O`** | `SVA` / `VFORM` / `NNUM` | 73 / 76 / 123 | 0 | 0 | 73 / 76 / 123 | 0.000000 | 0.000000 | 0.000000 | **0.000000** |
| **`POS`** | `SVA` | 73 | 14 | 136 | 59 | 0.093333 | 0.191781 | 0.125561 | **0.104012** |
| | `VFORM` | 76 | 7 | 38 | 69 | 0.155556 | 0.092105 | 0.115702 | **0.136719** |
| | `NNUM` | 123 | 10 | 43 | 113 | 0.188679 | 0.081301 | 0.113636 | **0.149254** |
| **`LR_base`** | `SVA` | 73 | 14 | 66 | 59 | 0.175000 | 0.191781 | 0.183007 | **0.178117** |
| | `VFORM` | 76 | 8 | 22 | 68 | 0.266667 | 0.105263 | 0.150943 | **0.204082** |
| | `NNUM` | 123 | **19** | 66 | 104 | **0.223529** | **0.154472** | **0.182692** | **0.205184** |
| **`kNN`** | `SVA` | 73 | 5 | 26 | 68 | 0.161290 | 0.068493 | 0.096154 | **0.126904** |
| | `VFORM` | 76 | 1 | 12 | 75 | 0.076923 | 0.013158 | 0.022472 | **0.039062** |
| | `NNUM` | 123 | 8 | 34 | 115 | 0.190476 | 0.065041 | 0.096970 | **0.137457** |
| **`LR_parser`** | `SVA` | 73 | 10 | **30** | 63 | **0.250000** | 0.136986 | 0.176991 | **0.214592** |
| | `VFORM` | 76 | 7 | **12** | 69 | **0.368421** | 0.092105 | 0.147368 | **0.230263** |
| | `NNUM` | 123 | 10 | 37 | 113 | 0.212766 | 0.081301 | 0.117647 | **0.160772** |

### Nhận xét chính xác cho Mục 6:
- **So sánh thứ hạng `dev` và `test`:**
  - Trên `dev` (`typed MICRO` $F_{0.5}$): `LR_parser` ($0.228426$) $>$ `LR_base` ($0.220162$) $>$ `POS` ($0.138996$) $>$ `kNN` ($0.080775$) $>$ `All_O` ($0.000000$).
  - Trên `test` (`typed MICRO` $F_{0.5}$): `LR_base` ($0.194867$) $>$ `LR_parser` ($0.193966$) $>$ `POS` ($0.122627$) $>$ `kNN` ($0.113636$) $>$ `All_O` ($0.000000$).
  - Cả hai nhánh `LR` đều vượt rõ rệt `POS` và `kNN` trên cả `dev` lẫn `test` (`POS` luôn xếp trên `kNN` ở cả hai tập). So với `POS` trên `test`, `LR_base` tìm đúng thêm $10$ lỗi ($\text{TP}$ từ $31 \rightarrow 41$) và giảm $63$ báo động giả ($\text{FP}$ từ $217 \rightarrow 154$).
  - Giữa `LR_base` và `LR_parser`: trên `dev`, `LR_parser` được chọn có $F_{0.5}$ cao hơn `LR_base` ($0.228426$ vs $0.220162$); trên `test`, `LR_parser` đạt Precision cao hơn ($25.47\%$ vs $21.03\%$, giảm $\text{FP}$ từ $154 \rightarrow 79$) và đạt $F_{0.5}$ cao hơn ở `SVA` ($0.214592$ vs $0.178117$) cùng `VFORM` ($0.230263$ vs $0.204082$), nhưng có Recall thấp hơn ở `NNUM` ($\text{TP}=10$ vs $19$), dẫn đến $F_{0.5}$ micro trên `test` thấp hơn nhẹ so với `LR_base` ($0.193966$ vs $0.194867$). Hai điểm `test` rất sát nhau này phản ánh sự đánh đổi Precision–Recall giữa hai cấu hình đã chọn ($C=1.0, \tau=0.45$ vs $C=0.1, \tau=0.35$), không chứng minh sự tương đương hay khác biệt có ý nghĩa thống kê.
