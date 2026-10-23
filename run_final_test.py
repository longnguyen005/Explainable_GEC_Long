"""Explicit, frozen-model final evaluation. Not invoked by any dev/notebook step."""
import bootstrap
import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description='Final test is excluded from the current work. Requires explicit opt-in.')
    parser.add_argument('--locked', type=Path, default=bootstrap.ROOT / 'outputs/dev_run_001/config_locked.json')
    parser.add_argument('--test-file', type=Path, required=True, help='User-supplied test JSON; it is not included in this project.')
    parser.add_argument('--authorize-test', action='store_true', help='Explicitly authorize opening the final test now.')
    args = parser.parse_args()
    if not args.authorize_test:
        parser.error('Test remains closed. Supply --authorize-test only after the team has reviewed the frozen configuration.')
    import joblib
    import numpy as np
    from threadpoolctl import threadpool_limits
    from sklearn.preprocessing import normalize
    from gec.data import flatten_gold, load_file
    from gec.dependency import get_parses
    from gec.exports import export_predictions
    from gec.features import get_tags, to_matrix
    from gec.io_utils import read_json, sha256, timestamp, write_csv, write_json
    from gec.metrics import score
    from gec.models import decode_knn, decode_lr
    from gec.rules import rule_predict

    root = bootstrap.ROOT
    locked = read_json(args.locked)
    config = locked['config']
    for name, expected in locked['code_sha256'].items():
        if sha256(root / name) != expected:
            raise RuntimeError(f'Frozen source has changed: {name}. Resolve on dev before opening test.')
    for entry in locked['bundles'].values():
        if sha256(root / entry['path']) != entry['sha256']:
            raise RuntimeError('A frozen model checksum has changed.')
    key = sha256(args.locked)[:16]
    out = root / 'outputs' / f'final_test_{key}'
    out.mkdir(parents=True, exist_ok=True)
    marker = out / 'evaluation_state.json'
    # Exclusive creation prevents inadvertent repeated evaluation, including after an interrupted run.
    with marker.open('x', encoding='utf-8') as stream:
        stream.write('{"status":"started"}')
    state = {'status': 'started', 'started_at': timestamp(), 'locked_sha256': sha256(args.locked)}
    write_json(marker, state)
    try:
        sentences, summary = load_file(args.test_file, 'test', allow_test=True, verify_expected=False)
        tags, _ = get_tags(root, 'test', sentences, root / config['cache_dir'])
        yt = flatten_gold(sentences)
        predictions = {'All_O': np.full(len(yt), 'O'),
                       'POS': np.array([label for s, t in zip(sentences, tags) for label in rule_predict(s.tokens, t)])}
        parsed, metadata = None, None
        metrics = []
        for name in ('LR_base', 'LR_parser', 'kNN'):
            entry = locked['bundles'][name]
            bundle = joblib.load(root / entry['path'])
            if bundle['variant'] == 'parser' and parsed is None:
                parsed, metadata, _ = get_parses(config, root / config['cache_dir'], 'test', sentences)
                expected_meta = locked['selection']['LR_parser']['parser_metadata'][0]
                for field in ('spacy', 'model', 'model_version', 'algorithm'):
                    if metadata[field] != expected_meta[field]:
                        raise RuntimeError('Parser identity differs from the frozen dev configuration.')
            x = to_matrix(sentences, tags, bundle['vocab'], parsed if bundle['variant'] == 'parser' else None)
            with threadpool_limits(limits=config['threads']):
                if bundle['kind'] == 'lr':
                    p = bundle['clf'].predict_proba(x)
                    predictions[name] = decode_lr(p, bundle['clf'].classes_, bundle['tau'])
                    export_predictions(out / f'predictions_{name}.csv', sentences, predictions[name], p, bundle['clf'].classes_)
                else:
                    z = normalize(bundle['svd'].transform(normalize(x)))
                    lab = []
                    for start in range(0, len(z), config['knn_batch_size']):
                        neighbors = bundle['neighbors'].kneighbors(z[start:start + config['knn_batch_size']], return_distance=False)
                        lab.append(bundle['yk'][neighbors])
                    predictions[name] = decode_knn(np.concatenate(lab), bundle['k'], bundle['tau'])
        for name, prediction in predictions.items():
            metrics.extend(score(name, yt, prediction))
            if name in ('All_O', 'POS', 'kNN'):
                export_predictions(out / f'predictions_{name}.csv', sentences, prediction)
        write_csv(out / 'metrics_test.csv', metrics)
        state.update(status='complete', completed_at=timestamp(), data=summary,
                     protocol='No fitting or tuning. Models fitted on train and selected using dev.')
        write_json(marker, state)
    except Exception as error:
        state.update(status='failed', failed_at=timestamp(), error=f'{type(error).__name__}: {error}')
        write_json(marker, state)
        raise


if __name__ == '__main__':
    main()

