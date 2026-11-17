# Changing the public IP of an ECS instance

A fixed public IP that Alibaba Cloud assigned to an instance cannot be edited in place, and no
bandwidth change will ever change it. The only self-service route to a different public address
runs through EIP. Every step below is performed by the customer in the console; this skill reads
state and explains order, caveats and the closing check.

## Preconditions to verify first

Run the entry script with `--intent ip-swap`, which also queries EIP records, then confirm:

1. the instance's current bandwidth billing mode, fixed bandwidth or pay-by-traffic;
2. whether the public address is a fixed public IP or already an EIP;
3. whether the instance is a subscription or pay-as-you-go instance;
4. which region the instance is in, because the EIP console and the fee are region scoped.

If the address is already an EIP, skip to step 3; steps 1 and 2 are only needed to move a fixed
public IP onto the EIP track.

## The five steps

| # | Step | Console area | Reference |
| --- | --- | --- | --- |
| 1 | Convert the bandwidth billing mode from fixed bandwidth to pay-by-traffic | ECS, bandwidth change | [change-the-billing-method-for-network-usage-1](https://help.aliyun.com/zh/ecs/user-guide/change-the-billing-method-for-network-usage-1) |
| 2 | Convert the instance's fixed public IP into an EIP | ECS, public IP conversion | [document_detail/61290.html](https://help.aliyun.com/document_detail/61290.html) |
| 3 | Unbind that EIP from the instance | VPC, EIP list | [document_detail/65204.html](https://help.aliyun.com/document_detail/65204.html) |
| 4 | Apply for a new EIP | VPC, EIP list | [document_detail/65203.html](https://help.aliyun.com/document_detail/65203.html) |
| 5 | Bind the new EIP to the instance | VPC, EIP list | [document_detail/72125.html](https://help.aliyun.com/document_detail/72125.html) |

Keep the order. Applying for a new EIP before the old address has become an unbound EIP is the most
common way to end up with two addresses and no idea which one serves traffic.

## Three caveats to state before step 1

1. **The conversion does not go back.** An EIP cannot be turned back into a fixed public IP, so the
   instance stays on the EIP track afterwards.
2. **An EIP costs money on its own.** Beyond bandwidth, an EIP carries its own configuration fee,
   and that fee is set per region. Quote it only from the live pricing page for the customer's
   region, never from memory.
3. **The bandwidth refund may be zero.** Converting fixed bandwidth to pay-by-traffic prorates and
   returns the bandwidth portion automatically, but if the instance was bought at a discount the
   returned amount can be nothing, and moving back to fixed bandwidth later can cost more than the
   original purchase.

Say all three before the customer starts, not afterwards. In the ticket corpus, this concern is the
main source of disputes once the change is already done.

## Closing check, the step customers forget

The old EIP keeps existing, keeps being bound to nothing, and keeps billing until it is released in
the VPC console for that region. Release is a customer action in the console and this skill never
performs it.

Two facts worth stating precisely:

* While the old EIP is not released, a newly applied EIP will not be the old address. If the
  customer's real requirement is "a different IP", leaving the old EIP unreleased actually
  guarantees the new one differs.
* If the customer's requirement is "exactly this old address again", that is not achievable by
  applying for a new EIP; the old address can only be kept by keeping its EIP.

Re-run the entry script with `--with-eip` after each customer step and read the EIP records: the
old address should move from bound to unbound and then disappear, and the new address should show
`associated_instance_id` equal to the instance id. That is how the runbook closes with evidence
rather than with a screenshot.

## Workloads that make this risky

* Domains or records pointing at the old address: DNS, SPF, DKIM, callback allow-lists, partner IP
  allow-lists, licence bindings and hardcoded endpoints all need updating before the switch.
* Anything the customer cannot re-point quickly should be prepared while the old EIP is still
  bound, then switched.
* If the customer only wants a different address because a port or an IP is blocked, confirm that
  first: an address change does not lift a block on the service, and it does not fix a bandwidth
  ceiling.

## Handoff triggers

* The customer wants a refund of the difference created by the conversion → explain the rules and
  route to a commercial follow-up, per [bandwidth-billing-matrix.md](bandwidth-modify-guide__bandwidth-billing-matrix.md).
* The old address is already released and a specific past IP is demanded → not achievable; state
  it plainly rather than opening the path.
* The real symptom is packet loss rather than the address itself → see
  [handoff-matrix.md](bandwidth-modify-guide__handoff-matrix.md).
