# Release evaluation and limits

Run local checks from the repository root:

```sh
python3 -m unittest discover -s tests -v
python3 scripts/cloud_identity_preflight.py --help
```

The unit suite covers complete pagination, repeated tokens, malformed responses,
bounded subprocess timeouts, error-output privacy, vendor-aware identity matching,
and blocking incomplete discovery. These tests mock CLIs and do not mutate cloud
accounts. They do not establish live IAM permissions or end-to-end success.

Before release, use the platform static detection and dynamic evaluation with
customer-authorized isolated accounts. Cover new onboarding for each provider,
repeat onboarding, wrong account, expired authorization, missing CLI, ambiguous
site, Windows launch, resource conflicts and timeout recovery. Cross-instance
transfer is outside the capability scope; verify it is rejected without writes. Exercise every declared permission in the corresponding
mode; record the model, engine, prompt, observations, and check result. Evaluate
Chinese and English requests and ordinary application SSO negative triggers.
Run repeated trials and measure the platform's required success rate rather
than inferring it from one successful account per provider.

Current limits: the preflight requires resolved profile names; profile discovery,
login orchestration, plan approval, and writes are performed by the agent.
Windows launcher is provided, but a real Windows host still needs validation.
Provider/API availability and authorization vary with deployed CLI versions.
Previously completed real account onboarding is historical evidence, not a
fresh evaluation of this published revision. Do not include customer IDs,
credentials, callback URLs, or private execution transcripts in evaluation files.

## Platform release gates

The platform requires capability coverage >=90%, process assertion coverage
>=80%, each participating testcase pass rate >=95%, and zero Forbidden hits.
Trigger/guidance scenarios stop before cloud discovery and cannot honestly assert
preflight or plan approval. Local invalid-input and UA scenarios execute real
bundled scripts without cloud calls; they do not prove successful discovery.
The guide cases cover decision explanations, not live multi-turn interactions.
Full discovery, plan confirmation, writes and health checks require
isolated authorized EIAM and provider accounts with real process expectations.
Do not attach approval or cloud-operation assertions to trigger-only prompts
just to raise coverage. Release remains blocked until these live paths satisfy
the platform gates.

## Execution coverage matrix

Guidance artifacts and response checks only validate explanations. Do not count
them as execution of the corresponding cloud or interactive path. The following
release cases remain required; enable each only after its fixture and permissions
are validated in the evaluation runner, not merely on a developer's workstation.

| Required case | Fixture and process evidence | Final assertions |
| --- | --- | --- |
| New onboarding, each supported provider | Verified EIAM and provider identities; actual preflight; displayed and approved plan; CreateCloudAccount; automatic system-role/config read; provider reads and approved writes | Dynamic config matches; latest EIAM account and role health are healthy; concrete resource IDs |
| Existing-resource reconciliation and repeat | Existing provider resources plus absent EIAM record; semantic comparisons; approved difference repair; repeat after success | No duplicate account/role; no rename workaround; only approved differences changed |
| Site/profile selection | Actual ambiguous input; user response through the runner's supported interaction mechanism; selected value retained | No API before missing target scope is resolved; selected partition/profile used |
| Interrupted resume | Persisted confirmed plan/context and actual partial state; injected or observed timeout; target readback before retry | No repeated successful writes, no missing-input loop, no assumed completion |
| Permission failure/partial failure | Deliberately scoped test identity; a permitted setup stage and a denied operation | Completed IDs, failed action and sanitized code, remaining work and exact missing permission; no rollback or broader grants |
| Throttling/system failure | Runner-supported bounded fault injection or genuine sandbox failure with provenance | Bounded retry, readback on ambiguous write, accurate unknown/partial state report |

Use process expectations for real CLI/API/script calls and final assertions for
observed health/state. Never substitute a narrative plan or a matching keyword
for a cloud execution assertion. A local script test using fake profile names
can validate early input rejection but cannot validate identity or live access.
Ownership-conflict cases must stop without disable/delete operations or shared
trust changes. They validate safe rejection, not account transfer.

Before scheduling live tests, resolve a separate target-cloud credential chain
for each provider in the runner. A custom Alibaba Cloud STS role alone does not
authorize AWS IAM or Tencent CAM. Do not serialize credentials in testcase files.
Missing live fixtures are release blockers, not testcase successes.

## Scope update and report 12927

The release scope is onboarding, same-instance reuse/resume, resource comparison,
approved creation/repair and health verification. Cross-instance transfers and
EIAM record cleanup are excluded; their deletion permissions are not declared.
Retain new-onboarding tests and their real CreateCloudAccount evidence.

Report 12927 had nine assertion-failed sessions: eight without-skill baseline
sessions and one with-skill missing-input final summary. Baseline failures must
remain visible as controls; never weaken expectations to make the baseline pass.
The with-skill group passed 30/31 and had zero Forbidden or execution failures.
The remaining coverage gates were capability 87.5%, process assertions 75%, and
missing incomplete-input coverage. The missing-instance collection case obtains
the real required input through HITL before any cloud calls, then runs actual
identity and existing-target preflight. Intent-only cases must remain cloud-free.

For subsequent runs, preserve the healthy test record unless a separate exact
cleanup/rebuild is authorized. Update read-only fixture IDs after a real rebuild.
A new-onboarding case requires ready_new; do not reinterpret ready_resume as new
creation just to run it against an occupied fixture. Record excluded test reasons
and retain the earlier real 15/15 new-onboarding result without claiming it is
a fresh execution of the current commit.
