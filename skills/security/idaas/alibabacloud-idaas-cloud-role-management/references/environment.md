# Prerequisites and portability

Use Python 3.9+ and official vendor CLIs. Alibaba CLI is always required for EIAM;
only AWS requires aws and only Tencent requires tccli. Do not install unrelated
vendor tools. Check command help with a 30 second deadline before credential
discovery. Plugin packages belong to the CLI runtime, while authorization belongs
to each selected profile. Check STS and the selected stage's EIAM/RAM/IMS commands
before APIs; do not require setup-only APIs for read-only diagnostics.
Use `scripts/role_environment.py --vendor VENDOR --scope SCOPE` to inspect, or
add `--repair` when official package installation/update is authorized. Repairs
use only the official Alibaba plugin source, are bounded to 300 seconds, and do
not create or change credential profiles. The diagnostic/system executor offers
the equivalent pre-API `--repair-environment` option. Stop if a required profile
or the original approved plan is missing; package repair cannot recover them.
Do not allow plugin-install prompts inside API JSON capture. Never perform
runtime repair after a real permission or parameter error to bypass that error. No browser automation
is needed when authorized CLI profiles already work. Expired auth uses the
official local login flow; the user enters secrets or codes locally.

Run `python3 scripts/role_tools.py validate --input REQUEST.json` on Unix.
On Windows use `scripts\run_role.cmd validate --input REQUEST.json`; the launcher
tries `py -3` and then `python`, without Bash/WSL. Commands use argument arrays,
UTF-8 files and Python pathlib. Windows behavior is not proven by macOS tests.

Generate session ID via Python uuid.uuid4().hex, persist it outside the package,
and set SKILL_SESSION_ID in each subprocess environment. `skill_ua.py` reads
the bundled version metadata and returns the versioned UA. Set
ALIBABA_CLOUD_USER_AGENT in the environment of Alibaba CLI calls only; do not
change global credential configuration. Use SDK user_agent when using an
explicitly authorized official SDK transport. Never import CLI OAuth tokens.

Ordinary operations use official plugins with lowercase-hyphenated names and
parameters. For GetCloudAccountRoleConfig and CheckCloudAccountRoleConfig,
CLI 3.5.2+ supports the official --force RPC route with explicit PascalCase API
parameters, version 2021-12-01 and endpoint eiam.cn-hangzhou.aliyuncs.com.
This route was verified against real EIAM responses; CLI 3.4.11 rejected it with
unchecked version before sending a request. A version/capability check proves
only local transport readiness. Preserve all authorization failures and stop;
--force must never be used to evade a denied request or change target scope.
Update an older runtime through the official CLI distribution and recheck.
No internal plugin binary is required for this route.

For remote runners, keep original plan artifacts in the runner's declared
resource store rather than a temporary script working directory. When the
runner supplies `EVAL_SETUP_RESOURCE_DIR`, inspect its original artifact index
there first. A relocated index may carry `plan_relative_path`: resolve it only
within that declared resource directory and verify the original digest/token
before using it. Relocation never authorizes regenerating or resealing a plan.
If the original artifact is absent, stop and request recovery. Do not search
other sessions or substitute their resources. Restore a missing named CLI
profile only through an already explicitly authorized official login/role-chain
recipe; otherwise request local reauthentication without collecting secrets.

Official forced-call documentation:
https://help.aliyun.com/zh/cli/force-call-apis

Recommended per-command bounds: help 30 seconds, identity/read/write 60 seconds,
health polling 60 seconds, at most three attempts only for explicit retryable
service errors. Close stdin, separate stderr, preserve exit codes. On timeout
state is unknown until readback; never retry a write blindly.

For the official IMS plugin, explicitly use `--endpoint ims.aliyuncs.com --region cn-hangzhou` for `get-oidc-provider` when default endpoint resolution fails. Preserve TLS certificate validation. A local help response proves syntax support only; require the real read to succeed before provisioning.
