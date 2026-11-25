"""Constants and embedded guidance data for the website build guide skill.

Everything the skill knows is declared here or in ``references/`` -- the
``scripts/`` directory must stay free of standalone data files, so the
deployment mainline, the customer self-check templates and the hand-off
routing table are carried as module-level constants.
"""

SKILL_NAME = "alibabacloud-ecs-website-build-guide"

# --- Cloud API surface (read-only, verified for this tier) -------------------
ECS_PRODUCT = "ecs"
ECS_API_VERSION = "2014-05-26"
STS_PRODUCT = "sts"
STS_API_VERSION = "2015-04-01"

ACTION_DESCRIBE_INSTANCES = "DescribeInstances"
ACTION_DESCRIBE_INSTANCE_STATUS = "DescribeInstanceStatus"

# Plugin-mode CLI form (lowercase-hyphenated) used for the identity pre-check.
STS_CALLER_IDENTITY_CMD = ["sts", "GetCallerIdentity"]

# --- Runtime limits ---------------------------------------------------------
DEFAULT_TIMEOUT = 60
CONNECT_TIMEOUT_NOTE = "each CLI invocation is bounded by DEFAULT_TIMEOUT"
MAX_ATTEMPTS = 3
BACKOFF_BASE_SECONDS = 2
PAGE_SIZE = 50
MAX_PAGES = 20

RETRYABLE_CODES = (
    "Throttling",
    "Throttling.User",
    "ServiceUnavailable",
    "InternalError",
    "RequestTimeout",
)

# --- Report contract -------------------------------------------------------
STATUS_OK = "OK"
STATUS_DEGRADED = "DEGRADED"
STATUS_FAIL = "FAIL"

WARN_PREFIX = "[WARN]"
DEGRADE_PREFIX = "[WARN|DEGRADE]"

DISCLAIMER = (
    "The actions below are executed by you in the console, in your panel, or on "
    "the server yourself. This skill only ran read-only queries and performed "
    "nothing on your behalf."
)

# --- Deployment mainline (five segments) -----------------------------------
# Each stage: entry point, what the customer does, what to fill, expected
# result, failure fallback, hand-off target, risk note.
MAINLINE_STAGES = [
    {
        "id": "connect",
        "title": "Stage 1 - Connect to the server",
        "entry": "ECS console > Instances > target instance > Connect (Workbench), "
                 "or a local SSH client on port 22 (Linux) / Remote Desktop on "
                 "port 3389 (Windows)",
        "action": "Open a session and set or reset the instance login credential "
                  "from the console if the customer does not have one.",
        "fill": "Instance ID or its public IP, the OS username "
                "(root for most Linux images, Administrator for Windows), the "
                "password or key pair.",
        "expected": "A shell (Linux) or desktop (Windows) prompt on the instance.",
        "fallback": "If the session cannot be established, that is a connectivity "
                    "symptom, not a deployment step: stop and hand off per "
                    "references/handoff-rules.md before continuing the mainline.",
        "handoff": "remote-connection diagnosis",
        "risk": "Credential reset may require a restart to take effect on some "
                "images; tell the customer before they use it.",
    },
    {
        "id": "environment",
        "title": "Stage 2 - Prepare the web runtime",
        "entry": "Inside the connected session, or the control panel's one-click "
                 "software installer",
        "action": "Install the runtime the application needs: a control panel "
                  "(BT/aaPanel) for the no-code path, or a web server plus the "
                  "language runtime (Nginx/Apache with PHP, or a Java servlet "
                  "container, or a Python/Node application server) for the manual "
                  "path, or a marketplace image that already ships the stack.",
        "fill": "The stack version required by the application package; the panel "
                "install path; the web root path the installer chooses.",
        "expected": "The web service reports running, and a default page is "
                    "served on the machine's own address.",
        "fallback": "A stack that installs but throws configuration or startup "
                    "errors is a web-server/runtime symptom: hand off, do not "
                    "debug it here.",
        "handoff": "web-server and runtime configuration",
        "risk": "Installing over an existing stack can rewrite its configuration; "
                "ask the customer to confirm the machine is not already serving "
                "another site.",
    },
    {
        "id": "site",
        "title": "Stage 3 - Create the site and its root directory",
        "entry": "Panel > Website > Add site, or the web server's site/vhost "
                 "configuration and its document root directory",
        "action": "Create the site entry bound to the domain and note the root "
                  "directory it writes files into.",
        "fill": "Domain name, root directory path, database name and credential if "
                "the application needs one, PHP/runtime version.",
        "expected": "The site appears in the panel's site list (or the vhost is "
                    "present) with a root directory path the customer can see.",
        "fallback": "Whether the site entry exists is invisible to this skill; ask "
                    "the customer for the paste-back in "
                    "references/customer-selfcheck.md. In-panel errors are a panel "
                    "symptom: hand off.",
        "handoff": "control-panel operations and diagnostics",
        "risk": "Pointing an existing site's root at a new directory hides the old "
                "site immediately; record the previous root path before changing "
                "it so it can be put back.",
    },
    {
        "id": "upload",
        "title": "Stage 4 - Upload the website files",
        "entry": "Panel file manager, or an SFTP/FTP client, or git in the session",
        "action": "Place the application package into the root directory noted in "
                  "Stage 3 and unpack it there.",
        "fill": "Local package path, remote root directory, file permissions for "
                "the web-server user.",
        "expected": "The root directory contains the application entry files "
                    "(index.php / index.html / WEB-INF, depending on the stack).",
        "fallback": "Failed or truncated transfers, and size limits, are a "
                    "file-transfer symptom: hand off rather than retrying blind.",
        "handoff": "file transfer and upload limits",
        "risk": "Uploading onto an existing directory can overwrite a live site; "
                "back up the current contents first.",
    },
    {
        "id": "resolve",
        "title": "Stage 5 - Point the domain at the server",
        "entry": "DNS console for the domain: add or edit resolution records",
        "action": "Create an A record for the domain and the bare domain pointing "
                  "at the instance public address, then wait for propagation.",
        "fill": "Record type A, host record (@ and www), the instance public IP, "
                "default TTL.",
        "expected": "The record list shows the A record with the intended address "
                    "and an enabled state.",
        "fallback": "Records that do not take effect for the customer's browser "
                    "are a resolution-path symptom; hand off. Filing ("
                    "ICP) prerequisites belong to the filing flow, not here.",
        "handoff": "domain resolution and ICP filing",
        "risk": "Editing an existing record that already serves traffic can take a "
                "live site offline; note the previous value before changing it.",
    },
    {
        "id": "verify",
        "title": "Stage 6 - Verify access, then re-verify read-only",
        "entry": "The customer's own browser or curl on their machine, plus a "
                 "re-run of this skill's read-only inventory",
        "action": "Open the domain, report exactly what the browser shows, and "
                  "re-run the entry script to confirm the instance and its bound "
                  "security groups are still as expected.",
        "fill": "The URL tested, the exact browser message or status code, and the "
                "time of the test.",
        "expected": "The site responds with the application's own page.",
        "fallback": "Anything other than a working page after all five build stages "
                    "is an access-failure symptom and leaves this skill: hand off to "
                    "the layered unreachable-site diagnosis.",
        "handoff": "unreachable or slow website, layered diagnosis",
        "risk": "None - this stage is observation only.",
    },
]

