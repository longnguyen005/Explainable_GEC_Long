import time
import warnings
from pathlib import Path
import joblib
import numpy as np
import sklearn
from sklearn.decomposition import TruncatedSVD
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import normalize
from threadpoolctl import threadpool_limits
from .data import TYPES
from .io_utils import object_hash, read_json, sha256, write_json
from .metrics import counts, prf


def decode_lr(probabilities, classes, tau):
    classes = np.asarray(classes)
    index_O = list(classes).index('O')
    p_error = 1 - probabilities[:, index_O]
    error_proba = probabilities.copy()
    error_proba[:, index_O] = -1
    return np.where(p_error >= tau, classes[error_proba.argmax(axis=1)], 'O')


def decode_knn(neighbor_labels, k, tau):
    neighbor_labels = neighbor_labels[:, :k]
    votes = np.stack([(neighbor_labels == label).sum(axis=1) for label in TYPES], axis=1)
    # Preserve the original TYPES-order tie break: SVA, VFORM, NNUM.
    best = np.array(TYPES)[votes.argmax(axis=1)]
    return np.where(votes.sum(axis=1) / k >= tau, best, 'O')


def select_lr(grid, margin):
    best_per_C = []
    for C in sorted({row['C'] for row in grid}):
        candidates = [row for row in grid if row['C'] == C]
        best_per_C.append(sorted(candidates, key=lambda r: (-r['F0.5'], -r['P'], -r['tau']))[0])
    maximum = max(row['F0.5'] for row in best_per_C)
    eligible = [row for row in best_per_C if maximum - row['F0.5'] < margin or row['F0.5'] == maximum]
    return min(eligible, key=lambda row: row['C']), best_per_C


def fit_lr_grid(root, config, variant, xtr, xdev, ytr, ydev, vocab, matrix_key):
    model_dir = root / config['model_dir']
    models, probabilities, grid = {}, {}, []
    for C in config['C_grid']:
        identity = {'matrix_key': matrix_key, 'labels': object_hash(ytr.tolist()), 'C': C,
                    'max_iter': config['lr_max_iter'], 'tol': config['lr_tol'],
                    'solver': 'lbfgs', 'class_weight': None, 'sklearn': sklearn.__version__,
                    'training_code': sha256(root / 'gec/models.py')}
        key = object_hash(identity)[:16]
        path = model_dir / f'lr_{variant}_C{C}_{key}.joblib'
        meta_path = path.with_suffix('.json')
        started = time.perf_counter()
        if path.exists() and meta_path.exists() and read_json(meta_path)['identity'] == identity:
            clf = joblib.load(path)
            info = read_json(meta_path)
            print(f'LR {variant} C={C}: restored fitted model', flush=True)
        else:
            print(f'LR {variant} C={C}: fit train only', flush=True)
            clf = LogisticRegression(C=C, solver='lbfgs', max_iter=config['lr_max_iter'],
                                     tol=config['lr_tol'], class_weight=None, random_state=config['seed'])
            with warnings.catch_warnings(record=True) as caught, threadpool_limits(limits=config['threads']):
                warnings.simplefilter('always', ConvergenceWarning)
                clf.fit(xtr, ytr)
            convergence = [str(w.message) for w in caught if issubclass(w.category, ConvergenceWarning)]
            info = {'identity': identity, 'fit_seconds': time.perf_counter() - started,
                    'n_iter': int(clf.n_iter_.max()), 'converged': not convergence,
                    'convergence_warnings': convergence}
            joblib.dump(clf, path, compress=3)
            write_json(meta_path, info)
            if convergence:
                raise RuntimeError(f'LR {variant} C={C} did not converge; see {meta_path}')
        with threadpool_limits(limits=config['threads']):
            proba = clf.predict_proba(xdev)
        models[C], probabilities[C] = (clf, path, info), proba
        for tau in config['tau_grid']:
            prediction = decode_lr(proba, clf.classes_, tau)
            tp, fp, fn = counts(ydev, prediction)
            grid.append({'system': f'LR_{variant}', 'C': C, 'tau': tau,
                         'TP': tp, 'FP': fp, 'FN': fn, **prf(tp, fp, fn),
                         'n_iter': info['n_iter'], 'converged': info['converged'],
                         'fit_seconds': info['fit_seconds'], 'feature_count': len(vocab)})
        local = sorted([r for r in grid if r['C'] == C], key=lambda r: (-r['F0.5'], -r['P'], -r['tau']))[0]
        print(f"LR {variant} C={C}: n_iter={info['n_iter']} best_tau={local['tau']} F0.5={local['F0.5']:.6f}", flush=True)
    chosen, per_C = select_lr(grid, config['near_tie_C_margin'])
    clf, fitted_path, info = models[chosen['C']]
    bundle_path = model_dir / f'lr_{variant}_selected.joblib'
    bundle = {'kind': 'lr', 'variant': variant, 'clf': clf, 'vocab': vocab,
              'tau': chosen['tau'], 'C': chosen['C'], 'min_count': config['min_count'],
              'matrix_key': matrix_key, 'fit_metadata': info, 'model_path': str(fitted_path.relative_to(root))}
    joblib.dump(bundle, bundle_path, compress=3)
    return {'chosen': chosen, 'per_C': per_C, 'grid': grid, 'models': models,
            'probabilities': probabilities, 'bundle': bundle, 'bundle_path': bundle_path,
            'prediction': decode_lr(probabilities[chosen['C']], clf.classes_, chosen['tau'])}


