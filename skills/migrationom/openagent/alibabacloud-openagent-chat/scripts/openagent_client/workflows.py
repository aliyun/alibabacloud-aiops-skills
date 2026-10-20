"""Conversation, task and decision workflows over the public API."""
import time
import uuid
import requests
from datetime import datetime, timezone
from contextlib import ExitStack, nullcontext
from .common import require, digest, authorization, ClientError, persist_diagnostic
from .settings import guard, load
from .stream import Projection, frames
from .validation import validate, response_compatibility

TERMINAL_STATUSES = frozenset(('COMPLETED', 'FAILED', 'CANCELLED', 'REJECTED'))


def incomplete(message, **available):
    return {'complete': False, 'recovery_needed': True, 'next_step': message, **available}


def new_conversation(store):
    local_session = str(uuid.uuid4())
    store.put('local-' + digest(local_session), {'local_session': local_session})
    return {'ok': True, 'local_session': local_session, 'status': 'ready'}


def require_local_conversation(store, local_session):
    # Existing bindings remain recoverable after upgrading older installations.
    require(store.get('local-' + digest(local_session)) or store.get('conversation-' + digest(local_session)),
            'LocalSessionRequired', 'Run task new once for a new conversation, then retain its returned local_session for follow-ups and recovery.')


def require_session_connection(store, session_id):
    """Keep known conversation IDs on their original connection before any I/O."""
    index = store.get('session-' + digest(session_id), {})
    expected = index.get('connection')
    if index.get('conversation'):
        binding = store.get(index['conversation'])
        require(isinstance(binding, dict) and binding.get('session_id') == session_id and binding.get('connection'),
                'InvalidConversationState', 'Restore the saved conversation binding before continuing.')
        require(expected in (None, binding['connection']), 'InvalidConversationState',
                'The conversation index and binding disagree. Preserve both records before recovery.')
        expected = binding['connection']
    if expected is not None:
        selected = (load(store) or {}).get('connection')
        require(selected and digest(selected) == expected, 'ConversationConnectionChanged',
                'This conversation belongs to another connection. Restore its original service region and credential source before continuing or cancelling.',
                session_id=session_id)


def operation_status(store, reference):
    entry = store.get('operation-' + digest(reference))
    result = {'ok': True, 'operation_ref': reference, 'operation': entry,
              'status': (entry or {}).get('outcome', (entry or {}).get('status', 'not_started'))}
    if entry and entry.get('action') == 'CreateSession' and not entry.get('identifiers', {}).get('sessionId'):
        result.update(creation_status='unconfirmed', business_task_submitted=False, recovery_available=False,
                      message='The client cannot confirm whether the cloud conversation was created. It did not submit a business task and has no identifiers for recovery. Missing identifiers do not prove that conversation creation failed.',
                      next_step='No cloud conversation identifier was saved, and no business task was submitted. Report the unconfirmed creation and stop. Other conversations cannot resolve this operation. Do not enumerate local files, query unrelated conversations, or submit with a different local conversation identifier.')
    return result


def local_status(store, local_session):
    name = 'conversation-' + digest(local_session)
    with store.lock('local_session', local_session, local_session=local_session):
        binding = store.get(name)
        if not binding:
            created = store.get('operation-' + digest(name + '/create'), {})
            session_id = created.get('identifiers', {}).get('sessionId')
            if created.get('status') == 'completed' and session_id:
                binding = {'connection': created.get('connection'), 'session_id': session_id}
                if binding['connection']:
                    store.put(name, binding)
                    attach_conversation(store, name, binding)
                else:
                    binding = None
        if binding:
            attach_conversation(store, name, binding)
            repair_session(store, binding['session_id'])
            binding = store.get(name)
    reference = binding['operation_ref'] if binding and binding.get('operation_ref') else name + '/create'
    result = operation_status(store, reference)
    result['conversation'] = binding
    entry = result['operation'] or {}
    result['session_id'] = (binding or {}).get('session_id') or entry.get('session_id')
    result['run_id'] = entry.get('run_id') or (binding or {}).get('run_id')
    result['recovery_available'] = bool(result['session_id'] and result['run_id'])
    if result['recovery_available']:
        result['recovery_command'] = ['task', 'recover', '--local-session', local_session]
    elif binding and entry and 'next_step' not in result:
        result['next_step'] = 'No task identifier was saved. Report the unconfirmed submission and stop; do not identify a replacement by reading other conversations or replaying the request.'
    elif not binding and not entry:
        result['next_step'] = 'No request is recorded for this local conversation.'
    return result


def recover(store, transport, local_session):
    saved = local_status(store, local_session)
    if not saved['recovery_available']:
        return saved
    require(saved['conversation']['connection'] == digest(load(store)['connection']),
            'ConversationConnectionChanged', 'Recovery requires the saved connection for this local conversation. Do not switch accounts or service regions automatically.')
    current = run(transport, saved['session_id'], saved['run_id'], store)
    continuation = completed_session_run_after_external_wait(transport, saved['session_id'], current)
    if continuation is not None:
        current = continuation
    result = {'ok': True, 'run': current, 'operation_ref': saved['operation_ref']}
    if continuation is not None:
        result.update(original_run_id=saved['run_id'], recovery_basis='authoritative_session_current_run')
    if current['status'] in ('RUNNING', 'PENDING'):
        result.update(next_step='The original task is still active. Continue observation; do not submit another task.',
                      recovery_command=['task', 'watch', '--session', saved['session_id'], '--run', saved['run_id']])
    else:
        result.update(history(transport, saved['session_id'], current['runId']))
    if (saved['operation'] or {}).get('first_error'):
        result['original_diagnostic'] = saved['operation']['first_error']
    return result


