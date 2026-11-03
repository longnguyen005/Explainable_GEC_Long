# Group02 Long — gói bổ sung phiếu chung và số liệu báo cáo

Đây là gói bổ sung cho `Explainable_GEC_Long`, không phải toàn bộ project hoặc xác nhận đã hoàn thành tất cả yêu cầu thầy. Giữ nguyên dữ liệu, mô hình, đặc trưng, cấu hình và test outputs đã có.

## Nội dung

- `Group02_FP63_Consensus.xlsx`: phiếu chung từ TV1, bảng đếm tự cập nhật và cột xác minh để người đọc ghi bổ sung.
- `review_consensus.csv`: cùng 63 ca được ghép với nguồn Long bằng record_id + token_index.
- `review_status.json`: trạng thái nguồn/phương pháp và các kịch bản precision; không suy đánh giá độc lập từ hai phiếu trùng nhau.
- `report_tables/`: CSV của Long đã đối chiếu số học, thêm bảng parser ba cấu hình × ba nhãn.
- `report_facts_Long.json`: cấu hình và kết quả đã lưu để truy nguồn.
- `HUONG_DAN_VIET_BAO_CAO_LONG.md`: số liệu, cách diễn giải và checklist phần còn thiếu.
- `fix_review_status.patch`: bản vá cho `summarize_reviews.py` và test trạng thái review.
- `fp02_intervention_dev.py`: kiểm tra FP02 trên cùng mô hình parser C = 1 và ngưỡng 0,45, cần mô hình đã fit trên máy Long.

Phiếu gốc và mô hình tham chiếu có nháp hỗ trợ AI; ghi phương pháp ở phần khai báo chung. Không có kết quả gán nhãn độc lập ban đầu được tạo bởi gói này.

## Áp dụng phần review

Giải nén thư mục `Group02_Long_Report_Pack` bên trong thư mục project Long. Sao lưu các file review hiện tại trước khi cập nhật. Từ thư mục project:

```bash
git apply --check Group02_Long_Report_Pack/fix_review_status.patch
git apply Group02_Long_Report_Pack/fix_review_status.patch
```

Nếu kiểm tra patch báo không khớp, dừng và đối chiếu phiên bản `summarize_reviews.py`; không ép áp dụng lên code đã thay đổi. Bản vá được tạo từ đúng ZIP Long đã cung cấp và không sửa `gec/`, `run_dev.py` hoặc `run_final_test.py`.

Sao chép `review_consensus.csv` vào `outputs/dev_run_001/baseline_ref/review_consensus.csv`. Giữ nguyên `review_Loan.csv`, `review_Yen.csv` và các phiếu nguồn. Sau đó chạy:

```bash
python summarize_reviews.py
```

Script đã vá vẫn tổng hợp số nhãn nhưng không coi đủ ô điền là bằng chứng độc lập. `disagreements_before_discussion` để null; `available_sheet_label_differences` chỉ mô tả khác biệt giữa hai file hiện có. Không tính kappa từ hai bản nháp chung.

`review_status.json` trong gói bổ sung giữ thông tin nguồn và trạng thái mới; không dùng nó để giả lập một lần đọc mới đã hoàn tất. Những cột người/ngày xác minh trong CSV/workbook chỉ điền khi thực sự kiểm tra.

## Kiểm tra FP02 trên dev

Sao chép `fp02_intervention_dev.py` vào thư mục `scripts/` của project Long. Dùng môi trường đã chạy project:

```bash
python scripts/fp02_intervention_dev.py
```

Script cần `data/json/dev.json`, môi trường POS/parser đúng phiên bản, vocabulary và mô hình `models/lr_parser_C1.0_*.joblib` đã fit từ lần chạy cũ. Nó giữ nguyên C = 1 và ngưỡng 0,45, so cấu hình chủ ngữ quan sát với hai profile can thiệp people/today. Không fit mô hình, không dò tham số và không mở test. Kết quả mới nằm ở thư mục riêng `outputs/fp02_intervention_dev_.../`.

Script đã kiểm tra cú pháp và tính bất biến của profile bằng dữ liệu giả nhỏ. Chưa chạy với mô hình thật của Long; không có số xác suất can thiệp mới nào được công bố trong gói này.

## Kiểm tra đã thực hiện khi tạo gói

- 63 khóa record/token, token và source khớp nguồn Long; 63 nhãn trùng bảng chung cũ.
- A/B/C = 34/14/15; B trong ba nhãn = 10; các tỷ lệ từ số đếm tính đúng.
- Các bảng dev/test được kiểm tra F0,5 và support từ TP/FP/FN; chỉ đọc kết quả đã lưu.
- Workbook đã kiểm tra công thức, thử thay một nhãn rồi khôi phục, và xem bản render.
- Bản vá review được chạy qua xử lý CSV/JSON trong môi trường cô lập không nạp mô hình ML; khi đủ cả hai phiếu, `independent_reviews_complete` vẫn false và số bất đồng trước thảo luận vẫn null.

Phần còn thiếu trên máy Long: dự đoán đầy đủ, artifact mô hình cần cho kiểm tra mẫu, lần chạy FP02, đọc/kiểm chứng thực tế, và đồng bộ notebook/báo cáo/đóng góp/lịch sử test. Xem bảng cụ thể trong hướng dẫn báo cáo.
