# Expected platform behaviour that is not a fault

Nine mechanisms in this tier's tickets were reported as breakage and were not.
Ruling them out comes before digging into a customer's configuration, because
the reverse order produces long dead-end threads: the customer changes web
server settings, nothing improves, and the actual explanation was a billing
state or a scheduled task the whole time.

Each entry below is the wording that raises it, the mechanism, and what the
report is allowed to conclude.

## 1. A console restart that looks like a hang

- **Wording**: stopping, stuck on stopped, restarting, "shut down by itself"
- **Mechanism**: a console restart without the forced option releases processes
  and flushes memory to the disk before the guest kernel stops. Normally 5 to 10
  minutes, up to 15. Nothing can be done meanwhile, and no in-instance command
  will run during it.
- **Conclusion available**: wait out the window, then re-test. Genuinely stuck
  belongs to the instance-state area.
- **Note**: the explanatory page for the stopped-or-restarting status was pasted
  into a ticket dialogue with its URL cut off mid-string, so this file quotes no
  URL for it. It is listed as pending in `references/web-service-runtime-config__help-docs.md`.
  Evidence: T-E923DA06 (window), T-43513829.

## 2. Everything stopped at the same time

- **Wording**: services disappeared, "auto closed", scheduled shutdown, turned off at night
- **Mechanism**: an OOS scheduled start/stop task, often left behind by a
  previous administrator, shuts the whole instance down at a fixed time.
- **Conclusion available**: the pattern is a task, not a crash. Hand off to the
  instance-state area plus the OOS task list; deleting the task is a manual step.
  Evidence: T-43513829.

## 3. Image pulls that time out from a mainland region

- **Wording**: cannot create image, pull timeout, docker hub timeout, registry timeout
- **Mechanism**: Docker Hub reachability from mainland regions was affected by an
  upstream change on Docker's side.
- **Conclusion available**: state the reachability fact, and separate it from a
  service fault before any guest inspection.
- **Limit**: third-party mirror addresses appeared in a ticket, pasted by a
  handling agent. They are not official and are not recommended here.
  Evidence: T-C59D3702.

## 4. Port reachable, site not serving

- **Wording**: port works but http does not, ping ok, telnet ok, domain not working
- **Mechanism**: a domain pointing at a mainland-region server must have
  completed ICP filing before it can serve a site.
- **Conclusion available**: when the network layer tests pass and HTTP still
  fails, filing is the first candidate, and the matter belongs to the filing
  process, not to a web server config.
- **Region nuance**: the mainland test is a `cn-` prefix with the one region
  excluded that the tickets did not treat under the same filing rule, so the
  prompt is not raised on every `cn-` instance. Evidence: T-713A543E.

## 5. Handshake fine, no response

- **Wording**: tcp handshake fine, response not received, retransmit, cannot reach internet
- **Mechanism**: a pay-by-traffic bandwidth service with an unpaid balance is
  suspended, so outbound response packets are stopped even though the guest sent
  them.
- **Conclusion available**: check billing state before assuming a service fault.
  The account-side fix is not this skill's; the report names the handoff.
  Evidence: T-7C096742.

## 6. Slow or failing only from overseas

- **Wording**: overseas users cannot open, other country slow, international access
- **Mechanism**: cross-border latency, not a platform restriction.
- **Conclusion available**: state that no restriction was found, then hand off
  the path and carrier question. This skill reports only what the guest side
  shows. Evidence: T-A692D630.

## 7. A security group that will not delete

- **Wording**: security group cannot be deleted, ip still occupied, eci
- **Mechanism**: after an ECI instance is deleted its elastic network interface
  can persist for up to 30 minutes.
- **Conclusion available**: wait, then retry. Another product's lifecycle.
  Evidence: T-35437580.

## 8. Cost tags that have not appeared

- **Wording**: bill has no tag, cost split missing, label not shown
- **Mechanism**: billing detail is produced on a T+1 cycle, and pod tags must be
  written as annotations rather than labels.
- **Conclusion available**: hand off to the cost-tagging area; the delay is
  expected. Evidence: T-BBB17081.

## 9. CDN asked for in an internal form

- **Wording**: cdn internal address, internal network cdn
- **Mechanism**: CDN is served over the public network; there is no
  internal-network form of it.
- **Conclusion available**: correct the premise before continuing any diagnosis.
  Evidence: T-48D25F5F.

## Why this list is checked first

Five of the nine close a ticket with no change to the customer's system at all.
The other four change who should be asked next, which is also faster than a
configuration investigation. A report that has not ruled these out is not yet
entitled to conclude anything about the customer's web server.
