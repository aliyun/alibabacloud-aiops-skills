"""Executable regressions for request14209; all cloud calls are mocked."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from test_idaas_saml_idp import MODULE as m, args_for, METADATA, CERT_PEM

EMPTY={'IdentityProviders':[], 'TotalCount':0, 'RequestId':'list_1'}
CREATED={'IdentityProviderId':'idp_created', 'RequestId':'create_1'}

class ExecutableWorkflowTest(unittest.TestCase):
    def args(self, directory, **overrides):
        p=Path(directory);src=p/'original.xml';src.write_text(METADATA)
        values=dict(confirm='CREATE', state_file=str(p/'state.json'),
                    input_guard_file=str(p/'constraints.json'))
        values.update(overrides)
        return args_for(str(src),**values)

    def test_resolve_persists_actual_computed_values_without_shell_redirect(self):
        with tempfile.TemporaryDirectory() as d:
            a=self.args(d,output_file=str(Path(d)/'outputs/metadata-resolution.json'))
            result=m.resolve(a)
            self.assertEqual(result,json.loads(Path(a.output_file).read_text()))
            self.assertEqual(m.certificate_summary(CERT_PEM)['sha256'].replace(':','').lower(),result['certificateSha256'])
            self.assertEqual('outputs/metadata-resolution.json',m.build_parser().parse_args(['resolve','--instance-id','idaas_test','--metadata-file',a.metadata_file]).output_file)

    def test_invalid_constraint_schema_stops_without_read_or_write_api(self):
        with tempfile.TemporaryDirectory() as d:
            a=self.args(d);p=Path(a.input_guard_file);original='{"instanceId":"idaas_test"}';p.write_text(original)
            with patch.object(m,'cli') as cli,self.assertRaisesRegex(m.SkillError,'script-owned'):
                m.create(a)
            cli.assert_not_called();self.assertEqual(original,p.read_text())
            self.assertFalse(Path(a.state_file).exists())

    def test_create_really_lists_before_post_and_returns_bound_receipt(self):
        with tempfile.TemporaryDirectory() as d:
            a=self.args(d,idp_quota=5)
            with patch.object(m,'cli',side_effect=[EMPTY,CREATED]) as cli:
                result=m.create(a)
            self.assertEqual(['ListIdentityProviders','CreateIdentityProvider'],[c.args[1] for c in cli.call_args_list])
            self.assertEqual('list_1',result['creationPreflight']['requestIds'][0])
            self.assertEqual('create_1',result['writeReceipt']['requestId'])
            submitted=cli.call_args_list[1].args[2];cert=submitted[submitted.index('--SamlConfig.Certificates.1.Content')+1]
            fp=m.certificate_summary(cert)['sha256'].replace(':','').lower()
            self.assertEqual([fp],result['writeReceipt']['submittedCertificateSha256s'])
            self.assertEqual(result,json.loads(Path(a.state_file).read_text())['result'])

    def test_existing_entity_conflict_blocks_post_and_pending_state(self):
        with tempfile.TemporaryDirectory() as d:
            a=self.args(d);listing={'TotalCount':1,'IdentityProviders':[{'IdentityProviderId':'idp_other','IdentityProviderExternalId':'urn:example:idp'}]}
            with patch.object(m,'cli',return_value=listing) as cli,self.assertRaisesRegex(m.SkillError,'existing IdP'):
                m.create(a)
            self.assertEqual(['ListIdentityProviders'],[c.args[1] for c in cli.call_args_list])
            self.assertFalse(Path(a.state_file).exists())

    def test_conflict_on_later_inventory_page_blocks_post(self):
        with tempfile.TemporaryDirectory() as d:
            a=self.args(d)
            first={'TotalCount':101,'IdentityProviders':[{'IdentityProviderId':f'idp_{n}','IdentityProviderExternalId':f'urn:other:{n}'} for n in range(100)]}
            last={'TotalCount':101,'IdentityProviders':[{'IdentityProviderId':'idp_conflict','IdentityProviderExternalId':'urn:example:idp'}]}
            with patch.object(m,'cli',side_effect=[first,last]) as cli,self.assertRaisesRegex(m.SkillError,'existing IdP'):
                m.create(a)
            self.assertEqual(2,cli.call_count);self.assertIn('2',cli.call_args_list[1].args[2])
            self.assertFalse(Path(a.state_file).exists())

    def test_known_quota_stops_before_post_but_no_universal_limit_is_invented(self):
        listing={'TotalCount':5,'IdentityProviders':[{'IdentityProviderId':f'idp_{n}','IdentityProviderExternalId':f'urn:other:{n}'} for n in range(5)]}
        with tempfile.TemporaryDirectory() as d:
            a=self.args(d,idp_quota=5)
            with patch.object(m,'cli',return_value=listing) as cli,self.assertRaisesRegex(m.SkillError,'quota is full'):
                m.create(a)
            self.assertEqual(1,cli.call_count);self.assertFalse(Path(a.state_file).exists())
            a.idp_quota=None
            with patch.object(m,'cli',side_effect=[listing,CREATED]):
                self.assertEqual('idp_created',m.create(a)['identityProviderId'])

    def test_missing_incomplete_or_changing_inventory_cannot_create(self):
        bad_sequences=[[{}],[{'TotalCount':1,'IdentityProviders':[]}],[{'TotalCount':1,'IdentityProviders':[{}]}],[{'TotalCount':2,'IdentityProviders':[{'IdentityProviderId':'idp_one'},{'IdentityProviderId':'idp_one'}]}],
                       [{'TotalCount':2,'IdentityProviders':[{'IdentityProviderId':'idp_one'}]},EMPTY]]
        for seq in bad_sequences:
            with self.subTest(seq=seq),tempfile.TemporaryDirectory() as d:
                a=self.args(d)
                with patch.object(m,'cli',side_effect=seq) as cli,self.assertRaises(m.SkillError):m.create(a)
                self.assertTrue(all(c.args[1]=='ListIdentityProviders' for c in cli.call_args_list))
                self.assertFalse(Path(a.state_file).exists())

    def test_completed_state_reentry_does_not_relist_or_recreate(self):
        with tempfile.TemporaryDirectory() as d:
            a=self.args(d)
            with patch.object(m,'cli',side_effect=[EMPTY,CREATED]):m.create(a)
            with patch.object(m,'cli') as cli:
                result=m.create(a)
            cli.assert_not_called();self.assertTrue(result['reusedCreationResult'])

    def test_older_completed_state_also_returns_absolute_state_path(self):
        with tempfile.TemporaryDirectory() as d:
            a=self.args(d)
            with patch.object(m,'cli',side_effect=[EMPTY,CREATED]):m.create(a)
            saved=json.loads(Path(a.state_file).read_text())
            saved['result'].pop('creationStateFile')
            Path(a.state_file).write_text(json.dumps(saved))
            with patch.object(m,'cli') as cli:resumed=m.create(a)
            cli.assert_not_called()
            self.assertEqual(str(Path(a.state_file).resolve()),resumed['creationStateFile'])
            self.assertEqual('idp_created',resumed['identityProviderId'])

    def test_absolute_state_from_first_round_survives_a_new_current_directory(self):
        import os
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            a=self.args(first)
            with patch.object(m,'cli',side_effect=[EMPTY,CREATED]):
                created=m.create(a)
            self.assertTrue(Path(created['creationStateFile']).is_absolute())
            original=os.getcwd()
            try:
                os.chdir(second)
                a.state_file=created['creationStateFile']
                with patch.object(m,'cli') as cli:
                    resumed=m.create(a)
                cli.assert_not_called()
                self.assertEqual('idp_created',resumed['identityProviderId'])
                self.assertTrue(resumed['reusedCreationResult'])
                # A new cwd cannot authorize another target with the old state.
                a.instance_id='idaas_other'
                with patch.object(m,'cli') as cli,self.assertRaisesRegex(m.SkillError,'different configuration'):m.create(a)
                cli.assert_not_called()
            finally:os.chdir(original)

    def test_nested_success_id_is_saved_and_missing_id_retains_request(self):
        with tempfile.TemporaryDirectory() as d:
            a=self.args(d)
            with patch.object(m,'cli',side_effect=[EMPTY,{'data':{'IdentityProviderId':'idp_nested'},'RequestId':'nested_request'}]):
                self.assertEqual('idp_nested',m.create(a)['identityProviderId'])
        with tempfile.TemporaryDirectory() as d:
            a=self.args(d)
            with patch.object(m,'cli',side_effect=[EMPTY,{'RequestId':'unknown_id_request'}]),self.assertRaisesRegex(m.SkillError,'no IdP ID'):
                m.create(a)
            saved=json.loads(Path(a.state_file).read_text());self.assertEqual('pending',saved['status'])
            self.assertEqual('unknown_id_request',saved['lastResult']['requestId'])
            self.assertTrue(saved['clientToken'])
            with patch.object(m,'cli') as cli,self.assertRaisesRegex(m.SkillError,'uncertain outcome'):m.create(a)
            cli.assert_not_called()

    def test_timeout_keeps_same_client_token_and_no_second_post(self):
        with tempfile.TemporaryDirectory() as d:
            a=self.args(d)
            with patch.object(m,'cli',side_effect=[EMPTY,m.SkillError('timeout')]),self.assertRaises(m.SkillError):m.create(a)
            before=Path(a.state_file).read_text()
            with patch.object(m,'cli') as cli,self.assertRaisesRegex(m.SkillError,'uncertain outcome'):m.create(a)
            cli.assert_not_called();self.assertEqual(before,Path(a.state_file).read_text())

if __name__=='__main__':unittest.main()
