"""Request validation and advisory, value-free response diagnostics."""
from itertools import islice
from datetime import datetime
import re
from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import ValidationError
from .contract import SCHEMAS, API_VERSION
from .common import skill_version, ClientError

LIMIT = 8
OPAQUE = {'metadata', 'rawEvent', 'content', 'delta', 'arguments', 'value',
          'snapshot', 'patch', 'responseSchema', 'parameters', 'input', 'output'}
FIELDS = set()
EVENTS = {}
MESSAGE_BRANCHES = {}
DATE_TIME = re.compile(r'[0-9]{4}-[0-9]{2}-[0-9]{2}[Tt](?:[01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]'
                       r'(?:\.[0-9]+)?(?:[Zz]|[+-]([0-9]{2}):([0-9]{2}))')


class CompatibleResponse(dict):
    """Client diagnostics live outside server keys, so no extension is overwritten."""
    compatibility = None


def response_compatibility(value):
    return getattr(value, 'compatibility', None)


def _date_time(value):
    if not isinstance(value, str):
        return True  # Schema type validation handles non-string inputs.
    match = DATE_TIME.fullmatch(value)
    if not match or (match[1] is not None and (int(match[1]) > 23 or int(match[2]) > 59)):
        return False
    try:
        datetime.fromisoformat(value.upper().replace('Z', '+00:00'))
        return True
    except ValueError:
        return False


def _format_checker():
    checker = FormatChecker()
    # Register on the instance: RFC3339 validation must not depend on optional extras.
    checker.checks('date-time')(_date_time)
    return checker


def _catalog(node):
    if isinstance(node, dict):
        FIELDS.update(node.get('properties', {}))
        for value in node.values():
            _catalog(value)
    elif isinstance(node, list):
        for value in node:
            _catalog(value)


for _resource, _schema in SCHEMAS.items():
    _catalog(_schema)
    if _resource == 'message':
        for _name, _definition in _schema.get('$defs', {}).items():
            _role = _definition.get('properties', {}).get('role', {}).get('const')
            if isinstance(_role, str):
                MESSAGE_BRANCHES[_role] = (_resource, _name)
    if _resource in ('event', 'event-core', 'event-state'):
        for _name, _definition in _schema.get('$defs', {}).items():
            for _part in [_definition, *_definition.get('allOf', [])]:
                _kind = _part.get('properties', {}).get('type', {}).get('const')
                if isinstance(_kind, str):
                    EVENTS[_kind] = (_resource, _name)


def event_kind(value):
    candidate = value.get('type') if isinstance(value, dict) else None
    return candidate if isinstance(candidate, str) and candidate in EVENTS else 'unknown'


def _kind(value):
    if value is None:
        return 'null'
    if isinstance(value, bool):
        return 'boolean'
    if isinstance(value, dict):
        return 'object'
    if isinstance(value, list):
        return 'array'
    if isinstance(value, str):
        return 'string'
    return 'number' if isinstance(value, (int, float)) else 'unknown'


def _path(parts):
    result, opaque = '$', False
    for item in islice(iter(parts), 32):
        if opaque:
            return result + '.*'
        if isinstance(item, int):
            result += '[' + str(item) + ']'
        else:
            result += '.' + (item if item in FIELDS else '*')
            opaque = item in OPAQUE or item not in FIELDS
    return result


