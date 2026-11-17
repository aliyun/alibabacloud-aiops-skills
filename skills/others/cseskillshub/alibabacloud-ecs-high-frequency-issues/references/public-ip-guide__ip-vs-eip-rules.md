# Public IP and EIP rules

Knowledge behind `scripts/areas/public_ip_guide/public_ip_guide.py`. Every rule here is about the asset
itself: who owns the address, what type it is, how it can move, and what a change
costs in principle. Reachability of a service is a different area
(`references/public-ip-guide__handoff-map.md`).

## 1. Telling the two address types apart

| | Fixed public IP | Elastic IP Address (EIP) |
| --- | --- | --- |
| Ownership | part of the instance | independent resource in the account |
| Billed with | the instance and its bandwidth | its own configuration fee plus its own bandwidth |
| Renews | with the instance | on its own, on the EIP page |
| Survives instance release | no | yes, while it stays allocated |
| Across an account transfer | moves with the instance and keeps its address | not carried by the instance: unbind it first, and a pay-as-you-go EIP can be transferred on its own |
| Can move between instances | no | yes, within the same account and region |
| Visible inside the guest | as the interface address | no: it is a one-to-one NAT mapping of a private address |

From the queries: an `EipAddress` object carrying an `IpAddress` or an
`AllocationId` means EIP; a populated `PublicIpAddress.IpAddress` list with no EIP
means a fixed public IP; neither means the instance has no public address right
now. Report what came back, and never infer the type from the address range alone.

## 2. Changing a fixed public IP: the five steps

A fixed public IP cannot be swapped in place as a general operation: the console's
own Change Public IP entry only covers a stopped instance inside a short window
after creation, with the limits in section 4. The general supported route turns the
fixed address into an EIP and replaces that EIP. The customer performs every step in
the console.

| # | Step | Document |
| --- | --- | --- |
| 1 | Switch public bandwidth billing from fixed bandwidth to pay-by-traffic | https://help.aliyun.com/zh/ecs/user-guide/change-the-billing-method-for-network-usage-1 |
| 2 | Convert the instance's fixed public IP into an EIP | https://help.aliyun.com/document_detail/61290.html |
| 3 | Unbind (disassociate) that EIP | https://help.aliyun.com/document_detail/65204.html |
| 4 | Allocate a new EIP in the same region | https://help.aliyun.com/document_detail/65203.html |
| 5 | Bind the new EIP to the instance | https://help.aliyun.com/document_detail/72125.html |

Step 1 is the precondition that surprises customers most: while the instance is on
fixed bandwidth the address cannot be detached, so a request to change the address
without touching billing has no supported path. A recorded case asked exactly that
and ended with the customer doing the switch themselves.

Step 2 is a conversion, not a release. The fixed public IP and the EIP exclude each
other on one instance, and the fixed address gives way through the cloud-side
resource conversion `ConvertNatPublicIpToEip` - a one-way, irreversible type change.
Never describe this to a customer as "release the fixed IP": in Alibaba Cloud
semantics a release is terminal (the address goes back to the pool and the binding
is gone), so a customer who follows the word "release" literally gives the address
up instead of converting it. If the request is phrased as "the NIC must release the
fixed IP", correct it to "the fixed IP is converted into an EIP, one way".

If the address is already an EIP, steps 1 and 2 are skipped: unbind, allocate, bind.

## 3. The three notices that always accompany the path

1. **It does not go back.** An EIP cannot be turned back into a fixed public IP of
   the instance. The original address type is gone for good. There is no reverse
   operation at all: the only supported direction is `ConvertNatPublicIpToEip`
   (fixed public IP to EIP); no API and no console entry converts an EIP back. The
   only way to a fixed public IP again is to release the public address and
   allocate a new one, and that address differs.
2. **An EIP bills separately.** It adds its own configuration fee on top of the
   bandwidth fee. One overseas case recorded a daily configuration fee of 0.72 CNY
   for a small EIP: a case figure, not a quote, confirm the current price on the
   buy page.
3. **The billing switch moves money.** Moving from fixed bandwidth to
   pay-by-traffic refunds the remaining bandwidth at the discounted rate, so on a
   promotional purchase the refund can be 0, and switching back to fixed bandwidth
   later can cost more than the refund. A recorded case involving a promotional
   renewal price ended with the customer warned that the original campaign price
   could not be renewed after the change.

Never quote a computed refund, difference, or renewal price. The console conversion
and buy pages show the estimated fee before the customer confirms; that page is the
answer. A support engineer could not compute it for an account either.

## 4. Shortcuts that do not work

- Dropping bandwidth to 0 Mbps, confirming the address is released, then buying
  bandwidth back: a recorded case was handed the same address again.
- Rebooting, stopping and starting, or reinstalling the image: a fixed public IP
  stays with the instance.
- Treating the console's own "change public IP" entry as a general replacement for
  the EIP path: the entry exists - instance details > All Actions > Network and
  Security Group > Change Public IP - but it is narrow rather than absent. It needs
  the instance stopped in **standard** stop mode (an economical-stop instance releases
  its public IP, so there is nothing left to change), it is only offered inside a
  short window after the instance was created (6 hours in the current documentation)
  and at most 3 times per instance, the new address is assigned randomly by the
  system and cannot be chosen, and where the address must be kept the documentation
  recommends an EIP instead. State the stop precondition first: a customer on
  economical stop mode who tries it loses the address instead of changing it. Beyond
  that window the five-step EIP path is the route.
- Doing the path to fix an interception, a link problem, or a client that will not
  connect: see section 7.

## 5. Keeping the address unique, and the billing tail

- As long as the old EIP is still allocated to the account, a newly allocated EIP
  cannot be that same address. That is how the "will I really get a different IP"
  question is answered: release the old one last.
