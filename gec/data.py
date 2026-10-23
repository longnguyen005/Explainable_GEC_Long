"""Reuse the audited decoder; all models receive the same source tokens/gold."""
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

from legacy_source.audit_counts import decode_record, load_records
from .io_utils import object_hash, sha256

TYPES = ('SVA', 'VFORM', 'NNUM')
EXPECTED = {
    'train': {'records': 14610, 'tokens': 416571, 'SVA': 1005, 'VFORM': 1190, 'NNUM': 1668},
    'dev': {'records': 2367, 'tokens': 68382, 'SVA': 74, 'VFORM': 69, 'NNUM': 120},
}


@dataclass
class Sentence:
    record_id: str
    tokens: list
    gold: list
    error_type: str
    source_positions: list
    target_edit: list


def load_file(path, split, allow_test=False, verify_expected=True):
    if split not in ('train', 'dev') and not (split == 'test' and allow_test):
        raise ValueError('Only train/dev are permitted in the development pipeline.')
    path = Path(path)
    sentences, excluded, changed = [], Counter(), []
    decoded = []
    for number, line, raw in load_records(path.read_text(encoding='utf-8')):
        row = decode_record(raw, split, number, line)
        decoded.append(row)
        if row['legacy_retained'] != row['retained']:
            changed.append(row['record_id'])
        if not row['retained']:
            excluded[row['edit_kind']] += 1
            continue
        tokens, gold = row['clean_source_tokens'], row['labels_after_filter']
        if not tokens or len(tokens) != len(gold) or any(not token for token in tokens):
            raise ValueError(f"Invalid source/labels: {row['record_id']}")
        sentences.append(Sentence(row['record_id'], tokens, gold, raw['error_type'],
                                  row['source_positions_clean_0based'], row['target_edit_tokens']))
    counts = Counter(label for sentence in sentences for label in sentence.gold)
    summary = {'split': split, 'original_records': len(decoded), 'records': len(sentences),
               'tokens': sum(len(s.tokens) for s in sentences),
               **{label: counts[label] for label in TYPES},
               'unique_sources': len({tuple(s.tokens) for s in sentences}),
               'excluded_records': sum(excluded.values()), 'input_sha256': sha256(path),
               'token_hash': token_hash(sentences), 'excluded_by_kind': dict(excluded),
               'legacy_retention_changes': changed}
    if verify_expected and split in EXPECTED:
        for key, expected in EXPECTED[split].items():
            if summary[key] != expected:
                raise ValueError(f'{split} {key}: expected {expected}, observed {summary[key]}')
    return sentences, summary


def load_development(data_dir):
    # Explicit names: never enumerate/load all JSON files in the directory.
    train, train_summary = load_file(Path(data_dir) / 'train.json', 'train')
    dev, dev_summary = load_file(Path(data_dir) / 'dev.json', 'dev')
    return train, dev, [train_summary, dev_summary]


def token_hash(sentences):
    return object_hash([(s.record_id, s.tokens) for s in sentences])


def flatten_gold(sentences):
    import numpy as np
    return np.array([label for sentence in sentences for label in sentence.gold])


def cross_split_duplicates(train, dev):
    seen = defaultdict(list)
    for sentence in train:
        seen[tuple(sentence.tokens)].append(sentence.record_id)
    return [{'train_ids': ';'.join(seen[tuple(s.tokens)]), 'dev_id': s.record_id,
             'token_count': len(s.tokens), 'source': ' '.join(s.tokens)}
            for s in dev if tuple(s.tokens) in seen]

