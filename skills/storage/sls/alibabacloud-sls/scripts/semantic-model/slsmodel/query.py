"""Validate complete model query responses and decode their table rows."""

from .errors import CatalogError


def decode_rows(header, data):
    """Check table structure; service completeness is checked by the adapter."""
    if not isinstance(header, list) or not isinstance(data, list):
        raise CatalogError("IncompleteCatalogRead", "Invalid model table envelope")
    if any(h is not None and not isinstance(h, str) for h in header):
        raise CatalogError("IncompleteCatalogRead", "Invalid model column name")
    if any(not h for h in header) or len(set(header)) != len(header):
        raise CatalogError("IncompleteCatalogRead", "Missing or duplicate model column")
    rows = []
    for row in data:
        if (
            not isinstance(row, list)
            or len(row) != len(header)
            or any(v is not None and not isinstance(v, str) for v in row)
        ):
            raise CatalogError("IncompleteCatalogRead", "Invalid model row")
        rows.append({h: (row[i] or "") if i < len(row) else "" for i, h in enumerate(header) if h})
    return rows


def decode_model_rows(body):
    if not isinstance(body, dict):
        raise CatalogError("IncompleteCatalogRead", "Model response must be an object")
    status = body.get("responseStatus") or {}
    if (
        not isinstance(status, dict)
        or status.get("result") != "Success"
        or status.get("level") != "Info"
    ):
        raise CatalogError(
            "IncompleteCatalogRead", "Model response does not certify a complete successful read"
        )
    return decode_rows(body.get("header"), body.get("data"))
