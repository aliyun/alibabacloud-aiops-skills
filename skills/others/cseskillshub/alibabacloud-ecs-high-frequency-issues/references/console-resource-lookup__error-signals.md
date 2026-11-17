# Error signal cards

The tier spec provided no dedicated error-code table for this skill, so this
file contains ONLY the strings that literally appeared in the injected ticket
dialogs or ticket summaries (requirements doc section 6.3) -- nothing is
extended or invented. Machine-readable copy: `ERROR_CARDS` in
`scripts/areas/console_resource_lookup/_constants.py`; quote the script output (`--error <key>`).

Auth-failure wording rule for all reports: name refusals as `NoPermission` /
`ImplicitDeny` codes exactly as the API returns them; never paraphrase a
refusal with any other security vocabulary, and never react to a refusal by
widening a policy.

## Card 1 -- `The specified ImageId does not exist` (T-D3CF844C, dialog)

- Where it appears: during ECS order submission when the chosen image is not
  available for the selected region / instance type combination.
- What to do: switch to another image on the buy page and retry. The ticket
  customer got stuck because they could not find where to switch ("there is
  no place to change the image"): reload the purchase form, pick the image in
  the image section of the custom/basic buy tab, and if the page itself
  misbehaves capture the exact wording before routing onward (the customer
  in T-D3CF844C was transferred twice).
- Boundary: this skill explains and navigates; ordering is the customer's
  action.

## Card 2 -- `NoPermission.RAM` with authorized action + request id (T-1D79BB54, dialog)

- Observed authorized actions: `ecs:ListTagResources`, `ecs:DescribeInstances`
  (missing grants inside a third-party ecosystem platform's call chain).
- The three-part attribution, in order: (1) read the failing ACTION, (2) read
  the principal and (3) the account the REQUEST ID belongs to. Same-account
  RAM user lacking an ECS read grant: suggest the managed read-only access
  policy class and hand the actual policy work to
  `area:ram-policy-diagnosis`. Request id owned by a third-party
  ecosystem platform: Alibaba Cloud ECS support cannot act on it -- the
  customer submits on that platform's own ticket channel.
- Anti-pattern seen live: the agent first assumed the wrong authorization
  principal and was corrected by the customer ("does not the main account
  already have these permissions?"). Always attribute before prescribing.

## Card 3 -- unsubscription refused: switch to a public image first (T-C3D40EB0, summary)

- The customer reported the console refusing self-unsubscription of a
  subscription instance with a message to change to a public image; the exact
  on-screen wording is pending a dialog re-pull, so describe the rule, not a
  fake quote: subscription instances on non-public (custom or marketplace)
  images cannot self-unsubscribe directly.
- What to do: state the rule; navigate to the image-change entry; route the
  eligibility computation and the actual unsubscription to the human
  commercial channel (see the refund-page entry in
  [console-entry-map.md](console-resource-lookup__console-entry-map.md)).
- Also on file from the same ticket: screenshot upload via SMS failed; the
  reliable path is the ticket page's own upload or a remote-assistance
  request -- when guiding a customer through a blocked self-service form,
  prefer in-page channels.

## Card 4 -- "this account does not support the call"-style refusal (T-1D79BB54, agent rephrasing)

- Treat as a scoping signal, not a permission bug: check whose request id it
  is and which account issued it before touching any policy
  (same three-part method as Card 2).

## Symptom phrases that are NOT errors but behave like them

These come from the ticket corpus and deserve equal routing:

- "The instance list is empty" while the server is still running its workload
  -> almost always the region switcher or another account (see
  [visibility-triage.md](console-resource-lookup__visibility-triage.md)); sweep before believing "the
  server is lost".
- "The button is greyed out" -> often means "no pending console-side action"
  (the console step already completed, T-37463A4B) or a billing-mode gate
  (T-5E9C11A3), not a permissions fault.
- "The violation/disposal reminder still shows" after the appeal was
  approved -> display residue pending refresh; the queried instance status
  is the anchor (T-0ADBA324).
- "My snapshots disappeared" -> two independent mechanisms, check both:
  region view wrong, and overdue payment pausing auto-snapshot policies while
  auto snapshots expire on a short retention (T-C8FA71CA, T-D52AE555).
