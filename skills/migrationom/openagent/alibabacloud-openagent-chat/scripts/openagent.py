#!/usr/bin/env python3
"""Run the conversation client from any directory, with explicit dependency setup."""
import json
import os
from pathlib import Path
import sys

if sys.version_info < (3, 11):
    print(json.dumps({'ok': False, 'code': 'PythonVersion', 'message': 'Python 3.11 or later is required.'}))
    sys.exit(2)


def run_entry():
    from openagent_client.common import skill_version
    if sys.argv[1:] == ['version']:
        print(json.dumps({'ok': True, 'name': 'alibabacloud-openagent-chat', 'version': skill_version()}))
        return 0
    if sys.argv[1:] == ['credentials', 'inspect']:
        # Presence checks need no SDK or provider resolution, including on first use.
        skill_version()
        from openagent_client.credentials import inspect_presence
        print(json.dumps(inspect_presence()))
        return 0
    from bootstrap import STAMP, ready
    if not ready():
        if sys.argv[1:] == ['setup', 'status']:
            print(json.dumps({'ok': True, 'configuration_target': 'OpenAgent Skill',
                              'runtime_status': 'dependencies_changed' if STAMP.exists() else 'setup_required',
                              'configured': None, 'local_state_read': False,
                              'bootstrap_command': [sys.executable, str(Path(__file__).resolve()), 'bootstrap'],
                              'next_step': 'Run bootstrap once, then check setup status. Saved connections have not been read or changed.'}))
            return 0
        print(json.dumps({'ok': False, 'code': 'DependenciesMissing',
                          'message': 'Run this absolute-path entry with bootstrap to prepare the locked dependencies, then retry.'}))
        return 2
    from openagent_client.cli import main
    return main()


if __name__ == '__main__':
    from openagent_client.common import ClientError
    from openagent_client.concurrency import Busy, installation
    try:
        if sys.argv[1:] == ['version']:
            sys.exit(run_entry())
        if sys.argv[1:] == ['bootstrap']:
            from bootstrap import bootstrap
            sys.exit(bootstrap())
        package = Path(__file__).resolve().parent.parent
        # Runtime preparation is exclusive; active conversation clients share a
        # lease so unrelated host conversations can continue in parallel.
        with installation(package):
            if sys.argv[1:] == ['credentials', 'inspect']:
                sys.exit(run_entry())
            from bootstrap import PYTHON, ready
            redirect = ready() and Path(sys.prefix).resolve() != PYTHON.parent.parent.resolve()
        if redirect:
            os.execv(str(PYTHON), [str(PYTHON), str(Path(__file__).resolve()), *sys.argv[1:]])
        with installation(package):
            sys.exit(run_entry())
    except ClientError as exc:
        print(json.dumps(exc.result))
        sys.exit(2)
    except Busy as exc:
        print(json.dumps({'ok': False, 'code': 'StateBusy', 'scope': exc.scope, 'local_only': True,
                          'message': 'Local runtime preparation is in progress. Preserve saved task identifiers and retry when it finishes.'}))
        sys.exit(2)
    except ImportError:
        print(json.dumps({'ok': False, 'code': 'DependenciesMissing', 'message': 'Run this entry with bootstrap once, then retry.'}))
        sys.exit(2)
    except PermissionError:
        print(json.dumps({'ok': False, 'code': 'LocalPermissionDenied', 'message': 'Check ownership and permissions of the required local paths.'}))
        sys.exit(2)
    except OSError:
        print(json.dumps({'ok': False, 'code': 'InvalidInstallation',
                          'message': 'A required installation or runtime file is unavailable. Repair the installation, then recover any submitted task using its saved identifiers.'}))
        sys.exit(2)
    except RuntimeError:
        print(json.dumps({'ok': False, 'code': 'LockingUnavailable', 'message': 'This platform cannot provide safe process leases.'}))
        sys.exit(2)
