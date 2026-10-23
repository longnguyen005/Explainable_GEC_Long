import json
from pathlib import Path
import numpy as np
from .data import TYPES
from .feature_strings import feature_strings
from .io_utils import write_csv, write_json
from .metrics import checked


def token_rows(sentences, prediction, probabilities=None, classes=None):
    total = sum(len(s.tokens) for s in sentences)
    if len(prediction) != total or (probabilities is not None and len(probabilities) != total):
        raise ValueError('Prediction/export token count mismatch.')
    iO = None if classes is None else list(classes).index('O')
    cursor = 0
    for sentence in sentences:
        for index, (token, gold) in enumerate(zip(sentence.tokens, sentence.gold)):
            row = {'record_id': sentence.record_id, 'token_index': index, 'token': token,
                   'gold': gold, 'prediction': str(prediction[cursor]), 'error_type': sentence.error_type,
                   'source': ' '.join(sentence.tokens)}
            if probabilities is not None:
                row['p_error'] = float(1 - probabilities[cursor, iO])
                row.update({f'p_{label}': float(probabilities[cursor, j]) for j, label in enumerate(classes)})
            yield row
            cursor += 1


def export_predictions(path, sentences, prediction, probabilities=None, classes=None):
    write_csv(path, token_rows(sentences, prediction, probabilities, classes))


def contributions(clf, vocab, features, error_label, limit=6):
    classes = list(clf.classes_)
    ci, oi = classes.index(error_label), classes.index('O')
    margin = clf.coef_[ci] - clf.coef_[oi]
    active = sorted({feature for feature in features if feature in vocab})
    values = [(f, float(margin[vocab[f]])) for f in active]
    positive = sorted([v for v in values if v[1] > 0], key=lambda v: -v[1])[:limit]
    negative = sorted([v for v in values if v[1] < 0], key=lambda v: v[1])[:limit]
    intercept = float(clf.intercept_[ci] - clf.intercept_[oi])
    return {'compared_error_label': error_label, 'intercept_error_minus_O': intercept,
            'full_margin_error_minus_O': intercept + sum(v for _, v in values),
            'top_positive': positive, 'top_negative': negative}


REVIEW_COLUMNS = ['review_label_A_B_C', 'reason', 'suggested_error_type', 'suggested_correction', 'reviewer', 'reviewed_at']


def export_reference_review(out_dir, sentences, prediction, proba, clf, vocab, tags):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    fps, fns = [], []
    flat = list(token_rows(sentences, prediction, proba, clf.classes_))
    cursor = 0
    for sentence, tag in zip(sentences, tags):
        features = feature_strings(sentence.tokens, tag)
        for i in range(len(sentence.tokens)):
            row = flat[cursor]
            cursor += 1
            if row['gold'] == 'O' and row['prediction'] != 'O':
                error = contributions(clf, vocab, features[i], row['prediction'])
                fps.append({'FP_ID': f'FP{len(fps)+1:03d}', **row,
                            'target_edit_reference': ' '.join(sentence.target_edit),
                            'contributions_error_minus_O': json.dumps(error, ensure_ascii=False)})
            if row['gold'] != 'O' and row['prediction'] == 'O':
                error = contributions(clf, vocab, features[i], row['gold'])
                fns.append({'FN_ID': f'FN{len(fns)+1:03d}', **row,
                            'target_edit_reference': ' '.join(sentence.target_edit),
                            'contributions_error_minus_O': json.dumps(error, ensure_ascii=False)})
    write_csv(out_dir / 'fp_reference.csv', fps)
    write_csv(out_dir / 'fn_reference.csv', fns)
    # Preserve completed human files when re-running the pipeline.
    template = [{**{k: v for k, v in row.items() if k != 'contributions_error_minus_O'},
                 **{name: '' for name in REVIEW_COLUMNS}} for row in fps]
    for person in ('Loan', 'Yen'):
        path = out_dir / f'review_{person}.csv'
        if not path.exists():
            write_csv(path, template, fieldnames=list(template[0]) if template else ['FP_ID', *REVIEW_COLUMNS])
    write_json(out_dir / 'review_manifest.json', {'FP_untyped': len(fps), 'FN_untyped': len(fns),
                                                'human_labels_completed': False,
                                                'instruction': 'Both reviewers annotate the same entire FP list independently. Do not copy AI judgments.'})
    return len(fps), len(fns)


DIAGNOSTIC_CASES = [('FP02', 'dev:001408', 3), ('FP03', 'dev:000644', 6),
                    ('FN01', 'dev:001866', 39), ('FN04', 'dev:001892', 11)]


def export_diagnostics(path, sentences, tags, parsed, variants):
    lookup, offset = {}, 0
    for index, sentence in enumerate(sentences):
        lookup[sentence.record_id] = (index, offset, sentence)
        offset += len(sentence.tokens)
    rows = []
    for report_case, record_id, token_index in DIAGNOSTIC_CASES:
        sentence_index, start, sentence = lookup[record_id]
        if token_index >= len(sentence.tokens):
            raise ValueError('Diagnostic token index invalid.')
        position = start + token_index
        dep = parsed[sentence_index][token_index]
        row = {'report_case_name': report_case, 'record_id': record_id, 'token_index': token_index,
               'token': sentence.tokens[token_index], 'gold': sentence.gold[token_index],
               'source': ' '.join(sentence.tokens), **dep}
        for name, result in variants.items():
            bundle = result['bundle']
            probs = result['probabilities'][bundle['C']]
            clf = bundle['clf']
            row[f'{name}_prediction'] = str(result['prediction'][position])
            row[f'{name}_p_error'] = float(1 - probs[position, list(clf.classes_).index('O')])
            row[f'{name}_C'], row[f'{name}_tau'] = bundle['C'], bundle['tau']
            fs = feature_strings(sentence.tokens, tags[sentence_index],
                                 parsed[sentence_index] if name == 'parser' else None)[token_index]
            row[f'{name}_SVA_margin'] = json.dumps(contributions(clf, bundle['vocab'], fs, 'SVA'), ensure_ascii=False)
        rows.append(row)
    write_csv(path, rows)
    return rows

