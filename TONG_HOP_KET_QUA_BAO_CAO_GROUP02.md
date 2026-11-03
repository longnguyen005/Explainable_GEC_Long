# TỔNG HỢP KẾT QUẢ CHÍNH THỨC CHO BÁO CÁO & VẤN ĐÁP — NHÓM 2 (GROUP 02)
**Đề tài:** EXPECT — Phát hiện token lỗi ngữ pháp `SVA`, `VFORM`, `NNUM` có khả năng giải thích

Tài liệu này tổng hợp đầy đủ các bảng số liệu, công thức, nhận xét và kịch bản vấn đáp cá nhân đã hoàn tất theo đúng **Nhận xét Tuần 10 của Thầy Khánh** và **Rubric Đồ án cuối kỳ**. Các thành viên trong nhóm có thể copy trực tiếp từng mục vào file Báo cáo.

---

## 1. MỤC 3 TRONG BÁO CÁO: Quy tắc chọn mô hình (24/10) & Khóa cấu hình trước khi mở `test`

- **Quy tắc chọn điểm vận hành (đã cài đặt trong [`gec/models.py`](gec/models.py)):**
  - Trên tập `dev`, dò lưới các cấu hình của từng mô hình:
    - `LR_base` và `LR_parser`: $C \in \{0.1, 0.3, 1.0, 3.0\} \times \tau \in \{0.05, 0.10, \dots, 0.95\}$ ($76$ cấu hình/mô hình).
    - `kNN`: $k \in \{3, 5, 7, 11\} \times \tau \in \{0.05, 0.10, \dots, 0.95\}$ ($76$ cấu hình).
  - **Tiêu chí chọn duy nhất (Quy tắc 24/10):** Chọn cấu hình tối đa hóa **$F_{0.5}$ micro có nhãn (`typed MICRO F0.5`)** trên tập `dev`. Nếu hai cấu hình có $F_{0.5}$ chênh nhau dưới $10^{-12}$, ưu tiên theo thứ tự:
    1. Precision (`typed MICRO P`) cao hơn;
    2. Tổng số cảnh báo dương tính ($\text{TP} + \text{FP}$) ít hơn;
    3. Hệ số điều chuẩn $C$ nhỏ hơn (hoặc $k$ lớn hơn đối với `kNN`);
    4. Ngưỡng xác suất $\tau$ lớn hơn.
- **Điểm vận hành được chọn và khóa cứng tại [`outputs/dev_run_001/config_locked.json`](outputs/dev_run_001/config_locked.json) (toàn bộ 228 dòng lưới lưu tại [`outputs/dev_run_001/tuning_grid.csv`](outputs/dev_run_001/tuning_grid.csv)):**
  - **`LR_base`:** $C = 1.0, \tau = 0.45$ ($\text{TP}=38, \text{FP}=112, \text{FN}=225, P=0.2533, R=0.1445, F_{0.5}=0.2202$).
  - **`LR_parser`:** $C = 0.1, \tau = 0.35$ ($\text{TP}=27, \text{FP}=55, \text{FN}=236, P=0.3293, R=0.1027, F_{0.5}=0.2284$).
  - **`kNN`:** $k = 7, \tau = 0.60$ ($\text{TP}=16, \text{FP}=45, \text{FN}=247, P=0.2623, R=0.0608, F_{0.5}=0.1656$).

---

## 2. MỤC 4 TRONG BÁO CÁO: Kết quả rà soát 63 ca FP trên `dev` & Tính lại Precision vị trí

### 2.1. Quy trình thực hiện (Công bố minh bạch có AI hỗ trợ)
Trên 63 ca báo động giả (False Positives) của mô hình tham chiếu `LR_reference_C3_tau065` ($\text{TP} = 30, \text{FP} = 63$, tổng $93$ cảnh báo trên tập `dev`), nhóm sử dụng công cụ AI để tạo bản gợi ý phân loại sơ bộ kèm giải thích ngữ pháp tiếng Việt, sau đó hai thành viên **Vũ Thị Loan (TV1)** ([`review_Loan.csv`](outputs/dev_run_001/baseline_ref/review_Loan.csv)) và **Mai Hải Yến (TV2)** ([`review_Yen.csv`](outputs/dev_run_001/baseline_ref/review_Yen.csv)) trực tiếp rà soát, kiểm chứng lại toàn bộ 63/63 câu trên ngữ cảnh câu gốc và thống nhất nhãn cuối cùng tại [`review_consensus.csv`](outputs/dev_run_001/baseline_ref/review_consensus.csv). Vì hai thành viên làm việc dựa trên cùng bản gợi ý có AI hỗ trợ nên nhóm công bố minh bạch quy trình này và **không** sử dụng sự trùng khớp giữa hai phiếu để báo cáo tỷ lệ đồng thuận độc lập hay hệ số Kappa.

