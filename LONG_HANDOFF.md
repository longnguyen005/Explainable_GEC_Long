# Bàn giao phần thực hiện của Long

Ngày tạo: 2026-11-03T22:22:14+07:00

## Trạng thái

Đã sửa pipeline dữ liệu, chạy All O/POS/LR/kNN, tái tạo LR tham chiếu Week 9, hoàn thành thí nghiệm dependency (gồm cả kiểm tra cùng điểm quyết định `C=1.0, tau=0.45` và can thiệp đặc trưng tại `FP02`), lưu model/config, kiểm tra lại dự đoán sau khi nạp model, chuẩn hóa/tổng hợp kết quả rà soát 63 FP của Vũ Thị Loan (TV1) và Mai Hải Yến (TV2), và hoàn tất đánh giá một lần trên tập `test` ngày 03/11/2026 tại `outputs/final_test_cc1e75b079e005f0/`. Mã gốc không đổi. Trong giai đoạn phát triển (`outputs/dev_run_001/`), chỉ `train`/`dev` được đọc và cấu hình đã được khóa trước khi mở `test`.

## Dữ liệu đã kiểm tra

| split | original_records | records | tokens | SVA | VFORM | NNUM | excluded_records |
| --- | --- | --- | --- | --- | --- | --- | --- |
| train | 15187 | 14610 | 416571 | 1005 | 1190 | 1668 | 577 |
| dev | 2413 | 2367 | 68382 | 74 | 69 | 120 | 46 |

Alignment dùng target+[MOD]+source, offset len(target)+1. Train loại 577 bản ghi, gồm 8 bản ghi bị giữ nhầm bởi code cũ. Dev loại 46. Một source trùng train/dev được giữ trong bảng chính theo split công khai; bảng độ nhạy bỏ source dev trùng nhưng không tuning lại.

## Kết quả đầy đủ trên dev

| system | scoring | TP | FP | FN | P | R | F0.5 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| All_O | typed | 0 | 0 | 263 | 0.000000 | 0.000000 | 0.000000 |
| All_O | untyped | 0 | 0 | 263 | 0.000000 | 0.000000 | 0.000000 |
| POS | typed | 36 | 222 | 227 | 0.139535 | 0.136882 | 0.138996 |
| POS | untyped | 37 | 221 | 226 | 0.143411 | 0.140684 | 0.142857 |
| LR_base | typed | 38 | 112 | 225 | 0.253333 | 0.144487 | 0.220162 |
| LR_base | untyped | 40 | 110 | 223 | 0.266667 | 0.152091 | 0.231750 |
| LR_reference_C3_tau065 | typed | 28 | 65 | 235 | 0.301075 | 0.106464 | 0.220472 |
| LR_reference_C3_tau065 | untyped | 30 | 63 | 233 | 0.322581 | 0.114068 | 0.236220 |
| LR_parser | typed | 27 | 55 | 236 | 0.329268 | 0.102662 | 0.228426 |
| LR_parser | untyped | 28 | 54 | 235 | 0.341463 | 0.106464 | 0.236887 |
| kNN | typed | 10 | 79 | 253 | 0.112360 | 0.038023 | 0.080775 |
| kNN | untyped | 11 | 78 | 252 | 0.123596 | 0.041825 | 0.088853 |

Phân biệt LR tham chiếu C=3/tau=0.65 với LR nền được chọn bằng quy tắc gần hòa (chọn C nhỏ nhất có F0.5 thấp hơn mức cực đại **dưới 0,005** theo số thực chưa làm tròn). LR tham chiếu khớp report Week 9: typed 28/65/235 và untyped 30/63/233. Điểm 0.233 trong CSV gốc thuộc pipeline cũ; không dùng làm điểm mới. Lần chạy mới dùng NLTK 3.9.2, khác tên phiên bản NLTK ghi trong report, nhưng tái tạo đúng đặc trưng và số đếm LR tham chiếu.

## Thí nghiệm parser

