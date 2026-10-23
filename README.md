# EXPECT - Phần thực hiện của Long

Bản làm việc độc lập của pipeline phát hiện token lỗi SVA/VFORM/NNUM trên source. Mã gốc được giữ nguyên trong `legacy_source/`; các CSV cũ nằm trong `legacy_results/`. Chỉ train/dev được sao chép. Không có dữ liệu test trong gói này.

## Chạy trên máy hiện tại

Mở PowerShell tại thư mục dự án:

```powershell
.\run_dev.ps1 -Stage audit
.\run_dev.ps1 -Stage all
```

Script chọn Python đi kèm Codex nếu có. Có thể chỉ định Python riêng:

```powershell
.\run_dev.ps1 -PythonExe 'C:\path\to\python.exe' -Stage all
```

Lần chạy tiếp dùng lại POS/parser/matrix và các model đã fit khi metadata khớp. Pipeline vẫn tính lại scoring và xuất kết quả từ model. Không chạy lại trên test.

## Cài trên máy khác

Sử dụng CPython 3.12 64-bit. Các dependency cục bộ của máy hiện tại trong `.deps/` không được đóng gói để chuyển sang máy khác.

```powershell
python -m pip install -r requirements-lock.txt
python prepare_resources.py
python -m unittest discover -s tests -v
python run_dev.py --stage all
```

Downloader chỉ chạy khi gọi `prepare_resources.py`. Không tải tài nguyên khi import hay khi chạy training. Không tắt xác minh TLS. POS dùng ba file JSON của NLTK và kiểm tra SHA-256. Model spaCy có checksum được ghi trong requirements.

## Luồng dữ liệu

1. Decoder dùng nguyên hàm đã audit: target + [MOD] + source; source offset bằng len(target)+1.
2. Bỏ [NONE], ánh xạ chỉ số source về token thật.
3. Chỉ giữ edit mục tiêu 1-1 có thay đổi; bản ghi ngoài phạm vi giữ toàn O.
4. Các đặc trưng chỉ nhận source. Target chỉ dùng tạo gold và diễn giải annotation tham chiếu.
5. Tất cả hệ thống dùng chung dữ liệu và scorer.

Số kiểm tra: train 14.610 bản ghi / 416.571 token / 3.863 gold; dev 2.367 / 68.382 / 263. Nếu lệch, chương trình dừng.

## Mô hình và lựa chọn

- All O và luật POS: luật giữ nguyên bản gốc, dự đoán thật bằng POS hiện tại.
- LR nền: đặc trưng từ/POS ±3, hình thái, n-gram, ngữ cảnh trái và danh từ/đại từ gần nhất bên trái; min_count=3; vocabulary chỉ fit train.
- LR parser: giữ nguyên đặc trưng nền, thêm ba đặc trưng cho VERB/AUX: POS chủ ngữ, Number của chủ ngữ và khoảng cách có hướng subject_index-token_index. Thiếu chủ ngữ dùng <NONE>/<UNK>. Chủ ngữ lấy trực tiếp; aux có thể dùng chủ ngữ của lexical head. Không dùng gold parsing order.
- spaCy nhận `Doc(words=...)` để giữ token EXPECT; mọi token train/dev đều được đối chiếu sau parsing. Chỉ khoảng trắng được chuẩn hóa giữa các token, không đưa token mới vào.
- LR dùng lbfgs/L2, class_weight=None, max_iter=1000, tol=1e-4. Grid C={0.1,0.3,1,3}, tau=0.05..0.95, bước 0.05.
- Trong mỗi C: tối đa typed micro F0.5; hòa chính xác ưu tiên P cao, rồi tau cao. Giữa các C: chọn C nhỏ nhất có F0.5 thấp hơn cực đại dưới 0.005. Quy tắc ghi trước fit, áp dụng giống nhau cho hai LR.
- kNN: SVD 200 chiều fit train; chuẩn hóa trước/sau SVD; cosine; toàn bộ 3.863 token lỗi + 38.630 O lấy mẫu, seed=0. k={5,10,20,50}, cùng grid tau. Hòa phiếu loại lỗi dùng thứ tự SVA,VFORM,NNUM như mã cũ.

## LR tham chiếu khác LR được chọn

`LR_reference_C3_tau065` luôn dùng C=3, tau=0.65 để đối chiếu report Week 9 và tạo phiếu review. `LR_base` dùng quy tắc lựa chọn ở trên, có thể chọn C khác. Không gắn precision rà soát của mô hình tham chiếu cho mô hình đã đổi cấu hình.

Không ép số FP phải bằng 63 và không ép điểm phải bằng 0.220/0.233. Các bảng giữ số đầy đủ; chỉ làm tròn khi viết báo cáo.

## Bàn giao

Kết quả chạy trong `outputs/dev_run_001/`:

- `metrics_dev.csv`: TP/FP/FN, P/R/F1/F0.5 typed/untyped và từng loại.
- `tuning_grid.csv`: grid đủ của hai LR và kNN.
- `baseline_ref/`: model reference metrics, prediction, FP/FN và hai phiếu review trống.
- `parser_four_cases.csv`: bốn trường hợp trong nhận xét instructor, trên các cấu hình đã chọn.
- `metrics_dev_without_duplicate.csv`: bỏ source dev trùng train, không tuning lại.
- `config_locked.json`: cấu hình và hash model đã đóng băng từ dev; nhóm vẫn cần kiểm tra trước khi mở test.
- `run_manifest.json`: dữ liệu, phiên bản, code hash và trạng thái từng giai đoạn.

Hai phiếu Loan/Yến dành cho người đọc độc lập. Chương trình không tự điền nhãn hoặc giả định nhóm đã thống nhất.

## Test cuối

`run_dev.py` không có tùy chọn test và có guard cấm mở test.json/test.pkl. Test cuối là entry point riêng `run_final_test.py`; không được notebook hoặc script dev gọi tự động. Đọc hướng dẫn trước khi quyết định mở test. Không có kết quả test được tạo trong lần thực hiện hiện tại.

## Nguồn kỹ thuật

- Mã/dữ liệu EXPECT: https://github.com/lorafei/Explainable_GEC (snapshot và SHA-256 trong SOURCE_MANIFEST.json).
- Giữ token có sẵn với spaCy: https://spacy.io/usage/linguistic-features#own-annotations
- Model spaCy và SHA-256: https://github.com/explosion/spacy-models/releases/tag/en_core_web_sm-3.8.0

Kết quả chỉ có hiệu lực trên subset gold-conditioned 1-1. O nghĩa là không có annotation mục tiêu trong bản ghi, không phải chứng nhận token đúng. Điểm dev đã được dùng chọn tham số. Rà soát FP là đánh giá nội bộ, không phải nhãn chuyên gia.

