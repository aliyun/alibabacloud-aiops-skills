from __future__ import annotations

import argparse
import fcntl
import json
import os
import shutil
import stat
import sys
import tempfile
import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

try:
    from .agenthub_command import format_agenthub_command
except ImportError:  # pragma: no cover - direct script execution
    from agenthub_command import format_agenthub_command


PROVIDER_ALIYUN_CLI = "aliyun_cli"
PROVIDER_AGENTHUB_CONFIG = "agenthub_config"

SOURCE_ALIYUN_CLI = "aliyun_cli"
SOURCE_AGENTHUB_OAUTH = "agenthub_oauth"
CREDENTIAL_SOURCE_CHOICES = (SOURCE_ALIYUN_CLI, SOURCE_AGENTHUB_OAUTH)

DEFAULT_CLI_PROFILE = "default"
DEFAULT_OAUTH_PROFILE = "aliyun_agenthub_oauth"
CLI_PROFILE_ENV = "ALIYUN_AGENTHUB_CLI_PROFILE"


class CredentialSourceError(RuntimeError):
    pass


@dataclass(frozen=True)
class CredentialSource:
    provider: str
    profile_name: str
    mode: str
    config_file: str
    locked: bool = False


def default_cli_config_path() -> Path:
    return Path(os.environ.get("ALIYUN_CONFIG_FILE", "~/.aliyun/config.json")).expanduser()


def default_private_config_path() -> Path:
    return Path(os.environ.get("ALIYUN_AGENTHUB_CONFIG_FILE", "~/.aliyun_agenthub/config.json")).expanduser()


def assert_requested_source(
    cache_file: Path,
    requested_source: str | None,
) -> CredentialSource | None:
    locked = _source_from_cache(cache_file)
    if not locked:
        if cache_file.exists():
            raise CredentialSourceError(
                "AgentHub 凭证缓存缺少来源锁；为避免复用来源不明的 Token 或静默切换云账号，"
                "已拒绝继续。请仅由用户在本地终端手动移除该凭证缓存，"
                "再重新运行 auth_init 并明确选择凭证来源。"
            )
        return None
    if not requested_source:
        return locked
    matches = (
        requested_source == SOURCE_ALIYUN_CLI
        and locked.provider == PROVIDER_ALIYUN_CLI
    ) or (
        requested_source == SOURCE_AGENTHUB_OAUTH
        and locked.provider == PROVIDER_AGENTHUB_CONFIG
        and _canonical_mode(locked.mode) == "OAuth"
    )
    if not matches:
        raise CredentialSourceError(
            "AgentHub 已锁定的凭证来源与本次显式选择不一致；"
            "为避免静默切换到其他云账号，已拒绝自动切换。"
            "请继续使用原来源；如需明确改用其他来源，请先由用户手动移除凭证缓存，"
            "再重新运行 auth_init。"
        )
    return locked


def select_credential_source(
    *,
    cache_file: Path,
    cli_config_path: Path | None = None,
    private_config_path: Path | None = None,
    explicit_cli_profile: str | None = None,
    requested_source: str | None = None,
    cli_available: bool | None = None,
) -> CredentialSource:
    cli_path = cli_config_path or default_cli_config_path()
    private_path = private_config_path or default_private_config_path()
    requested_cli_profile = (
        explicit_cli_profile or os.environ.get(CLI_PROFILE_ENV, "")
    ).strip() or DEFAULT_CLI_PROFILE
    cli_ok = _cli_available(cli_available)

    if requested_source and requested_source not in CREDENTIAL_SOURCE_CHOICES:
        raise CredentialSourceError(f"unsupported credential source: {requested_source}")

    locked = assert_requested_source(cache_file, requested_source)
    if locked and _source_is_available(locked, cli_path, private_path, cli_ok):
        # Alibaba Cloud CLI has no supported environment variable for an
        # alternate profile file.  A locked CLI source therefore follows the
        # current official CLI config path; private AgentHub profiles can keep
        # their explicitly locked file.
        effective_config_file = (
            str(cli_path)
            if locked.provider == PROVIDER_ALIYUN_CLI
            else (locked.config_file or str(private_path))
        )
        return CredentialSource(
            provider=locked.provider,
            profile_name=locked.profile_name,
            mode=locked.mode,
            config_file=effective_config_file,
            locked=True,
        )
    if locked:
        raise CredentialSourceError(
            "AgentHub 已锁定的凭证来源当前不可用；为避免静默切换到其他云账号，"
            "已拒绝自动切换。请在本地终端恢复原 profile 后重试；如需明确改用其他来源，"
            f"请先由用户手动移除凭证缓存 `{cache_file}`，再重新运行 auth_init。"
        )

    if requested_source is None:
        raise CredentialSourceError(
            build_setup_guidance(
                cli_available=cli_ok,
                cli_config_path=cli_path,
                private_config_path=private_path,
            )
        )

    if requested_source == SOURCE_ALIYUN_CLI:
        if not cli_ok:
            raise CredentialSourceError(
                build_setup_guidance(
                    cli_available=False,
                    cli_config_path=cli_path,
                    private_config_path=private_path,
                    explicit_cli_profile=requested_cli_profile,
                    requested_source=requested_source,
                )
            )
        source = _select_cli_source(cli_path, requested_cli_profile)
        if source:
            return source
        raise CredentialSourceError(
            build_setup_guidance(
                cli_available=True,
                cli_config_path=cli_path,
                private_config_path=private_path,
                explicit_cli_profile=requested_cli_profile,
                requested_source=requested_source,
            )
        )

    source = _select_private_oauth_source(private_path)
    if source:
        return source
    raise CredentialSourceError(
        build_setup_guidance(
            cli_available=cli_ok,
            cli_config_path=cli_path,
            private_config_path=private_path,
            explicit_cli_profile=requested_cli_profile,
            requested_source=requested_source,
        )
    )


