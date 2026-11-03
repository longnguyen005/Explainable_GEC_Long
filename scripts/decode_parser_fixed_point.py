"""Dev-only check: LR parser at the LR-base decision point (C=1.0, tau=0.45), per label.

No training, no tuning, no test access. Loads the already fitted C=1.0 parser model,
rebuilds dev features with the saved train vocabulary, and writes results to
outputs/fixed_point_check/ (outputs/dev_run_001 is not modified).

Usage (from project root):  python scripts/decode_parser_fixed_point.py
"""
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import bootstrap  # noqa: E402,F401  (sets NLTK_DATA / thread limits)

import joblib  # noqa: E402
import numpy as np  # noqa: E402
from gec.data import flatten_gold, load_file  # noqa: E402
from gec.dependency import get_parses  # noqa: E402
from gec.exports import export_predictions  # noqa: E402
from gec.features import get_tags, to_matrix  # noqa: E402
from gec.io_utils import read_json, timestamp, write_csv, write_json  # noqa: E402
from gec.metrics import counts, score  # noqa: E402
from gec.models import decode_lr  # noqa: E402

# Expected micro typed counts for LR_parser C=1.0 tau=0.45 from outputs/dev_run_001/tuning_grid.csv
EXPECTED_MICRO = (38, 122, 225)


def main():
    config = read_json(ROOT / 'configs/dev.json')
    cache_dir = ROOT / config['cache_dir']
    cache_dir.mkdir(exist_ok=True)
    out = ROOT / 'outputs' / 'fixed_point_check'
    out.mkdir(parents=True, exist_ok=True)

    sentences, _ = load_file(ROOT / config['data_dir'] / 'dev.json', 'dev')
    tags, _ = get_tags(ROOT, 'dev', sentences, cache_dir)
    parsed, parser_meta, _ = get_parses(config, cache_dir, 'dev', sentences)
    y_dev = flatten_gold(sentences)

    vocab = joblib.load(ROOT / 'models/lr_parser_selected.joblib')['vocab']  # same vocab for every C
    x_dev = to_matrix(sentences, tags, vocab, parsed)
    # Populate dev matrix cache files so verify_run.py can run without re-running train feature extraction.
    import scipy.sparse as sp
    base_bundle = joblib.load(ROOT / 'models/lr_base_selected.joblib')
    parser_bundle = joblib.load(ROOT / 'models/lr_parser_selected.joblib')
    base_npz = cache_dir / f"matrix_base_{base_bundle['matrix_key'][:16]}_dev.npz"
    parser_npz = cache_dir / f"matrix_parser_{parser_bundle['matrix_key'][:16]}_dev.npz"
    if not base_npz.exists():
        sp.save_npz(base_npz, to_matrix(sentences, tags, base_bundle['vocab'], None))
    if not parser_npz.exists():
        sp.save_npz(parser_npz, x_dev)
    model_paths = sorted((ROOT / 'models').glob('lr_parser_C1.0_*.joblib'))
    if len(model_paths) != 1:
        raise RuntimeError(f'Expected exactly one C=1.0 parser model, found {model_paths}')
    clf = joblib.load(model_paths[0])
    proba = clf.predict_proba(x_dev)

    rows = []
    for tau in (0.45, 0.60):  # 0.45 = LR-base point; 0.60 = best tau for parser at C=1.0 in the grid
        pred = decode_lr(proba, clf.classes_, tau)
        if tau == 0.45:
            micro = counts(y_dev, pred)
            if micro != EXPECTED_MICRO:
                raise RuntimeError(f'Reproduction mismatch: got {micro}, grid says {EXPECTED_MICRO}. Stop.')
            export_predictions(out / 'predictions_LR_parser_C1.0_tau0.45.csv', sentences, pred, proba, clf.classes_)
        for row in score(f'LR_parser_C1.0_tau{tau}', y_dev, pred):
            rows.append(row)
    write_csv(out / 'metrics_parser_fixed_point.csv', rows)

    # Descriptive dev check for the agreement hypothesis: gold SVA rate by (subject number, verb tag).
    pred_045 = decode_lr(proba, clf.classes_, 0.45)
    cell_total, cell_gold_sva, cell_pred_sva = Counter(), Counter(), Counter()
    flat_index = 0
    for sentence, dep_row in zip(sentences, parsed):
        for dep in dep_row:
            if dep['pos'] in ('VERB', 'AUX') and dep['tag'] in ('VBZ', 'VBP'):
                key = (dep['subject_number'], dep['tag'])
                cell_total[key] += 1
                cell_gold_sva[key] += int(y_dev[flat_index] == 'SVA')
                cell_pred_sva[key] += int(pred_045[flat_index] == 'SVA')
            flat_index += 1
    if flat_index != len(y_dev):
        raise RuntimeError('Token count mismatch in agreement table.')
    agreement = [{'subject_number': k[0], 'verb_tag': k[1], 'tokens': n,
                  'gold_SVA': cell_gold_sva[k], 'gold_SVA_rate': cell_gold_sva[k] / n,
                  'pred_SVA_C1_tau045': cell_pred_sva[k]}
                 for k, n in sorted(cell_total.items())]
    write_csv(out / 'agreement_by_subject_number_and_tag.csv', agreement)

    write_json(out / 'run_info.json', {
        'run_at': timestamp(), 'model': str(model_paths[0].relative_to(ROOT)),
        'vocab_size': len(vocab), 'parser_metadata': parser_meta,
        'reproduced_grid_micro_C1_tau045': list(EXPECTED_MICRO),
        'test_opened': False, 'training_performed': False,
    })
    for row in rows:
        print(row['system'], row['scoring'], row['label'], row['TP'], row['FP'], row['FN'], f"{row['F0.5']:.4f}")
    print('Agreement table:', out / 'agreement_by_subject_number_and_tag.csv')


if __name__ == '__main__':
    main()
