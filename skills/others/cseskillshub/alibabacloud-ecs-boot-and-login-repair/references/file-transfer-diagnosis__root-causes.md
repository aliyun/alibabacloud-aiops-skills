# Root causes behind the file-transfer area

Ranked from the support history behind this tier. The ranking is a prior for
which check to run first, never a conclusion. State a cause only when a value
returned by an action or by the customer supports it, and say where the value
came from.

## B1 — no transfer path chosen

| Rank | Cause | Discriminating evidence |
|---|---|---|
| 1 | Customer assumes ECS ships an FTP server or a console upload button | The customer asks for an "FTP password" or an upload button; no instance-side FTP service exists |
| 2 | Customer is looking at the instance connection page, which has no file transfer function | The page named by the customer |
| 3 | Customer needs a method for a file larger than a console limit | File size versus the console's stated per-file limit |

Correct answer is a method, not a fault: SFTP/SCP on 22, FTP with a configured
passive range, Workbench, panel upload, or OSS as an intermediary.

## B2 — cannot connect

| Rank | Cause | Discriminating evidence |
|---|---|---|
| 1 | Ingress rule for the transfer port missing, narrowed, or authorizing the wrong source | `ecs:DescribeSecurityGroupAttribute` compared with the customer's real egress address |
| 2 | Security group allows 3389 but the RDP port was changed | The guest's configured RDP port; ticket `T-16BA2895` documents `33089` |
| 3 | Service not listening, or listening only on loopback | Customer-pasted `ss -tlnp`; the skill's whitelist cannot read it directly |
| 4 | Guest firewall drops what the security group allows | Customer-pasted `firewall-cmd --list-all`, `ufw status`, `iptables -S` |
| 5 | Customer-side egress, VPN or corporate proxy blocks the port | One-sided failure: hotspot or another client works |
| 6 | Instance is stopped, in another account or in another region | `ecs:DescribeInstances` empty while `sts:GetCallerIdentity` succeeds |

## B3 — connects but slow

| Rank | Cause | Discriminating evidence |
|---|---|---|
| 1 | Instance public bandwidth is small or at its peak | Configured outbound value versus observed rate; console chart |
| 2 | Link quality on the customer-to-instance path, especially cross-border | Region pair, one-sided failure, MTR-style measurements |
| 3 | Small-file overhead or client concurrency | File count; single archive transfers at a normal rate |
| 4 | Disk IO saturation on the instance | Disk latency/throughput readings; the IO performance area owns the conclusion |

## B4 — transferred but rejected or invisible

| Rank | Cause | Discriminating evidence |
|---|---|---|
| 1 | File landed outside the directory the application reads | `ls -l` / `stat` on the intended target versus the actual path |
| 2 | Write permission missing for the login user | `ls -l` ownership and mode on the target directory |
| 3 | Disk space or inodes exhausted | `df -h` / `df -i` pasted by the customer |
| 4 | Panel or PHP upload limit reached | Panel setting and `upload_max_filesize` / `post_max_size` |
| 5 | Application cache or deployment path not refreshed | The file exists on disk but the site still serves the old one |

## B5 — protocol mode details

| Rank | Cause | Discriminating evidence |
|---|---|---|
| 1 | FTP passive range not configured or not allowed | Login succeeds, data channel fails; `control connection` / `ECONNREFUSED` |
| 2 | Passive range configured on the server but not opened in the security group (or vice versa) | Compare the server's range with the group's rule |
| 3 | Too many parallel connections from one client IP | Single-connection test succeeds |
| 4 | Active mode used through NAT or a firewall | Switching to passive fixes it; SFTP avoids the issue entirely |
| 5 | Client incompatibility | Another client or the `sftp` command works |

## B6 — capability boundary

| Rank | Cause | Discriminating evidence |
|---|---|---|
| 1 | Console artifact can be downloaded once, not fetched through an API | The artifact type and the console path |
| 2 | Workbench per-file size limit reached | File size versus the console's stated limit; ticket `T-16BA2895` documents 100 MB on download |
| 3 | Cloud Assistant has no file-download interface | The requested direction is instance → customer |
| 4 | Cross-account or cross-region bulk transfer needs an intermediary | Accounts or regions differ; OSS is the documented alternative |
| 5 | No public IP and no jump path | Network reachability of the instance; use a jump host or OSS |

## Reporting rule

Lead with the branch and the confirmed cause. If no cause is confirmed, say
`unverified`, list which readings were taken, and name the single next reading
that would decide it. Never present a ranked prior as a measured fact.