def build_setup_guidance(
    *,
    cli_available: bool | None = None,
    cli_config_path: Path | None = None,
    private_config_path: Path | None = None,
    explicit_cli_profile: str | None = None,
    requested_source: str | None = None,
) -> str:
    cli_path = cli_config_path or default_cli_config_path()
    private_path = private_config_path or default_private_config_path()
    cli_ok = _cli_available(cli_available)
    selected_cli_profile = (
        explicit_cli_profile or os.environ.get(CLI_PROFILE_ENV, "")
    ).strip() or DEFAULT_CLI_PROFILE
    python_executable = os.environ.get("AGENTHUB_PYTHON") or sys.executable
    cli_auth_command = format_agenthub_command(
        "auth_init",
        "--credential-source",
        SOURCE_ALIYUN_CLI,
        python_executable=python_executable,
    )
    oauth_auth_command = format_agenthub_command(
        "auth_init",
        "--credential-source",
        SOURCE_AGENTHUB_OAUTH,
        python_executable=python_executable,
    )
    configure_oauth_command = format_agenthub_command(
        "configure_oauth",
        "--profile",
        DEFAULT_OAUTH_PROFILE,
        python_executable=python_executable,
    )

    if requested_source == SOURCE_ALIYUN_CLI:
        cli_status = "已检测到 aliyun CLI。" if cli_ok else "当前未检测到 aliyun CLI。"
        return (
            f"AgentHub CLI 凭证未就绪：将使用 profile `{selected_cli_profile}`，"
            f"但当前无法通过该 profile 完成初始化。配置文件：`{cli_path}`。\n\n"
            f"{cli_status}\n"
            f"如需使用其他 CLI profile，请在本地终端设置 `{CLI_PROFILE_ENV}` 后重试；"
            f"未设置时固定使用 `{DEFAULT_CLI_PROFILE}`。\n\n"
            f"重试命令：\n  {cli_auth_command}\n\n"
            f"也可以明确改用 AgentHub OAuth：\n  {oauth_auth_command}\n\n"
            "Aliyun CLI 负责解释 profile 的认证 mode 和凭证链。"
        )

    if requested_source == SOURCE_AGENTHUB_OAUTH:
        return (
            "AgentHub OAuth 凭证未就绪：未找到可用的 AgentHub OAuth profile。\n"
            f"私有配置文件：`{private_path}`。\n\n"
            "请仅由用户在本地交互终端依次执行：\n"
            f"  {configure_oauth_command}\n"
            f"  {oauth_auth_command}\n\n"
            "端侧 Agent 不得代执行配置命令、打开授权流程或读取配置文件。"
        )

    cli_status = "已检测到 aliyun CLI。" if cli_ok else "当前未检测到 aliyun CLI。"
    return (
        "AgentHub 首次认证需要用户明确选择凭证来源；当前尚未选择，未发起认证请求。\n\n"
        f"{cli_status}\n"
        f"方式一：复用 aliyun CLI profile（默认 `{DEFAULT_CLI_PROFILE}`；"
        f"可通过 `{CLI_PROFILE_ENV}` 指定其他名称）：\n  {cli_auth_command}\n\n"
        "方式二：使用 AgentHub OAuth profile：\n"
        f"  {oauth_auth_command}\n\n"
        "所有凭证配置和 OAuth 授权必须由用户在本地交互终端手动完成。"
    )


