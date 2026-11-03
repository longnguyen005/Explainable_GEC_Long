"""Dev-only feature intervention for Long's existing fitted parser LR at C=1.

Copy this file into Explainable_GEC_Long/scripts/, then run from that project:
    python scripts/fp02_intervention_dev.py

Loads existing artifacts only. No model fitting, threshold selection or test access.
Output is kept separate from the original dev run and the frozen test results.
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path


def make_scenarios(dependency_row, token_index):
    """Change only the subject profile at the selected token; preserve the input."""
    scenarios = {'as_parsed': copy.deepcopy(dependency_row)}
    for name, index, tag, number in [
        ('manual_people', 1, 'NNS', 'Plur'),
        ('manual_today', 2, 'NN', 'Sing'),
    ]:
        row = copy.deepcopy(dependency_row)
        row[token_index].update(subject_index=index, subject_tag=tag,
                                subject_number=number,
                                subject_distance=str(index - token_index))
        scenarios[name] = row
    return scenarios


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--project-root', type=Path, default=Path(__file__).resolve().parents[1])
    args = cli.parse_args()
    root = args.project_root.resolve()
    if not (root / 'configs/dev.json').is_file():
        cli.error('Copy this script into the existing project scripts/ directory, or supply --project-root.')
    sys.path.insert(0, str(root))
    import bootstrap  # noqa: F401
    import joblib
    from gec.data import load_file
    from gec.dependency import get_parses
    from gec.features import get_tags, to_matrix
    from gec.io_utils import read_json, sha256, timestamp, write_csv, write_json
    from gec.models import decode_lr

    config = read_json(root / 'configs/dev.json')
    locked = read_json(root / 'outputs/dev_run_001/config_locked.json')
    # The review-summary patch does not alter any of these frozen ML sources.
    for relative, expected in locked['code_sha256'].items():
        if sha256(root / relative) != expected:
            raise RuntimeError(f'Frozen ML source differs: {relative}. Resolve using the recorded dev run.')
    selected_entry = locked['bundles']['LR_parser']
    selected_path = root / selected_entry['path']
    if sha256(selected_path) != selected_entry['sha256']:
        raise RuntimeError('Saved parser vocabulary/model bundle differs from the lock.')
    candidates = sorted((root / config['model_dir']).glob('lr_parser_C1.0_*.joblib'))
    if len(candidates) != 1:
        raise FileNotFoundError(f'Need the single existing C=1 parser model, found {len(candidates)}. This script does not train a replacement.')
    model_path = candidates[0]
    model = joblib.load(model_path)
    vocabulary = joblib.load(selected_path)['vocab']
    if float(model.C) != 1.0 or model.n_features_in_ != len(vocabulary):
        raise RuntimeError('C=1 model and train vocabulary do not match.')

    dev_path = root / config['data_dir'] / 'dev.json'
    sentences, dev_summary = load_file(dev_path, 'dev')
    frozen_dev = next(item for item in locked['data'] if item['split'] == 'dev')
    if dev_summary['input_sha256'] != frozen_dev['input_sha256']:
        raise RuntimeError('Dev data differ from the frozen run.')
    tags, _ = get_tags(root, 'dev', sentences, root / config['cache_dir'])
    parsed, parser_meta, _ = get_parses(config, root / config['cache_dir'], 'dev', sentences)
    expected_parser = locked['selection']['LR_parser']['parser_metadata'][1]
    for field in ('spacy', 'model', 'model_version', 'algorithm', 'tokens', 'pipeline'):
        if parser_meta[field] != expected_parser[field]:
            raise RuntimeError(f'Parser identity differs from the dev run: {field}')
    record_id, token_index = 'dev:001408', 3
    matches = [i for i, sentence in enumerate(sentences) if sentence.record_id == record_id]
    if len(matches) != 1:
        raise RuntimeError('FP02 record identity differs.')
    index = matches[0]
    sentence = sentences[index]
    if sentence.tokens[1:4] != ['people', 'today', 'realize']:
        raise RuntimeError('FP02 source/token identity differs.')
    if sentence.gold[token_index] != 'O':
        raise RuntimeError('FP02 gold is expected to be O.')
    tau = 0.45
    rows = []
    baseline_vector = None
    for scenario, dependency in make_scenarios(parsed[index], token_index).items():
        matrix = to_matrix([sentence], [tags[index]], vocabulary, [dependency])
        vector = matrix[token_index]
        if scenario == 'as_parsed':
            baseline_vector = vector
        changed = (vector - baseline_vector).tocoo()
        inverse = {column: feature for feature, column in vocabulary.items()}
        changed_features = [inverse[int(column)] for column in changed.col]
        if any(not feature.startswith('dep_subj_') for feature in changed_features):
            raise RuntimeError('Intervention changed a non-subject feature.')
        probabilities = model.predict_proba(vector)
        prediction = decode_lr(probabilities, model.classes_, tau)[0]
        active = dependency[token_index]
        row = {'record_id':record_id, 'token_index':token_index, 'token':'realize',
               'scenario':scenario, 'C':1.0, 'tau':tau, 'gold':'O', 'prediction':prediction,
               'p_error':float(1-probabilities[0,list(model.classes_).index('O')]),
               'subject_tag':active['subject_tag'], 'subject_number':active['subject_number'],
               'subject_distance':active['subject_distance'],
               'changed_features':json.dumps(changed_features, ensure_ascii=False)}
        for class_index, label in enumerate(model.classes_):
            row['p_'+label] = float(probabilities[0,class_index])
        rows.append(row)
    out = root / 'outputs' / ('fp02_intervention_dev_' + timestamp().replace(':','').replace('+','_'))
    out.mkdir(parents=True, exist_ok=False)
    write_csv(out / 'fp02_feature_intervention_dev.csv', rows)
    write_json(out / 'run_info.json', {
        'run_at':timestamp(), 'record_id':record_id, 'token_index':token_index,
        'C':1.0, 'tau':tau, 'fitted_model':str(model_path.relative_to(root)),
        'model_sha256':sha256(model_path), 'dev_sha256':sha256(dev_path),
        'parser_metadata':parser_meta, 'training_performed':False,
        'tuning_performed':False, 'test_opened':False,
        'manual_profiles':'people: NNS/Plur/dist -2; today: NN/Sing/dist -1. Declared hypothetical feature interventions, not expert parser labels.',
        'interpretation':'One fixed fitted model and threshold. A single-token illustration, not a causal estimate of full-dataset performance.',
    })
    print(json.dumps(rows, ensure_ascii=False, indent=2))
    print('OUTPUT_DIR='+str(out))


if __name__ == '__main__':
    main()
