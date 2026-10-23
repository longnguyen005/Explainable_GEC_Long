# Phiếu review độc lập cho Loan và Yến

Danh sách này thuộc LR tham chiếu C=3, tau=0.65, dữ liệu đã sửa alignment. Có 30 TP và 63 FP untyped, tổng 93 cảnh báo. Không dùng danh sách này để đánh giá LR_base có cấu hình khác hoặc LR_parser.

1. Loan mở review_Loan.csv; Yến mở review_Yen.csv. Cả hai đọc cùng toàn bộ 63 ca.
2. Điền review_label_A_B_C bằng A/B/C; ghi reason, suggested_error_type, suggested_correction, reviewer, reviewed_at.
3. A: token phù hợp ngữ pháp, mô hình báo nhầm. B: có lỗi thuộc SVA/VFORM/NNUM tại vị trí dự đoán mà annotation chưa phản ánh. C: chưa chắc hoặc thiếu ngữ cảnh. B cần nêu cách sửa và căn cứ; một lỗi ở vị trí khác không đủ để xác nhận dự đoán.
4. Đọc độc lập, không xem nhãn của nhau. Dùng source đầy đủ; target_edit_reference chỉ là phép sửa được annotation, không khẳng định mọi vị trí còn lại đều đúng.
5. Giữ nguyên bản nhãn độc lập trước thảo luận. Chạy summarize_reviews.py để lập bảng bất đồng; chương trình không tự điền đồng thuận.
6. Sau thảo luận, điền review_consensus.csv và chạy lại công cụ để tổng hợp. Giữ C nếu chưa chắc.

Precision vị trí rà soát = (30+B)/93. Cận giả định = [(30+B)/93, (30+B+C)/93], không phải khoảng tin cậy. Đây là rà soát nội bộ, không phải nhãn chuyên gia; không thay thế điểm benchmark và không tạo ra recall/F0.5 đã hiệu chỉnh.

Hai phiếu hiện để trống có chủ ý. Long/AI không điền thay hai người đánh giá độc lập.
