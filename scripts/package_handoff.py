"""Portable source/data/results/selected-model bundle, without machine-specific deps."""
import sys
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import bootstrap
from gec.io_utils import read_json, sha256, timestamp, write_json


def main():
    output = ROOT.parent / 'output' / 'packages'
    output.mkdir(parents=True, exist_ok=True)
    files = []
    for directory in ('gec', 'tests', 'configs', 'scripts', 'data', 'legacy_source', 'legacy_results', 'resources', 'outputs'):
        files.extend(p for p in (ROOT / directory).rglob('*') if p.is_file()
                     and '__pycache__' not in p.parts and p.suffix != '.pyc')
    for name in ('README.md', 'LONG_HANDOFF.md', 'EXPECT_Long_Dev.ipynb', 'SOURCE_MANIFEST.json',
                 'requirements.txt', 'requirements-lock.txt', 'bootstrap.py', 'run_dev.py', 'run_dev.ps1',
                 'prepare_resources.py', 'run_final_test.py', 'verify_run.py', 'summarize_reviews.py'):
        files.append(ROOT / name)
    locked = read_json(ROOT / 'outputs/dev_run_001/config_locked.json')
    files.extend(ROOT / row['path'] for row in locked['bundles'].values())
    # Per-C checkpoints are small and allow the LR grids to resume after copying.
    files.extend(p for p in (ROOT / 'models').iterdir() if p.is_file() and p.name.startswith('lr_'))
    files = sorted(set(files))
    if any(p.name.casefold() in ('test.json', 'test.pkl') for p in files):
        raise RuntimeError('Test data must not be packaged.')
    inventory = {str(p.relative_to(ROOT)): {'bytes': p.stat().st_size, 'sha256': sha256(p)} for p in files}
    write_json(ROOT / 'ARTIFACTS_SHA256.json', {'created_at': timestamp(), 'files': inventory,
                                              'test_data_included': False, 'local_dependencies_included': False})
    files.append(ROOT / 'ARTIFACTS_SHA256.json')
    path = output / 'Explainable_GEC_Long_handoff.zip'
    with ZipFile(path, 'w', compression=ZIP_DEFLATED, compresslevel=5) as archive:
        for file in files:
            archive.write(file, str(Path('Explainable_GEC_Long') / file.relative_to(ROOT)))
    with ZipFile(path) as archive:
        bad = archive.testzip()
        if bad:
            raise RuntimeError(f'ZIP integrity failed: {bad}')
        count = len(archive.infolist())
    write_json(output / 'Explainable_GEC_Long_handoff.sha256.json',
               {'file': path.name, 'sha256': sha256(path), 'bytes': path.stat().st_size,
                'entries': count, 'zip_integrity_passed': True})
    print(f'Package: {path}; {path.stat().st_size / 1024**2:.1f} MiB; {count} files; ZIP integrity passed.')


if __name__ == '__main__':
    main()
