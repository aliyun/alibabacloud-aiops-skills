"""Regression cases derived from run32245; never call a live cloud service."""
import argparse
import base64
import hashlib
import json
import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from test_idaas_saml_idp import MODULE as m, args_for, METADATA, SP_METADATA


class Run32245RegressionTest(unittest.TestCase):
    def prepare(self, directory):
        source = Path(directory) / 'original.xml'
        source.write_text(METADATA)
        pin = hashlib.sha256(base64.b64decode('MAMCAQE=')).hexdigest()
        args = args_for(str(source), expected_certificate_sha256=[pin],
                        input_guard_file=str(Path(directory) / 'constraints.json'),
                        confirm='CREATE', accept_warnings=True)
        return source, pin, args

    @patch.object(m, 'cli')
    def test_dropping_pin_after_failed_resolution_cannot_create_or_update(self, cli):
        with tempfile.TemporaryDirectory() as directory:
            source, pin, args = self.prepare(directory)
            source.write_text(METADATA.replace('MAMCAQE=', 'MAMCAQI='))
            with self.assertRaisesRegex(m.SkillError, 'mismatch'):
                m.resolve(args)
            args.expected_certificate_sha256 = None
            for action in ['CREATE', 'UPDATE']:
                args.confirm = action
                args.idp_id = 'idp_original'
                with self.subTest(action=action), self.assertRaisesRegex(m.SkillError, 'mismatch'):
                    (m.create if action == 'CREATE' else m.update)(args)
            cli.assert_not_called()

    @patch.object(m, 'cli', side_effect=[{'IdentityProviders': [], 'TotalCount': 0}, {'IdentityProviderId': 'idp_created', 'RequestId': 'request'}])
    def test_restoring_original_source_allows_create_without_changing_saved_pin(self, cli):
        with tempfile.TemporaryDirectory() as directory:
            source, pin, args = self.prepare(directory)
            source.write_text(METADATA.replace('MAMCAQE=', 'MAMCAQI='))
            with self.assertRaises(m.SkillError):
                m.resolve(args)
            source.write_text(METADATA)
            args.expected_certificate_sha256 = None
            result = m.create(args)
            self.assertEqual('idp_created', result['identityProviderId'])
            self.assertEqual(2, cli.call_count)
            saved = json.loads(Path(args.input_guard_file).read_text())
            self.assertEqual([[pin]], list(saved['sources'].values()))

    @patch.object(m, 'cli')
    def test_new_pin_cannot_override_original_constraint(self, cli):
        with tempfile.TemporaryDirectory() as directory:
            _, _, args = self.prepare(directory)
            m.resolve(args)
            args.expected_certificate_sha256 = ['00' * 32]
            with self.assertRaisesRegex(m.SkillError, 'conflicts with the original pin'):
                m.create(args)
            cli.assert_not_called()

    @patch.object(m, 'cli')
    def test_corrupt_and_locked_constraints_stop_before_write(self, cli):
        with tempfile.TemporaryDirectory() as directory:
            _, _, args = self.prepare(directory)
            guard = Path(args.input_guard_file)
            guard.write_text('not json')
            with self.assertRaisesRegex(m.SkillError, 'Cannot read metadata constraints'):
                m.create(args)
            guard.unlink()
            lock = guard.with_name(guard.name + '.lock')
            lock.write_text('')
            with self.assertRaisesRegex(m.SkillError, 'locked'):
                m.create(args)
            args.expected_certificate_sha256 = None
            with self.assertRaisesRegex(m.SkillError, 'locked'):
                m.create(args)
            cli.assert_not_called()

    @patch.object(m, 'cli')
    def test_parser_default_preserves_failed_pin_between_commands(self, cli):
        with tempfile.TemporaryDirectory() as directory:
            source, pin, _ = self.prepare(directory)
            source.write_text(METADATA.replace('MAMCAQE=', 'MAMCAQI='))
            previous = os.getcwd()
            try:
                os.chdir(directory)
                resolve_args = m.build_parser().parse_args([
                    'resolve', '--instance-id', 'idaas_test', '--metadata-file', str(source),
                    '--expected-certificate-sha256', pin,
                ])
                with self.assertRaisesRegex(m.SkillError, 'mismatch'):
                    m.resolve(resolve_args)
                create_args = m.build_parser().parse_args([
                    'create', '--instance-id', 'idaas_test', '--name', 'test',
                    '--metadata-file', str(source), '--confirm', 'CREATE', '--accept-warnings',
                ])
                with self.assertRaisesRegex(m.SkillError, 'mismatch'):
                    m.create(create_args)
                cli.assert_not_called()
            finally:
                os.chdir(previous)

    def test_constraints_for_distinct_sources_do_not_block_each_other(self):
        with tempfile.TemporaryDirectory() as directory:
            _, _, args = self.prepare(directory)
            m.resolve(args)
            other = Path(directory) / 'other.xml'
            other.write_text(METADATA.replace('MAMCAQE=', 'MAMCAQI='))
            args.metadata_file = str(other)
            args.expected_certificate_sha256 = [hashlib.sha256(base64.b64decode('MAMCAQI=')).hexdigest()]
            self.assertEqual('local-file', m.resolve(args)['resolvedBy'])

    def sp_args(self, directory):
        source = Path(directory) / 'downloaded-original.xml'
        source.write_bytes(SP_METADATA)
        args = argparse.Namespace(instance_id='idaas_test', idp_id='idp_test', output_mode='raw',
                                  raw_input_file=str(source), output_file=str(Path(directory) / 'sp.xml'))
        return source, args

    def endpoint(self):
        return {'EndpointMetadata': {'SamlMetaEndpoint': 'https://idaas.example.com/meta',
                                     'SamlEntityId': 'https://idaas.example.com/meta',
                                     'SamlAcsEndpoint': 'https://idaas.example.com/acs'}}

    @patch.object(m, 'fetch_sp_metadata', side_effect=AssertionError('Provided recovery must not redownload'))
    @patch.object(m, 'show')
    def test_exact_target_original_xml_recovers_handoff_and_retains_provenance(self, show, fetch):
        show.return_value = self.endpoint()
        with tempfile.TemporaryDirectory() as directory:
            source, args = self.sp_args(directory)
            result = m.sp_metadata(args)
            self.assertEqual('user-supplied-file', result['rawMetadataSource'])
            self.assertEqual(SP_METADATA, Path(args.output_file).read_bytes())
            self.assertEqual(SP_METADATA.decode(), result['rawMetadataXml'])
            markdown = m.sp_handoff_markdown(result)
            self.assertIn('user-supplied-file', markdown)
            self.assertIn(SP_METADATA.decode(), markdown)
            self.assertIn('```xml', markdown)
            fetch.assert_not_called()
            show.assert_called_once_with(args)

    @patch.object(m, 'show')
    def test_other_target_or_acs_html_and_oversize_cannot_be_delivered(self, show):
        show.return_value = self.endpoint()
        variants = [SP_METADATA.replace(b'entityID="https://idaas.example.com/meta"', b'entityID="https://other.example.com/meta"'),
                    SP_METADATA.replace(b'Location="https://idaas.example.com/acs"', b'Location="https://other.example.com/acs"'),
                    b'<html>WAF denied</html>', b'x' * (m.MAX_METADATA_BYTES + 1)]
        with tempfile.TemporaryDirectory() as directory:
            source, args = self.sp_args(directory)
            for body in variants:
                with self.subTest(body=body[:70]):
                    source.write_bytes(body)
                    with self.assertRaises(m.SkillError):
                        m.sp_metadata(args)
                    self.assertFalse(Path(args.output_file).exists())

    @patch.object(m, 'show')
    def test_supplied_xml_requires_both_authoritative_endpoints(self, show):
        show.return_value = {'EndpointMetadata': {'SamlMetaEndpoint': 'https://idaas.example.com/meta'}}
        with tempfile.TemporaryDirectory() as directory:
            _, args = self.sp_args(directory)
            with self.assertRaisesRegex(m.SkillError, 'without the target'):
                m.sp_metadata(args)

    def test_fields_handoff_contains_all_final_answer_labels_and_values(self):
        result = {'outputMode': 'fields', 'spMetadataUrl': 'https://idaas.example.com/meta',
                  'spEntityId': 'https://idaas.example.com/entity', 'spAcsUrl': 'https://idaas.example.com/acs'}
        answer = m.sp_handoff_markdown(result)
        for value in ['SP Metadata URL', 'SP Entity ID', 'ACS URL', *list(result.values())[1:]]:
            self.assertIn(value, answer)

    def test_field_labels_cannot_turn_missing_endpoint_into_complete_handoff(self):
        with self.assertRaisesRegex(m.SkillError, 'incomplete'):
            m.sp_handoff_markdown({'outputMode': 'fields', 'spMetadataUrl': 'https://idaas.example.com/meta'})

    @patch.object(m, 'sp_metadata')
    def test_markdown_cli_and_unchanged_default_json_cli(self, handler):
        handler.return_value = {'outputMode': 'fields', 'spMetadataUrl': 'https://idaas.example.com/meta',
                                'spEntityId': 'https://idaas.example.com/entity', 'spAcsUrl': 'https://idaas.example.com/acs'}
        command = ['skill', 'sp-metadata', '--instance-id', 'idaas_test', '--idp-id', 'idp_test']
        for flags in [[], ['--output-format', 'markdown']]:
            output = io.StringIO()
            with self.subTest(flags=flags), patch.object(m.sys, 'argv', command + flags), redirect_stdout(output):
                self.assertEqual(0, m.main())
            if not flags:
                self.assertEqual(handler.return_value, json.loads(output.getvalue()))
            else:
                self.assertIn('SP Entity ID: https://idaas.example.com/entity', output.getvalue())


if __name__ == '__main__':
    unittest.main()
