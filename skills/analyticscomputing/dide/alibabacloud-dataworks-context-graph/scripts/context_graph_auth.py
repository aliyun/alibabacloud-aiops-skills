"""Parse explicit credential files as data without execution or automatic local discovery."""

import json
import os
import stat
import unicodedata

from context_graph_contract import SkillError


CREDENTIAL_NAMES = (
    "ALIBABA_CLOUD_ACCESS_KEY_ID", "ALIBABA_CLOUD_ACCESS_KEY_SECRET", "ALIBABA_CLOUD_SECURITY_TOKEN",
)
FAMILIES = (
    ("AccessKeyId", "AccessKeySecret", "SecurityToken"),
    CREDENTIAL_NAMES,
    ("accessKeyId", "accessKeySecret", "securityToken"),
)
MAX_CREDENTIAL_BYTES = 64 * 1024
FILE_ERROR = "The explicit credentials file must be valid UTF-8 JSON or simple key=value in a regular file, at most 64 KiB, with complete credentials from one naming family."


def valid_secret(value):
    return isinstance(value, str) and bool(value) and not any(
        char.isspace() or unicodedata.category(char).startswith("C") for char in value)


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError
        result[key] = value
    return result


def _parse(text):
    if text.lstrip().startswith("{"):
        return json.loads(text, object_pairs_hook=_pairs)
    items = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        key, separator, value = stripped.partition("=")
        if not separator:
            raise ValueError
        key, value = key.strip(), value.strip()
        if value.startswith(("\"", "'")):
            if len(value) < 2 or value[-1] != value[0]:
                raise ValueError
            value = value[1:-1]
        elif value.endswith(("\"", "'")):
            raise ValueError
        items.append((key, value))
    return _pairs(items)


def read_credentials_file(path):
    """Replace the complete identity from the file; a long-lived AccessKey clears inherited STS with an empty Token."""
    descriptor = None
    try:
        flags = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0)
        descriptor = os.open(path, flags)
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_CREDENTIAL_BYTES:
            raise ValueError
        with os.fdopen(descriptor, "rb") as stream:
            descriptor = None
            raw = stream.read(MAX_CREDENTIAL_BYTES + 1)
        if len(raw) > MAX_CREDENTIAL_BYTES:
            raise ValueError
        values = _parse(raw.decode("utf-8"))
        if not isinstance(values, dict):
            raise ValueError
        family = next((names for names in FAMILIES if set(values) in (set(names[:2]), set(names))), None)
        if family is None or not all(valid_secret(values[key]) for key in values):
            raise ValueError
        return {target: values.get(source, "") for source, target in zip(family, CREDENTIAL_NAMES)}
    except (OSError, UnicodeError, ValueError, TypeError, RecursionError):
        # Exclude paths, values, and parser exceptions to avoid exposing user configuration.
        raise SkillError("CredentialsFileInvalid", FILE_ERROR) from None
    finally:
        if descriptor is not None:
            os.close(descriptor)


def credential_shape(environ):
    values = [environ.get(key, "") for key in CREDENTIAL_NAMES]
    if not any(values):
        return "not_configured"
    return "configured" if all(valid_secret(value) for value in values[:2]) and (
        not values[2] or valid_secret(values[2])) else "invalid"
