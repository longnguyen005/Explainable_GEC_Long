"""Check two human reviews; never fabricate labels or overwrite consensus decisions."""
import bootstrap
import argparse
import csv
from pathlib import Path
from gec.io_utils import read_json, write_csv, write_json


def read_rows(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--reference-dir', type=Path, default=bootstrap.ROOT / 'outputs/dev_run_001/baseline_ref')
    args = parser.parse_args()
    folder = args.reference_dir
    reference = read_rows(folder / 'fp_reference.csv')
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
    status = {'expected_cases': len(ids), 'Loan_completed': counts[0], 'Yen_completed': counts[1],
              'independent_reviews_complete': counts == [len(ids), len(ids)]}
    write_json(folder / 'review_status.json', status)
    print(status)
    if not status['independent_reviews_complete']:
        print('Human reviews are incomplete; no consensus or adjusted precision is calculated.')
        return
    rows = []
    for case_id in ids:
        left, right = reviews[0][case_id], reviews[1][case_id]
        a, b = left['review_label_A_B_C'].strip().upper(), right['review_label_A_B_C'].strip().upper()
        rows.append({'FP_ID': case_id, 'Loan_label': a, 'Yen_label': b,
                     'disagreed_before_discussion': a != b,
                     'Loan_reason': left['reason'], 'Yen_reason': right['reason'],
                     'consensus_A_B_C': '', 'consensus_reason': ''})
    write_csv(folder / 'independent_comparison.csv', rows)
    consensus_path = folder / 'review_consensus.csv'
    if not consensus_path.exists():
        write_csv(consensus_path, rows)
    status['disagreements_before_discussion'] = sum(r['disagreed_before_discussion'] for r in rows)
    consensus = read_rows(consensus_path)
    if len(consensus) != len(ids) or {r['FP_ID'] for r in consensus} != set(ids):
        raise ValueError('Consensus IDs mismatch.')
    complete = all(r['consensus_A_B_C'].strip().upper() in ('A', 'B', 'C') and r['consensus_reason'].strip() for r in consensus)
    status['consensus_complete'] = complete
    if complete:
        numbers = {label: sum(r['consensus_A_B_C'].strip().upper() == label for r in consensus) for label in ('A', 'B', 'C')}
        metrics = read_rows(folder / 'metrics_dev.csv')
        metric = next(r for r in metrics if r['scoring'] == 'untyped' and r['label'] == 'MICRO')
        tp, fp = int(metric['TP']), int(metric['FP'])
        status.update(numbers, reference_TP=tp, reference_FP=fp,
                      estimated_precision=(tp + numbers['B']) / (tp + fp) if tp + fp else 0,
                      assumption_upper_bound=(tp + numbers['B'] + numbers['C']) / (tp + fp) if tp + fp else 0,
                      limitation='Internal human review, not expert gold. Upper bound assumes every C is a true target error; not a confidence interval.')
    write_json(folder / 'review_status.json', status)
    print(status)


if __name__ == '__main__':
    main()

