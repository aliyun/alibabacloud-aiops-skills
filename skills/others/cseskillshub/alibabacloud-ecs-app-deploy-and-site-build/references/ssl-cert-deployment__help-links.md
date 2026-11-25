# Verified help-document links (the only URLs this skill may quote)

Every URL below was either an aliyun help-search hit for this tier or
appears verbatim in a support-ticket transcript listed in the confirmed
requirements document. Where a needed document was NOT hit by the search,
this file says so explicitly instead of guessing a URL — the agent must do
the same: never invent documentation addresses.

## Core deployment reference

| Topic | URL | Relation |
| --- | --- | --- |
| Deploy an SSL certificate to enable HTTPS on ECS | https://help.aliyun.com/zh/ecs/user-guide/ssl.md | primary guide for the deployment (branch T2) console paths |

## Snapshot backup references (used with the snapshot-first notice)

These links were sent to customers inside the source tickets, in exactly
this create / billing / delete trio:

| Topic | URL |
| --- | --- |
| Create a snapshot | https://help.aliyun.com/document_detail/25455.html |
| Create a snapshot of a disk (guide) | https://help.aliyun.com/zh/ecs/user-guide/create-a-snapshot-of-a-disk |
| Snapshot billing | https://help.aliyun.com/document_detail/56159.html |
| Snapshot billing (product overview) | https://help.aliyun.com/zh/ecs/product-overview/snapshots-1 |
| Delete a snapshot | https://help.aliyun.com/document_detail/128131.html |

## Handoff-adjacent self-service references

| Topic | URL | Used when handing off |
| --- | --- | --- |
| Download a domain name certificate (registration proof, not TLS) | https://help.aliyun.com/zh/dws/user-guide/download-a-domain-name-certificate | ticket asks "download my certificate" but means the domain registration document |
| Self-service center: query the data center address of an instance | https://smartservice.console.aliyun.com/service/self-service-center/search?questionId=27082&trackFrom=searchResult | qualification or compliance material requests |

## Secondary background (weak relevance, cite only if asked)

| Topic | URL | Note |
| --- | --- | --- |
| Access cloud services over the internal network or a dedicated line | https://help.aliyun.com/zh/ecs/user-guide/access-the-cloud-through-the-private-network.md | egress-path background only; NOT about website certificates |

## Gaps — flagged, not filled

The following references were needed by this tier but NOT hit by the
verified search; they must be supplied before they can ever be quoted:
official pages for the certificate service free-quota rules and the
V1-to-V2 transition, the DV phone-validation contact rules, the per-server
certificate deployment guides for nginx and IIS, the security-group
outbound-rules page, and the third-party toolchain docs (acme.sh, certbot,
BaoTa, 1Panel, Posh-ACME). Until then the skill answers those points from
references/ssl-cert-deployment__aliyun-cert-service-faq.md WITH the confidence tag, or says the
console page is the authority. No fabricated URLs, ever.
