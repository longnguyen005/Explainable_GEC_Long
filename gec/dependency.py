"""Pretokenized spaCy parsing; source tokens only, no correction/evidence input."""
import gzip
import json
import time
import spacy
from spacy.tokens import Doc
from .data import token_hash
from .io_utils import object_hash

SUBJECT_DEPS = {'nsubj', 'nsubjpass', 'csubj', 'csubjpass'}
ALGORITHM = 'v1: direct subject; auxiliary inherits lexical head subject; exact signed distance'


def describe(doc):
    result = []
    for token in doc:
        subject, relation = None, 'none'
        if token.pos_ in ('VERB', 'AUX'):
            candidates = sorted((c for c in token.children if c.dep_ in SUBJECT_DEPS),
                                key=lambda c: (abs(c.i - token.i), c.i))
            if candidates:
                subject, relation = candidates[0], 'direct'
            elif token.dep_ in ('aux', 'auxpass', 'cop') and token.head != token:
                candidates = sorted((c for c in token.head.children if c.dep_ in SUBJECT_DEPS),
                                    key=lambda c: (abs(c.i - token.i), c.i))
                if candidates:
                    subject, relation = candidates[0], 'auxiliary_head'
        result.append({'token': token.text, 'pos': token.pos_, 'tag': token.tag_,
                       'dep': token.dep_, 'head_index': token.head.i,
                       'subject_index': None if subject is None else subject.i,
                       'subject_text': '<NONE>' if subject is None else subject.text,
                       'subject_tag': '<NONE>' if subject is None else subject.tag_,
                       'subject_number': '<UNK>' if subject is None else ('|'.join(subject.morph.get('Number')) or '<UNK>'),
                       'subject_distance': '<NONE>' if subject is None else str(subject.i - token.i),
                       'subject_relation': relation})
    return result


def get_parses(config, cache_dir, split, sentences, nlp=None):
    if nlp is None:
        nlp = spacy.load(config['parser_model'], disable=['ner', 'lemmatizer'])
    metadata = {'spacy': spacy.__version__, 'model': config['parser_model'],
                'model_version': nlp.meta['version'], 'tokens': token_hash(sentences),
                'algorithm': ALGORITHM,
                'pipeline': nlp.pipe_names,
                'tokenization': 'Doc(words=EXPECT tokens, spaces=True except final token)'}
    key = object_hash(metadata)
    path = cache_dir / f'parser_{split}_{key[:16]}.json.gz'
    started = time.perf_counter()
    if path.exists():
        with gzip.open(path, 'rt', encoding='utf-8') as stream:
            payload = json.load(stream)
        if payload['metadata'] != metadata:
            raise ValueError('Parser cache mismatch.')
        parsed = payload['parsed']
    else:
        print(f'Parser {split}: {len(sentences)} pretokenized records', flush=True)
        docs = (Doc(nlp.vocab, words=s.tokens, spaces=[True] * (len(s.tokens) - 1) + [False])
                for s in sentences)
        parsed = []
        for index, (sentence, doc) in enumerate(zip(sentences, nlp.pipe(docs, batch_size=config['parser_batch_size'], n_process=1)), 1):
            if [t.text for t in doc] != sentence.tokens:
                raise ValueError(f'Parser changed tokenization: {sentence.record_id}')
            parsed.append(describe(doc))
            if index % 2000 == 0:
                print(f'Parser {split}: {index}/{len(sentences)}', flush=True)
        with gzip.open(path, 'wt', encoding='utf-8') as stream:
            json.dump({'metadata': metadata, 'parsed': parsed}, stream, ensure_ascii=False)
    if len(parsed) != len(sentences) or any([d['token'] for d in row] != s.tokens for s, row in zip(sentences, parsed)):
        raise ValueError('Parser/source token alignment failed.')
    print(f'Parser {split}: ready in {time.perf_counter() - started:.1f}s', flush=True)
    return parsed, metadata, nlp