LR nền chọn C=1.0, tau=0.45. LR parser chọn C=0.1, tau=0.35. Hai phiên bản dùng cùng grid và quy tắc gần hòa được ghi trước fit. Vì cả C/ngưỡng có thể thay đổi, cần tách bạch phép so ở cùng C/ngưỡng cố định và phép so hai cấu hình được chọn.

Vocab nền 126.797 đặc trưng; parser 126.847. Tập quan hệ chủ ngữ trong `gec/dependency.py` là `SUBJECT_DEPS = {'nsubj', 'nsubjpass', 'csubj', 'csubjpass'}` (không có `expl`). Parser giữ khớp toàn bộ 484.953 token train/dev, chạy trên source, không dùng correction/evidence/parsing order của gold.

| system | label | TP | FP | FN | P | R | F0.5 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| LR_base | SVA | 12 | 41 | 62 | 0.226415 | 0.162162 | 0.209790 |
| LR_base | VFORM | 7 | 17 | 62 | 0.291667 | 0.101449 | 0.212121 |
| LR_base | NNUM | 19 | 54 | 101 | 0.260274 | 0.158333 | 0.230583 |
| LR_parser | SVA | 12 | 16 | 62 | 0.428571 | 0.162162 | 0.322581 |
| LR_parser | VFORM | 5 | 15 | 64 | 0.250000 | 0.072464 | 0.167785 |
| LR_parser | NNUM | 10 | 24 | 110 | 0.294118 | 0.083333 | 0.195312 |

Kết luận trên `dev`:
1. **Ở phép so cùng `C=1.0, tau=0.45` (`outputs/fixed_point_check/metrics_parser_fixed_point.csv`):** Tổng TP typed giữ nguyên 38, tổng FP tăng 112 -> 122 (F0.5 micro 0.220162 -> 0.210410); riêng nhãn `SVA`, **TP SVA giảm 12 -> 11; FP giữ 41** (F0.5 SVA 0.209790 -> 0.195035). Như vậy tại cùng điểm quyết định `C=1.0, tau=0.45`, thêm 3 đặc trưng parser không tự làm giảm FP của SVA.
2. **Ở phép so hai cấu hình được chọn (`LR_base` `C=1.0, tau=0.45` vs `LR_parser` `C=0.1, tau=0.35`):** Micro F0.5 tăng từ 0.220162 lên 0.228426, nhưng TP typed giảm 38 xuống 27 và FP giảm 112 xuống 55. Riêng SVA, TP và recall giữ nguyên (12/74); FP giảm 41 xuống 16, F0.5 tăng 0.209790 lên 0.322581 (nhờ kết hợp điều chuẩn mạnh hơn ở `C=0.1, tau=0.35` với đặc trưng parser). VFORM và NNUM giảm F0.5. Không nói parser giúp tìm thêm SVA; mức tăng ở cấu hình được chọn chủ yếu đến từ giảm báo nhầm. Kết quả kiểm tra khả năng tổng quát hóa trên tập `test` (chấm ngày 03/11/2026) được trình bày tại mục Cấu hình khóa và test bên dưới.

Thay đổi từng token so LR nền: {"removed_FP": 70, "new_FP": 14, "lost_gold": 18, "recovered_gold": 7, "other_type_change": 2}. Xem parser_changed_predictions.csv để đọc cả ca tốt lên và xấu đi.

### Bốn ca instructor yêu cầu

| report_case_name | record_id | token | subject_text | subject_tag | subject_number | reference_C3_tau065_prediction | base_prediction | parser_prediction |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| FP02 | dev:001408 | realize | people | NNS | Plur | SVA | SVA | SVA |
| FP03 | dev:000644 | is | learning | VBG | <UNK> | SVA | SVA | SVA |
| FN01 | dev:001866 | is | reasons | NNS | Plur | O | O | O |
| FN04 | dev:001892 | is | <NONE> | <NONE> | <UNK> | O | SVA | O |

