"""Offline client regression tests. Standard library only; never connect to a server."""
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest import mock

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'call-data-service-api.py'
spec = importlib.util.spec_from_file_location('dataphin_client', SCRIPT)
client = importlib.util.module_from_spec(spec)
spec.loader.exec_module(client)
OK = client.SUCCESS_CODE


class ClientTests(unittest.TestCase):
    def setUp(self):
        session_env = mock.patch.dict(os.environ, {'SKILL_SESSION_ID': '0123456789abcdef0123456789abcdef'})
        session_env.start()
        self.addCleanup(session_env.stop)
        # Block network access even if a test accidentally misses its transport mock.
        self.network = mock.patch('socket.socket', side_effect=AssertionError('Network forbidden in offline tests'))
        self.network.start()
        self.addCleanup(self.network.stop)
        self.gateway = client.Gateway('example.invalid', 'test-app', 'unit-test-secret', quiet=True)

    def fixed_headers(self, path, session='0123456789abcdef0123456789abcdef'):
        with mock.patch.object(client, 'datetime') as dt, \
             mock.patch.object(client.uuid, 'uuid4', return_value='00000000-0000-0000-0000-000000000001'), \
             mock.patch.object(client.time, 'time', return_value=1788912000), \
             mock.patch.dict(os.environ, {'SKILL_SESSION_ID': session}):
            dt.now.return_value = '2026-09-09 00:00:00'
            return self.gateway._headers(path)

    def test_signature_matches_sdk_golden_vector(self):
        # Independently computed with the original SDK signature_composer + sha_hmac256.
        headers = self.fixed_headers('/list/101?appKey=test-app&env=PROD')
        self.assertEqual(headers['x-ca-signature'], 'QLCFd8PJSJ0z3Sjujkcx5xuGqdDtqYe8EUuMtvZa/6o=')
        self.assertEqual(headers['x-ca-signature-headers'],
                         'x-ca-key,x-ca-nonce,x-ca-signature-method,x-ca-stage,x-ca-timestamp')
        self.assertNotIn('content-md5', headers)

    def test_session_does_not_affect_signature(self):
        path = '/list/101?appKey=test-app&env=PROD'
        first, second = self.fixed_headers(path, '1'*32), self.fixed_headers(path, '2'*32)
        self.assertEqual(first['x-ca-signature'], second['x-ca-signature'])
        self.assertIn('/' + '1'*32 + ' skill-version/', first['user-agent'])
        self.assertIn('/' + '2'*32 + ' skill-version/', second['user-agent'])
        self.assertNotIn('x-ca-user-agent', first)

    def test_query_string_signed_verbatim(self):
        one = self.fixed_headers('/list/101?b=%2F&a=1')['x-ca-signature']
        two = self.fixed_headers('/list/101?a=1&b=%2F')['x-ca-signature']
        self.assertNotEqual(one, two)

    def test_method_mapping_and_data_environment(self):
        self.gateway.env = 'PRE'
        for method in ['LIST', 'GET', 'CREATE', 'UPDATE', 'DELETE']:
            self.assertEqual(self.gateway.api_path('101', method),
                             '/' + method.lower() + '/101?appKey=test-app&env=PRE')

    def connection(self, response):
        conn = mock.Mock()
        conn.getresponse.return_value = response
        patcher = mock.patch.object(self.gateway, '_connect', return_value=conn)
        patcher.start()
        self.addCleanup(patcher.stop)
        return conn

    def test_sync_preserves_body_path_and_response(self):
        body = {'conditions': {'tag': ['a', 'b']}, 'returnFields': ['id'], 'keepColumnCase': True}
        answer = {'code': OK, 'result': {'id': 1}}
        conn = self.connection(mock.Mock(status=200, read=mock.Mock(return_value=json.dumps(answer).encode())))
        self.assertEqual(self.gateway.call('101', 'GET', body), answer)
        args, kwargs = conn.request.call_args
        self.assertEqual(args, ('POST', '/get/101?appKey=test-app&env=PROD'))
        self.assertEqual(json.loads(kwargs['body']), body)
        conn.close.assert_called_once()

    def test_http_error_closes_connection(self):
        conn = self.connection(mock.Mock(status=403, read=mock.Mock(return_value=b'Forbidden')))
        with self.assertRaisesRegex(RuntimeError, 'HTTP 403'):
            self.gateway.call('101', 'LIST', {})
        conn.close.assert_called_once()

    def test_async_pagination_and_close(self):
        replies = [dict(code=OK, jobId='job-test'), dict(code=OK, result={'status': 1}),
                   dict(code=OK, result={'status': 2}), dict(code=OK, results=[{'id': 1}]),
                   dict(code=OK, results=[{'id': 2}]), dict(code=OK, results=[]), dict(code=OK)]
        with mock.patch.object(self.gateway, '_post', side_effect=replies) as post, \
             mock.patch.object(client.time, 'sleep'):
            result = self.gateway.async_call('101', 'LIST', {})
        self.assertEqual(result['results'], [{'id': 1}, {'id': 2}])
        paths = [c.args[0].split('?')[0] for c in post.call_args_list]
        self.assertEqual(paths, ['/list/101', '/getJobStatus', '/getJobStatus',
                                 '/getJobResult', '/getJobResult', '/getJobResult', '/closeJob'])

    def test_async_without_job_returns_sync_response(self):
        answer = dict(code=OK, result={'id': 1})
        with mock.patch.object(self.gateway, '_post', return_value=answer) as post:
            self.assertEqual(self.gateway.async_call('101', 'GET', {}), answer)
        post.assert_called_once()

    def test_async_failure_closes_job(self):
        replies = [dict(code=OK, jobId='job-test'), dict(code=OK, result={'status': 3}),
                   dict(code=OK, result='test failure'), dict(code=OK)]
        with mock.patch.object(self.gateway, '_post', side_effect=replies) as post, \
             mock.patch.object(client.time, 'sleep'):
            with self.assertRaises(RuntimeError): self.gateway.async_call('101', 'LIST', {})
        self.assertTrue(post.call_args.args[0].startswith('/closeJob?'))

    def test_async_timeout_still_closes_job(self):
        with mock.patch.object(self.gateway, '_post', side_effect=[dict(code=OK, jobId='job-test'), dict(code=OK)]) as post:
            with self.assertRaises(TimeoutError): self.gateway.async_call('101', 'LIST', {}, timeout=0)
        self.assertTrue(post.call_args.args[0].startswith('/closeJob?'))

    def test_sse_frames(self):
        response = mock.Mock(status=200)
        response.getheader.return_value = 'text/event-stream'
        response.readline.side_effect = [b'data:{"id":1}\n', b'\n', b'data:{"id":2}\n', b'\n', b'']
        conn = self.connection(response)
        self.assertEqual(list(self.gateway.sse('101', 'GET', {})), [{'id': 1}, {'id': 2}])
        self.assertEqual(conn.request.call_args.kwargs['headers']['accept'], 'text/event-stream')
        conn.close.assert_called_once()

    def test_sse_json_fallback(self):
        answer = dict(code=OK, result={'id': 1})
        response = mock.Mock(status=200, read=mock.Mock(return_value=json.dumps(answer).encode()))
        response.getheader.return_value = 'application/json'
        self.connection(response)
        self.assertEqual(list(self.gateway.sse('101', 'GET', {})), [answer])

    def test_cli_help_without_site_packages_or_credentials(self):
        for args in [[], ['call'], ['async-call'], ['sse']]:
            result = subprocess.run([sys.executable, '-I', '-S', str(SCRIPT), *args, '--help'],
                                    capture_output=True, text=True, env={}, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
        result = subprocess.run([sys.executable, '-I', '-S', str(SCRIPT), 'call', '--api-id', '101', '--method', 'LIST'],
                                capture_output=True, text=True, env={}, timeout=10)
        self.assertEqual(result.returncode, 2)
        self.assertIn('DATAPHIN_APP_KEY', result.stderr)

    def test_cli_business_error_exit_status(self):
        with mock.patch.object(sys, 'argv', ['client', 'call', '--api-id', '101', '--method', 'LIST']), \
             mock.patch.object(client, '_build_gateway') as build, \
             mock.patch('sys.stdout', new_callable=io.StringIO):
            build.return_value.call.return_value = {'code': 'TEST_ERROR', 'message': 'test error'}
            with self.assertRaises(SystemExit) as context: client.main()
        self.assertEqual(context.exception.code, 1)


if __name__ == '__main__':
    unittest.main()
