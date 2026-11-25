# Hand-off Rules

This skill answers one question: *how do I get a website or application
environment built and launched on my ECS instance.* It locates the deployment
target with read-only queries and walks the mainline. It does not diagnose
failures, judge commercial entitlements, or operate anything.

Everything else in the customer's wording is a **routing decision, not a task**.
Recognise it early: walking a build checklist at a customer whose real problem is
an access failure wastes their time and produces an unfounded conclusion.

> Skill names for the destinations below are given as capability descriptions,
> except where a name is confirmed. The neighbour-skill list for this batch was
> not supplied with this tier's requirements, so exact target identifiers must be
> aligned before quoting one to a customer. The single confirmed cross-reference
> is `alibabacloud-wxz-website-builder`, which covers the AI website-builder
> product rather than self-managed deployment on ECS.

---

## Routing table

| Customer says (symptom) | Why it leaves this skill | Route to | Sentence to use |
|---|---|---|---|
| "my site was working but now it cannot be opened", "the domain gives an error", "access is very slow" | The build already exists; the question is why access fails, which needs a layered check | unreachable / slow website, layered diagnosis | "Your site is already deployed, so this is an access-failure case rather than a build case. It needs the layered check - your machine and the address the domain resolves to, then the instance's security group, then the web service. Please use the unreachable-website diagnosis for it." |
| "the panel won't open", "wrong password on the panel", "the panel shows an error" | Panel-side state and panel credentials are outside the ECS read-only surface | control-panel operations and diagnostics | "That has to be located inside the control panel itself. Use the panel diagnosis flow; this guide only covers where panel site creation sits in the deployment mainline." |
| "Nginx/Apache/IIS won't start after my change", "PHP/Java/Python runtime error", "WordPress install fails", "Docker container error" | A configuration or runtime failure carrying its own error text is a diagnosis, not a walkthrough | web-server and runtime configuration | "That is a web-server or runtime configuration error. Send the exact error text and route it to the web-environment configuration flow; this guide does not debug service errors." |
| "ICP filing", "filing service code", "how many service codes does my purchase include", "filing was rejected" | Filing prerequisites and product entitlements are a separate flow, and non-ECS entitlements are not visible to an ECS read at all | ICP filing flow | "Filing resources and steps are handled by the filing flow. If the question is how many service codes a purchased product includes, check that product's own console entitlement page - the ECS side cannot see it." |
| "I can't connect", "SSH refused", "Remote Desktop fails" | Connection establishment has its own symptom axis; stage 1 presumes a session is possible | remote-connection diagnosis | "Stage 1 assumes a session can be opened. Since it cannot, this needs the remote-connection diagnosis first; come back to the deployment mainline once you are in." |
| "the upload fails", "file too large", "transfer times out" | Transfer failure and size-limit behaviour belong elsewhere | file transfer and upload limits | "The transfer itself is failing, which is a file-transfer case. Route it there; once the files land, stage 4 continues here." |
| "the database won't connect", "install MySQL", "database whitelist" | Database-side deployment and connectivity form their own tier | database deployment and connectivity | "Database installation and connectivity are handled by their own flow; this guide only records where the application's database name and credential get filled in, during stage 3." |
| "moving my existing site from another server / another cloud" | Migration has its own sequencing of data, environment and cut-over | whole-site migration | "This is a migration of an existing site, not a new build. Please use the migration flow so the data and cut-over steps are ordered correctly." |
| "SSL certificate", "HTTPS not trusted", "certificate chain" | Certificate lifecycle is a separate flow | SSL certificate application and deployment | "Certificate request and binding belong to the certificate flow. Finish the HTTP build here first, then bind the certificate there." |
| "I want a refund for the instance I was told to buy", "I was charged wrongly", "unsubscribe" | Commercial entitlements and refund eligibility are decided in the billing flow; this skill does not judge them and submits nothing | unsubscription, refund and billing | "Refund eligibility and unsubscription are commercial decisions made in the billing flow. I cannot judge them or file anything for you - I can only point you at the console entry. Let me hand this over." |
| "the AI website-builder product ..." | Different product, different surface | `alibabacloud-wxz-website-builder` | "That question is about the AI website-builder product rather than deploying a site yourself on ECS; use the website-builder product flow for it." |

---

## Staying inside the boundary

- **Recognise, then route.** Name the symptom, give the sentence, and stop. Do
  not run the deployment walkthrough "just in case".
- **Never acquire the missing capability.** If closing the case would require
  reading a panel, entering the instance, or changing a resource, the answer is
  the paste-back request in [customer-selfcheck.md](customer-selfcheck.md) or a
  hand-off - not an improvised command, and not a claim that something was
  checked.
- **No commercial or filing judgements.** Where a build question and an
  entitlement question arrive together (a customer told to buy another instance
  for filing reasons, for example), answer only the technical part - what the
  account actually holds in the queried region, from the read-only inventory -
  and route the entitlement and refund part with the sentences above.
- **Mixed cases.** Handle the build mainline only while the blocker is a build
  step. The moment the blocker is a failure symptom, hand that symptom off and
  say which stages remain open.
- **Degradation is not a hand-off.** A failed read (`[WARN|DEGRADE]`) is reported
  with the read's own error and re-run; do not dress a partial result up as an
  out-of-scope case.
