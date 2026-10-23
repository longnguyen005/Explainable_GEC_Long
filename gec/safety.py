"""Runtime guard for development. Final test runner is a separate entry point."""
import os
import sys

_installed = False


def install_development_guard():
    global _installed
    if _installed:
        return

    def audit(event, args):
        if event == 'open' and args and isinstance(args[0], (str, bytes, os.PathLike)):
            name = os.path.basename(os.fsdecode(args[0])).casefold()
            if name in ('test.json', 'test.pkl'):
                raise PermissionError('Development mode forbids opening test.json/test.pkl.')

    sys.addaudithook(audit)
    _installed = True