STAGE_IDS = [s["id"] for s in MAINLINE_STAGES] + ["all"]

# --- Customer self-check templates ----------------------------------------
# Cloud-side read-only APIs cannot see any of this; the customer runs the
# read-only commands or opens the console page and pastes the output back.
SELF_CHECK_ITEMS = [
    {
        "id": "panel-sites",
        "stage": "site",
        "question": "Does the panel already list a site for this domain?",
        "customer_action": "Panel > Website > Site list: send a screenshot or the "
                           "list of domain names with their root directories.",
        "why": "Site existence is the single most common cause of a domain that "
               "resolves to the server but serves nothing, and it is invisible to "
               "the ECS read-only APIs.",
    },
    {
        "id": "web-root",
        "stage": "upload",
        "question": "Is the application code actually in the site root?",
        "customer_action": "Run these read-only commands in the session and paste "
                           "the output: ls -la <site-root-directory> and df -h",
        "why": "Distinguishes 'files never uploaded' from 'uploaded to the wrong "
               "directory' from 'disk full'.",
    },
    {
        "id": "web-service",
        "stage": "environment",
        "question": "Is the web service running and listening?",
        "customer_action": "Run these read-only commands and paste the output: "
                           "systemctl status nginx (or httpd / the panel service) "
                           "and ss -lntp",
        "why": "A listening process on port 80/443 is the precondition for any "
               "access test to mean anything.",
    },
    {
        "id": "local-resolve",
        "stage": "resolve",
        "question": "What address does the domain resolve to on the customer's "
                    "machine?",
        "customer_action": "Run a read-only lookup locally and paste the output: "
                           "nslookup <domain> or dig +short <domain>",
        "why": "The public DNS view and the customer's local view routinely "
               "disagree; this skill performs no network probes of its own.",
    },
    {
        "id": "access-result",
        "stage": "verify",
        "question": "What exactly does the browser show?",
        "customer_action": "Open the URL and report the visible result verbatim: "
                           "the page, or the exact error text and HTTP status from "
                           "the browser's network tab.",
        "why": "This is the only evidence that can close the deployment loop; "
               "without it the skill reports a staged conclusion and an open to-do "
               "list, never 'resolved'.",
    },
]

