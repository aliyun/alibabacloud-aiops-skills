# Guest-side information-only runbook (two states of the whitelist)

Facts about certificate-tier data live in three places: the cloud side
(instance region, state, public address — automated), the outside-in view
(DNS answer and the live TLS handshake — automated, needs no authorization),
and INSIDE the guest (what really listens, which files nginx or IIS
actually load, what the CA endpoints see from this box). The third layer
has no cloud API substitute: `DescribeInvocations` returns history only,
never a live reading. This module defines what may run inside the guest,
under what gate, and what must stay manual.

## State A — dispatchable NOW (the batch low-risk list, current entries)

The unified low-risk list shipped with this batch enumerates disk-tier
commands. The subset usable for this tier without any whitelist extension:

| Command | Takes | What it proves here |
| --- | --- | --- |
| `stat` | one file path | owner, mode, size and timestamps of a certificate or key file — the direct evidence for a "certificate permission error" (ticket T-B5F37974 opened with exactly that wording) |
| `ls -l` | one directory path | which certificate files actually exist where nginx or IIS expects them |
| `wc -l` | one file path | a quick sanity check that a pasted or converted file is complete (a truncated pem has the wrong line count) |

Dispatch rules (mandatory, enforced in `scripts/axes/ssl_cert_deployment/ssl_cert_deployment_report.py`):

1. Before any dispatch, present the notice: the exact command line, the
   target instance, its information-only nature, and that a query leaves no
   state behind. Obtain the customer's explicit approval for THIS command at
   THIS time. One approval, one command; approvals are never reused or
   batched.
2. ONE command per Cloud Assistant dispatch. The command string never
   contains quotes, redirection, chaining or any destructive token — the
   script refuses such requests outright, not just the agent.
3. No Windows reading is dispatchable at all yet: the approved list has no
   Windows rows for this tier. Windows evidence goes through State B.
4. Any failure (agent offline, dispatch denied, the invocation never
   settles) yields `STATUS: DEGRADED` plus the missing item named, and the
   run falls back to "ask the customer to run it and paste the output".
   Never pretend the reading happened.

## State B — printed as a manual checklist, NEVER dispatched (pending the whitelist extension)

These commands are information-only but NOT on the approved list for this
tier. The skill prints them for the customer to run, then interprets the
pasted output against the table below. The agent must not send them through
Cloud Assistant.

Linux:

```
curl -I --connect-timeout 10 https://acme-v02.api.letsencrypt.org
curl -I --connect-timeout 10 https://alidns.aliyuncs.com
nc -vz <host> 443                       (or: telnet <host> 443)
ss -tlnp                                 (what really listens on 443)
iptables -S                              (guest firewall view)
nginx -t ; nginx -T                      (config test + full effective dump)
openssl x509 -in <crt> -noout -dates -subject -issuer
openssl x509 -in <crt> -noout -modulus | md5sum
openssl rsa  -in <key> -noout -modulus | md5sum
```

Windows (tickets T-75A1E320 and T-382FDB28 are this branch):

```
Test-NetConnection acme-v02.api.letsencrypt.org -Port 443
tracetcp acme-v02.api.letsencrypt.org:443
Get-ChildItem Cert:\LocalMachine\My | Format-Table FriendlyName, NotAfter, Thumbprint
Get-WebBinding
```

Confidence note for Windows: the certificate STORE and the file-system path
are two different views of "installed"; state which one a conclusion refers
to, exactly as this tier states which capacity lens a number belongs to.

## Reading interpretation table

| Pasted evidence | Verdict | Next |
| --- | --- | --- |
| `stat` shows the key owned by root mode 600 while nginx runs as another user | permission fault | manual fix: correct ownership, a customer decision |
| curl to an ACME endpoint stalls until timeout, while curl to a domestic endpoint works | cross-border path (see references/ssl-cert-deployment__acme-network-egress.md) | alternatives branch; do not chase the "block" theory |
| curl is reset immediately (matches err_connection_closed) | local interception or endpoint reset | check guest firewall rows, security software, then re-test |
| the two openssl modulus md5 values differ | certificate and key do not match | back up current files to another directory, reissue, reinstall — all manual, snapshot first |
| `ss -tlnp` shows nothing on 443 but the security group is open | the web service is not listening | service start or config binding — manual |
| `nginx -t` fails after a deploy | config syntax or file paths wrong | fix config manually; reload stays manual |
| a `*.cn` validation log shows query timed out looking up A/AAAA | CA-side resolver cache | wait or change validation method |

## Evidence artifact (not part of this skill)

Handing the report over as a file was proposed as an optional low-risk
write, but that proposal is not signed off, so this skill ships no
file-writing path at all: the entry script has no artifact option, the
report is returned as text for the customer to copy, and nothing on the
instance or in `/tmp` is created, appended, truncated or deleted here.
