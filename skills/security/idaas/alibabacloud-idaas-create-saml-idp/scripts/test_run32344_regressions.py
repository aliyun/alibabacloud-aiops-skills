"""Replay final-handoff failures with a real journal, without live cloud writes."""
import argparse
import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from test_idaas_saml_idp import MODULE as m, SP_METADATA

DETAIL = {'InstanceId': 'idaas_test', 'IdentityProviderId': 'idp_test',
          'AuthnStatus': 'disabled', 'SamlConfig': {
              'SamlMetaEndpoint': 'https://idaas.example.com/meta',
              'SamlEntityId': 'https://idaas.example.com/meta',
              'SamlAcsEndpoint': 'https://idaas.example.com/acs'}}

class FinalHandoffTest(unittest.TestCase):
    def prepare(self, directory, mode='raw'):
        args = argparse.Namespace(profile='default', region='cn-hangzhou',
            instance_id='idaas_test', idp_id='idp_test', confirm='ENABLE',
            output_mode=mode, output_file=str(Path(directory)/'sp.xml') if mode=='raw' else None,
            raw_input_file=None, handoff_state_file=str(Path(directory)/'journal.json'))
        with patch.object(m, 'show', return_value=DETAIL), patch.object(m, 'fetch_sp_metadata', return_value=SP_METADATA):
            original = m.sp_metadata(args)
        m.check_result(args, {'readbackVerified':True, 'serviceError':'UnsupportedAction'}, 'unsupported')
        return args, original

    def test_raw_enable_repeats_complete_exact_xml_without_network_download(self):
        with tempfile.TemporaryDirectory() as directory:
            args, original = self.prepare(directory)
            with patch.object(m, 'cli', side_effect=[DETAIL, {'RequestId':'enabled'}]) as cli, patch.object(m, 'fetch_sp_metadata') as fetch:
                result=m.enable(args)
            self.assertTrue(result['enabled'])
            self.assertEqual(original['rawMetadataXml'], result['spHandoff']['rawMetadataXml'])
            self.assertIn('```xml\n'+original['rawMetadataXml']+'\n```', result['spHandoffMarkdown'])
            self.assertIn(original['spMetadataUrl'], result['spHandoffMarkdown'])
            fetch.assert_not_called()
            self.assertEqual(['GetIdentityProvider', 'EnableIdentityProviderAuthn'], [c.args[1] for c in cli.call_args_list])

    def test_fields_enable_has_all_three_actual_values(self):
        with tempfile.TemporaryDirectory() as directory:
            args, original = self.prepare(directory, 'fields')
            with patch.object(m, 'cli', side_effect=[DETAIL, {'RequestId':'enabled'}]):
                result=m.enable(args)
            for key in ('spMetadataUrl','spEntityId','spAcsUrl'):
                self.assertIn(original[key],result['spHandoffMarkdown'])

    def test_delivery_preparation_failure_cannot_follow_a_successful_write(self):
        with tempfile.TemporaryDirectory() as directory:
            args, _ = self.prepare(directory, 'fields')
            incomplete=copy.deepcopy(DETAIL);del incomplete['SamlConfig']['SamlAcsEndpoint']
            with patch.object(m,'cli',return_value=incomplete) as cli, self.assertRaises(m.SkillError):
                m.enable(args)
            self.assertEqual(['GetIdentityProvider'],[c.args[1] for c in cli.call_args_list])

    def test_wrong_target_readback_blocks_enable_and_delivery(self):
        with tempfile.TemporaryDirectory() as directory:
            args, _ = self.prepare(directory)
            foreign=copy.deepcopy(DETAIL);foreign['IdentityProviderId']='idp_other'
            with patch.object(m,'cli',return_value=foreign) as cli, self.assertRaises(m.SkillError):
                m.enable(args)
            self.assertEqual(['GetIdentityProvider'],[c.args[1] for c in cli.call_args_list])

if __name__=='__main__':unittest.main()
