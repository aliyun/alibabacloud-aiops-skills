# Deployment Mainline - Building a Website on an ECS Instance

The walkthrough this skill emits, stage by stage. It exists so a customer who
has just bought an ECS instance can get from "empty server" to "my site answers
at my domain" without guessing what comes next.

Two rules govern every stage below:

1. **The customer performs the actions.** This skill only ran read-only queries.
   Before the walkthrough is relayed, state the disclaimer: *"The actions below
   are executed by you in the console, in your panel, or on the server itself;
   this skill only ran read-only queries and performed nothing on your
   behalf."*
2. **Each stage ends in an observable result.** Entry point, what to fill, what
   a normal result looks like, and what to do when it does not look like that -
   including when to stop and route the case to the flow that owns the symptom
   (see [handoff-rules.md](handoff-rules.md)).

Structure: **five build stages plus one verification loop.**

---

## Before stage 1 - confirm the target

Run the read-only inventory (`scripts/axes/website_build_guide/website_build_guide.py --region-id <region>`)
and confirm with the customer:

- which instance is the deployment target, when more than one is visible;
- that the instance is in state `Running`;
- whether it has a public address, since stage 5 needs one for a plain A record.

If nothing is visible in the region, that is **not** proof the account owns no
server: reads are per region and per account. Ask for the purchase region and
re-run there. If the instance is not `Running`, point the customer at the
console instance list to start it themselves; a state that will not change is a
status symptom and leaves this guide.

---

## Stage 1 - Connect to the server

| | |
|---|---|
| **Entry point** | ECS console -> Instances -> target instance -> *Connect* (opens a browser session), or a local SSH client to port 22 on the public address |
| **What the customer does** | Opens a session; if no login credential was set at purchase, sets one from the console first |
| **What to fill** | The instance's public address; the OS user name (`root` on most Linux images); the password, or the key pair chosen at purchase |
| **Expected result** | A shell prompt belonging to the instance - the hostname and `uname -a` output refer to that machine |
| **If it fails** | Connection refused, timeouts, or authentication failures are a *connectivity* symptom. Route to remote-connection diagnosis (see [handoff-rules.md](handoff-rules.md)) and do not continue the walkthrough on top of a machine nobody can reach |
| **Risk notice** | Setting a new login credential can require the customer to restart the instance on some images; say so before they use it, and tell them a restart interrupts anything already serving traffic |

Windows instances use Remote Desktop on port 3389 and the `Administrator`
account. See [Windows instances](#windows-instances) for the confidence caveat.

## Stage 2 - Prepare the web runtime

Choose exactly one flavour, and ask the customer which they want before
expanding this stage:

- **Control panel (BT / aaPanel and similar).** Fastest for non-technical
  customers; gives a one-click installer and a file manager. The panel's own
  software catalogue installs the web server, the language runtime and the
  database.
- **Manual stack.** Nginx or Apache plus the runtime the application needs
  (PHP, a Java servlet container, a Python or Node application server).
- **Marketplace or custom image** that already ships the stack. Custom images
  that carry a prepared environment are described in the ECS documentation:
  <https://help.aliyun.com/zh/ecs/user-guide/share-a-custom-image.md> (link
  taken from the injected evidence for this tier; re-verify before quoting it to
  a customer).
- **Container runtime**, when the application is delivered as an image.

| | |
|---|---|
| **Entry point** | The connected session, or the panel's software installer |
| **What the customer does** | Installs the web server and the language runtime the application package requires |
| **What to fill** | The version the application asks for, the install path, and the document-root path the installer picks - write it down, stage 3 and 4 both need it |
| **Expected result** | The service reports running, and requesting the machine's own address returns the vendor's default page |
| **If it fails** | An install that completes but throws configuration or start-up errors is a *web-server / runtime* symptom -> hand off. A panel that will not open, or a panel error message, is a *panel* symptom -> hand off |
| **Risk notice** | Installing a stack over an existing one can rewrite that stack's configuration. Ask the customer to confirm the machine is not already serving another site before proceeding |

## Stage 3 - Create the site and its root directory

