"""Count-first metrics with explicit shape and label validation."""
import numpy as np
from .data import TYPES


def checked(yt, yp):
    yt, yp = np.asarray(yt), np.asarray(yp)
    if yt.ndim != 1 or yp.ndim != 1 or yt.shape != yp.shape:
        raise ValueError(f'Gold/prediction shape mismatch: {yt.shape}, {yp.shape}')
    allowed = {'O', *TYPES}
    if not set(yt.tolist()).issubset(allowed) or not set(yp.tolist()).issubset(allowed):
        raise ValueError('Unknown label.')
    return yt, yp


def prf(tp, fp, fn):
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    return {'P': p, 'R': r, 'F1': 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.0,
            'F0.5': 1.25 * tp / (1.25 * tp + fp + 0.25 * fn) if 1.25 * tp + fp + 0.25 * fn else 0.0}


def counts(yt, yp, typed=True):
    yt, yp = checked(yt, yp)
    if typed:
        return (int(((yt == yp) & (yt != 'O')).sum()),
                int(((yp != 'O') & (yp != yt)).sum()),
                int(((yt != 'O') & (yp != yt)).sum()))
    return (int(((yt != 'O') & (yp != 'O')).sum()),
            int(((yt == 'O') & (yp != 'O')).sum()),
            int(((yt != 'O') & (yp == 'O')).sum()))


def score(name, yt, yp):
    yt, yp = checked(yt, yp)
    rows = []
    for label in TYPES:
        tp = int(((yt == label) & (yp == label)).sum())
        fp = int(((yt != label) & (yp == label)).sum())
        fn = int(((yt == label) & (yp != label)).sum())
        rows.append({'system': name, 'scoring': 'typed', 'label': label,
                     'gold': tp + fn, 'TP': tp, 'FP': fp, 'FN': fn, **prf(tp, fp, fn)})
    for typed in (True, False):
        tp, fp, fn = counts(yt, yp, typed)
        rows.append({'system': name, 'scoring': 'typed' if typed else 'untyped', 'label': 'MICRO',
                     'gold': tp + fn, 'TP': tp, 'FP': fp, 'FN': fn, **prf(tp, fp, fn)})
    return rows


def micro_f05(yt, yp):
    return prf(*counts(yt, yp))['F0.5']

