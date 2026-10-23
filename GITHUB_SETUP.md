# Bắt đầu từ bản clone GitHub

Repo chứa phần việc của Long: pipeline đã audit alignment, baseline All-O/POS, LR, kNN, thử nghiệm dependency parser, notebook, unit tests và kết quả DEV đã khóa. Không chứa phần việc của Mai Yến. Test chưa được mở hoặc chấm; hai phiếu review độc lập của Loan/Yến vẫn để trống.

## 1. Clone repository

```powershell
git clone https://github.com/longnguyen005/Explainable_GEC_Long.git
cd Explainable_GEC_Long
```

Repository riêng tư: đăng nhập tài khoản có quyền truy cập khi clone hoặc tải Release.

## 2. Khôi phục dữ liệu và model từ Release

Mở [Long DEV handoff v1](https://github.com/longnguyen005/Explainable_GEC_Long/releases/tag/long-dev-v1), tải `Explainable_GEC_Long_handoff.zip`, kiểm tra SHA-256 theo phần mô tả Release. ZIP có sẵn thư mục gốc `Explainable_GEC_Long/`: giải nén vào **thư mục cha của bản clone**, cho phép gộp vào folder project cùng tên. Không giải nén bên trong project vì sẽ tạo thêm một thư mục lồng.

Gói này là snapshot gốc của lần chạy DEV ngày 22/10/2026: train/dev, fitted models, predictions, kết quả, manifests và tài nguyên NLTK POS. Không có dữ liệu hoặc kết quả test. `.deps/` và runtime cache không nằm trong ZIP; model spaCy được cài từ requirements, xem bước 3.

`data/`, `models/`, `cache/`, `resources/`, các CSV dự đoán đầy đủ và bảng audit từng record được bỏ khỏi Git. Model kNN khoảng 128 MB vượt giới hạn file Git thông thường; các artifact lớn được phân phối qua Release. Git vẫn lưu bảng metrics, tuning, cấu hình, audit tóm tắt, bốn ví dụ parser và phiếu review.

`ARTIFACTS_SHA256.json` mô tả snapshot trong ZIP, không bao gồm các file thiết lập GitHub được thêm sau đó. Không chỉnh các file code/model đã khóa nếu muốn xác minh lại đúng snapshot.

## 3. Cài môi trường và kiểm tra

Dùng CPython 3.12 64-bit. Từ thư mục project:

```powershell
python -m pip install -r requirements-lock.txt
python prepare_resources.py
python -m unittest discover -s tests -v
python verify_run.py
```

`verify_run.py` kiểm tra các artifact DEV có sẵn, gồm nạp model và đối chiếu dự đoán trên dev; không huấn luyện hay chấm test. Nếu chỉ clone mà chưa giải nén Release, công cụ sẽ thiếu dữ liệu/model/predictions.

Đọc [README.md](README.md) để xem pipeline và cách chạy lại dev, [LONG_HANDOFF.md](LONG_HANDOFF.md) để xem phân tích kết quả. Không cần train lại để đọc bảng đã xuất.

## 4. Các điểm cần giữ khi trình bày

- LR tham chiếu C=3, tau=0,65 tạo 63 FP **untyped**; typed có 65 FP. LR base được chọn là C=1, tau=0,45.
- LR tham chiếu giảm FP so với POS (222→65), TP cũng giảm (36→28).
- Parser được chọn C=0,1, tau=0,35: giảm FP SVA nhưng TP SVA vẫn 12; không cải thiện mọi loại lỗi.
- Kết quả chỉ trên dev đã dùng tuning, subset edit 1–1; có một source trùng train–dev và bảng sensitivity riêng.
- Phiếu con người chưa hoàn tất; không có consensus hoặc precision rà soát được giả lập.
- `run_final_test.py` chỉ được dùng sau khi có quyết định mở test và xác nhận cấu hình. Việc đưa code lên GitHub không thực hiện đánh giá test.