- FP02 `realize` (`dev:001408`, token 3): *Quan sát:* parser trích xuất đúng chủ ngữ `people` (`NNS`, `Plur`, `-2`), nhưng cả LR nền (`C=1.0, tau=0.45`), LR parser cùng điểm (`C=1.0, tau=0.45`) lẫn LR parser được chọn (`C=0.1, tau=0.35`) đều vẫn dự đoán `SVA`; khi can thiệp thay riêng đặc trưng chủ ngữ từ `people` sang `today` ở cùng mô hình `C=1.0`, `p_error` chỉ đổi nhẹ (`0.993020 -> 0.989731`). *Giả thuyết:* các đặc trưng cửa sổ cục bộ (`subj_w=today`, `p-1|p=NN|VBP`) vẫn được giữ nguyên và 3 đặc trưng parser chưa ghép chéo với nhãn động từ `VBP`.
- FP03 `is` (`dev:000644`, token 6): *Quan sát:* parser trích xuất đầu ngữ chủ ngữ danh động từ `learning` (`VBG`, `-3`) thay vì danh từ `languages` (`NNS`), nhưng `subject_number` là `<UNK>` và cảnh báo `SVA` vẫn còn. *Giả thuyết:* token `VBG` trong `spaCy` không có thuộc tính hình thái `Number` nên `describe()` gán `<UNK>` thay vì biểu diễn chủ ngữ mệnh đề `VBG` như ngôi thứ 3 số ít.
- FN01 `is` (`dev:001866`, token 39): *Quan sát:* parser trích xuất chủ ngữ bên phải `reasons` (`NNS`, `Plur`, `+2`) và `p_error` tăng (`0.011861 -> 0.034733` ở `C=1.0`; `0.069654` ở `C=0.1`), nhưng vẫn thấp hơn ngưỡng nên FN vẫn còn. *Giả thuyết:* biên quyết định tổng thể vẫn bị kéo về lớp `O` bởi các đặc trưng ngữ cảnh cục bộ xung quanh (`what is our ...`).
- FN04 `is` (`dev:001892`, token 11): *Quan sát:* tại động từ `is` thứ hai trong câu ghép nối bằng dấu phẩy, `describe()` trả về `subject_text=<NONE>, subject_number=<UNK>` do token 11 không có con trực tiếp thuộc `SUBJECT_DEPS = {'nsubj', 'nsubjpass', 'csubj', 'csubjpass'}` (lưu ý: `SUBJECT_DEPS` trong `gec/dependency.py` không có `expl`). LR nền `C=1.0` dự đoán đúng `SVA` (`p_error=0.473200`), còn LR parser trả về `O` (`p_error=0.073707` ở `C=1.0`; `0.150214` ở `C=0.1`), tạo một hồi quy FN. *Giả thuyết:* quy tắc chỉ tìm con trực tiếp trong `SUBJECT_DEPS` (hoặc qua head của `aux`/`auxpass`/`cop`) không lấy được danh ngữ `chances` phía trước trong cấu trúc comma splice. Tên `FN04` là mã ca trong report của LR tham chiếu `C=3.0`.


Các nhận xét cú pháp trên được tách thành quan sát trực tiếp trên đầu ra parser và giả thuyết cơ chế trong ngữ cảnh, không phải nhãn chuyên gia mới. Đặc trưng đóng góp được tính bằng hệ số lớp lỗi trừ hệ số O; file chi tiết giữ intercept và tổng margin đầy đủ, không chỉ vài đặc trưng lớn nhất.

## kNN

kNN chọn k=10, tau=0.8; 42.493 mẫu (3.863 lỗi + 38.630 O), SVD 200 chiều, cosine, seed=0. Với k=10, tau=0.75 và 0.80 cùng yêu cầu ít nhất 8/10 láng giềng là lỗi; khác ngưỡng ghi với report nhưng cùng quyết định. Ties trong grid ưu tiên tau cao hơn. Không suy nguyên nhân kNN thấp chỉ từ điểm tổng.

## Kết quả rà soát 63 FP của Loan và Yến

