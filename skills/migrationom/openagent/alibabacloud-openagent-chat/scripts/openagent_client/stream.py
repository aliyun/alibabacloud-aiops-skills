"""Bounded UTF-8 SSE parsing and current-run projections."""
import codecs
import json
import jsonpatch
from .common import require, ClientError
from .validation import inspect_response, event_kind
from .presentation import error_code

LIMIT = 1048576


def frames(chunks):
    decoder = codecs.getincrementaldecoder('utf-8')('strict')
    buffer, lines, size = '', [], 0
    frame_index, event_index = 0, 0
    try:
        for chunk in chunks:
            buffer += decoder.decode(chunk)
            require(len(buffer.encode('utf-8')) <= LIMIT, 'StreamLimit', 'The stream line is too large.')
            while '\n' in buffer:
                line, buffer = buffer.split('\n', 1)
                line = line.removesuffix('\r')
                require('\r' not in line, 'InvalidStream', 'Invalid line ending.')
                if line:
                    size += len(line.encode('utf-8')) + 1
                    lines.append(line)
                    require(size <= LIMIT and len(lines) <= 1024, 'StreamLimit', 'The stream frame is too large.')
                    continue
                if not lines:
                    continue
                frame_index += 1
                event, data = [], []
                for field in lines:
                    if field.startswith(':'):
                        continue
                    key, sep, value = field.partition(':')
                    if key in ('event', 'data'):
                        (event if key == 'event' else data).append(value.removeprefix(' '))
                if not data:
                    lines, size = [], 0
                    continue
                payload = json.loads('\n'.join(data))
                require(isinstance(payload, dict), 'InvalidStream', 'The stream payload is not an object.')
                if not payload.get('type') and len(event) == 1:
                    payload['type'] = event[0]
                event_index += 1
                yield payload
                lines, size = [], 0
        buffer += decoder.decode(b'', final=True)
        require(not buffer and not lines, 'IncompleteStream', 'The connection ended inside a stream frame.')
    except ClientError:
        raise
    except (ValueError, UnicodeError, RecursionError):
        raise ClientError('InvalidStream', 'The stream contains invalid text or structured data.') from None


