# Evidence gaps: what this skill deliberately does not assert

Every item below was either contradicted inside the ticket corpus, missing from it, or unverified
against the interface documentation. The skill's discipline is to record the gap and fall back to
the human question, rather than to fill it from a model's memory. Anything on this page is a to-do
for a later revision, not a licence to guess today.

## 1. Bandwidth utilisation, the reading customers actually need

The tier's verified query surface contains no bandwidth-utilisation metric. Whether a peak reached
the configured ceiling is therefore never printed by the script; the answer asks the customer for
the console bandwidth monitoring chart, or for their own business-side counter over the same window,
and the run is marked `DEGRADED` when that figure is what the decision rests on.

A monitoring metric was considered for this purpose and is **not** wired in, because the injected
evidence never confirmed its request parameters (namespace, metric name and dimensions for public
bandwidth) against the interface. Two related warnings for whoever adds it later:

* the metric's authorisation name does not follow the shape of its API name, so it must be looked up
  rather than derived;
* adding a call means updating four places at once, listed in [ram-policies.md](ram-policies.md).

## 2. Temporary upgrade duration and frequency

The corpus gives two different minimum durations for a temporary bandwidth upgrade and no
corroborated figure for how often one may be applied. Nothing is asserted here. The correct answer
in a live case is the official temporary-upgrade page plus the selector shown on the customer's own
change page, quoted as what that page currently says.

## 3. The bandwidth floor on a downgrade

One ticket summary reports a minimum bandwidth restriction when reducing bandwidth, while another
customer in the same corpus targeted zero. Unresolved, so the guidance is only "read the value the
page enforces".

## 4. Money

No amount is ever stated: refunds, price differences, per-region EIP configuration fees, renewal
totals. The corpus itself shows agents falling back to the console preview and to commercial
follow-up, so the skill matches that and does not pretend to be better. A per-day EIP figure that
appeared in one conversation is an anecdote about one region at one moment and must not be repeated
as a rate.

## 5. Error codes and customer-visible error strings

The tier supplied no error code list for this problem area, and none was verified against the
interface documentation during development. Consequently this skill quotes no invented error code.
The only literals it uses are the two authorisation outcomes a customer genuinely sees when a RAM
identity lacks a query action, `NoPermission` and `ImplicitDeny`. A later revision should build the
real catalogue from the console and the API reference; until then, a case that hinges on an
unrecognised error string is escalated with the exact text rather than reinterpreted.

## 6. Handoff target names

The skill names in [handoff-matrix.md](bandwidth-modify-guide__handoff-matrix.md) were carried over from the batch template
and not checked against the live registry. Until they are, a handoff states the area the problem
belongs to and escalates a ticket, instead of telling the customer to invoke something that may not
exist.

## 7. Response field names

The script reads only fields that are present in the response, and prints the values it finds, so a
renamed or absent field degrades instead of being invented. The bandwidth, address and charge fields
this tier relies on are the documented names of the two describe calls; if a future revision adds
fields, they need the same care.

## 8. Dialogue coverage behind the analysis

Most of the representative tickets behind this skill were analysed from their summaries only,
because their conversations could not be retrieved, and a couple more contain nothing but a call
log entry. Conclusions that rest solely on a summary are the ones most likely to be wrong in
detail: the duration and frequency items above are exactly that class of claim, which is why they
are gaps rather than guidance.

## 9. Documentation still missing from the corpus

Pages a complete answer would want, for which no verified URL exists: the shared traffic package,
the data-transfer billing explanation behind pay-by-traffic charges, the downgrade refund rules, and
the per-region EIP pricing page. Each is referenced conceptually in the guidance and pointed at the
console or commercial channel rather than at a guessed URL.

## 10. Deliberately unused capability

`DescribeInvocations` was available and verified for this tier but is not called, because this tier
sends no in-instance command: bandwidth and traffic are cloud-side facts, so there is nothing for a
guest-side probe to add. Keeping it out means the policy in [ram-policies.md](ram-policies.md)
matches the calls that really happen. An earlier draft of the design listed it as the entry point
for in-instance measurement; that path stays closed unless a future revision re-opens the decision
about running commands inside the customer's instance.