- `baseline_ref/fp_reference.csv`: đủ 63 FP untyped, giữ câu/token/ID/probability và annotation tham chiếu.
- `baseline_ref/raw_TV1_Loan.csv` và `raw_TV2_Yen.csv`: bản gốc phiếu rà soát 63 FP của Vũ Thị Loan và Mai Hải Yến (ngày 2026-10-27).
- `baseline_ref/review_Loan.csv`, `review_Yen.csv`, `review_consensus.csv`, `review_status.json`: đã chuẩn hóa và tổng hợp bằng `summarize_reviews.py` (63/63 ca hoàn tất; `review_forms_filled=true`, `independent_reviews_complete=false`, `disagreements_before_discussion=null`).
- Thống kê 63 ca FP (`LR_reference_C3_tau065`, 30 TP + 63 FP = 93 cảnh báo):
  - **A (báo nhầm thật):** 34 ca.
  - **B (lỗi thật nhưng gold chưa ghi):** 14 ca — gồm **10 ca thuộc 3 nhãn mục tiêu** (`SVA`: 5, `VFORM`: 3, `NNUM`: 2), **3 ca `Khác`** ngoài phạm vi (`FP021`, `FP028`, `FP048`) và **1 ca `Chưa xác định`** (`FP049`).
  - **C (chưa chắc / thiếu ngữ cảnh):** 15 ca.
  - **Precision hiệu chỉnh (chỉ tính 10 ca B thuộc 3 nhãn):** `(30 + 10) / 93` = **0.430108** (cận trên giả định gộp C: `55 / 93` = 0.591398).
  - **Precision hiệu chỉnh (tính cả 14 ca B):** `(30 + 14) / 93` = **0.473118** (cận trên giả định gộp C: `59 / 93` = 0.634409).
  - Lưu ý phương pháp: Hai phiếu TV1 và TV2 xuất phát từ cùng bản nháp có AI hỗ trợ; yêu cầu hai lượt đọc độc lập ban đầu vẫn là giới hạn phương pháp đã khai báo, không báo cáo độ đồng thuận độc lập hay hệ số Cohen kappa giữa hai bản này.

## Cấu hình khóa, kết quả test và lịch sử hai đợt test của nhóm

- `outputs/dev_run_001/config_locked.json` giữ model, tham số và SHA-256 ở trạng thái snapshot trước khi mở `test` (`dev_selection_frozen`, `team_review_pending=true`, `test_authorized=false`). Notebook không tự chạy đánh giá `test`.
- Entry point `run_final_test.py` đã được chạy với cờ `--authorize-test` ngày **03/11/2026** và lưu kết quả tại `outputs/final_test_cc1e75b079e005f0/` (`metrics_test.csv`, `evaluation_state.json`, `predictions_*.csv`). Trên `test` (`272` vị trí `gold`, `typed MICRO`): `LR_base` đạt `TP/FP/FN = 41/154/231, F0.5 = 0.194867`; `LR_parser` đạt `27/79/245, F0.5 = 0.193966`; `POS` đạt `31/217/241, F0.5 = 0.122627`; `kNN` đạt `14/72/258, F0.5 = 0.113636`.
- **Lịch sử hai đợt đánh giá `test` của Nhóm 02:** Trước khi thống nhất chọn bản triển khai `Explainable_GEC_Long`, nhóm từng có một đợt chạy trên nhánh triển khai ngày **02/11/2026** (quy ước khoảng cách chủ ngữ parser khác bản Long, ngưỡng `kNN` `tau=0.75`; không dùng làm số chính thức) và đợt chạy ngày **03/11/2026** trên bản `Explainable_GEC_Long` đã khóa. Nhóm khai báo minh bạch lịch sử hai đợt này (không tuyên bố cả nhóm chỉ mở `test` một lần) và cam kết **không dùng kết quả `test` của bất kỳ đợt nào để chọn lại hay chỉnh sửa `C`, `k`, ngưỡng `tau` hay mô hình**.

## Bảng đóng góp thực tế của từng thành viên

