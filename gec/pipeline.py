import importlib.metadata
import platform
import sys
from pathlib import Path
import joblib
import numpy as np
from .data import cross_split_duplicates, flatten_gold, load_development
from .dependency import get_parses
from .exports import export_diagnostics, export_predictions, export_reference_review
from .features import get_tags, matrices
from .io_utils import object_hash, read_json, sha256, timestamp, write_csv, write_json
from .metrics import score
from .models import decode_lr, fit_knn, fit_lr_grid
from .rules import rule_predict


def code_fingerprints(root):
    paths = sorted((root / 'gec').glob('*.py')) + [root / name for name in
            ('bootstrap.py', 'run_dev.py', 'run_final_test.py')]
    return {str(p.relative_to(root)): sha256(p) for p in paths}


def environment():
    packages = ['numpy', 'scipy', 'scikit-learn', 'pandas', 'nltk', 'spacy',
                'en-core-web-sm', 'joblib', 'threadpoolctl', 'nbformat']
    versions = {}
    for package in packages:
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = None
    return {'python': sys.version, 'platform': platform.platform(), 'packages': versions}


def run(config_path, stage='all'):
    root = Path(__file__).resolve().parents[1]
    config = read_json(config_path)
    out, cache = root / config['output_dir'], root / config['cache_dir']
    for folder in (out, cache, root / config['model_dir']):
        folder.mkdir(parents=True, exist_ok=True)
    started = timestamp()
    manifest = {'started_at': started, 'config': config, 'config_sha256': sha256(config_path),
                'stage': stage, 'status': 'running', 'environment': environment(),
                'splits_read': ['train', 'dev'], 'test_opened': False, 'test_scored': False,
                'source_only_features': True, 'scope': 'gold-conditioned one-to-one subset',
                'selection_protocol_recorded_before_fit': config['selection_protocol']}
    write_json(out / 'run_manifest.json', manifest)
    write_json(out / 'selection_protocol.json', {'recorded_at': started,
                                               'protocol': config['selection_protocol'],
                                               'reference': {'C': config['reference_C'], 'tau': config['reference_tau']},
                                               'team_review_pending': True})
    try:
        train, dev, summaries = load_development(root / config['data_dir'])
        manifest['data'] = summaries
        for summary in summaries:
            print(f"{summary['split']}: {summary['records']} records, {summary['tokens']} tokens, gold="
                  f"{summary['SVA'] + summary['VFORM'] + summary['NNUM']}", flush=True)
        count_rows = [{k: v for k, v in row.items() if not isinstance(v, (dict, list))} for row in summaries]
        write_csv(out / 'data_counts.csv', count_rows)
        write_json(out / 'data_audit_details.json', summaries)
        duplicates = cross_split_duplicates(train, dev)
        write_csv(out / 'cross_split_duplicates.csv', duplicates)
        if stage == 'audit':
            manifest.update(status='complete_audit_only', completed_at=timestamp())
            write_json(out / 'run_manifest.json', manifest)
            return

        tags_tr, meta_tr = get_tags(root, 'train', train, cache)
        tags_dev, meta_dev = get_tags(root, 'dev', dev, cache)
        ytr, ydev = flatten_gold(train), flatten_gold(dev)
        xtr, xdev, vocab, base_key = matrices(root, config, 'base', train, dev, tags_tr, tags_dev,
                                            [meta_tr, meta_dev])
        metrics, predictions, selected, all_grid = [], {}, {}, []
        predictions['All_O'] = np.full(len(ydev), 'O')
        predictions['POS'] = np.array([label for sentence, tags in zip(dev, tags_dev)
                                       for label in rule_predict(sentence.tokens, tags)])
        for name in ('All_O', 'POS'):
            metrics.extend(score(name, ydev, predictions[name]))
            export_predictions(out / f'predictions_{name}.csv', dev, predictions[name])
        write_csv(out / 'metrics_dev.csv', metrics)

        base = fit_lr_grid(root, config, 'base', xtr, xdev, ytr, ydev, vocab, base_key)
        all_grid.extend(base['grid'])
        predictions['LR_base'] = base['prediction']
        metrics.extend(score('LR_base', ydev, base['prediction']))
        base_proba = base['probabilities'][base['chosen']['C']]
        export_predictions(out / 'predictions_LR_base.csv', dev, base['prediction'], base_proba, base['bundle']['clf'].classes_)
        selected['LR_base'] = {'parameters': base['chosen'], 'per_C_best': base['per_C'],
                               'bundle': str(base['bundle_path'].relative_to(root))}

        ref_C, ref_tau = config['reference_C'], config['reference_tau']
        ref_clf, _, ref_info = base['models'][ref_C]
        ref_proba = base['probabilities'][ref_C]
        ref_pred = decode_lr(ref_proba, ref_clf.classes_, ref_tau)
        ref_name = 'LR_reference_C3_tau065'
        predictions[ref_name] = ref_pred
        metrics.extend(score(ref_name, ydev, ref_pred))
        reference_dir = out / 'baseline_ref'
        export_predictions(reference_dir / 'predictions_dev.csv', dev, ref_pred, ref_proba, ref_clf.classes_)
        reference_path = root / config['model_dir'] / 'lr_reference.joblib'
        joblib.dump({**base['bundle'], 'clf': ref_clf, 'C': ref_C, 'tau': ref_tau,
                     'fit_metadata': ref_info}, reference_path, compress=3)
        fp_count, fn_count = export_reference_review(reference_dir, dev, ref_pred, ref_proba, ref_clf, vocab, tags_dev)
        ref_metrics = score(ref_name, ydev, ref_pred)
        write_csv(reference_dir / 'metrics_dev.csv', ref_metrics)
        selected['LR_reference'] = {'C': ref_C, 'tau': ref_tau, 'bundle': str(reference_path.relative_to(root)),
                                    'FP_untyped': fp_count, 'FN_untyped': fn_count,
                                    'report_expected_FP': 63, 'matches_report_FP_count': fp_count == 63}
        print(f'Reference review exported: {fp_count} FP, {fn_count} FN (actual, not forced to 63).', flush=True)
        write_csv(out / 'metrics_dev.csv', metrics)
        write_csv(out / 'tuning_grid.csv', all_grid)
        write_json(out / 'selected_config.json', selected)
        manifest['completed_stages'] = ['data', 'POS', 'LR_base', 'reference_review']
        write_json(out / 'run_manifest.json', manifest)
        variants = {'base': base}

        if stage in ('parser', 'all'):
            parsed_tr, dep_meta_tr, nlp = get_parses(config, cache, 'train', train)
            parsed_dev, dep_meta_dev, _ = get_parses(config, cache, 'dev', dev, nlp)
            pxtr, pxdev, pvocab, parser_key = matrices(root, config, 'parser', train, dev, tags_tr, tags_dev,
                                                      [meta_tr, meta_dev], parsed_tr, parsed_dev,
                                                      [dep_meta_tr, dep_meta_dev])
            parser_result = fit_lr_grid(root, config, 'parser', pxtr, pxdev, ytr, ydev, pvocab, parser_key)
            variants['parser'] = parser_result
            all_grid.extend(parser_result['grid'])
            predictions['LR_parser'] = parser_result['prediction']
            metrics.extend(score('LR_parser', ydev, parser_result['prediction']))
            parser_proba = parser_result['probabilities'][parser_result['chosen']['C']]
            export_predictions(out / 'predictions_LR_parser.csv', dev, parser_result['prediction'], parser_proba,
                               parser_result['bundle']['clf'].classes_)
            selected['LR_parser'] = {'parameters': parser_result['chosen'], 'per_C_best': parser_result['per_C'],
                                     'bundle': str(parser_result['bundle_path'].relative_to(root)),
                                     'parser_metadata': [dep_meta_tr, dep_meta_dev]}
            export_diagnostics(out / 'parser_four_cases.csv', dev, tags_dev, parsed_dev, variants)
            write_json(out / 'parser_alignment.json', {'train_records': len(parsed_tr), 'dev_records': len(parsed_dev),
                                                      'train_tokens': len(ytr), 'dev_tokens': len(ydev),
                                                      'changed_tokens': 0, 'checked_every_token': True,
                                                      'metadata': [dep_meta_tr, dep_meta_dev]})
            manifest['completed_stages'].append('LR_parser')
            write_csv(out / 'metrics_dev.csv', metrics)
            write_json(out / 'selected_config.json', selected)

        if config['run_knn'] and stage in ('knn', 'all'):
            knn = fit_knn(root, config, xtr, xdev, ytr, ydev, vocab, base_key)
            all_grid.extend(knn['grid'])
            predictions['kNN'] = knn['prediction']
            metrics.extend(score('kNN', ydev, knn['prediction']))
            export_predictions(out / 'predictions_kNN.csv', dev, knn['prediction'])
            selected['kNN'] = {'parameters': knn['chosen'], 'bundle': str(knn['bundle_path'].relative_to(root))}
            manifest['completed_stages'].append('kNN')

        duplicate_ids = {row['dev_id'] for row in duplicates}
        mask = np.array([s.record_id not in duplicate_ids for s in dev for _ in s.tokens])
        sensitivity = [row for name, pred in predictions.items() for row in score(name, ydev[mask], pred[mask])]
        write_csv(out / 'metrics_dev_without_duplicate.csv', sensitivity)
        write_csv(out / 'metrics_dev.csv', metrics)
        # Use a common schema because LR and kNN grids have different parameters.
        grid_columns = ['system', 'C', 'k', 'tau', 'TP', 'FP', 'FN', 'P', 'R', 'F1', 'F0.5',
                        'n_iter', 'converged', 'fit_seconds', 'feature_count']
        write_csv(out / 'tuning_grid.csv', all_grid, grid_columns)
        write_json(out / 'selected_config.json', selected)
        if stage == 'all':
            bundles = {name: {'path': entry['bundle'], 'sha256': sha256(root / entry['bundle'])}
                       for name, entry in selected.items() if 'bundle' in entry}
            locked = {'locked_at': timestamp(), 'status': 'dev_selection_frozen', 'team_review_pending': True,
                      'test_authorized': False, 'test_has_not_been_opened': True,
                      'config': config, 'selection': selected, 'bundles': bundles,
                      'data': summaries, 'environment': environment(),
                      'code_sha256': code_fingerprints(root)}
            write_json(out / 'config_locked.json', locked)
        manifest.update(status='complete', completed_at=timestamp(), selected=selected,
                        code_sha256=code_fingerprints(root))
        write_json(out / 'run_manifest.json', manifest)
        for row in metrics:
            if row['label'] == 'MICRO':
                print(f"{row['system']:27} {row['scoring']:7} TP={row['TP']:3} FP={row['FP']:3} FN={row['FN']:3} F0.5={row['F0.5']:.6f}", flush=True)
    except Exception as error:
        manifest.update(status='failed', failed_at=timestamp(), error=f'{type(error).__name__}: {error}')
        write_json(out / 'run_manifest.json', manifest)
        raise