def operation_lock(store, reference):
    return store.lock('operation', reference, operation_ref=reference)


def select_operation(store, transport, action, session_id, body, *, target=None, new_turn=False):
    """Allocate a durable reference under a short domain lock, before any request."""
    domain = {'connection': load(store)['connection'], 'session': session_id,
              'action': action, 'target': target}
    name = 'logical-' + digest(domain)
    identity = digest(body)
    with operation_lock(store, name):
        slot = store.get(name)
        require(slot is None or isinstance(slot, dict) and slot.get('version') == 1
                and isinstance(slot.get('reference'), str) and slot.get('fingerprint'),
                'InvalidOperationState', 'The saved operation index is invalid. Restore local state before submitting.')
        if slot:
            prior_ref = slot['reference']
        elif action == 'MESSAGE':
            index = store.get('session-' + digest(session_id), {})
            prior_ref = index.get('latest_operation_ref')
        else:
            prior_ref = None
        if slot and action == 'MESSAGE' and (slot['fingerprint'] != identity or new_turn):
            latest = store.get('session-' + digest(session_id), {}).get('latest_operation_ref')
            prior_ref = latest or prior_ref
        if slot is None and action == 'CancelRun':
            # Old cancellations have no session binding. Match only this exact domain.
            matches = []
            for path in store.root.glob('operation-*.json'):
                old = store.get(path.stem)
                if old.get('action') == action and old.get('path') == {'sessionId': session_id, 'runId': target}:
                    expected = digest({'action': action, 'path': old['path'], 'body': body,
                                       'connection': domain['connection']})
                    require(old.get('fingerprint') == expected, 'LegacyOperationAmbiguous',
                            'A prior cancellation exists for this run. Inspect it using its original reference before proceeding.')
                    matches.append(old)
            require(not matches, 'LegacyOperationRecoveryRequired',
                    'A legacy cancellation already exists. Use its original operation reference to recover; no cancellation was submitted.')
        prior = store.get('operation-' + digest(prior_ref)) if prior_ref else None
        if slot and slot['fingerprint'] == identity and not new_turn:
            return prior_ref
        if prior:
            if action == 'MESSAGE':
                legacy = digest({'session': session_id, 'body': body,
                                 'connection': load(store)['connection']})
                if not slot and prior.get('fingerprint') == legacy and not new_turn:
                    store.put(name, {'version': 1, 'reference': prior_ref, 'fingerprint': identity})
                    return prior_ref
                require(prior.get('status') == 'completed', 'OutcomeUnknown',
                        'Recover the saved operation before starting another turn.', operation_ref=prior_ref)
                if prior.get('run_id'):
                    current = run(transport, session_id, prior['run_id'], store)
                    current = completed_session_run_after_external_wait(transport, session_id, current) or current
                    require(current['status'] in TERMINAL_STATUSES,
                            'DecisionPending', 'Observe, resolve or cancel the saved task first.', operation_ref=prior_ref)
            else:
                require(slot['fingerprint'] == identity, 'OperationReferenceConflict',
                        'This logical action already has a different saved request. Inspect its operation status.', operation_ref=prior_ref)
        elif slot:
            # A crash between allocation and journal creation still owns this slot.
            require(slot['fingerprint'] == identity and not new_turn, 'OutcomeUnknown',
                    'Repeat the allocated request unchanged before starting another turn.', operation_ref=prior_ref)
        reference = str(uuid.uuid4())
        store.put(name, {'version': 1, 'reference': reference, 'fingerprint': identity})
        return reference


def submission_result(entry, reference):
    result = {'ok': entry['status'] == 'completed', 'status': entry.get('outcome', entry['status']),
              'operation_ref': reference, 'session_id': entry.get('session_id'),
              'run_id': entry.get('run_id'),
              'message': 'No task was resubmitted. Recover or inspect the saved task.'}
    result['recovery_command'] = (['task', 'result', '--session', entry['session_id'], '--run', entry['run_id']]
                                  if entry.get('session_id') and entry.get('run_id') else
                                  ['operation', 'status', '--operation-ref', reference])
    return result


def mutate(store, transport, action, *, operation_ref, path=None, body=None, approval=None, connection_snapshot=None):
    if (path or {}).get('sessionId'):
        require_session_connection(store, path['sessionId'])
    if action == 'CancelRun' and operation_ref is None:
        authorization(approval)
        operation_ref = select_operation(store, transport, action, path['sessionId'], body, target=path['runId'])
    session = (path or {}).get('sessionId')
    submission = store.lock('session_submission', session, session_id=session) if session and action != 'CancelRun' else nullcontext()
    with submission, operation_lock(store, operation_ref):
        return _mutate(store, transport, action, operation_ref=operation_ref, path=path, body=body, approval=approval,
                       connection_snapshot=connection_snapshot)