def source_to_cache_payload(source: CredentialSource) -> dict[str, Any]:
    return {
        "provider": source.provider,
        "profile": source.profile_name,
        "mode": source.mode,
        "config_file": source.config_file,
        "selected_at": int(time.time()),
    }


def _select_cli_source(config_path: Path, requested_profile: str | None) -> CredentialSource | None:
    config = _load_json_config(config_path)
    profile_name = requested_profile or DEFAULT_CLI_PROFILE
    profile = _profiles_by_name(config).get(profile_name)
    if profile is None:
        return None
    return CredentialSource(
        provider=PROVIDER_ALIYUN_CLI,
        profile_name=profile_name,
        mode=_canonical_mode(profile.get("mode") or "AK"),
        config_file=str(config_path),
    )


def _select_private_oauth_source(config_path: Path) -> CredentialSource | None:
    config = _load_json_config(config_path, private=True)
    profiles = _profiles_by_name(config)
    current = str(config.get("current") or "").strip()
    for name in dict.fromkeys((current, DEFAULT_OAUTH_PROFILE)):
        if not name:
            continue
        profile = profiles.get(name)
        if not _private_profile_usable(profile, allowed_modes={"oauth"}):
            continue
        return CredentialSource(
            provider=PROVIDER_AGENTHUB_CONFIG,
            profile_name=name,
            mode="OAuth",
            config_file=str(config_path),
        )
    return None


def _source_from_cache(cache_file: Path) -> CredentialSource | None:
    try:
        fd = _open_owned_regular_file(cache_file, private=True)
    except FileNotFoundError:
        return None
    except (OSError, CredentialSourceError) as exc:
        raise CredentialSourceError(
            "AgentHub 凭证缓存不安全或不可读；为避免静默切换云账号，已拒绝自动切换。"
        ) from exc
    try:
        with os.fdopen(fd, "r", encoding="utf-8") as stream:
            fd = -1
            data = json.load(stream)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CredentialSourceError(
            "AgentHub 凭证缓存格式无效；为避免静默切换云账号，已拒绝自动切换。"
        ) from exc
    finally:
        if fd >= 0:
            os.close(fd)
    if not isinstance(data, dict):
        raise CredentialSourceError(
            "AgentHub 凭证缓存结构无效；为避免静默切换云账号，已拒绝自动切换。"
        )
    if "credential_source" not in data:
        return None
    source = data.get("credential_source")
    if not isinstance(source, dict):
        raise CredentialSourceError(
            "AgentHub 凭证缓存中的来源锁无效；为避免静默切换云账号，已拒绝自动切换。"
        )
    provider = str(source.get("provider") or "").strip()
    profile_name = str(source.get("profile") or source.get("profile_name") or "").strip()
    mode = str(source.get("mode") or "").strip()
    config_file = str(source.get("config_file") or "").strip()
    if provider not in {PROVIDER_ALIYUN_CLI, PROVIDER_AGENTHUB_CONFIG} or not profile_name or not mode:
        raise CredentialSourceError(
            "AgentHub 凭证缓存中的来源锁无效；为避免静默切换云账号，已拒绝自动切换。"
        )
    return CredentialSource(
        provider=provider,
        profile_name=profile_name,
        mode=_canonical_mode(mode),
        config_file=config_file,
        locked=True,
    )


def _source_is_available(
    source: CredentialSource,
    cli_config_path: Path,
    private_config_path: Path,
    cli_available: bool,
) -> bool:
    if source.provider == PROVIDER_ALIYUN_CLI:
        if not cli_available:
            return False
        config = _load_json_config(cli_config_path)
        profile = _profiles_by_name(config).get(source.profile_name)
        return profile is not None and _same_mode(profile, source.mode)
    if source.provider == PROVIDER_AGENTHUB_CONFIG:
        config_path = Path(source.config_file).expanduser() if source.config_file else private_config_path
        config = _load_json_config(config_path, private=True)
        profile = _profiles_by_name(config).get(source.profile_name)
        return _private_profile_usable(profile, allowed_modes=None) and _same_mode(profile, source.mode)
    return False


def _private_profile_usable(
    profile: dict[str, Any] | None,
    *,
    allowed_modes: set[str] | None,
) -> bool:
    if not profile:
        return False
    mode = str(profile.get("mode") or "AK").lower()
    if allowed_modes is not None and mode not in allowed_modes:
        return False
    if mode == "ak":
        return bool(profile.get("access_key_id") and profile.get("access_key_secret"))
    if mode == "oauth":
        if str(profile.get("oauth_site_type") or "").upper() != "CN":
            return False
        if profile.get("oauth_access_token") or profile.get("oauth_refresh_token"):
            return True
        return bool(
            profile.get("access_key_id")
            and profile.get("access_key_secret")
            and profile.get("sts_token")
            and _parse_expiration(profile.get("sts_expiration"))
        )
    return False


