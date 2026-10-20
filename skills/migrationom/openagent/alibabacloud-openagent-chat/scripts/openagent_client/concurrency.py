"""Process leases; lock files live outside replaceable packages and runtimes."""
import contextlib
import hashlib
import os
from pathlib import Path


class Busy(Exception):
    def __init__(self, scope, **identifiers):
        self.scope, self.identifiers = scope, identifiers
        super().__init__(scope)


@contextlib.contextmanager
def lease(path, scope, *, shared=False, wait=False, **identifiers):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if path.is_symlink():
        raise PermissionError('Unsafe lock path')
    fd = os.open(path, os.O_CREAT | os.O_RDWR | getattr(os, 'O_NOFOLLOW', 0), 0o600)
    try:
        stat = os.fstat(fd)
        if os.name == 'posix' and (stat.st_uid != os.getuid() or stat.st_mode & 0o022):
            raise PermissionError('Unsafe lock permissions')
        if os.name == 'posix':
            import fcntl
            try:
                fcntl.flock(fd, (fcntl.LOCK_SH if shared else fcntl.LOCK_EX) | (0 if wait else fcntl.LOCK_NB))
            except BlockingIOError:
                raise Busy(scope, **identifiers) from None
        elif os.name == 'nt':
            windows_lock(fd, shared, wait, scope, identifiers)
        else:
            raise RuntimeError('Unsupported process locking platform')
        yield fd
    finally:
        os.close(fd)


def installation_paths(package):
    from .common import resolve_paths
    home = resolve_paths()['runtime']
    key = hashlib.sha256(str(Path(package).resolve()).encode()).hexdigest()
    # Packages in one storage namespace share the runtime installation gate.
    return home / '.bootstrap.lock', home / ('installation-' + key + '.lock')


@contextlib.contextmanager
def installation(package, *, exclusive=False):
    from .common import APP_NAME, private_directory, resolve_paths
    paths = resolve_paths()
    if paths.get('runtime_parent') is not None:
        private_directory(paths['runtime_parent'])
    private_directory(paths['runtime'])
    runtime, package_lock = installation_paths(package)
    with contextlib.ExitStack() as held:
        # The production namespace retains the historical interpreter gate.
        # A dedicated distribution never locks or reads production storage.
        legacy = Path.home() / '.local/share/openagent'
        if APP_NAME == 'openagent' and legacy.exists():
            private_directory(legacy)
            held.enter_context(lease(legacy / '.bootstrap.lock', 'installation', shared=not exclusive))
        runtime_fd = held.enter_context(lease(runtime, 'installation', shared=not exclusive))
        package_fd = held.enter_context(lease(package_lock, 'installation', shared=not exclusive))
        yield (runtime_fd, package_fd)


def windows_lock(fd, shared, wait, scope, identifiers):
    import ctypes
    from ctypes import wintypes
    import msvcrt
    class Overlapped(ctypes.Structure):
        _fields_ = [('Internal', ctypes.c_size_t), ('InternalHigh', ctypes.c_size_t),
                    ('Offset', wintypes.DWORD), ('OffsetHigh', wintypes.DWORD),
                    ('hEvent', wintypes.HANDLE)]
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    lock = kernel.LockFileEx
    lock.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD,
                     wintypes.DWORD, wintypes.DWORD, ctypes.POINTER(Overlapped)]
    lock.restype = wintypes.BOOL
    overlapped = Overlapped()
    flags = (0 if shared else 2) | (0 if wait else 1)
    if not lock(msvcrt.get_osfhandle(fd), flags, 0, 1, 0, ctypes.byref(overlapped)):
        error = ctypes.get_last_error()
        if error == 33:
            raise Busy(scope, **identifiers)
        raise ctypes.WinError(error)
