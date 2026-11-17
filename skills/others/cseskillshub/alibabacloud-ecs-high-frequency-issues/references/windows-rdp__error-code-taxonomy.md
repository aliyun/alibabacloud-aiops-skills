# Error-text / error-code taxonomy for Windows Remote Desktop

A customer reports these as the literal text or code on the `mstsc` dialog. The
skill matches on this observable string (never invents a code that a ticket did
not show), routes to a branch, and states a confidence — several causes below
are operator-inferred in the source tickets and must be reported as a probable
branch, not a proven root cause. The machine-readable form lives in
`ERROR_TAXONOMY` in [../scripts/areas/windows_rdp/_constants.py](../scripts/areas/windows_rdp/_constants.py).

## Code / string to branch

| Customer-visible text or code | Branch | What it means | This skill's move (never executes a fix) |
| --- | --- | --- | --- |
| `0xd07` | account-lockout | Sign-in rejected: the user account is locked. | Query local account state / lockout events; guide a rescue sign-in and narrowing the 3389 source; never auto-unlock. |
| `0x204` | client-or-path | Client could not establish the RDP connection. | Verify cloud side + in-guest listener; emit the client evidence checklist (telnet / tracetcp / tracert / cip.cc). |
| "function requested is not supported" | nla-credssp | CredSSP / NLA negotiation between client and server failed. | Query the RDP-Tcp NLA registry values (read-only); give the client-side adjustment as manual guidance. |
| "security layer" / "cannot connect to the security database" | nla-credssp | The RDP security layer could not be negotiated. | Same branch; suggest a Workbench/VNC bypass to split client vs instance. |
| "credential security support provider" / CredSSP / NLA | nla-credssp | Authentication oracle mismatch, often after a client or server patch. | Read NLA values; recommend the client change manually; do not claim a proven cause. |
| "an internal error has occurred" | sam-lsa | Generic authentication-layer failure from `mstsc`. | Classify as a probable SAM/LSA service state issue; advise rescue sign-in then a manual restart and Windows update; never restart here. |
| "Security Account Manager (SAM) or Local Security Authority (LSA) ... error state" | sam-lsa | The SamSs service is in a bad state (Kerberos ticket, a defective patch, or interfering security software). | Give the operator's own steps (snapshot first, restart to recover, apply the latest cumulative update) as manual guidance. |
| "cannot connect to the local security authority" | sam-lsa | Authentication could not reach the LSA. | Confirm reachability through a bypass channel; treat as probable, not proven. |
| stuck at "Please wait" after the password stage | session-conflict | Session conflict / resource hold, often after switching users. | Query sessions (read-only); advise a manual restart and the multi-session setting as a console step. |
| "online reset password failed" | credential | The Cloud Assistant command behind an online reset could not run. | Read `DescribeCloudAssistantStatus`; give the console (offline) reset step, noting it needs a console restart. |
| instance sign-in failed with a RequestId | cloud-side-policy / manual | The console sign-in request itself failed. | Record the RequestId for platform follow-up; continue the layered checks. |
| VNC shows only 800x600 or a blank/garbled picture | channel-choice or resource-exhaustion | VNC is a rescue console, not a daily desktop; or the desktop stack is exhausted. | Explain channel choice; read the resource watermark; do not call it an instance fault by itself. |

## Notes carried from the source tickets (so wording stays honest)

* The "four wrong passwords locks the account" threshold is the *default* local
  Windows policy the tickets referenced; a domain-joined host can carry a
  different policy that these query-only reads cannot see.
* The SAM/LSA explanation ("defective Microsoft patch or third-party security
  software interfering with SamSs; low-probability Windows defect") is the
  support engineer's own wording from one well-documented ticket; the fix there
  was "snapshot, restart, update Windows" — all manual.
* NLA / certificate root causes were **inferred** in several tickets where the
  real resolution happened on a phone call; do not present them as confirmed.
* These codes are the `mstsc` client-side codes the tickets actually quoted.
  Any additional code (for example `0x113f`, `0x3`) has no evidence in this
  tier and must not be added to the map.
