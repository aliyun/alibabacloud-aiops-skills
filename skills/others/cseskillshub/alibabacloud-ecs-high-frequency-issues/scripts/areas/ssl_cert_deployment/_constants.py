"""Constants for the ECS SSL certificate application and deployment skill.

All reference data (triage tables, the guest reading whitelist, the manual
command checklist, product-rule FAQ wording, error-code guides and handoff
targets) lives here as in-script constants: standalone data files are not
allowed under ``scripts/``.

The skill's Cloud Assistant dispatch action and the snapshot backup action
are confirmation-gated; every other mutating operation (restarting or
reloading a web service, changing security group or firewall rules,
removing certificate files, editing nginx or IIS configuration, changing
forced-HTTPS redirects, deleting snapshots) is out of scope for this skill
by design and appears as manual guidance only.
"""

SKILL_NAME = "alibabacloud-ecs-ssl-cert-deployment"

# --- Observability -----------------------------------------------------------
# Attached to every single CLI invocation so a run is traceable end to end.
USER_AGENT_TEMPLATE = "AlibabaCloud-Agent-Skills/{skill}/{session-id}"

# --- aliyun CLI transport ------------------------------------------------------
CLI_BINARY = "aliyun"
CLI_TIMEOUT_SECONDS = 30
CLI_MAX_RETRIES = 3
CLI_BACKOFF_BASE_SECONDS = 1.0
CLI_BACKOFF_MAX_SECONDS = 8.0
POLL_INTERVAL_SECONDS = 5
POLL_DEADLINE_SECONDS = 120

# Every product runs in plugin mode: the lowercase-hyphenated command form
# (sts GetCallerIdentity -> get-caller-identity). Callers pass PascalCase API
# action names; the CLI layer translates them.
PRODUCT_ECS = "ecs"
PRODUCT_STS = "sts"
PRODUCT_CAS = "cas"
ECS_API_VERSION = "2014-05-26"
STS_API_VERSION = "2015-04-01"
# Certificate service (CAS) read API version, confirmed with `aliyun help cas`;
# the alidns version covers the DNS-record read quoted in the capability note.
CAS_API_VERSION = "2020-04-07"
ALIDNS_API_VERSION = "2015-01-09"
PLUGIN_MODE_COMMANDS = {
("sts", "GetCallerIdentity"): "get-caller-identity",
}

ACTION_DESCRIBE_INSTANCES = "DescribeInstances"
ACTION_DESCRIBE_INSTANCE_STATUS = "DescribeInstanceStatus"
ACTION_DESCRIBE_INVOCATIONS = "DescribeInvocations"
ACTION_GET_CALLER_IDENTITY = "GetCallerIdentity"
# Read-only certificate inventory: the certificate list, the issuance status and
# the validity window of the certificate orders this account owns. Verified with
# `aliyun cas list-user-certificate-order --help` and a live call.
ACTION_LIST_USER_CERTIFICATE_ORDER = "ListUserCertificateOrder"
CAS_ORDER_TYPE_CERT = "CERT"
# OrderType values walked by one run: CERT = issued plus uploaded certificates,
# CPACK = certificate orders still in the pipeline. Both are documented values of
# the same read-only action.
CAS_ORDER_SCOPES = ("CERT", "CPACK")
CAS_PAGE_SIZE = 50
CAS_MAX_PAGES = 2
# Status tokens of ListUserCertificateOrder, quoted verbatim from the CLI help.
CAS_STATUS_MEANINGS = {
    "payed": "paid, waiting for the application to be submitted",
    "checking": "under review",
    "checked_fail": "review failed",
    "issued": "issued",
    "willexpired": "about to expire",
    "expired": "expired",
}
# Validity fields a certificate row may carry. Whichever one comes back is
# echoed; none is invented when absent.
CAS_EXPIRY_FIELDS = ("ExpireTime", "NotAfter", "ExpireDate", "ValidityEnd")
CAS_ISSUE_FIELDS = ("IssuedTime", "IssueTime", "NotBefore", "ValidFrom")
CAS_DOMAIN_FIELDS = ("Domain", "CommonName", "DomainName")
# Confirmation-gated actions. They are dispatched ONLY through an explicit
# operator command line that carries the user-confirmation flags; see
# scripts/areas/ssl_cert_deployment/ssl_cert_deployment_report.py and the User Confirmation section of
# SKILL.md. The dispatch action below carries ONE whitelisted,
# information-only guest reading; the snapshot action backs up one named
# disk before the customer performs a manual change.
ACTION_RUN_COMMAND = "RunCommand"
ACTION_CREATE_SNAPSHOT = "CreateSnapshot"

