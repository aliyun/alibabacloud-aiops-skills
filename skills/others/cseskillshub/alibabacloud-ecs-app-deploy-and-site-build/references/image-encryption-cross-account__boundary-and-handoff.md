# Boundary and hand-off decisions

The skill answers one symptom axis: **an image that carries encryption, and what
breaks when that image is shared, copied or used across Alibaba Cloud accounts.**
Confirm the axis with the read-only evidence, not with the customer's wording:
customers say "the image is gone" for six different problems.

Route on the object first: is the thing in question an image, a snapshot, a disk,
a key, or an instance? Then on the encryption attribute, which only the report
can establish (`encryption=encrypted` / `not encrypted` / `unknown` from
`DescribeImages`). Hand off as soon as either test fails; a hand-off with the
reason is a complete answer, a diagnosis of another skill's symptom is not.

| Adjacent symptom | Hand it to | Trigger you can actually observe |
| --- | --- | --- |
| Unencrypted image shared, copied across regions, or moved through OSS | the cross-account / cross-region image skill for unencrypted images | Report shows `encryption=not encrypted` on every matched image |
| Image build stuck, image build failed, image size limits, an image that will not select at purchase time | the custom image lifecycle skill | `Status=CreateFailed`, or the report shows no encryption element in the failure context |
| Image cost, snapshot cost of copies, removing old images | the image billing and clean-up skill | The ask is money or space, not access or an error |
| Switching the operating system of a running instance | the change-operating-system skill | The customer wants an existing instance re-imaged; that is a mutating flow this skill never performs |
| Encrypted **disks** and KMS key lifecycle, key cost, key rotation | the disk encryption and KMS skill | The object of the complaint is a disk or a key, not an image |
| A RAM sub-account missing policies for unrelated actions | the RAM and permission-policy skill | `NoPermission` / `ImplicitDeny` on an action that is not one of the three in `ram-policies.md` |
| Anything that needs data from inside the operating system | the Cloud Assistant / remote connection skill | The next fact needed is a guest-side reading; ask the customer to run a read-only command and paste it, per `customer-selfcheck.md` section C |

The neighbour names above describe symptom domains, not registered skill
identifiers: the authoritative tier list for this batch was not available when
this package was written, so match on the symptom, and if no skill covers it, say
so and leave the case with a human.

## Hand-off phrasing

Use the customer's own object and the observed fact, then state the limit plainly.

* "The image you pointed at has no encrypted snapshot attached, so the
  cross-account encryption limits do not apply to it. Your region-to-region
  question is handled by the image copy flow, which I am not able to advise on
  here."
* "The next fact needed is on the receiving account. My queries run under your
  own account only, so I cannot see their side; follow the checklist in
  `customer-selfcheck.md` section A and send me the screenshot."
* "This needs an actual change to the share or the image. I am read-only by
  design: I will tell you exactly which console page and which field, and you
  perform it, then I re-check the result with the same queries."
* "The instance itself has to be inspected from inside the operating system. I do
  not run commands inside instances; run this read-only command and paste the
  output, or take the case to the remote-connection flow."

## What is never in scope, whatever the customer asks

* Running a mutating operation on the customer's behalf, or producing a command
  line for the customer to run that changes a resource. The console steps in
  `guide-steps.md` are guidance only.
* Asserting a limit that the cited documentation does not state. If
  `image-encryption-basis.md` section J covers the question, the answer is "not
  established by the cited documents", plus the self-check item that would settle
  it.
* Inferring an error code from a symptom. Quote a code only when the report or
  the customer's own message contains it.
* Reading the peer account by asking for its credentials. There is no path for
  that here, and none should be improvised.
