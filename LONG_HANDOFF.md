# Bàn giao phần thực hiện của Long

Ngày tạo: 2026-10-22T20:57:31+07:00

## Trạng thái

Đã sửa pipeline dữ liệu, chạy All O/POS/LR/kNN, tái tạo LR tham chiếu Week 9, hoàn thành thí nghiệm dependency, lưu model/config và kiểm tra lại dự đoán sau khi nạp model. Mã gốc không đổi. Chỉ train/dev được đọc; chưa mở/chấm test. Hai người vẫn cần thực hiện review độc lập và nhóm cần xem xét cấu hình trước đánh giá cuối.

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

Phân biệt LR tham chiếu C=3/tau=0.65 với LR nền được chọn bằng quy tắc gần hòa. LR tham chiếu khớp report Week 9: typed 28/65/235 và untyped 30/63/233. Điểm 0.233 trong CSV gốc thuộc pipeline cũ; không dùng làm điểm mới. Lần chạy mới dùng NLTK 3.9.2, khác tên phiên bản NLTK ghi trong report, nhưng tái tạo đúng đặc trưng và số đếm LR tham chiếu.

## Thí nghiệm parser

LR nền chọn C=1.0, tau=0.45. LR parser chọn C=0.1, tau=0.35. Hai phiên bản dùng cùng grid và quy tắc gần hòa được ghi trước fit. Vì cả C/ngưỡng có thể thay đổi, đây là so sánh hai pipeline được chọn bằng cùng quy trình, không phải tác động thuần của thêm ba đặc trưng tại một C/ngưỡng cố định.

Vocab nền 126.797 đặc trưng; parser 126.847. Parser giữ khớp toàn bộ 484.953 token train/dev, chạy trên source, không dùng correction/evidence/parsing order của gold.

| system | label | TP | FP | FN | P | R | F0.5 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| LR_base | SVA | 12 | 41 | 62 | 0.226415 | 0.162162 | 0.209790 |
| LR_base | VFORM | 7 | 17 | 62 | 0.291667 | 0.101449 | 0.212121 |
| LR_base | NNUM | 19 | 54 | 101 | 0.260274 | 0.158333 | 0.230583 |
| LR_parser | SVA | 12 | 16 | 62 | 0.428571 | 0.162162 | 0.322581 |
| LR_parser | VFORM | 5 | 15 | 64 | 0.250000 | 0.072464 | 0.167785 |
| LR_parser | NNUM | 10 | 24 | 110 | 0.294118 | 0.083333 | 0.195312 |

Kết luận: micro F0.5 tăng từ 0.220162 lên 0.228426, nhưng TP typed giảm 38 xuống 27 và FP giảm 112 xuống 55. Riêng SVA, TP và recall giữ nguyên (12/74); FP giảm 41 xuống 16, F0.5 tăng 0.209790 lên 0.322581. VFORM và NNUM giảm F0.5. Không nói parser giúp tìm thêm SVA; mức tăng hiện tại chủ yếu là giảm báo nhầm. Đây là điểm dev sau lựa chọn, một seed, chưa có bằng chứng generalization trên test.

Thay đổi từng token so LR nền: {"removed_FP": 70, "new_FP": 14, "lost_gold": 18, "recovered_gold": 7, "other_type_change": 2}. Xem parser_changed_predictions.csv để đọc cả ca tốt lên và xấu đi.

### Bốn ca instructor yêu cầu

| report_case_name | record_id | token | subject_text | subject_tag | subject_number | reference_C3_tau065_prediction | base_prediction | parser_prediction |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| FP02 | dev:001408 | realize | people | NNS | Plur | SVA | SVA | SVA |
| FP03 | dev:000644 | is | learning | VBG | <UNK> | SVA | SVA | SVA |
| FN01 | dev:001866 | is | reasons | NNS | Plur | O | O | O |
| FN04 | dev:001892 | is | <NONE> | <NONE> | <UNK> | O | SVA | O |

- FP02 `realize`: parser lấy đúng `people`, nhưng cả LR nền lẫn LR parser vẫn dự đoán SVA theo ngưỡng đã chọn. Xác suất lỗi giảm; chưa sửa được FP này.
- FP03 `is`: parser lấy `learning` thay vì danh từ `languages`; Number của chủ ngữ không có. Cảnh báo SVA vẫn còn.
- FN01 `is`: parser nhận `reasons` bên phải, nhưng xác suất lỗi vẫn thấp hơn ngưỡng; FN vẫn còn.
- FN04 `is`: parser không tìm thấy chủ ngữ trong cấu trúc này. LR nền C=1 tìm đúng SVA; LR parser trả O, tạo một hồi quy. Tên FN04 là tên trong report của LR tham chiếu C=3, không phải phân loại hiện tại của LR nền.