# The complete set of actions this skill may ever call, as (product, action)
# pairs so the RAM-console rendering is always derived, never hardcoded.
API_WHITELIST = (
    ("ecs", ACTION_DESCRIBE_INSTANCES),
    ("ecs", ACTION_DESCRIBE_INSTANCE_STATUS),
    ("ecs", ACTION_DESCRIBE_INVOCATIONS),
    ("ecs", ACTION_RUN_COMMAND),      # gated dispatch, whitelisted readings
    ("ecs", ACTION_CREATE_SNAPSHOT),  # gated pre-change backup
    ("cas", ACTION_LIST_USER_CERTIFICATE_ORDER),  # read-only cert inventory
    ("sts", ACTION_GET_CALLER_IDENTITY),
)
GATED_WRITE_PAIRS = (
    ("ecs", ACTION_RUN_COMMAND),
    ("ecs", ACTION_CREATE_SNAPSHOT),
)


def ram_action_name(pair):
    """Render one (product, action) pair as its RAM action string."""
    product, action = pair
    return "{0}:{1}".format(product, action)


# Cloud Assistant script kinds.
CLOUD_ASSISTANT_KIND_LINUX = "RunShellScript"
CLOUD_ASSISTANT_KIND_WINDOWS = "RunPowerShellScript"

# --- Paging --------------------------------------------------------------------
PAGE_SIZE = 50
MAX_PAGES = 10

# --- Guest reading whitelist (class B of the low-risk operation list) ------------
# The unified low-risk list shipped with this batch enumerates disk-tier
# commands; the certificate-tier core readings (openssl date and modulus
# checks, curl or TCP egress probes, ss or netstat listeners, firewall
# queries, nginx -t, Get-WebBinding) are NOT on it yet. Until the whitelist
# extension is approved, those commands are only printed as a manual
# checklist the customer runs, and the ONLY readings this skill may
# dispatch are the generic file-system inspections below, one per call.
GUEST_READINGS_LINUX = (
    "stat",    # owner, mode and timestamps of one certificate or key file
    "ls -l",   # directory listing of a certificate folder
    "wc -l",   # line count of a certificate or key file
)
GUEST_READINGS_WINDOWS = ()  # no approved Windows reading yet (pending review)

LINUX_PATH_RE = r"^/[A-Za-z0-9][A-Za-z0-9._/+ -]{0,127}$"
# A quote, redirection, chaining or destructive verb anywhere in the
# requested reading means the request is refused outright.
GUEST_BLOCKED_TOKENS = (
    ";", "|", "&", ">", "<", "`", "$", "*", "?", "\n", "\\", "'", "\"",
    "&&", "||", "$(", "${",
)
GUEST_BLOCKED_WORDS = (
    "rm", "rmdir", "mv", "cp", "dd", "kill", "killall", "shutdown", "reboot",
    "halt", "mkfs", "fdisk", "parted", "wipefs", "truncate", "mount",
    "umount", "systemctl", "service", "crontab", "chown", "chmod", "passwd",
    "useradd", "userdel", "init", "format", "cipher", "del", "erase",
    "sdelete", "set", "out-file", "new-item", "remove-item", "move-item",
    "rename-item", "clear-recyclebin", "invoke", "start-process",
    "stop-process", "iwr", "curl", "wget", "nc", "ssh", "scp", "eval", "iex",
)

# --- ACME and validation endpoints (customer toolchains hit these) ------------------
ACME_ENDPOINTS = (
    "acme-v02.api.letsencrypt.org",
    "acme-staging-v02.api.letsencrypt.org",
)
DNS_PROVIDER_ENDPOINTS = ("alidns.aliyuncs.com", "api.cloudflare.com")
# Let's Encrypt fronts its ACME API behind Cloudflare edge space. When a
# resolver returns an address inside this range, the endpoint is overseas
# even though the toolchain calls it a US service name.
CLOUDFLARE_LE_CIDR = "172.65.0.0/16"
# Region ids that sit outside the mainland network backbone.
CN_MAINLAND_PREFIX = "cn-"
CN_OVERSEAS_REGIONS = ("cn-hongkong",)


def is_mainland_region(region_id: str) -> bool:
    """True when the region id names a mainland region (Hong Kong excluded)."""
    rid = (region_id or "").strip().lower()
    if not rid.startswith(CN_MAINLAND_PREFIX):
        return False
    return rid not in CN_OVERSEAS_REGIONS


