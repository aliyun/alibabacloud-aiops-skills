"""Injected query boundary, read modes, SPL escaping and row decoding."""

import unicodedata
from enum import IntEnum
from typing import Protocol

from .errors import CatalogError

Row = dict[str, str]


class ReadMode(IntEnum):
    OVERVIEW = 0
    COMPLETE = 1


class QueryFunc(Protocol):
    def __call__(self, spl: str, mode: ReadMode) -> list[Row]: ...


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