def _same_mode(profile: dict[str, Any] | None, mode: str) -> bool:
    return bool(profile and _canonical_mode(profile.get("mode") or "AK") == _canonical_mode(mode))


def _load_json_config(path: Path, *, private: bool = False) -> dict[str, Any]:
    try:
        fd = _open_owned_regular_file(path, private=private)
    except (FileNotFoundError, OSError, CredentialSourceError):
        return {}
    try:
        with os.fdopen(fd, "r", encoding="utf-8") as stream:
            fd = -1
            data = json.load(stream)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {}
    finally:
        if fd >= 0:
            os.close(fd)
    return data if isinstance(data, dict) else {}


def _open_owned_regular_file(
    path: Path,
    *,
    private: bool,
    repair_private_mode: bool = False,
) -> int:
    before = path.lstat()
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags)
    try:
        info = os.fstat(fd)
        unsafe = (
            not stat.S_ISREG(info.st_mode)
            or info.st_uid != os.getuid()
            or (info.st_dev, info.st_ino) != (before.st_dev, before.st_ino)
        )
        if private:
            unsafe = unsafe or info.st_nlink != 1
        if unsafe:
            raise CredentialSourceError(f"unsafe AgentHub config file: {path}")
        if private and stat.S_IMODE(info.st_mode) != 0o600:
            if not repair_private_mode:
                raise CredentialSourceError(f"unsafe AgentHub config file: {path}")
            os.fchmod(fd, 0o600)
            repaired = os.fstat(fd)
            if stat.S_IMODE(repaired.st_mode) != 0o600:
                raise CredentialSourceError(f"cannot repair AgentHub config file mode: {path}")
        return fd
    except BaseException:
        os.close(fd)
        raise


def _profiles_by_name(config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for profile in config.get("profiles", []):
        if not isinstance(profile, dict):
            continue
        name = str(profile.get("name") or "").strip()
        if name:
            result[name] = profile
    return result


def _cli_available(value: bool | None) -> bool:
    if value is not None:
        return value
    return shutil.which("aliyun") is not None


def _canonical_mode(mode: Any) -> str:
    normalized = str(mode or "AK").strip().lower()
    if normalized == "ststoken":
        return "StsToken"
    if normalized == "ramrolearn":
        return "RamRoleArn"
    if normalized == "oauth":
        return "OAuth"
    return "AK" if normalized == "ak" else str(mode or "AK")


def _parse_expiration(value: Any) -> float | None:
    if value is None:
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if time.time() < parsed - 60 else None


def _select_command(args: argparse.Namespace) -> int:
    try:
        source = select_credential_source(
            cache_file=Path(args.cache_file).expanduser(),
            cli_config_path=Path(args.cli_config_file).expanduser(),
            private_config_path=Path(args.private_config_file).expanduser(),
            requested_source=args.credential_source,
        )
    except CredentialSourceError as exc:
        print(str(exc), file=sys.stderr)
        return 20
    json.dump(asdict(source), sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


def _assert_source_command(args: argparse.Namespace) -> int:
    try:
        assert_requested_source(
            Path(args.cache_file).expanduser(),
            args.credential_source,
        )
    except CredentialSourceError as exc:
        print(str(exc), file=sys.stderr)
        return 20
    return 0


def _cache_update_command(args: argparse.Namespace) -> int:
    try:
        updates = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"invalid cache update JSON: {exc}", file=sys.stderr)
        return 2
    if not isinstance(updates, dict):
        print("cache update JSON must be an object", file=sys.stderr)
        return 2
    try:
        update_credential_cache(Path(args.cache_file).expanduser(), updates=updates)
    except (OSError, CredentialSourceError) as exc:
        print(f"cannot update AgentHub credential cache: {exc}", file=sys.stderr)
        return 1
    return 0


def _cache_clear_token_command(args: argparse.Namespace) -> int:
    try:
        update_credential_cache(
            Path(args.cache_file).expanduser(),
            updates={},
            remove_fields=("token_response", "token_obtained_at", "token_expires_in"),
        )
    except (OSError, CredentialSourceError) as exc:
        print(f"cannot clear AgentHub token cache: {exc}", file=sys.stderr)
        return 1
    return 0


def _cache_repair_command(args: argparse.Namespace) -> int:
    try:
        repair_credential_cache(Path(args.cache_file).expanduser())
    except (OSError, CredentialSourceError) as exc:
        print(f"cannot repair AgentHub credential cache: {exc}", file=sys.stderr)
        return 1
    return 0


def update_credential_cache(
    cache_file: Path,
    *,
    updates: dict[str, Any],
    remove_fields: tuple[str, ...] = (),
) -> None:
    cache_file.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    _secure_private_directory(cache_file.parent)
    with _cache_lock(cache_file):
        try:
            fd = _open_owned_regular_file(
                cache_file,
                private=True,
                repair_private_mode=True,
            )
        except FileNotFoundError:
            data = {}
        else:
            try:
                with os.fdopen(fd, "r", encoding="utf-8") as stream:
                    fd = -1
                    data = json.load(stream)
            except (UnicodeDecodeError, json.JSONDecodeError):
                data = {}
            finally:
                if fd >= 0:
                    os.close(fd)
            if not isinstance(data, dict):
                data = {}
        for field in remove_fields:
            data.pop(field, None)
        data.update(updates)
        _atomic_write_json(cache_file, data)


def repair_credential_cache(cache_file: Path) -> None:
    """Safely migrate a current-user legacy cache from permissive modes."""
    cache_file.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    _secure_private_directory(cache_file.parent)
    with _cache_lock(cache_file):
        try:
            fd = _open_owned_regular_file(
                cache_file,
                private=True,
                repair_private_mode=True,
            )
        except FileNotFoundError:
            return
        else:
            os.close(fd)


def _secure_private_directory(path: Path) -> None:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    flags |= getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags)
    try:
        info = os.fstat(fd)
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid():
            raise CredentialSourceError(f"unsafe cache directory: {path}")
        os.fchmod(fd, 0o700)
    finally:
        os.close(fd)