# --- Customer-quotable error strings and codes -> verdict guide ----------------------
# The two tier error codes plus the literal tool outputs observed in real
# support tickets. The report quotes the matching row verbatim.
ERROR_CODE_GUIDE = (
    (
        "err_cert_date_invalid",
        "The certificate notBefore/notAfter window does not cover the current "
        "time: expired, not yet valid, or the server clock is skewed.",
        "Renew or re-issue the certificate; check the system clock before "
        "concluding the certificate itself is wrong. A certificate that is "
        "not expired can still fail: an expired one and a mismatched key are "
        "different faults (evidence: ticket T-B5F37974).",
    ),
    (
        "err_connection_closed",
        "The TLS or TCP connection to the endpoint was reset or closed during "
        "the handshake, which is a different failure shape than a timeout.",
        "Reset usually means a local firewall, an endpoint-side drop, or an "
        "intermediate device cutting the session; timeout usually means a "
        "path problem. Run the two-way split from references/"
        "guest-diagnostics-runbook.md (telnet-style connect test plus curl) and "
        "report which one reproduced.",
    ),
    (
        "context deadline exceeded",
        "Literal timeout text from 1Panel and Go-based ACME toolchains when the "
        "validation API call never completes (evidence: ticket T-6A73F6B0).",
        "Map to the egress branch: mainland region plus an overseas ACME or "
        "DNS-provider endpoint means a cross-border path issue, not an "
        "Alibaba Cloud block.",
    ),
    (
        "query timed out looking up A/AAAA",
        "Literal ACME DNS validation timeout text; observed for .cn domains "
        "when the CA-side DNSSEC cache was stale (evidence: ticket T-4AC3F65A).",
        "The cause sits at the CA resolver, not on the instance: wait for the "
        "cache window or switch the validation method (HTTP-01 instead of "
        "DNS-01, or the other way around).",
    ),
)

# --- Triage decision tree (rendered by the report mode) ---------------------------------
TRIAGE_TREE_INTRO = (
    "Entry symptom decides the branch. The script evaluates the automated "
    "checks first (region and OS kind, instance state, public DNS resolution "
    "versus the instance address, the live TLS view of each domain), then "
    "routes the remaining evidence to manual steps."
)

APPLY_FAIL_BRANCHES = (
    (
        "region in mainland AND endpoint resolves inside 172.65.0.0/16 (or "
        "any overseas address)",
        "Cross-border path to the CA edge node. Alibaba Cloud does not block "
        "Let's Encrypt; mainland regions reach the overseas edge addresses "
        "over a congested public path (evidence: tickets T-BAA897DB, "
        "T-C3B1F4A7, T-A49EBFF0, T-75A1E320, T-6A73F6B0).",
        "Alternative paths, all customer-side: apply through the Alibaba "
        "Cloud SSL certificate console free certificate instead; use another "
        "CA reachable from the region; retry off-peak; or route the tool "
        "through a working proxy. Keep BaoTa or 1Panel and change only the CA "
        "when the panel itself is otherwise fine.",
    ),
    (
        "endpoint is a domestic address (for example alidns.aliyuncs.com) "
        "and still unreachable",
        "Suspect the instance egress path: security group outbound rules, the "
        "guest firewall, or proxy configuration. Inbound acceptance does not "
        "imply outbound reachability (evidence: ticket T-233E37E1).",
        "Manual checklist only: the egress probe commands are not on the "
        "approved reading whitelist yet. Print the suggested commands from "
        "references/ssl-cert-deployment__guest-diagnostics-runbook.md and ask the customer to paste "
        "results back.",
    ),
    (
        "failure happens during DNS validation with A/AAAA lookup timeout",
        "CA-side resolver cache, common for .cn domains.",
        "Wait for the cache window to expire or switch validation method; do "
        "not change the instance.",
    ),
    (
        "connection reset instead of timeout",
        "Matches err_connection_closed: a local firewall drop or endpoint "
        "reset rather than a path timeout.",
        "Two-way split test (telnet-style connect plus curl -I) to localize; "
        "check the guest firewall and any security software with the printed "
        "manual commands.",
    ),
)

DEPLOY_BRANCHES = (
    (
        "external TLS view serves a certificate whose names do not cover the "
        "requested host, and that certificate belongs to another site on the "
        "same server (domain / certificate mismatch)",
        "SNI fallback: the nginx server block whose server_name matches the "
        "requested host has no ssl_certificate / ssl_certificate_key pair "
        "(or does not listen 443 ssl), so the handshake is answered by the "
        "default server block and nginx serves THAT block's certificate. "
        "This is the first ruling and the certificate itself is usually fine "
        "(evidence: ticket T-F9AA3466, a subdomain with no TLS pair was "
        "served the main domain's certificate).",
        "Manual: run nginx -T, find the block whose server_name covers the "
        "host, add the fullchain ssl_certificate and the matching "
        "ssl_certificate_key there, make it listen 443 ssl, leave the "
        "default server block untouched; nginx -t then reload, snapshot "
        "first. Reissuing or re-purchasing the certificate does not fix it.",
    ),
    (
        "external TLS view still shows the old certificate (issuer, serial or "
        "fingerprint of the previous cert)",
        "The web service did not load the new file: imported is not loaded. "
        "IIS needs the certificate selected in the site binding; nginx needs "
        "the ssl_certificate lines to point at the new files inside every "
        "included config; containerized nginx needs the install path to be "
        "inside the container view (evidence: tickets T-382FDB28, "
        "T-08D625D0).",
        "Walk the web-server branch checklist from "
        "references/ssl-cert-deployment__nginx-iis-deploy-checklist.md. Reload or restart stays a "
        "manual action after a snapshot; create the backup snapshot first "
        "when the customer is about to change server files.",
    ),
    (
        "external TLS view shows the new certificate but the browser still "
        "warns",
        "Chain incomplete or a second vhost without the binding; compare the "
        "served chain with the fullchain file.",
        "Manual: verify the fullchain file order and every listening vhost; "
        "the reload itself stays manual.",
    ),
    (
        "certificate permission error while installing",
        "File owner or mode on the key file; this reading IS on the approved "
        "whitelist and can be dispatched after confirmation.",
        "Run guest-probe mode with stat or ls -l on the named certificate "
        "path (one reading, confirmed), then hand the customer the manual "
        "fix steps.",
    ),
)