def _mutate(store, transport, action, *, operation_ref, path=None, body=None, approval=None, connection_snapshot=None):
    require(operation_ref, 'OperationReferenceRequired', 'Choose a stable operation reference before submitting a change.')
    name = 'operation-' + digest(operation_ref)
    selected = connection_snapshot if connection_snapshot is not None else (load(store) or {}).get('connection')
    identity = digest({'action': action, 'path': path, 'body': body, 'connection': selected})
    existing = store.get(name)
    if existing:
        require(existing['fingerprint'] == identity, 'OperationReferenceConflict', 'This reference was already used for a different operation.')
        return {'ok': existing['status'] == 'completed', 'status': existing['status'],
                'message': 'This operation was already attempted and was not submitted again.', 'operation': existing,
                'operation_ref': operation_ref, 'recovery_command': ['operation', 'status', '--operation-ref', operation_ref]}
    entry = {'fingerprint': identity, 'action': action, 'status': 'outcome_unknown',
             'idempotency_key': str(uuid.uuid4()), 'time': time.time(), 'path': path, 'connection': digest(selected)}
    if approval:
        entry['authorization'] = authorization(approval)
    store.put(name, entry)
    try:
        result = transport.call(action, path=path, body=body, key=entry['idempotency_key'])
    except ClientError as exc:
        exc.result.update(status='outcome_unknown', operation_ref=operation_ref,
                          next_step='Report this unconfirmed operation and stop. Do not resubmit it, invent retry authorization, or change conversation identifiers to bypass recovery. The cause and recovery time are not established by this error. Inspect operation status using the saved reference if needed.')
        if action == 'CreateSession':
            exc.result['business_task_submitted'] = False
            exc.result['creation_status'] = 'unconfirmed'
            exc.result['recovery_available'] = False
            saved = operation_status(store, operation_ref)
            exc.result['outcome_explanation'] = saved['message']
            exc.result['next_step'] = saved['next_step']
        raise
    except Exception:
        raise ClientError('OutcomeUnknown', 'The operation outcome is unconfirmed. Inspect its saved reference; do not resubmit.',
                          operation_ref=operation_ref, recovery_command=['operation', 'status', '--operation-ref', operation_ref]) from None
    entry.update(status='completed', request_id=result.get('requestId'))
    data = result.get('data') or {}
    entry['identifiers'] = {k: data[k] for k in ('sessionId', 'runId') if k in data}
    store.put(name, entry)
    return {'ok': True, 'result': result, 'operation': entry, 'operation_ref': operation_ref}


def send(store, transport, session_id, body, operation_ref, progress=None, parent_id=None, *, settings_checked=False, retry_authorization=None, recovery_attempt=0, new_turn=False):
    require_session_connection(store, session_id)
    if body.get('type') == 'RECONNECT':
        return _send(store, transport, session_id, body, operation_ref, progress, parent_id,
                     settings_checked=settings_checked, retry_authorization=retry_authorization, recovery_attempt=recovery_attempt)
    try:
        with ExitStack() as submission:
            submission.enter_context(store.lock('session_submission', session_id, session_id=session_id, operation_ref=operation_ref))
            repair_session(store, session_id)
            if operation_ref is None:
                operation_ref = select_operation(store, transport, body['type'], session_id, body, target=parent_id, new_turn=new_turn)
            submission.enter_context(operation_lock(store, operation_ref))
            result = _send(store, transport, session_id, body, operation_ref, progress, parent_id,
                           settings_checked=settings_checked, retry_authorization=retry_authorization,
                           recovery_attempt=recovery_attempt, submission=submission)
            return {**result, 'operation_ref': operation_ref, 'turn_ref': operation_ref}
    except ClientError as error:
        if operation_ref is not None:
            error.result.setdefault('operation_ref', operation_ref)
            error.result.setdefault('recovery_command', ['operation', 'status', '--operation-ref', operation_ref])
        raise


