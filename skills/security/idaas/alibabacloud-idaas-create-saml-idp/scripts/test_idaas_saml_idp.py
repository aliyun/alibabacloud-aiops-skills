import argparse
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


MODULE_PATH = Path(__file__).with_name("idaas_saml_idp.py")
SPEC = importlib.util.spec_from_file_location("idaas_saml_idp", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)

CERT_BODY = "MAMCAQE="
CERT_PEM = f"-----BEGIN CERTIFICATE-----\n{CERT_BODY}\n-----END CERTIFICATE-----"
METADATA = f"""<?xml version="1.0"?>
<md:EntityDescriptor xmlns:md="urn:oasis:names:tc:SAML:2.0:metadata"
                     xmlns:ds="http://www.w3.org/2000/09/xmldsig#"
                     entityID="urn:example:idp">
  <md:IDPSSODescriptor protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol"
                       WantAuthnRequestsSigned="true">
    <md:KeyDescriptor use="signing">
      <ds:KeyInfo><ds:X509Data><ds:X509Certificate>{CERT_BODY}</ds:X509Certificate></ds:X509Data></ds:KeyInfo>
    </md:KeyDescriptor>
    <md:SingleSignOnService Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
                             Location="https://idp.example.com/post"/>
    <md:SingleSignOnService Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
                             Location="https://idp.example.com/sso"/>
  </md:IDPSSODescriptor>
</md:EntityDescriptor>
"""
SP_METADATA = b'''<?xml version="1.0"?>
<md:EntityDescriptor xmlns:md="urn:oasis:names:tc:SAML:2.0:metadata"
 entityID="https://idaas.example.com/meta">
 <md:SPSSODescriptor protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol">
  <md:AssertionConsumerService Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
   Location="https://idaas.example.com/acs" index="0"/>
 </md:SPSSODescriptor>
</md:EntityDescriptor>'''


def args_for(path: str, **overrides):
    values = dict(
        profile="default",
        region="cn-hangzhou",
        instance_id="idaas_test",
        name="Example SAML",
        metadata_url=None,
        metadata_file=path,
        entity_id=None,
        sso_url=None,
        certificate_file=None,
        network_access_endpoint_id=None,
        binding=None,
        allow_insecure_test=False,
        require_request_signed=None,
        want_response_signed=True,
        want_assertions_signed=True,
        max_clock_skew=180,
        authn_status="enabled",
        client_token=None,
        accept_warnings=False,
        confirm=None,
    )
    values.update(overrides)
    return argparse.Namespace(**values)