CERT_BODY_BRANCHES = (
    (
        "served certificate window does not cover now",
        "err_cert_date_invalid: expired, not yet valid, or clock skew.",
        "Renew and redeploy (manual); check the system clock; explain that "
        "having months left on validity does not rule out a mismatched key.",
    ),
    (
        "customer reports key mismatch or nginx logs SSL errors after "
        "renewal",
        "Certificate and private key modulus pair mismatch (evidence: ticket "
        "T-B5F37974, root cause found only inside the guest with openssl).",
        "Print the openssl modulus comparison from "
        "references/ssl-cert-deployment__guest-diagnostics-runbook.md for the customer to run; on a "
        "match failure: back the current files up to another directory, "
        "re-issue, reinstall. All of it manual, snapshot-first before file "
        "changes. A certificate change is not evidence of intrusion; "
        "intruders plant processes or deface pages, they do not rotate "
        "certificates (support wording from the same ticket).",
    ),
    (
        "renewal failed while a forced HTTPS redirect is active",
        "The redirect amplifies the fault: every plain HTTP visit is sent to "
        "a broken 443, so the whole site appears down (evidence: ticket "
        "T-411B8BA7).",
        "Manual: temporarily disable the forced redirect, restore HTTP, then "
        "re-issue and rebind the certificate. Editing the redirect config "
        "stays a customer action.",
    ),
)

HTTPS_BRANCHES = (
    (
        "public DNS answer differs from the instance public address",
        "Traffic never reaches this instance: a stale A record, an old CDN or "
        "another host (evidence: ticket T-BF6A05D6, where tcpdump proved no "
        "inbound traffic while the resolution pointed elsewhere).",
        "Report both addresses; the customer corrects the DNS record "
        "(manual). Re-run the report afterwards to verify.",
    ),
    (
        "TLS handshake reset or closed (err_connection_closed)",
        "Port reachable but the session dies: check the security group "
        "inbound rule for 443 and any deny rule targeting the server own "
        "address (evidence: ticket T-438814FA, hidden deny-self rule).",
        "Print the security-group self-check list from "
        "references/ssl-cert-deployment__triage-decision-tree.md; rule edits stay manual.",
    ),
    (
        "TCP timeout on 443 with correct resolution",
        "Inbound 443 not accepted, or nothing listening.",
        "Manual: security group inbound checklist plus the listening-socket "
        "reading (ss or netstat) from the runbook, which is currently "
        "customer-executed; report the paste-back.",
    ),
    (
        "everything consistent and still unreachable",
        "Beyond automated reach: packet-level self-proof is needed.",
        "Escalate to a human session (snapshot plus authorization is the "
        "support path); record which checks already passed.",
    ),
)

PRODUCT_RULES_BRANCHES = (
    (
        "free certificate entry or quota wording (V1 versus V2)",
        "Console flow questions, ticket-derived wording: the legacy free "
        "certificate entry stopped accepting new orders and the console "
        "redirects to the newer certificate version; the quoted free quota "
        "was twenty certificates a year, cleared on December 31 (evidence: "
        "ticket T-9A27862F, single-ticket wording).",
        "State the rule with the confidence tag below and point at the SSL "
        "certificates console; the certificate list, its status and its "
        "validity dates are read by this area through "
        "cas:ListUserCertificateOrder, while the remaining free quota and "
        "the review progress stay console-side for the customer.",
    ),
    (
        "domain level confusion (second versus third level host names)",
        "Level counting from the right: example.com is the registrable "
        "domain, api.example.com is a host one level below it; a "
        "wildcard covers one level only.",
        "Print the level rule and let the customer confirm the exact host to "
        "certify; application itself stays manual in the console.",
    ),
    (
        "DV phone validation and expedite requests",
        "Domain validation calls the enterprise phone on public registry "
        "records, not necessarily the console contact (evidence: ticket "
        "T-14495C53, single-ticket wording); review order cannot be "
        "expedited.",
        "Update the contact data at the registry source or answer the "
        "verification call; set the expectation that no expedite path "
        "exists for the skill or for support staff.",
    ),
)

