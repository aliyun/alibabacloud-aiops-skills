# Module 5: Remediation Best Practices

## Purpose
Guide containment, eradication, and hardening after a confirmed cryptomining
compromise. This skill is **read-only** — it does NOT perform any of these
actions. It produces prioritized recommendations; the operator executes them
via the Security Center console, ECS console, or their ops tooling.

## Priority Framework

### Pre-P0 — Preserve Evidence & Backup (before any cleanup)
0. **Create a snapshot / disk image of the affected instance BEFORE any
   eradication action.** This preserves forensic evidence (process memory,
   malicious files, logs) and provides a rollback point if cleanup breaks
   business data. In ticket practice, 35/73 cases performed backup first.
   - ECS console → Disks → Create Snapshot (or automated snapshot policy)
   - Do NOT create a "custom image" from the infected instance for later
     rebuild — that bakes the malware into the image (see warning below).

### P0 — Immediate Containment (within 30 minutes)
1. **Isolate the affected instance(s)** at the network layer — tighten the
   security group / VPC ACL to cut outbound mining-pool and C2 traffic. Prefer
   network isolation over shutdown so forensic state is preserved.
2. **Kill the mining process(es)** identified in the IOC section (Step 2), then
   **remove persistence**: cron jobs (`/etc/cron*`, user crontabs), systemd
   units/timers, rc/startup scripts, `LD_PRELOAD` entries, and rogue SSH
   `authorized_keys`. A miner that reinstalls itself was not fully eradicated.
3. **Block the mining-pool IPs/domains** (IOC list) on egress firewall /
   security group so any missed implant cannot reconnect.

### P1 — Eradicate Entry & Rotate Secrets (within 2 hours)
4. **Patch the entry vulnerability** flagged `asap` in Step 4 (or fix the weak
   config / default credential on the exposed service).
5. **Rotate credentials** that may have been exposed on the host: RAM AccessKeys,
   SSH keys, database passwords, and any secrets in env/config files.
6. **Hunt the sample fleet-wide** using the IOC hashes/process names — worm-style
   miners (sysrv, kinsing) spread laterally; assume neighbors are compromised.

### P2 — Reduce Attack Surface (within 24 hours)
7. **Close unnecessary public exposure** (Step 4 exposed assets): remove public
   IPs, restrict ports, front services with WAF / bastion / VPN.
8. **Enable Security Center proactive defense** — anti-mining / malicious-process
   protection, webshell protection, and auto-quarantine where appropriate.
9. **Enforce least privilege** on the compromised host's identity and review
   RAM permissions granted to it.

### P3 — Long-Term Hardening (within 1 week)
10. **Rebuild from a known-good image** for full assurance if the host held
    sensitive data or the rootkit depth is uncertain.

> **WARNING:** Never create a custom image from an infected instance and use it
> to "reset" the server. The image will contain the malware (persistence scripts,
> trojanized binaries, cron backdoors), causing immediate reinfection on boot.
> Always rebuild from an **official base image** or a **pre-infection snapshot**,
> then restore only verified-clean business data.
11. **Continuous monitoring** — enable real-time mining/malicious-process alerts,
    periodic baseline/config checks, and CPU/network anomaly alerting.
12. **Vulnerability lifecycle** — establish routine patching SLAs for `asap`
    vulnerabilities and exposed-asset reviews.

## Why Not Just Kill the Process?

**Ticket analysis: ~1/3 of cases (23/73) experienced reinfection** because only
the process was killed without removing persistence or blocking the entry vector.

Cryptominers almost always install persistence and often a watchdog that
respawns the miner. The full persistence checklist:

- `cron` jobs (`/etc/cron*`, user crontabs, `/var/spool/cron/`)
- `systemd` units / timers
- `rc.local` / startup scripts (`/etc/rc.d/`)
- `LD_PRELOAD` entries (`/etc/ld.so.preload`)
- **`ld.so.preload` / shared-object hijack** (dynamic linker injection)
- **`/etc/init.d/` legacy scripts**
- **`.bashrc` / `.profile` / `/etc/profile.d/` shell-profile injection**
- **Rogue SSH `authorized_keys`** (attacker's public key)
- **Malicious Docker containers / Kubernetes DaemonSets**
- **Hidden users** (UID=0 pseudo-users in `/etc/passwd`)

Killing the process without removing ALL of the above, closing the entry
vulnerability, and blocking the pool endpoints leads to reinfection within
minutes. Follow the full Pre-P0 → P0 → P1 sequence.

**A miner that comes back within hours was NOT fully eradicated — re-run Step 1
(`query_mining_alerts.py`) to confirm zero alerts before declaring success.**

## Post-Cleanup Verification Checklist

Before declaring the incident resolved, confirm ALL of the following:

- [ ] No mining alerts in SAS for 24+ hours (re-run Step 1 / `query_mining_alerts.py`)
- [ ] No mining-pool outbound connections in network logs
- [ ] All persistence items removed (cron, systemd, ld.so.preload, init.d, rc, authorized_keys, profile scripts)
- [ ] Entry vulnerability patched or exposed port closed (verify via Step 4 / `query_attack_surface.py`)
- [ ] Mining-pool IPs/domains blocked at security group / firewall egress
- [ ] Credentials rotated (RAM AK, SSH keys, DB passwords)
- [ ] If custom image was used: image source verified clean or rebuilt from official base

## Reference Documents
- [Security Center — Handle Alerts](https://www.alibabacloud.com/help/en/security-center/user-guide/alerts)
- [Security Center — Vulnerability Management](https://www.alibabacloud.com/help/en/security-center/)
- [ECS Security Group Best Practices](https://www.alibabacloud.com/help/en/ecs/)