- An EIP that was unbound but never released keeps being billed. After the customer
  acts, query the region's EIPs and confirm the old allocation id is gone. This
  exact gap produced an unexpected charge in a recorded case, where the customer
  believed the guidance itself had created the cost.

Console entry for that check, parameterised by the customer's region rather than a
hardcoded one: `https://vpc.console.aliyun.com/eip/{region-id}/eips`.

## 6. More than one address on one instance

- One instance carries one public address by default: one fixed public IP, or one
  EIP associated with it. More public addresses mean more EIPs.
- Several EIPs on one instance go through secondary elastic network interfaces, one
  EIP per interface: https://help.aliyun.com/zh/ecs/user-guide/manage-eni.md
- Binding rules and limits: https://help.aliyun.com/zh/ecs/user-guide/associate-or-disassociate-an-eip.md
- Inside the operating system only private addresses appear; the EIP is a NAT
  mapping, so its absence from `ip addr` output is expected, not a fault.
- The security group must allow the port on the interface that carries the mapping:
  https://help.aliyun.com/zh/ecs/user-guide/5-minute-guide-to-security-groups-secure-and-precise-network-access-control.md
- Which connection method to use once several addresses exist:
  https://help.aliyun.com/zh/ecs/user-guide/connect-to-instance.md
- Where the address is not visible but the instance is unreachable, the usual root
  cause is inside the guest: several secondary private addresses configured on the
  interface without the matching static configuration or with an extra route. Cloud
  queries cannot see that. Ask the customer for the interface and route output and
  point at the secondary private IP documentation; changing guest configuration is
  not something this skill does.

## 7. Transfer, migration, re-imaging

- Instance transfer between enterprise accounts requires the same enterprise
  verification subject on both sides. Which subject an account carries is
  registration data, not an ECS field, so no query here can settle it; the customer
  checks it.
- A VPC-type instance does not carry its EIP across a transfer. Disassociate the
  EIP before the instance is transferred, then bind it again on the receiving side.
  Procedure:
  https://help.aliyun.com/zh/ecs/user-guide/how-to-cross-account-transfer-migration-ecs-instance
- A pay-as-you-go EIP can be transferred on its own, separately from any instance.
  So "the EIP cannot follow the machine" is not the same as "the address is lost":
  the EIP is a transferable asset in its own right.
- The fixed public IP that the system assigned travels with the instance: it is
  transferred together with the instance and keeps the same address. It cannot,
  however, be detached and given to a different instance.
- Transfer constraints recorded in a case, to re-check against the live document:
  the vSwitch and security group in one VPC, the destination vSwitch in the
  instance's zone, no cross-region transfer, and a destination account holding
  pay-as-you-go resources needing an available balance above 100 CNY. Case figures,
  not a quote.
- Different verification subject means rebuild, not transfer: share a custom image
  or migrate the host. The public address changes either way, so DNS and IP
  allowlists must be republished.
- Changing the image, the operating system, or the CPU architecture keeps a fixed
  public IP attached to the instance, but any address that must survive a move
  between instances needs an EIP.
- If keeping the address is the real goal, the answer is usually "convert to an EIP
  once, then move the EIP" with the cost notice in section 3 attached.

## 8. Released addresses and history

- Private addresses of a released instance are not retained anywhere queryable,
  including the audit trail.
- A released public address can be reclaimed inside 7 days by the customer, self
  service, without a support ticket: on the EIP page apply for that specific address,
  or call `AllocateEipAddressPro` with the address in the `IpAddress` parameter. The
  attempt fails as `OperationFailed.AllocateUnfamiliarIp` or
  `OperationDenied.IpBelongToOtherUser` once the window has passed or another account
  already holds the address, so a reclaim is never guaranteed even inside the 7 days.
  A fixed public IP of a classic-network instance has no reclaim path at all. State
  the window as the platform rule it is, together with the two failure conditions.
- Releasing an EIP stops its billing and returns it to the shared pool; the address
  is then no longer reserved for the account, so the 7-day reclaim path above is the
  only way back and only while nobody else holds it.
- Release protection does not override the automatic release cycle of every account
  type; some account types recycle resources on a shorter cycle than the standard
  overdue window. The lifecycle itself belongs to the expiry and arrears skill.
- A released address is handed to another customer, and somebody else's stale DNS
  record can then land on this account's address. That is not repaired by changing
  the address again: serve only the intended host name in the web server
  configuration, and do not use the address itself as the server name.

## 9. When changing the address is the wrong tool

Each of these appeared as a request to change the address, and in each recorded case
the change would have been ineffective, or worse than the problem:

- Domains resolving to this address with no relationship to it, including scanner
  traffic against other people's host names: the records are theirs, unreachable
  from here. The fix is host-name based serving, and the case record says explicitly
  that it does not affect filing and that changing the EIP is not recommended.
- Filing interception on port 443 while direct address access works: a recorded
  customer had already run the full irreversible conversion path before asking, with
  no effect.
- Handshake succeeds, data does not arrive: a path problem.
- One client tool fails while another path works: a client problem.
- Attack traffic and blackhole: a new address leaks again and does not stop it.
- Overdue or expiry release: a released address cannot be renewed back, which is the
  only thing this area adds.

Before offering section 2 to any of these, run the gate and hand off with the
exclusion evidence from the state block.

## 10. Close-out check

After the customer has acted, rerun the entry point with `--intent verify`, passing
the old EIP's `--allocation-id` and, when known, `--old-address`. The check answers
three things only: what the instance's address is now, whether the old allocation id
still resolves, and which EIPs in the region are allocated but unbound. Report the
values that came back; anything else stays unverified.