def _send(store, transport, session_id, body, operation_ref, progress=None, parent_id=None, *, settings_checked=False, retry_authorization=None, recovery_attempt=0, submission=None):
    validate(body, 'api', 'SendMessageRequest')
    mode = body['type']
    name = 'operation-' + digest(operation_ref)
    fingerprint = digest({'session': session_id, 'body': body, 'connection': load(store)['connection']})
    legacy_fingerprint = fingerprint
    if mode == 'RESUME':
        fingerprint = digest({'session': session_id, 'body': body, 'parent_run': parent_id,
                              'connection': load(store)['connection']})
    existing = store.get(name) if mode != 'RECONNECT' else None
    if existing:
        require(existing['fingerprint'] == fingerprint or mode == 'RESUME' and
                existing.get('parent_run') is None and existing['fingerprint'] == legacy_fingerprint,
                'OperationReferenceConflict', 'This reference belongs to a different task submission.')
        return submission_result(existing, operation_ref)
    retry_of = None
    if mode != 'RECONNECT':
        repair_session(store, session_id)
    if mode == 'RESUME':
        index = store.get('session-' + digest(session_id), {})
        prior_ref = index.get('latest_operation_ref')
        prior = store.get('operation-' + digest(prior_ref), {}) if prior_ref else {}
        require(not (prior.get('parent_id') == parent_id), 'DecisionNotPending',
                'This decision was already submitted. Recover the saved response instead.',
                session_id=session_id, run_id=prior.get('run_id'), operation_ref=prior_ref)
        current = run(transport, session_id, parent_id, store)
        require(current['status'] == 'WAITING_USER', 'DecisionNotPending', 'The task is no longer waiting for this decision.')
    if mode == 'MESSAGE':
        index = store.get('session-' + digest(session_id), {})
        prior_ref = index.get('latest_operation_ref')
        if not prior_ref and index.get('conversation'):
            prior_ref = (store.get(index['conversation']) or {}).get('operation_ref')
        prior = store.get('operation-' + digest(prior_ref)) if prior_ref else None
        if prior:
            require(prior['status'] == 'completed', 'OutcomeUnknown',
                    'Recover the previous task before submitting another request.', session_id=session_id,
                    run_id=prior.get('run_id'), operation_ref=prior_ref)
            if prior.get('run_id'):
                current = run(transport, session_id, prior['run_id'], store)
                current = completed_session_run_after_external_wait(transport, session_id, current) or current
                require(current['status'] in TERMINAL_STATUSES, 'DecisionPending',
                        'Resolve or cancel the previous task before submitting a new request.',
                        session_id=session_id, run_id=prior['run_id'], operation_ref=prior_ref)
        if prior and prior.get('fingerprint') == fingerprint and prior.get('outcome') in ('failed', 'error', 'rejected'):
            require(retry_authorization, 'RetryAuthorizationRequired',
                    'This task already failed. Report that result and wait for the user to explicitly request another attempt. Do not change the text, reference or conversation to bypass this check.',
                    session_id=session_id, run_id=prior.get('run_id'), operation_ref=prior_ref)
            approval = authorization(retry_authorization)
            require(approval != prior.get('retry_authorization'), 'RetryAuthorizationRequired',
                    'The previous retry authorization was already used. Obtain a new user decision before retrying again.')
            retry_of = {'retry_of': prior.get('run_id'), 'retry_authorization': approval}
    if mode != 'RECONNECT' and not settings_checked:
        guard(store, transport)
    entry = {'operation_ref': operation_ref, 'time': time.time(), 'fingerprint': fingerprint, 'parent_run': parent_id, 'parent_id': parent_id, 'mode': mode, 'session_id': session_id, 'status': 'outcome_unknown', 'idempotency_key': str(uuid.uuid4()), 'connection': digest(load(store)['connection'])}
    if retry_of:
        entry.update(retry_of)
    if mode != 'RECONNECT':
        if retry_of:
            with store.lock('retry_authorization', retry_of['retry_authorization'], wait=True):
                require(not store.get('retry-authorization-' + retry_of['retry_authorization']), 'RetryAuthorizationRequired', 'This retry authorization was already consumed.')
                store.put('retry-authorization-' + retry_of['retry_authorization'], {'operation_ref': operation_ref})
        save_submission(store, session_id, operation_ref, entry, initial=True)
    projection = Projection(session_id, mode, body.get('runId'), parent_id)
    try:
        stream = transport.call('SendMessage', path={'sessionId': session_id}, body=body, key=entry['idempotency_key'] if mode != 'RECONNECT' else None)
        for event in frames(stream):
            projection.accept(event)
            if event['type'] == 'RUN_STARTED':
                entry['run_id'] = event['runId']
                if mode != 'RECONNECT':
                    save_submission(store, session_id, operation_ref, entry)
                    # RUN_STARTED establishes durable recovery; observation holds no submit lease.
                    if submission is not None:
                        submission.close()
                if progress:
                    progress({'ok': True, 'status': 'observing', 'session_id': session_id, 'run_id': entry['run_id']})
        result = projection.finish()
        if result['status'] == 'unknown':
            return {'ok': True, **result, 'recovery_needed': True,
                    'recovery_command': ['task', 'result', '--session', session_id, '--run', projection.run_id]}
        entry.update(status='completed', outcome=result['status'])
        if mode != 'RECONNECT':
            save_submission(store, session_id, operation_ref, entry)
        else:
            record_outcome(store, session_id, result['run_id'], result['status'])
        return {'ok': True, **result, **({'operation_ref': operation_ref, 'turn_ref': operation_ref} if mode != 'RECONNECT' else {})}
    except ClientError as exc:
        if (projection.run_id or body.get('runId')) and exc.result['code'] in ('InvalidStream', 'ObservationIncomplete', 'ObservationInterrupted', 'IncompleteStream', 'OutcomeUnknown', 'ObservationTimeout', 'NetworkInterrupted') and recovery_attempt < 2:
            time.sleep((1, 2)[recovery_attempt])
            if getattr(transport, 'response', None) is not None:
                transport.response.close()
            try:
                return watch(store, transport, session_id, projection.run_id or body.get('runId'), progress,
                             recovery_attempt=recovery_attempt + 1)
            except ClientError as recovery_error:
                if recovery_error.result['code'] == 'ContinuationMismatch':
                    raise
                return {'ok': True, 'status': 'unknown', 'session_id': session_id,
                        'run_id': projection.run_id or body.get('runId'),
                        'operation_ref': operation_ref,
                        'messages': list(projection.messages.values()),
                        'observation_error_code': exc.result['code'],
                        'recovery_error_code': recovery_error.result['code'],
                        **incomplete('Read-only recovery could not confirm the outcome. Preserve this partial answer and recover the saved task later; do not resubmit it.'),
                        'recovery_command': ['task', 'result', '--session', session_id, '--run', projection.run_id or body.get('runId')]}
        exc.result.update(session_id=session_id, run_id=projection.run_id or body.get('runId'), operation_ref=operation_ref)
        persist_diagnostic(store, exc.result)
        if mode != 'RECONNECT' and exc.result.get('diagnostic'):
            entry.setdefault('first_error', {k: exc.result[k] for k in ('code', 'diagnostic', 'diagnostic_ref', 'diagnostic_saved') if k in exc.result})
            try:
                save_submission(store, session_id, operation_ref, entry)
            except (OSError, ClientError):
                exc.result['journal_error_saved'] = False
        raise
    except Exception as exc:
        if isinstance(exc, (requests.exceptions.ConnectionError, requests.exceptions.Timeout, requests.exceptions.ChunkedEncodingError)) and (projection.run_id or body.get('runId')) and recovery_attempt < 2:
            time.sleep((1, 2)[recovery_attempt])
            if getattr(transport, 'response', None) is not None:
                transport.response.close()
            try:
                return watch(store, transport, session_id, projection.run_id or body.get('runId'), progress,
                             recovery_attempt=recovery_attempt + 1)
            except ClientError as recovery_error:
                recovery_error.result.update(session_id=session_id, run_id=projection.run_id or body.get('runId'),
                                             operation_ref=operation_ref)
                raise
        raise ClientError('ObservationInterrupted', 'Observation stopped without a confirmed outcome. Recover the saved task; do not resubmit.', session_id=session_id, run_id=projection.run_id or body.get('runId'), operation_ref=operation_ref) from None
    finally:
        transport.close()


