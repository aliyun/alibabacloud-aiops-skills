"""Package identity, private state and safe errors shared by the client."""
import hashlib
import json
from contextlib import ExitStack, contextmanager
import os
import re
import sys
import tempfile
import uuid
from pathlib import Path

APP_NAME = 'openagent'
ROOT = Path(__file__).resolve().parents[2]
MANIFEST = 'assets/release.json'
CANONICAL_NAME = 'alibabacloud-openagent-chat'


class ClientError(Exception):
    def __init__(self, code, message, **details):
        self.result = {'ok': False, 'code': code, 'message': message, **details}
        super().__init__(message)


def parse_manifest(content, path):
    """Read the installed package identity without loading SDKs or local state."""
    def invalid(reason):
        raise ClientError('InvalidSkillManifest', 'The release metadata is invalid: ' + reason,
                          manifest_path=str(path)) from None
    if len(content) > 64 * 1024:
        invalid('size limit exceeded.')
    try:
        value = json.loads(content.decode('utf-8'))
    except (ValueError, UnicodeError):
        invalid('expected UTF-8 JSON.')
    if not isinstance(value, dict):
        invalid('expected a JSON object.')
    if value.get('name') != CANONICAL_NAME:
        invalid('name must match the installed OpenAgent Skill.')
    version = value.get('version')
    if not isinstance(version, str) or not re.fullmatch(r'(0|[1-9][0-9]{0,8})\.(0|[1-9][0-9]{0,8})\.(0|[1-9][0-9]{0,8})', version):
        invalid('version must be major.minor.patch with no whitespace or leading zeroes.')
    return version


def skill_version(root=ROOT):
    """Use release.json as the single version source, independent of the cwd."""
    path = Path(root) / MANIFEST
    try:
        with path.open('rb') as source:
            content = source.read(64 * 1024 + 1)
    except OSError:
        raise ClientError('InvalidSkillManifest', 'The release metadata is missing or unreadable.',
                          manifest_path=str(path)) from None
    return parse_manifest(content, path)


def user_agent(root=ROOT):
    version = skill_version(root)
    # Each Transport keeps this invocation identity across requests and retries.
    # Hosts may correlate subprocesses with a separate ID per host conversation.
    session_id = os.environ.get('SKILL_SESSION_ID')
    if session_id is None:
        session_id = uuid.uuid4().hex
    require(isinstance(session_id, str) and bool(re.fullmatch(r'[0-9a-fA-F]{32}', session_id)),
            'InvalidInvocation', 'The invocation identifier must contain 32 hexadecimal characters.')
    return 'AlibabaCloud-Agent-Skills/' + CANONICAL_NAME + '/' + session_id + ' skill-version/' + version


def require(condition, code, message, **details):
    if not condition:
        raise ClientError(code, message, **details)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()


