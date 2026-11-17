# Appeal Materials, Channels and Timeliness

All lists below are standardized from real ticket practice in this tier —
what the reviewers actually asked for, in the order they asked. Submitting
the complete set in one round is the single biggest saving: tickets show
cases escalated or auto-closed precisely because materials arrived piecemeal.

## Universal precondition: principal authorization (branch of this tier)

An appeal is only actionable when it comes from the **verified real-name
subject of the account** — or a representative holding an authorization for
that subject. Materials naming a different entity than the account subject
are rejected without review. Before preparing any submission, confirm the
requester acts for the account principal; if not, route to the manual
channel rather than assembling a doomed package.

## The original notice is the anchor

Punishment records and content detail are NOT queryable through this skill
(privacy-restricted; no verified API). The console message / SMS / email the
customer received is the only authoritative carrier of: the punished object
(instance / URL / account / order), any release timestamp, any rectification
deadline, and the appeal entry it names. Step one of every appeal path: read
the notice text with the customer and extract these fields verbatim.

## Material checklists by disposal type

### 1. Content violation (instance-level stop or URL/site block)

- Detailed business description of the affected site or service
- Business license of the account's real-name subject
- ICP filing number of the domain (when the service is a website)
- Official website / service link
- The violating URL(s) as named in the notice (if disclosed)
- Screenshot proof the content was deleted or fixed (deletion evidence)
- Instance ID / public IP of the affected asset

Misconception to correct up front: complete qualifications (license, ICP
trademark, software copyright) do not prevent a content violation — the
sample hit is content-based; and "my server only stores game data" does not
help when an associated hosted site was tampered with and matched a fraud
sample.

### 2. Account-level freeze / risk-control restriction

- Account ID and the freeze notice text
- Business license of the real-name subject
- Legal-representative identity verification in the form the notice demands
- Business description and typical usage statement
- Authorization proof when a representative submits

### 3. Transaction risk control (order / payment / renewal intercepted)

- Photo of the account holder **holding** the ID card, portrait side visible
  (person-and-card verification; a student certificate or a plain ID
  screenshot is NOT an accepted substitute — state this BEFORE the customer
  submits, tickets show invalid-material tug-of-war otherwise)
- Registration information consistent with the certificate
- Order / RequestId reference when available
- Console interception wording, typically `ErrorCode: UnknownError` with a
  RequestId: record it; it identifies the review request, it is not a
  software bug

If the review declines, some verdicts are final ("admission criteria not
met"); the escalation path is a duty-manager call, not this skill.

### 4. Egress-port / mail area

Not collected here. Port 25 mail sending belongs to the adjacent
email-sending area (default-block policy, exception review handled off this
skill); supervisory tunnel blocks cannot be appealed through the cloud
platform at all. Hand off instead of collecting materials.

### 5. Judicial / regulatory / law-enforcement

No material is submitted through a support appeal: individuals file a
report with local police; law-enforcement bodies use the formal
cooperation channel with the compliance team. The cloud provider does not
provide third-party data to private parties and does not issue stamped
evidence letters. Use the fixed talk verbatim and run no queries.

## Channels: self-service vs manual

- Where the notice offers a self-service appeal entry, submit through it.
  Note: several disposal types are **not self-service** — account
  restrictions and non-reversible review types run through manual channels
  only, and some unblock requests require manual verification with the
  material set attached (asset ID, URLs, deletion proof).
- If the appeal link named in the notice is broken or unreachable, do not
  loop on it: open a manual support ticket and attach the original notice.
- The canonical current URLs of the self-service unblock platform and the
  unified appeal form are pending official verification for this skill;
  until confirmed, always point at the entry contained in the customer's
  own notice or at a support ticket — never a guessed or recalled link.

## Timeliness wording (ticket-confirmed practice)

- Specialist review runs in queue order: results **typically the same day,
  at the latest within 3 calendar days** after a complete submission,
  synchronized back through the console message / SMS channel.
- Expedite requests: effort can be forwarded, but no outcome and no queue
  jump can be guaranteed; say exactly that.
- Automatic release (attack-behavior freezes etc.): fixed timestamp,
  **cannot be advanced manually**; repeated "unblock now" tickets do not
  change it.
- Review outcome is never predictable from the cloud side: the platform
  decides; this skill only prepares a complete, correctly-authorized
  submission.

## Cost-reduction side-guidance (account freeze while instances bill)

When a frozen account blocks the console but pay-as-you-go instances keep
running, the customer may log in via SSH / Workbench / VNC and stop the
instances to reduce charges. Stopped pay-as-you-go instances can still
accrue CPU / memory / disk charges depending on the stop mode, so end the
guidance with "the actual bill is authoritative". Official procedure:
https://help.aliyun.com/zh/ecs/user-guide/stop-an-instance.md and
https://help.aliyun.com/zh/ecs/instance-management-and-operations-faqs.md.
The skill only quotes the guidance; the stop itself is a customer action
outside this skill.

## Closing evidence

After an approved unblock, re-run the read-only checks and show the
instance status back at Running — the same verification a human engineer
did manually in the source tickets, now reproducible.
