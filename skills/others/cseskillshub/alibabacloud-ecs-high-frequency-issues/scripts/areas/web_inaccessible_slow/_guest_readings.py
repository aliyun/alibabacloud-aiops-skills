"""Turn an in-guest reading into a verdict, whether dispatched or pasted back.

The tool used to collect `ss -lntp` output and stop at "it is not yet a verdict",
which left the largest in-guest cause class permanently unconfirmed even when the
reading was already in hand. This module reads the reading: listeners, bind
address, packet filter and service state, and names only what the text proves.

Pure parsing. No I/O, no dispatch, no credential. A shape it cannot read stays
undecided instead of being guessed.
"""
import re

LISTEN_RE = re.compile(
    r"(?i)^\s*(?:tcp|tcp6|udp|udp6)?\s*(?:\S+\s+){0,3}?"
    r"(\d{1,3}(?:\.\d{1,3}){3}|\[[0-9a-f:]+\]|\*|::|0\.0\.0\.0):(\d{1,5})\b")
LISTEN_STATE_RE = re.compile(r"(?i)\bLISTEN(?:ING)?\b")
SOCKET_TOKEN_RE = re.compile(r"(\d{1,3}(?:\.\d{1,3}){3}|\[[0-9a-f:]+\]|::|0\.0\.0\.0|\*):(\d{1,5})")
IPTABLES_BLOCK_RE = re.compile(
    r"(?i)-A\s+(?:INPUT|IN_public\S*)\b[^\n]*?(?:--dport[s]?\s+(?:\d+[,: ]*)*%s\b|-p\s+tcp[^\n]*?--dport\s+%s\b)"
    r"[^\n]*?-j\s+(DROP|REJECT)")
FIREWALLD_PORTS_RE = re.compile(r"(?im)^\s*ports:\s*(.*)$")
FIREWALLD_SERVICES_RE = re.compile(r"(?im)^\s*services:\s*(.*)$")
SERVICE_DEAD_RE = re.compile(
    r"(?i)Active:\s*(?:inactive|failed|activating)|\b(?:dead|failed)\b[^\n]{0,20}\bnginx\b"
    r"|应用程序池[^\n]{0,12}(?:已停止|停止|Stopped)|\bStopped\b[^\n]{0,20}(?:AppPool|应用池)")
SERVICE_RUNNING_RE = re.compile(r"(?i)Active:\s*active\s*\(running\)|\bStarted\b[^\n]{0,16}(?:nginx|IIS)")
WIN_APPPOOL_RE = re.compile(r"(?i)(?:AppPool|应用程序池|应用池)[^\n]{0,24}(Stopped|已停止|停止)")


def _tested_ports(port):
    text = str(port or "")
    found = [int(value) for value in re.findall(r"\d{1,5}", text)]
    return [value for value in found if 0 < value < 65536] or [80, 443]


def listeners_in(text):
    out = []
    for line in (text or "").splitlines():
        if not LISTEN_STATE_RE.search(line):
            continue
        for match in SOCKET_TOKEN_RE.finditer(line):
            address, port = match.group(1), int(match.group(2))
            if port == 0:
                continue
            if address in ("0.0.0.0", "::", "*", "[::]") or address.startswith("127.") or address == "[::1]":
                out.append((address, port))
            elif re.fullmatch(r"\d{1,3}(?:\.\d{1,3}){3}", address):
                out.append((address, port))
    return out


def interpret(text, port, os_type="linux"):
    """Return {verdict, evidence, actions, listeners}. verdict may be 'undecided'."""
    body = text or ""
    ports = _tested_ports(port)
    sockets = listeners_in(body)
    evidence, actions = [], []
    result = {"verdict": "undecided", "evidence": evidence, "actions": actions,
              "listeners": sockets, "ports": ports}
    if not body.strip():
        return result

    service_dead = SERVICE_DEAD_RE.search(body) or WIN_APPPOOL_RE.search(body)
    service_running = SERVICE_RUNNING_RE.search(body)
    if service_dead:
        evidence.append("Service state in the reading: %s" % service_dead.group(0).strip()[:120])
        result["verdict"] = "service_stopped"
        actions.append("Start the web service (or the IIS application pool) and confirm it stays "
                       "up: read its status and the last error log lines first, so a crash loop "
                       "is not mistaken for a stopped service. Take a snapshot before any change "
                       "that touches configuration.")
        return result
    if service_running:
        evidence.append("Service state in the reading: %s" % service_running.group(0).strip()[:120])

    if sockets:
        evidence.append("Listening sockets read: %s"
                        % ", ".join("%s:%d" % (address, number) for address, number in sockets[:12]))
        for number in ports:
            bound = [address for address, bound_port in sockets if bound_port == number]
            if not bound:
                result["verdict"] = "no_listener"
                evidence.append("No socket is listening on the tested port %d." % number)
                actions.append("Start or reconfigure the web service so it listens on TCP %d, "
                               "then re-test from outside. A port with no listener answers with "
                               "a reset, which is what a browser shows as connection refused."
                               % number)
                return result
            if all(address.startswith("127.") or address == "[::1]" for address in bound):
                result["verdict"] = "loopback_only"
                evidence.append("Port %d is bound to %s only." % (number, ", ".join(bound)))
                actions.append("Change the service bind address for TCP %d from loopback to "
                               "0.0.0.0 (or the instance private address) and reload; a "
                               "loopback-only bind serves the instance itself and nobody else."
                               % number)
                return result
        blocked = _firewall_block(body, ports)
        if blocked:
            result["verdict"] = "guest_firewall"
            evidence.append(blocked)
            actions.append("Add an inbound allow rule for the tested port in the guest firewall "
                           "and reload it, keeping the existing rules intact; then re-test. The "
                           "cloud security group and the guest firewall are two independent "
                           "gates and both must admit the port.")
            return result
        result["verdict"] = "excluded"
        evidence.append("The tested port is listening on a non-loopback address and no guest "
                        "packet-filter block for it appears in this reading.")
        return result

    blocked = _firewall_block(body, ports)
    if blocked:
        result["verdict"] = "guest_firewall"
        evidence.append(blocked)
        actions.append("Add an inbound allow rule for the tested port in the guest firewall and "
                       "reload it, then re-test from outside.")
    return result


def _firewall_block(body, ports):
    for number in ports:
        pattern = re.compile(IPTABLES_BLOCK_RE.pattern % (number, number), re.I)
        hit = pattern.search(body)
        if hit:
            return "Guest packet filter drops TCP %d: %s" % (number, hit.group(0).strip()[:160])
    ports_line = FIREWALLD_PORTS_RE.search(body)
    services_line = FIREWALLD_SERVICES_RE.search(body)
    if ports_line is not None or services_line is not None:
        allowed = (ports_line.group(1) if ports_line else "") + " " + \
                  (services_line.group(1) if services_line else "")
        for number in ports:
            service_names = {80: "http", 443: "https"}.get(number, "")
            if str(number) in allowed or (service_names and service_names in allowed.split()):
                continue
            return ("firewalld active zone admits [%s] and does not admit TCP %d."
                    % (allowed.strip()[:120], number))
    return ""
