# TỔNG HỢP KẾT QUẢ CHÍNH THỨC CHO BÁO CÁO — NHÓM 2 (GROUP 02)
**Bản triển khai:** `Explainable_GEC_Long` (Đã đồng bộ 100% với `Group02_Long_Report_Pack` ngày 03/11/2026)

Tài liệu này tổng hợp đầy đủ các bảng số liệu, công thức và nhận xét đã đối chiếu chính xác với các file CSV trong [`Group02_Long_Report_Pack/report_tables/`](Group02_Long_Report_Pack/report_tables/) và đầu ra đã lưu của Long.

---

## 1. MỤC 3 TRONG BÁO CÁO: Quy tắc chọn mô hình & Cấu hình đã khóa trên `dev`

- **Quy tắc chọn điểm vận hành trong code ([`gec/models.py`](gec/models.py), [`configs/dev.json`](configs/dev.json)):**
  - **Đối với `LR_base` và `LR_parser` (`select_lr`):**
    1. Lưới tham số: $C \in \{0.1, 0.3, 1.0, 3.0\} \times \tau \in \{0.05, 0.10, \dots, 0.95\}$ ($76$ cấu hình/mô hình).
    2. Trong mỗi giá trị $C$, chọn ngưỡng $\tau$ tối đa hóa **$F_{0.5}$ micro có nhãn (`typed MICRO F0.5`)** trên tập `dev`; nếu hòa điểm thì ưu tiên Precision (`P`) cao hơn rồi đến ngưỡng $\tau$ cao hơn.
    3. Giữa các đại diện tốt nhất của từng $C$ (`per_C_best`), chọn **$C$ nhỏ nhất** (điều chuẩn mạnh nhất) có $F_{0.5}$ thấp hơn mức cực đại **dưới `near_tie_C_margin = 0.005`** (`maximum - row['F0.5'] < 0.005`, dùng số thực chưa làm tròn theo đúng [`gec/models.py`](gec/models.py)).
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

- **Ý nghĩa kết quả can thiệp `FP02` (Tách bạch quan sát và giả thuyết):**
  - **Quan sát trực tiếp trên đầu ra:** `spaCy` đã trích xuất đúng chủ ngữ của `realize` là `people` (`NNS`, `Plur`, khoảng cách `-2`), nên `as_parsed` và `manual_people` hoàn toàn trùng nhau ($p_{\text{error}} = 0.993020$). Khi thay riêng 3 đặc trưng chủ ngữ sang `today` (`NN`, `Sing`, `-1`) trên cùng mô hình $C = 1.0, \tau = 0.45$, xác suất lỗi chỉ thay đổi rất nhẹ từ $0.993020 \rightarrow 0.989731$ và dự đoán vẫn là `SVA`.
  - **Giả thuyết cơ chế:** Trong biểu diễn hiện tại, các đặc trưng cửa sổ cục bộ (`pos=VBP`, `p-1|p=NN|VBP`, `p-1=NN`, `subj_w=today`) vẫn được giữ nguyên trong vector đặc trưng, và ba đặc trưng `dep_subj_pos=NNS`, `dep_subj_number=Plur`, `dep_subj_distance=-2` được đưa vào dưới dạng đơn lẻ (không ghép chéo với nhãn động từ `VBP` thành cặp kiểm tra hòa hợp `Plur|VBP`), nên sự thay đổi của riêng 3 đặc trưng chủ ngữ chưa đủ làm đổi dấu tổng điểm quyết định.

### 3.3. Quan sát đầu ra và giả thuyết giới hạn trên 4 ca chẩn đoán
(Chi tiết lưu tại [`outputs/fixed_point_check/parser_limitation_cases.csv`](outputs/fixed_point_check/parser_limitation_cases.csv) và [`outputs/dev_run_001/parser_four_cases.csv`](outputs/dev_run_001/parser_four_cases.csv); tập quan hệ chủ ngữ trong [`gec/dependency.py`](gec/dependency.py) là `SUBJECT_DEPS = {'nsubj', 'nsubjpass', 'csubj', 'csubjpass'}`, **không có `expl`**):
1. **`FP02` (`dev:001408`, token 3 `realize`, `gold=O`):**
   - *Quan sát:* `spaCy` trích xuất đúng `people` (`NNS`, `Plur`, `-2`); dự đoán ở cả `LR_base` ($C=1.0$), `LR_parser` ($C=1.0$) và `LR_parser` ($C=0.1$) đều vẫn là `SVA`.
   - *Giả thuyết:* Không phải lỗi gán cây của `spaCy`; có thể do các đặc trưng cục bộ (`subj_w=today`, `p-1|p=NN|VBP`) vẫn giữ nguyên và thiếu đặc trưng tương tác chéo giữa số của chủ ngữ với nhãn động từ.