### 2.2. Bảng 3 dòng phân loại 63 ca FP (Từ [`review_status.json`](outputs/dev_run_001/baseline_ref/review_status.json))

| Nhóm phân loại | Ký hiệu | Số ca | Tỷ lệ (/ 63 FP) | Chi tiết theo loại lỗi |
| :--- | :---: | :---: | :---: | :--- |
| **(a) Báo động giả thật sự** *(Câu gốc đã đúng ngữ pháp tại token bị bắt)* | `A` | **34** | $53.97\%$ | Thường gặp ở câu có mệnh đề phụ/cụm giới từ xen giữa chủ ngữ và động từ (`FP02`, `FP03`), hoặc danh từ không đếm được/tập hợp. |
| **(b) Lỗi thật bị bộ dữ liệu bỏ sót** *(Missing gold annotation)* | `B` | **14** | $22.22\%$ | • **10 ca thuộc 3 nhãn mục tiêu:** `SVA`: 5 ca (`FP16`, `FP17`, `FP21`, `FP41`, `FP42`); `VFORM`: 3 ca (`FP18`, `FP31`, `FP48`); `NNUM`: 2 ca (`FP09`, `FP26`).<br>• **4 ca lỗi ngoài 3 nhãn:** 3 ca `Khác` (`FP05`, `FP32`, `FP59`) và 1 ca `Chưa xác định` (`FP43`). |
| **(c) Mơ hồ / cần thêm ngữ cảnh** *(Đều chấp nhận được tùy cách hiểu)* | `C` | **15** | $23.81\%$ | Các trường hợp phụ thuộc văn cảnh đoạn văn (thì quá khứ/hiện tại, số ít/số nhiều theo ý người viết). |
| **Tổng cộng** | | **63** | **$100\%$** | |

### 2.3. Công thức tính lại Precision vị trí (Sửa lỗi hiển thị Mục 4.3)
$$\text{P} = \frac{30 + b}{93}$$
- **Trước khi đọc lại ($b = 0$):** $\text{P}_{\text{gốc}} = \frac{30}{93} = 32.26\%$.
- **Khi chỉ tính $b = 10$ ca nhóm `(b)` thuộc đúng 3 nhãn mục tiêu (`SVA`, `VFORM`, `NNUM`):**
  $$\text{P}_{\text{hiệu chỉnh (3 nhãn)}} = \frac{30 + 10}{93} = \frac{40}{93} = \mathbf{43.01\%} \quad (\text{cận trên nếu cộng thêm } 15\text{ ca } C: \frac{55}{93} = 59.14\%)$$
- **Khi tính toàn bộ $b = 14$ ca nhóm `(b)` (gồm cả 4 ca ngoài 3 nhãn):**
  $$\text{P}_{\text{hiệu chỉnh (tất cả B)}} = \frac{30 + 14}{93} = \frac{44}{93} = \mathbf{47.31\%} \quad (\text{cận trên nếu cộng thêm } 15\text{ ca } C: \frac{59}{93} = 63.44\%)$$

---

## 3. MỤC 5 TRONG BÁO CÁO: Bảng đối chiếu 3 dòng nhánh `LR_parser` trên tập `dev`

Số liệu trích xuất từ [`outputs/dev_run_001/metrics_dev.csv`](outputs/dev_run_001/metrics_dev.csv) và [`outputs/fixed_point_check/metrics_parser_fixed_point.csv`](outputs/fixed_point_check/metrics_parser_fixed_point.csv) (file dự đoán từng token ở cùng điểm quyết định được lưu tại [`outputs/fixed_point_check/predictions_LR_parser_C1.0_tau0.45.csv`](outputs/fixed_point_check/predictions_LR_parser_C1.0_tau0.45.csv)):

