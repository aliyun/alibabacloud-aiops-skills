# Help-center references used by this skill

Provenance discipline for this page: every link below was present in the
evidence injected for this tier - either a help-search hit or a URL that support
engineers actually sent to customers in tickets of this tier. English titles are
renderings of the cited page subject; the live page title is localized, so
confirm the title before quoting it to a customer. Nothing was added from
recall, and where the title or the exact path could not be confirmed from the
evidence it is marked `TODO`.

## 1. Primary references (use these first)

| Link | Subject (English rendering) | Used for | Evidence provenance |
| --- | --- | --- | --- |
| `https://help.aliyun.com/zh/ecs/user-guide/instance-logon-credential-management.md` | Instance logon credential management | The authoritative answer to "where can I see my password": it cannot be viewed, only reset; default usernames; reset methods | Help-search hit for the credential topic **and** a page support sent in this tier |
| `https://help.aliyun.com/zh/ecs/user-guide/instance-logon-credential-management#9eeaf0e7062fc` | Same page, section anchor | The credential-consultation answer specifically | Anchored variant cited by support in this tier |
| `https://help.aliyun.com/zh/ecs/user-guide/reset-the-logon-password-of-an-instance` | Reset the instance logon password | Online versus offline reset, restart requirement | Help-search hit; support cited an anchored form of this page (`#3a870eb960qkd`) |
| `https://help.aliyun.com/zh/ecs/user-guide/connect-to-instance.md` | Choose a connection method | Deciding between Workbench, session manager, RDP and SSH when verifying a credential | Help-search hit for the connection topic |
| `https://help.aliyun.com/zh/ecs/user-guide/workbench-overview.md` | Workbench overview | What the Workbench channel can and cannot do | Help-search hit |
| `https://help.aliyun.com/zh/ecs/user-guide/connect-to-a-linux-instance-by-using-a-password-or-key.md` | Sign in to a Linux instance with a password or a key | The two Linux logon modes behind most branch-① confusions | Help-search hit for the key-pair topic |
| `https://help.aliyun.com/zh/ecs/user-guide/workbench-password-free-login-principle-temporary-ssh-key-pair.md` | Passwordless logon principle: temporary SSH key pair | Why "the key pair has been removed" and passwordless-logon failures happen | Help-search hit |
| `https://help.aliyun.com/zh/ecs/user-guide/connect-to-an-instance-by-using-session-manager-2.md` | Connect by session manager | Alternative entry when the agent path or RDP is unusable | Help-search hit |
| `https://help.aliyun.com/zh/ecs/user-guide/overview-52.md` | Instance overview: configuration and lifecycle states | What `Running` / `Stopped` mean for the reset path | Help-search hit |

Lockout explanation, the most-quoted customer-facing page in this tier:

| Link | Subject | Note |
| --- | --- | --- |
| `https://help.aliyun.com/zh/ecs/user-guide/for-safety-consideration-have-lock-the-user-account-the-reason-is-that-login-attempt-or-password-change-try-too-much` | Account locked for security reasons after too many logon or password-change attempts | Cited by support in many lockout cases of this tier |
| `https://help.aliyun.com/zh/ecs/for-safety-consideration-have-lock-the-user-account-the-reason-is-that-login-attempt-or-password-change-try-too-much` | Same subject, different path | **`TODO`: the evidence contains both path spellings (with and without `user-guide/`). Verify which one is live before quoting; do not send both.** |
| `https://help.aliyun.com/zh/ecs/support/modify-the-remote-desktop-port-of-a-windows-instance` | Change the remote-desktop port of a Windows instance | Hardening advice, manual steps |
| `https://help.aliyun.com/zh/ecs/user-guide/modify-the-default-port-used-by-an-instance-to-accept-connections` | Change the default port an instance uses to accept connections | Hardening advice, manual steps |

Snapshot-first rule, which this skill treats as mandatory before any write:

| Link | Subject | Used for |
| --- | --- | --- |
| `https://help.aliyun.com/zh/ecs/user-guide/create-a-snapshot` | Create a snapshot | The authority for "snapshot first, covering the system disk" |
| `https://help.aliyun.com/zh/ecs/product-overview/snapshots-1` | Snapshots: concept and billing | The answer to "does a snapshot cost money, and how much" |

## 2. Numeric-id pages cited by support in this tier

