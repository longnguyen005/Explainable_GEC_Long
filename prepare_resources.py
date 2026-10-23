"""Explicit resource download; never called by training or module imports."""
import bootstrap
from pathlib import Path
import nltk
from gec.io_utils import sha256, write_json


def main():
    target = bootstrap.ROOT / 'resources/nltk_data'
    target.mkdir(parents=True, exist_ok=True)
    resource = 'averaged_perceptron_tagger_eng'
    nltk.download(resource, download_dir=str(target), raise_on_error=True)
    files = sorted((target / 'taggers' / resource).glob('*.json'))
    if len(files) != 3:
        raise RuntimeError('Expected the three JSON files of the English perceptron tagger.')
    write_json(bootstrap.ROOT / 'resources/pos_manifest.json',
               {'nltk_version': nltk.__version__, 'resource': resource,
                'files': {str(p.relative_to(bootstrap.ROOT)): sha256(p) for p in files}})
    print('POS resources ready; TLS verification was not disabled.')


if __name__ == '__main__':
    main()