# Confidence tag attached to every product-rule statement sourced from a
# single ticket summary (batch decision: downgrade to non-committal wording
# until official docs confirm the figures).
PRODUCT_RULES_CONFIDENCE = (
    "Confidence: ticket-derived wording only. Treat the official console and "
    "help documentation as authoritative before quoting numbers or deadlines "
    "to the customer."
)

# --- Web-server branch checklists (manual; printed by checklist mode) -------------------
WEB_SERVER_CHECKLISTS = {
    "nginx": (
        "1. When the served certificate belongs to another site on the same "
        "server (or the browser reports a name mismatch), start with SNI "
        "selection, not the certificate files: in the nginx -T dump find the "
        "server block whose server_name covers the requested host. That "
        "block MUST carry both ssl_certificate (fullchain) and "
        "ssl_certificate_key and must listen 443 ssl. If it carries neither, "
        "nginx hands the handshake to the default server block (first listen "
        "443 block or the explicit default_server) and serves THAT block's "
        "certificate (evidence: ticket T-F9AA3466, a subdomain with no TLS "
        "pair was served the main domain's certificate). Reissuing the "
        "certificate does not fix this.",
        "2. Locate every config the master file includes: run "
        "nginx -T (full effective config dump, information-only) and check "
        "the ssl_certificate and ssl_certificate_key lines in each server "
        "block, including everything under conf.d and sites-enabled "
        "(evidence: ticket T-08D625D0, a conf.d include carried the old "
        "path).",
        "3. Confirm the two lines reference the new files, and that the "
        "certificate file is the fullchain, not the bare server certificate.",
        "4. Validate before loading: run nginx -t and report its output.",
        "5. Load the new pair: nginx -s reload or systemctl reload nginx is "
        "a MANUAL change: take a snapshot of the system disk first, tell the "
        "customer the service reloads without dropping connections but a "
        "bad config can fail subsequent restarts, and let the customer run "
        "it.",
        "6. Verify from outside: rerun this report; the served fingerprint "
        "and expiry window must match the new certificate.",
    ),
    "iis": (
        "1. Importing a pfx into the certificate store does NOT bind it: "
        "open the site, Edit bindings, HTTPS entry, and select the new "
        "certificate in the SSL certificate list (evidence: ticket "
        "T-382FDB28, the exact step the customer missed).",
        "2. Binding host name field: type the bare host name, for example "
        "www.example.com, with no trailing slash and no URL scheme; a "
        "wrongly formatted field makes the whole site unreachable "
        "(evidence: the correction inside the same ticket).",
        "3. Expired versus new: the bindings list shows the thumbprint; "
        "compare with the new certificate thumbprint.",
        "4. Applying changes: recycling the application pool or restarting "
        "the site is a MANUAL step after a snapshot.",
        "5. Windows certificate-store readings (Get-WebBinding, "
        "Get-Certificate) are not on the approved reading whitelist yet: "
        "print them for the customer and read the paste-back.",
    ),
    "baota": (
        "1. Open the site settings, SSL tab, confirm the certificate shown "
        "matches the issued one (issuer and expiry), then click Save to let "
        "the panel rewrite the vhost config.",
        "2. If the panel certificate request fails while the panel is the "
        "only toolchain issue, keep BaoTa and switch the CA to the Alibaba "
        "Cloud free certificate, then paste the certificate and key into "
        "the custom certificate box (support advice from tickets "
        "T-C3B1F4A7, T-A49EBFF0).",
        "3. The Force HTTPS switch: when renewal fails, a live switch sends "
        "visitors to the broken 443; disabling it is a manual panel click.",
    ),
    "1panel": (
        "1. Open the website, certificate settings, confirm which domain "
        "record the ACME account validates and which CA is selected.",
        "2. For cross-account DNS (the domain lives in another account), "
        "the automatic DNS validation needs an API token scoped to the "
        "account that owns the zone; a timeout on the provider API is the "
        "path failure from ticket T-6A73F6B0.",
        "3. Switch the CA inside the panel to retry issuance after a "
        "cross-border failure; keep the panel otherwise unchanged.",
    ),
    "docker-nginx": (
        "1. The files must be visible INSIDE the container: an acme.sh "
        "install command that writes to a host path the container does not "
        "mount leaves nginx serving the old pair (evidence: ticket "
        "T-B5F37974, acme.sh --install-cert with --key-file, "
        "--fullchain-file and a docker exec reload command).",
        "2. Rebuild the pair only after backing the current files up to "
        "another directory; reissue with the original DNS provider plugin, "
        "reinstall to the same paths, then reload the container.",
        "3. The reload command (docker exec ... nginx -s reload) is a "
        "MANUAL step: snapshot the container host disk first.",
    ),
    "apache": (
        "1. Check SSLEngine, SSLCertificateFile, SSLCertificateKeyFile and "
        "SSLCertificateChainFile in every VirtualHost *:443 block and in "
        "included files.",
        "2. apachectl configtest before loading; graceful restart is manual "
        "after a snapshot.",
    ),
}

