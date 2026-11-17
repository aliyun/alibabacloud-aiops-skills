#!/usr/bin/env python3
"""
_constants.py -- Embedded static data for the ECS SLB backend diagnosis skill
==============================================================================
SECURITY: This skill is strictly READ-ONLY. This module holds only constants
(API metadata, decision rules, self-check checklists distilled from real
support tickets). It never reads or writes any credential; authentication is
resolved exclusively by the aliyun CLI default credential chain.

Per platform rule 1.1.2, scripts/ may only contain executable code, so every
table / checklist / FAQ used by the diagnosis is embedded here as a Python
constant. There are no data files in this skill.
"""

# ---------------------------------------------------------------------------
# Skill identity (observability)
# ---------------------------------------------------------------------------

SKILL_NAME = "alibabacloud-ecs-slb-backend-diagnosis"

# User-Agent template -- every aliyun CLI call of one run carries
#   AlibabaCloud-Agent-Skills/{SKILL_NAME}/{session-id}
# where session-id is a 32-character hex string (uuid.uuid4().hex), generated
# once per run by _cli.session_id() and shared by all calls of that run.
UA_TEMPLATE = "AlibabaCloud-Agent-Skills/{skill}/{session-id}"

# ---------------------------------------------------------------------------
# API / endpoint metadata
# ---------------------------------------------------------------------------
# OpenAPI versions (informational; the aliyun CLI carries its own metadata).
# The cms value follows the same pinning used by the sibling read-only skills
# (metrics endpoint family, API version 2019-01-01).
API_VERSIONS = {
    "ecs": "2014-05-26",
    "cms": "2019-01-01",
    "vpc": "2016-04-28",
    "sts": "2015-04-01",
}

DEFAULT_REGION = "cn-hangzhou"

# Per-call CLI subprocess timeout (seconds). Every network invocation uses it
# (platform rule 7.6.1).
DEFAULT_TIMEOUT = 60

# ---------------------------------------------------------------------------
# Query limits / guardrails
# ---------------------------------------------------------------------------
PAGE_SIZE = 50           # DescribeInstances / DescribeEipAddresses page size
MAX_PAGES = 20           # hard pagination guardrail per loop
MAX_INSTANCES = 10       # instances rendered in the report (detail cap)
MAX_METRIC_CALLS = 20    # cap on cms DescribeMetricLast calls per run
MAX_TYPE_QUERY = 10      # DescribeInstanceTypes instance-types per call

# ---------------------------------------------------------------------------
# CloudMonitor metric parameters used for the "is traffic still flowing" check
# ---------------------------------------------------------------------------
# Namespace / metric names follow the same read-only CloudMonitor usage of
# the sibling ECS skills (acs_ecs_dashboard, instance-dimension metrics).
# If a metric name is not authorized or reports nothing for the instance,
# the call degrades with a [WARN] line -- absence of datapoints is reported
# honestly and never interpreted as "zero traffic".
CMS_NAMESPACE = "acs_ecs_dashboard"
CMS_METRICS = [
    "CPUUtilization",     # backend busy / alive signal
    "InternetOutRate",    # public egress traffic signal (bits/s)
]
CMS_PERIOD_SECONDS = "300"

# ---------------------------------------------------------------------------
# Symptom triage: customer keyword -> scenario code
# ---------------------------------------------------------------------------
# Keys are lowercase substrings matched against the customer's own wording.
# Order matters: first match wins, more specific phrases first.
SYMPTOM_KEYWORDS = [
    ("eip-slb",       ["eip", "elastic ip", "eip retention fee",
                       "eip configuration fee"]),
    ("certificate",   ["certificate", "ssl", "tls", "https cert", "cert is still",
                       "old certificate", "new certificate"]),
    ("health-check",  ["health check", "healthcheck", "not in a normal listening",
                       "unhealthy", "empty reply from server"]),
    ("http-5xx",      ["502", "bad gateway", "504", "gateway timeout",
                       "404", "not found", "unexpected response code"]),
    ("real-client-ip", ["real client ip", "client ip", "x-forwarded-for",
                        "xff", "127.0.0.1 in the log", "visitor ip"]),
    ("scaling",       ["scaling", "auto scaling", "new instance gets no",
                       "new server is not used", "scaled-out"]),
    ("selection",     ["does alb", "does clb", "does nlb", "ftp", "port range",
                       "which load balancer", "cross-zone", "cross zone",
                       "availability zone", "select", "support"]),
    ("handoff",       ["bill", "billing", "invoice", "refund", "cpu", "memory",
                       "ssh", "rdp", "security group", "waf", "firewall",
                       "nopermission", "permission", "dns", "bandwidth"]),
]

