# Kiểm đếm EXPECT và kiểm tra chuyển nhãn

Bước 1 chỉ kiểm tra dữ liệu và đơn vị đếm. Không huấn luyện mô hình, không sinh dự đoán, không tính P/R/F và không thay đổi dữ liệu gốc.

## Đơn vị phải phân biệt

- Bản ghi annotation: một phần tử JSON, có một error_type và một edit được annotation. Không tự gọi mỗi bản ghi là một câu văn độc lập.
- Chuỗi source duy nhất: nhóm theo toàn bộ dãy token source sau khi bỏ [NONE], giữ nguyên chữ hoa/thường. Đây là định danh theo văn bản vì không có ID câu/tài liệu; hai lần xuất hiện độc lập có cùng văn bản có thể bị gộp.
- Token thật: token source khác [NONE]. Bảng tách token đếm theo lượt bản ghi và token đếm một lần mỗi chuỗi source.
- Edit được annotation: một thao tác sửa có thể liên quan nhiều token hoặc chỉ một chỗ trống cần chèn. Hai token trong một span không tự động là hai lỗi ngữ pháp độc lập.
- Vị trí lỗi: vị trí token thật trong source có annotation của ba loại mục tiêu. Chỗ chèn được đếm riêng là gap, không phải token lỗi.
- Nhãn O: không có nhãn mục tiêu tại token đó trong bản ghi hiện tại; không đồng nghĩa với đúng ngữ pháp hoặc câu sạch.

## Bảng trước và sau lọc

| Split | Giai đoạn | Bản ghi | Chuỗi source duy nhất | Token thật theo lượt bản ghi | Edit ba loại | Vị trí token ba loại | Gap ba loại |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| train | trước lọc | 15187 | 15051 | 432611 | 4440 | 4385 | 211 |
| train | sau lọc | 14610 | 14479 | 416571 | 3863 | 3863 | 0 |
| dev | trước lọc | 2413 | 2413 | 69648 | 309 | 315 | 8 |
| dev | sau lọc | 2367 | 2367 | 68382 | 263 | 263 | 0 |

Token thật khác số token có cả placeholder trong báo cáo cũ. Xem đầy đủ hai cách đếm trong `counts_summary.csv`.

## Phân bố số lỗi mỗi đơn vị

`error_count_distribution.csv` tách hai đơn vị: lượt bản ghi và nhóm chuỗi source; mỗi đơn vị có cả số edit và số vị trí token. Không dùng số vị trí token để thay thế số edit.

| Split | Giai đoạn | Chuỗi source có 0 vị trí mục tiêu | Có 1 vị trí | Có ≥2 vị trí |
| --- | --- | ---: | ---: | ---: |
| train | trước lọc | 10843 | 4060 | 148 |
| train | sau lọc | 10636 | 3843 | 0 |
| dev | trước lọc | 2112 | 288 | 13 |
| dev | sau lọc | 2104 | 263 | 0 |

Một edit có thể gồm nhiều vị trí; bảng trên là số vị trí, không phải số lỗi độc lập. Bảng edit sau lọc:

| Split sau lọc | Chuỗi source có ≥2 edit mục tiêu đã annotation | Chuỗi source có ≥2 vị trí mục tiêu | Vị trí có nhãn mục tiêu mâu thuẫn |
| --- | ---: | ---: | ---: |
| train | 0 | 0 | 0 |
| dev | 0 | 0 | 0 |

Các số này chỉ mô tả annotation được quan sát. Không kết luận mỗi câu tự nhiên có tối đa một lỗi. Việc lọc có điều kiện trên gold đã đổi quần thể đánh giá.

Trên dev sau lọc, 2367 bản ghi thuộc 2367 chuỗi source khác nhau. Đếm trực tiếp có 263 bản ghi được annotation edit mục tiêu và 2104 bản ghi không có annotation của ba loại mục tiêu. Phép trừ cho đúng số trong trường hợp này sau khi đã kiểm tra số chuỗi trùng và số edit mỗi chuỗi; không mặc định coi số token lỗi là số câu có lỗi.

## Phạm vi và số mẫu bị loại

Giữ bản ghi thuộc SVA/VFORM/NNUM chỉ khi span source và target đều đúng một token, không [NONE], có thay đổi. Bản ghi thuộc các loại khác được giữ với nhãn mục tiêu toàn O, giống thiết kế cũ. Chúng không phải tập câu sạch đã được chứng nhận.

| Split | SVA sau lọc | VFORM sau lọc | NNUM sau lọc | Tổng sau lọc | Mẫu mục tiêu bị loại |
| --- | ---: | ---: | ---: | ---: | ---: |
| train | 1005 | 1190 | 1668 | 3863 | 577 |
| dev | 74 | 69 | 120 | 263 | 46 |

Loại nào và vì sao bị loại được đếm chính xác trong `exclusion_summary.csv`; ID, span và quyết định của mọi bản ghi nằm ở `records_audit.csv`.

## Lỗi offset của code cũ

Script gốc `read_jsonl.py` ghép `target + [MOD] + source`; vì vậy source_offset phải là **len(target)+1**. Code cũ của nhóm tách bằng len(source), nên sai khi hai chuỗi có độ dài khác nhau. Với cặp dài bằng nhau, hai cách có thể trùng kết quả và che khuất lỗi này.

| Split | Lỗi mục tiêu 1-1 theo cách cũ | Theo giải mã đúng | Mẫu có quyết định/nhãn khác |
| --- | ---: | ---: | ---: |
| train | 3871 | 3863 | 8 |
| dev | 263 | 263 | 0 |

Đọc `legacy_mismatches.csv` để kiểm chứng từng mẫu. Các điểm mô hình ở báo cáo Week 8 thuộc pipeline cũ; chưa phải kết quả sau khi sửa chuyển nhãn. Cần dùng cách chuyển đúng khi chạy các bước tiếp theo.

## Năm ví dụ

| Ví dụ | ID | Loại gộp | Span source → target | Quyết định |
| ---: | --- | --- | --- | --- |
| 1 | dev:000756 | SVA | pollute → pollutes | giữ |
| 2 | dev:001803 | VFORM | have → having | giữ |
| 3 | dev:000823 | NNUM | failures → failure | giữ |
| 4 | dev:000257 | ngoài ba loại | [NONE] → to | giữ |
| 5 | train:013924 | VFORM | To fly → Flying | loại |

Xem bảng token đầy đủ trong `examples_5.md`; `examples_5.json` giữ cả annotation gốc và ánh xạ chỉ số.

## Dấu vết tái lập

`run_manifest.json` lưu SHA-256 từng JSON đầu vào, các split đã đọc và chính sách chuyển đổi. Không có tải mạng hay dependency ngoài thư viện chuẩn. Kết quả chỉ kiểm tra annotation trong file, không chứng minh dữ liệu đã gán nhãn đầy đủ hoặc đúng chuyên môn.