def run(transport, session_id, run_id, store=None):
    if store is not None:
        require_session_connection(store, session_id)
    response = transport.call('GetRun', path={'sessionId': session_id, 'runId': run_id})
    warning = response_compatibility(response)
    def check_identity(data):
        if isinstance(data, dict):
            require(data.get('sessionId', session_id) == session_id and data.get('runId', run_id) == run_id,
                    'ContinuationMismatch', 'The response belongs to a different conversation or task.')
    check_identity(response.get('data'))
    if not isinstance(response.get('data'), dict) or not isinstance(response['data'].get('status'), str):
        try:
            observed = transport.call('GetRun', path={'sessionId': session_id, 'runId': run_id})
            check_identity(observed.get('data'))
            if isinstance(observed.get('data'), dict):
                response = {**response, **observed, 'data': {**(response.get('data') if isinstance(response.get('data'), dict) else {}), **observed['data']}}
        except ClientError as error:
            if error.result['code'] == 'ContinuationMismatch':
                raise
            # Preserve the first response when the bounded read fails.
    current = response.get('data')
    if not isinstance(current, dict):
        current = incomplete('Task details are unavailable. Read this same task again; use its available messages without treating the outcome as confirmed.')
    else:
        current = dict(current)
    # Requested identities are usable context when omitted; conflicting identities
    # are not a compatibility issue and must never be rebound to this journal.
    require(current.get('sessionId', session_id) == session_id and current.get('runId', run_id) == run_id,
            'ContinuationMismatch', 'The response belongs to a different conversation or task.')
    current.setdefault('sessionId', session_id)
    current.setdefault('runId', run_id)
    if not isinstance(current.get('status'), str) or current['status'] not in TERMINAL_STATUSES | {'PENDING', 'RUNNING', 'WAITING_USER'}:
        current.update(incomplete('The task outcome is not confirmed. Recover this same task before submitting a follow-up.', status='UNKNOWN'))
    if warning:
        current['compatibility_warning'] = warning
    if store is not None:
        repair_session(store, session_id)
    if store is not None and current['status'] in TERMINAL_STATUSES | {'WAITING_USER'}:
        record_outcome(store, session_id, run_id, current['status'].lower())
    return current