# Explicit --symptom values accepted by argparse (same codes as above).
SCENARIOS = [
    "certificate", "health-check", "http-5xx", "real-client-ip",
    "selection", "scaling", "eip-slb", "handoff", "other",
]

# ---------------------------------------------------------------------------
# Console self-check checklists (facts the cloud APIs cannot read here)
# ---------------------------------------------------------------------------
# There is deliberately NO Server Load Balancer read API contract verified for
# this skill, so every load-balancer-side fact must come from the customer's
# own console inspection. The agent hands these checklists to the customer and
# re-runs the entry script with the returned values.
SELF_CHECK_CONSOLES = {
    "certificate": [
        "SLB/ALB console -> the instance -> Listeners: report the listener "
        "protocol (TCP / UDP / HTTP / HTTPS) and port of the HTTPS (443) "
        "entry point.",
        "If the listener protocol is TCP or UDP: there is no certificate "
        "field on the listener by design (see rule CERT-L4).",
        "For the HTTPS (layer-7) listener: report the certificate name / "
        "expiry shown on the listener detail.",
        "Report the backend server group and each backend server's "
        "forwarded-to port for this listener.",
    ],
    "health-check": [
        "SLB/ALB console -> the affected listener -> its health-check "
        "settings: report health-check protocol, port, URI, success codes, "
        "interval and unhealthy threshold.",
        "Listener detail -> backend servers: report each server's health "
        "status (normal / abnormal) and its port mapping "
        "(listener port -> backend port).",
        "On each backend ECS (customer-executed, read-only): "
        "`ss -ltnp` (Linux) or `netstat -ano` (Windows) and return the "
        "output lines around the health-check / backend port.",
        "On each backend ECS (customer-executed): `curl -v "
        "http://127.0.0.1:<backend-port><health-check-URI>` with an empty "
        "Host header equivalent (`-H 'Host: '`) and return the raw output.",
        "Listener detail -> access control (whitelist/blacklist): report "
        "whether it is enabled and which CIDRs it contains (verification "
        "for this branch is a known gap -- see references).",
    ],
    "real-client-ip": [
        "Report the full request path: client -> DNS/CDN -> which LB product "
        "(CLB / ALB / NLB, and its edition on the instance detail page) -> "
        "listener protocol/port -> backend port, or 'no load balancer'.",
        "For ALB/CLB layer-7 listeners: on the backend, log the received "
        "X-Forwarded-For / X-Real-IP request headers (e.g. an Nginx "
        "log_format including $http_x_forwarded_for) and return one sample "
        "log line.",
    ],
    "selection": [
        "Report the ALB instance edition shown on the console instance "
        "detail page (Basic / Standard / Standard with WAF) when an ALB is "
        "involved.",
        "Report the required protocol(s) and port or port-range the "
        "load balancer must forward (e.g. TCP 4021 control + passive data "
        "range 50000-50501 for FTP).",
    ],
    "scaling": [
        "ESS console -> scaling group -> detail: report whether a load "
        "balancer (CLB/ALB) listener or server group is attached to the "
        "scaling group.",
        "SLB console -> the listener's virtual server group / backend "
        "servers: report whether the scaled-out instance IDs appear there "
        "and their health status.",
    ],
    "eip-slb": [
        "EIP console: report which instance type the EIP is bound to "
        "(ECS instance / SLB instance / NAT) -- the script also lists EIP "
        "bindings it can see, but report both so they can be cross-checked.",
    ],
    "http-5xx": [
        "SLB/ALB console: report the listener protocol, the backend "
        "forwarded-to port, and the backend server group type/protocol "
        "(HTTP / HTTPS / gRPC) of the affected listener.",
        "On the backend (customer-executed): list which service listens on "
        "the forwarded-to port and which paths it serves (application "
        "route table or reverse-proxy location blocks), and return a "
        "sample of the access log for a failing request.",
    ],
    "handoff": [
        "No load-balancer-side self-check is needed: state the main demand "
        "and hand off with the read-only evidence this script already "
        "collected.",
    ],
    "other": [
        "Ask the customer (or re-state) the exact symptom sentence and any "
        "error string shown in the browser, console, log or curl output.",
    ],
}