def read_json(path):
    p = Path(path)
    require(p.stat().st_size <= 8 * 1024 * 1024, 'InputTooLarge', 'The input exceeds the size limit.')
    return json.loads(p.read_text(encoding='utf-8'))


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    require(not path.is_symlink(), 'UnsafePath', 'State files must not be symbolic links.')
    fd, name = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(value, f, ensure_ascii=False, sort_keys=True)
            f.flush()
            os.fsync(f.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def _write_private_bytes(path, content):
    require(not path.is_symlink(), 'UnsafePath', 'Private files must not be symbolic links.')
    fd, temporary = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def resolve_paths(root=None, *, platform=None, environ=None, home=None):
    """Resolve storage without creating directories or importing dependencies."""
    platform = sys.platform if platform is None else platform
    environ = os.environ if environ is None else environ
    home = Path.home() if home is None else Path(home)
    if root is not None:
        base = Path(root).absolute()
        # Reopening a Store via its public state root keeps the same sandbox.
        if base.name == 'state' and all((base.parent / name).is_dir() for name in ('config', 'data', 'cache', 'runtime')):
            base = base.parent
        return {'base': base, 'legacy': base, **{name: base / name for name in ('config', 'state', 'data', 'cache', 'runtime')}}

    def absolute_env(name, fallback):
        value = environ.get(name)
        return Path(value) if value and Path(value).is_absolute() else Path(fallback)

    identity = str(os.getuid()) if hasattr(os, 'getuid') else hashlib.sha256(str(home).encode()).hexdigest()[:16]
    temporary = Path(tempfile.gettempdir()) / (APP_NAME + '-runtime-' + identity)
    if platform.startswith('linux'):
        config = absolute_env('XDG_CONFIG_HOME', home / '.config') / APP_NAME
        runtime_value = environ.get('XDG_RUNTIME_DIR')
        runtime_parent = Path(runtime_value) if runtime_value and Path(runtime_value).is_absolute() else None
        return {'base': None, 'legacy': config, 'config': config,
                'state': absolute_env('XDG_STATE_HOME', home / '.local/state') / APP_NAME,
                'data': absolute_env('XDG_DATA_HOME', home / '.local/share') / APP_NAME,
                'cache': absolute_env('XDG_CACHE_HOME', home / '.cache') / APP_NAME,
                'runtime': runtime_parent / APP_NAME if runtime_parent else temporary,
                'runtime_parent': runtime_parent}
    if platform == 'darwin':
        support = home / 'Library/Application Support' / APP_NAME
        return {'base': None, 'legacy': support, 'config': support / 'config', 'state': support / 'state',
                'data': support / 'data', 'cache': home / 'Library/Caches' / APP_NAME, 'runtime': temporary}
    if platform == 'win32':
        local = absolute_env('LOCALAPPDATA', home / 'AppData/Local') / APP_NAME
        return {'base': None, 'legacy': local, 'config': local / 'config', 'state': local / 'state',
                'data': local / 'data', 'cache': local / 'Cache', 'runtime': temporary}
    config = absolute_env('XDG_CONFIG_HOME', home / '.config') / APP_NAME
    return {'base': None, 'legacy': config, 'config': config,
            'state': absolute_env('XDG_STATE_HOME', home / '.local/state') / APP_NAME,
            'data': absolute_env('XDG_DATA_HOME', home / '.local/share') / APP_NAME,
            'cache': absolute_env('XDG_CACHE_HOME', home / '.cache') / APP_NAME, 'runtime': temporary}


def private_directory(path):
    path = Path(path)
    require(not path.is_symlink(), 'UnsafePath', 'Private directories must not be symbolic links.')
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    require(path.is_dir(), 'UnsafePath', 'Private storage must be a directory.')
    if os.name == 'posix':
        require(path.stat().st_uid == os.getuid() and path.stat().st_mode & 0o077 == 0,
                'UnsafePermissions', 'Private storage must be owned by you and accessible only to you.')
    return path


def _file_digest(path):
    require(not path.is_symlink(), 'UnsafePath', 'State files must not be symbolic links.')
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


class Store:
    def __init__(self, root=None):
        paths = resolve_paths(root)
        self.base = paths['base']
        self.legacy_root = paths['legacy']
        if self.base is not None or paths['config'].parent == self.legacy_root:
            private_directory(self.legacy_root)
        if paths.get('runtime_parent') is not None:
            private_directory(paths['runtime_parent'])
        for name in ('config', 'state', 'data', 'cache', 'runtime'):
            setattr(self, name + '_root', private_directory(paths[name]))
        self.root = self.state_root
        with self._lifecycle_lock():
            self._migrate_legacy()
        self.connection_migration_warning = None
        if self._get_raw('connection') is None and self._get_raw('.connection-migration-warning') == {'code': 'LegacyConnectionConflict'}:
            self.connection_migration_warning = {
                'code': 'LegacyConnectionConflict',
                'message': 'Previous local connection records disagree. Choose the intended service region and credential source with setup configure; historical files were retained.',
            }

    def path(self, name):
        require(bool(re.fullmatch(r'[a-zA-Z0-9_.-]+', name)), 'InvalidReference', 'Invalid local reference.')
        # Connection is the only configuration consumed by the session client.
        # Historical management records keep their paths for offline recovery.
        root = self.config_root if name in ('connection', 'settings') else self.cache_root if name in ('observation', 'compatibility-check') or name.startswith('release-') else self.state_root
        return root / (name + '.json')

    def runtime_path(self, name):
        require(bool(re.fullmatch(r'[a-zA-Z0-9_.-]+', name)), 'InvalidReference', 'Invalid runtime reference.')
        return self.runtime_root / name

    def get(self, name, default=None):
        value = self._get_raw(name, default)
        if name == 'connection' and value is not None:
            self._validate_connection(value)
        return value

    def _get_raw(self, name, default=None):
        p = self.path(name)
        require(not p.is_symlink(), 'UnsafePath', 'State files must not be symbolic links.')
        return read_json(p) if p.exists() else default

    def put(self, name, value):
        if name == 'connection':
            self.save_connection(value)
        else:
            write_json(self.path(name), value)

    def save_connection(self, connection):
        """Save only the selected service and credential-provider reference."""
        self._validate_connection(connection)
        # A readable local connection file must never become a credential store.
        payload = json.dumps(connection, ensure_ascii=False, sort_keys=True, indent=2) + '\n'
        _write_private_bytes(self.path('connection'), payload.encode('utf-8'))
        self.path('.connection-migration-warning').unlink(missing_ok=True)
        self.connection_migration_warning = None

    @staticmethod
    def _validate_connection(value):
        from .credentials import validate_source
        require(isinstance(value, dict) and set(value) == {'region', 'endpoint', 'credentials'},
                'InvalidConnection', 'The connection accepts only region, endpoint and credentials.')
        require(isinstance(value['region'], str) and re.fullmatch(r'[a-z0-9-]{1,64}', value['region'])
                and isinstance(value['endpoint'], str) and re.fullmatch(r'[A-Za-z0-9.-]{1,253}', value['endpoint']),
                'InvalidConnection', 'Choose a service region and endpoint host name.')
        validate_source(value['credentials'])
        require(all(isinstance(item, str) and 0 < len(item) <= 4096 and not any(ord(char) < 32 for char in item)
                    for item in value['credentials'].values()),
                'InvalidCredentialSource', 'Credential-provider references must be nonempty text.')

    @contextmanager
    def lock(self, scope='state', reference='shared', *, shared=False, wait=False, **identifiers):
        from .concurrency import lease
        filename = scope + '-' + digest(reference) + '.lock'
        # Existing clients still use durable-state lock locations. Keep their
        # gates until active old commands finish, alongside the runtime lease.
        with ExitStack() as held:
            roots = dict.fromkeys((self.runtime_root, self.state_root, self.legacy_root))
            for root in roots:
                held.enter_context(lease(root / filename, scope, shared=shared, wait=wait, **identifiers))
            yield

    @contextmanager
    def lifecycle(self, *, exclusive=False):
        from .concurrency import lease
        with ExitStack() as held:
            for root in dict.fromkeys((self.runtime_root, self.state_root, self.legacy_root)):
                held.enter_context(lease(root / '.lock', 'shared_configuration', shared=not exclusive))
            yield

    def _lifecycle_lock(self):
        from .concurrency import lease
        return lease(self.runtime_path('.storage.lock'), 'storage_migration')

    def merge(self, name, patch):
        with self.lock('state', name, wait=True):
            value = self.get(name, {})
            value.update(patch)
            self.put(name, value)
            return value

    @staticmethod
    def _management_record(name):
        return (name in {'settings', 'setup', 'observation', 'compatibility-check',
                         'last-update', 'update-transaction', '.setup-commit', '.layout-migration'}
                or name.startswith(('plan-', 'release-')))

    def _legacy_sources(self):
        # Read a bounded set of historical files, never dependency trees or a
        # different distribution's home. Session journals already in state stay
        # untouched; only the old mixed directory needs session-file copies.
        sources = {}
        for path in self.legacy_root.glob('*.json'):
            if path == self.path('connection') or path.name.startswith('.connection-migration'):
                continue
            sources[path] = 'legacy/' + path.name
        for root, label in ((self.state_root, 'state'), (self.config_root, 'config'), (self.cache_root, 'cache')):
            for path in root.glob('*.json'):
                if self._management_record(path.stem):
                    sources.setdefault(path, label + '/' + path.name)
        require(len(sources) <= 4096, 'MigrationTooLarge',
                'The previous local state exceeds the migration limit. Preserve it before selecting a smaller set.')
        total = 0
        for path in sources:
            require(not path.is_symlink() and path.is_file(), 'UnsafePath', 'Invalid legacy state file.')
            total += path.stat().st_size
        require(total <= 64 * 1024 * 1024, 'MigrationTooLarge',
                'The previous local state exceeds the migration size limit. Preserve it before selecting a smaller set.')
        return sources

    def _migrate_legacy(self):
        sources = self._legacy_sources()
        if not sources:
            return
        snapshot = {label: _file_digest(path) for path, label in sources.items()}
        if self._get_raw('.connection-migration-complete') == snapshot:
            return
        from filelock import FileLock, Timeout
        try:
            with ExitStack() as held:
                for root in dict.fromkeys((self.legacy_root, self.state_root)):
                    for path in [root / '.lock', *sorted(root.glob('operation-*.lock'))]:
                        require(not path.is_symlink(), 'UnsafePath', 'Legacy locks must not be symbolic links.')
                        held.enter_context(FileLock(str(path), timeout=0, mode=0o600))
                self._migrate_legacy_locked(sources, snapshot)
        except Timeout:
            raise ClientError('MigrationBusy', 'A previous OpenAgent process is using local state. Retry after it completes; no state was moved.') from None

    def _migrate_legacy_locked(self, sources, snapshot):
        values = {}
        for path in sources:
            if self._management_record(path.stem) and path.stem not in ('setup', 'settings'):
                continue
            try:
                values[path] = read_json(path)
            except (ValueError, ClientError):
                if path.stem not in ('setup', 'settings'):
                    raise
                # Removed or malformed management state cannot block recovery
                # of existing conversations; keep its bytes, ask for connection.
        require(all(_file_digest(path) == snapshot[label] for path, label in sources.items()),
                'MigrationConflict', 'Previous local state changed during migration. Preserve both versions.')
        # Back up exact bytes before interpreting old management state. Removed
        # controls, setup plans and update records are retained, never executed.
        backup = private_directory(self.data_root / 'legacy-migrations' / digest(snapshot))
        for path, label in sources.items():
            target = backup / label
            private_directory(target.parent)
            if target.exists():
                require(_file_digest(target) == snapshot[label], 'MigrationConflict', 'The retained local backup changed.')
            else:
                _write_private_bytes(target, path.read_bytes())
            require(_file_digest(target) == snapshot[label], 'MigrationConflict', 'Previous local state changed before backup.')

        outputs = {}
        for path, value in values.items():
            if path.parent == self.legacy_root and not self._management_record(path.stem):
                require(path != self.path(path.stem), 'MigrationConflict', 'The connection layout is inconsistent.')
                outputs[path.stem] = value

        connection = self._get_raw('connection')
        if connection is None:
            # Extract connection only. If historical records disagree, preserve
            # both and require an explicit choice instead of changing accounts.
            candidates = []
            for path, value in values.items():
                if path.stem not in ('setup', 'settings'):
                    continue
                selected = value.get('connection') if isinstance(value, dict) else None
                try:
                    self._validate_connection(selected)
                except ClientError:
                    continue
                candidates.append(selected)
            if candidates and not all(value == candidates[0] for value in candidates):
                # A choice conflict blocks automatic selection, not setup or
                # recovery. Explicitly saving a connection resolves this state.
                write_json(self.path('.connection-migration-warning'), {'code': 'LegacyConnectionConflict'})
                candidates = []
            connection = candidates[0] if candidates else None
            if connection is not None:
                outputs['connection'] = connection

        for name, value in outputs.items():
            existing = self._get_raw(name)
            require(existing is None or existing == value, 'MigrationConflict',
                    'Current session state differs from the previous state. Preserve both versions before resolving the conflict.')
        require(all(_file_digest(path) == snapshot[label] for path, label in sources.items()),
                'MigrationConflict', 'Previous local state changed before migration. Preserve both versions.')
        for name, value in outputs.items():
            current = self._get_raw(name)
            require(current is None or current == value, 'MigrationConflict', 'Current local state changed during migration.')
            if current is None:
                self.put(name, value)
        require(all(_file_digest(path) == snapshot[label] for path, label in sources.items()),
                'MigrationConflict', 'Previous local state changed during migration. Preserve both versions.')
        # Old files remain available to the user; this marker only avoids
        # repeatedly copying an unchanged migration source on every command.
        write_json(self.path('.connection-migration-complete'), snapshot)


def authorization(reference):
    require(isinstance(reference, str) and 3 <= len(reference.strip()) <= 512
            and not (reference.strip().startswith('<') and reference.strip().endswith('>')),
            'AuthorizationRequired', 'Record the explicit user authorization for this exact change.')
    return digest(reference)


def persist_diagnostic(store, result):
    """Persist only diagnostics constructed by the validator, never raw events."""
    import time
    import uuid
    if not result.get('diagnostic') or result.get('diagnostic_ref'):
        return
    reference = 'diagnostic-' + uuid.uuid4().hex
    record = {'time': time.time(), 'code': result['code'], 'diagnostic': result['diagnostic']}
    for key in ('session_id', 'run_id'):
        if result.get(key):
            record[key] = result[key]
    try:
        store.put(reference, record)
        result['diagnostic_ref'] = reference
    except (OSError, ClientError):
        result['diagnostic_saved'] = False
