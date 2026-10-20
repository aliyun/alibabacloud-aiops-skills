"""Expose business answers, never internal execution events, by default."""
import re


def error_code(value):
    return value if isinstance(value, str) and re.fullmatch(r'[A-Za-z][A-Za-z0-9_.-]{0,100}', value) else 'TaskFailed'


def _business_fields(value, strings, booleans=()):
    if not isinstance(value, dict):
        return {}
    return {key: item for key, item in value.items()
            if (key in strings and isinstance(item, str))
            or (key in booleans and isinstance(item, bool))}


def _questions(value):
    if not isinstance(value, dict) or not isinstance(value.get('questions'), list):
        return []
    output = []
    for item in value['questions']:
        if not isinstance(item, dict):
            continue
        question = _business_fields(item, {'id', 'header', 'question', 'answerType', 'placeholder'},
                                    {'required', 'allowOther'})
        if not all(question.get(key) for key in ('id', 'header', 'question')):
            continue
        if question.get('answerType') not in ('text', 'single_select', 'multi_select'):
            continue
        if isinstance(item.get('options'), list):
            options = [_business_fields(option, {'value', 'label', 'description', 'preview'},
                                        {'recommended'}) for option in item['options']]
            question['options'] = [option for option in options if option.get('value') and option.get('label')]
        if question['answerType'] != 'text' and len(question.get('options', [])) < 2:
            continue
        output.append(question)
    return output


def interactions(items):
    fields = {'id', 'reason', 'message', 'toolCallId', 'expiresAt', 'data', 'responseSchema'}
    output = []
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict):
            continue
        visible = {key: value for key, value in item.items() if key in fields}
        if item.get('reason') == 'input_required':
            questions = _questions(item.get('data')) or _questions(item.get('metadata'))
            visible.pop('data', None)
            if questions:
                visible['data'] = {'questions': questions}
        output.append(visible)
    return output


def messages(items):
    output = []
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict):
            continue
        message = item.get('message', item)
        if not isinstance(message, dict):
            continue
        if message.get('role') not in ('assistant', 'user'):
            continue
        content = message.get('content')
        if not isinstance(content, str) or not content.strip():
            continue
        output.append({**({'run_id': item['runId']} if 'runId' in item else {}),
                       'id': message.get('id'), 'role': message['role'], 'content': content})
    return output


def result(value, details=False):
    if not isinstance(value, dict):
        return value
    run = value.get('run') if isinstance(value.get('run'), dict) else {}
    visible = messages(value.get('messages', []))
    if not run and 'messages' not in value:
        return value
    if not run and 'status' not in value:
        output = {**value, 'messages': visible}
        if details:
            output['diagnostic'] = value
        return output
    run_id = value.get('run_id') or run.get('runId', run.get('id'))
    answers = [item for item in visible if item['role'] == 'assistant'
               and (not run_id or 'run_id' not in item or item['run_id'] == run_id)]
    status = value.get('status') or str(run.get('status', 'unknown')).lower()
    output = {k: v for k, v in value.items() if k not in ('messages', 'unscoped_messages', 'activities', 'run')}
    if value.get('unscoped_messages'):
        output['unscoped_message_count'] = len(value['unscoped_messages'])
    output.update(status=status, session_id=value.get('session_id', run.get('sessionId')),
                  run_id=value.get('run_id', run.get('runId', run.get('id'))),
                  answer='\n\n'.join(item['content'] for item in answers))
    if run.get('recovery_needed') is True or run.get('complete') is False:
        if isinstance(value.get('complete'), bool):
            output['history_complete'] = value['complete']
        output.update(complete=False, recovery_needed=True)
        steps = []
        for step in (run.get('next_step'), output.get('next_step')):
            if isinstance(step, str) and step and step not in steps:
                steps.append(step)
        if steps:
            output['next_step'] = ' '.join(steps)
    if 'messages' in value:
        output['answer_available'] = bool(answers)
        if status == 'completed' and not answers:
            output['next_step'] = 'The cloud reports completion but returned no business answer. Do not interpret this as an empty resource list or invent a result. Report that the requested business result is unavailable.'
    outcome = run.get('outcome') if isinstance(run.get('outcome'), dict) else {}
    if outcome.get('type') == 'interrupt':
        output['interactions'] = interactions(outcome.get('interrupts'))
    elif 'interactions' in output:
        output['interactions'] = interactions(output['interactions'])
    if 'error_code' in output:
        output['error_code'] = error_code(output['error_code'])
    if status in ('failed', 'cancelled', 'closed', 'error', 'rejected'):
        output['ok'] = False
    if status in ('failed', 'error', 'rejected'):
        output['retry_requires_authorization'] = True
        output['failure_summary'] = 'The cloud task has ended in failure. This result does not establish the underlying cause or a recovery time.'
        output['next_step'] = 'Report this confirmed business-task failure and the error code. Connection recovery cannot restart a task that has already ended. Do not claim the fault is temporary, exclude account or model configuration as a cause, or suggest a recovery time without evidence. Retry only after a new explicit user decision; use the same conversation and record that decision with --authorization-ref.'
    if details:
        output['diagnostic'] = value
    return output
