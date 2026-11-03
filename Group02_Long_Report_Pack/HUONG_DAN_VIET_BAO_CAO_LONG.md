# Nhóm 02 — Số liệu và việc hoàn thiện bản Long

Ngày tổng hợp: 03/11/2026. Bản triển khai được chọn: `Explainable_GEC_Long`.
Tài liệu này đối chiếu phiếu TV1 với kết quả đã lưu của Long. Đây là đầu vào để nhóm viết báo cáo; chưa phải xác nhận bộ nộp đã hoàn tất. Không huấn luyện hoặc đánh giá test lại khi chuẩn bị gói này.

## 1. Phiếu chung đã thống nhất thế nào?

Nhóm chọn TV1 làm phiếu chung. Đã ghép đủ **63/63** ca theo `(record_id, token_index)`, kiểm tra token và toàn bộ source khớp với `outputs/dev_run_001/baseline_ref/fp_reference.csv` của Long. Cả 63 nhãn cũng trùng nhãn chung đang có trong ZIP Long. Nhãn và lý do được giữ nguyên; chỉ chuẩn hóa cách trình bày.

| Nhóm đọc lỗi | Số ca | Ý nghĩa |
| --- | ---: | --- |
| A | 34 | Token được đánh dấu phù hợp ngữ pháp theo cách đọc hiện tại |
| B | 14 | Có thể có lỗi tại token nhưng gold không chú thích |
| C | 15 | Chưa đủ ngữ cảnh để kết luận |

Trong B có **10 ca thuộc ba nhãn**: SVA 5, VFORM 3, NNUM 2; còn 3 ca loại khác và 1 ca chưa xác định. Đây là phân loại trong phiếu được cung cấp, không phải một vòng đánh giá chuyên gia mới.

Phiếu thuộc **LR tham chiếu C = 3, ngưỡng 0,65 trên dev**, với TP/FP/FN untyped = **30/63/233**, tổng 93 cảnh báo. Phiếu không thuộc LR cuối C = 1, ngưỡng 0,45 và không thuộc LR có parser.

| Cách tính từ nhãn hiện có | Precision vị trí |
| --- | ---: |
| Theo gold: 30 / 93 | 32,26% |
| Kịch bản cộng 10 B thuộc ba nhãn: 40 / 93 | 43,01% |
| Kịch bản cộng mọi B, gồm ngoài phạm vi: 44 / 93 | 47,31% |

Không gọi 47,31% là precision benchmark của ba nhãn. Các kịch bản này không thay gold, không sửa điểm chính thức và không áp sang mô hình cuối. Việc khớp phiếu với đầu ra không xác minh tính đúng chuyên môn của từng nhận xét.

**Phương pháp cần khai báo:** TV1 được nhóm chọn làm phiếu chung từ bản nháp có AI hỗ trợ. Hai phiếu trùng nhau không cung cấp bằng chứng hai lượt gán nhãn ban đầu độc lập. Không có số bất đồng trước thảo luận đã được xác lập. Các cột tự kiểm tra trong workbook để trống cho người thực sự đọc bổ sung. Tên/ngày nguồn được giữ như thông tin do phiếu khai, không suy ra một lượt xác minh mới.

## 2. Cấu hình đúng của bản Long

| Hệ thống | Tham số | Ngưỡng | F0,5 typed dev |
| --- | --- | --- | --- |
| LR_base | C = 1.0 | 0.45 | 0.220162 |
| LR_parser | C = 0.1 | 0.35 | 0.228426 |
| kNN | k = 10 | 0.8 | 0.080775 |

LR được fit bằng train. Trong mỗi C, chọn ngưỡng tối đa typed micro F0,5; bằng điểm ưu tiên precision cao rồi ngưỡng cao. Giữa các C, chọn C nhỏ nhất có điểm kém cực đại **dưới 0,005**, dùng số chưa làm tròn. Áp dụng riêng cho LR base và parser. C = 1 của base và C = 0,1 của parser đúng với các đại diện theo C đã lưu của Long.

kNN dùng k = 10 và ngưỡng **0,80** trong triển khai này. Không chép k = 7, ngưỡng 0,60 hoặc điểm dev 0,1656 từ tài liệu tổng hợp cũ. Cũng không dùng ngưỡng kNN 0,75 của triển khai 02/11.

Đặc trưng chỉ lấy từ source; vocabulary và SVD fit trên train. Parser dùng khoảng cách `subject_index - token_index`, không cắt khoảng cách; tổng số chiều parser là 126.847. Việc dùng một quy ước khoảng cách khác triển khai 02/11 không tự làm mô hình sai; cần mô tả đúng quy ước thực tế.

## 3. Bảng kết quả chính để nhóm viết báo cáo

### Dev — typed micro, 263 vị trí gold