| Dòng | Mô hình & Ngưỡng quyết định trên `dev` | `SVA` (TP / FP / FN / $F_{0.5}$) | `VFORM` (TP / FP / FN / $F_{0.5}$) | `NNUM` (TP / FP / FN / $F_{0.5}$) | `MICRO` Typed (TP / FP / FN / $P$ / $R$ / $F_{0.5}$) | `MICRO` Untyped ($F_{0.5}$) |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: |
| **1** | **`LR_base`** (`C=1.0, tau=0.45`) | 12 / 41 / 62 / **0.2098** | 7 / 17 / 62 / **0.2121** | 19 / 54 / 101 / **0.2306** | 38 / 112 / 225 / 0.2533 / 0.1445 / **0.2202** | **0.2367** |
| **2** | **`LR_parser` cùng ngưỡng với `LR_base`** (`C=1.0, tau=0.45`) | 11 / 41 / 63 / **0.1950** | 8 / 37 / 61 / **0.1606** | 19 / 44 / 101 / **0.2554** | 38 / 122 / 225 / 0.2375 / 0.1445 / **0.2104** | **0.2215** |
| **3** | **`LR_parser` chọn theo quy tắc 24/10** (`C=0.1, tau=0.35`) | 12 / 16 / 62 / **0.3226** | 5 / 15 / 64 / **0.1678** | 10 / 24 / 110 / **0.1953** | 27 / 55 / 236 / 0.3293 / 0.1027 / **0.2284** | **0.2369** |

- **Nhận xét cốt lõi cho Mục 5:**
  1. **Khi giữ cố định điểm quyết định `C=1.0, tau=0.45` (so Dòng 1 và Dòng 2):** Việc bổ sung đặc trưng cú pháp phụ thuộc từ `spaCy` chưa làm giảm $\text{FP}$ của `SVA` (vẫn là $41$, $\text{TP}$ giảm nhẹ $12 \rightarrow 11$, $F_{0.5}$ giảm từ $0.2098 \rightarrow 0.1950$), tăng $\text{FP}$ của `VFORM` ($17 \rightarrow 37$), và chỉ giúp giảm $\text{FP}$ ở `NNUM` ($54 \rightarrow 44$, nâng $F_{0.5}$ từ $0.2306 \rightarrow 0.2554$).
  2. **Khi chọn điểm vận hành theo quy tắc 24/10 (Dòng 3 — `C=0.1, tau=0.35`):** Hệ số điều chuẩn mạnh hơn ($C=0.1$) kết hợp với đặc trưng chủ ngữ cú pháp giúp cắt giảm mạnh $\text{FP}$ của `SVA` từ $41 \rightarrow 16$ trong khi giữ nguyên $\text{TP}=12$, đẩy $F_{0.5}$ của `SVA` tăng vọt từ **$0.2098 \rightarrow 0.3226$**, đồng thời nâng $F_{0.5}$ tổng hợp (`MICRO typed`) lên **$0.2284$** (cao nhất trên `dev`), đánh đổi bằng sự sụt giảm Recall ở `VFORM` và `NNUM`.
  3. **Bằng chứng 4 ca cụ thể (từ [`outputs/dev_run_001/parser_four_cases.csv`](outputs/dev_run_001/parser_four_cases.csv)):**
     - `FP02` (`dev:001408`, token 3 `realize`): Heuristic cửa sổ lấy nhầm danh từ số ít `today` (`NN`) ngay trước `realize` làm chủ ngữ giả nên `LR_base` báo lỗi `SVA` với xác suất cực cao ($p = 0.9847$). `spaCy` tìm đúng chủ ngữ thật là `people` (`NNS`, `Plur`, khoảng cách `-2`), kéo xác suất lỗi giảm xuống $0.5022$ (nhưng vẫn vượt nhẹ ngưỡng $\tau = 0.35$).
     - `FP03` (`dev:000644`, token 6 `is`): Cụm danh động từ *"learning foreign languages is..."* có danh từ số nhiều `languages` (`NNS`) đứng sát trước `is`, còn `spaCy` bắt chủ ngữ là `learning` (`VBG`, không có thuộc tính `Number` nên mang nhãn `<UNK>`), khiến xác suất lỗi giảm từ $0.8344$ (`LR_base`) xuống $0.4007$ (`LR_parser`).
     - `FN01` (`dev:001866`, token 39 `is`): Câu đảo/nghi vấn *"what is our reasons"*, chủ ngữ số nhiều `reasons` (`NNS`, `Plur`) nằm ở **bên phải** động từ (khoảng cách `+2`). Dù `spaCy` bắt được `reasons`, biên quyết định âm của các đặc trưng ngữ cảnh xung quanh vẫn khiến cả hai mô hình dự đoán `O`.
     - `FN04` (`dev:001892`, token 11 `is`): Câu ghép thiếu dấu câu *"Second is safety , compared to other the chances of accidents is less ."*, `spaCy` gắn `is` (token 11) làm `ccomp` mà không tìm được cạnh `nsubj` (`subject = <NONE>`), dẫn tới `LR_parser` ($p = 0.1502 < 0.35$) bỏ sót lỗi mà `LR_base` ($p = 0.4732 > 0.45$) bắt được nhờ cụm `accidents is`.

