# Bucket Exposure-Surface Check

How the forensics script audits the bucket's public exposure surface.
All five checks are read-only OSS control-plane queries; each degrades
independently with `[WARN]` and the audit continues with the remaining
checks.

## 1. Bucket ACL — `GetBucketInfo`

The `acl.grant` field from `GetBucketInfo` is graded:

| ACL | Grade | Meaning for traffic abuse |
|---|---|---|
| `public-read-write` | `open_public_read_write` | Anyone can read AND write objects — exposure level **high**, immediate containment needed (also explains "strange files in my bucket") |
| `public-read` | `open_public_read` | Anonymous GetObject allowed — exposure level **high**, typical scraping precondition |
| `private` | `private` | Anonymous direct reads denied at the ACL layer — shifts suspicion to credentials (AK leak / signed-URL leak) |

`GetBucketInfo` simultaneously yields the bucket location (region),
storage class, and owner — used to derive the SLS project name.

## 2. Bucket policy anonymous-grant detection — `GetBucketPolicy`

The policy JSON is scanned for Allow statements whose Principal covers
everyone:

- `Principal: "*"` or `{"RAM": ["*"]}` (or any member list containing
  `"*"`) = anonymous grant.
- Without `Condition` → state `open` (anonymous access permitted by
  policy; exposure level **high** even when the ACL is private).
- With `Condition` keys (e.g. `IpAddress`, referer-style conditions) →
  state `conditional`: manual review required — a condition does not
  guarantee the restriction is effective.
- No Allow-everyone statement → state `closed`.
- **404 (NoSuchBucketPolicy) is a valid finding**: no policy configured →
  state `closed`, not an error.

## 3. Block Public Access — `GetBucketPublicAccessBlock`

- `block_public_access: true` → bucket-level public ACL/policy grants are
  overridden; recorded as a protective finding.
- `false` → exposure raised to at least **medium** when the rest is
  closed.
- **404 (not configured) is a valid finding**: treated as "not enabled".

Official scope facts (Block Public Access doc): the feature exists on FOUR
dimensions — OSS-global, single Bucket, single Access Point, single Object
FC Access Point. When enabled, existing public grants in Bucket Policy/ACL
are IGNORED and new public grants cannot be created; disabling restores
them. Conflicting settings resolve by precedence:
`OSS-global > Bucket > Access Point > Object FC Access Point` — a higher
level's "on" can never be overridden by a lower level's "off". The
global switch is managed via `GetPublicAccessBlock` /
`PutPublicAccessBlock` (account level, default off), which this read-only
skill does not query — when the bucket-level check shows `false` but
public reads still fail, the global switch being ON is the official
explanation to suggest the user verify.

## 4. Anti-hotlink (Referer) — `GetBucketReferer`

| Configuration | Finding |
|---|---|
| `allow_empty_referer: true` and empty whitelist | Anti-hotlink protection is NOT effective — direct-link scrapers bypass it |
| `allow_empty_referer: true` with a whitelist | Partially effective; empty Referer still allowed → exposure at least **medium** |
| `allow_empty_referer: false` with a whitelist | Effective against browser-based hotlinking |

Note: Referer checks only apply to browser-like clients; programmatic
scrapers send no Referer at all, so this control never replaces a private
ACL.

## 5. Requester Pays — `GetBucketRequestPayment`

| Configuration | Finding |
|---|---|
| payer `Requester` | Exposure NEUTRALIZER: anonymous requests fail with EC 0003-00000701 (they carry no `x-oss-request-payer` header), so a nominally public-read bucket is not anonymously readable |
| payer `Owner` | No neutralizing effect; exposure follows the ACL/policy findings |

The payer is an EXPOSURE NEUTRALIZER measured on a real bucket, exactly
like Block Public Access: it changes what "public-read" means in practice.
The audit therefore distinguishes NOMINAL publicness (the ACL/policy says
public) from EFFECTIVE publicness (public AND no neutralizer active) —
the verdict and root-cause routing follow the effective one.

## Verdict composition

`exposure_verdict` combines the five findings into one graded result:

- **high** — effectively public: public ACL or an anonymous unconditional
  policy grant, with NEITHER Block Public Access NOR Requester Pays
  neutralizing it.
- **medium** — nominally public but neutralized (a latent public grant
  masked by Block Public Access / Requester Pays: switching the
  neutralizer off restores the exposure), or a closed surface with Block
  Public Access disabled, or a conditional anonymous policy, or an
  ineffective Referer configuration.
- **low** — private ACL, closed policy, block enabled (or not needed).

Every finding is recorded verbatim in the report
(`exposure.verdict.findings`) so the final answer can cite exact evidence;
when a check degraded, the verdict states the limitation instead of
guessing.

## What the exposure audit can and cannot prove

- It CAN prove: whether anonymous reads are possible, whether a policy
  opens the bucket, whether protective controls (Block Public Access,
  Requester Pays) are enabled.
- It CANNOT prove: who is downloading the objects right now — that is the
  real-time-log's job (see [traffic-abuse-playbook.md](traffic-abuse-playbook.md)).
  Never announce a root cause from the exposure audit alone.