| | |
|---|---|
| **Entry point** | Panel -> Website -> Add site; or the web server's site/vhost configuration plus its document root |
| **What the customer does** | Creates the site entry bound to the domain and records the root directory it writes into |
| **What to fill** | Domain name, root directory path, runtime version, and - if the application needs one - a database name and its credential |
| **Expected result** | The domain appears in the panel's site list (or the vhost exists) with a visible root path |
| **If it fails** | Whether the entry exists is invisible to the cloud side: ask the customer for the paste-back in [customer-selfcheck.md](customer-selfcheck.md). Never assert "you have no site created" without their evidence |
| **Risk notice** | Pointing an existing site's root at a new directory hides the old site immediately. Record the previous root path before changing it so the customer can put it back |

## Stage 4 - Upload the website files

| | |
|---|---|
| **Entry point** | Panel file manager, an SFTP/FTP client, or `git` inside the session |
| **What the customer does** | Places the application package into the root directory from stage 3 and unpacks it there |
| **What to fill** | Local package path, remote root directory, and readable permissions for the web-server user |
| **Expected result** | The root directory holds the application's entry file (`index.php`, `index.html`, `WEB-INF`, depending on the stack) |
| **If it fails** | A transfer that fails, truncates, or hits a size limit is a *file-transfer* symptom -> hand off rather than retrying blind |
| **Risk notice** | Uploading onto a populated directory can overwrite a live site. Back the current contents up first, and confirm the target path twice - a mistyped path leaves the site empty and looks like a server fault |

## Stage 5 - Point the domain at the server

| | |
|---|---|
| **Entry point** | The DNS console for the domain: add or edit resolution records |
| **What the customer does** | Creates an `A` record for the domain and the bare domain pointing at the instance's public address, then waits for propagation |
| **What to fill** | Type `A`; host record `@` and `www`; the public address from the inventory; default TTL |
| **Expected result** | The record list shows the `A` record with the intended address in an enabled state |
| **If it fails** | Records that do not take effect for the customer's browser are a *resolution* symptom -> hand off. Mainland-China endpoints may additionally require filing, which is its own flow -> hand off, and never judge filing eligibility here |
| **Risk notice** | Editing a record that already carries traffic can take a live site offline. Note the previous value before changing it |

**Common misunderstanding to correct here:** "resolved" and "deployed" are not
the same thing. A domain that resolves to the server still shows nothing if
stages 3 and 4 have not been completed on that server. Buying the instance does
not publish a site by itself.

## Verification loop - confirm, then re-check read-only

| | |
|---|---|
| **Entry point** | The customer's own browser, plus a re-run of the entry script |
| **What the customer does** | Opens the domain and reports verbatim what appears - the page, or the exact error text and HTTP status from the browser's network tab |
| **What the skill re-reads** | `DescribeInstances` + `DescribeInstanceStatus`, to confirm the target and its bound security groups are unchanged |
| **Expected result** | The application's own page |
| **If it fails** | Anything other than a working page after all five build stages is an *access failure*, and this skill stops: route to the layered unreachable-site diagnosis. Continuing to guess here produces the wrong kind of answer |
| **Closure rule** | Only the customer's pasted result can close the loop. Without it, output a staged conclusion plus the outstanding paste-back items and state that the final result depends on their verification. Never report "solved" or "site is live" on cloud-side evidence alone |

---

## Windows instances

The representative tickets for this tier were all Linux or panel-based, so the
Windows equivalents (Remote Desktop, IIS site binding, Windows-specific runtime
installation) are **not covered by verified evidence here**. Treat any Windows
walkthrough as low confidence: keep stages 3 through 6 conceptually the same, state
plainly that the IIS path is not verified by this skill's sources, and prefer
routing to the flow that owns web-server configuration rather than improvising
commands.

## Documentation links

Only one link is carried by the injected evidence for this tier, the custom
image document quoted in stage 2, and it should be re-verified before being sent
to a customer. The following topics appear in the tickets but have **no verified
URL in this package** - supply and check them before quoting any link, rather
than reciting one from memory:

- ECS remote-connection methods (browser session, SSH, VNC)
- domain resolution records and propagation
- website file upload methods (panel, SFTP/FTP, git)
- control-panel site creation and root-directory settings (panel vendor docs)
- filing service codes and product filing entitlements