# --- Hand-off routing ------------------------------------------------------
# Symptom the customer uses -> why it is out of scope + the routing sentence.
HANDOFF_RULES = [
    {
        "signal": "site worked before / cannot be opened / access error",
        "reason": "The deployment already exists; the question is why access "
                  "fails, which needs layered diagnosis.",
        "route": "unreachable or slow website, layered diagnosis",
        "sentence": "Your site is already deployed, so this is an access-failure "
                    "case rather than a build case. It needs the layered check "
                    "(client and local resolution, then security group, then web "
                    "service); hand it to the unreachable-website diagnosis.",
    },
    {
        "signal": "panel cannot be opened / panel login / panel error message",
        "reason": "Panel-side state and panel credentials are outside the ECS "
                  "read-only API surface.",
        "route": "control-panel operations and diagnostics",
        "sentence": "This needs to be located and fixed inside the control panel "
                    "itself. Use the panel diagnosis flow; this guide only covers "
                    "where panel site creation sits in the deployment mainline.",
    },
    {
        "signal": "Nginx/Apache/IIS config error, PHP/Java/Python runtime error, "
                  "Docker or WordPress install error",
        "reason": "A configuration or runtime failure with its own error text is a "
                  "diagnosis task, not a walkthrough.",
        "route": "web-server and runtime configuration",
        "sentence": "That is a web-server or runtime configuration error. Send the "
                    "exact error text and route it to the web-environment "
                    "configuration flow; this guide does not debug service errors.",
    },
    {
        "signal": "ICP filing, filing subject, filing service code, filing "
                  "interception",
        "reason": "Filing prerequisites and service-code entitlements are a "
                  "separate flow, and non-ECS product entitlements are not visible "
                  "to ECS read-only APIs at all.",
        "route": "ICP filing flow and filing interception",
        "sentence": "Filing resources and steps are handled by the filing flow. If "
                    "the question is how many service codes a purchased product "
                    "includes, check that product's own console entitlement page; "
                    "the ECS side cannot see it.",
    },
    {
        "signal": "cannot connect remotely / SSH refused / RDP fails",
        "reason": "Connection establishment failure is its own symptom axis.",
        "route": "remote connection diagnosis",
        "sentence": "Stage 1 assumes a session can be opened. Since it cannot, "
                    "route this to the remote-connection diagnosis first, then come "
                    "back to the deployment mainline.",
    },
    {
        "signal": "upload fails / file too large / transfer times out",
        "reason": "Transfer failure and size-limit behaviour is a separate flow.",
        "route": "file transfer and upload limits",
        "sentence": "The transfer itself is failing, which is a file-transfer case. "
                    "Route it there; once files land, Stage 4 continues here.",
    },
    {
        "signal": "database install, database whitelist, connection refused by "
                  "the database",
        "reason": "Database-side deployment and connectivity are a separate tier.",
        "route": "database deployment and connectivity",
        "sentence": "Database installation and connectivity are handled by their "
                    "own flow; this guide only records where the application's "
                    "database name and credential get filled in during Stage 3.",
    },
    {
        "signal": "moving an existing site from another server or cloud",
        "reason": "Migration has its own sequencing (data, environment, cutover) "
                  "distinct from a from-scratch build.",
        "route": "whole-site migration",
        "sentence": "This is a migration of an existing site, not a new build. "
                    "Route it to the migration flow so the data and cutover steps "
                    "are sequenced correctly.",
    },
    {
        "signal": "SSL certificate application, deployment, certificate chain",
        "reason": "Certificate lifecycle is a separate flow.",
        "route": "SSL certificate application and deployment",
        "sentence": "Certificate request and binding are handled by the "
                    "certificate flow. Finish the HTTP build here first, then bind "
                    "the certificate there.",
    },
    {
        "signal": "refund, unsubscription, charged incorrectly",
        "reason": "Commercial entitlements and refund eligibility are decided by "
                  "the billing flow; this skill does not judge them.",
        "route": "unsubscription, refund and billing",
        "sentence": "Refund eligibility and unsubscription are commercial "
                    "decisions made in the billing flow, and this skill neither "
                    "judges them nor submits anything for you. I can only point you "
                    "at the console entry.",
    },
    {
        "signal": "AI website-builder product usage",
        "reason": "That is a different product with its own skill surface.",
        "route": "alibabacloud-wxz-website-builder",
        "sentence": "That question is about the AI website-builder product rather "
                    "than deploying a site yourself on ECS; use the website-builder "
                    "product flow for it.",
    },
]

# --- Entitlement caveat ----------------------------------------------------
ENTITLEMENT_CAVEAT = (
    "Instance inventory is only what the two read-only ECS APIs can see, for the "
    "current credential's account, in the one region queried. Entitlements of "
    "non-ECS products are not visible here; send the customer to that product's "
    "own console page instead of inferring."
)
