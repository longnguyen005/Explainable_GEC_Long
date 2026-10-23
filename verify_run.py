"""Independent reconciliation of saved predictions, models and manifests; no fitting."""
import bootstrap
import csv
from pathlib import Path
import joblib
import numpy as np
import scipy.sparse as sp
from threadpoolctl import threadpool_limits
from gec.data import flatten_gold, load_development
from gec.io_utils import read_json, sha256, timestamp, write_json
from gec.models import decode_lr
from gec.safety import install_development_guard


def rows(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def main():
    install_development_guard()
    root = bootstrap.ROOT
    out = root / 'outputs/dev_run_001'
    manifest = read_json(out / 'run_manifest.json')
    if manifest['status'] != 'complete' or manifest['stage'] != 'all':
        raise RuntimeError('A full development run must complete first.')
    train, dev, summaries = load_development(root / 'data/json')
    golden = [(s.record_id, i, token, gold) for s in dev for i, (token, gold) in enumerate(zip(s.tokens, s.gold))]
    metric_rows = rows(out / 'metrics_dev.csv')
    files = {'All_O': out / 'predictions_All_O.csv', 'POS': out / 'predictions_POS.csv',
             'LR_base': out / 'predictions_LR_base.csv',
             'LR_reference_C3_tau065': out / 'baseline_ref/predictions_dev.csv',
             'LR_parser': out / 'predictions_LR_parser.csv', 'kNN': out / 'predictions_kNN.csv'}
    reconciliations, predicted = [], {}
    for system, path in files.items():
        data = rows(path)
        if len(data) != len(golden):
            raise AssertionError(f'{system}: prediction row count mismatch.')
        for expected, row in zip(golden, data):
            observed = (row['record_id'], int(row['token_index']), row['token'], row['gold'])
            if observed != expected:
                raise AssertionError(f'{system}: row order/gold mismatch.')
        predicted[system] = np.array([r['prediction'] for r in data])
        # Deliberately use plain Python counters, independent of the numpy scorer.
        for metric in [m for m in metric_rows if m['system'] == system]:
            if metric['label'] != 'MICRO':
                label = metric['label']
                tp = sum(r['gold'] == label and r['prediction'] == label for r in data)
                fp = sum(r['gold'] != label and r['prediction'] == label for r in data)
                fn = sum(r['gold'] == label and r['prediction'] != label for r in data)
            elif metric['scoring'] == 'typed':
                tp = sum(r['gold'] != 'O' and r['gold'] == r['prediction'] for r in data)
                fp = sum(r['prediction'] != 'O' and r['gold'] != r['prediction'] for r in data)
                fn = sum(r['gold'] != 'O' and r['gold'] != r['prediction'] for r in data)
            else:
                tp = sum(r['gold'] != 'O' and r['prediction'] != 'O' for r in data)
                fp = sum(r['gold'] == 'O' and r['prediction'] != 'O' for r in data)
                fn = sum(r['gold'] != 'O' and r['prediction'] == 'O' for r in data)
            if (tp, fp, fn) != tuple(int(metric[k]) for k in ('TP', 'FP', 'FN')):
                raise AssertionError('Metric counter mismatch.')
            f = 1.25 * tp / (1.25 * tp + fp + .25 * fn) if 1.25 * tp + fp + .25 * fn else 0
            if abs(f - float(metric['F0.5'])) > 1e-12:
                raise AssertionError('F0.5 mismatch.')
        reconciliations.append({'system': system, 'prediction_rows': len(data), 'independent_counts_match': True})
    locked = read_json(out / 'config_locked.json')
    roundtrips = []
    config = locked['config']
    for name in ('LR_base', 'LR_parser', 'LR_reference'):
        entry = locked['bundles'][name]
        if sha256(root / entry['path']) != entry['sha256']:
            raise AssertionError('Frozen model SHA mismatch.')
        bundle = joblib.load(root / entry['path'])
        x = sp.load_npz(root / 'cache' / f"matrix_{bundle['variant']}_{bundle['matrix_key'][:16]}_dev.npz")
        with threadpool_limits(limits=config['threads']):
            pred = decode_lr(bundle['clf'].predict_proba(x), bundle['clf'].classes_, bundle['tau'])
        expected_system = 'LR_reference_C3_tau065' if name == 'LR_reference' else name
        if not np.array_equal(pred, predicted[expected_system]):
            raise AssertionError('Reloaded model predictions differ from the exported CSV.')
        roundtrips.append({'model': name, 'full_dev_predictions_identical_after_reload': True})
    # Recompute a representative kNN block from the persisted SVD/neighbors.
    entry = locked['bundles']['kNN']
    if sha256(root / entry['path']) != entry['sha256']:
        raise AssertionError('kNN model SHA mismatch.')
    bundle = joblib.load(root / entry['path'])
    from sklearn.preprocessing import normalize
    from gec.models import decode_knn
    x = sp.load_npz(root / 'cache' / f"matrix_base_{bundle['matrix_key'][:16]}_dev.npz")
    indices = np.unique(np.linspace(0, x.shape[0] - 1, 128, dtype=int))
    with threadpool_limits(limits=config['threads']):
        z = normalize(bundle['svd'].transform(normalize(x[indices])))
        neighbors = bundle['neighbors'].kneighbors(z, return_distance=False)
    pred = decode_knn(bundle['yk'][neighbors], bundle['k'], bundle['tau'])
    if not np.array_equal(pred, predicted['kNN'][indices]):
        raise AssertionError('Reloaded kNN block differs from exported predictions.')
    for name, expected in locked['code_sha256'].items():
        if sha256(root / name) != expected:
            raise AssertionError(f'Frozen code changed: {name}')
    alignment = read_json(out / 'parser_alignment.json')
    if alignment['changed_tokens'] != 0 or not alignment['checked_every_token']:
        raise AssertionError('Parser token validation failed.')
    if len(rows(out / 'baseline_ref/fp_reference.csv')) != 63:
        raise AssertionError('Reference model no longer reproduces the reported 63 FP.')
    for person in ('Loan', 'Yen'):
        review = rows(out / f'baseline_ref/review_{person}.csv')
        if len(review) != 63 or len({r['FP_ID'] for r in review}) != 63:
            raise AssertionError('Human review template ID mismatch.')
    if len(rows(out / 'tuning_grid.csv')) != 228:
        raise AssertionError('Expected 76 settings per LR variant and kNN.')
    result = {'verified_at': timestamp(), 'status': 'passed', 'test_opened': False,
              'test_scored': False, 'training_performed_by_verifier': False,
              'metric_reconciliations': reconciliations, 'lr_roundtrips': roundtrips,
              'knn_reload_probe_rows': len(indices), 'knn_reload_predictions_identical': True,
              'parser_alignment_all_tokens': True, 'grid_rows': 228,
              'reference_FP_count': 63, 'human_review_labels_not_fabricated': True}
    write_json(out / 'verification.json', result)
    print(result)


if __name__ == '__main__':
    main()