2. **`FP03` (`dev:000644`, token 6 `is`, `gold=O`):**
   - *Quan sát:* `spaCy` trích xuất đầu ngữ chủ ngữ danh động từ là `learning` (`VBG`, `-3`) thay vì danh từ số nhiều `languages` (`NNS`) đứng cạnh `is`, nhưng `subject_number` nhận giá trị `<UNK>` và dự đoán vẫn là `SVA` ($p_{\text{error}} = 0.790195$ ở $C=1.0$; $0.400730$ ở $C=0.1$).
   - *Giả thuyết:* Token `VBG` trong `spaCy` không có thuộc tính hình thái `Number` nên hàm `describe()` gán `dep_subj_number=<UNK>` thay vì quy chủ ngữ danh động từ về ngôi thứ 3 số ít (`Sing`), khiến mô hình chưa nhận được tín hiệu hòa hợp số ít rõ ràng.
3. **`FN01` (`dev:001866`, token 39 `is`, `gold=SVA`):**
   - *Quan sát:* Trong cấu trúc *"what is our reasons"*, `spaCy` trích xuất chủ ngữ bên phải là `reasons` (`NNS`, `Plur`, khoảng cách `+2`). Xác suất lỗi tăng từ $0.011861$ (`LR_base`) lên $0.034733$ ($C=1.0$) và $0.069654$ ($C=0.1$), nhưng vẫn dưới ngưỡng nên dự đoán là `O`.
   - *Giả thuyết:* Tín hiệu chủ ngữ số nhiều bên phải có đẩy xác suất lỗi tăng lên theo chiều kỳ vọng, nhưng tổng biên quyết định vẫn âm có thể do các đặc trưng ngữ cảnh cục bộ xung quanh (`what is our ...`) nghiêng mạnh về lớp `O`.
4. **`FN04` (`dev:001892`, token 11 `is`, `gold=SVA`):**
   - *Quan sát:* Trong câu *"Second is safety , compared to other the chances of accidents is less ."*, tại động từ `is` thứ hai (token 11), hàm `describe()` trả về `subject_text=<NONE>, subject_tag=<NONE>, subject_number=<UNK>, subject_relation=none` vì token 11 không có con trực tiếp thuộc `SUBJECT_DEPS = {'nsubj', 'nsubjpass', 'csubj', 'csubjpass'}`. Xác suất lỗi giảm từ $0.473200$ (`LR_base` dự đoán `SVA`) xuống $0.073707$ ($C=1.0$, dự đoán `O`) và $0.150214$ ($C=0.1$, dự đoán `O`).
   - *Giả thuyết:* Trong câu ghép nối bằng dấu phẩy (comma splice), cây phụ thuộc và quy tắc chỉ tìm con trực tiếp trong `SUBJECT_DEPS` (hoặc qua head của `aux`/`auxpass`/`cop`) không lấy được danh ngữ `chances` phía trước, dẫn tới mất tín hiệu chủ ngữ và gây ra 1 ca hồi quy FN so với `LR_base`.

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

---

## 5. LỊCH SỬ HAI ĐỢT ĐÁNH GIÁ `TEST` CỦA NHÓM & BẢNG ĐÓNG GÓP THỰC TẾ

### 5.1. Khai báo minh bạch lịch sử hai đợt đánh giá `test` của Nhóm 02
- Trong quá trình hoàn thiện đồ án, Nhóm 02 tồn tại hai nhánh chạy độc lập trước khi thống nhất chọn bản triển khai chính thức:
  1. **Đợt chạy ngày 02/11/2026 (bản triển khai song song trước khi đồng bộ):** Dùng quy ước khoảng cách chủ ngữ của parser khác bản Long và ngưỡng `kNN` $\tau = 0.75$; nhánh này đã được chấm trên `test` ngày 02/11/2026. Kết quả của đợt này không dùng làm số chính thức trong báo cáo.
  2. **Đợt chạy ngày 03/11/2026 trên bản triển khai được chọn (`Explainable_GEC_Long`):** Toàn bộ mô hình và tham số của bản Long đã được khóa trên `dev` (`locked_at = 2026-10-22T20:52:41+07:00`) tại [`outputs/dev_run_001/config_locked.json`](outputs/dev_run_001/config_locked.json) (`LR_base`: $C=1.0, \tau=0.45$; `LR_parser`: $C=0.1, \tau=0.35$; `kNN`: $k=10, \tau=0.80$). Ngày 03/11/2026, nhóm chạy `run_final_test.py --authorize-test` đúng một lần trên bản Long (lưu tại [`outputs/final_test_cc1e75b079e005f0/`](outputs/final_test_cc1e75b079e005f0/)) để có bộ số liệu `dev`–`test` đồng nhất từ cùng một pipeline.