Các nhận xét cú pháp trên là phân tích đầu ra parser trong ngữ cảnh, không phải nhãn chuyên gia mới. Đặc trưng đóng góp được tính bằng hệ số lớp lỗi trừ hệ số O; file chi tiết giữ intercept và tổng margin đầy đủ, không chỉ vài đặc trưng lớn nhất.

## kNN

kNN chọn k=10, tau=0.8; 42.493 mẫu (3.863 lỗi + 38.630 O), SVD 200 chiều, cosine, seed=0. Với k=10, tau=0.75 và 0.80 cùng yêu cầu ít nhất 8/10 láng giềng là lỗi; khác ngưỡng ghi với report nhưng cùng quyết định. Ties trong grid ưu tiên tau cao hơn. Không suy nguyên nhân kNN thấp chỉ từ điểm tổng.

## Bàn giao cho Loan và Yến

- baseline_ref/fp_reference.csv: đủ 63 FP untyped, giữ câu/token/ID/probability và annotation tham chiếu.
- baseline_ref/review_Loan.csv và review_Yen.csv: hai phiếu giống nhau, cột nhãn/lý do còn trống.
- baseline_ref/fn_reference.csv: 233 FN untyped để chẩn đoán.
- baseline_ref/REVIEW_GUIDE_VI.md: rubric và công thức precision đúng cho LR tham chiếu.
- Chạy summarize_reviews.py để kiểm tra đủ ca, ghi bất đồng rồi nhập đồng thuận thủ công. Không tính precision rà soát khi phiếu chưa hoàn tất.

## Cấu hình khóa và test

config_locked.json giữ model, tham số và SHA-256. Trạng thái dev_selection_frozen; team_review_pending=true; test_authorized=false. Đây là đóng băng kỹ thuật để tái lập, chưa phải khẳng định nhóm đã duyệt. Test không được đóng gói. Không chạy test trực tiếp từ notebook.

Entry point run_final_test.py đã chuẩn bị, cần đường dẫn test do người dùng cung cấp và cờ --authorize-test rõ ràng. Nó kiểm tra hash code/model, không fit/tuning, lưu marker một lần chạy. Chỉ dùng khi quyết định mở test đã được đưa ra. Lần thực hiện hiện tại chưa gọi đánh giá test; chỉ kiểm tra --help và loader từ chối test trong chế độ dev.

## Kiểm tra đã thực hiện

- 13 unit tests cho alignment, scoring, ngưỡng, tie rule, parser aux/chủ ngữ bên phải và chặn test.
- Đối chiếu độc lập các số TP/FP/FN và F0.5 từ toàn bộ CSV bằng bộ đếm Python khác scorer numpy.
- Nạp lại ba LR đã lưu, dự đoán toàn bộ dev trùng CSV.
- Nạp lại kNN và kiểm tra 128 vị trí trải đều dev.
- Kiểm tra mọi token parser và 228 cấu hình grid.
- So SHA-256 mã gốc: không thay đổi.

## Gợi ý phần trình bày của Long

1. Đầu vào chỉ source, đầu ra là nhãn token; khác evidence extraction của mã gốc.
2. LR nền học đặc trưng cục bộ; nearest noun không luôn là chủ ngữ.
3. Parser cung cấp ba đặc trưng với token alignment được kiểm tra.
4. SVA precision tăng nhưng recall chưa tăng; có cả hồi quy ở FN04.
5. Nhóm khóa tham số bằng dev và giữ test cho đánh giá cuối.

## File nên mở trước

README.md để chạy; outputs/dev_run_001/metrics_dev.csv để xem điểm; parser_four_cases.csv để đọc ví dụ; baseline_ref/ để bàn giao review. Notebook EXPECT_Long_Dev.ipynb chứa các cell đã chạy để kiểm tra và trình bày kết quả lưu sẵn, có tùy chọn tái chạy pipeline dev. Việc huấn luyện thực tế được thực hiện qua CLI và lưu log, không khẳng định đã dùng một Jupyter server.
