# Release evidence and limits

This first implementation is instruction-driven: the agent executes official
CLI/API operations, while bundled scripts validate inputs, compare JSON and bind
plans to stable digests/tokens. It is not an unattended role-provisioning daemon.
No helper claims to have performed a cloud operation it did not execute.

Local unit tests prove validation, mutation detection, token determinism and
structural comparisons only. They do not prove cloud authorization, cross-cloud
provisioning, effective business permissions or a real Windows execution.

Before customer publication, require deployment support for the dynamic role
configuration and check operations. Use official Alibaba Cloud CLI 3.5.2 or later with the narrowly scoped
forced RPC transport in scripts/eiam_transport.py. The public EIAM plugin may
omit these two operations. Both canonical forced RPC calls succeeded on
2026-10-26; CLI 3.4.11 rejected the API version locally.
An actual authorized configuration read succeeded on 2026-10-22. New role provisioning, health checking and repeat reuse were verified with
real Alibaba Cloud, AWS and Tencent Cloud roles on 2026-10-22. Each cloud
role received a separately approved business policy; all users/groups remained
unassigned. AWS used its already-managed EIAM instance after an ownership
conflict blocked duplicate account onboarding. Tencent account onboarding was
performed separately through the account-onboarding skill. These observations
do not prove unattended execution, effective end-user access, a real Windows
run, or availability in another customer deployment. Platform static/dynamic
release checks remain separate gates. A transient AWS JWKS retrieval failure
and connection timeouts were retained in evidence; final fresh checks passed
after bounded retries, without changing provider keys or shared trust.
Do not publish a claim of unattended customer completion based on private
employee diagnostics.

Platform dynamic release tests must cover all advertised vendors' real fresh
creation, registration/reuse, exact approved trust repair, idempotency, partial
resume, policy drift, system-role collision, wrong owner, incomplete permission
intent, profile/site choice, missing account/provider, permission/parameter/
throttle/system failures and Windows invocation. Compare business policies
independently from EIAM health. Keep baseline and skill evidence separate.

Use isolated role names and preapproved exact policies. A sample or prior test
account is not mutation authorization. Never delete a business role to prepare
a test. Obtain scoped cleanup approval for any disposable fixtures separately.
Mocks prove exceptional branch handling only; they are not real provisioning.

Use the platform's currently displayed release criteria, preserve model and
commit identity, and inspect runtime failures separately from assertion failures.
No release or customer-readiness claim is allowed until required real tests pass.