@contextmanager
def _cache_lock(cache_file: Path):
    lock_file = cache_file.with_name(f".{cache_file.name}.lock")
    try:
        before = lock_file.lstat()
    except FileNotFoundError:
        before = None
    flags = os.O_RDWR | os.O_CREAT
    flags |= getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(lock_file, flags, 0o600)
    try:
        info = os.fstat(fd)
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_uid != os.getuid()
            or info.st_nlink != 1
            or (
                before is not None
                and (info.st_dev, info.st_ino) != (before.st_dev, before.st_ino)
            )
        ):
            raise CredentialSourceError(f"unsafe cache lock: {lock_file}")
        after = lock_file.lstat()
        if (
            stat.S_ISLNK(after.st_mode)
            or (info.st_dev, info.st_ino) != (after.st_dev, after.st_ino)
        ):
            raise CredentialSourceError(f"unsafe cache lock: {lock_file}")
        os.fchmod(fd, 0o600)
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)


def _atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    try:
        fd = _open_owned_regular_file(path, private=True)
    except FileNotFoundError:
        pass
    else:
        os.close(fd)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.tmp.", dir=path.parent)
    temporary_path = Path(temporary_name)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(data, stream, ensure_ascii=False, separators=(",", ":"))
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, path)
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        temporary_path.unlink(missing_ok=True)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Select AgentHub credential source.")
    subcommands = parser.add_subparsers(dest="command", required=True)
    select = subcommands.add_parser("select", help="Select CLI or private AgentHub profile.")
    select.add_argument("--cache-file", required=True)
    select.add_argument("--cli-config-file", default=str(default_cli_config_path()))
    select.add_argument("--private-config-file", default=str(default_private_config_path()))
    select.add_argument("--credential-source", choices=CREDENTIAL_SOURCE_CHOICES)
    assert_source = subcommands.add_parser("assert-source", help=argparse.SUPPRESS)
    assert_source.add_argument("--cache-file", required=True)
    assert_source.add_argument(
        "--credential-source",
        choices=CREDENTIAL_SOURCE_CHOICES,
    )
    cache_update = subcommands.add_parser("cache-update", help=argparse.SUPPRESS)
    cache_update.add_argument("--cache-file", required=True)
    cache_clear = subcommands.add_parser("cache-clear-token", help=argparse.SUPPRESS)
    cache_clear.add_argument("--cache-file", required=True)
    cache_repair = subcommands.add_parser("cache-repair", help=argparse.SUPPRESS)
    cache_repair.add_argument("--cache-file", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    if args.command == "select":
        return _select_command(args)
    if args.command == "assert-source":
        return _assert_source_command(args)
    if args.command == "cache-update":
        return _cache_update_command(args)
    if args.command == "cache-clear-token":
        return _cache_clear_token_command(args)
    if args.command == "cache-repair":
        return _cache_repair_command(args)
    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
