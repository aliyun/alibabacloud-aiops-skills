# Error signatures — literal text to branch

The mirror of `ERROR_SIGNATURES` in `_constants.py`. Matching is case-insensitive
substring matching on the customer's own error text, and error signatures rank
above symptom keywords. Quote the matched signature in the report so the
customer can see why the branch was chosen.

| Literal pattern | Branch | Likely cause | Confidence | Next action |
|---|---|---|---|---|
| `permission denied` | B4 | Upload landed on a path the login user cannot write | high | Re-upload into the site root (for example `/www/wwwroot/<site>`), or switch the client to SFTP on port 22 with the instance account |
| `econnrefused` | B5 | Server refused the data connection: passive range not opened, or connection limit hit | medium | Prefer SFTP, or configure and allow the FTP passive range; limit parallel connections from one client IP |
| `eai_noname` | B2 | Host name is incomplete or not resolvable | high | Re-enter the full public IP or resolved domain; verify account and password separately |
| `errno 110` | B2 | Outbound connection timed out (ETIMEDOUT) while downloading from the instance | medium | Test the same download from the instance and from the workstation; if only one side fails, the local egress path is the suspect |
| `connection lost before handshake` | B2 | SSH session torn down before authentication completed | medium | Confirm which account is locked or rate limited; hand the credential part to the login credential skill |
| `control connection` | B5 | FTP control channel times out after login, typical of an unopened passive range | high | Switch to SFTP, or open the passive range and set the same range on the server |
| `no folders available` | B1 | FTP account root is not a browsable directory | medium | Use SFTP with the instance account, or set the FTP user home to the site directory |
| `can't connect to the remote computer` | B2 | Remote desktop unreachable; out of scope unless a transfer is blocked by it | low | Hand the connection fault to the remote connection skill; keep only upload-path guidance here |
| `forcibly closed` | B5 | Connection reset during transfer, often an idle or concurrency limit | low | Retry with one connection, or compress the files and transfer a single archive over SFTP |

## Rules for using this table

1. Report the matched literal, not a paraphrase. "ECONNREFUSED" is evidence;
   "connection problem" is not.
2. A signature gives the branch and a prior, never the final cause. Confirm with
   cloud evidence or a customer-pasted reading before stating a root cause.
3. When several signatures match, list them in script order and say which one
   is being treated as primary.
4. When nothing matches, `classify` returns `no-match` and defaults to B1; that
   is an invitation to ask the intake questions, not a diagnosis.
