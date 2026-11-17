# Customer-side probes: requesting the reading and recording where it came from

Cloud APIs describe the configured capacity and the aggregate counters. They cannot see inside the
operating system, and this skill is read-only: it executes nothing in the guest and has no channel to
do so. When a reading only exists inside the instance, the customer produces it. This page is about
asking for that reading once, and about never letting a customer-supplied number pass as a
cloud-collected one.

For which commands may be suggested at all, see
[guest-command-whitelist.md](network-quality-bandwidth__guest-command-whitelist.md). For reading a path table once it arrives,
see [mtr-interpretation.md](network-quality-bandwidth__mtr-interpretation.md).

## Ask for everything in one message

Asking piecemeal is what makes these cases loop: in the evidence set behind this skill, one ticket
asked twice for the same server-side test and still closed without it. Request the whole set at once.

For a latency or loss case, the one-shot request is:

1. the customer's own public IP as seen from their side;
2. the path from the customer to the instance public IP;
3. the path from the instance back to that customer public IP;
4. the wall clock time each test was run, to the minute.

For a bandwidth case, the one-shot request is:

1. the instance id and region, if not already known;
2. the incident window, to the minute, not "yesterday afternoon";
3. the transfer rate the customer actually observed, with its unit (Mbps, MB/s, KB/s);
4. whatever the real-time per-connection view showed while the rate was high, if they can capture it
   at that moment.

## Wording to send with a printed command

Keep it short and honest about who runs it:

> Please run this inside the instance and paste the complete output, together with the time you ran
> it: `<command>`. I cannot run it for you, because this diagnosis only reads cloud-side data and
> never executes anything on your server. It only measures and prints; it changes no setting and
> installs nothing. If the tool is not installed, tell me rather than installing it, and I will give
> you the graphical alternative.

Never imply that the skill already ran the command, and never present a printed command as something
scheduled to happen on the customer's behalf.

## Recording provenance in the report

Every number in the report carries its origin. Two origins only:

| Origin | How it is obtained | Confidence ceiling |
| --- | --- | --- |
| Cloud-collected | a query the script made, named by action, with the sampled time | high, when a documented rule agrees with it |
| Customer-supplied | output pasted back into the conversation | low, always, even when it looks conclusive |

Rules that follow from that table:

- a customer-supplied reading can support a hypothesis and can rule the cloud side in or out, but it
  cannot on its own make a conclusion high confidence;
- the report names the tool, the target, and the time for each pasted block, so a reader can tell
  which test produced which line;
- when the pasted output is the only evidence for the customer's local network or a carrier segment,
  say that the owner attribution is a hypothesis resting on customer-provided data;
- `report --pasted-output-file` masks anything that looks like a credential and truncates the excerpt,
  so a long paste does not push the cloud-side evidence out of the report.

## When the paste-back is unusable

| Problem | What to do |
| --- | --- |
| No timestamp | ask for the time it was run; without it the reading cannot be aligned with the cloud series, and it stays out of the evidence list |
| Truncated table, middle hops missing | say which rows are missing and what judgement they would have supported; do not infer them from the rows that arrived |
| A destination row that is missing entirely | the test did not complete; ask for a rerun with a stated round count rather than reading the last visible hop as the destination |
| Output of a tool that is not on the whitelist | do not treat it as this skill's evidence; record what the customer sent, and route it to the area that owns it |
| Credential material pasted alongside | advise once that it be changed outside the ticket, do not repeat it, and keep it out of the report |
| The customer reports the tool is absent | do not suggest installing it; give the graphical alternative or continue with cloud-side facts only |

## When the customer cannot or will not run the measurement

Symptoms: no shell access, the instance is hung, the tool is missing, or the customer declines. Then:

1. state which of these applies;
2. continue with everything the cloud side can still prove, because a missing in-instance reading
   must not become a dead end;
3. name the reading that is absent and the conclusion it would have supported;
4. report `STATUS: DEGRADED`, and cap the confidence of anything that needed that reading at low.