| Hệ thống | TP | FP | FN | P | R | F0,5 |
| --- | --- | --- | --- | --- | --- | --- |
| All_O | 0 | 0 | 263 | 0.000000 | 0.000000 | 0.000000 |
| POS | 36 | 222 | 227 | 0.139535 | 0.136882 | 0.138996 |
| LR_base | 38 | 112 | 225 | 0.253333 | 0.144487 | 0.220162 |
| kNN | 10 | 79 | 253 | 0.112360 | 0.038023 | 0.080775 |
| LR_parser | 27 | 55 | 236 | 0.329268 | 0.102662 | 0.228426 |

### Test — typed micro, 272 vị trí gold

| Hệ thống | TP | FP | FN | P | R | F0,5 |
| --- | --- | --- | --- | --- | --- | --- |
| All_O | 0 | 0 | 272 | 0.000000 | 0.000000 | 0.000000 |
| POS | 31 | 217 | 241 | 0.125000 | 0.113971 | 0.122627 |
| LR_base | 41 | 154 | 231 | 0.210256 | 0.150735 | 0.194867 |
| kNN | 14 | 72 | 258 | 0.162791 | 0.051471 | 0.113636 |
| LR_parser | 27 | 79 | 245 | 0.254717 | 0.099265 | 0.193966 |

CSV untyped và typed theo từng loại nằm trong `report_tables/`. Các metric được tính lại từ TP/FP/FN để kiểm tra số học; không tạo dự đoán mới.

Trên test của Long, LR base có 41 TP và 154 FP; POS có 31 TP và 217 FP. LR base tìm đúng thêm 10 lỗi và giảm 63 cảnh báo nhầm theo typed scoring. LR parser có precision cao hơn và recall thấp hơn base. Hai điểm test gần nhau không chứng minh hai mô hình tương đương hoặc khác nhau có ý nghĩa thống kê.

Trên dev, parser được chọn có F0,5 cao hơn base. Vì vậy không viết rằng LR base là mô hình tốt nhất trên dev của Long. Giữ cả hai nhánh LR trong phép so sánh đã khai báo; không tạo một câu chuyện lựa chọn trước test mà hồ sơ không ghi.

## 4. Thí nghiệm parser theo yêu cầu thầy

| Nhánh | C | Ngưỡng | TP SVA | FP SVA | FN SVA | F0,5 SVA |
| --- | --- | --- | --- | --- | --- | --- |
| LR_base_control | 1.0 | 0.45 | 12 | 41 | 62 | 0.209790 |
| LR_parser_control | 1.0 | 0.45 | 11 | 41 | 63 | 0.195035 |
| LR_parser_selected | 0.1 | 0.35 | 12 | 16 | 62 | 0.322581 |

Bảng đủ ba nhãn và MICRO nằm ở `report_tables/teacher_comparison_dev_Long.csv`.

Ở cùng C = 1 và ngưỡng 0,45, tổng TP typed giữ 38, FP tăng từ 112 lên 122; riêng SVA, TP giảm từ 12 xuống 11 và FP giữ 41. Kết quả này **không cho thấy parser giảm FP SVA ở cùng điểm quyết định**.

Parser được chọn C = 0,1, ngưỡng 0,35 có ít FP SVA hơn, nhưng đã đổi C/ngưỡng. Không gán toàn bộ chênh lệch đó riêng cho việc thêm parser.

`parser_four_cases.csv` hiện so base được chọn C = 1 / 0,45 với parser được chọn C = 0,1 / 0,35. Các xác suất trong bảng này không phải phép can thiệp trên cùng mô hình. Mã FP02 chẩn đoán là `dev:001408`, token 3 `realize`, khác mã FP002 trong phiếu 63 ca.

Đã bổ sung script `fp02_intervention_dev.py`: giữ cùng parser LR C = 1, ngưỡng 0,45, thay riêng ba giá trị đặc trưng chủ ngữ ở FP02. Script chỉ dùng dev và mô hình đã fit. **Chưa chạy với mô hình Long trong phiên này**, vì ZIP không chứa mô hình C = 1. Không ghi kết quả can thiệp là đã có cho đến khi Long chạy và lưu CSV/JSON.

## 5. Những phần còn phải hoàn thiện

