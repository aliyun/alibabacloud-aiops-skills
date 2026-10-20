# AWS adapter

Verify `aws sts get-caller-identity --profile PROFILE --region REGION --output json`.
Require Account to equal the requested 12-digit account ID. Derive site from
verified ARN partition: aws-cn means china_mainland, aws means global. Reject
unsupported partitions instead of generating an incorrect ARN.

Prefer existing IAM Identity Center/SSO, role-chain, or external credential
profiles. If the installed CLI supports official remote login, use it with the
appropriate region and keep the process alive; otherwise use its supported SSO
flow. Do not ask for access keys or encoded login results in chat.

Read AwsCloudAccountRoleConfig: RoleName, TrustConfig.AssumeRolePolicyDocument,
TrustConfig.RoleSessionDuration, and PolicyConfigs[].PolicyDocument. Derive
OIDC URL/audience from this configuration and read actual partition-aware ARNs.

Use IAM list/get/create-open-id-connect-provider for discovery and creation;
get-role/create-role/update-assume-role-policy/update-role for the generated
system role; get/create-policy, get/create-policy-version and
set-default-policy-version for managed policies; and
list-attached-role-policies/attach-role-policy for attachments. Supply only the
permissions needed for the selected operations in the authorized account.
Use a thumbprint only when the current endpoint or generated configuration
requires it; inspect official API requirements before calling.

Compare existing objects before writes. An authorization error is not absence.
Report trust changes and policy-version changes in the approved plan. Do not
create a new name to bypass a collision.

On OperationDenied.CloudAccountAlreadyManaged, stop writes and report the
conflicting EIAM instance/record when accessible. Cross-instance transfer is
outside this skill. Do not remove old records or change shared IAM trust.
The owner must resolve the conflict separately before retrying onboarding.
