# M1 — Transfer conditions, direction rules, and console blockers

Knowledge distilled from real support-ticket dialogues for the
"cross-account ECS transfer / verified-entity change" tier. The feasibility
engine in `scripts/axes/account_transfer_guide/transfer_guide.py --assess` reads the same tables
embedded in `scripts/axes/account_transfer_guide/_constants.py`; this file is the readable version for
interpretation.

> Evidence discipline: every rule below is tagged. `dialogue-verified` rules
> were re-read in ticket transcripts; `single-source` rules exist only in one
> ticket summary and MUST be hedged to the customer with "confirm against
> the official transfer-limitations section" — never presented as certain.
> The official limitations anchor:
> `https://help.aliyun.com/zh/ecs/user-guide/how-to-cross-account-transfer-migration-ecs-instance#babb9b36856x4`

## The five hard pre-transfer conditions

Support recites this list nearly word-for-word in multiple independent
tickets; it is the backbone of the checklist:

1. **Same verified entity (enterprises).** Enterprise accounts can transfer
   ECS instances only to accounts verified under the SAME enterprise
   entity — and the enterprise NAME must match character-for-character.
   Different enterprises cannot transfer between each other.
   *(dialogue-verified)*
2. **Same VPC, same zone, same region.** The vSwitch and security group
   entered in the transfer wizard must be in ONE VPC, and the destination
   vSwitch must sit in the instance's zone. Cross-region transfer is
   unsupported. *(dialogue-verified)*
3. **Target balance.** If the target account already has pay-as-you-go
   resources, its available balance (cash + credit line) must exceed
   100 CNY. *(dialogue-verified; not queryable from this skill — the target
   account owner checks Billing Center)*
4. **Unbind first.** Anything bound to the instance — an associated EIP, an
   SSH key pair — must be detached before the transfer.
   *(dialogue-verified; `--precheck` lists exactly which bindings exist)*
5. **Instance-level limits.** Some instances cannot be transferred at all,
   notably campaign / discounted purchases; read the official limitations
   section before starting. *(dialogue-verified for campaign exclusion;
   discount history needs a backend ticket check)*

Timing: an online transfer typically completes in about **30 minutes**
(dialogue-verified; never promise an expedite). Frequency: one ticket
summary states an instance can be transferred **once per half year** —
single-source, hedge it.

## Direction matrix

| Source -> Target | Verdict | Basis |
| --- | --- | --- |
| enterprise -> enterprise | Eligible ONLY when same verified entity AND identical name | dialogue-verified (3 tickets) |
| individual -> enterprise | Eligible with conditions; the limitations anchor applies | dialogue-verified |
| enterprise -> individual | Not supported — even when the legal representative is the same natural person | single-source (phone-record ticket) — hedge |
| individual -> individual | Generally accepted; the five conditions still decide | weak evidence — hedge |
| either direction, campaign/discount instance | Not eligible for direct transfer | dialogue-verified |
| either direction, distribution (reseller) relationship | Blocked per one summary — route to backend review | single-source — hedge |

A customer frequently believes "same legal person" or "both are enterprise
accounts" is enough — it is not; condition 1 asks for the identical entity
name. Answer "can it be done / why not / what next" together in one pass.

## What cannot be verified through cloud queries here

Real-name entity, campaign / discount labels, reseller relationship, and
account balance are NOT exposed to any read API this skill is allowed to
call — support handled them by asking the customer and escalating to the
backend. The skill therefore outputs a three-way verdict
(`TRANSFER_ELIGIBLE` / `TRANSFER_NOT_ELIGIBLE` / `NEEDS_MANUAL_REVIEW`) and,
for the manual items, asks the customer to self-check in Account Center or
submit a ticket with: **instance ID, both account UIDs, and the exact error
text**.

## Console blocker catalog (K6)

| What the customer pastes / sees | Root cause | Fix |
| --- | --- | --- |
| "the vSwitch cannot be selected" at the network step | No vSwitch exists in the instance's zone inside a matching VPC | `--precheck` for the instance ZoneId/VpcId, create or pick a vSwitch in that exact zone, retry (dialogue-verified pair: blocker ticket + condition 2) |
| "transfer failed" | One of the five conditions: campaign purchase / entity mismatch / bindings not detached / cross-region / balance | run `--assess` then `--precheck`; if all excluded, ticket with instance ID + both UIDs + error text |
| Status shows "under review" after a failure | A transfer application is in review (typically the re-submitted one) | wait for review to settle; check the transfer record; single-source reading — hedge |
| "the real-name authentication type of the enterprise account and the target account is inconsistent" | Direction not supported (see matrix) | `--assess` with both types; if blocked, `--guide image-migration` |
| "where do I find the instance ID?" | Console navigation friction | `--precheck --region-id <r>` lists IDs automatically |

## The human console flow (never automated by this skill)

There is **no** transfer-initiation API in the verified evidence: the source
account owner starts the transfer in the ECS console, the target account
owner accepts it, then both watch the wizard (vSwitch + security group
inputs happen here). Guide with the flow anchor
`https://help.aliyun.com/zh/ecs/user-guide/how-to-cross-account-transfer-migration-ecs-instance#0be63e3029ta3`
and hand over the M3 post-transfer list at the end. The snapshot backup
before any image-rebuild step is the only action this skill may run, and
only behind the confirmation gate (M2).