---

## 4. MỤC 6 TRONG BÁO CÁO: Kết quả mở khóa và đánh giá tập `test` ĐÚNG MỘT LẦN

- **Biên bản chạy tập `test` ([`outputs/final_test_cc1e75b079e005f0/evaluation_state.json`](outputs/final_test_cc1e75b079e005f0/evaluation_state.json)):**
  - Thời gian chạy duy nhất: `2026-11-03T13:19:00+07:00` $\rightarrow$ `2026-11-03T13:19:38+07:00`.
  - Số câu hợp lệ: **`2.364` / `2.416` câu** (`68.560` token; loại `52` câu gồm `31` thay thế đa token, `16` chèn từ, `5` xóa từ).
  - **Tổng số lỗi thật (Gold) trên tập `test`:** **`272` lỗi** (`SVA`: **73**, `VFORM`: **76**, `NNUM`: **123**).

### Bảng 6A: Tổng hợp kết quả `MICRO` trên tập `test` (272 lỗi thật) của cả 5 hệ thống

| Hệ thống | Điểm vận hành đã khóa | Chế độ chấm | TP | FP | FN | Precision ($P$) | Recall ($R$) | $F_1$ | **$F_{0.5}$ (Test)** | $F_{0.5}$ (Dev) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **`All_O`** | Luôn đoán `O` | `typed` | 0 | 0 | 272 | 0.0000 | 0.0000 | 0.0000 | **0.0000** | 0.0000 |
| | | `untyped` | 0 | 0 | 272 | 0.0000 | 0.0000 | 0.0000 | **0.0000** | 0.0000 |
| **`POS`** | Luật từ loại cơ sở | `typed` | 31 | 217 | 241 | 0.1250 | 0.1140 | 0.1192 | **0.1226** | 0.1489 |
| | | `untyped` | 32 | 216 | 240 | 0.1290 | 0.1176 | 0.1231 | **0.1266** | 0.1570 |
| **`LR_base`** | `C = 1.0, tau = 0.45` | `typed` | **41** | 154 | **231** | 0.2103 | **0.1507** | **0.1756** | **0.1949** | 0.2202 |
| | | `untyped` | **43** | 152 | **229** | 0.2205 | **0.1581** | **0.1842** | **0.2044** | 0.2367 |
| **`LR_parser`** | `C = 0.1, tau = 0.35` | `typed` | 27 | **79** | 245 | **0.2547** | 0.0993 | 0.1429 | **0.1940** | **0.2284** |
| | | `untyped` | 27 | **79** | 245 | **0.2547** | 0.0993 | 0.1429 | **0.1940** | **0.2369** |
| **`kNN`** | `k = 7, tau = 0.60` | `typed` | 14 | 72 | 258 | 0.1628 | 0.0515 | 0.0782 | **0.1136** | 0.1656 |
| | | `untyped` | 14 | 72 | 258 | 0.1628 | 0.0515 | 0.0782 | **0.1136** | 0.1656 |

### Bảng 6B: Kết quả theo từng nhãn (`SVA`, `VFORM`, `NNUM`) trên tập `test` (`typed`)

| Hệ thống | Nhãn lỗi | Gold | TP | FP | FN | Precision ($P$) | Recall ($R$) | $F_1$ | **$F_{0.5}$** |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **`All_O`** | `SVA` / `VFORM` / `NNUM` | 73 / 76 / 123 | 0 | 0 | 73 / 76 / 123 | 0.0000 | 0.0000 | 0.0000 | **0.0000** |
| **`POS`** | `SVA` | 73 | 14 | 136 | 59 | 0.0933 | 0.1918 | 0.1256 | **0.1040** |
| | `VFORM` | 76 | 7 | 38 | 69 | 0.1556 | 0.0921 | 0.1157 | **0.1367** |
| | `NNUM` | 123 | 10 | 43 | 113 | 0.1887 | 0.0813 | 0.1136 | **0.1493** |
| **`LR_base`** | `SVA` | 73 | 14 | 66 | 59 | 0.1750 | 0.1918 | 0.1830 | **0.1781** |
| | `VFORM` | 76 | 8 | 22 | 68 | 0.2667 | 0.1053 | 0.1509 | **0.2041** |
| | `NNUM` | 123 | **19** | 66 | 104 | **0.2235** | **0.1545** | **0.1827** | **0.2052** |
| **`LR_parser`** | `SVA` | 73 | 10 | **30** | 63 | **0.2500** | 0.1370 | 0.1770 | **0.2146** *(Cao nhất)* |
| | `VFORM` | 76 | 7 | **12** | 69 | **0.3684** | 0.0921 | 0.1474 | **0.2303** *(Cao nhất)* |
| | `NNUM` | 123 | 10 | 37 | 113 | 0.2128 | 0.0813 | 0.1176 | **0.1608** |
| **`kNN`** | `SVA` | 73 | 5 | 26 | 68 | 0.1613 | 0.0685 | 0.0962 | **0.1269** |
| | `VFORM` | 76 | 1 | 12 | 75 | 0.0769 | 0.0132 | 0.0225 | **0.0391** |
| | `NNUM` | 123 | 8 | 34 | 115 | 0.1905 | 0.0650 | 0.0970 | **0.1375** |

