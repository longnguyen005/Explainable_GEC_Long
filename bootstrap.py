"""Project-local dependencies; importing this file never downloads resources."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEPS = ROOT / '.deps'
if DEPS.exists():
    sys.path.insert(0, str(DEPS))
for variable in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ.setdefault(variable, '4')
os.environ.setdefault('NLTK_DATA', str(ROOT / 'resources' / 'nltk_data'))