| Thành viên | Phần việc thực tế đã thực hiện | File / Hiện vật bằng chứng |
| --- | --- | --- |
| Nguyễn Thành Long | Sửa lỗi alignment (`offset = len(target) + 1`), xây dựng pipeline tiền xử lý và huấn luyện 5 hệ thống (`All_O`, `POS`, `LR_base`, `LR_parser`, `kNN`), quy tắc chọn `select_lr`, tích hợp `spaCy` parser, chạy kiểm tra cùng điểm quyết định `C=1.0, tau=0.45` và can thiệp đặc trưng `FP02`, chạy `test` ngày 03/11/2026, viết unit tests và đóng gói bàn giao. | `gec/*.py`, `run_dev.py`, `run_final_test.py`, `verify_run.py`, `scripts/*.py`, `tests/*.py`, `models/*.joblib`, `outputs/`, `EXPECT_Long_Dev.ipynb` |
| Vũ Thị Loan (TV1) | Phiếu rà soát 63 ca FP của `LR_reference_C3_tau065` (bản gốc `raw_TV1_Loan.csv`, ngày ghi trên phiếu 2026-10-27), được chọn làm phiếu chung `review_consensus.csv`; phân loại `A=34, B=14 (10 ca thuộc 3 nhãn), C=15` kèm lý do từng ca. Phần việc khác do nhóm bổ sung theo thực tế. | `outputs/dev_run_001/baseline_ref/raw_TV1_Loan.csv`, `review_Loan.csv`, `review_consensus.csv`, `Group02_FP63_Consensus.xlsx` |
| Mai Hải Yến (TV2) | Phiếu rà soát 63 ca FP (`raw_TV2_Yen.csv`, chuẩn hóa tại `review_Yen.csv`). Phần việc khác do nhóm bổ sung theo thực tế. | `outputs/dev_run_001/baseline_ref/raw_TV2_Yen.csv`, `review_Yen.csv`, `independent_comparison.csv` |

## Kiểm tra đã thực hiện

- 14 unit tests cho alignment, scoring, ngưỡng, tie rule, parser aux/chủ ngữ bên phải, chuẩn hóa phiếu review 63 FP và chặn test.
- Đối chiếu độc lập các số TP/FP/FN và F0.5 từ toàn bộ CSV bằng bộ đếm Python khác scorer numpy.
- Nạp lại ba LR đã lưu, dự đoán toàn bộ dev trùng CSV.
- Nạp lại kNN và kiểm tra 128 vị trí trải đều dev.
- Kiểm tra mọi token parser và 228 cấu hình grid.
- So SHA-256 mã gốc: không thay đổi.

## Gợi ý phần trình bày của Long

1. Đầu vào chỉ source, đầu ra là nhãn token; khác evidence extraction của mã gốc.
2. LR nền học đặc trưng cục bộ; nearest noun không luôn là chủ ngữ.
3. Parser cung cấp ba đặc trưng với token alignment được kiểm tra (`SUBJECT_DEPS = {'nsubj', 'nsubjpass', 'csubj', 'csubjpass'}`).
4. Ở phép so cùng `C=1.0, tau=0.45`, **TP SVA giảm 12 -> 11; FP giữ 41**; ở cấu hình được chọn `C=0.1, tau=0.35`, SVA precision tăng nhờ giảm FP (`41 -> 16`) và giữ `TP = 12`, có hồi quy ở `FN04`.
5. Nhóm khóa tham số bằng `dev` và đã chấm `test` ngày 03/11/2026 tại `outputs/final_test_cc1e75b079e005f0/` (khai báo minh bạch lịch sử hai đợt test 02/11 và 03/11 của nhóm, không chọn lại tham số theo test).

## File nên mở trước

README.md để chạy; `TONG_HOP_KET_QUA_BAO_CAO_GROUP02.md` và `Group02_Long_Report_Pack/HUONG_DAN_VIET_BAO_CAO_LONG.md` để lấy bảng viết báo cáo; `outputs/dev_run_001/metrics_dev.csv` và `outputs/final_test_cc1e75b079e005f0/metrics_test.csv` để xem điểm; `parser_four_cases.csv` và `outputs/fixed_point_check/parser_limitation_cases.csv` để đọc ví dụ; `baseline_ref/` để xem kết quả review 63 FP. Notebook EXPECT_Long_Dev.ipynb chứa các cell đã chạy để kiểm tra và trình bày kết quả lưu sẵn (kèm trace mẫu `dev:001408` token 3 `realize`).
