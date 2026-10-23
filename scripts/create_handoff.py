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
    instructions = f'''# Phiếu review độc lập cho Loan và Yến

Danh sách này thuộc LR tham chiếu C=3, tau=0.65, dữ liệu đã sửa alignment. Có {tp} TP và {fp} FP untyped, tổng {tp+fp} cảnh báo. Không dùng danh sách này để đánh giá LR_base có cấu hình khác hoặc LR_parser.

1. Loan mở review_Loan.csv; Yến mở review_Yen.csv. Cả hai đọc cùng toàn bộ {fp} ca.
2. Điền review_label_A_B_C bằng A/B/C; ghi reason, suggested_error_type, suggested_correction, reviewer, reviewed_at.
3. A: token phù hợp ngữ pháp, mô hình báo nhầm. B: có lỗi thuộc SVA/VFORM/NNUM tại vị trí dự đoán mà annotation chưa phản ánh. C: chưa chắc hoặc thiếu ngữ cảnh. B cần nêu cách sửa và căn cứ; một lỗi ở vị trí khác không đủ để xác nhận dự đoán.
4. Đọc độc lập, không xem nhãn của nhau. Dùng source đầy đủ; target_edit_reference chỉ là phép sửa được annotation, không khẳng định mọi vị trí còn lại đều đúng.
5. Giữ nguyên bản nhãn độc lập trước thảo luận. Chạy summarize_reviews.py để lập bảng bất đồng; chương trình không tự điền đồng thuận.
6. Sau thảo luận, điền review_consensus.csv và chạy lại công cụ để tổng hợp. Giữ C nếu chưa chắc.

Precision vị trí rà soát = ({tp}+B)/{tp+fp}. Cận giả định = [({tp}+B)/{tp+fp}, ({tp}+B+C)/{tp+fp}], không phải khoảng tin cậy. Đây là rà soát nội bộ, không phải nhãn chuyên gia; không thay thế điểm benchmark và không tạo ra recall/F0.5 đã hiệu chỉnh.

Hai phiếu hiện để trống có chủ ý. Long/AI không điền thay hai người đánh giá độc lập.
'''
    (out / 'baseline_ref/REVIEW_GUIDE_VI.md').write_text(instructions, encoding='utf-8')

    case_text = '''- FP02 `realize`: parser lấy đúng `people`, nhưng cả LR nền lẫn LR parser vẫn dự đoán SVA theo ngưỡng đã chọn. Xác suất lỗi giảm; chưa sửa được FP này.
- FP03 `is`: parser lấy `learning` thay vì danh từ `languages`; Number của chủ ngữ không có. Cảnh báo SVA vẫn còn.
- FN01 `is`: parser nhận `reasons` bên phải, nhưng xác suất lỗi vẫn thấp hơn ngưỡng; FN vẫn còn.
- FN04 `is`: parser không tìm thấy chủ ngữ trong cấu trúc này. LR nền C=1 tìm đúng SVA; LR parser trả O, tạo một hồi quy. Tên FN04 là tên trong report của LR tham chiếu C=3, không phải phân loại hiện tại của LR nền.
'''
    handoff = f'''# Bàn giao phần thực hiện của Long

Ngày tạo: {timestamp()}

## Trạng thái

Đã sửa pipeline dữ liệu, chạy All O/POS/LR/kNN, tái tạo LR tham chiếu Week 9, hoàn thành thí nghiệm dependency, lưu model/config và kiểm tra lại dự đoán sau khi nạp model. Mã gốc không đổi. Chỉ train/dev được đọc; chưa mở/chấm test. Hai người vẫn cần thực hiện review độc lập và nhóm cần xem xét cấu hình trước đánh giá cuối.

## Dữ liệu đã kiểm tra

{md_table(counts, ['split', 'original_records', 'records', 'tokens', 'SVA', 'VFORM', 'NNUM', 'excluded_records'])}

Alignment dùng target+[MOD]+source, offset len(target)+1. Train loại 577 bản ghi, gồm 8 bản ghi bị giữ nhầm bởi code cũ. Dev loại 46. Một source trùng train/dev được giữ trong bảng chính theo split công khai; bảng độ nhạy bỏ source dev trùng nhưng không tuning lại.

## Kết quả đầy đủ trên dev

{md_table(micro, ['system', 'scoring', 'TP', 'FP', 'FN', 'P', 'R', 'F0.5'])}

Phân biệt LR tham chiếu C=3/tau=0.65 với LR nền được chọn bằng quy tắc gần hòa. LR tham chiếu khớp report Week 9: typed 28/65/235 và untyped 30/63/233. Điểm 0.233 trong CSV gốc thuộc pipeline cũ; không dùng làm điểm mới. Lần chạy mới dùng NLTK 3.9.2, khác tên phiên bản NLTK ghi trong report, nhưng tái tạo đúng đặc trưng và số đếm LR tham chiếu.

## Thí nghiệm parser

LR nền chọn C={selected['LR_base']['parameters']['C']}, tau={selected['LR_base']['parameters']['tau']}. LR parser chọn C={selected['LR_parser']['parameters']['C']}, tau={selected['LR_parser']['parameters']['tau']}. Hai phiên bản dùng cùng grid và quy tắc gần hòa được ghi trước fit. Vì cả C/ngưỡng có thể thay đổi, đây là so sánh hai pipeline được chọn bằng cùng quy trình, không phải tác động thuần của thêm ba đặc trưng tại một C/ngưỡng cố định.

Vocab nền 126.797 đặc trưng; parser 126.847. Parser giữ khớp toàn bộ 484.953 token train/dev, chạy trên source, không dùng correction/evidence/parsing order của gold.

{md_table(classes, ['system', 'label', 'TP', 'FP', 'FN', 'P', 'R', 'F0.5'])}

Kết luận: micro F0.5 tăng từ 0.220162 lên 0.228426, nhưng TP typed giảm 38 xuống 27 và FP giảm 112 xuống 55. Riêng SVA, TP và recall giữ nguyên (12/74); FP giảm 41 xuống 16, F0.5 tăng 0.209790 lên 0.322581. VFORM và NNUM giảm F0.5. Không nói parser giúp tìm thêm SVA; mức tăng hiện tại chủ yếu là giảm báo nhầm. Đây là điểm dev sau lựa chọn, một seed, chưa có bằng chứng generalization trên test.

Thay đổi từng token so LR nền: {json.dumps(change_counts, ensure_ascii=False)}. Xem parser_changed_predictions.csv để đọc cả ca tốt lên và xấu đi.

### Bốn ca instructor yêu cầu

{md_table(cases, ['report_case_name', 'record_id', 'token', 'subject_text', 'subject_tag', 'subject_number', 'reference_C3_tau065_prediction', 'base_prediction', 'parser_prediction'])}

{case_text}

Các nhận xét cú pháp trên là phân tích đầu ra parser trong ngữ cảnh, không phải nhãn chuyên gia mới. Đặc trưng đóng góp được tính bằng hệ số lớp lỗi trừ hệ số O; file chi tiết giữ intercept và tổng margin đầy đủ, không chỉ vài đặc trưng lớn nhất.

## kNN

kNN chọn k={selected['kNN']['parameters']['k']}, tau={selected['kNN']['parameters']['tau']}; 42.493 mẫu (3.863 lỗi + 38.630 O), SVD 200 chiều, cosine, seed=0. Với k=10, tau=0.75 và 0.80 cùng yêu cầu ít nhất 8/10 láng giềng là lỗi; khác ngưỡng ghi với report nhưng cùng quyết định. Ties trong grid ưu tiên tau cao hơn. Không suy nguyên nhân kNN thấp chỉ từ điểm tổng.

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
    notebook.metadata['execution_note'] = 'Inspection cells executed sequentially by CPython; training was executed separately by run_dev.py. No Jupyter server or test evaluation was run.'
    notebook.cells = [
        nbformat.v4.new_markdown_cell('# EXPECT: phần thực hiện của Long\n\nChỉ train/dev. Notebook kiểm tra và hiển thị đầu ra thật đã lưu. Đặt RUN_TRAINING=True để gọi lại pipeline dev; model/cache hợp lệ được dùng lại. Không có cell đánh giá test.'),
        nbformat.v4.new_code_cell("from pathlib import Path\nimport os, sys, json\nROOT = Path.cwd()\nif not (ROOT / 'run_dev.py').exists():\n    raise RuntimeError('Mở notebook từ thư mục Explainable_GEC_Long')\nsys.path.insert(0, str(ROOT))\nimport bootstrap\nfrom gec.safety import install_development_guard\ninstall_development_guard()\nimport pandas as pd\nOUT = ROOT / 'outputs/dev_run_001'\nprint('Python:', sys.version.split()[0])\nprint('Chế độ dev: test.json/test.pkl bị chặn')"),
        nbformat.v4.new_code_cell("RUN_TRAINING = False\nif RUN_TRAINING:\n    import subprocess\n    subprocess.run([sys.executable, '-u', 'run_dev.py', '--stage', 'all'], cwd=ROOT, check=True)\nmanifest = json.loads((OUT / 'run_manifest.json').read_text(encoding='utf-8'))\nassert manifest['status'] == 'complete'\nassert manifest['splits_read'] == ['train', 'dev']\nassert not manifest['test_scored']\nprint('CLI run:', manifest['status'], manifest['completed_at'])"),
        nbformat.v4.new_code_cell("from gec.data import load_development\ntrain, dev, summaries = load_development(ROOT / 'data/json')\nprint(pd.DataFrame([{k:v for k,v in s.items() if k in ['split','records','tokens','SVA','VFORM','NNUM']} for s in summaries]).to_string(index=False))"),
        nbformat.v4.new_code_cell("metrics = pd.read_csv(OUT / 'metrics_dev.csv')\nprint(metrics[metrics['label'].eq('MICRO')][['system','scoring','TP','FP','FN','P','R','F0.5']].to_string(index=False))"),
        nbformat.v4.new_code_cell("grid = pd.read_csv(OUT / 'tuning_grid.csv')\nassert len(grid) == 228\nprint(pd.read_csv(OUT / 'lr_best_per_C.csv')[['system','C','tau','F0.5','selected_C']].to_string(index=False))\nprint('Grid rows:', len(grid))"),
        nbformat.v4.new_code_cell("classes = metrics[metrics['system'].isin(['LR_base','LR_parser']) & metrics['label'].ne('MICRO')]\nprint(classes[['system','label','TP','FP','FN','P','R','F0.5']].to_string(index=False))\ncases = pd.read_csv(OUT / 'parser_four_cases.csv')\nprint(cases[['report_case_name','token','subject_text','reference_C3_tau065_prediction','base_prediction','parser_prediction']].to_string(index=False))"),
        nbformat.v4.new_code_cell("for person in ['Loan','Yen']:\n    review = pd.read_csv(OUT / 'baseline_ref' / f'review_{person}.csv', keep_default_na=False)\n    done = review['review_label_A_B_C'].str.strip().ne('').sum()\n    print(person, 'completed:', done, '/', len(review))\nprint('Phiếu để người đọc độc lập điền; chưa có precision rà soát.')"),
        nbformat.v4.new_code_cell("verification = json.loads((OUT / 'verification.json').read_text(encoding='utf-8'))\nassert verification['status'] == 'passed'\nfrom gec.io_utils import sha256\nlocked = json.loads((OUT / 'config_locked.json').read_text(encoding='utf-8'))\nfor entry in locked['bundles'].values():\n    assert sha256(ROOT / entry['path']) == entry['sha256']\nprint('Independent verification:', verification['status'])\nprint('Model checksums: matched')\nprint('Frozen state:', locked['status'], '; team review pending:', locked['team_review_pending'])\nprint('Test scored:', verification['test_scored'])"),
        nbformat.v4.new_markdown_cell('Kết luận trên dev: SVA F0.5 tăng nhờ giảm FP, recall giữ nguyên. VFORM/NNUM giảm ở cấu hình parser được chọn. Chưa suy ra chất lượng trên test hoặc độ tin cậy phản hồi cho người học. Xem LONG_HANDOFF.md để đọc đầy đủ giới hạn và cách bàn giao.')
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
