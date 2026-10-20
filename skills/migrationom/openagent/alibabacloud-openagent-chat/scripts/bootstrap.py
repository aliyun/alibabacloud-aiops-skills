"""Fixed, external Python environment; installation is explicit and hash-locked."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import venv
from openagent_client.common import private_directory, resolve_paths

ROOT = Path(__file__).resolve().parent
LOCK = ROOT.parent / 'assets' / 'requirements.txt'
PATHS = resolve_paths()
RUNTIME = PATHS['data'] / 'python-runtimes' / hashlib.sha256(LOCK.read_bytes()).hexdigest()
PYTHON = RUNTIME / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
STAMP = RUNTIME / 'requirements.sha256'

def fingerprint():
    return hashlib.sha256(LOCK.read_bytes()).hexdigest()

def ready():
    return PYTHON.is_file() and STAMP.is_file() and STAMP.read_text().strip() == fingerprint()

def install():
    if not ready():
        private_directory(RUNTIME)
        # A failed install never leaves the old ready marker behind.
        STAMP.unlink(missing_ok=True)
        venv.EnvBuilder(with_pip=True, symlinks=os.name != 'nt', clear=True).create(RUNTIME)
        result = subprocess.run([str(PYTHON), '-m', 'pip', 'install', '--disable-pip-version-check',
                                 '--require-hashes', '-r', str(LOCK)], capture_output=True)
        if result.returncode:
            print(json.dumps({'ok': False, 'code': 'DependencyInstallFailed',
                              'message': 'The locked dependency installation failed. Check local package-index access; installation output is withheld because it may contain credentials.'}))
            return 2
        STAMP.write_text(fingerprint() + '\n')
        STAMP.chmod(0o600)
    print(json.dumps({'ok': True, 'status': 'ready', 'entry': str(ROOT / 'openagent.py'),
                      'python': str(PYTHON)}))
    return 0


def bootstrap():
    from openagent_client.concurrency import Busy, installation
    try:
        if PATHS['data'].parent == PATHS['legacy']:
            private_directory(PATHS['legacy'])
        private_directory(PATHS['data'])
        private_directory(RUNTIME.parent)
        if RUNTIME.is_symlink():
            raise OSError('Unsafe runtime directory')
        with installation(ROOT.parent, exclusive=True):
            return install()
    except Busy as exc:
        print(json.dumps({'ok': False, 'code': 'StateBusy', 'scope': exc.scope, 'local_only': True,
                          'message': 'The local installation is in use. Retry after active commands finish.'}))
        return 2
    except Exception:
        print(json.dumps({'ok': False, 'code': 'BootstrapFailed', 'message': 'The managed environment could not be created. Check Python, process locking support and local permissions; no ready marker was written.'}))
        return 2
