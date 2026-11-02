"""Replay run32294 failures offline; no cloud writes or network calls."""
import argparse
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from test_idaas_saml_idp import MODULE as m, args_for, METADATA, SP_METADATA

DETAIL = {'IdentityProviderId': 'idp_test', 'AuthnConfig': {'AuthnStatus': 'disabled'},
          'SamlConfig': {'SamlMetaEndpoint': 'https://idaas.example.com/meta',
                         'SamlEntityId': 'https://idaas.example.com/meta',
                         'SamlAcsEndpoint': 'https://idaas.example.com/acs'}}

class Run32294RegressionTest(unittest.TestCase):
    def args(self, directory, **extra):
        values = dict(profile='default', region='cn-hangzhou', instance_id='idaas_test',
                      idp_id='idp_test', confirm='ENABLE', skip_check=False, timeout=1, interval=0,
                      output_mode='raw', raw_input_file=None, output_file=str(Path(directory)/'sp.xml'),
                      handoff_state_file=str(Path(directory)/'journal.json'))
        values.update(extra)
        return argparse.Namespace(**values)

    def test_resolve_redirected_json_has_computed_top_level_fields(self):
        with tempfile.TemporaryDirectory() as d:
            source=Path(d)/'idp.xml'; source.write_text(METADATA)
            r=m.resolve(args_for(str(source)))
            self.assertEqual(r['metadata']['entityId'], r['entityId'])
            self.assertEqual(hashlib.sha256(__import__('base64').b64decode('MAMCAQE=')).hexdigest(), r['certificateSha256'])
            self.assertTrue(r['ssoUrl'])
            self.assertIn('metadata',r)

    def test_unsupported_check_reads_exact_target_and_retains_original_error(self):
        with tempfile.TemporaryDirectory() as d:
            a=self.args(d)
            with patch.object(m,'cli',side_effect=[m.SkillError('UnsupportedAction: original'),DETAIL]) as cli:
                r=m.check(a)
            self.assertEqual('GetIdentityProvider',cli.call_args_list[1].args[1])
            self.assertIn('idp_test',cli.call_args_list[1].args[2])
            self.assertEqual(('idaas_test','idp_test','unsupported',True),
                             (r['instanceId'],r['identityProviderId'],r['outcome'],r['readbackVerified']))
            self.assertIn('original',r['serviceError'])
            self.assertFalse(r['supported'])

    def test_failed_or_wrong_readback_never_verified(self):
        with tempfile.TemporaryDirectory() as d:
            for reply in [m.SkillError('Forbidden'), {'IdentityProviderId':'idp_other'}]:
                with self.subTest(reply=reply),patch.object(m,'cli',side_effect=[m.SkillError('UnsupportedAction'),reply]):
                    self.assertFalse(m.check(self.args(d))['readbackVerified'])

    def test_other_errors_are_not_unsupported(self):
        with tempfile.TemporaryDirectory() as d:
            for error in ['Forbidden','InvalidParameter','Throttling']:
                with self.subTest(error=error),patch.object(m,'cli',side_effect=m.SkillError(error)):
                    with self.assertRaises(m.SkillError):m.check(self.args(d))

    def test_failed_and_timed_out_jobs_cannot_allow_staged_enable(self):
        with tempfile.TemporaryDirectory() as d:
            for status in ['failed','completed']:
                with patch.object(m,'cli',side_effect=[{'IdentityProviderStatusCheckJobId':'job'}, {'Status':status}]):
                    self.assertEqual('failed',m.check(self.args(d))['outcome'])
            with patch.object(m,'cli',return_value={'IdentityProviderStatusCheckJobId':'job'}):
                self.assertEqual('failed',m.check(self.args(d,timeout=0))['outcome'])

    def test_waf_then_enable_confirmation_still_blocks_without_cloud_write(self):
        with tempfile.TemporaryDirectory() as d:
            a=self.args(d)
            with patch.object(m,'show',return_value=DETAIL),patch.object(m,'fetch_sp_metadata',side_effect=m.SkillError('WAF HTML')):
                with self.assertRaisesRegex(m.SkillError,'Ask ONLY for original SP XML'):m.sp_metadata(a)
            with patch.object(m,'cli') as cli:
                with self.assertRaisesRegex(m.SkillError,'handoff is incomplete'):m.enable(a)
                cli.assert_not_called()
            a.output_mode='fields';a.output_file=None
            with patch.object(m,'show',return_value=DETAIL):m.sp_metadata(a)
            self.assertFalse(m.handoff_state(a)['spComplete'])

    def complete(self,a):
        with patch.object(m,'show',return_value=DETAIL),patch.object(m,'fetch_sp_metadata',return_value=SP_METADATA):m.sp_metadata(a)
        with patch.object(m,'cli',side_effect=[m.SkillError('UnsupportedAction'),DETAIL]):m.check(a)

    def test_verified_original_and_check_allow_exact_target_enable(self):
        with tempfile.TemporaryDirectory() as d:
            a=self.args(d);self.complete(a)
            with patch.object(m,'cli',side_effect=[DETAIL,{'RequestId':'enable'}]) as cli:
                self.assertTrue(m.enable(a)['enabled'])
            self.assertEqual('EnableIdentityProviderAuthn',cli.call_args_list[-1].args[1])
            self.assertIn('idp_test',cli.call_args_list[-1].args[2])

    def test_altered_missing_or_foreign_raw_blocks(self):
        with tempfile.TemporaryDirectory() as d:
            a=self.args(d);self.complete(a)
            for content in [b'<html>WAF</html>',SP_METADATA.replace(b'idaas.example.com',b'other.example.com')]:
                Path(a.output_file).write_bytes(content)
                with patch.object(m,'cli',return_value=DETAIL) as cli:
                    with self.assertRaises(m.SkillError):m.enable(a)
                    self.assertTrue(all(c.args[1]!='EnableIdentityProviderAuthn' for c in cli.call_args_list))
            Path(a.output_file).unlink()
            with patch.object(m,'show',return_value=DETAIL),self.assertRaises(m.SkillError):m.enable(a)

    def test_supplied_foreign_xml_never_completes_handoff(self):
        with tempfile.TemporaryDirectory() as d:
            a=self.args(d);a.raw_input_file=str(Path(d)/'foreign.xml')
            Path(a.raw_input_file).write_bytes(SP_METADATA.replace(b'idaas.example.com',b'other.example.com'))
            with patch.object(m,'show',return_value=DETAIL),self.assertRaises(m.SkillError):m.sp_metadata(a)
            self.assertFalse(m.handoff_state(a)['spComplete'])

    def test_profile_and_target_journals_are_separate_and_normal_enable_unchanged(self):
        with tempfile.TemporaryDirectory() as d:
            a=self.args(d);m.handoff_state(a,{'staged':True,'spComplete':False})
            b=self.args(d,profile='other')
            self.assertEqual({},m.handoff_state(b))
            with patch.object(m,'cli',return_value={}):self.assertTrue(m.enable(b)['enabled'])
            with patch.object(m,'cli') as cli,self.assertRaises(m.SkillError):m.enable(a)
            cli.assert_not_called()

    def test_later_check_failure_invalidates_older_success(self):
        with tempfile.TemporaryDirectory() as d:
            a=self.args(d);self.complete(a)
            with patch.object(m,'cli',side_effect=m.SkillError('Forbidden')),self.assertRaises(m.SkillError):m.check(a)
            with patch.object(m,'cli') as cli,self.assertRaises(m.SkillError):m.enable(a)
            cli.assert_not_called()

    def test_successful_job_records_supported_without_claiming_real_sso(self):
        with tempfile.TemporaryDirectory() as d:
            with patch.object(m,'cli',side_effect=[{'IdentityProviderStatusCheckJobId':'job'},{'Status':'Success'}]):
                result=m.check(self.args(d))
            self.assertEqual('supported',result['outcome'])
            self.assertFalse(result['readbackVerified'])
            self.assertNotIn('ssoPassed',result)

    def test_fresh_official_endpoints_must_still_match_original(self):
        with tempfile.TemporaryDirectory() as d:
            a=self.args(d);self.complete(a)
            different=json.loads(json.dumps(DETAIL));different['SamlConfig']['SamlAcsEndpoint']='https://other.example.com/acs'
            with patch.object(m,'cli',return_value=different) as cli,self.assertRaises(m.SkillError):m.enable(a)
            self.assertTrue(all(c.args[1]!='EnableIdentityProviderAuthn' for c in cli.call_args_list))

    def test_parser_carries_journal_across_separate_commands(self):
        import os
        with tempfile.TemporaryDirectory() as d:
            previous=os.getcwd()
            try:
                os.chdir(d)
                parser=m.build_parser()
                flags=['--instance-id','idaas_test','--idp-id','idp_test']
                sp=parser.parse_args(['sp-metadata',*flags,'--output-mode','raw'])
                with patch.object(m,'show',return_value=DETAIL),patch.object(m,'fetch_sp_metadata',side_effect=m.SkillError('WAF')):
                    with self.assertRaises(m.SkillError):m.sp_metadata(sp)
                en=parser.parse_args(['enable',*flags,'--confirm','ENABLE'])
                with patch.object(m,'cli') as cli,self.assertRaises(m.SkillError):m.enable(en)
                cli.assert_not_called()
            finally:os.chdir(previous)

    def test_corrupt_or_locked_journal_blocks_enable(self):
        with tempfile.TemporaryDirectory() as d:
            a=self.args(d);p=Path(a.handoff_state_file);p.write_text('bad')
            with patch.object(m,'cli') as cli,self.assertRaises(m.SkillError):m.enable(a)
            cli.assert_not_called();p.unlink();p.with_name(p.name+'.lock').touch()
            with patch.object(m,'cli') as cli,self.assertRaises(m.SkillError):m.enable(a)
            cli.assert_not_called()

if __name__=='__main__':unittest.main()