WEB_SERVERS = ("nginx", "iis", "apache", "baota", "1panel", "docker-nginx")
GUEST_LINUX = "linux"
GUEST_WINDOWS = "windows"

# --- Egress probe readings the customer runs (NOT dispatched here) ----------------
SUGGESTED_EGRESS_COMMANDS = {
    GUEST_LINUX: (
        "curl -I --connect-timeout 10 https://acme-v02.api.letsencrypt.org "
        "(renewal endpoint reachability; a stall at connect is a path "
        "timeout, an immediate reset matches err_connection_closed)",
        "curl -I --connect-timeout 10 https://acme-staging-v02.api."
        "letsencrypt.org (staging endpoint, same split)",
        "curl -I --connect-timeout 10 https://alidns.aliyuncs.com (domestic "
        "validation endpoint: unreachable means the instance egress path is "
        "the problem, not the cross-border route)",
        "telnet <host> 443 or nc -vz <host> 443 (TCP-only split, the "
        "method support used in ticket T-3E637B73 for the outbound "
        "direction)",
        "openssl x509 -in <cert-file> -noout -dates -subject (validity "
        "window and owner of the file on disk)",
        "Compare modulus: openssl x509 -noout -modulus -in <crt> versus "
        "openssl rsa -noout -modulus -in <key> must be byte-identical",
        "ss -tlnp or netstat -tlnp (what actually listens on 443)",
        "iptables -S or firewall-cmd --list-all (guest firewall view)",
    ),
    GUEST_WINDOWS: (
        "Test-NetConnection <host> -Port 443 (TCP reachability split)",
        "tracetcp <host>:443, the tool the customer and engineer used in "
        "ticket T-75A1E320: a completed trace with a failing curl isolates "
        "the fault to the path above TCP",
        "Get-ChildItem Cert:\\LocalMachine\\My | Format-Table FriendlyName, "
        "NotAfter, Thumbprint (store view of installed certificates)",
        "Get-WebBinding (IIS binding table, information only)",
    ),
}

EGRESS_PROBE_NOTE = (
    "These commands are information-only, but they are not on the approved "
    "reading whitelist for this skill tier, so the skill prints them for the "
    "customer to run and pastes the results back. The agent never dispatches "
    "them through Cloud Assistant."
)

# --- Misconception corrections (support wording, ticket-grounded) ---------------------
MISCONCEPTIONS = (
    ("Inbound rules opened, so outbound must work",
     "Inbound and outbound directions are evaluated separately; check each "
     "direction independently (evidence: ticket T-233E37E1). Closing a port "
     "inbound affects outside visitors only, never local processes."),
    ("Alibaba Cloud blocks Let's Encrypt",
     "No platform block exists on these endpoints; mainland-to-overseas "
     "edge paths degrade on their own, and the engineer tested that from "
     "several machines at the time (tickets T-C3B1F4A7, T-A49EBFF0, "
     "T-75A1E320)."),
    ("Microsoft.com works, so my network is fine",
     "A reachable overseas site proves nothing about a specific congested "
     "edge range; per-endpoint probing is required (ticket T-75A1E320)."),
    ("Certificate imported, therefore effective",
     "Import and bind are two steps in IIS, and download plus reference plus "
     "reload are three steps in nginx (tickets T-382FDB28, T-08D625D0)."),
    ("Certificate has a month left, so it cannot be the problem",
     "Expiry and key pairing are independent; a valid certificate with the "
     "wrong key fails exactly like an expired one (ticket T-B5F37974)."),
    ("The certificate changed, so the server must be compromised",
     "Support wording: intrusion means foreign processes or defaced pages, "
     "not silently rotated certificates (ticket T-B5F37974)."),
)

# --- Snapshot-first rule and the customer notice text ---------------------------------
SNAPSHOT_FIRST_RULE = (
    "Before guiding ANY in-server change (replacing certificate files, "
    "editing nginx or IIS configuration, toggling forced HTTPS), the "
    "customer backs the affected disk up first. Run the entry script in "
    "snapshot-backup mode (it dispatches ONE snapshot of the named disk "
    "after explicit user confirmation), or relay the console steps and the "
    "links below. Pure diagnosis is exempt."
)
SNAPSHOT_NOTICE = (
    "Snapshots are billed by stored capacity while they exist, and the "
    "delete option is available at any time; remove temporary backups after "
    "the change succeeds. Official pages: create "
    "https://help.aliyun.com/document_detail/25455.html , billing "
    "https://help.aliyun.com/document_detail/56159.html , delete "
    "https://help.aliyun.com/document_detail/128131.html (links as used by "
    "support engineers in the source tickets)."
)

