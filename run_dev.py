"""Development entry point. There is deliberately no --test option."""
import bootstrap
import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=Path, default=bootstrap.ROOT / 'configs/dev.json')
    parser.add_argument('--stage', choices=['audit', 'base', 'parser', 'knn', 'all'], default='all')
    args = parser.parse_args()
    from gec.safety import install_development_guard
    install_development_guard()
    from gec.pipeline import run
    run(args.config, args.stage)


if __name__ == '__main__':
    main()

