# M2: Container (K8s/ACK/ACS) Storage-Volume Mount 403 Attribution

Knowledge base for 403 / AccessDenied failures when mounting an OSS bucket
as a Kubernetes storage volume (static PV/PVC via CSI ossfs). The single
most common confusion is between the MOUNT CREDENTIAL's RAM permission and
the bucket's BUCKET POLICY - they are two different authorization models
and one does not replace the other.

## Sources (official documentation, verified)

| Topic | Official doc |
|---|---|
| ACK OSS volume overview (static volumes only) | https://help.aliyun.com/zh/ack/ack-managed-and-ack-dedicated/user-guide/oss-volume-overview/ |
| Mount static OSS volumes with ossfs 1.0 (Secret / RRSA) | https://help.aliyun.com/zh/ack/ack-managed-and-ack-dedicated/user-guide/mount-statically-provisioned-oss-volumes |
| Mount static OSS volumes with ossfs 2.0 | https://help.aliyun.com/zh/ack/ack-managed-and-ack-dedicated/user-guide/mount-oss-volumes-through-ossfs-2-0 |
| OSS volume FAQ (FailedMount, permission scenarios, RRSA, cross-account) | https://help.aliyun.com/zh/ack/ack-managed-and-ack-dedicated/user-guide/faq-about-oss-volumes-1 |
| Bucket Policy vs RAM Policy differences | https://help.aliyun.com/zh/oss/user-guide/ram-policy/ |

## The two authorization models (do not confuse)

| Aspect | Mount credential (RAM) | Bucket Policy |
|---|---|---|
| What it is | The identity the CSI/ossfs mount ACTS AS: a Secret-stored AccessKey of a RAM user, or an RRSA RAM role assumed by the pod's ServiceAccount | A policy ATTACHED TO THE BUCKET granting principals (other accounts' UIDs / assumed-role ARNs) access |
| Who must satisfy it for a mount | ALWAYS - the mount itself issues ListObjects/GetObject with this identity | Only when the mount identity belongs to a DIFFERENT account than the bucket owner |
| Typical 403 cause | RAM policy missing `oss:GetObject`/`oss:ListObjects` on the bucket, or Secret AK rotated/deleted but the PV still references stale values | Cross-account principal not listed, or Principal written in RAM-policy ARN form instead of the UID form Bucket Policy requires |

Key attribution rule: **a 403 during the mount itself (FailedMount /
csi-plugin event) is almost always the mount-credential side, not the
Bucket Policy side.** Bucket Policy only becomes the first suspect for
cross-account mounts after the mount credential's own RAM permission is
verified.

## 403 diagnosis order for container volume mounts

1. **Credential account vs bucket owner**: the Secret AK / RRSA role must
   belong to the account owning the bucket (or be granted via Bucket
   Policy for cross-account). The entry script's GetBucketInfo `owner_id`
   vs GetCallerIdentity UID comparison provides evidence for the
   same-account part. Note: `The bucket you access does not belong to you`
   during mount is FIRST a client-side pre-check permission failure - the
   mount identity lacks `oss:ListObjects` on the bucket-level resource (or
   `oss:GetBucketInfo` when the tool pre-checks it); per the official doc it
   does NOT indicate a bucket-ownership problem. Ownership/credential
   mismatch and wrong-region endpoint are secondary hypotheses only.
2. **RAM permission of the mount identity**: it needs at least
   `oss:ListObjects` (mount lists the root) plus `oss:GetObject` /
   `oss:PutObject` for used operations on
   `acs:oss:*:*:<bucket>` and `acs:oss:*:*:<bucket>/*`.
3. **Secret freshness**: after AK rotation, updating the Secret is NOT
   picked up by already-mounted volumes on some versions - the official FAQ
   records this scenario; remount is required (guidance only).
4. **Endpoint region**: PV `url` must match the bucket region; a wrong-region
   URL can also surface as 403, but "does not belong to you" is primarily the
   client-side pre-check permission failure (item 2), wrong-region being only
   a secondary hypothesis.
5. **Storage class**: an Archive bucket whose objects are unrestored (and
   archive direct read disabled) fails reads with 403 - verify the bucket
   storage class via the entry script before blaming authorization (see
   M3; a measured ticket showed exactly this root cause for an ACS volume
   mount 403 where network, AK permission and bucket existence were all
   fine).
6. **subpath/subpathExpr mounts**: the official FAQ notes permission
   failures when the credential lacks permission on the subpath scope.
7. **RRSA specifics**: roleArn/oidcProviderArn must be configured and the
   RAM role's trust policy must allow the cluster's OIDC provider;
   otherwise the role assumption fails before any OSS call.

## Manual verification guidance (user executes; this skill never does)

- `kubectl describe pod` / `kubectl get events` - read the FailedMount
  message; it carries the ossfs error text to route via M1's table.
- Confirm the Secret content keys (`akId`/`akSecret` or the RRSA
  annotations) exist and are current.
- For cross-account: confirm the bucket-side Bucket Policy lists the mount
  identity's account UID (numeric form) or assumed-role ARN as Principal.

## Out of scope for this module

- Generic RAM/Bucket Policy authoring unrelated to mounts -> skill
  alibabacloud-oss-cross-account-auth-diagnosis.
- NAS/CPFS/disk volumes -> different products, not this skill.