# --- Out-of-scope routing (mirrors references/ssl-cert-deployment__handoffs.md) ----------------------------
HANDOFFS = (
    ("Mail sending on ports 25, 465 or 587: the platform limits port 25 by "
     "default and does not limit 465 and 587; suspected local interception "
     "needs the same egress split (ticket T-3E637B73)",
     "outbound-network and mail-service diagnosis tiers, not certificate "
     "triage"),
    ("ICP filing verification, rectification deadlines, keeping access "
     "records alive (second half of ticket T-B5F37974)",
     "the filing channel or a human agent; this skill only recognizes the "
     "topic"),
    ("Domain name certificate download, data center address proof, service "
     "provider unit wording, graded-protection or value-added telecom "
     "materials (tickets T-231D5C7C, T-B0AD7067)",
     "self-service center and compliance material channels; the keywords "
     "certificate collide here but nothing about TLS does"),
    ("Remote login failure where the RDP or SSH port was moved, for example "
     "5562 (ticket T-1F44C122)",
     "instance connection tiers such as alibabacloud-ecs-diagnose or the "
     "remote-access tier"),
    ("Disk capacity, inode exhaustion, expansion not visible, IO "
     "performance",
     "area:disk-expand-diagnosis, "
     "area:disk-expand-diagnosis, "
     "area:resource-bottleneck"),
    ("A purchased certificate deployment service that the customer says was "
     "delivered wrongly (ticket T-1F44C122)",
     "the original service order and a human agent; this skill only runs "
     "self-service verification"),
    ("Website unreachable with 502, 504 or 404 and no certificate or HTTPS "
     "wording at all",
     "alibabacloud-ecs-diagnose and the web-access tiers"),
)

# --- Verified official links (from aliyun help search hits and the ticket "
#     transcripts; the only URLs the skill may quote) -----------------------------------
HELP_LINKS = (
    ("Deploy an SSL certificate for HTTPS on ECS",
     "https://help.aliyun.com/zh/ecs/user-guide/ssl.md"),
    ("Create a disk snapshot",
     "https://help.aliyun.com/zh/ecs/user-guide/create-a-snapshot-of-a-disk"),
    ("Snapshot billing",
     "https://help.aliyun.com/zh/ecs/product-overview/snapshots-1"),
    ("Download a domain name certificate (registration, not TLS)",
     "https://help.aliyun.com/zh/dws/user-guide/download-a-domain-name-certificate"),
    ("Self-service center query for the data center address",
     "https://smartservice.console.aliyun.com/service/self-service-center/search?questionId=27082&trackFrom=searchResult"),
)

NOT_VERIFIED_NOTE = (
    "Certificate inventory, order/quota state and validity dates ARE read "
    "from the certificate service through the read-only "
    "cas:ListUserCertificateOrder action (OrderType CERT for issued and "
    "uploaded certificates, CPACK for orders still in the pipeline); the "
    "sibling read actions ListCertificates, GetUserCertificateDetail and "
    "DescribeCertificateState cover the same product and may be named in "
    "guidance, but this area does not call them. DNS record content is "
    "readable through alidns:DescribeDomainRecords and security group rules "
    "through ecs:DescribeSecurityGroupAttribute; neither is called by this "
    "area, so those two remain customer-read console steps here. When a read "
    "is refused or fails, the run marks that topic NOT VERIFIED instead of "
    "filling the gap. The skill never invents an answer."
)

# Capability map printed by the report so a reader can see which evidence is
# machine-read and which is deliberately left to the customer.
EVIDENCE_SURFACE = (
    ("certificate inventory / order status / validity dates",
     "read-only API (cas ListUserCertificateOrder)"),
    ("outside-in DNS resolution and TLS handshake",
     "read by this script (public resolver plus real handshake)"),
    ("DNS record content of the zone",
     "readable via alidns DescribeDomainRecords, not called by this area"),
    ("security group inbound/outbound rule content",
     "readable via ecs DescribeSecurityGroupAttribute, not called by this area"),
    ("in-guest certificate, listener and web-server state",
     "customer-run commands, paste-back (whitelist pending)"),
)

# --- Failure vocabulary -------------------------------------------------------------
# Permission failures are reported with these literals only.
CODE_NO_PERMISSION = "NoPermission"
CODE_IMPLICIT_DENY = "ImplicitDeny"
CODE_INVALID_CREDENTIAL = "InvalidCredential"
CODE_MISSING_PARAMETER = "MissingParameter"
CODE_CLI_TIMEOUT = "CliTimeout"
CODE_CLI_UNAVAILABLE = "CliUnavailable"
CODE_API_ERROR = "ApiError"
CODE_PARSE_ERROR = "ResponseParseError"