def history(transport, session_id, run_id=None, max_pages=10):
    query = {'maxResults': 100}
    if run_id:
        query['runId'] = run_id
    messages, seen, warnings, unscoped = [], set(), [], []
    def partial(message):
        return incomplete(message, messages=messages, compatibility_warnings=warnings,
                          **({'unscoped_messages': unscoped} if unscoped else {}))
    for _ in range(max_pages):
        try:
            response = transport.call('ListMessages', path={'sessionId': session_id}, query=query)
        except ClientError as error:
            available = partial('History retrieval is incomplete. Use the available messages and recover this same task; do not resubmit it.')
            available['history_error_code'] = error.result['code']
            return available
        if response_compatibility(response) and len(warnings) < 8:
            warnings.append(response_compatibility(response))
        data = response.get('data')
        if not isinstance(data, dict) or not isinstance(data.get('timeline'), list):
            try:
                observed = transport.call('ListMessages', path={'sessionId': session_id}, query=query)
                if isinstance(observed.get('data'), dict):
                    data = observed['data']
            except ClientError:
                pass
        if not isinstance(data, dict) or not isinstance(data.get('timeline'), list):
            return partial('The response has no usable message timeline. Read the same task history again; do not infer an empty business result.')
        require(data.get('sessionId', session_id) == session_id, 'ContinuationMismatch',
                'The history belongs to a different conversation.')
        for item in data['timeline']:
            if not isinstance(item, dict):
                unscoped.append(item)
            elif not run_id or item.get('runId') == run_id:
                messages.append(item)
            elif not item.get('runId'):
                unscoped.append(item)
        token = data.get('nextToken')
        if not token:
            if unscoped or 'nextToken' not in data:
                return partial('Some history metadata is missing. Preserve the available messages; confirm message ownership or pagination before claiming a complete answer.')
            return {'messages': messages, 'complete': True,
                    **({'compatibility_warnings': warnings} if warnings else {})}
        if not isinstance(token, str) or token in seen:
            return partial('History pagination could not continue. Preserve this partial result and read this same task again.')
        seen.add(token)
        query['nextToken'] = token
    return {**partial('The history page limit was reached. Continue reading from next_token.'), 'next_token': token}


def completed_session_run_after_external_wait(transport, session_id, current):
    """Observe an external callback without rewriting the original submission."""
    outcome = current.get('outcome') if isinstance(current.get('outcome'), dict) else {}
    pending = outcome.get('interrupts') or []
    if (current.get('status') != 'WAITING_USER' or outcome.get('type') != 'interrupt'
            or not isinstance(pending, list) or not pending
            or any(not isinstance(item, dict) or item.get('reason') != 'out_of_band_approval' for item in pending)):
        return None
    require(current.get('sessionId') == session_id, 'ContinuationMismatch',
            'The saved approval task belongs to a different conversation.')
    session = transport.call('GetSession', path={'sessionId': session_id})['data']
    require(session.get('sessionId') == session_id, 'ContinuationMismatch',
            'The observed conversation does not match the saved approval task.')
    latest = session.get('lastRunId')
    if (session.get('status') != 'IDLE' or session.get('lastRunStatus') != 'COMPLETED'
            or not latest or latest == current.get('runId')):
        return None
    continuation = run(transport, session_id, latest)
    require(continuation.get('sessionId') == session_id and continuation.get('runId') == latest,
            'ContinuationMismatch', 'The continuation does not match the observed conversation and task.')
    if continuation.get('status') == 'COMPLETED' and continuation.get('outcome', {}).get('type') == 'success':
        return continuation
    return None


def watch(store, transport, session_id, run_id, progress=None, *, recovery_attempt=0):
    current = run(transport, session_id, run_id, store)
    continuation = completed_session_run_after_external_wait(transport, session_id, current)
    if continuation is not None:
        return {'ok': True, 'run': continuation, 'original_run_id': run_id,
                'recovery_basis': 'authoritative_session_current_run',
                **history(transport, session_id, continuation['runId'])}
    if current['status'] not in ('RUNNING', 'PENDING'):
        return {'ok': True, 'run': current, **history(transport, session_id, run_id)}
    return send(store, transport, session_id, {'type': 'RECONNECT', 'runId': run_id}, 'observation', progress, recovery_attempt=recovery_attempt)