| Ưu tiên | File / phần | Việc cần làm và bằng chứng hoàn tất |
| --- | --- | --- |
| 1 | `summarize_reviews.py`, `tests/test_reviews.py` | Áp dụng `fix_review_status.patch`: tách đủ ô điền khỏi đánh giá độc lập, bỏ tự suy bất đồng trước thảo luận = 0, bỏ ngày review hardcode. Giữ phiếu TV1 làm bản chung và các phiếu nguồn riêng. Bản vá được kiểm tra bằng xử lý CSV/JSON, không chạy mô hình. |
| 1 | Bằng chứng đọc lỗi | Thành viên tự đọc, kiểm chứng và sửa nhận xét nếu cần; ghi người/ngày thực tế. Yêu cầu hai lượt ban đầu độc lập chưa được đáp ứng bằng hai bản sao nháp chung. Nếu có lượt đánh giá bổ sung, ghi đúng điều kiện đã tiếp xúc nháp trước đó. Không dùng việc chuẩn hóa file để tuyên bố đã hoàn thành đọc độc lập. |
| 1 | Dự đoán và mô hình đã lưu | Bổ sung đủ `outputs/dev_run_001/predictions_*.csv`, `baseline_ref/predictions_dev.csv`, `outputs/fixed_point_check/predictions_LR_parser_C1.0_tau0.45.csv` và dự đoán trong thư mục test. Cần mô hình/vocabulary đã lưu để kiểm tra mẫu trực tiếp, gồm parser C = 1 cho FP02. ZIP hiện tại không có các dự đoán đầy đủ và mô hình. Lấy từ lần chạy đã có. |
| 2 | Kiểm tra FP02 | Chạy script bổ sung với đúng mô hình đã lưu, giữ CSV và thông tin chạy. Đọc kết quả thực tế, kể cả khi dự đoán không đổi. Không huấn luyện lại hoặc dùng test cho bước này. |
| 2 | Giới hạn parser | Đọc vài ca của chính parser Long, lưu record/token, chủ ngữ quan sát và lý do. MISSING, chủ ngữ bên phải hoặc khác danh từ gần nhất chỉ là cờ tìm ca, chưa chứng minh parser sai. |
| 2 | `README.md`, notebook, tài liệu tổng hợp | Cập nhật test đã hoàn tất ngày 03/11. Thay bảng và quy tắc sai bằng CSV trong gói này. Notebook trình bày đọc đầu ra đã lưu, không tự chạy test khi Run All. Giữ file khóa gốc như snapshot trước test. |
| 2 | Dữ liệu / môi trường | Cung cấp nguồn và phiên bản dữ liệu hợp lệ, checksum, split IDs; hướng dẫn cài đúng `requirements-lock.txt`, NLTK và spaCy. Dữ liệu có thể cung cấp qua nguồn hợp lệ thay vì nhúng vào ZIP. |
| 3 | Báo cáo / đóng góp / lịch sử test | Dùng số của Long nhất quán, mô tả O không đồng nghĩa đúng ngữ pháp, phạm vi subset 1–1 và đơn vị bản ghi. Ghi đóng góp thực tế và AI hỗ trợ. Nhóm đã có đợt triển khai 02/11 và Long 03/11, nên không khẳng định cả nhóm chỉ mở test một lần. Không chọn lại C/ngưỡng theo test. |

Phần rubric đọc ít nhất 10 lỗi có thể lấy từ bộ dev tham chiếu nếu các thành viên thực sự đọc và giải thích được; không bắt buộc thêm một vòng huấn luyện. Nếu muốn phân tích riêng LR cuối của Long, lấy mẫu từ **dự đoán Long đã lưu**; không dùng CSV 10 FP/10 FN của triển khai 02/11 như thể là cùng mô hình.

## 6. Cách dùng gói này

1. Giữ nguyên ZIP và kết quả gốc của Long. Đây là gói bổ sung, không phải toàn bộ bộ nộp chạy được.
2. Đọc `Group02_FP63_Consensus.xlsx` và dùng `review_consensus.csv` làm bảng chung. Không chép phiếu chung đè lên hai phiếu nguồn để biến chúng thành hai lượt đọc độc lập.
3. Xem `README.md` để áp dụng bản vá và chạy kiểm tra FP02 trên máy Long.
4. Viết báo cáo bằng bảng trong `report_tables/` và lập luận ở mục 3–4. Dùng kết quả thực tế sau khi kiểm tra, không ép về dự đoán ban đầu của thầy.
5. Gom dự đoán, nguồn dữ liệu, cấu hình và log còn thiếu; kiểm tra một ID từ source → đặc trưng → xác suất/ngưỡng → dự đoán → gold.

## Căn cứ yêu cầu

- MLA Final Project Requirements and Rubric, 26/10/2026, trang 1–3 và 6–8.
- Nhận xét Tuần 10 Đại trà Nhóm 2, 27/10/2026: ba việc bắt buộc gồm đọc 63 FP độc lập, tái lập parser cùng điểm quyết định, quy tắc chọn trong code và khóa trước test.
- Các file trong ZIP `Explainable_GEC_Long.zip` và phiếu TV1 được cung cấp. File nội bộ dùng làm bằng chứng, không thay tài liệu tham khảo khoa học.
