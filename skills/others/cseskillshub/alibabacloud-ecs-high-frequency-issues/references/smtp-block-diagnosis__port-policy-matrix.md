# Port / Policy Matrix -- Mail Ports on Alibaba Cloud ECS

This is the evidence-anchored truth table the diagnosis routes against. Two
discipline rules apply to EVERY row:

1. **Evidence tags are part of the data.** `[dialogue]` = verbatim support
   ticket conversation reviewed; `[summary]` = ticket summary only, original
   dialogue not re-pulled; `official doc` = help-center document linked below;
   `UNCONFIRMED` = reports conflict -- state the conflict honestly and verify
   against current official documentation BEFORE making any promise. Never
   quote an UNCONFIRMED row as settled policy.
2. **Scope discipline.** The platform-side facts below concern Alibaba Cloud
   only. What the *receiving* provider does (spam policy, overseas-IP policy)
   is a separate layer -- see references/smtp-block-diagnosis__smtp-error-signatures.md.

| Port | Direction | Platform restriction | Can a customer apply to change it? | Typical symptom | Evidence |
|------|-----------|----------------------|------------------------------------|-----------------|----------|
| 25 | outbound (sending) | Yes -- blocked by default on new instances regardless of security-group egress rules | Yes, application via the console; review ~1 business day; result by email; NOT guaranteed; direct-MX self-hosted use is refused per the agreement | silent TCP timeout to remote :25 while 443/465/587 behave differently | `[dialogue]` tickets T-BFFFC987, T-0DC2E989; official doc https://help.aliyun.com/zh/ecs/product-overview/limits |
| 25 | inbound (receiving) | **UNCONFIRMED** -- `[summary]` reports conflict: some say inbound 25 has no platform restriction (security group + listener only), others were told inbound also needs an unblock application | Verify current official policy first; if an application is needed, use the same entry as outbound | "cannot receive mail on 25" | `[summary]` T-5919F890 / T-398559AD vs T-DE88AA98 / T-62FDA757 / T-248E052C |
| 465 | outbound | Not restricted -- no opening needed (implicit TLS submission) | n/a | works once customer security-group egress + guest firewall + provider account allow it | `[dialogue]` T-8E8AD7A5 agent verbatim |
| 587 | outbound | Not restricted -- no opening needed (STARTTLS submission) | n/a | same as 465 | `[dialogue]` T-8E8AD7A5; `[summary]` T-3E637B73 |
| 993 / 995 | outbound (IMAPS/POP3S client access) | Not restricted by the platform as mail-sending ports | n/a | when they time out together with 465/587, suspect customer egress rules, not a platform mail policy | `[dialogue]` T-897D4DEA (all-mail-port timeout; SG egress found limited) |
| 25 (IPv6) | outbound | **IPv6 opening for 25 is NOT supported** | No -- IPv4 only, or use 465 | IPv6 telnet to provider :25 fails even when IPv4 was unblocked | `[dialogue]` T-F418FAF1 |
| any | regions outside the Chinese mainland | **UNCONFIRMED** whether the 25 policy and unblock application behave identically overseas | point customers to the official limits doc + an application attempt with honest purpose | overseas instance refused / told no | `[summary]` T-AFC2095D vs successful unblocks `[summary]` T-9F9BED3F / T-B6515F06 |
| 25 (application) | -- | The Port-25 Usage Service Agreement limits an unblocked 25 to **connecting to third-party SMTP servers**; self-hosted MTA direct-to-MX delivery is out of scope | declaring a use case truthfully and being refused is the correct outcome -- NEVER misdeclare | compliant applicant (direct MX) refused with reviewer note | `[dialogue]` T-0DC2E989 (reviewer note verbatim) |
| 25 (application) | -- | Application must reference a **VPC-mode public IP** (not a classic-network IP form) | Yes -- correct the IP form in the application | "no permission to use this IP address" at apply time | `[dialogue]` T-384967AE (resolved by using the VPC public IP) |
| PTR / rDNS | -- | Custom reverse DNS for the public IP is **not self-service** (ECS and lightweight alike) | No | mail rejected by providers requiring matching PTR | `[summary]` T-043B7B7E -- verify current docs; recommend an external provider |

## Conflicting agent wordings observed in tickets (why unified wording matters)

Past tickets contain ALL of the following statements for the same symptom,
sometimes within one ticket -- the skill's value includes collapsing them
into the single table above:

- "25 is blocked on all cloud providers everywhere" `[summary]` T-C8F61FF1
- "default restricted, unblock applications are NOT supported" `[summary]`
  T-E5CF70BE / T-C35AA6FA
- "you may submit an unblock application, a specialist reviews it"
  `[dialogue]` T-0DC2E989 / T-BFFFC987 -- applications DID succeed in some
  tickets `[summary]` T-9F9BED3F / T-B6515F06
- "465/587 must be 'opened' too" (customer misconception, refuted by
  `[dialogue]` T-8E8AD7A5: they are open by default)

## Layer mapping (what each row means for attribution)

| Observation | Layer to conclude | Next pointer |
|-------------|-------------------|--------------|
| 25 timeout + 465/587/443 reach the provider | platform outbound-25 block | references/smtp-block-diagnosis__unblock-application-path.md + 465 relay |
| 25 AND 465/587 timeout, 443 fine | customer config layer (SG egress / guest firewall) | security-group quickstart doc + firewall readings |
| every port including 443 timeout | broader egress path | general public-network handoff (vpc skill) |
| banner received then 5xx/4xx reply | peer application layer | references/smtp-block-diagnosis__smtp-error-signatures.md |
| TCP connected then closed quietly | reachable; session refused by peer or link | peer/provider + cross-border hint |
| refused on receive-side test | nothing listening host-side | listener / container mapping |