class SamlIdpSkillTest(unittest.TestCase):
    def metadata_file(self):
        handle = tempfile.NamedTemporaryFile("w", suffix=".xml", delete=False)
        handle.write(METADATA)
        handle.close()
        self.addCleanup(Path(handle.name).unlink, missing_ok=True)
        return handle.name

    def test_parse_metadata_extracts_sso_cert_and_signing_policy(self):
        metadata = MODULE.parse_metadata_xml(METADATA.encode(), "test")
        self.assertEqual("urn:example:idp", metadata["entityId"])
        self.assertEqual("HTTP-POST", metadata["ssoServices"][0]["binding"])
        self.assertEqual("HTTP-REDIRECT", metadata["ssoServices"][1]["binding"])
        self.assertTrue(metadata["wantAuthnRequestsSigned"])
        self.assertEqual([CERT_PEM], metadata["certificates"])

    def test_plan_prefers_redirect_and_infers_signed_request(self):
        result = MODULE.plan(args_for(self.metadata_file()))
        self.assertEqual("HTTP-REDIRECT", result["saml"]["bindingMethod"])
        self.assertEqual("https://idp.example.com/sso", result["saml"]["idpSsoUrl"])
        self.assertTrue(result["saml"]["requireRequestSigned"])
        self.assertTrue(result["saml"]["wantResponseSigned"])
        self.assertTrue(result["saml"]["wantAssertionsSigned"])
        self.assertEqual(1, len(result["saml"]["certificates"]))
        self.assertEqual("enabled", result["authenticationStatusAfterCreate"])
        self.assertNotIn("BEGIN CERTIFICATE", str(result))
        self.assertTrue(result["ready"])

    def test_explicit_post_and_no_sign_override_metadata(self):
        result = MODULE.plan(args_for(
            self.metadata_file(), binding="HTTP-POST", require_request_signed=False,
        ))
        self.assertEqual("HTTP-POST", result["saml"]["bindingMethod"])
        self.assertFalse(result["saml"]["requireRequestSigned"])

    def test_rejects_private_key_file(self):
        with self.assertRaisesRegex(MODULE.SkillError, "private key"):
            MODULE.certificate_pem("-----BEGIN PRIVATE KEY-----\nMAMCAQE=\n-----END PRIVATE KEY-----")

    def test_rejects_more_than_two_certificates(self):
        repeated = METADATA.replace(
            "</md:KeyDescriptor>",
            "</md:KeyDescriptor><md:KeyDescriptor use=\"signing\"><ds:KeyInfo><ds:X509Data>"
            "<ds:X509Certificate>MAMCAQI=</ds:X509Certificate></ds:X509Data></ds:KeyInfo></md:KeyDescriptor>"
            "<md:KeyDescriptor use=\"signing\"><ds:KeyInfo><ds:X509Data>"
            "<ds:X509Certificate>MAMCAQM=</ds:X509Certificate></ds:X509Data></ds:KeyInfo></md:KeyDescriptor>",
        )
        handle = tempfile.NamedTemporaryFile("w", suffix=".xml", delete=False)
        handle.write(repeated)
        handle.close()
        self.addCleanup(Path(handle.name).unlink, missing_ok=True)
        with self.assertRaisesRegex(MODULE.SkillError, "at most two"):
            MODULE.plan(args_for(handle.name))

    @patch.object(MODULE, "cli")
    def test_create_uses_flat_saml_parameters_and_force(self, mocked_cli):
        mocked_cli.side_effect = [{"IdentityProviders": [], "TotalCount": 0, "RequestId": "list_request"}, {"IdentityProviderId": "idp_123", "RequestId": "req_123"}]
        result = MODULE.create(args_for(self.metadata_file(), confirm="CREATE"))
        self.assertEqual("idp_123", result["identityProviderId"])
        operation = mocked_cli.call_args.args[1]
        parameters = mocked_cli.call_args.args[2]
        self.assertEqual("CreateIdentityProvider", operation)
        self.assertIn("--SamlConfig.IdPEntityId", parameters)
        self.assertIn("--SamlConfig.Certificates.1.Content", parameters)
        self.assertIn(CERT_PEM, parameters)
        self.assertIn("--SamlConfig.WantResponseSigned", parameters)
        self.assertIn("--SamlConfig.WantAssertionsSigned", parameters)
        authn_flag = parameters.index("--AuthnConfig.AuthnStatus")
        self.assertEqual("enabled", parameters[authn_flag + 1])
        self.assertEqual("enabled", result["authenticationStatus"])
        self.assertIn("sp-metadata", result["next"])
        self.assertEqual("POST", mocked_cli.call_args.kwargs["method"])
        self.assertTrue(mocked_cli.call_args.kwargs["force"])

    @patch.object(MODULE, "cli")
    def test_create_can_explicitly_remain_disabled(self, mocked_cli):
        mocked_cli.side_effect = [{"IdentityProviders": [], "TotalCount": 0, "RequestId": "list_request"}, {"IdentityProviderId": "idp_disabled"}]
        result = MODULE.create(args_for(
            self.metadata_file(), confirm="CREATE", authn_status="disabled",
        ))
        parameters = mocked_cli.call_args.args[2]
        authn_flag = parameters.index("--AuthnConfig.AuthnStatus")
        self.assertEqual("disabled", parameters[authn_flag + 1])
        self.assertEqual("disabled", result["authenticationStatus"])

    def test_create_requires_confirmation(self):
        with self.assertRaisesRegex(MODULE.SkillError, "--confirm CREATE"):
            MODULE.create(args_for(self.metadata_file()))

    @patch.object(MODULE, "cli")
    def test_wrong_certificate_fingerprint_blocks_create_and_update(self, mocked_cli):
        for operation in ("create", "update"):
            with self.subTest(operation=operation):
                args = args_for(self.metadata_file(), confirm=operation.upper(), idp_id="idp_test",
                                expected_certificate_sha256=["00" * 32])
                with self.assertRaisesRegex(MODULE.SkillError, "Certificate SHA-256 mismatch"):
                    getattr(MODULE, operation)(args)
        mocked_cli.assert_not_called()

    def test_certificate_pin_accepts_colon_case_and_rejects_extra_certificate(self):
        pin = MODULE.certificate_summary(CERT_PEM)["sha256"]
        self.assertTrue(MODULE.plan(args_for(self.metadata_file(), expected_certificate_sha256=[pin]))["ready"])
        for pins in ([pin, "11" * 32], ["invalid"]):
            with self.subTest(pins=pins), self.assertRaises(MODULE.SkillError):
                MODULE.plan(args_for(self.metadata_file(), expected_certificate_sha256=pins))

    @patch.object(MODULE, "cli")
    def test_create_state_reuses_success_without_second_cloud_write(self, mocked_cli):
        mocked_cli.side_effect = [{"IdentityProviders": [], "TotalCount": 0, "RequestId": "list_request"}, {"IdentityProviderId": "idp_once", "RequestId": "req_once"}]
        with tempfile.TemporaryDirectory() as directory:
            args = args_for(self.metadata_file(), confirm="CREATE", state_file=str(Path(directory) / "state.json"))
            first = MODULE.create(args)
            second = MODULE.create(args)
        self.assertEqual(first["identityProviderId"], second["identityProviderId"])
        self.assertTrue(second["reusedCreationResult"])
        self.assertEqual(2, mocked_cli.call_count)

    @patch.object(MODULE, "cli")
    def test_create_state_blocks_retry_after_uncertain_timeout(self, mocked_cli):
        mocked_cli.side_effect = [{"IdentityProviders": [], "TotalCount": 0, "RequestId": "list_request"}, MODULE.SkillError("read timeout after POST")]
        with tempfile.TemporaryDirectory() as directory:
            args = args_for(self.metadata_file(), confirm="CREATE", state_file=str(Path(directory) / "state.json"))
            with self.assertRaisesRegex(MODULE.SkillError, "read timeout"):
                MODULE.create(args)
            with self.assertRaisesRegex(MODULE.SkillError, "uncertain outcome"):
                MODULE.create(args)
        self.assertEqual(2, mocked_cli.call_count)

    @patch.object(MODULE, "cli")
    def test_create_state_rejects_changed_target_configuration(self, mocked_cli):
        mocked_cli.side_effect = [{"IdentityProviders": [], "TotalCount": 0, "RequestId": "list_request"}, {"IdentityProviderId": "idp_once"}]
        with tempfile.TemporaryDirectory() as directory:
            args = args_for(self.metadata_file(), confirm="CREATE", state_file=str(Path(directory) / "state.json"))
            MODULE.create(args)
            args.instance_id = "idaas_other"
            with self.assertRaisesRegex(MODULE.SkillError, "different configuration"):
                MODULE.create(args)
        self.assertEqual(2, mocked_cli.call_count)

    @patch.object(MODULE, "cli")
    def test_existing_creation_lock_blocks_concurrent_write(self, mocked_cli):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            path.with_name("state.json.lock").touch()
            args = args_for(self.metadata_file(), confirm="CREATE", state_file=str(path))
            with self.assertRaisesRegex(MODULE.SkillError, "locked"):
                MODULE.create(args)
        mocked_cli.assert_not_called()

    @patch.object(MODULE, "cli")
    def test_list_does_not_hide_saml_providers_with_invalid_direction(self, mocked_cli):
        mocked_cli.return_value = {"TotalCount": 1, "IdentityProviders": [{
            "IdentityProviderId": "idp_existing", "Direction": "pull",
            "IdentityProviderType": MODULE.SAML_IDP_TYPE,
        }]}
        args = argparse.Namespace(instance_id="idaas_test", page_size=100)
        result = MODULE.list_idps(args)
        self.assertEqual(1, result["TotalCount"])
        self.assertNotIn("--Direction", mocked_cli.call_args.args[2])

    @patch.object(MODULE, "cli")
    def test_url_resolution_normalizes_openapi_response(self, mocked_cli):
        mocked_cli.return_value = {
            "IdentityProviderMetadata": {
                "SamlMetadataConfiguration": {
                    "IdPEntityId": "urn:example:idp",
                    "IdPSsoUrl": "https://idp.example.com/sso",
                    "Certificates": {"certificates": [{"Content": CERT_PEM}]},
                }
            }
        }
        result = MODULE.resolve(args_for(
            "", metadata_file=None, metadata_url="https://idp.example.com/metadata",
        ))
        self.assertEqual("idaas", result["resolvedBy"])
        self.assertEqual("urn:example:idp", result["metadata"]["entityId"])
        self.assertEqual(1, len(result["metadata"]["certificates"]))

    def test_clock_skew_range_is_enforced(self):
        with self.assertRaisesRegex(MODULE.SkillError, "between 0 and 360"):
            MODULE.plan(args_for(self.metadata_file(), max_clock_skew=361))

    def test_cli_version_requirement_rejects_legacy_cli(self):
        completed = MODULE.subprocess.CompletedProcess(
            args=["aliyun", "version"], returncode=0, stdout="3.3.2\n", stderr="",
        )
        with patch.object(MODULE.subprocess, "run", return_value=completed):
            with self.assertRaisesRegex(MODULE.SkillError, "3.3.3 or later"):
                MODULE.require_cli("/usr/bin/aliyun")

    @patch.object(MODULE, "skill_version", return_value="1.2.3")
    @patch.object(MODULE, "session_id", return_value="session-test")
    @patch.object(MODULE, "require_cli", return_value="3.5.1")
    @patch.object(MODULE.shutil, "which", return_value="/usr/bin/aliyun")
    @patch.object(MODULE.subprocess, "run")
    def test_cloud_call_user_agent_contains_version_and_session(
        self, mocked_run, _which, _require_cli, _session_id, _skill_version,
    ):
        mocked_run.return_value = MODULE.subprocess.CompletedProcess(
            args=["aliyun"], returncode=0, stdout="{}", stderr="",
        )
        args = argparse.Namespace(profile="default", region="cn-hangzhou")
        MODULE.cli(args, "ListEiamInstances", [])
        environment = mocked_run.call_args.kwargs["env"]
        user_agent = environment["ALIBABA_CLOUD_USER_AGENT"]
        self.assertEqual(
            "AlibabaCloud-Agent-Skills/alibabacloud-idaas-create-saml-idp/session-test skill-version/1.2.3",
            user_agent,
        )

    @patch.object(MODULE, "cli")
    def test_unsupported_status_check_is_non_blocking(self, mocked_cli):
        mocked_cli.side_effect = MODULE.SkillError(
            "UnsupportedAction: Current instance status cannot supported this action."
        )
        args = argparse.Namespace(
            profile="default", region="cn-hangzhou", instance_id="idaas_test",
            idp_id="idp_test", timeout=1, interval=0, skip_check=False,
        )
        result = MODULE.check(args)
        self.assertFalse(result["supported"])
        self.assertTrue(result["skipped"])
        self.assertIn("show/sp-metadata", result["next"])

    def test_skip_check_does_not_call_service(self):
        args = argparse.Namespace(
            profile="default", region="cn-hangzhou", instance_id="idaas_test",
            idp_id="idp_test", timeout=1, interval=0, skip_check=True,
        )
        with patch.object(MODULE, "cli") as mocked_cli:
            result = MODULE.check(args)
        mocked_cli.assert_not_called()
        self.assertTrue(result["skipped"])

    @patch.object(MODULE, "cli")
    def test_instances_expose_stable_selection_and_instance_id(self, mocked_cli):
        mocked_cli.return_value = {
            "Instances": [{
                "InstanceId": "idaas_example",
                "Description": "Example instance",
                "InstanceStatus": "RUNNING",
                "InstanceVersion": "EIAM 2.0",
                "SSODomain": "example.aliyunidaas.com",
            }]
        }
        args = argparse.Namespace(profile="default", region="cn-hangzhou", running_only=False)
        result = MODULE.instances(args)
        self.assertEqual(1, result[0]["selection"])
        self.assertEqual("idaas_example", result[0]["instanceId"])
        self.assertEqual("Example instance", result[0]["description"])
        self.assertEqual("RUNNING", result[0]["status"])

    @patch.object(MODULE, "show")
    def test_sp_metadata_extracts_handoff_fields(self, mocked_show):
        mocked_show.return_value = {
            "IdentityProviderDetail": {
                "EndpointMetadata": {
                    "SamlMetaEndpoint": "https://idaas.example.com/meta",
                    "SamlEntityId": "https://idaas.example.com/meta",
                    "SamlAcsEndpoint": "https://idaas.example.com/acs",
                },
                "SamlConfig": {
                    "WantResponseSigned": True,
                    "WantAssertionsSigned": False,
                },
            }
        }
        args = argparse.Namespace(instance_id="idaas_test", idp_id="idp_test", output_mode="fields")
        result = MODULE.sp_metadata(args)
        self.assertEqual("fields", result["outputMode"])
        self.assertEqual("https://idaas.example.com/meta", result["spMetadataUrl"])
        self.assertEqual("https://idaas.example.com/acs", result["spAcsUrl"])
        self.assertTrue(result["signatureRequirements"]["response"])

    @patch.object(MODULE, "fetch_sp_metadata")
    @patch.object(MODULE, "show")
    def test_sp_metadata_can_return_raw_xml(self, mocked_show, mocked_fetch):
        mocked_show.return_value = {
            "IdentityProviderDetail": {
                "EndpointMetadata": {
                    "SamlMetaEndpoint": "https://idaas.example.com/meta",
                    "SamlEntityId": "https://idaas.example.com/meta",
                    "SamlAcsEndpoint": "https://idaas.example.com/acs",
                }
            }
        }
        raw_xml = SP_METADATA
        mocked_fetch.return_value = raw_xml
        args = argparse.Namespace(instance_id="idaas_test", idp_id="idp_test", output_mode="raw")
        result = MODULE.sp_metadata(args)
        mocked_fetch.assert_called_once_with("https://idaas.example.com/meta")
        self.assertEqual("raw", result["outputMode"])
        self.assertEqual(raw_xml.decode(), result["rawMetadataXml"])
        self.assertNotIn("spAcsUrl", result)

    @patch.object(MODULE, "fetch_sp_metadata", return_value=SP_METADATA)
    @patch.object(MODULE, "show")
    def test_raw_xml_artifact_is_exact_download_and_invalid_body_is_never_written(self, mocked_show, mocked_fetch):
        mocked_show.return_value = {"EndpointMetadata": {
            "SamlMetaEndpoint": "https://idaas.example.com/meta",
            "SamlEntityId": "https://idaas.example.com/meta",
        }}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sp.xml"
            args = argparse.Namespace(instance_id="idaas_test", idp_id="idp_test",
                                      output_mode="raw", output_file=str(path))
            result = MODULE.sp_metadata(args)
            self.assertEqual(SP_METADATA, path.read_bytes())
            self.assertEqual(str(path), result["rawMetadataFile"])
            path.unlink()
            mocked_fetch.return_value = b"<html>challenge</html>"
            with self.assertRaises(MODULE.SkillError):
                MODULE.sp_metadata(args)
            self.assertFalse(path.exists())

    @patch.object(MODULE.subprocess, "run")
    @patch.object(MODULE.shutil, "which", return_value="/usr/bin/curl")
    @patch.object(MODULE, "fetch_metadata", side_effect=MODULE.SkillError("certificate verify failed"))
    def test_sp_metadata_fetch_falls_back_to_system_curl(self, mocked_fetch, mocked_which, mocked_run):
        raw_xml = SP_METADATA
        mocked_run.return_value = MODULE.subprocess.CompletedProcess(
            args=["curl"], returncode=0, stdout=raw_xml, stderr=b"",
        )
        result = MODULE.fetch_sp_metadata("https://idaas.example.com/meta")
        self.assertEqual(raw_xml, result)
        command = mocked_run.call_args.args[0]
        self.assertEqual("/usr/bin/curl", command[0])
        self.assertNotIn("--location", command)
        self.assertEqual("https://idaas.example.com/meta", command[-1])

    @patch.object(MODULE.subprocess, "run")
    @patch.object(MODULE.shutil, "which", return_value="/usr/bin/curl")
    @patch.object(MODULE, "fetch_metadata", return_value=b"<html><body>WAF deny</body></html>")
    def test_http_200_html_uses_validated_curl_fallback(self, mocked_fetch, mocked_which, mocked_run):
        mocked_run.return_value = MODULE.subprocess.CompletedProcess(
            args=["curl"], returncode=0, stdout=SP_METADATA, stderr=b"",
        )
        self.assertEqual(SP_METADATA, MODULE.fetch_sp_metadata("https://idaas.example.com/meta"))
        mocked_fetch.assert_called_once()
        mocked_run.assert_called_once()

    @patch.object(MODULE.subprocess, "run")
    @patch.object(MODULE.shutil, "which", return_value="/usr/bin/curl")
    @patch.object(MODULE, "fetch_metadata", return_value=b"<html><body>WAF deny</body></html>")
    def test_two_html_downloads_fail_without_returning_fake_metadata(self, mocked_fetch, mocked_which, mocked_run):
        mocked_run.return_value = MODULE.subprocess.CompletedProcess(
            args=["curl"], returncode=0, stdout=b"<html><body>WAF deny</body></html>", stderr=b"",
        )
        with self.assertRaisesRegex(MODULE.SkillError, "do not retry creation or synthesize XML"):
            MODULE.fetch_sp_metadata("https://idaas.example.com/meta")
        mocked_run.assert_called_once()

    @patch.object(MODULE.subprocess, "run")
    @patch.object(MODULE, "fetch_metadata", return_value=SP_METADATA)
    def test_valid_primary_download_does_not_make_an_extra_request(self, mocked_fetch, mocked_run):
        self.assertEqual(SP_METADATA, MODULE.fetch_sp_metadata("https://idaas.example.com/meta"))
        mocked_run.assert_not_called()

    def test_sp_metadata_rejects_idp_and_empty_descriptors(self):
        for payload in (METADATA.encode(), b"<EntityDescriptor/>",
                        b'<EntityDescriptor xmlns="urn:oasis:names:tc:SAML:2.0:metadata" entityID="x"/>'):
            with self.subTest(payload=payload):
                with self.assertRaises(MODULE.SkillError):
                    MODULE.parse_sp_metadata(payload)

    @patch.object(MODULE, "fetch_sp_metadata", return_value=SP_METADATA)
    @patch.object(MODULE, "show")
    def test_raw_delivery_rejects_another_sp_entity(self, mocked_show, mocked_fetch):
        mocked_show.return_value = {"EndpointMetadata": {
            "SamlMetaEndpoint": "https://idaas.example.com/meta",
            "SamlEntityId": "https://idaas.example.com/another-idp/meta",
        }}
        args = argparse.Namespace(instance_id="idaas_test", idp_id="idp_test", output_mode="raw")
        with self.assertRaisesRegex(MODULE.SkillError, "matching the requested SP Entity ID"):
            MODULE.sp_metadata(args)

    def test_raw_delivery_rejects_missing_acs_and_oversized_payload(self):
        no_acs = SP_METADATA.replace(b"AssertionConsumerService", b"OtherEndpoint")
        with self.assertRaisesRegex(MODULE.SkillError, "AssertionConsumerService"):
            MODULE.parse_sp_metadata(no_acs)
        with self.assertRaisesRegex(MODULE.SkillError, "5 MiB"):
            MODULE.parse_sp_metadata(b"x" * (MODULE.MAX_METADATA_BYTES + 1))

    @patch.object(MODULE, "cli")
    def test_update_uses_full_flat_saml_configuration(self, mocked_cli):
        mocked_cli.return_value = {"RequestId": "req_update"}
        result = MODULE.update(args_for(
            self.metadata_file(), idp_id="idp_123", confirm="UPDATE",
            want_response_signed=False,
        ))
        parameters = mocked_cli.call_args.args[2]
        self.assertTrue(result["updated"])
        self.assertIn("--SamlConfig.Certificates.1.Content", parameters)
        response_flag = parameters.index("--SamlConfig.WantResponseSigned")
        self.assertEqual("false", parameters[response_flag + 1])
        self.assertEqual("POST", mocked_cli.call_args.kwargs["method"])
        self.assertTrue(mocked_cli.call_args.kwargs["force"])


if __name__ == "__main__":
    unittest.main()
