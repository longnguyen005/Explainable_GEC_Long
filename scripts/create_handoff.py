"""Generate human-readable handoff and a genuinely executed inspection notebook."""
import ast
import contextlib
import csv
import importlib.metadata
import io
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import bootstrap
import nbformat
from gec.io_utils import read_json, sha256, timestamp, write_csv, write_json


def read_csv(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def md_table(rows, columns):
    result = ['| ' + ' | '.join(columns) + ' |', '| ' + ' | '.join('---' for _ in columns) + ' |']
    for row in rows:
        values = []
        for name in columns:
            value = row.get(name, '')
            if name in ('P', 'R', 'F1', 'F0.5') and value != '':
                value = f'{float(value):.6f}'
            values.append(str(value).replace('|', '/').replace('\n', ' '))
        result.append('| ' + ' | '.join(values) + ' |')
    return '\n'.join(result)


def main():
    out = ROOT / 'outputs/dev_run_001'
    verification = read_json(out / 'verification.json')
    if verification['status'] != 'passed':
        raise RuntimeError('Verification must pass before handoff.')
    metrics = read_csv(out / 'metrics_dev.csv')
    micro = [r for r in metrics if r['label'] == 'MICRO']
    classes = [r for r in metrics if r['label'] != 'MICRO' and r['system'] in ('LR_base', 'LR_parser')]
    selected = read_json(out / 'selected_config.json')
    grid = read_csv(out / 'tuning_grid.csv')
    counts = read_csv(out / 'data_counts.csv')
    cases = read_csv(out / 'parser_four_cases.csv')
    reference_rows = read_csv(out / 'baseline_ref/predictions_dev.csv')
    ref_lookup = {(r['record_id'], r['token_index']): r for r in reference_rows}
    for case in cases:
        ref = ref_lookup[(case['record_id'], case['token_index'])]
        case['reference_C3_tau065_prediction'] = ref['prediction']
        case['reference_C3_tau065_p_error'] = ref['p_error']
    write_csv(out / 'parser_four_cases.csv', cases)

    base = read_csv(out / 'predictions_LR_base.csv')
    parser = read_csv(out / 'predictions_LR_parser.csv')
    transitions, change_counts = [], {}
    for left, right in zip(base, parser):
        if (left['record_id'], left['token_index'], left['gold']) != (right['record_id'], right['token_index'], right['gold']):
            raise AssertionError('Parser comparison row mismatch.')
        if left['prediction'] == right['prediction']:
            continue
        gold, before, after = left['gold'], left['prediction'], right['prediction']
        if gold != 'O' and before != gold and after == gold:
            kind = 'recovered_gold'
        elif gold != 'O' and before == gold and after != gold:
            kind = 'lost_gold'
        elif gold == 'O' and before != 'O' and after == 'O':
            kind = 'removed_FP'
        elif gold == 'O' and before == 'O' and after != 'O':
            kind = 'new_FP'
        else:
            kind = 'other_type_change'
        change_counts[kind] = change_counts.get(kind, 0) + 1
        transitions.append({'change': kind, 'record_id': left['record_id'], 'token_index': left['token_index'],
                            'token': left['token'], 'gold': gold, 'base_prediction': before,
                            'parser_prediction': after, 'base_p_error': left['p_error'],
                            'parser_p_error': right['p_error'], 'source': left['source']})
    write_csv(out / 'parser_changed_predictions.csv', transitions)
    write_json(out / 'parser_change_counts.json', change_counts)

    per_C = []
    for variant in ('base', 'parser'):
        for row in selected[f'LR_{variant}']['per_C_best']:
            per_C.append({**row, 'selected_C': row['C'] == selected[f'LR_{variant}']['parameters']['C']})
    write_csv(out / 'lr_best_per_C.csv', per_C)
    source_manifest = read_json(ROOT / 'SOURCE_MANIFEST.json')
    original_root = Path(source_manifest['source_directory'])
    original_unchanged = all(sha256(original_root / Path(name).name) == expected
                             for name, expected in source_manifest['snapshots'].items())
    write_json(out / 'original_source_check.json', {'checked_at': timestamp(), 'original_sources_unchanged': original_unchanged,
                                                  'test_files_checked': False})
    if not original_unchanged:
        raise AssertionError('An original source changed unexpectedly.')

    reference_metric = next(r for r in micro if r['system'] == 'LR_reference_C3_tau065' and r['scoring'] == 'untyped')
    fp = int(reference_metric['FP'])
    tp = int(reference_metric['TP'])
    review_status = read_json(out / 'baseline_ref/review_status.json')
    instructions = f'''# Phiếu review cho Loan và Yến

Danh sách này thuộc LR tham chiếu C=3, tau=0.65, dữ liệu đã sửa alignment. Có {tp} TP và {fp} FP untyped, tổng {tp+fp} cảnh báo. Không dùng danh sách này để đánh giá LR_base có cấu hình khác hoặc LR_parser.

1. Loan (`review_Loan.csv`, bản gốc `raw_TV1_Loan.csv`) và Yến (`review_Yen.csv`, bản gốc `raw_TV2_Yen.csv`) đã kiểm tra đủ {fp} ca.
2. Nhãn `review_label_A_B_C` gồm A/B/C; kèm `reason`, `suggested_error_type`, `suggested_correction`, `reviewer`, `reviewed_at`.
3. A: token phù hợp ngữ pháp, mô hình báo nhầm ({review_status.get('A', 0)} ca). B: có lỗi tại vị trí dự đoán mà annotation chưa phản ánh ({review_status.get('B', 0)} ca, trong đó {review_status.get('B_in_scope_3_types', 0)} ca thuộc SVA/VFORM/NNUM và {review_status.get('B_out_of_scope', 0)} ca ngoài phạm vi/chưa chốt thì). C: chưa chắc hoặc thiếu ngữ cảnh ({review_status.get('C', 0)} ca).
4. Kết quả tổng hợp lưu tại `independent_comparison.csv`, `review_consensus.csv` và `review_status.json`.

Precision vị trí rà soát (chỉ tính B thuộc 3 nhãn SVA/VFORM/NNUM) = ({tp}+{review_status.get('B_in_scope_3_types', 0)})/{tp+fp} = {review_status.get('estimated_precision_in_scope_3_types', 0):.6f}.
Precision vị trí rà soát (tính toàn bộ B) = ({tp}+{review_status.get('B', 0)})/{tp+fp} = {review_status.get('estimated_precision', 0):.6f}.
Cận giả định = [({tp}+B)/{tp+fp}, ({tp}+B+C)/{tp+fp}], không phải khoảng tin cậy. Đây là rà soát nội bộ có AI hỗ trợ đã được hai người đọc kiểm tra, không phải nhãn chuyên gia; không báo cáo độ đồng thuận độc lập hay Cohen kappa giữa hai bản sao.
'''
    (out / 'baseline_ref/REVIEW_GUIDE_VI.md').write_text(instructions, encoding='utf-8')

    case_text = '''- FP02 `realize` (`dev:001408`, token 3): *Quan sát:* parser trích xuất đúng chủ ngữ `people` (`NNS`, `Plur`, `-2`), nhưng cả LR nền (`C=1.0, tau=0.45`), LR parser cùng điểm (`C=1.0, tau=0.45`) lẫn LR parser được chọn (`C=0.1, tau=0.35`) đều vẫn dự đoán `SVA`; khi can thiệp thay riêng đặc trưng chủ ngữ từ `people` sang `today` ở cùng mô hình `C=1.0`, `p_error` chỉ đổi nhẹ (`0.993020 -> 0.989731`). *Giả thuyết:* các đặc trưng cửa sổ cục bộ (`subj_w=today`, `p-1|p=NN|VBP`) vẫn được giữ nguyên và 3 đặc trưng parser chưa ghép chéo với nhãn động từ `VBP`.
- FP03 `is` (`dev:000644`, token 6): *Quan sát:* parser trích xuất đầu ngữ chủ ngữ danh động từ `learning` (`VBG`, `-3`) thay vì danh từ `languages` (`NNS`), nhưng `subject_number` là `<UNK>` và cảnh báo `SVA` vẫn còn. *Giả thuyết:* token `VBG` trong `spaCy` không có thuộc tính hình thái `Number` nên `describe()` gán `<UNK>` thay vì biểu diễn chủ ngữ mệnh đề `VBG` như ngôi thứ 3 số ít.
- FN01 `is` (`dev:001866`, token 39): *Quan sát:* parser trích xuất chủ ngữ bên phải `reasons` (`NNS`, `Plur`, `+2`) và `p_error` tăng (`0.011861 -> 0.034733` ở `C=1.0`; `0.069654` ở `C=0.1`), nhưng vẫn thấp hơn ngưỡng nên FN vẫn còn. *Giả thuyết:* biên quyết định tổng thể vẫn bị kéo về lớp `O` bởi các đặc trưng ngữ cảnh cục bộ xung quanh (`what is our ...`).
- FN04 `is` (`dev:001892`, token 11): *Quan sát:* tại động từ `is` thứ hai trong câu ghép nối bằng dấu phẩy, `describe()` trả về `subject_text=<NONE>, subject_number=<UNK>` do token 11 không có con trực tiếp thuộc `SUBJECT_DEPS = {'nsubj', 'nsubjpass', 'csubj', 'csubjpass'}` (lưu ý: `SUBJECT_DEPS` trong `gec/dependency.py` không có `expl`). LR nền `C=1.0` dự đoán đúng `SVA` (`p_error=0.473200`), còn LR parser trả về `O` (`p_error=0.073707` ở `C=1.0`; `0.150214` ở `C=0.1`), tạo một hồi quy FN. *Giả thuyết:* quy tắc chỉ tìm con trực tiếp trong `SUBJECT_DEPS` (hoặc qua head của `aux`/`auxpass`/`cop`) không lấy được danh ngữ `chances` phía trước trong cấu trúc comma splice. Tên `FN04` là mã ca trong report của LR tham chiếu `C=3.0`.
'''
    handoff = f'''# Bàn giao phần thực hiện của Long

Ngày tạo: {timestamp()}

## Trạng thái

Đã sửa pipeline dữ liệu, chạy All O/POS/LR/kNN, tái tạo LR tham chiếu Week 9, hoàn thành thí nghiệm dependency (gồm cả kiểm tra cùng điểm quyết định `C=1.0, tau=0.45` và can thiệp đặc trưng tại `FP02`), lưu model/config, kiểm tra lại dự đoán sau khi nạp model, chuẩn hóa/tổng hợp kết quả rà soát 63 FP của Vũ Thị Loan (TV1) và Mai Hải Yến (TV2), và hoàn tất đánh giá một lần trên tập `test` ngày 03/11/2026 tại `outputs/final_test_cc1e75b079e005f0/`. Mã gốc không đổi. Trong giai đoạn phát triển (`outputs/dev_run_001/`), chỉ `train`/`dev` được đọc và cấu hình đã được khóa trước khi mở `test`.

## Dữ liệu đã kiểm tra

{md_table(counts, ['split', 'original_records', 'records', 'tokens', 'SVA', 'VFORM', 'NNUM', 'excluded_records'])}

Alignment dùng target+[MOD]+source, offset len(target)+1. Train loại 577 bản ghi, gồm 8 bản ghi bị giữ nhầm bởi code cũ. Dev loại 46. Một source trùng train/dev được giữ trong bảng chính theo split công khai; bảng độ nhạy bỏ source dev trùng nhưng không tuning lại.

## Kết quả đầy đủ trên dev

{md_table(micro, ['system', 'scoring', 'TP', 'FP', 'FN', 'P', 'R', 'F0.5'])}

Phân biệt LR tham chiếu C=3/tau=0.65 với LR nền được chọn bằng quy tắc gần hòa (chọn C nhỏ nhất có F0.5 thấp hơn mức cực đại **dưới 0,005** theo số thực chưa làm tròn). LR tham chiếu khớp report Week 9: typed 28/65/235 và untyped 30/63/233. Điểm 0.233 trong CSV gốc thuộc pipeline cũ; không dùng làm điểm mới. Lần chạy mới dùng NLTK 3.9.2, khác tên phiên bản NLTK ghi trong report, nhưng tái tạo đúng đặc trưng và số đếm LR tham chiếu.

## Thí nghiệm parser

LR nền chọn C={selected['LR_base']['parameters']['C']}, tau={selected['LR_base']['parameters']['tau']}. LR parser chọn C={selected['LR_parser']['parameters']['C']}, tau={selected['LR_parser']['parameters']['tau']}. Hai phiên bản dùng cùng grid và quy tắc gần hòa được ghi trước fit. Vì cả C/ngưỡng có thể thay đổi, cần tách bạch phép so ở cùng C/ngưỡng cố định và phép so hai cấu hình được chọn.

Vocab nền 126.797 đặc trưng; parser 126.847. Tập quan hệ chủ ngữ trong `gec/dependency.py` là `SUBJECT_DEPS = {{'nsubj', 'nsubjpass', 'csubj', 'csubjpass'}}` (không có `expl`). Parser giữ khớp toàn bộ 484.953 token train/dev, chạy trên source, không dùng correction/evidence/parsing order của gold.

{md_table(classes, ['system', 'label', 'TP', 'FP', 'FN', 'P', 'R', 'F0.5'])}

Kết luận trên `dev`:
1. **Ở phép so cùng `C=1.0, tau=0.45` (`outputs/fixed_point_check/metrics_parser_fixed_point.csv`):** Tổng TP typed giữ nguyên 38, tổng FP tăng 112 -> 122 (F0.5 micro 0.220162 -> 0.210410); riêng nhãn `SVA`, **TP SVA giảm 12 -> 11; FP giữ 41** (F0.5 SVA 0.209790 -> 0.195035). Như vậy tại cùng điểm quyết định `C=1.0, tau=0.45`, thêm 3 đặc trưng parser không tự làm giảm FP của SVA.
2. **Ở phép so hai cấu hình được chọn (`LR_base` `C=1.0, tau=0.45` vs `LR_parser` `C=0.1, tau=0.35`):** Micro F0.5 tăng từ 0.220162 lên 0.228426, nhưng TP typed giảm 38 xuống 27 và FP giảm 112 xuống 55. Riêng SVA, TP và recall giữ nguyên (12/74); FP giảm 41 xuống 16, F0.5 tăng 0.209790 lên 0.322581 (nhờ kết hợp điều chuẩn mạnh hơn ở `C=0.1, tau=0.35` với đặc trưng parser). VFORM và NNUM giảm F0.5. Không nói parser giúp tìm thêm SVA; mức tăng ở cấu hình được chọn chủ yếu đến từ giảm báo nhầm. Kết quả kiểm tra khả năng tổng quát hóa trên tập `test` (chấm ngày 03/11/2026) được trình bày tại mục Cấu hình khóa và test bên dưới.

Thay đổi từng token so LR nền: {json.dumps(change_counts, ensure_ascii=False)}. Xem parser_changed_predictions.csv để đọc cả ca tốt lên và xấu đi.

### Bốn ca instructor yêu cầu

{md_table(cases, ['report_case_name', 'record_id', 'token', 'subject_text', 'subject_tag', 'subject_number', 'reference_C3_tau065_prediction', 'base_prediction', 'parser_prediction'])}

{case_text}

Các nhận xét cú pháp trên được tách thành quan sát trực tiếp trên đầu ra parser và giả thuyết cơ chế trong ngữ cảnh, không phải nhãn chuyên gia mới. Đặc trưng đóng góp được tính bằng hệ số lớp lỗi trừ hệ số O; file chi tiết giữ intercept và tổng margin đầy đủ, không chỉ vài đặc trưng lớn nhất.

## kNN

kNN chọn k={selected['kNN']['parameters']['k']}, tau={selected['kNN']['parameters']['tau']}; 42.493 mẫu (3.863 lỗi + 38.630 O), SVD 200 chiều, cosine, seed=0. Với k=10, tau=0.75 và 0.80 cùng yêu cầu ít nhất 8/10 láng giềng là lỗi; khác ngưỡng ghi với report nhưng cùng quyết định. Ties trong grid ưu tiên tau cao hơn. Không suy nguyên nhân kNN thấp chỉ từ điểm tổng.

## Kết quả rà soát 63 FP của Loan và Yến

- `baseline_ref/fp_reference.csv`: đủ 63 FP untyped, giữ câu/token/ID/probability và annotation tham chiếu.
- `baseline_ref/raw_TV1_Loan.csv` và `raw_TV2_Yen.csv`: bản gốc phiếu rà soát 63 FP của Vũ Thị Loan và Mai Hải Yến (ngày 2026-10-27).
- `baseline_ref/review_Loan.csv`, `review_Yen.csv`, `review_consensus.csv`, `review_status.json`: đã chuẩn hóa và tổng hợp bằng `summarize_reviews.py` (63/63 ca hoàn tất; `review_forms_filled=true`, `independent_reviews_complete=false`, `disagreements_before_discussion=null`).
- Thống kê 63 ca FP (`LR_reference_C3_tau065`, 30 TP + 63 FP = 93 cảnh báo):
  - **A (báo nhầm thật):** {review_status.get('A', 0)} ca.
  - **B (lỗi thật nhưng gold chưa ghi):** {review_status.get('B', 0)} ca — gồm **{review_status.get('B_in_scope_3_types', 0)} ca thuộc 3 nhãn mục tiêu** (`SVA`: 5, `VFORM`: 3, `NNUM`: 2), **3 ca `Khác`** ngoài phạm vi (`FP021`, `FP028`, `FP048`) và **1 ca `Chưa xác định`** (`FP049`).
  - **C (chưa chắc / thiếu ngữ cảnh):** {review_status.get('C', 0)} ca.
  - **Precision hiệu chỉnh (chỉ tính 10 ca B thuộc 3 nhãn):** `(30 + 10) / 93` = **{review_status.get('estimated_precision_in_scope_3_types', 0):.6f}** (cận trên giả định gộp C: `55 / 93` = {review_status.get('assumption_upper_bound_in_scope_3_types', 0):.6f}).
  - **Precision hiệu chỉnh (tính cả 14 ca B):** `(30 + 14) / 93` = **{review_status.get('estimated_precision', 0):.6f}** (cận trên giả định gộp C: `59 / 93` = {review_status.get('assumption_upper_bound', 0):.6f}).
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
3. Parser cung cấp ba đặc trưng với token alignment được kiểm tra (`SUBJECT_DEPS = {{'nsubj', 'nsubjpass', 'csubj', 'csubjpass'}}`).
4. Ở phép so cùng `C=1.0, tau=0.45`, **TP SVA giảm 12 -> 11; FP giữ 41**; ở cấu hình được chọn `C=0.1, tau=0.35`, SVA precision tăng nhờ giảm FP (`41 -> 16`) và giữ `TP = 12`, có hồi quy ở `FN04`.
5. Nhóm khóa tham số bằng `dev` và đã chấm `test` ngày 03/11/2026 tại `outputs/final_test_cc1e75b079e005f0/` (khai báo minh bạch lịch sử hai đợt test 02/11 và 03/11 của nhóm, không chọn lại tham số theo test).

## File nên mở trước

README.md để chạy; `TONG_HOP_KET_QUA_BAO_CAO_GROUP02.md` và `Group02_Long_Report_Pack/HUONG_DAN_VIET_BAO_CAO_LONG.md` để lấy bảng viết báo cáo; `outputs/dev_run_001/metrics_dev.csv` và `outputs/final_test_cc1e75b079e005f0/metrics_test.csv` để xem điểm; `parser_four_cases.csv` và `outputs/fixed_point_check/parser_limitation_cases.csv` để đọc ví dụ; `baseline_ref/` để xem kết quả review 63 FP. Notebook EXPECT_Long_Dev.ipynb chứa các cell đã chạy để kiểm tra và trình bày kết quả lưu sẵn (kèm trace mẫu `dev:001408` token 3 `realize`).
'''
    (ROOT / 'LONG_HANDOFF.md').write_text(handoff, encoding='utf-8')

    # Pin all distributions actually installed into this project-local dependency folder.
    pins = []
    for distribution in importlib.metadata.distributions(path=[str(ROOT / '.deps')]):
        name = distribution.metadata['Name']
        if name.lower().replace('_', '-') == 'en-core-web-sm':
            pins.append('en-core-web-sm @ https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl#sha256=1932429db727d4bff3deed6b34cfc05df17794f4a52eeb26cf8928f7c1a0fb85')
        else:
            pins.append(f'{name}=={distribution.version}')
    (ROOT / 'requirements-lock.txt').write_text('\n'.join(sorted(set(pins), key=str.lower)) + '\n', encoding='utf-8')

    notebook = nbformat.v4.new_notebook()
    notebook.metadata['kernelspec'] = {'display_name': 'Python 3', 'language': 'python', 'name': 'python3'}
    notebook.metadata['language_info'] = {'name': 'python', 'version': sys.version.split()[0]}
    notebook.metadata['execution_note'] = 'Inspection cells executed sequentially by CPython; training was executed separately by run_dev.py. No Jupyter server or test re-evaluation was run.'
    notebook.cells = [
        nbformat.v4.new_markdown_cell('# EXPECT: phần thực hiện của Long\n\nNotebook kiểm tra và hiển thị đầu ra thật đã lưu (không tự chạy huấn luyện hay đánh giá lại test khi Run All). Đặt RUN_TRAINING=True nếu muốn gọi lại pipeline dev.'),
        nbformat.v4.new_code_cell("from pathlib import Path\nimport os, sys, json\nROOT = Path.cwd()\nif not (ROOT / 'run_dev.py').exists():\n    raise RuntimeError('Mở notebook từ thư mục Explainable_GEC_Long')\nsys.path.insert(0, str(ROOT))\nimport bootstrap\nfrom gec.safety import install_development_guard\ninstall_development_guard()\nimport pandas as pd\nOUT = ROOT / 'outputs/dev_run_001'\nprint('Python:', sys.version.split()[0])\nprint('Chế độ dev: test.json/test.pkl bị chặn trong phiên làm việc này')"),
        nbformat.v4.new_code_cell("RUN_TRAINING = False\nif RUN_TRAINING:\n    import subprocess\n    subprocess.run([sys.executable, '-u', 'run_dev.py', '--stage', 'all'], cwd=ROOT, check=True)\nmanifest = json.loads((OUT / 'run_manifest.json').read_text(encoding='utf-8'))\nassert manifest['status'] == 'complete'\nassert manifest['splits_read'] == ['train', 'dev']\nassert not manifest['test_scored']\nprint('CLI run:', manifest['status'], manifest['completed_at'])"),
        nbformat.v4.new_code_cell("from gec.data import load_development\ntrain, dev, summaries = load_development(ROOT / 'data/json')\nprint(pd.DataFrame([{k:v for k,v in s.items() if k in ['split','records','tokens','SVA','VFORM','NNUM']} for s in summaries]).to_string(index=False))"),
        nbformat.v4.new_code_cell("metrics = pd.read_csv(OUT / 'metrics_dev.csv')\nprint(metrics[metrics['label'].eq('MICRO')][['system','scoring','TP','FP','FN','P','R','F0.5']].to_string(index=False))"),
        nbformat.v4.new_code_cell("grid = pd.read_csv(OUT / 'tuning_grid.csv')\nassert len(grid) == 228\nprint(pd.read_csv(OUT / 'lr_best_per_C.csv')[['system','C','tau','F0.5','selected_C']].to_string(index=False))\nprint('Grid rows:', len(grid))"),
        nbformat.v4.new_code_cell("classes = metrics[metrics['system'].isin(['LR_base','LR_parser']) & metrics['label'].ne('MICRO')]\nprint(classes[['system','label','TP','FP','FN','P','R','F0.5']].to_string(index=False))\nfixed = pd.read_csv(ROOT / 'outputs/fixed_point_check/metrics_parser_fixed_point.csv')\nprint('\\nFixed-point parser check (C=1.0, tau=0.45 vs tau=0.60):')\nprint(fixed[['system','scoring','label','TP','FP','FN','P','R','F0.5']].to_string(index=False))\ncases = pd.read_csv(OUT / 'parser_four_cases.csv')\nprint('\\nFour diagnostic cases:')\nprint(cases[['report_case_name','record_id','token','subject_text','reference_C3_tau065_prediction','base_prediction','parser_prediction']].to_string(index=False))"),
        nbformat.v4.new_code_cell("# Trace 1 ID từ source -> đặc trưng -> xác suất/ngưỡng -> dự đoán -> gold (dev:001408, token 3 'realize')\nrow_fp02 = cases[cases['record_id'].eq('dev:001408')].iloc[0]\nprint('Record:', row_fp02['record_id'], '| Token index:', row_fp02['token_index'], '| Token:', row_fp02['token'], '| Gold:', row_fp02['gold'])\nprint('Source:', row_fp02['source'])\nprint('Parser subject:', row_fp02['subject_text'], '| tag:', row_fp02['subject_tag'], '| number:', row_fp02['subject_number'], '| distance:', row_fp02['subject_distance'])\nprint('LR_base (C=1.0, tau=0.45): p_error =', row_fp02['base_p_error'], '-> prediction =', row_fp02['base_prediction'])\nprint('LR_parser (C=0.1, tau=0.35): p_error =', row_fp02['parser_p_error'], '-> prediction =', row_fp02['parser_prediction'])\ninterv_dirs = sorted((ROOT / 'outputs').glob('fp02_intervention_dev_*'))\nif interv_dirs:\n    interv = pd.read_csv(interv_dirs[-1] / 'fp02_feature_intervention_dev.csv')\n    print('\\nFP02 intervention at C=1.0, tau=0.45:')\n    print(interv[['scenario','subject_tag','subject_number','subject_distance','p_error','p_SVA','prediction']].to_string(index=False))"),
        nbformat.v4.new_code_cell("for person in ['Loan','Yen']:\n    review = pd.read_csv(OUT / 'baseline_ref' / f'review_{person}.csv', keep_default_na=False)\n    done = review['review_label_A_B_C'].str.strip().ne('').sum()\n    print(person, 'review_fields_filled:', done, '/', len(review))\nstatus = json.loads((OUT / 'baseline_ref' / 'review_status.json').read_text(encoding='utf-8'))\nprint('review_forms_filled:', status['review_forms_filled'], '| independent_reviews_complete:', status['independent_reviews_complete'], '| disagreements_before_discussion:', status['disagreements_before_discussion'])\nprint(f\"A={status['A']}, B={status['B']} (in-scope 3 types={status['B_in_scope_3_types']}, out-of-scope={status['B_out_of_scope']}), C={status['C']}\")\nprint(f\"Adjusted precision (in-scope 3 types): {status['estimated_precision_in_scope_3_types']:.6f} | (all B): {status['estimated_precision']:.6f}\")"),
        nbformat.v4.new_code_cell("verification = json.loads((OUT / 'verification.json').read_text(encoding='utf-8'))\nassert verification['status'] == 'passed'\nfrom gec.io_utils import sha256\nlocked = json.loads((OUT / 'config_locked.json').read_text(encoding='utf-8'))\nfor entry in locked['bundles'].values():\n    assert sha256(ROOT / entry['path']) == entry['sha256']\nprint('Independent verification:', verification['status'])\nprint('Model checksums: matched')\nprint('Frozen dev lock state:', locked['status'])\ntest_dirs = sorted((ROOT / 'outputs').glob('final_test_*'))\nif test_dirs:\n    test_state = json.loads((test_dirs[-1] / 'evaluation_state.json').read_text(encoding='utf-8'))\n    test_metrics = pd.read_csv(test_dirs[-1] / 'metrics_test.csv')\n    print('\\nSaved final test evaluation:', test_state['status'], '| completed_at:', test_state.get('completed_at'))\n    print(test_metrics[test_metrics['label'].eq('MICRO')][['system','scoring','gold','TP','FP','FN','P','R','F0.5']].to_string(index=False))"),
        nbformat.v4.new_markdown_cell('Kết luận: Trên dev, ở cùng C=1.0/tau=0.45, thêm 3 đặc trưng parser chưa giảm FP SVA (giữ 41 FP); ở cấu hình được chọn C=0.1/tau=0.35, SVA F0.5 tăng nhờ giảm FP (41 xuống 16), VFORM/NNUM giảm. Trên test (272 lỗi gold, chấm ngày 03/11/2026), LR_base (0.194867) và LR_parser (0.193966) đều vượt POS (0.122627) và kNN (0.113636); LR_parser có precision cao hơn và dẫn đầu ở SVA/VFORM, còn LR_base có recall cao hơn ở NNUM.')
    ]
    previous_dir = Path.cwd()
    os.chdir(ROOT)
    namespace = {'__name__': '__notebook__'}
    execution = []
    try:
        count = 0
        for cell in notebook.cells:
            if cell.cell_type != 'code':
                continue
            count += 1
            stdout = io.StringIO()
            began = timestamp()
            with contextlib.redirect_stdout(stdout):
                exec(compile(cell.source, f'notebook_cell_{count}', 'exec'), namespace)
            cell.execution_count = count
            cell.outputs = [nbformat.v4.new_output('stream', name='stdout', text=stdout.getvalue())]
            execution.append({'cell': count, 'started_at': began, 'completed_at': timestamp(), 'status': 'passed'})
    finally:
        os.chdir(previous_dir)
    nbformat.validate(notebook)
    nbformat.write(notebook, ROOT / 'EXPECT_Long_Dev.ipynb')
    write_json(out / 'notebook_execution.json', {'engine': 'sequential CPython exec; not a Jupyter server',
                                               'training_in_notebook': False, 'cells': execution,
                                               'test_scored': False})
    print('Created LONG_HANDOFF.md, review guide, change analysis, requirements lock and executed inspection notebook.')


if __name__ == '__main__':
    main()
