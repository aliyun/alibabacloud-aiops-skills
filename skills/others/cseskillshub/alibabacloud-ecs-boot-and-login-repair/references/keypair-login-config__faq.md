# FAQ

Short answers to the questions this tier actually receives, each one consistent with
`scripts/axes/keypair_login_config/_constants.py`. Where the ticket corpus is contradictory, the answer says so
and names the operative wording instead of picking a side silently.

Provenance: these answers are distilled from what support agents actually told
customers, not copied from a help page. Before quoting one to a customer, check it
against the official documentation anchors in `OFFICIAL_DOCS` in
`scripts/axes/keypair_login_config/_constants.py`; where an answer and a help page disagree, the help page wins
and this file gets corrected.

## Lost the private key. Can you send it again?

No. The private key file is offered for download exactly once, at create or import
time, and the platform keeps no copy, so there is nothing to query back. Any tool or
person claiming to recover it is wrong or dishonest. The path forward is a new key
pair: create or import one, bind it to the instance, restart from the console, then
log on with the new file. If the workload cannot be restarted now, there is a
no-restart alternative in `keypair-and-credential-guidance.md`.

## Can you tell me the instance password?

No. Instance passwords are never recorded and never queryable. The recovery path is a
reset: online through Cloud Assistant when the agent reports, offline with a console
restart when it does not. An offline restart needs a snapshot first.

## The key pair is bound and I still get `Permission denied (publickey)`

Four things, cheapest first: the log-on user name (`root` or `ecs-user`), whether the
client actually offered that key, whether the console restart that makes a binding
effective ever happened, and the in-guest layer (daemon options, the `.ssh`
permission chain, the host firewall). See `error-signatures.md` for the walk and
`guest-evidence-commands.md` for the readings a human runs.

## Does binding a key pair break password logon?

It can. With a key pair bound, password logon may stay refused even after a
successful reset. Either use the key path or unbind the key pair; resetting twice does
not change the outcome.

## Two people need to log on to the same Linux instance at the same time

The console binding covers one log-on account, so multi-user key logon is an in-guest
file arrangement: each person generates their own key pair and shares only the public
half, an account that can already log on appends each public key as one complete line
to that user's `authorized_keys`, and the permission chain has to be right or nothing
works. Steps and the exact permissions are in
`keypair-and-credential-guidance.md`. Linux sessions are not capped the way Windows
sessions are; the limit that bites people on Windows is a different one, below.

## Three users cannot log on to Windows at the same time

Windows Server allows two concurrent Remote Desktop sessions by default, and the same
user name reconnects into the existing session instead of opening a second one, which
is what "my session got hijacked" usually is. More concurrent sessions need the
Remote Desktop Session Host role plus RDS client access licences; a 120-day trial is
the only vendor-supported path. A third-party terminal-services activation script is
an unlicensed path and this skill does not help with it.

## My Windows account says it is locked out but nobody typed a wrong password

`0xd07` means the lockout policy fired on repeated failed attempts. A passwordless
logon attempt types no password, so the attempts came from somewhere else, and on an
instance with a public address on 3389 that is normally internet brute-force traffic.
`net accounts` shows the threshold and the durations. Release through one successful
VNC logon or the console send-command path, then tighten 3389 to the customer's own
source address in the security group. Full walkthrough:
`error-signatures.md`.

## Workbench passwordless logon fails but a key logon works

Different channels. Passwordless logon uses a temporary SSH key pair delivered inside
the guest by the Cloud Assistant agent, and it does not depend on the root password or
on `PermitRootLogin`. So the agent status is the first read, and a colleague who can
use passwordless logon while a RAM sub-account cannot is a permission problem, not a
credential problem: the sub-account needs ECS view and manage permission plus Cloud
Assistant permission. See `login-decision-tree.md`.

## My colleague can do it and I cannot

Check who is asking before what is broken. `ecs:DescribeInstances` returning no such
instance for an id that plainly exists means the wrong account, the wrong region, or a
released instance. The report prints the caller identity on line one for exactly this
reason. `NoPermission` and `ImplicitDeny` are the only two authorization literals;
what to do for each is in `ram-policies.md`.

## An unexpected key appeared in `authorized_keys`

The platform neither pre-installs third-party keys nor edits that file on its own, so
it came from inside the guest or from another tool. Remove it, change the instance
password, temporarily fall back to password logon while reviewing how it got there,
and pull the execution history before drawing any conclusion. The history is
`ecs:DescribeInvocations`, requested with the output payload suppressed. Content
drift never gets an answer from a guess.

## It stopped working after changing the image

Probably not a credential fault. A new image has a different log-on account and a
different `authorized_keys` location, and community images flagged as *Others Linux*
generally fall outside console credential management after an image swap on an
existing instance. Then bind a key pair for the new account or use the in-guest path,
instead of retrying console resets against an unsupported image.
`keypair-and-credential-guidance.md`.

## Do you restart my instance, or take the snapshot for me?

Never a restart, and never a credential edit: power changes, key pair lifecycle
changes, password resets, security group edits and every in-guest configuration
change are customer-executed console steps that this skill only guides.

Two calls do exist, and each one happens only if it carries its own confirmation on
that same run — announced first, confirmed for that target only, never inferred from
an earlier answer:

* one published inspection reading inside the guest (`--run-inspection` plus
  `--confirm-inspection`);
* one pre-change snapshot of one disk you name (`--snapshot-disk-id` plus
  `--confirm-snapshot`), stated as billable storage at the same time.

The one case where the ordering must not be skipped is a restart-dependent step:
snapshot first, wait for it to complete, then restart.

## Can a passkey or fingerprint logon be fixed here?

No. A passkey, security key, fingerprint or face logon to a third-party website is
WebAuthn on that platform; an ECS instance has no biometric hardware and no matching
operating system framework for it. Handoff, with the wording to use, in
`handoff-boundaries.md`.