These URLs appear in ticket conversations of this tier, but the page titles were
not part of the evidence. Keep them as candidate references, resolve the title
before recommending them, and prefer the slug-form pages above when both cover
the same subject.

| Link | What support used it for | Status |
| --- | ---| --- |
| `https://help.aliyun.com/document_detail/25455.html` | Why an account is locked, and what to do | `TODO` confirm title and that the id still resolves |
| `https://help.aliyun.com/document_detail/56159.html` | Paired with the page above in lockout replies | `TODO` confirm title and content |
| `https://help.aliyun.com/document_detail/128131.html` | Security hardening advice | `TODO` confirm title |
| `https://help.aliyun.com/document_detail/25471.html` | Security-group rule background | `TODO` confirm title |
| `https://help.aliyun.com/document_detail/108451.html` | Paired with the page above | `TODO` confirm title |
| `https://help.aliyun.com/knowledge_list/60787.html` | Collection of further hardening suggestions | `TODO` confirm title; optional, only for the hardening section |

## 3. Entry-level pages (weakly related, use only as an on-ramp)

For brand-new or trial customers whose real problem is "I never set or record a
password and cannot find the console entry". Answer the credential slice from
section 1 and stop there.

- `https://help.aliyun.com/zh/ecs/user-guide/common-operations-for-the-ecs-free-trial.md`
  - free-trial common operations
- `https://help.aliyun.com/zh/ecs/user-guide/create-a-subscription-instance-on-the-quick-launch-tab.md`
  - quick-launch purchase, where the credential is set at purchase time
- `https://help.aliyun.com/zh/ecs/user-guide/quickly-purchase-a-windows-instance-and-build-an-iis-service.md`
  - new Windows instance walkthrough
- `https://help.aliyun.com/zh/ecs/user-guide/use-the-ecs-instance-in-the-console.md`
  and `https://help.aliyun.com/zh/ecs/user-guide/create-an-instance-by-using-the-wizard.md`
  - credential choice at creation time
- `https://help.aliyun.com/zh/ecs/user-guide/customize-the-initialization-configuration-for-an-instance.md`
  - initialization data; only relevant if an initialization script changed the
    account or password, which no case in this tier's evidence demonstrated

Excluded as noise: the launch-template purchase page surfaced in one help-search
query is unrelated to logon credentials and is deliberately not part of this
skill's references.

## 4. Handoff-only pages (quote these when leaving scope, never as a fix here)

- `https://help.aliyun.com/zh/ecs/user-guide/resize-linux-cloud-disks` - disk
  expansion, for the "reset fails because the disk is full" handoff.
- `https://help.aliyun.com/zh/ecs/user-guide/re-initialize-a-system-disk` -
  re-initialising a system disk. This is a destructive action that belongs to
  the security incident or recovery process; the evidence for this tier shows it
  being recommended after ransomware damage. This skill never recommends it as
  part of a credential repair.

## 5. Deliberately excluded

One ticket in this tier's evidence shows a support engineer sending a
**firewall-management page for a different product line** (a lightweight
application-server firewall guide) to a customer of an ECS Windows instance. The
product was misaligned. That link is excluded on purpose: do not add it back,
and do not reuse its wording for an ECS instance. Where remote-desktop port
changes are needed, use the ECS pages in section 1.

## 6. Topics where the evidence located no official page

These are the claims this skill has to make without a citation. Each is printed
with the confidence label the report contract requires, and none of them may be
upgraded into a documented statement:

1. **The lockout-threshold change itself.** The command used throughout this
   tier has no authoritative page in the evidence - only explanation pages for
   *why* an account gets locked. Approved wording for the command and its risk
   statement is an open point.
2. **The interactive-sign-in-clears-the-lock route.** Known from tickets, not
   from a page.
3. **RDP username polluted with the local computer name, and clearing
   remembered credentials.** A real and repeated fix, with no documentation
   behind it in the evidence.
4. **Workbench remembering old credentials, and how to start a new session or
   switch instance.** Same situation.
5. **Snapshot rollback rolling the logon password back with the disk.** One
   ticket summary, no dialogue and no page: operational note at low confidence.
6. **Default logon user per image family** (root versus `ecs-user` versus
   `cloud-user`). Support answered from experience. `TODO`: confirm whether the
   credential-management page in section 1 covers per-image defaults, and link
   an image page if it does not.
7. **Whether console key-pair binding remains unavailable for Windows images.**
   A negative capability statement from a ticket answer, with no page. Verify
   before asserting it.