STATUS_OK = "OK"
STATUS_DEGRADED = "DEGRADED"
STATUS_FAIL = "FAIL"
NOT_RETURNED = "not returned"

# Transient conditions worth retrying.
RETRYABLE_MARKERS = (
    "throttling", "throttlingexception", "systembusy", "serviceunavailable",
    "internalerror", "internal failure", "temporar", "connection reset",
    "timed out", "timeout", "500", "502", "503", "429",
)
# Conditions that must never be retried.
NON_RETRYABLE_MARKERS = (
    "missingparameter", "invalidparameter", "signaturedoesnotmatch",
    "invalidaccesskeyid", "no permission", "nopermission", "implicitdeny",
    "accessdenied", "notfound", "invalidinstanceidnotfound",
    "incorrectinstancestatus",
)
# Credential-chain failures, classified apart because the recovery is to
# refresh the local CLI configuration, not to retry or request a permission.
CREDENTIAL_ERROR_MARKERS = (
    "invalidaccesskeyid", "signaturedoesnotmatch", "invalidsecuritytoken",
    "securitytokenexpired", "invalidcredential",
)
# Credential material that must never reach the terminal or a log line. Each
# pattern makes the separators optional so one entry covers the concatenated,
# underscored and hyphenated spellings a real CLI response can use.
SENSITIVE_KEY_PATTERNS = (
    r"access[-_]?key[-_]?id",
    r"access[-_]?key[-_]?secret",
    r"security[-_]?token",
    r"bearer token",
    r"signature",
    r"password",
    r"passwd",
    r"private key",
)
MASKED_VALUE = "***"

# --- External verification ------------------------------------------------------------
DEFAULT_TLS_PORT = 443
TLS_CONNECT_TIMEOUT_SECONDS = 12
DNS_RESOLVE_TIMEOUT_SECONDS = 8
EXPIRING_SOON_DAYS = 30

# --- Report banners -------------------------------------------------------------------
BANNER = "ECS SSL Certificate Application and Deployment Triage"
FINAL_ANSWER_BANNER = (
    "+====================================================================+\n"
    "|  Alibaba Cloud ECS Skill: {skill}\n"
    "|  Session: {session_id}\n"
    "+====================================================================+"
)

# --- Product FAQ topics (offline knowledge, printed by faq mode) -----------------------
PRODUCT_FAQ_TOPICS = {
    "free-cert-entry": (
        "Topic: where to apply for a free certificate now.",
        "The legacy free certificate entry stopped taking new orders and "
        "the console routes creation into the newer certificate version. "
        "The certificates this account already owns, their status and their "
        "validity dates are read by this area through the read-only "
        "cas:ListUserCertificateOrder action; the remaining free quota and "
        "the review progress are not returned by it and stay console-side. "
        "The yearly free quota and its clearing date quoted in support "
        "tickets (twenty certificates a year, cleared on December 31) are "
        "single-ticket wording.",
        "Entry: the SSL certificates section of the console; application, "
        "verification and download stay manual customer steps.",
    ),
    "domain-levels": (
        "Topic: which level a certificate covers.",
        "Count labels from the right: the registrable domain is the last "
        "two labels, api.example.com is one host below it, and a wildcard "
        "for the registrable domain covers one label level only. A "
        "third-level host such as www.api.example.com needs its own name "
        "or its own wildcard.",
        "Ask the customer for the exact host the browser visits, then "
        "certify that name.",
    ),
    "dv-phone": (
        "Topic: domain validation phone call and expedite requests.",
        "Domain validation for organizational calls uses the enterprise "
        "phone number registered at public business registries, which may "
        "differ from the console contact; update the registry-side contact "
        "or answer that number (single-ticket wording from ticket "
        "T-14495C53). Review order cannot be expedited through support.",
        "Expectation management: neither this skill nor a support agent "
        "can move a validation queue forward.",
    ),
    "renew-window": (
        "Topic: when to renew.",
        "Renewal should complete before the served certificate leaves its "
        "validity window; a failed renewal combined with a forced HTTPS "
        "redirect takes the whole site down, plain HTTP visits included "
        "(ticket T-411B8BA7). The external TLS check in this skill names "
        "the exact remaining days from the served certificate.",
        "Automate renewal where the toolchain supports it, and keep the "
        "redirect switch as the manual escape hatch.",
    ),
}

SYMP_SYMPTOMS = (
    "apply-fail", "deploy-not-effective", "cert-invalid",
    "https-unreachable", "product-rules",
)
EXIT_BY_STATUS = {STATUS_OK: 0, STATUS_DEGRADED: 1, STATUS_FAIL: 2}
