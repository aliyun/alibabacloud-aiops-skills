# AWS roles

Verify `aws sts get-caller-identity --profile PROFILE --region REGION --output json`.
Account must match. ARN partition aws means global, aws-cn means china_mainland.
Reject other partitions. IAM is global within a partition; region is not a
business permission boundary. Read the existing OIDC provider in that partition.

Inspect IAM get-role, list-attached-role-policies, list-role-policies,
get-role-policy, get-policy and get-policy-version. Paginate all lists; preserve
managed policy versions and PermissionsBoundary. Service control policies and
session policies can further restrict effective permissions; report uncertainty.

Read AwsCloudAccountRoleConfig.RoleName and TrustConfig with
AssumeRolePolicyDocument and RoleSessionDuration. For an absent role use
`iam create-role --role-name NAME --assume-role-policy-document file://TRUST.json
--max-session-duration SECONDS` plus the verified profile/output/timeout flags.
Policy files contain the validated dynamic trust, not copied examples.
Attach approved managed policy ARNs with attach-role-policy. For a new dedicated
inline policy use put-role-policy only with its approved name/document. Do not
overwrite a different existing inline policy. Creating a dedicated managed policy
requires the separately disclosed policy name/document; read after creation.

For approved trust repair use update-assume-role-policy with merged content;
update-role for an approved session change. Never modify a shared managed policy
or remove boundaries/extra attachments. URL-decode IAM returned trust/policy
documents once when necessary, then parse JSON before comparison.

Verify ARN path and case exactly rather than constructing an expected ARN from
role name alone. Never replace OIDC with SAML. Read back trust, boundary, duration,
all attachments and inline documents before reporting verification success.

Official CLI reference:
https://docs.aws.amazon.com/cli/latest/reference/iam/create-role.html
