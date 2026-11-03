# Phiếu review cho Loan và Yến

Danh sách này thuộc LR tham chiếu C=3, tau=0.65, dữ liệu đã sửa alignment. Có 30 TP và 63 FP untyped, tổng 93 cảnh báo. Không dùng danh sách này để đánh giá LR_base có cấu hình khác hoặc LR_parser.

1. Loan (`review_Loan.csv`, bản gốc `raw_TV1_Loan.csv`) và Yến (`review_Yen.csv`, bản gốc `raw_TV2_Yen.csv`) đã kiểm tra đủ 63 ca.
2. Nhãn `review_label_A_B_C` gồm A/B/C; kèm `reason`, `suggested_error_type`, `suggested_correction`, `reviewer`, `reviewed_at`.
3. A: token phù hợp ngữ pháp, mô hình báo nhầm (34 ca). B: có lỗi tại vị trí dự đoán mà annotation chưa phản ánh (14 ca, trong đó 10 ca thuộc SVA/VFORM/NNUM và 4 ca ngoài phạm vi/chưa chốt thì). C: chưa chắc hoặc thiếu ngữ cảnh (15 ca).
4. Kết quả tổng hợp lưu tại `independent_comparison.csv`, `review_consensus.csv` và `review_status.json`.

Precision vị trí rà soát (chỉ tính B thuộc 3 nhãn SVA/VFORM/NNUM) = (30+10)/93 = 0.430108.
Precision vị trí rà soát (tính toàn bộ B) = (30+14)/93 = 0.473118.
Cận giả định = [(30+B)/93, (30+B+C)/93], không phải khoảng tin cậy. Đây là rà soát nội bộ có AI hỗ trợ đã được hai người đọc kiểm tra, không phải nhãn chuyên gia; không báo cáo độ đồng thuận độc lập hay Cohen kappa giữa hai bản sao.
