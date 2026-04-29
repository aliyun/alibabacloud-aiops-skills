#!/usr/bin/env python3
"""Upload a local file to an ADBPG knowledge base using upload_document_async_advance.

Uses the Alibaba Cloud Python SDK default credential chain (CredentialClient with no config).

Dependencies: see ../requirements.txt (skill root). Install:
    pip install -r requirements.txt
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

from alibabacloud_credentials.client import Client as CredentialClient
from alibabacloud_credentials.exceptions import CredentialException
from alibabacloud_gpdb20160503.client import Client
from alibabacloud_gpdb20160503 import models
from alibabacloud_tea_openapi.models import Config
from alibabacloud_tea_util.models import RuntimeOptions
from Tea.exceptions import TeaException, UnretryableException

USER_AGENT = "AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-postgresql-knowledgebase-ops"
DEFAULT_TIMEOUT_MS = 10_000

_MAX_REGION_LEN = 64
_MAX_DB_INSTANCE_ID_LEN = 64
_MAX_NAME_LEN = 128
_MAX_PASSWORD_LEN = 256
_MAX_FILE_PATH_LEN = 4096
_MAX_ENDPOINT_LEN = 128
_MAX_LOADER_LEN = 64

_REGION_RE = re.compile(r"^[a-z]{2}-[a-z0-9-]+$")
_DB_INSTANCE_RE = re.compile(r"^gp-[a-zA-Z0-9]+$")
_NAME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_-]*$")
_ENDPOINT_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9.-]*[a-zA-Z0-9]$|^[a-zA-Z0-9]$")
_LOADER_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_-]*$")


def _err(msg: str) -> None:
    print(msg, file=sys.stderr)


def validate_region_id(value: str) -> str | None:
    if not value or len(value) > _MAX_REGION_LEN:
        return "--region-id must be non-empty and within length limits."
    if not _REGION_RE.match(value):
        return "--region-id must match an Aliyun region id (e.g. cn-hangzhou)."
    return None


def validate_db_instance_id(value: str) -> str | None:
    if not value or len(value) > _MAX_DB_INSTANCE_ID_LEN:
        return "--db-instance-id must be non-empty and within length limits."
    if not _DB_INSTANCE_RE.match(value):
        return "--db-instance-id must match gp-xxxxxx."
    return None


def validate_namespace(value: str) -> str | None:
    if not value or len(value) > _MAX_NAME_LEN:
        return "--namespace must be non-empty and within length limits."
    if not _NAME_RE.match(value):
        return "--namespace must start with a letter; use only letters, digits, underscore, hyphen."
    return None


def validate_collection(value: str) -> str | None:
    if not value or len(value) > _MAX_NAME_LEN:
        return "--collection must be non-empty and within length limits."
    if not _NAME_RE.match(value):
        return "--collection must start with a letter; use only letters, digits, underscore, hyphen."
    return None


def validate_namespace_password(value: str) -> str | None:
    if not value or len(value) > _MAX_PASSWORD_LEN:
        return "--namespace-password length invalid."
    if "\x00" in value:
        return "--namespace-password must not contain NUL bytes."
    if not value.isprintable():
        return "--namespace-password must be printable ASCII/Unicode (no control characters)."
    return None


def validate_endpoint(value: str) -> str | None:
    if not value or len(value) > _MAX_ENDPOINT_LEN:
        return "--endpoint invalid length."
    if not _ENDPOINT_RE.match(value):
        return "--endpoint must be a hostname (letters, digits, dots, hyphens)."
    return None


def validate_document_loader_name(value: str) -> str | None:
    if not value or len(value) > _MAX_LOADER_LEN:
        return "--document-loader-name invalid length."
    if not _LOADER_RE.match(value):
        return "--document-loader-name must start with a letter; use letters, digits, underscore, hyphen."
    return None


def validate_file_path(raw: str) -> str | None:
    if not raw or len(raw) > _MAX_FILE_PATH_LEN:
        return "--file path empty or too long."
    if "\x00" in raw:
        return "--file must not contain NUL bytes."
    parts = Path(raw).parts
    if ".." in parts:
        return "--file must not contain path traversal (..)."
    try:
        p = Path(raw).expanduser()
        _ = p.resolve()
    except (OSError, ValueError):
        return "--file is not a valid path on this system."
    return None


def build_client(region_id: str, endpoint: str) -> Client:
    return Client(
        Config(
            credential=CredentialClient(),
            region_id=region_id,
            endpoint=endpoint,
            connect_timeout=DEFAULT_TIMEOUT_MS,
            read_timeout=DEFAULT_TIMEOUT_MS,
            user_agent=USER_AGENT,
        )
    )


def _format_api_error(exc: Exception) -> str:
    if isinstance(exc, UnretryableException):
        inner = getattr(exc, "inner_exception", None)
        if isinstance(inner, TeaException):
            return _format_api_error(inner)
        if inner is not None:
            return f"Request failed ({type(inner).__name__}): {inner}"
    if isinstance(exc, TeaException):
        parts = []
        if exc.code:
            parts.append(f"code={exc.code}")
        if exc.message:
            parts.append(exc.message)
        if exc.data is not None:
            parts.append(f"data={exc.data!r}")
        body = "; ".join(parts) if parts else str(exc)
        hint = (
            "Check --region-id, --db-instance-id, --namespace, passwords, and RAM permissions; "
            "verify network and endpoint reachability."
        )
        return f"API error ({body}). {hint}"
    return f"{type(exc).__name__}: {exc}"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Upload a local file to an ADBPG DocumentCollection (async job)."
    )
    parser.add_argument("--region-id", default="cn-hangzhou")
    parser.add_argument("--db-instance-id", required=True)
    parser.add_argument("--namespace", required=True)
    parser.add_argument("--namespace-password", required=True)
    parser.add_argument("--collection", required=True)
    parser.add_argument("--file", dest="file_path", required=True, help="Path to local file")
    parser.add_argument("--document-loader-name", default="ADBPGLoader")
    parser.add_argument("--chunk-size", type=int, default=500)
    parser.add_argument("--chunk-overlap", type=int, default=50)
    parser.add_argument("--endpoint", default="gpdb.aliyuncs.com")
    args = parser.parse_args()

    checks = [
        validate_region_id(args.region_id),
        validate_db_instance_id(args.db_instance_id),
        validate_namespace(args.namespace),
        validate_collection(args.collection),
        validate_namespace_password(args.namespace_password),
        validate_endpoint(args.endpoint),
        validate_document_loader_name(args.document_loader_name),
        validate_file_path(args.file_path),
    ]
    for msg in checks:
        if msg:
            _err(msg)
            return 2

    if args.chunk_size < 1 or args.chunk_size > 1_000_000:
        _err("--chunk-size must be between 1 and 1000000.")
        return 2
    if args.chunk_overlap < 0 or args.chunk_overlap > args.chunk_size:
        _err("--chunk-overlap must be >= 0 and <= --chunk-size.")
        return 2

    path = args.file_path
    if not os.path.isfile(path):
        _err(
            "Not a file or path does not exist (after validation). "
            "Pass a readable file path with --file."
        )
        return 2

    try:
        client = build_client(args.region_id, args.endpoint)
        with open(path, "rb") as fh:
            request = models.UploadDocumentAsyncAdvanceRequest(
                region_id=args.region_id,
                dbinstance_id=args.db_instance_id,
                namespace=args.namespace,
                namespace_password=args.namespace_password,
                collection=args.collection,
                file_name=os.path.basename(path),
                file_url_object=fh,
                document_loader_name=args.document_loader_name,
                chunk_size=args.chunk_size,
                chunk_overlap=args.chunk_overlap,
            )
            runtime = RuntimeOptions(
                connect_timeout=DEFAULT_TIMEOUT_MS,
                read_timeout=DEFAULT_TIMEOUT_MS,
            )
            response = client.upload_document_async_advance(request, runtime)
    except FileNotFoundError:
        _err("File not found after open. Check --file.")
        return 2
    except PermissionError:
        _err("Permission denied reading file. Fix filesystem permissions or choose another path.")
        return 2
    except OSError as e:
        _err(f"Cannot read file: {type(e).__name__}. Check path and permissions.")
        return 2
    except CredentialException:
        _err(
            "Credential resolution failed. Configure the default credential chain outside this session "
            "(for example `aliyun configure` or env-based setup per Alibaba Cloud docs), then retry. "
            "Do not paste secrets into logs."
        )
        return 3
    except UnretryableException as e:
        _err(_format_api_error(e))
        return 4
    except TeaException as e:
        _err(_format_api_error(e))
        return 4
    except Exception as e:
        msg_l = str(e).lower()
        if "timeout" in msg_l or "timed out" in msg_l:
            _err(
                "Network or timeout error. Check connectivity, firewall, and try again; "
                "increase timeouts in this script if uploads are large."
            )
            return 5
        _err(f"Unexpected error: {type(e).__name__}. Retry or enable verbose logging outside production.")
        return 1

    print(f"JobId: {response.body.job_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
