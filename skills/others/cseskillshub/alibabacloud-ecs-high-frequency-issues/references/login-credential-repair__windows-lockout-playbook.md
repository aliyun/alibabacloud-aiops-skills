# Windows account lockout playbook (branches LC5 / LC6)

Applies when the remote-desktop or console session reports that the account is
locked for security reasons, or that the referenced account is locked and may
not be logged on. Nothing in this file is executed by the skill: every
state-changing line is a step the customer or a human engineer performs, after
the gates in `../SKILL.md`.

## 1. Explain the mechanism before touching anything

Say this, in this shape, because the customer's next question is always "but I
did not type the wrong password":

- Windows locks an account after a configured number of failed logon attempts.
  The lock is a working security feature, not a defect of the instance.
- The failed attempts do not have to come from the owner. If the remote-desktop
  port is open to the whole internet, automated guessing tools produce those
  attempts continuously, and they trip the same threshold.
- A restart clears the lock temporarily; it returns as soon as the guessing
  traffic resumes. Unlocking without closing the exposure is a repeating job,
  not a fix.
- The account may also simply be disabled rather than locked; those are
  different states and different steps, so check which one it is first.

## 2. Diagnostic order

1. Confirm the area: the session reaches a logon prompt or produces a lock
   message (see the boundary test in
   [login-credential-decision-tree.md](login-credential-repair__login-credential-decision-tree.md)).
   A port that never answers is not this playbook.
2. Confirm the OS family and instance state from the cloud reads the report
   already contains; a Stopped instance changes the order of operations.
3. Read the effective policy with the **query form** of the account command
   (no parameters) and the account-state query. These change nothing; see
   [guest-credential-checks.md](login-credential-repair__guest-credential-checks.md).
4. Distinguish locked from disabled: a locked account still reports as enabled
   but fails logon; a disabled account reports as not active.
5. Only then consider a write, and only as a human step with the risk
   statement in section 5.

## 3. Zero-write paths first

Two of the three routes below change no setting at all. Try them before any
policy write.

| Route | What it is | Status in the evidence |
| --- | --- | --- |
| Interactive sign-in through the console session manager | Sign in once with a valid credential; a successful interactive logon clears the failed-attempt counter | Reported as sufficient in this tier's evidence; no help document was located in the evidence for it |
| Wait out the lockout duration | If the policy has a lockout duration, the account unlocks by itself after that window | Read the duration with the query form before promising this |
| Change the lockout threshold to zero | `net accounts /lockoutthreshold:0` - **a policy write**, despite being quoted as "the unlock command" throughout this tier | Authoritative source and approved wording not found in the evidence |

**Un-reconciled guidance variants.** The evidence for this tier contains three
different instructions given to customers for the same symptom: clear the
lockout threshold, enable the built-in account (`net user <name> /active:yes`),
and "sign in once through the console session and the lock clears". They have
different semantics - policy write, account attribute write, interactive
unlock - and are not interchangeable. This playbook lists all three and marks
them un-reconciled; it does not silently pick one. If a single line has to be
recommended, recommend the interactive console sign-in, because it is the only
one of the three with no state change.

## 4. Guided Cloud Assistant steps (customer performs them)

The console route used across this tier, with the four stumbling blocks that
actually cost customers round trips. Read them out with the steps; they are the
majority of the back-and-forth.

1. Open the ECS console Cloud Assistant page **in the region that owns the
   instance**. If the instance cannot be selected in the list, the region
   selector in the top-left corner is almost always wrong.
2. Create / run the command and paste the content into the command box.
3. **Set the command type to Bat.** `net accounts` is a Windows command-prompt
   command. With the type left on Shell the Run button is greyed out or the
   command fails, and customers describe this as "the button is disabled".
4. Type the two instructions on **separate lines**, and note that the
   threshold argument needs a leading space: `net accounts /lockoutthreshold:0`
   and then `net accounts`. Written on one line, or without the space, the
   console reports a format error.
5. Wait for the run to finish, then reconnect.
6. Success criterion, stated in advance so the customer knows what to look
   for: the `net accounts` output reports the **lockout threshold as 0**.
   That is the read form of step 4, and it is also how the change is verified.
7. If Cloud Assistant itself cannot reach the instance, fall back to the
   console session: sign in, open a command prompt or PowerShell (Win+R, then
   `powershell`, or search for PowerShell in the Start menu), and run the same
   two lines there.

## 5. Risk statement that must accompany the threshold write

Print this with the step, not after it:

- Setting the lockout threshold to 0 removes the repeated-failure check
  entirely. While the remote-desktop port is reachable from the internet, the
  instance is then continuously guessable with no lockout protection at all.
- Snapshots first: this is a configuration change, so a manual snapshot that
  covers the **system disk** comes before it. Snapshots are billable; say so
  and give the billing page from [help-docs.md](login-credential-repair__help-docs.md).
- Tell-and-confirm: state what runs, that it changes a security policy, that
  it is reversible by setting the threshold back, and that it costs nothing by
  itself - then get a yes for this one step.
- Close the loop: after access is restored, set a sane threshold again (for
  example five failed attempts with a defined lockout duration) and move the
  source restriction in place, or the change is permanent exposure.

## 6. Root-cause hardening (manual console steps)

Unlocking treats the symptom. The only durable fixes are about exposure:

1. Restrict the remote-desktop port (default 3389) and the SSH port (default
   22) inbound to the customer's own public egress address. The customer can
   read their current egress address from any public "what is my IP" page;
   this skill does not maintain a list of such sites and does not read or edit
   security-group rules itself.
2. Or move the remote-desktop service to a non-default port so it is not
   scanned. Both the console guidance and the Windows-side steps are manual;
   a registry edit is a write and is never dispatched here.
3. Set a complex logon password: mixed case, digits and symbols. When the
   customer says (accurately) that their own address changes constantly and
   source restriction is impractical, say plainly that the remaining
   compensations are a strong password, a non-default port, and monitoring -
   and that the risk is theirs to accept. Do not present a one-time unlock as
   a fix.
4. Only open the ports the business needs.
5. Patch reported vulnerabilities, but take a snapshot before patching.
6. If a customer's own address range keeps moving, note the follow-up they
   will otherwise miss: each change of that address requires updating the rule,
   otherwise they lock themselves out of their own instance.

If the customer reports that a deny rule or an unusually high-priority rule
exists on the remote-desktop port, that is a plausible additional cause of
"locked out even after unlocking" - and it cannot be confirmed by this skill,
which never reads security-group rules. Say so and hand that part to the
security-group / network area.

## 7. What this playbook cannot do

- It cannot read the failed-attempt count or the source addresses. That data is
  only in the guest security log, and the in-guest command whitelist for this
  area is not approved. When asked directly for the attempt count, answer that
  the current flow cannot retrieve it, and name where it lives.
- It cannot unlock, enable an account, change a policy, edit a security group,
  restart the instance or restart a service.
- It does not reproduce "an engineer logged in and turned something off
  somewhere": undocumented manual changes are not something this skill can
  audit or imitate.