- **Cam kết nguyên tắc đánh giá:** Nhóm **không dùng kết quả `test` của bất kỳ đợt nào để quay lại chọn hay chỉnh sửa $C$, $k$, ngưỡng $\tau$, đặc trưng hay trọng số mô hình**. Báo cáo chính thức sử dụng nhất quán số liệu của bản `Explainable_GEC_Long` và khai báo rõ lịch sử hai đợt chạy này (không tuyên bố cả nhóm chỉ mở `test` duy nhất một lần).

### 5.2. Bảng đóng góp thực tế của từng thành viên và khai báo sử dụng AI

| Thành viên | Vai trò & Phần việc thực tế đã thực hiện | Sản phẩm / File bằng chứng trong gói nộp |
| :--- | :--- | :--- |
| **Nguyễn Thành Long** | • Sửa lỗi căn chỉnh vị trí token (`offset = len(target) + 1`) và xây dựng pipeline dữ liệu, tiền xử lý (`gec/data.py`).<br>• Triển khai và huấn luyện toàn bộ 5 hệ thống (`All_O`, `POS`, `LR_base`, `LR_parser`, `kNN`), quy tắc chọn mô hình `select_lr`, khóa cấu hình `config_locked.json`.<br>• Tích hợp `spaCy` dependency parser (`gec/dependency.py`), chạy kiểm tra cùng điểm quyết định `C=1.0, tau=0.45` (`scripts/decode_parser_fixed_point.py`) và thí nghiệm can thiệp đặc trưng chủ ngữ tại `FP02` (`scripts/fp02_intervention_dev.py`).<br>• Chạy đánh giá `test` cuối cùng (`run_final_test.py`), viết unit tests (`tests/`), kiểm tra độc lập (`verify_run.py`) và đóng gói bàn giao (`EXPECT_Long_Dev.ipynb`, `LONG_HANDOFF.md`). | `gec/*.py`, `run_dev.py`, `run_final_test.py`, `verify_run.py`, `scripts/*.py`, `tests/*.py`, `models/*.joblib`, `outputs/dev_run_001/`, `outputs/fixed_point_check/`, `outputs/fp02_intervention_dev_*/`, `outputs/final_test_cc1e75b079e005f0/`, `EXPECT_Long_Dev.ipynb` |
| **Vũ Thị Loan (TV1)** | • Phiếu rà soát 63 ca FP của mô hình tham chiếu `LR_reference_C3_tau065` trên `dev` (bản gốc `raw_TV1_Loan.csv`, ngày ghi trên phiếu 2026-10-27), được nhóm chọn làm phiếu chung `review_consensus.csv`.<br>• Phân loại `A = 34`, `B = 14` (`10` ca thuộc 3 nhãn mục tiêu, `3` ca loại khác, `1` ca chưa xác định), `C = 15` kèm lý do/gợi ý sửa từng ca.<br>• *(Phần việc khác — báo cáo, slide... — nhóm tự bổ sung theo thực tế.)* | `outputs/dev_run_001/baseline_ref/raw_TV1_Loan.csv`, `review_Loan.csv`, `review_consensus.csv`, `Group02_FP63_Consensus.xlsx` |
| **Mai Hải Yến (TV2)** | • Phiếu rà soát 63 ca FP của mô hình tham chiếu `LR_reference_C3_tau065` (bản gốc `raw_TV2_Yen.csv`, chuẩn hóa tại `review_Yen.csv`).<br>• *(Phần việc khác — báo cáo, slide, gói `Group02_Long_Report_Pack`... — nhóm tự bổ sung theo thực tế.)* | `outputs/dev_run_001/baseline_ref/raw_TV2_Yen.csv`, `review_Yen.csv`, `independent_comparison.csv` |

- **Khai báo sử dụng AI hỗ trợ:** Nhóm có sử dụng công cụ AI để hỗ trợ viết script kiểm tra/đóng gói, chuẩn hóa định dạng bảng biểu và tạo bản nháp gợi ý ban đầu cho phiếu rà soát 63 ca FP. Vì hai phiếu `raw_TV1_Loan.csv` và `raw_TV2_Yen.csv` cùng xuất phát từ bản nháp có AI hỗ trợ, nhóm ghi nhận trung thực trong `review_status.json` rằng `review_forms_filled = true`, `independent_reviews_complete = false`, `disagreements_before_discussion = null` và không dùng sự trùng khớp giữa hai phiếu để báo cáo độ đồng thuận độc lập ban đầu.
