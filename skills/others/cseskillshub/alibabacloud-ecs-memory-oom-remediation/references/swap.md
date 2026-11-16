# Swap configuration reference

Command wording and constraints follow the Alibaba Cloud document on configuring the
Swap partition of a Linux instance:
https://help.aliyun.com/zh/ecs/support/how-do-i-configure-the-swap-partition-of-a-linux-instance

## When Swap is a candidate

- The instance is a Linux ECS instance.
- Physical memory is at most 8 GiB. Above 8 GiB the official guidance is not to
  configure Swap, and this skill never recommends or performs it.
- There is memory-pressure evidence: OOM lines in the kernel log, a used-memory signal,
  or a CloudMonitor memory utilisation reading at or above 85 percent.
- After the change at least 5 GiB of disk space stays free. The official document
  advises against configuring Swap when the remaining space drops below 5 GiB.
- The system disk is not a basic cloud disk. The official document warns that Swap on a
  basic cloud disk performs poorly and creates I/O bottlenecks; efficient cloud disks,
  SSD cloud disks and ESSD are acceptable.
- The Cloud Assistant plugin is reachable in the guest, or the customer is willing to
  run the manual steps themselves.

The entry script evaluates every item above and prints them one by one as PASS, FAIL or
UNKNOWN. UNKNOWN is treated as unmet: an unproven precondition never authorizes a change.

## Two ways to get Swap

1. **Guided (default).** The customer runs the commands. This is what the skill outputs
   whenever the confirmation for a change was not given in the current turn.
2. **Confirmed delivery.** With `--confirm-swap-change enable` (or `disable`) the skill
   delivers exactly one frozen plugin command through Cloud Assistant. The token may be
   passed only after the customer said yes to that specific change in this turn; the
   command text is not built from customer input.

## Plugin commands (Cloud Assistant, recommended path)

Status of the current configuration:

```bash
acs-plugin-manager --exec --plugin ACS-ECS-SwapConfig --params --status
```

Enable (the plugin sets `vm.swappiness` to 20 by default):

```bash
acs-plugin-manager --exec --plugin ACS-ECS-SwapConfig --params --enable
```

Disable and roll the change back:

```bash
acs-plugin-manager --exec --plugin ACS-ECS-SwapConfig --params --disable
```

`disable` is a change with the same blast radius as `enable`: it also requires the
confirmation token and it also gets verified afterwards.

## Manual steps when Cloud Assistant is not usable

```bash
swapon --show                                   # current state
sudo fallocate -l 1G /swapfile                 # create the file
sudo dd if=/dev/zero of=/swapfile bs=1M count=1024   # fallback if fallocate fails
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
SWAP_FILE_PATH="/swapfile"
if ! grep -q "swap" /etc/fstab; then
  echo "${SWAP_FILE_PATH} none swap sw 0 0" | sudo tee -a /etc/fstab
fi
sudo swapoff -a && sudo swapon -a && swapon --show   # verify persistence
```

Rollback of the manual path: `sudo swapoff /swapfile`, delete the matching
`/etc/fstab` entry, then remove the swap file.

The skill prints these steps for the customer to run; it does not splice them into a
delivered command.

## Performance limits that must stay in the answer

- Swap lives on disk. It relieves memory pressure, it does not replace memory.
- Swap increases disk I/O. Watch whether the IOPS utilisation and the OOM evidence both
  improve after the change; if IOPS becomes the new bottleneck, the correct answer is a
  larger instance spec.
- Long-term reliance on Swap is a signal to upgrade the instance type, not a steady
  state.

## When a confirmed enable is still refused

The confirmation token is necessary, not sufficient. A confirmed `enable` delivers nothing
when:

- a precondition fails or is unknown - `SWAP-CHANGE-BLOCKED:`;
- the Cloud Assistant agent reads as `offline` or `unresponsive` -
  `SWAP-CHANGE-AGENT-UNREACHABLE:`;
- the guest already shows Swap with more than one tenth of its room left -
  `SWAP-CHANGE-ALREADY-CONFIGURED:`. A second Swap file does not address the process that
  holds the memory, so the report routes to the holder, the runtime limit or the spec.

Swap that exists but is nearly exhausted is a different case: adding to it remains a
legitimate mitigation and still needs the same confirmation.

## Verification after a change

A confirmed change re-collects on its own: once the plugin command returns, the entry
command dispatches the read-only collector again and prints the comparison in the same
report, so nothing is claimed as fixed on the strength of intent. Each key is judged by
its own meaning, not by "the value moved":

| Verdict | When it is issued |
|---|---|
| `EASED` | OOM lines stopped, available memory rose by at least 10 percent, or the busiest device's `%util` fell |
| `WORSENED` | available memory fell by at least 10 percent, or `%util` rose |
| `STILL PRESENT` | the kernel log still carries OOM lines |
| `CONFIGURED` / `REMOVED` | Swap appeared or disappeared - a state change, explicitly not a relief claim |
| `UNCHANGED` | the movement is inside the tolerance |
| `UNVERIFIED` | one of the samples did not carry a usable reading (including an unreadable `iostat`) |
| `NO BASELINE` | the pre-change sample had nothing to compare against |

When the in-guest collector was not consented, the report says
`UNVERIFIED: the change was delivered but ... was not read back` and hands the customer
`swapon --show` instead. Running with `--verify` outside a change compares two samples of
the same run and labels that limitation, because the pre-remediation reference lives in the
earlier report.