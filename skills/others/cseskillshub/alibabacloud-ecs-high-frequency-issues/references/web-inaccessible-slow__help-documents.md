# Help documents and tools actually cited

Two rules shape this file. First, **no URL is invented**: an identifier that was not seen in an
engineer reply or in the verified API surface is written as a search key or as console navigation,
never as a link. Second, **a tool the skill cannot call is handed to the customer as a page to run
and paste back**, which is exactly what engineers did in the reviewed tickets.

## Verified backfill (2026-11-12)

Three engineer-cited documents are now resolved to live-verified URLs and frozen
as anchors in `references/doc-anchors.json`:

- `how-to-grab-data-packets-when-the-network-is-abnormal` -> anchor `web-inaccessible-slow__grab-packets`
- `query-and-case-analysis-linux-cpu-load` -> anchor `web-inaccessible-slow__linux-cpu-load`
- `log-on-to-an-instance-by-using-vnc` -> anchor `web-inaccessible-slow__vnc-logon`

These satisfy the "no invented URL" rule: each was seen in an engineer reply and
then live-verified (soft-404 judged, hash checked) before registration.

## Documentation identifiers

| Identifier | Where it came from | How to use it |
| --- | --- | --- |
| `what-do-i-do-if-i-cannot-access-a-website-hosted-on-an-instance` | the troubleshooting article cited for this scenario | Resolve it against the help site at run time (search the slug on the help portal, or open the article from the instance troubleshooting entry). Quote the article **title and slug** in the reply; do not paste a link assembled by hand, because a guessed path 404s in front of the customer |
| `455815` | document number referenced by engineers while locating this problem | Cite the number so the customer and the next engineer can find the same page; again, resolve rather than construct |

If a doc identifier cannot be resolved during the conversation, say what the article was for and
let the customer search it. An unverified link is worse than no link.

## Customer-run probes (no API exists in this skill)

| Page or tool | What it measures | How the skill uses it |
| --- | --- | --- |
| `boce` style multi-region dial test page | Whether the site answers from other cities and other carriers | Ask the customer to run it for the domain and for the direct IP and to paste the result table. This is the L3 evidence, and the only L3 evidence the skill claims |
| `cip` style "what is my IP" page | The client's real egress address, i.e. the address a security group rule has to allow | Ask the customer to open it and read out the address, or read the address from the web access log. Enterprise and VDI clients see a shared egress here, which is the usual reason "my colleague can open it and I cannot" |
| Browser developer tools, Network tab | Status code per request, redirect chain, failed sub-resource | Used to separate L6 from L7 and to find a page that loads but whose assets fail |
| Local `nslookup` / `dig` from the client | What the client's own resolver returns | Compared with the zone answer from L2 to expose a cached or overridden record |

These are **not** programmatic here: no API for either probe was verified for this tier, so the
skill never claims to have run them.

## Console navigation (parameterised, never copied)

Give the path plus placeholders, and take every identifier from the customer's own session:

- **ECS console > Instances > region `{regionId}` > instance `{instanceId}` > Security Groups** -
  to inspect or add the inbound rule named in the L4 finding;
- **ECS console > Instances > `{instanceId}` > Cloud Assistant** - to see whether the agent that
  level B depends on is present and online;
- **VPC console > Elastic IP Addresses > region `{regionId}`** - to confirm the binding behind an
  L1/L2 mismatch;
- **DNS console > Authoritative zones > `{domain}` > Resolution settings** - to change a record,
  which the customer does themselves;
- **ICP/Beian filing console** - for the L7 filing inference;
- **Billing center** - the authoritative place for arrears and expiry, and for the snapshot cost.

Never hard-code a resource id, a domain or an account id copied from another ticket or from an
example. Verify every identifier against `ecs:DescribeInstances` in the current session before
putting it in a link or a path, and never write another customer's resource into a reply.

## Declared evidence gaps

These four are open on purpose. Each one is a place where a plausible-looking addition would have
been a fabrication:

1. **CloudMonitor namespace and metric names.** The `DescribeMetricLast` call is verified, the
   metric identifiers were not. The scripts take them from the operator
   (`--cms-namespace`, `--cms-metric`) plus a saturation threshold (`--saturate-above`); with no
   threshold, L8 reports `INCONCLUSIVE` instead of guessing what "high" means.
2. **Blackhole / DDoS cleaning state and its unblocking window.** No verified describe call and no
   verified article identifier, so the skill points at the Anti-DDoS console by name only.
3. **Filing (ICP / access filing) state.** No verified describe call; L7 states an inference,
   labels it as such, and sends the customer to the filing console.
4. **Windows in-guest command set and its documentation.** Nothing Windows-specific was approved
   for dispatch, so the IIS path is guidance-only and no PowerShell command is presented as
   something the skill ran.

Two further absences worth stating: **Simple Application Server firewall** documentation was not
cited in this batch (the skill identifies the asset type and hands off), and **disk I/O as a cause
of slowness** had no ticket evidence, so no branch and no reference exists for it.
