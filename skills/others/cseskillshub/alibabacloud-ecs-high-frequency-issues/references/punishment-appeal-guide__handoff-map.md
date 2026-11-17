# Handoff Map — identify, say the sentence, refer out

This skill covers ONLY the punishment / rectification / unblock-appeal
symptom area. The neighboring areas below repeatedly collide with it in real
tickets. Recognition is part of this skill's job; implementation is not.
When a case matches, state the boundary sentence, refer to the target, and
stop expanding scope.

| Customer signal | Actual area | Refer to | Boundary sentence (adapt wording, keep the meaning) |
|-----------------|-------------|----------|-----------------------------------------------------|
| DDoS attack, blackhole status, anti-DDoS unblocking | attack & blackhole handling | area:attack-blackhole-diagnosis | "Blackhole and anti-DDoS release is a separate mechanism, not a violation punishment; the blackhole diagnosis skill covers it." |
| Instance will not start / stuck mid-state, no notice involved | instance state | area:instance-state-diagnosis (or area:instance-start-stop-anomaly) | "Nothing in the evidence shows a platform action; this is a plain start/stop fault." |
| General ECS fault triage without any violation/risk wording | overall diagnosis | alibabacloud-ecs-diagnose | "No punishment signal present; the general diagnosis skill is the right entry." |
| Outage explained by security-group rules alone | reachability / access block | area:access-block-layered | "The read-only facts show a configuration gap, not a platform disposal." |
| Expansion not effective / partition not grown | disk expansion | area:disk-expand-diagnosis | "Capacity-change behavior is a different area; no disposal involved." |
| Slow disk IO / performance below spec | disk IO | area:resource-bottleneck | "Performance is not a punishment question." |
| Deep virus cleanup / intrusion forensics inside the guest | host intrusion | area:host-intrusion-cleanup | "This skill supplies the rectification checklist; the hands-on cleanup area takes it from here, snapshot first." |
| Port 25 mail sending, mass mailing, SMTP errors | email sending | adjacent email-sending / port-25 area | "Outbound 25 is the anti-spam policy area; applications are evaluated there, not here." |
| ICP filing / public-security filing procedure | filing | area:icp-filing-guide | "The filing procedure itself is the filing area; this skill only covers filing numbers as appeal materials." |
| Forgot password / lost key pair / cannot log in to the OS | guest login | area:login-credential-repair | "Login-credential repair is not an account action; unless a freeze notice exists." |
| Simple Application Server (lightweight) instance "banned" | product boundary | the dedicated lightweight-server area | "That is a different product's disposal channel; this ECS skill will not read its resources." |
| Refund / compensation / "just give me money back" | commercial | manual ticket (Billing/Support) | "Commercial requests are outside this read-only skill; the console ticket entry is the path." |

## Special cases seen in tickets

- **Supervisory blocking of tunnel protocols (e.g. self-hosted VPN on
  UDP 443)**: originates above the cloud platform; nobody at the cloud side
  can lift it. Fixed talk plus compliant alternatives: VNC / Workbench
  login, a bastion host, or a managed VPN gateway product.
- **Domain registered elsewhere got suspended by its registrar**: not an
  Alibaba Cloud disposal; check the WHOIS/registrar notice and refer.
- **"Unreachable from the mainland" without a notice**: run the read-only
  verification here; if the instance is normal and no notice exists, the
  claim is unverified — ask how the test was done before routing further.
- **Mixed tickets** (content violation plus expired domain plus weak
  passwords): resolve the punishment area first (it blocks everything),
  then hand the leftovers to their areas one by one.

## Fixed handoff format in reports

Every report line in the handoff section is emitted as:

`* <boundary sentence> -> <target area>`

so the final answer can relay it without re-interpretation.
