#!/usr/bin/env python3
"""Bind a human decision to a live service card; no cloud/product APIs here."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import sys
import time
import uuid


def strict_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON key')
        result[key] = value
    return result


def loads(text):
    return json.loads(text, object_pairs_hook=strict_object,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError('Invalid number')))


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False)


def api_name(tool):
    if not isinstance(tool, str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,159}', tool):
        raise ValueError('Invalid operation name')
    return tool.lower().replace('-', '').replace('_', '')


def secret_key(key):
    name = key.lower().replace('-', '').replace('_', '')
    return name != 'clienttoken' and (name == 'token' or any(part in name for part in
        ('password', 'passwd', 'secret', 'token', 'authorization', 'credential', 'accesskey', 'privatekey')))


def has_secrets(value):
    if isinstance(value, dict):
        return any(secret_key(key) or has_secrets(item) for key, item in value.items())
    if isinstance(value, list):
        return any(has_secrets(item) for item in value)
    if isinstance(value, str):
        if value.lstrip().startswith(('{', '[')):
            try:
                return has_secrets(loads(value))
            except ValueError:
                pass
        if value.startswith('aliyun '):
            return any(part.startswith('--') and secret_key(part[2:]) for part in shlex.split(value))
    return False


def redact(value):
    if isinstance(value, dict):
        return {key: '[REDACTED]' if secret_key(key) else redact(item) for key, item in value.items()}
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, str):
        if value.lstrip().startswith(('{', '[')):
            try:
                return canonical(redact(loads(value)))
            except ValueError:
                pass
        if value.startswith('aliyun '):
            try:
                parts = shlex.split(value)
                for index, part in enumerate(parts[:-1]):
                    if part.startswith('--') and secret_key(part[2:]):
                        parts[index + 1] = '[REDACTED]'
                return shlex.join(parts)
            except ValueError:
                return '[REDACTED COMMAND]'
    return value


def forbidden(tool, args):
    names = [api_name(tool)]
    if names[0].endswith('callcli'):
        command = args.get('command')
        if not isinstance(command, str):
            raise ValueError('CLI card has no command')
        parts = shlex.split(command)
        if len(parts) < 3 or parts[0] != 'aliyun' or any(part in (';', '&&', '|', '||') for part in parts):
            raise ValueError('Unrecognized CLI card')
        names.append(api_name(parts[2]))
    if any(name.startswith(('delete', 'release', 'drop', 'truncate', 'destroy', 'purge')) for name in names):
        return True
    # Explicit deletion protection fields, including settings encoded as JSON.
    def disabled(value):
        return value is False or value == 0 or (isinstance(value, str) and
            value.lower() in ('false', '0', 'off', 'disabled', 'disable'))
    def inspect(value):
        if isinstance(value, str) and value.lstrip().startswith(('{', '[')):
            try:
                return inspect(loads(value))
            except ValueError:
                return False
        if isinstance(value, list):
            return any(inspect(item) for item in value)
        if not isinstance(value, dict):
            return False
        keys = {key.lower().replace('-', '').replace('_', ''): item for key, item in value.items()}
        protection = {'deletionprotection', 'deletionlock', 'deleteprotection', 'enabledeletionprotection'}
        if any(key in protection and disabled(item) for key, item in keys.items()):
            return True
        if 'modifydbclusterdeletion' in names and not (
            keys.get('protection') is True or keys.get('protection') == 'true'
        ):
            return True
        if any('deletion' in name for name in names) and disabled(keys.get('protection', True)):
            return True
        parameter = keys.get('name', keys.get('parametername'))
        if isinstance(parameter, str) and parameter.lower().replace('_', '').replace('-', '') in protection:
            if disabled(keys.get('value', keys.get('parametervalue', True))):
                return True
        # Metadata-query wrappers must not turn SQL deletion into a permitted API.
        for key, item in keys.items():
            if key in ('sql', 'query', 'sqlstatement') and isinstance(item, str):
                sql = re.sub(r'/\*.*?\*/|--[^\n]*', ' ', item, flags=re.S)
                if re.search(r'(^|;)\s*(delete|drop|truncate)\b', sql, re.I):
                    return True
        return any(inspect(item) for item in value.values())
    return inspect(args)


def normalize(tool, args):
    if not isinstance(args, dict) or forbidden(tool, args):
        raise ValueError('Forbidden or malformed operation')
    # Normalize only CLI-style top-level key spelling; do not coerce values or
    # interpret a product schema. Nested JSON and every extra field stay bound.
    normalized = {}
    for key, value in args.items():
        name = key.lower().replace('-', '').replace('_', '')
        if not name or name in normalized:
            raise ValueError('Duplicate argument alias')
        normalized[name] = value
    digest = hashlib.sha256(canonical({'tool': api_name(tool), 'args': normalized}).encode()).hexdigest()
    return {'tool': api_name(tool), 'sha256': digest, 'arguments': redact(normalized)}


def private_dir(path, create=False):
    if not path.is_absolute() or path.is_symlink():
        raise ValueError('Use an absolute private directory')
    if create:
        path.mkdir(mode=0o700, parents=False, exist_ok=True)
    stat = path.stat()
    if not path.is_dir() or stat.st_uid != os.getuid() or stat.st_mode & 0o077:
        raise ValueError('Confirmation directory must be private and owned by this user')


def exclusive_json(path, value):
    temporary = path.parent / ('.' + uuid.uuid4().hex + '.tmp')
    try:
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w') as out:
            out.write(canonical(value) + '\n')
        # Publish a complete file without overwriting a prior decision.
        os.link(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def read_json(path):
    if path.is_symlink() or path.stat().st_uid != os.getuid() or path.stat().st_mode & 0o077:
        raise ValueError('Unsafe confirmation file')
    return loads(path.read_text())


def update(path, value):
    temporary = path.with_suffix('.tmp')
    exclusive_json(temporary, value)
    temporary.replace(path)


def valid_uuid(value):
    if str(uuid.UUID(value)) != value.lower():
        raise ValueError('Invalid confirmation or session ID')
    return value


def wait_card(directory, card, session, seconds):
    private_dir(directory, create=True)
    valid_uuid(session)
    card_id = valid_uuid(card.get('confirmation_id', card.get('confirmationId', '')))
    if str(card.get('approved', card.get('Approved'))) != '0':
        raise ValueError('Card is not pending')
    tool = card.get('tool_name', card.get('toolName'))
    args = card.get('tool_args', card.get('toolArgs'))
    plan = normalize(tool, args)
    record = {'confirmation_id': card_id, 'session_id': session, 'tool': tool,
              'arguments': redact(args), 'plan_sha256': plan['sha256'], 'state': 'pending',
              'created_at': time.time(), 'expires_at': time.time() + seconds}
    path = directory / (card_id + '.json')
    exclusive_json(path, record)
    decision_path = directory / (card_id + '.decision.json')
    while time.time() < record['expires_at']:
        if decision_path.exists():
            try:
                decision = read_json(decision_path)
            except json.JSONDecodeError:
                time.sleep(0.05)
                continue
            if any(decision.get(key) != record[key] for key in ('confirmation_id', 'session_id', 'plan_sha256')):
                raise ValueError('Decision does not match live card')
            approved = decision.get('decision') == 'approve'
            record['state'] = 'approved' if approved else 'rejected'
            update(path, record)
            return approved
        time.sleep(0.1)
    record['state'] = 'expired'
    update(path, record)
    return False


def decide(directory, card_id, session, digest, decision):
    private_dir(directory)
    valid_uuid(card_id)
    valid_uuid(session)
    path = directory / (card_id + '.json')
    record = read_json(path)
    if record['state'] != 'pending' or time.time() >= record['expires_at']:
        raise ValueError('Card is no longer pending')
    if record['session_id'] != session or record['plan_sha256'] != digest:
        raise ValueError('Decision does not match live card')
    exclusive_json(directory / (card_id + '.decision.json'), {
        'confirmation_id': card_id, 'session_id': session, 'plan_sha256': digest, 'decision': decision})
    return {'state': 'decision_submitted', 'confirmation_id': card_id, 'decision': decision}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    norm = commands.add_parser('normalize')
    norm.add_argument('--tool', required=True)
    norm.add_argument('--reject-secrets', action='store_true')
    check = commands.add_parser('check-dir')
    check.add_argument('--directory', required=True, type=Path)
    wait = commands.add_parser('wait')
    wait.add_argument('--directory', required=True, type=Path)
    wait.add_argument('--session-id', required=True)
    wait.add_argument('--seconds', type=int, default=90)
    opts = parser.parse_args()
    try:
        if opts.command == 'normalize':
            value = loads(sys.stdin.read())
            if opts.reject_secrets and has_secrets(value):
                raise ValueError('Do not supply secret-bearing approval arguments')
            result = normalize(opts.tool, value)
        elif opts.command == 'check-dir':
            private_dir(opts.directory, create=True)
            result = {'private': True}
        else:
            if not 1 <= opts.seconds <= 110:
                raise ValueError('Invalid confirmation deadline')
            result = {'approved': wait_card(opts.directory, loads(sys.stdin.read()), opts.session_id, opts.seconds)}
        print(canonical(result))
        return 0
    except (OSError, ValueError, TypeError, KeyError) as error:
        print(f'Confirmation error ({type(error).__name__}); no approval generated.', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