# ---------------------------------------------------------------------------
# Rule knowledge (verdict text keyed by rule id)
# ---------------------------------------------------------------------------
# Every rule carries:
#   verdict : the conclusion sentence relayed to the customer
#   action  : what the customer does next (manual guidance only)
#   doc     : official documentation URL, or the empty string when the caliber
#             is ticket-derived and the official doc reference is still
#             pending (NEVER fabricate a URL -- see references/ files)
RULES = {
    "CERT-L4": {
        "verdict": (
            "The listener is a layer-4 (TCP/UDP) listener. Layer-4 "
            "listeners terminate no TLS, so no certificate is bound on the "
            "load balancer: the SSL certificate must be configured on the "
            "backend ECS application (Nginx / Tomcat / IIS / BT panel) "
            "that listens on the forwarded port."
        ),
        "action": (
            "Update the certificate inside the backend web-server "
            "configuration on each backend ECS, reload the service, then "
            "re-verify from the public side (browser / openssl s_client "
            "certificate view). Step guidance: "
            "references/slb-backend-diagnosis__listener-cert-placement.md"
        ),
        "doc": "",
        "source": "ticket caliber (T-46370FEF, T-03338C00); official SLB doc pending",
    },
    "CERT-L7": {
        "verdict": (
            "The listener is a layer-7 (HTTPS) listener: the certificate is "
            "managed on the listener itself. Replace the server certificate "
            "bound to the HTTPS listener in the SLB/ALB console (select the "
            "new certificate from the Certificate Management service list)."
        ),
        "action": (
            "Console-only change performed by the customer; afterwards "
            "re-verify the served certificate chain and expiry from the "
            "public side. Step guidance: "
            "references/slb-backend-diagnosis__listener-cert-placement.md"
        ),
        "doc": "",
        "source": "ticket caliber (T-46370FEF self-correction); official SLB doc pending",
    },
    "CERT-DEPLOY-VISIBILITY": {
        "verdict": (
            "The Certificate Management service instance list only shows "
            "load-balancer instances of listener types that accept a "
            "cert deployment (layer-7 HTTPS listeners). A CLB instance "
            "whose 443 entry is a TCP (layer-4) listener therefore never "
            "appears for one-click deployment -- this is expected "
            "behavior, not a sync failure."
        ),
        "action": (
            "Configure the certificate on the backends (rule CERT-L4) "
            "instead of deploying through the Certificate Management "
            "service."
        ),
        "doc": "",
        "source": "ticket caliber (T-46370FEF)",
    },
    "HC-NOT-LISTENING": {
        "verdict": (
            "The health-check port has no listening socket on the backend "
            "(console message: the health-check port on the backend server "
            "is not in a normal listening state). The load balancer probe "
            "cannot connect at all."
        ),
        "action": (
            "Customer starts the service or fixes its listen directive/port "
            "on the backend (manual), then re-checks listener health."
        ),
        "doc": "",
        "source": "ticket caliber (T-4923E710, T-0ED134F1)",
    },
    "HC-PORT-MISMATCH": {
        "verdict": (
            "The listener forwards / health-checks to a port different from "
            "the port the backend application actually listens on (typical "
            "after SMC migration or an 80->8080 style remap): the probed "
            "port answers nothing or answers with the wrong service."
        ),
        "action": (
            "Align backend port == application port (customer changes the "
            "listener/server-group config in the console themselves)."
        ),
        "doc": "",
        "source": "ticket caliber (T-4923E710, T-0ED134F1)",
    },
    "HC-EMPTY-REPLY": {
        "verdict": (
            "\"Empty reply from server\" on the health-check probe means "
            "the connection was accepted but the application closed it "
            "without an HTTP response -- typically probing an HTTPS-only "
            "port over plain HTTP, or a migrated Nginx config that rejects "
            "requests with an empty Host / raw-IP Host (default server "
            "closes or redirects to the old domain)."
        ),
        "action": (
            "Probe both shapes locally (plain HTTP to the port, and with "
            "the real Host header); point the health check at a plain-HTTP "
            "port that answers unknown Hosts with 200/404 -- not by "
            "dropping the connection. references/"
            "health-check-troubleshooting.md"
        ),
        "doc": "",
        "source": "ticket caliber (T-4923E710: HTTPS backend port 443 "
                  "health-checked over HTTP after SMC migration)",
    },
    "E502-BACKEND-UNHEALTHY": {
        "verdict": (
            "HTTP 502 from the load balancer means the request reached the "
            "LB but no healthy backend answered it: the backend process is "
            "not listening on the forwarded port, or it closed the "
            "connection."
        ),
        "action": (
            "Walk the health-check decision tree (listening socket -> port "
            "mapping -> local curl) before touching any LB config."
        ),
        "doc": "",
        "source": "ticket caliber (T-0ED134F1)",
    },
    "E404-ROUTE-MISSING": {
        "verdict": (
            "HTTP 404 (incl. \"WebSocket handshake: Unexpected response "
            "code: 404\") means a backend DID answer but has no route for "
            "the requested path: the forwarded-to port hosts the wrong "
            "service (e.g. a docker-proxy gateway without the /mqtt "
            "route) while the reverse proxy carrying that route listens "
            "on another port (443)."
        ),
        "action": (
            "Map each served path to its listening port on the backend, "
            "then have the customer align the listener's backend port "
            "with the service that actually answers the path."
        ),
        "doc": "",
        "source": "ticket caliber (T-B0B319C1)",
    },
    "ALB-BASIC-HTTPS-BACKEND": {
        "verdict": (
            "ALB Basic edition HTTPS listeners cannot attach a server group "
            "whose backend protocol is HTTPS (full-chain HTTPS is not "
            "supported on Basic): end TLS at the ALB listener and serve "
            "plain HTTP from the backend, or move to a higher ALB edition."
        ),
        "action": (
            "Customer confirms the ALB edition on the console instance "
            "detail page and adjusts the server-group backend protocol to "
            "HTTP (or plans an edition change; changes are done by the "
            "customer, never by this skill)."
        ),
        "doc": "",
        "source": "ticket caliber (T-B0B319C1, from the ticket summary; "
                  "dialogue partially truncated), official ALB doc pending",
    },
    "RIP-L7-XFF": {
        "verdict": (
            "Behind a layer-7 listener (CLB HTTP/HTTPS, ALB), the real "
            "client IP is carried in the X-Forwarded-For request header; "
            "the backend access log only shows it if the backend parses "
            "and logs the header (Nginx realip/log_format, IIS/other "
            "header-aware logging). The remote address alone will be the "
            "load balancer address."
        ),
        "action": (
            "Give the customer the backend log/header configuration steps; "
            "verify by a returned sample log line showing the visitor's "
            "real IP. references/slb-backend-diagnosis__real-client-ip.md"
        ),
        "doc": "",
        "source": "ticket caliber (T-7E731914)",
    },
    "RIP-NO-LB-LOCAL-PROXY": {
        "verdict": (
            "There is no load balancer in this chain: Nginx reverse-"
            "proxying to a local IIS/other service over 127.0.0.1 records "
            "the loopback address; CLB layer-7 XFF documentation does not "
            "apply. The fix is in the local proxy pair (pass the header and "
            "configure the front app / IIS logging to read it), not in any "
            "cloud product."
        ),
        "action": (
            "Treat as a local web-server configuration consultation; hand "
            "off to the web-service runtime tier when it goes deeper. "
            "references/slb-backend-diagnosis__real-client-ip.md"
        ),
        "doc": "",
        "source": "ticket caliber (T-0C44237A)",
    },
    "SEL-FTP": {
        "verdict": (
            "ALB is a layer-7 product for HTTP/HTTPS-class traffic only; it "
            "does not front FTP. For FTP (control port + a large passive-"
            "mode data port range) use NLB, which forwards port ranges at "
            "layer 4."
        ),
        "action": (
            "Guidance only: NLB listener covering control port and the "
            "passive data range, health check on the CONTROL port (not the "
            "data range), prefer FTP passive mode with the range open. If "
            "listing still fails, packet capture on the backend is needed "
            "-- hand off to a human. references/slb-backend-diagnosis__lb-selection-matrix.md"
        ),
        "doc": "",
        "source": "ticket caliber (T-B4BA68B7), official NLB/ALB doc pending",
    },
    "SEL-MULTI-ZONE": {
        "verdict": (
            "Production load balancing should spread backends across at "
            "least two availability zones of the same region; whether the "
            "extra cost is justified is a business decision, but single-Zone "
            "backends lose the zone-level fault tolerance the LB provides."
        ),
        "action": (
            "The script reports the actual zone spread of the given "
            "backends from DescribeInstances; the customer evaluates the "
            "architecture. "
            "https://help.aliyun.com/zh/ecs/user-guide/hablog.md"
        ),
        "doc": "https://help.aliyun.com/zh/ecs/user-guide/hablog.md",
        "source": "ticket caliber (T-7F098751) + ECS high-availability doc",
    },
    "SCALING-MUST-ATTACH-LB": {
        "verdict": (
            "Auto Scaling only creates instances -- traffic arrives only "
            "after the scaled-out instances are attached to the load "
            "balancer's backend (scaling group configured with the CLB/ALB "
            "server group, or images/manual attach). Creating ECS instances "
            "without attaching them to the LB leaves the origin server "
            "carrying all requests."
        ),
        "action": (
            "Check the scaling group's attached load balancer and the "
            "server-group membership + health of the new instances. "
            "references/slb-backend-diagnosis__ess-lb-integration.md"
        ),
        "doc": "https://help.aliyun.com/zh/ecs/user-guide/hablog.md",
        "source": "ticket caliber (T-0AF7B6D9, T-662BBFDC)",
    },
    "SCALING-SHARED-STATE": {
        "verdict": (
            "With multiple backends, application connections to "
            "127.0.0.1 / localhost databases or Redis break on every new "
            "instance: state must live on a shared reachable address "
            "(intranet IP of a dedicated data node, or managed RDS/Redis)."
        ),
        "action": (
            "Guide the customer to repoint application connection strings to "
            "the shared intranet address before scaling out. "
            "references/slb-backend-diagnosis__ess-lb-integration.md"
        ),
        "doc": "",
        "source": "ticket caliber (T-0AF7B6D9)",
    },
    "EIP-ON-SLB-FEE": {
        "verdict": (
            "An EIP bound to a load balancer (SLB) is NOT exempt from the "
            "EIP configuration (retention) fee; the fee waiver applies only "
            "to EIPs directly bound to a VPC-type ECS/ECI instance with the "
            "account quota at or below 2000. Billing attribution itself "
            "belongs to the billing tier."
        ),
        "action": (
            "This skill only states the rule caliber and lists the EIP "
            "binding facts it can see; for the bill itself hand off to the "
            "billing-attribution tier or a human ticket (see references/"
            "handoff-playbook.md)."
        ),
        "doc": "https://help.aliyun.com/document_detail/197103.html#cde7d1a2df7z4",
        "source": "ticket T-1D4D04B3 (agent quoted this FAQ URL; anchor "
                  "validity to be re-checked)",
    },
    "GAP-NO-LB-API": {
        "verdict": (
            "This skill has no verified load-balancer-side read API: "
            "listener protocols, port mappings, health-check configs, "
            "server groups, access-control lists and ALB editions are read "
            "ONLY from the customer's console self-checks."
        ),
        "action": (
            "Hand the customer SELF_CHECK list items; re-run this script "
            "with the returned values. Never guess an LB-side config."
        ),
        "doc": "",
        "source": "requirements doc section 3 contract gap",
    },
}

