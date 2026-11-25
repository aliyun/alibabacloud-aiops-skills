# Customer Self-Check Templates

Most of the facts needed to finish a website build are **not** on the cloud side.
A control panel's site list, the contents of a document root, whether a web
service is listening, what a domain resolves to on the customer's own machine,
what the browser finally shows - none of these can be reached by the two
read-only ECS queries this skill is allowed to make.

So they are asked for. Each block below is a paste-back request the skill issues
verbatim. **The customer runs the commands, on their own server, themselves.
This skill never executes anything on an instance and never calls a write or
execution API.**

Use the cloud-side reads first ([precheck-queries.md](precheck-queries.md)) so
the questions are grounded: "on the Running instance `i-...` in `cn-...`, please
check ..." is a different request from a bare command list.

---

## 1. Does the panel already list a site for this domain?

**Ask:** In the control panel, open Website -> site list, and send the list of
domain names with the root directory shown beside each (a screenshot is fine).

**Why it matters:** "the domain resolves to the server but shows nothing" is most
often "no site entry exists for that domain yet". This is the single most common
root cause in this tier, and it is exactly the kind of fact the cloud side cannot
see - so it must be collected, not assumed.

**Reading the answer:** the domain is absent -> stage 3 has not run. Present with
a different root than stage 4 used -> the files and the site entry disagree.

## 2. Is the application code actually in the site root?

**Ask:** run these read-only commands in your own session and paste the output:

```bash
ls -la <site-root-directory>
df -h
```

**Why it matters:** separates "never uploaded" from "uploaded to the wrong path"
from "the disk is full so the upload silently truncated". Both commands only
report state; neither changes anything.

**Reading the answer:** no entry file present -> back to stage 4. Files present but
owned by a user the web service cannot read -> permissions. `df -h` at 100 % on
the data mount -> capacity, which leaves this guide as its own symptom.

## 3. Is the web service running and listening?

**Ask:** paste the output of these read-only commands:

```bash
systemctl status nginx      # or httpd, or the panel's own service name
ss -lntp
```

**Why it matters:** nothing is reachable until a process is actually bound to
port 80/443. `ss -lntp` shows the bind, and `systemctl status` shows whether the
service is active and why it failed to start.

**Reading the answer:** no listener on 80/443 -> stage 2 is incomplete. Listening
only on `127.0.0.1` -> the service is bound to loopback, a configuration matter
that leaves this guide. Errors in the status output -> web-server configuration
flow.

## 4. What does the domain resolve to on the customer's machine?

**Ask:** run a read-only lookup locally and paste the result:

```bash
nslookup <domain>       # or: dig +short <domain>
```

**Why it matters:** the public DNS view and the customer's own view routinely
disagree, and this skill performs no network probing at all - no HTTP request to
their site, no DNS query, no port test. The customer's output is the only
evidence available.

**Reading the answer:** an address that is not the instance's public address ->
stage 5's record is wrong or points at an old machine. The right address but no
page -> this stops being a build case and becomes an access-failure case
([handoff-rules.md](handoff-rules.md)).

## 5. What exactly does the browser show?

**Ask:** open the URL and report the visible result verbatim - the page itself,
or the exact error text and the HTTP status from the browser's network tab, plus
the time of the test.

**Why it matters:** this is the only evidence that closes the loop. Everything
else proves prerequisites, not success.

**Reading the answer:** the application's own page -> done, and say what was
verified. A connection problem, a timeout, or a server-generated error -> the
deployment prerequisites were met and the remaining problem is an access
failure: hand off with the collected evidence attached.

---

## Rules for issuing these

1. **Ask, do not assert.** Never write "you have not created the site" before the
   customer's evidence says so; write "please check whether ...".
2. **Read-only commands only, executed by the customer.** Nothing in this file
   changes a file, a service or a configuration; do not add commands that do.
3. **One batch, clearly numbered.** Ask for everything outstanding at once so the
   customer is not drip-fed, and echo which instance and region the questions are
   about.
4. **Absence of answers caps the conclusion.** If the customer does not paste
   back, report the cloud-side facts, list the outstanding items as a to-do, and
   state plainly that whether the site is live depends on their verification.
   The skill's `STATUS` may be `OK` while the *case* remains unclosed - those are
   different things, and the answer must not blur them.
