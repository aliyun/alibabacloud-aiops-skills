"""Injected query boundary, read modes, SPL escaping and row decoding."""

import unicodedata
from enum import IntEnum
from typing import Protocol

from .errors import CatalogError

Row = dict[str, str]


class ReadMode(IntEnum):
    OVERVIEW = 0
    COMPLETE = 1


class ModelQuery(Protocol):
    """An SPL query already bound to one Context Model or Project Source Model."""
    def __call__(self, spl: str, mode: ReadMode) -> list[Row]: ...


class ModelTransport(Protocol):
    """Injected request transport shared by both model API clients."""
    def request(self, action, method, path, query=None, body=None, project=None): ...


def literal(value):
    if any(unicodedata.category(c) == "Cc" for c in value):
        raise CatalogError("InvalidParameter", "Catalog value contains a control character")
    return value.replace("'", "''")


def decode_rows(header, data, mode=ReadMode.COMPLETE):
    """Check table structure; service completeness is checked by the adapter."""
    complete = mode == ReadMode.COMPLETE
    if not isinstance(header, list) or not isinstance(data, list):
        raise CatalogError("IncompleteCatalogRead", "Invalid model table envelope")
    if any(h is not None and not isinstance(h, str) for h in header):
        raise CatalogError("IncompleteCatalogRead", "Invalid model column name")
    if complete and (any(not h for h in header) or len(set(header)) != len(header)):
        raise CatalogError("IncompleteCatalogRead", "Missing or duplicate model column")
    rows = []
    for row in data:
        if (not isinstance(row, list) or (complete and len(row) != len(header))
                or any(v is not None and not isinstance(v, str) for v in row)):
            raise CatalogError("IncompleteCatalogRead", "Invalid model row")
        rows.append({h: (row[i] or "") if i < len(row) else "" for i, h in enumerate(header) if h})
    return rows


def decode_model_rows(body, mode=ReadMode.COMPLETE):
    if not isinstance(body, dict):
        raise CatalogError("IncompleteCatalogRead", "Model response must be an object")
    status = body.get("responseStatus") or {}
    if mode == ReadMode.COMPLETE and (not isinstance(status, dict) or
            status.get("result") != "Success" or status.get("level") != "Info"):
        raise CatalogError("IncompleteCatalogRead", "Model response does not certify a complete successful read")
    return decode_rows(body.get("header"), body.get("data"), mode)