def respond(store, transport, session_id, run_id, answers, operation_ref, reference, progress=None):
    require_session_connection(store, session_id)
    authorization(reference)
    require(isinstance(answers, list) and answers and all(isinstance(a, dict) and
            isinstance(a.get('interaction_id'), str) for a in answers), 'InvalidAnswers', 'Provide identified user responses.')
    replay_entries = [{'interruptId': a['interaction_id'], 'status': 'cancelled'} if a.get('cancel') is True
                      else {'interruptId': a['interaction_id'], 'status': 'resolved', 'payload': a.get('response')}
                      for a in answers]
    replay_body = {'type': 'RESUME', 'resume': replay_entries}
    if operation_ref is None:
        domain = {'connection': load(store)['connection'], 'session': session_id,
                  'action': 'RESUME', 'target': run_id}
        slot = store.get('logical-' + digest(domain))
        if slot:
            require(isinstance(slot, dict) and slot.get('version') == 1 and slot.get('reference'),
                    'InvalidOperationState', 'Restore the saved operation index before responding.')
            require(slot['fingerprint'] == digest(replay_body), 'OperationReferenceConflict',
                    'This decision already has a different saved response.', operation_ref=slot['reference'])
            operation_ref = slot['reference']
        else:
            latest = store.get('session-' + digest(session_id), {}).get('latest_operation_ref')
            old = store.get('operation-' + digest(latest)) if latest else None
            legacy = digest({'session': session_id, 'body': replay_body, 'connection': domain['connection']})
            require(not old or old.get('fingerprint') != legacy, 'LegacyOperationRecoveryRequired',
                    'A matching legacy response has no parent metadata. Inspect it with its original reference; do not submit again.', operation_ref=latest)
    if operation_ref and store.get('operation-' + digest(operation_ref)):
        return send(store, transport, session_id, replay_body, operation_ref, progress, parent_id=run_id)
    current = run(transport, session_id, run_id, store)
    require(current['status'] == 'WAITING_USER', 'DecisionNotPending', 'The task is no longer waiting for this decision.')
    outcome = current.get('outcome')
    items = outcome.get('interrupts') if isinstance(outcome, dict) else None
    require(isinstance(items, list) and items and all(isinstance(x, dict) and isinstance(x.get('id'), str)
            and x['id'] and isinstance(x.get('reason'), str) for x in items),
            'DecisionDetailsRequired', 'The decision details are incomplete. Read this same task again or ask for the missing decision detail before submitting a response.')
    pending = {x['id']: x for x in items}
    require(isinstance(answers, list) and answers, 'InvalidAnswers', 'Provide the user responses requested by this task.')
    require(all(isinstance(a, dict) and isinstance(a.get('interaction_id'), str) and a['interaction_id'] for a in answers), 'InvalidAnswers', 'Each answer must identify a pending decision.')
    require(len({a.get('interaction_id') for a in answers}) == len(answers), 'InvalidAnswers', 'Each decision may appear only once.')
    entries = []
    for answer in answers:
        require(isinstance(answer, dict) and not (set(answer) - {'interaction_id', 'cancel', 'response'}), 'InvalidAnswers', 'Unknown answer field.')
        item = pending.get(answer.get('interaction_id'))
        require(item is not None, 'DecisionNotPending', 'The answer refers to an unknown or outdated decision.')
        require(item['reason'] != 'out_of_band_approval', 'ExternalApprovalRequired', 'The user must complete this decision at the provided approval destination. Observe its result; do not submit it locally.')
        if item.get('expiresAt'):
            try:
                expires = datetime.fromisoformat(item['expiresAt'].replace('Z', '+00:00'))
                require(expires.tzinfo is not None, 'DecisionDetailsRequired', 'The decision expiry has no timezone. Read or clarify the decision details before responding.')
                require(expires > datetime.now(timezone.utc), 'DecisionExpired', 'This decision has expired.')
            except (ValueError, TypeError, AttributeError):
                raise ClientError('DecisionDetailsRequired', 'The decision expiry is unreadable. Read or clarify this decision before responding.') from None
        if answer.get('cancel') is True:
            require('response' not in answer, 'InvalidAnswers', 'A cancelled decision cannot also contain an answer.')
            entries.append({'interruptId': item['id'], 'status': 'cancelled'})
            continue
        require('response' in answer and answer.get('cancel', False) is False, 'AnswerRequired', 'Record the actual user answer or explicit cancellation.')
        payload = answer['response']
        known = {'input_required': 'AskUserQuestionResumePayload', 'tool_call': 'ToolApprovalResumePayload'}
        if item['reason'] in known and 'data' in item:
            validate(payload, 'run', known[item['reason']])
        if item['reason'] == 'tool_call' and isinstance(payload, dict) and payload.get('always') is True:
            require(item.get('data', {}).get('allowAlways') is True, 'InvalidAnswer',
                    'This decision does not offer permission for future operations. Submit the user decision for this operation only.')
        if item['reason'] == 'input_required' and 'data' in item:
            check_question_answers(payload, item['data']['questions'])
        entries.append({'interruptId': item['id'], 'status': 'resolved', 'payload': payload})
    require(set(pending) == {x['interruptId'] for x in entries}, 'IncompleteAnswers', 'Collect a response for every pending decision.')
    return send(store, transport, session_id, {'type': 'RESUME', 'resume': entries}, operation_ref, progress, parent_id=run_id)


def check_question_answers(payload, questions):
    definitions = {q['id']: q for q in questions}
    supplied = payload['answers']
    ids = [a['questionId'] for a in supplied]
    require(len(set(ids)) == len(ids) and set(ids) <= set(definitions), 'InvalidAnswers', 'Answer each identified question at most once.')
    require({q['id'] for q in questions if q.get('required', True)} <= set(ids), 'IncompleteAnswers', 'Answer all required questions.')
    for answer in supplied:
        q, value = definitions[answer['questionId']], answer['value']
        if q['answerType'] == 'multi_select':
            require(isinstance(value, list) and value, 'InvalidAnswers', 'This question expects multiple choices.')
            values = value
        else:
            require(isinstance(value, str) and (value.strip() or not q.get('required', True)), 'InvalidAnswers', 'This question expects a text answer or a single choice.')
            values = [value]
        if q['answerType'] != 'text' and not q.get('allowOther', True):
            allowed = {option['value'] for option in q['options']}
            require(set(values) <= allowed, 'InvalidAnswers', 'Choose one of the offered values.')


