"""JSON Schema validation + forbidden-field guard.

Two checks per call:
  1. spec.input_schema (jsonschema draft-07) — standard validation
  2. spec.forbidden_fields — explicit denylist with reason
"""
from __future__ import annotations

from typing import Any, Dict, List

try:
    import jsonschema
    from jsonschema import Draft7Validator
except ImportError:  # pragma: no cover - handled by -doctor
    jsonschema = None
    Draft7Validator = None  # type: ignore

from .errors import ForbiddenField, MissingField, ValidationFailed


def validate_input(args: Dict[str, Any], spec: Dict[str, Any]) -> None:
    """Validate args against spec.input_schema and forbidden_fields.

    Raises:
      MissingField     — required field absent
      ForbiddenField   — denylist hit
      ValidationFailed — any other schema violation
    """
    _check_forbidden(args, spec)
    _check_schema(args, spec.get("input_schema") or {}, op_name=spec.get("name", "?"))


def validate_output(result: Any, spec: Dict[str, Any]) -> None:
    """Validate Op result against output_schema. Drift becomes OUTPUT_SCHEMA_DRIFT."""
    schema = spec.get("output_schema")
    if not schema or jsonschema is None:
        return
    try:
        Draft7Validator(schema).validate(result)
    except jsonschema.ValidationError as e:  # pragma: no cover
        from .errors import OutputSchemaDrift

        raise OutputSchemaDrift(
            f"Return value does not match output_schema: {e.message}",
            fix_hint=(
                f"Backend schema may have drifted; check ops/{spec.get('name')}.json "
                f"last_verified field for expiry"
            ),
        )


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------
def _check_forbidden(args: Dict[str, Any], spec: Dict[str, Any]) -> None:
    forbidden = spec.get("forbidden_fields") or []
    for entry in forbidden:
        field = entry.get("field")
        if field and field in args:
            raise ForbiddenField(
                f"Field {field} is forbidden ({spec.get('name')})",
                fix_hint=entry.get("reason", "Run cadt_deploy_on_aliyun -d to see why"),
                fields=[{"name": field, "reason": entry.get("reason", "")}],
            )


def _check_schema(args: Dict[str, Any], schema: Dict[str, Any], *, op_name: str) -> None:
    if jsonschema is None:
        raise ValidationFailed(
            "jsonschema library not installed; cannot validate input",
            fix_hint="pip install 'jsonschema>=4.0'",
        )

    validator = Draft7Validator(schema)
    errors = sorted(validator.iter_errors(args), key=lambda e: list(e.path))
    if not errors:
        return

    # Categorize the first error precisely; bundle all into fields[].
    first = errors[0]
    fields = [_field_from_error(e) for e in errors]

    if first.validator == "required":
        missing = [m for m in first.message.split("'") if m and m != " is a required property"]
        missing_name = missing[1] if len(missing) >= 2 else "(unknown)"
        raise MissingField(
            f"Field {missing_name} is required but not provided ({op_name})",
            fix_hint=_required_hint(missing_name, schema),
            fields=fields,
        )

    raise ValidationFailed(
        f"Input validation failed: {first.message}",
        fix_hint=f"See ops/{op_name}.json#/input_schema to fix the field",
        fields=fields,
    )


def _field_from_error(e: Any) -> Dict[str, Any]:
    return {
        "name": ".".join(str(x) for x in e.absolute_path) or "(root)",
        "reason": e.message,
        "validator": e.validator,
    }


def _required_hint(field_name: str, schema: Dict[str, Any]) -> str:
    """Try to give a concrete next-action hint for a missing required field."""
    props = (schema.get("properties") or {}).get(field_name) or {}
    desc = props.get("description") or ""
    if desc:
        return f"Field {field_name}: {desc}"
    return f"See ops/<Op>.json#/input_schema/properties/{field_name} for details"