class Projection:
    def __init__(self, session_id, mode='MESSAGE', run_id=None, parent_id=None):
        self.session_id, self.mode, self.expected_run, self.parent_id = session_id, mode, run_id, parent_id
        self.run_id = None
        self.terminal = None
        self.previous = None
        self.messages = {}
        self.message_origins = {}
        self.activities = {}
        self.tools = {}
        self.state = None
        self.has_state = False
        self.last_text = None
        self.last_tool = None
        self.count = 0
        self.compatibility = []

    def accept(self, event):
        index = self.count + 1
        diagnostic = inspect_response(event, 'event', 'AGUIEvent')
        if diagnostic and len(self.compatibility) < 8:
            self.compatibility.append(diagnostic)
        try:
            self._accept(event)
        except (KeyError, TypeError, ValueError, AttributeError):
            raise ClientError('ObservationIncomplete',
                              'A stream update is missing usable information. Read the saved task to recover its answer; do not submit the business request again.',
                              run_id=self.run_id) from None
        except ClientError as error:
            diagnostic = {'phase': 'stream_sequence', 'event_index': index,
                          'event_type': event_kind(event), 'mode': self.mode}
            mid = event.get('messageId')
            if mid is not None:
                diagnostic['message_known'] = mid in self.messages
                origin = self.message_origins.get(mid)
                if origin:
                    diagnostic.update(message_origin=origin[0], message_origin_event_index=origin[1],
                                      message_has_content='content' in self.messages[mid])
            error.result.setdefault('diagnostic', {}).update(diagnostic)
            raise

    def _accept(self, event):
        kind = event['type']
        require(self.terminal is None, 'InvalidStream', 'An event followed the task terminal.')
        if self.count == 0:
            require(kind == 'RUN_STARTED', 'InvalidStream', 'The task stream did not start correctly.')
            self.run_id = event['runId']
            require(isinstance(self.run_id, str) and self.run_id, 'ObservationIncomplete',
                    'The stream has no usable task identifier. Inspect the original operation; do not resubmit it.')
            if self.mode == 'RECONNECT':
                require(self.run_id == self.expected_run, 'ContinuationMismatch', 'The stream belongs to a different task.')
            if self.mode == 'RESUME':
                require(event.get('parentRunId') == self.parent_id, 'ContinuationMismatch', 'The resumed task has an unexpected parent.')
        else:
            require(kind != 'RUN_STARTED', 'InvalidStream', 'Duplicate task start.')
        require(event.get('sessionId', self.session_id) == self.session_id and event.get('runId', self.run_id) == self.run_id,
                'ContinuationMismatch', 'The event belongs to a different task.')
        if self.mode == 'RECONNECT' and self.count == 1:
            require(kind == 'MESSAGES_SNAPSHOT', 'InvalidStream', 'The resumed observation has no message snapshot.')
        if kind == 'MESSAGES_SNAPSHOT':
            messages = event['messages']
            require(len({m['id'] for m in messages}) == len(messages), 'InvalidStream', 'Duplicate message identifiers.')
            self.messages = {m['id']: m for m in messages}
            self.message_origins = {m['id']: ('snapshot', self.count + 1) for m in messages}
            self.tools = {t['id']: t['function']['arguments'] for m in messages for t in m.get('toolCalls', [])}
        elif kind == 'TEXT_MESSAGE_START':
            require(event['messageId'] not in self.messages, 'InvalidStream', 'Duplicate message start.')
            self.messages[event['messageId']] = {'id': event['messageId'], 'role': event['role'], 'content': ''}
            self.message_origins[event['messageId']] = ('text_start', self.count + 1)
            self.last_text = event['messageId']
        elif kind in ('TEXT_MESSAGE_CONTENT', 'TEXT_MESSAGE_CHUNK'):
            mid = event.get('messageId', self.last_text)
            require(mid is not None, 'InvalidStream', 'Missing message identity.')
            if kind == 'TEXT_MESSAGE_CONTENT':
                require(mid in self.messages, 'InvalidStream', 'Message content preceded its start.')
            self.messages.setdefault(mid, {'id': mid, 'role': event.get('role', 'assistant'), 'content': ''})
            self.message_origins.setdefault(mid, ('text_chunk', self.count + 1))
            self.messages[mid]['content'] = self.messages[mid].get('content', '') + event.get('delta', '')
            self.last_text = mid
        elif kind == 'STATE_SNAPSHOT':
            self.state, self.has_state = event['snapshot'], True
        elif kind == 'STATE_DELTA':
            require(self.has_state, 'InvalidStream', 'State updates require a snapshot.')
            self.state = self.apply_patch(self.state, event['delta'])
        elif kind == 'ACTIVITY_SNAPSHOT':
            mid = event['messageId']
            content = event['content']
            if not event.get('replace', True) and mid in self.activities:
                content = {**self.activities[mid]['content'], **content}
            self.activities[mid] = {'activityType': event['activityType'], 'content': content}
        elif kind == 'ACTIVITY_DELTA':
            activity = self.activities.get(event['messageId'])
            require(activity and activity['activityType'] == event['activityType'], 'InvalidStream', 'Activity updates require a matching snapshot.')
            activity['content'] = self.apply_patch(activity['content'], event['patch'])
        elif kind == 'TOOL_CALL_START':
            require(event['toolCallId'] not in self.tools, 'InvalidStream', 'Duplicate tool start.')
            self.tools[event['toolCallId']] = ''
            self.last_tool = event['toolCallId']
        elif kind in ('TOOL_CALL_ARGS', 'TOOL_CALL_CHUNK'):
            tid = event.get('toolCallId', self.last_tool)
            require(tid is not None, 'InvalidStream', 'Missing tool identity.')
            if kind == 'TOOL_CALL_ARGS':
                require(tid in self.tools, 'InvalidStream', 'Tool arguments preceded their start.')
            self.tools[tid] = self.tools.get(tid, '') + event.get('delta', '')
            require(len(self.tools[tid].encode()) <= LIMIT, 'StreamLimit', 'Tool arguments are too large.')
            self.last_tool = tid
        elif kind == 'TOOL_CALL_END':
            try:
                require(isinstance(json.loads(self.tools[event['toolCallId']]), dict), 'InvalidStream', 'Tool arguments must form an object.')
            except (ValueError, KeyError):
                raise ClientError('InvalidStream', 'Tool arguments are incomplete.') from None
        elif kind in ('RUN_FINISHED', 'RUN_ERROR'):
            self.terminal = event
        self.count += 1
        self.previous = kind
        require(len(self.messages) + len(self.tools) + len(self.activities) <= 4096, 'StreamLimit', 'Too many stream entities.')
        require(len(json.dumps([self.messages, self.tools, self.activities, self.state]).encode()) <= 8 * LIMIT,
                'StreamLimit', 'The current task projection is too large.')

    @staticmethod
    def apply_patch(value, patch):
        try:
            return jsonpatch.apply_patch(value, patch, in_place=False)
        except Exception:
            raise ClientError('InvalidStream', 'A state update could not be applied.') from None

    def finish(self):
        require(self.terminal is not None, 'OutcomeUnknown', 'Observation ended before the task outcome was confirmed.', run_id=self.run_id)
        result = {'session_id': self.session_id, 'run_id': self.run_id,
                  'messages': [m for m in self.messages.values() if m.get('role') in ('assistant', 'activity')],
                  'activities': self.activities}
        if self.compatibility:
            result['compatibility_warnings'] = self.compatibility
        if self.terminal['type'] == 'RUN_ERROR':
            result.update(status={'Run.Cancelled': 'cancelled', 'Session.Closed': 'closed'}.get(self.terminal.get('code'), 'failed'))
            if 'code' in self.terminal:
                result['error_code'] = error_code(self.terminal['code'])
        elif isinstance(self.terminal.get('outcome'), dict) and self.terminal['outcome'].get('type') == 'interrupt':
            result.update(status='waiting_user', interactions=self.terminal['outcome'].get('interrupts', []))
        elif isinstance(self.terminal.get('outcome'), dict) and self.terminal['outcome'].get('type') in ('success', 'completed'):
            result.update(status='completed')
        else:
            result.update(status='unknown', complete=False,
                          next_step='The stream ended without a usable outcome. Preserve the available answer and recover this same task before another action.')
        return result