# ---------------------------------------------------------------------------
# Handoff table: main demand outside this tier -> sibling tier / channel
# ---------------------------------------------------------------------------
# "target" values are CANDIDATE tier names that follow the ECS naming family;
# the batch tier list was not available to verify them, so callers present the
# handoff DIRECTION and fall back to a human ticket instead of asserting an
# unconfirmed identifier to a customer (see references/slb-backend-diagnosis__handoff-playbook.md).
HANDOFF = {
    "access-block": {
        "signals": ["security group", "firewall", "waf", "port is closed",
                    "nc ", "tcpdump", "ddos"],
        "target": "area:access-block-layered",
        "note": (
            "Port-reachability / security-group-deny disputes (nc tests only "
            "the TCP handshake, tcpdump showing 0 packets) belong to the "
            "layered access-blocking tier."
        ),
    },
    "web-access": {
        "signals": ["website", "cannot open", "site down", "slow to load"],
        "target": "area:web-inaccessible-slow",
        "note": (
            "Site unreachable with no load balancer in the path (or a pure "
            "DNS / backend-app problem) belongs to the website-access tier."
        ),
    },
    "bandwidth": {
        "signals": ["bandwidth", "traffic spike", "iftop", "upload script",
                    "outbound traffic"],
        "target": "area:network-quality-bandwidth",
        "note": (
            "Public bandwidth / traffic anomaly attribution belongs to the "
            "network-quality tier; this skill only reports the metric "
            "last-datapoint facts as a lead."
        ),
    },
    "billing": {
        "signals": ["bill", "invoice", "refund", "charged", "arrears", "cost"],
        "target": "area:billing-attribution-bill-check",
        "note": (
            "Billing attribution is out of scope; only the EIP-on-SLB rule "
            "caliber stays here (rule EIP-ON-SLB-FEE)."
        ),
    },
    "performance": {
        "signals": ["cpu", "memory", "load average", "t5", "burstable",
                    "top ", "performance"],
        "target": "area:resource-bottleneck",
        "note": (
            "Instance-performance disputes (CPU spikes, burstable-credit "
            "questions, uneven per-node load at equal LB weight) belong to "
            "the performance tier. Host-machine metrics are never exposed "
            "to customers; say so explicitly. In-instance commands are "
            "customer-executed only."
        ),
    },
    "remote-conn": {
        "signals": ["ssh", "rdp", "workbench", "login", "connection dropped"],
        "target": "area:ssh-connection",
        "note": "SSH/RDP instability after ruling out the LB factor belongs "
                "to the remote-connection tier.",
    },
    "spec-change": {
        "signals": ["upgrade instance type", "change specification", "c9i",
                    "instance family", "cannot select"],
        "target": "area:spec-change-purchase",
        "note": (
            "Specification-change eligibility rules (e.g. e-series cannot "
            "change to c9i / 8-series) belong to the spec-change tier; only "
            "the cross-zone LB architecture sub-question stays here."
        ),
    },
    "ram-permission": {
        "signals": ["nopermission", "ram", "sub-account", "sub account",
                    "jushita", "policy"],
        "target": "area:ram-policy-diagnosis",
        "note": (
            "NoPermission.RAM-style errors are a permission tier matter; the "
            "requestID may not even belong to the current account. The "
            "Jushita open platform is administered separately -- submit via "
            "its own ticket entrance; cloud-side support cannot change it."
        ),
    },
    "intranet-dns": {
        "signals": ["container", "dns", "coredns", "tunl0", "internal resolve"],
        "target": "area:vpc-connectivity-check",
        "note": (
            "Container DNS reuse / intranet authoritative records pointing "
            "at an ALB private IP are VPC/DNS matters; the ALB here is only "
            "a resolution target."
        ),
    },
    "scaling-group": {
        "signals": ["scaling group config", "health check of scaling group"],
        "kind": "product-channel",
        "target": "the Auto Scaling (ESS) console and its own product support",
        "note": "Scaling-group-internal configuration (outside the LB "
                "integration) belongs to the ESS tier.",
    },
    "cert-deploy": {
        "signals": ["install certificate on nginx", "certificate on the server"],
        "target": "area:ssl-cert-deployment",
        "note": "Plain host-level certificate installation with no load "
                "balancer in the question belongs to the cert-deployment "
                "tier.",
    },
}

