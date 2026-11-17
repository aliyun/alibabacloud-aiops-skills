# M3 — Post-transfer verification checklist

A transfer moves the instance and nothing else. Most "after the transfer
something broke" tickets trace back to skipping this list, so deliver it
proactively at the end of every eligible-transfer conversation
(`scripts/axes/account_transfer_guide/transfer_guide.py --guide post-transfer` emits the same items).

## 1. Public IP and EIP

* Bound EIPs must be detached BEFORE the transfer (condition 4) and do not
  follow the instance automatically — after the transfer the instance's
  public address is different unless the EIP itself was transferred.
* EIP transfer is its own flow with its own limits: only **pay-as-you-go
  (post-paid) EIPs** qualify, and for an enterprise source the target
  account must be verified under an **identical enterprise entity**.
  Doc: `https://help.aliyun.com/zh/eip/transfer-pay-as-you-go-eip`
* Actions: bind a new EIP or accept the new IP, then immediately execute
  items 2-4 below.

## 2. Snapshots and images stay behind

"ECS transfer moves the instance itself only; snapshots under the source
account do NOT migrate with it — they remain in the source account"
(dialogue-verified). Find them: source account > ECS console >
**Storage & Snapshots > Snapshots**. If the new owner needs them, share
(images) or copy them BEFORE the transfer. When a customer reports
"snapshots disappeared", first confirm they are looking in the SOURCE
account at that exact page before anything else.

## 3. DNS records

Every domain record pointing at the old IP must be repointed to the new
one: Cloud DNS console `https://dns.console.aliyun.com/#/dns/domainList`,
how-to `https://help.aliyun.com/zh/dns/modify-a-dns-record`. Global
propagation takes **up to 48 hours** (support wording). Verify with the
worldwide probe `https://boce.aliyun.com/detect/dns`.

## 4. Third-party integrations keyed on the old IP

Licenses, partner whitelists, and any application that **hard-codes the
public IP** break the moment the IP changes (real ticket: a platform
authorization bound to the old IP failed after transfer). Inventory such
bindings before transferring; fixing them is customer-side development
work — this skill only produces the checklist evidence.

## 5. ICP filing (hedge)

Phone-record evidence states an already-filed domain usually needs only its
DNS repointed (no fresh ICP filing) when the IP changes. **Single-source,
never re-verified** — always add "confirm against the official ICP-filing
rules" and do not present it as certain.

## 6. Discount eligibility lost

Backend-verified wording: an instance that participated in a discount /
campaign purchase **cannot join discount campaigns again after being
transferred**. Say it before the customer starts, not after.

## 7. Ownership of bills moves

After a successful transfer the target account owns the instance and its
charges going forward. Account balances, resource packages, coupons and
invoices never move between accounts.

## Exit condition

Each item answered with either a checked fact (queried or customer-
confirmed) or an explicit "unverifiable from here — check in console page
X". Never mark an item as done without evidence, and never run any fix
yourself — items 1-4 are customer actions with the console entries given
above.
