# Transfer methods, ports and documented paths

The mirror of `PORT_MATRIX` in `_constants.py`. Quote a row only for the method
the customer actually chose or is being offered.

| Method | Port / path | Notes |
|---|---|---|
| SFTP / SCP / rsync | TCP 22 | Single port, no dynamic data range. The default recommendation for Linux. |
| FTP | TCP 21 plus a passive data port range | The passive range must be configured on the server and allowed in the security group with an English slash, for example `39000/40000`. |
| Remote desktop file drag and drop | TCP 3389 | Requires an RDP session and drive redirection. If the session itself fails, see the port note below and hand the connection fault to the remote connection skill. |
| Web panel upload | The panel's actual port, often not the documented default | The allowed rule must match the port the panel listens on. |
| Workbench file management | Browser to the Workbench service | No inbound customer-side port is required. |
| Object storage intermediary | HTTPS 443 to OSS | No instance inbound port involved; use for bulk or cross-region transfer. |

## Selecting a method

1. Linux and a shell account → SFTP/SCP on TCP 22. One port, encrypted, no
   passive range to maintain.
2. Must keep FTP → configure a bounded passive range, allow exactly that range
   in the security group, and set the same range in the FTP server.
3. Windows and an interactive session → RDP drag-and-drop, or Workbench file
   management when the RDP path is unavailable.
4. Many files, a different region or a different account → OSS as the
   intermediary: upload to a bucket, download from the instance over HTTPS.
5. Console artifacts (key pairs, downloaded reports) → they can be downloaded
   once from the console; re-issue rather than trying to fetch them through an
   API that does not expose them.

## Console and platform limits

- **Workbench one-time download size.** The Workbench file management console
  has a per-file size limit; ticket `T-16BA2895` documents a customer hitting
  the 100 MB limit on download. Re-check the live console text before quoting a
  number, and for larger files use SFTP, OSS or a split archive. Never tell the
  customer that the limit can be lifted for their account: it is a platform
  policy, not a customer-side setting.
- **RDP port may not be 3389.** A customer can change the remote desktop port
  (ticket `T-16BA2895` documents port `33089`). A security group that allows
  3389 then looks correct while the session still fails. Ask whether the RDP
  port was changed, and check the guest's configured port before blaming the
  security group. The connection fault itself belongs to the remote connection
  skill; only the file-transfer consequence stays here.
- **No FTP service by default.** ECS ships no FTP server, and the instance
  connection page has no file-transfer function of its own. Do not give the
  customer a "default FTP password".
- **Cloud Assistant has no file-download interface.** It can push files; it
  cannot be used to pull a file back.

## Failure signatures per method

| Method | Common failure | Discriminating evidence |
|---|---|---|
| SFTP | Port 22 not allowed, or sshd rejects the account | Security group rule plus the exact client error; credential part hands off |
| FTP | Passive range closed or mismatched | Control channel logs in, data channel fails (`ECONNREFUSED`, `control connection`) |
| RDP drag-and-drop | Session port changed or drive redirection disabled | RDP port setting; client redirection option |
| Panel upload | Panel port rule missing, or PHP upload limit reached | Panel listening port; PHP `upload_max_filesize` / `post_max_size` pasted by the customer |
| Workbench | Per-file size limit reached | The file size versus the console's stated limit |
| OSS intermediary | Bucket policy, endpoint or credential problem | OSS error code and the endpoint used |

## Where the port matrix is used

`manual_steps()` prints the attached security group and points at this table
when the group list is readable. Compare inbound rules against the chosen
method row; report a missing or narrowed rule as the finding, not as a guess.