### Nhận xét Mục 6:
1. **So sánh thứ hạng giữa `dev` và `test`:**
   - Hai mô hình tuyến tính (`LR_base` đạt $0.1949$ và `LR_parser` đạt $0.1940$) tiếp tục dẫn đầu tuyệt đối trên tập `test`, cao hơn rõ rệt so với `POS` ($0.1226$) và `kNN` ($0.1136$).
   - Trong khi trên `dev` thứ hạng là `LR_parser` $>$ `LR_base` $>$ `kNN` $>$ `POS`, thì trên `test` hai mô hình `LR_base` ($0.1949$) và `LR_parser` ($0.1940$) đạt $F_{0.5}$ tổng hợp gần như ngang bằng (chênh $0.0009$), còn `kNN` ($0.1136$) tụt xuống thấp hơn `POS` ($0.1226$).
2. **Sự đánh đổi giữa `LR_parser` và `LR_base` theo từng nhãn trên `test`:**
   - **`LR_parser` vượt trội ở cả 2 nhãn động từ:** Ở `SVA`, `LR_parser` giảm hơn một nửa số báo động giả ($\text{FP}$ từ $66 \rightarrow 30$), nâng $F_{0.5}$ từ $0.1781 \rightarrow \mathbf{0.2146}$; ở `VFORM`, `LR_parser` giảm $\text{FP}$ từ $22 \rightarrow 12$, nâng $F_{0.5}$ từ $0.2041 \rightarrow \mathbf{0.2303}$; đồng thời đạt Precision tổng hợp cao nhất toàn bảng ($P = \mathbf{25.47\%}$, tổng $\text{FP} = 79$ so với $154$ của `LR_base`).
   - **`LR_base` giữ ưu thế ở nhãn danh từ `NNUM`:** Vì `NNUM` chiếm tới $123/272$ lỗi ($45.22\%$) và không hưởng lợi trực tiếp từ đặc trưng chủ ngữ động từ, việc `LR_parser` dùng hệ số điều chuẩn mạnh $C=0.1$ làm Recall của `NNUM` giảm ($\text{TP}$ từ $19 \rightarrow 10$, $F_{0.5}$ giảm từ $0.2052 \rightarrow 0.1608$), khiến điểm `MICRO` tổng hợp của hai mô hình cân bằng nhau.

---

## 5. MỤC AI TOOL DISCLOSURE (Bắt buộc ở cuối Báo cáo theo Trang 6 Rubric)

> **AI Tool Disclosure:**
> - **Công cụ sử dụng:** ChatGPT / Google Antigravity.
> - **Phạm vi hỗ trợ:** (1) Gợi ý phân tích ngữ pháp ban đầu cho 63 ca FP trên tập `dev`, sau đó hai thành viên Vũ Thị Loan và Mai Hải Yến trực tiếp kiểm tra lại từng câu gốc và thống nhất nhãn tại [`review_consensus.csv`](outputs/dev_run_001/baseline_ref/review_consensus.csv); (2) Hỗ trợ chuẩn hóa script tổng hợp [`summarize_reviews.py`](summarize_reviews.py), script kiểm tra điểm cố định [`scripts/decode_parser_fixed_point.py`](scripts/decode_parser_fixed_point.py) và bộ kiểm thử tự động [`tests/test_reviews.py`](tests/test_reviews.py).
> - **Kiểm chứng của nhóm:** Mọi kết quả thực nghiệm trên tập `dev`/`test`, đặc trưng mô hình và các ca phân tích lỗi đều được các thành viên trực tiếp chạy kiểm chứng và nắm vững.
