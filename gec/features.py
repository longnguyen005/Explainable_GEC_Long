from array import array
from collections import Counter
import gzip
import json
from pathlib import Path
import nltk
import numpy as np
import scipy.sparse as sp
from .data import token_hash
from .feature_strings import feature_strings
from .io_utils import object_hash, read_json, sha256, write_json


def get_tags(root, split, sentences, cache_dir):
    manifest = read_json(root / 'resources/pos_manifest.json')
    for name, expected in manifest['files'].items():
        if sha256(root / name) != expected:
            raise ValueError('POS model checksum mismatch.')
    metadata = {'tokens': token_hash(sentences), 'nltk': nltk.__version__, 'resource': manifest,
                'algorithm': 'nltk.pos_tag source tokens; v1'}
    key = object_hash(metadata)
    path = cache_dir / f'pos_{split}_{key[:16]}.json.gz'
    if path.exists():
        with gzip.open(path, 'rt', encoding='utf-8') as stream:
            payload = json.load(stream)
        if payload['metadata'] != metadata:
            raise ValueError('POS cache metadata mismatch.')
        tags = payload['tags']
    else:
        print(f'POS {split}: tagging {len(sentences)} records', flush=True)
        tags = [[tag for _, tag in nltk.pos_tag(s.tokens)] for s in sentences]
        with gzip.open(path, 'wt', encoding='utf-8') as stream:
            json.dump({'metadata': metadata, 'tags': tags}, stream)
    if len(tags) != len(sentences) or any(len(t) != len(s.tokens) for s, t in zip(sentences, tags)):
        raise ValueError('POS cache/token alignment mismatch.')
    return tags, metadata


def iter_features(sentences, tags, dependency=None):
    if len(sentences) != len(tags) or (dependency is not None and len(dependency) != len(sentences)):
        raise ValueError('Sentence/tag/parser record mismatch.')
    for index, (sentence, tag) in enumerate(zip(sentences, tags)):
        if len(sentence.tokens) != len(tag):
            raise ValueError('Tag alignment mismatch.')
        dep = None if dependency is None else dependency[index]
        if dep is not None and len(dep) != len(tag):
            raise ValueError('Parser alignment mismatch.')
        yield from feature_strings(sentence.tokens, tag, dep)


def fit_vocab(sentences, tags, min_count=3, dependency=None):
    cnt = Counter()
    for features in iter_features(sentences, tags, dependency):
        cnt.update(features)
    return {feature: index for index, feature in enumerate(sorted(f for f, count in cnt.items() if count >= min_count))}


def to_matrix(sentences, tags, vocab, dependency=None):
    indptr, indices = array('q', [0]), array('i')
    for features in iter_features(sentences, tags, dependency):
        indices.extend(vocab[f] for f in features if f in vocab)
        indptr.append(len(indices))
    matrix = sp.csr_matrix((np.ones(len(indices), dtype=np.float32),
                            np.frombuffer(indices, dtype=np.int32).copy(),
                            np.frombuffer(indptr, dtype=np.int64).copy()),
                           shape=(len(indptr) - 1, len(vocab)))
    matrix.sum_duplicates()
    matrix.data[:] = 1
    matrix.sort_indices()
    return matrix


def matrices(root, config, variant, train, dev, tags_tr, tags_dev, pos_meta,
             dep_tr=None, dep_dev=None, dep_meta=None):
    key = object_hash({'train': token_hash(train), 'dev': token_hash(dev), 'pos': pos_meta,
                       'variant': variant, 'dependency': dep_meta, 'min_count': config['min_count'],
                       'feature_source': sha256(root / 'gec/feature_strings.py'),
                       'matrix_source': sha256(root / 'gec/features.py')})
    prefix = root / config['cache_dir'] / f'matrix_{variant}_{key[:16]}'
    vocab_path = Path(str(prefix) + '_vocab.json')
    tr_path, dev_path = Path(str(prefix) + '_train.npz'), Path(str(prefix) + '_dev.npz')
    if vocab_path.exists() and tr_path.exists() and dev_path.exists():
        vocab = read_json(vocab_path)
        xtr, xdev = sp.load_npz(tr_path), sp.load_npz(dev_path)
    else:
        print(f'Features {variant}: fit vocabulary on train only', flush=True)
        vocab = fit_vocab(train, tags_tr, config['min_count'], dep_tr)
        xtr = to_matrix(train, tags_tr, vocab, dep_tr)
        xdev = to_matrix(dev, tags_dev, vocab, dep_dev)
        sp.save_npz(tr_path, xtr)
        sp.save_npz(dev_path, xdev)
        write_json(vocab_path, vocab)
    if xtr.shape[0] != sum(len(s.tokens) for s in train) or xdev.shape[0] != sum(len(s.tokens) for s in dev):
        raise ValueError('Matrix row count mismatch.')
    print(f'Features {variant}: train={xtr.shape}, dev={xdev.shape}', flush=True)
    return xtr, xdev, vocab, key