def _violation(error, prefix=()):
    rule = error.validator if error.validator in Draft202012Validator.VALIDATORS else 'schema'
    item = {'path': _path((*prefix, *error.absolute_path)), 'rule': rule, 'actual_type': _kind(error.instance)}
    if rule == 'type':
        types = error.validator_value if isinstance(error.validator_value, list) else [error.validator_value]
        item['expected_types'] = [x for x in types if x in ('null', 'boolean', 'object', 'array', 'number', 'integer', 'string')]
    elif rule == 'required' and isinstance(error.instance, dict):
        missing = [x for x in error.validator_value if x not in error.instance]
        item['missing_fields'] = [x if x in FIELDS else '*' for x in missing[:LIMIT]]
    elif rule in ('minimum', 'maximum', 'minLength', 'maxLength', 'minItems', 'maxItems'):
        if type(error.validator_value) in (int, float):
            item['limit'] = error.validator_value
    elif rule == 'additionalProperties' and isinstance(error.instance, dict):
        properties = error.schema.get('properties', {})
        patterns = error.schema.get('patternProperties', {})
        unknown = list(islice((key for key in error.instance if key not in properties
                              and not any(isinstance(key, str) and re.search(pattern, key)
                                          for pattern in patterns)), LIMIT + 1))
        item['unexpected_fields'] = [key if isinstance(key, str) and key in FIELDS else '*'
                                     for key in unknown[:LIMIT]]
        if len(unknown) > LIMIT:
            item['unexpected_fields_truncated'] = True
    # Never use ValidationError.message, repr(instance), enum values or unknown keys.
    return item


def _validator(resource, definition):
    pointer = '/'.join(part.replace('~', '~0').replace('/', '~1') for part in (resource, '$defs', definition))
    return Draft202012Validator({'$ref': '#/$defs/' + pointer, '$defs': SCHEMAS},
                               format_checker=_format_checker())


def _message_diagnostics(errors):
    """Refine only canonical message unions; validation still uses the full schema."""
    unions = [SCHEMAS['message']['$defs'][name] for name in ('Message', 'AGUIMessage')]
    for error in errors:
        role = error.instance.get('role') if isinstance(error.instance, dict) else None
        branch = MESSAGE_BRANCHES.get(role) if isinstance(role, str) else None
        if branch and error.validator == 'oneOf' and error.schema in unions:
            children = list(islice(_validator(*branch).iter_errors(error.instance), LIMIT + 1))
            if children:
                for child in children:
                    yield child, tuple(error.absolute_path)
                continue
        yield error, ()


def _context(resource, definition, value):
    result = {'client_version': skill_version(), 'api_version': API_VERSION,
              'schema': definition, 'resource': resource}
    if resource == 'event':
        result['event_type'] = event_kind(value)
    return result


def validate(value, resource, definition):
    context = _context(resource, definition, value)
    try:
        _validator(resource, definition).validate(value)
    except ValidationError as error:
        try:
            # The union rejects a frame for many irrelevant alternative event types.
            # Evaluate only its declared canonical branch for precise diagnostics.
            branch = EVENTS.get(context.get('event_type'))
            errors = list(islice(_validator(*branch).iter_errors(value), LIMIT + 1)) if branch else [error]
            if not errors:
                errors = [error]
            refined = list(islice(_message_diagnostics(errors), LIMIT + 1))
            context.update(violations=[_violation(e, prefix) for e, prefix in refined[:LIMIT]],
                           truncated=len(refined) > LIMIT or len(errors) > LIMIT)
        except Exception:
            context.update(violations=[{'path': '$', 'rule': 'schema', 'actual_type': _kind(value)}], diagnostic_detail_unavailable=True)
        raise ClientError('ContractMismatch', 'The data does not match the installed contract. Inspect the value-free diagnostic and recover any saved task before retrying.',
                          schema=definition, diagnostic=context) from None
    except Exception as error:
        from referencing.exceptions import Unresolvable, NoSuchResource
        failure = 'reference_resolution' if isinstance(error, (Unresolvable, NoSuchResource)) else 'validator_failure'
        context['failure_kind'] = failure
        raise ClientError('ContractValidationFailed', 'The client could not evaluate its installed contract. This is a client validation failure, not evidence of invalid cloud data.',
                          schema=definition, diagnostic=context) from None


def inspect_response(value, resource, definition):
    """Keep inbound data intact; consumers check only what their next step needs.

    The published schema is useful for diagnosis, but it is not an allowlist for
    service extensions. Missing optional presentation metadata must not discard
    an otherwise useful answer. Diagnostics never contain response values.
    """
    try:
        validate(value, resource, definition)
    except ClientError as error:
        return error.result.get('diagnostic', {})
    return None