def fit_knn(root, config, xtr, xdev, ytr, ydev, vocab, matrix_key):
    identity = {'matrix': matrix_key, 'labels': object_hash(ytr.tolist()), 'seed': config['seed'],
                'svd_components': config['svd_components'], 'O_per_error': config['knn_O_per_error'],
                'k_grid': config['k_grid'], 'sklearn': sklearn.__version__,
                'training_code': sha256(root / 'gec/models.py')}
    key = object_hash(identity)[:16]
    cache_dir, model_dir = root / config['cache_dir'], root / config['model_dir']
    labels_path = cache_dir / f'knn_neighbors_{key}.npy'
    fit_path = model_dir / f'knn_fit_{key}.joblib'
    meta_path = model_dir / f'knn_fit_{key}.json'
    if labels_path.exists() and fit_path.exists() and meta_path.exists() and read_json(meta_path)['identity'] == identity:
        lab_dev = np.load(labels_path)
        fitted = joblib.load(fit_path)
        info = read_json(meta_path)
        print('kNN: restored fit and dev neighbor labels', flush=True)
    else:
        started = time.perf_counter()
        print(f"kNN: train-only SVD {config['svd_components']} components", flush=True)
        svd = TruncatedSVD(n_components=config['svd_components'], random_state=config['seed'])
        with threadpool_limits(limits=config['threads']):
            ztr = normalize(svd.fit_transform(normalize(xtr)))
            zdev = normalize(svd.transform(normalize(xdev)))
        rng = np.random.RandomState(config['seed'])
        idx_error, idx_O = np.where(ytr != 'O')[0], np.where(ytr == 'O')[0]
        size_O = config['knn_O_per_error'] * len(idx_error)
        if len(idx_O) < size_O:
            raise ValueError('Not enough O tokens for the declared sampling protocol.')
        keep = np.concatenate([idx_error, rng.choice(idx_O, size=size_O, replace=False)])
        zkeep, ykeep = ztr[keep], ytr[keep]
        nn = NearestNeighbors(n_neighbors=max(config['k_grid']), metric='cosine', algorithm='brute',
                              n_jobs=config['threads']).fit(zkeep)
        del ztr
        chunks = []
        for start in range(0, len(zdev), config['knn_batch_size']):
            with threadpool_limits(limits=config['threads']):
                neighbors = nn.kneighbors(zdev[start:start + config['knn_batch_size']], return_distance=False)
            chunks.append(ykeep[neighbors])
            if start % (config['knn_batch_size'] * 16) == 0:
                print(f'kNN dev neighbors: {start}/{len(zdev)}', flush=True)
        lab_dev = np.concatenate(chunks)
        fitted = {'svd': svd, 'neighbors': nn, 'yk': ykeep, 'keep_indices': keep,
                  'vocab': vocab, 'variant': 'base', 'kind': 'knn', 'matrix_key': matrix_key}
        info = {'identity': identity, 'fit_and_neighbors_seconds': time.perf_counter() - started,
                'error_tokens': len(idx_error), 'O_tokens': size_O, 'sample_tokens': len(keep),
                'explained_variance_ratio_sum': float(svd.explained_variance_ratio_.sum())}
        np.save(labels_path, lab_dev)
        joblib.dump(fitted, fit_path, compress=3)
        write_json(meta_path, info)
    grid = []
    for k in config['k_grid']:
        for tau in config['tau_grid']:
            pred = decode_knn(lab_dev, k, tau)
            tp, fp, fn = counts(ydev, pred)
            grid.append({'system': 'kNN', 'k': k, 'tau': tau, 'TP': tp, 'FP': fp, 'FN': fn,
                         **prf(tp, fp, fn), 'feature_count': len(vocab)})
    chosen = sorted(grid, key=lambda r: (-r['F0.5'], -r['P'], r['k'], -r['tau']))[0]
    bundle = {**fitted, 'k': chosen['k'], 'tau': chosen['tau'], 'fit_metadata': info}
    bundle_path = model_dir / 'knn_selected.joblib'
    joblib.dump(bundle, bundle_path, compress=3)
    print(f"kNN: selected k={chosen['k']} tau={chosen['tau']} F0.5={chosen['F0.5']:.6f}", flush=True)
    return {'chosen': chosen, 'grid': grid, 'bundle_path': bundle_path, 'bundle': bundle,
            'prediction': decode_knn(lab_dev, chosen['k'], chosen['tau'])}

