# Commands: execution whitelist and manual lane

The skill has exactly one gated command channel. The whitelist below is the
mirror of `GUEST_COMMAND_WHITELIST` in `_constants.py`; anything outside it is
printed for the customer to run and paste back, never executed by the agent.

## Execution whitelist (one command, one approval)

| Program | Allowed flags |
|---|---|
| `df` | `-h`, `-i`, `--output`, `--print-free`, `--total`, `-k`, `-m`, `-T` |
| `du` | `-x`, `-s`, `-h`, `--max-depth`, `--inodes`, `--apparent-size`, `--block-size` |
| `ls` | `-l`, `-a`, `-h`, `-t`, `-r`, `-i`, `-d`, `-1`, `-la`, `-lh`, `-lt` |
| `stat` | no flags |
| `findmnt` | `-l`, `-t`, `-o`, `--submounts`, `-r`, `-n`, `-R`, `--TARGET` |
| `lsof` | `+L1`, `-p`, `-u`, `-n`, `-P` |
| `wc` | `-l`, `-c`, `-w` |

Value-taking flags must be joined with `=`, for example
`findmnt --target=/www`. Shell composition and redirection characters are
rejected: `; & | < > $ \n \r \ ' ` * ? ! ( ) { } "`. Maximum command length is
400 characters, maximum path length 200.

Before sending any command the agent MUST state the exact command line, the
scope (this one instance, this one command), the effect (inspection only, no
rollback required), and obtain approval for that single command. A second
command needs a second approval.

## Manual lane (customer runs and pastes back)

| Purpose | Command |
|---|---|
| Listening sockets | `ss -tlnp` or `netstat -tlnp` |
| Host firewall | `firewall-cmd --list-all`, `ufw status verbose`, `iptables -S`, `nft list ruleset` |
| Transfer throughput | `iftop`, `nload`, `sar -n DEV 1 5` |
| FTP server configuration | the server's config file and its `pasv_min_port` / `pasv_max_port` |
| Panel status | `bt status`, `bt 22` (panel port) |
| PHP upload limits | the panel's PHP settings page, or `php -i | grep -E 'upload_max_filesize|post_max_size'` |
| Security group as the customer sees it | a console screenshot or the rule list pasted verbatim |

Commands that change state (`sysctl -w`, `chmod`, `chown`, service restarts,
`iptables -F`) are never sent and never recommended as something the agent will
run. When the customer must run one, state that it is temporary until the next
restart where that is true, and that it is their action.

## Customer-side port test

Ask the customer to test the transfer port from their own network and again on
a phone hotspot:

```
# from the customer workstation; nc is illustrative, the customer runs it
nc -vz <public-ip> 22
```

A failure on one network only points at the customer's egress path, not at the
instance. This is a manual step: the agent does not run it from the sandbox and
must not present a sandbox result as the customer's network result.
