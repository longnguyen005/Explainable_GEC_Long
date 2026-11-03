"""Standardize and summarize two human reviews; preserve existing consensus decisions."""
import bootstrap
import argparse
import csv
import sys
from collections import Counter
from pathlib import Path
from gec.exports import REVIEW_COLUMNS
from gec.io_utils import read_json, write_csv, write_json

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

IN_SCOPE_TYPES = ('SVA', 'VFORM', 'NNUM')
RAW_FILES = {'Loan': 'raw_TV1_Loan.csv', 'Yen': 'raw_TV2_Yen.csv'}


def read_rows(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def parse_raw_sheet(raw_path, reference_rows):
    with Path(raw_path).open(encoding='utf-8-sig', newline='') as stream:
        lines = list(csv.reader(stream))
    reviewer, reviewed_at = '', ''
    header_index = None
    for idx, row in enumerate(lines):
        if not any(cell.strip() for cell in row):
            continue
        first = row[0].strip()
        if first == 'Người đọc':
            reviewer = row[1].strip() if len(row) > 1 else ''
            reviewed_at = row[3].strip() if len(row) > 3 else ''
        elif first == 'Mã ca':
            header_index = idx
            break
    if header_index is None:
        raise ValueError(f'Cannot find header row "Mã ca" in {raw_path}')

    ref_by_id = {r['FP_ID']: r for r in reference_rows}
    parsed = {}
    for row in lines[header_index + 1:]:
        if not row or not row[0].strip().startswith('FP'):
            continue
        fp_id = row[0].strip()
        if fp_id not in ref_by_id:
            raise ValueError(f'Unknown FP_ID {fp_id} in {raw_path}')
        ref = ref_by_id[fp_id]
        rec_id, tok_idx, tok = row[1].strip(), row[2].strip(), row[3].strip()
        if (rec_id, int(tok_idx), tok) != (ref['record_id'], int(ref['token_index']), ref['token']):
            raise ValueError(f'Key mismatch at {fp_id} in {raw_path}')
        marked_source = row[4].strip()
        clean_source = marked_source.replace('[[', '').replace(']]', '')
        if clean_source != ref['source']:
            raise ValueError(f'Source mismatch at {fp_id} in {raw_path}')

        label = row[5].strip().upper()
        reason = row[6].strip()
        correction = row[7].strip() if len(row) > 7 else ''
        err_type = row[8].strip() if len(row) > 8 else ''
        note = row[9].strip() if len(row) > 9 else ''
        if note and note != '—' and note not in reason:
            reason = f'{reason} [Ghi chú/Nguồn: {note}]'

        base = {k: v for k, v in ref.items() if k != 'contributions_error_minus_O'}
        parsed[fp_id] = {
            **base,
            'review_label_A_B_C': label,
            'reason': reason,
            'suggested_error_type': err_type,
            'suggested_correction': correction,
            'reviewer': reviewer,
            'reviewed_at': reviewed_at,
        }
    if len(parsed) != len(reference_rows):
        raise ValueError(f'Expected {len(reference_rows)} cases in {raw_path}, found {len(parsed)}')
    return [parsed[r['FP_ID']] for r in reference_rows]


def standardize_if_raw_present(folder, reference_rows):
    for person, raw_name in RAW_FILES.items():
        raw_path = folder / raw_name
        target_path = folder / f'review_{person}.csv'
        if raw_path.exists():
            needs_sync = not target_path.exists()
            if not needs_sync:
                try:
                    existing = read_rows(target_path)
                    needs_sync = (
                        len(existing) != len(reference_rows)
                        or 'FP_ID' not in (existing[0] if existing else {})
                        or not all(r.get('review_label_A_B_C', '').strip() for r in existing)
                    )
                except Exception:
                    needs_sync = True
            if needs_sync:
                standardized = parse_raw_sheet(raw_path, reference_rows)
                write_csv(target_path, standardized, fieldnames=list(standardized[0]))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--reference-dir', type=Path, default=bootstrap.ROOT / 'outputs/dev_run_001/baseline_ref')
    parser.add_argument('--force-standardize', action='store_true',
                        help='Re-generate review_Loan.csv and review_Yen.csv from raw_TV1/TV2 if present.')
    args = parser.parse_args()
    folder = args.reference_dir
    reference = read_rows(folder / 'fp_reference.csv')
    if args.force_standardize:
        for person, raw_name in RAW_FILES.items():
            raw_path = folder / raw_name
            if raw_path.exists():
                standardized = parse_raw_sheet(raw_path, reference)
                write_csv(folder / f'review_{person}.csv', standardized, fieldnames=list(standardized[0]))
    else:
        standardize_if_raw_present(folder, reference)

    ids = [r['FP_ID'] for r in reference]
    reviews = []
    for person in ('Loan', 'Yen'):
        rows = read_rows(folder / f'review_{person}.csv')
        if len(rows) != len(ids) or len({r['FP_ID'] for r in rows}) != len(ids) or {r['FP_ID'] for r in rows} != set(ids):
            raise ValueError(f'{person}: missing or duplicate FP IDs.')
        mapping = {r['FP_ID']: r for r in rows}
        for row in rows:
            label = row['review_label_A_B_C'].strip().upper()
            if label not in ('', 'A', 'B', 'C'):
                raise ValueError(f"Invalid human label: {row['FP_ID']}")
            if label and not row['reason'].strip():
                raise ValueError('Each completed human decision needs a reason.')
        reviews.append(mapping)

    counts = [sum(bool(r['review_label_A_B_C'].strip()) for r in review.values()) for review in reviews]
    forms_filled = counts == [len(ids), len(ids)]
    status = {'expected_cases': len(ids), 'Loan_completed': counts[0], 'Yen_completed': counts[1],
              'review_forms_filled': forms_filled,
              'independent_reviews_complete': False,
              'disagreements_before_discussion': None,
              'review_method': 'shared_draft_with_TV1_selected_as_common_review',
              'human_verification_status': 'Not inferred from completed fields or matching labels.'}
    write_json(folder / 'review_status.json', status)
    if not forms_filled:
        print(status)
        print('Human reviews are incomplete; no consensus or adjusted precision is calculated.')
        return

    existing_consensus = {}
    consensus_path = folder / 'review_consensus.csv'
    if consensus_path.exists():
        for row in read_rows(consensus_path):
            if row.get('FP_ID'):
                existing_consensus[row['FP_ID']] = row

    comparison_rows, consensus_rows = [], []
    for case_id in ids:
        left, right = reviews[0][case_id], reviews[1][case_id]
        a, b = left['review_label_A_B_C'].strip().upper(), right['review_label_A_B_C'].strip().upper()
        agreed = (a == b)
        prev = existing_consensus.get(case_id, {})
        prev_label = prev.get('consensus_A_B_C', '').strip().upper()
        prev_reason = prev.get('consensus_reason', '').strip()
        consensus_label = prev_label if prev_label in ('A', 'B', 'C') else (a if agreed else '')
        consensus_reason = prev_reason if prev_reason else (left['reason'] if agreed else '')
        err_type = prev.get('suggested_error_type', '').strip() or left.get('suggested_error_type', '').strip()
        correction = prev.get('suggested_correction', '').strip() or left.get('suggested_correction', '').strip()

        base_row = {
            'FP_ID': case_id,
            'record_id': left['record_id'],
            'token_index': left['token_index'],
            'token': left['token'],
            'prediction': left['prediction'],
            'Loan_label': a,
            'Yen_label': b,
            'disagreed_before_discussion': None,
            'labels_differ_in_available_sheets': not agreed,
            'Loan_reason': left['reason'],
            'Yen_reason': right['reason'],
            'suggested_error_type': err_type,
            'suggested_correction': correction,
            'consensus_A_B_C': consensus_label,
            'consensus_reason': consensus_reason,
        }
        comparison_rows.append({k: base_row[k] for k in (
            'FP_ID', 'Loan_label', 'Yen_label', 'disagreed_before_discussion',
            'labels_differ_in_available_sheets',
            'Loan_reason', 'Yen_reason', 'consensus_A_B_C', 'consensus_reason'
        )})
        consensus_rows.append(base_row)

    write_csv(folder / 'independent_comparison.csv', comparison_rows)
    write_csv(consensus_path, consensus_rows)
    status['available_sheet_label_differences'] = sum(r['labels_differ_in_available_sheets'] for r in comparison_rows)

    consensus = read_rows(consensus_path)
    if len(consensus) != len(ids) or {r['FP_ID'] for r in consensus} != set(ids):
        raise ValueError('Consensus IDs mismatch.')
    complete = all(r['consensus_A_B_C'].strip().upper() in ('A', 'B', 'C') and r['consensus_reason'].strip() for r in consensus)
    status['consensus_complete'] = complete
    if complete:
        numbers = {label: sum(r['consensus_A_B_C'].strip().upper() == label for r in consensus) for label in ('A', 'B', 'C')}
        b_rows = [r for r in consensus if r['consensus_A_B_C'].strip().upper() == 'B']
        b_type_counts = Counter((r.get('suggested_error_type') or 'Unspecified').strip() for r in b_rows)
        b_in_scope = sum(cnt for et, cnt in b_type_counts.items() if et in IN_SCOPE_TYPES)
        b_out_of_scope = numbers['B'] - b_in_scope

        metrics = read_rows(folder / 'metrics_dev.csv')
        metric = next(r for r in metrics if r['scoring'] == 'untyped' and r['label'] == 'MICRO')
        tp, fp = int(metric['TP']), int(metric['FP'])
        total_alerts = tp + fp
        status.update(
            numbers,
            B_in_scope_3_types=b_in_scope,
            B_out_of_scope=b_out_of_scope,
            B_by_error_type=dict(b_type_counts),
            reference_TP=tp,
            reference_FP=fp,
            estimated_precision_in_scope_3_types=(tp + b_in_scope) / total_alerts if total_alerts else 0,
            estimated_precision=(tp + numbers['B']) / total_alerts if total_alerts else 0,
            assumption_upper_bound_in_scope_3_types=(tp + b_in_scope + numbers['C']) / total_alerts if total_alerts else 0,
            assumption_upper_bound=(tp + numbers['B'] + numbers['C']) / total_alerts if total_alerts else 0,
            reviewers=['VŨ THỊ LOAN', 'MAI HẢI YẾN'],
            source_declared_review_dates=sorted({r.get('reviewed_at', '') for review in reviews for r in review.values() if r.get('reviewed_at')}),
            methodology_note=(
                'TV1 is selected as the common review. The available sheets derive from an '
                'AI-assisted shared draft. Matching labels do not establish independent initial '
                'annotation, pre-discussion disagreement, or expert correctness.'
            ),
            limitation=(
                'Internal review labels selected from an AI-assisted draft, not expert gold; direct verification is not established by this script. In-scope precision counts '
                'only B in {SVA, VFORM, NNUM} (10 cases); all-B precision includes 3 out-of-scope (Khác) '
                'and 1 undetermined-tense case. Upper bound assumes every C is a true target error; '
                'not a confidence interval.'
            ),
        )
        manifest_path = folder / 'review_manifest.json'
        if manifest_path.exists():
            manifest_data = read_json(manifest_path)
            manifest_data['review_fields_filled'] = True
            manifest_data['independent_reviews_complete'] = False
            manifest_data['human_labels_completed'] = None
            manifest_data['reviewers'] = ['VŨ THỊ LOAN', 'MAI HẢI YẾN']
            manifest_data.pop('reviewed_at', None)
            manifest_data['source_declared_review_dates'] = status['source_declared_review_dates']
            write_json(manifest_path, manifest_data)
    write_json(folder / 'review_status.json', status)
    print(status)


if __name__ == '__main__':
    main()