# ---------------------------------------------------------------------------
# Fixed calibers quoted by support agents in the source tickets (customer-safe,
# each with a ticket source; official doc where available)
# ---------------------------------------------------------------------------
FIXED_CALIBERS = [
    "Cloud monitoring does not expose host-machine (physical server) metrics "
    "to customers (ticket T-7D518A67).",
    "nc only proves the TCP handshake completed; it does not prove a service "
    "answers (ticket T-3C6E3D78).",
    "The Jushita open platform is administered separately from Alibaba Cloud "
    "support; use its own ticket entrance (ticket T-1D79BB54).",
    "EIP configuration-fee waiver applies only to EIPs directly bound to "
    "VPC-type ECS/ECI with quota <= 2000 (ticket T-1D4D04B3).",
    "Never send panel/instance passwords in plaintext in a ticket; if already "
    "sent, change them immediately (ticket T-46370FEF safety notice).",
]

# ---------------------------------------------------------------------------
# Inline boundary assertions (pure-function safety net; run at import time)
# ---------------------------------------------------------------------------
assert UA_TEMPLATE.startswith("AlibabaCloud-Agent-Skills/"), "UA template drift"
assert "{session-id}" in UA_TEMPLATE, "UA template must carry session-id"
assert DEFAULT_TIMEOUT > 0, "timeout must be positive"


def _handoff_entry_wellformed(spec):
    """A handoff names a sibling skill, or an explicitly marked product channel."""
    target = spec.get("target", "")
    if not target:
        return False
    if spec.get("kind") == "product-channel":
        return not target.startswith("alibabacloud-")
    return target.startswith("alibabacloud-")


assert set(HANDOFF) and all(_handoff_entry_wellformed(v)
                            for v in HANDOFF.values()), "handoff targets malformed"
_codes = {code for code, _ in SYMPTOM_KEYWORDS}
assert _codes <= set(SCENARIOS) | {"other"}, "triage code not in SCENARIO set"