def ask(store, transport, local_session, content, operation_ref, progress=None, *, retry_authorization=None, new_turn=False):
    """Bind exactly one local conversation to a cloud conversation and journal turns."""
    require(isinstance(local_session, str) and 0 < len(local_session) <= 512,
            'LocalSessionRequired', 'Use the current host conversation identifier; do not use a shared default.')
    require(isinstance(content, str) and content.strip(), 'EmptyTask', 'Provide the business task to perform.')
    name = 'conversation-' + digest(local_session)
    selected = digest(load(store)['connection'])
    with store.lock('local_session', local_session, local_session=local_session):
        binding = store.get(name)
        require(binding is None or binding['connection'] == selected, 'ConversationConnectionChanged',
                'This local conversation belongs to a different connection. Restore its connection to recover it, or use a new local conversation for the selected connection.')
        settings_checked = False
        if binding is None:
            guard(store, transport)
            settings_checked = True
            created = mutate(store, transport, 'CreateSession', operation_ref=name + '/create', body={})
            ids = created['operation'].get('identifiers', {})
            require(created['operation']['status'] == 'completed' and ids.get('sessionId'), 'OutcomeUnknown',
                    'Conversation creation is unconfirmed. Inspect the saved operation; no new conversation was submitted.', operation_ref=name + '/create')
            binding = {'connection': selected, 'session_id': ids['sessionId']}
            store.put(name, binding)
        attach_conversation(store, name, binding)
    reference = name + '/turn/' + digest(operation_ref) if operation_ref else None
    try:
        return send(store, transport, binding['session_id'], {'type': 'MESSAGE', 'content': content}, reference, progress,
                    settings_checked=settings_checked, retry_authorization=retry_authorization, new_turn=new_turn)
    except ClientError as exc:
        saved = local_status(store, local_session)
        exc.result['recovery_available'] = saved['recovery_available']
        if saved.get('recovery_command'):
            exc.result['recovery_command'] = saved['recovery_command']
        raise


def bind_submission(store, session_id, operation_ref, entry, *, initial=False):
    with store.lock('session_state', session_id, wait=True):
        _bind_submission(store, session_id, operation_ref, entry, initial=initial)


def _bind_submission(store, session_id, operation_ref, entry, *, initial=False):
    name = 'session-' + digest(session_id)
    index = store.get(name, {})
    if initial:
        binding = store.get(index['conversation'], {}) if index.get('conversation') else {}
        original = entry.get('connection') or index.get('connection') or binding.get('connection')
        require(index.get('connection') in (None, original), 'InvalidConversationState',
                'The saved submission belongs to another connection. Preserve its original records.')
        # Repairing an older journal must not relabel it with today's selected
        # connection. Only proven submission or binding metadata supplies scope.
        if original is not None:
            index['connection'] = original
        index['latest_operation_ref'] = operation_ref
        index['sequence'] = entry.get('sequence', index.get('sequence', 0))
        store.put(name, index)
    if index.get('latest_operation_ref') != operation_ref:
        return
    if index.get('conversation'):
        binding = store.get(index['conversation'])
        if binding:
            binding.update(operation_ref=operation_ref, run_id=entry.get('run_id'), status=entry['status'])
            store.put(index['conversation'], binding)


def save_submission(store, session_id, operation_ref, entry, *, initial=False):
    name = 'operation-' + digest(operation_ref)
    with store.lock('session_state', session_id, wait=True):
        saved = store.get(name, {})
        if initial:
            index = store.get('session-' + digest(session_id), {})
            entry['sequence'] = index.get('sequence', 0) + 1
        # Observers may finish while the submitting stream is still draining.
        terminal = saved.get('status') == 'completed' and saved.get('outcome') != 'waiting_user'
        patch = dict(entry)
        if terminal or (saved.get('status') == 'completed' and patch.get('status') != 'completed'):
            patch.pop('status', None)
            patch.pop('outcome', None)
        saved.update(patch)
        store.put(name, saved)
        if saved.get('run_id'):
            store.put('run-' + digest({'session': session_id, 'run': saved['run_id']}), {'journal': name})
        _bind_submission(store, session_id, operation_ref, saved, initial=initial)


def record_outcome(store, session_id, run_id, outcome):
    with store.lock('session_state', session_id, wait=True):
        index = store.get('run-' + digest({'session': session_id, 'run': run_id}))
        if index:
            entry = store.get(index['journal'])
            if entry:
                if entry.get('status') == 'completed' and entry.get('outcome') != 'waiting_user':
                    return
                entry.update(status='completed', outcome=outcome)
                store.put(index['journal'], entry)
                session_index = store.get('session-' + digest(session_id), {})
                reference = session_index.get('latest_operation_ref')
                if reference and 'operation-' + digest(reference) == index['journal']:
                    _bind_submission(store, session_id, reference, entry)


def repair_session(store, session_id):
    """Repair indices after a journal write interrupted between file replacements."""
    with store.lock('session_state', session_id, wait=True):
        entries = []
        for path in store.root.glob('operation-*.json'):
            try:
                entry = store.get(path.stem)
            except (ClientError, OSError, ValueError):
                continue
            if entry and entry.get('session_id') == session_id and entry.get('operation_ref'):
                entries.append(entry)
                if entry.get('run_id'):
                    store.put('run-' + digest({'session': session_id, 'run': entry['run_id']}), {'journal': path.stem})
        if entries:
            latest = max(entries, key=lambda entry: (entry.get('sequence', 0), entry.get('time', 0)))
            _bind_submission(store, session_id, latest['operation_ref'], latest, initial=True)


def attach_conversation(store, name, binding):
    session_id = binding['session_id']
    with store.lock('session_state', session_id, wait=True):
        index = store.get('session-' + digest(session_id), {})
        require(index.get('conversation') in (None, name), 'ConversationBindingConflict',
                'This cloud conversation is already bound to another local conversation.')
        index['conversation'] = name
        store.put('session-' + digest(session_id), index)
