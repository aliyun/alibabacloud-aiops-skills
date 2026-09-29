# Cross-product lifecycle

Use this reference only when one request spans two or more of domain acquisition, ICP filing, DNS, and website building. Treat the lifecycle as resumable stages, not one transaction.

## Stage model

| Stage | Typical commands | Completion evidence |
|---|---|---|
| 1. Discover | `domain check`, `domain price`, `domain whois` | Availability and price source are explicit. |
| 2. Acquire | `domain buy` or `domain transfer-in` | Order accepted and tracked to its terminal state; browser opening alone is not acquisition. |
| 3. Verify and govern | `domain template`, `verification`, `contact`, locks | Required identity and policy state is returned by a readback. |
| 4. File | `domain icp ask`, `fill`, `status`, `info` | Filing status is explicit; page opening or data entry is not approval. |
| 5. Build | `domain wxz chat-start`, resume/generate, `preview` | A project and preview are available. |
| 6. Configure DNS and domain | `domain dns`, `domain wxz site --operation domain-bind`, `site --operation domain-cert` | Saved DNS, binding, and certificate states are independently read back. |
| 7. Publish | `domain wxz deploy --operation publish`, `deploy --operation status`, `site --operation online` | Deployment reaches a successful terminal state and the intended site state is verified. |
| 8. Operate | renewal, auto-renew, history, analytics, deployment history | The recurring control and its current state are reported. |

## Orchestration rules

1. Start from the earliest unmet stage. Do not repeat stages already evidenced as complete.
2. Ask only for the minimum identifier or choice that changes the next action. Reuse returned IDs; never guess them.
3. Freeze user-supplied identifiers across stages. Discovery can fill a missing identifier but cannot replace a domain, `bizId`, profile, payment route, or deployment channel already supplied by the user.
4. Separate confirmation boundaries. Domain purchase, renewal, DNS mutation, domain binding, publication, and deletion never share one blanket approval.
5. Stop at external waiting states and failed gates such as authentication, payment confirmation, filing review, DNS propagation, certificate issuance, failed preview, or asynchronous deployment. Return the status command and identifier needed to resume.
6. Re-read state before a destructive or delayed follow-up. A preview or quote is stale when the target, amount, configuration, or service state changes.
7. Preserve product semantics in the final answer. Examples: fixed-price marketplace transaction versus registration, filing submitted versus approved, DNS saved versus propagated, and deployment accepted versus live.

## Agent plan template

Use this compact structure before a multi-stage workflow:

```text
Goal: the user's intended domain and website outcome
Current stage: earliest stage with missing evidence
Next CLI command: exact aliyun domain leaf
Confirmation: none, browser handoff, or explicit high-risk confirmation
Resume evidence: returned ID and status command
Remaining stages: ordered list, without auto-executing them
```
