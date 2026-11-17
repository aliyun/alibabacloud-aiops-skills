# Official Help Links and Entry Points

Every URL below comes from injected evidence: either cited by the support
engineer inside a real ticket conversation, or returned by the official help
search for this tier. Verification status is marked per row - forward a
"ticket-cited" link only with the note that it was used by support engineers
in real conversations, and re-check availability when in doubt. This skill
only SHOWS links; it never submits forms, places orders or opens sessions on
the customer's behalf.

## Verified this round (official help search hit)

| Topic | URL |
|---|---|
| Build a website on ECS (SaaS-to-self-built handoff, general site setup) | https://help.aliyun.com/zh/ecs/user-guide/build-a-website.md |
| Filing-server conditions: subscription billing, purchased length longer than 3 months including renewals, unrelated to usage time and remaining term; free trial excluded, pay-as-you-go must convert first | https://help.aliyun.com/zh/icp-filing/basic-icp-service/user-guide/icp-filing-server-access-information-check |

## Ticket-cited (used by support engineers in the representative tickets)

| Topic | URL | Cited in |
|---|---|---|
| Server conditions that support ICP filing | https://help.aliyun.com/knowledge_detail/36891.html | T-C097A6CB |
| Filing server access information check | https://help.aliyun.com/zh/icp-filing/basic-icp-service/user-guide/icp-filing-server-access-information-check | T-C097A6CB |
| Filing butler (paid handled filing service) | https://gs.aliyun.com/product/butler | T-C097A6CB |
| Manage security-group rules | https://help.aliyun.com/zh/ecs/user-guide/manage-security-group-rules | T-63E5332F |
| Domain holder transfer (real-name change) | https://help.aliyun.com/knowledge_detail/35816.html | T-2E81A6EC |
| ECS instance ownership-transfer conditions (VPC type) | https://help.aliyun.com/document_detail/151401.html | T-2E81A6EC |
| ECS ownership-transfer operation manual | https://help.aliyun.com/knowledge_detail/281188.html | T-2E81A6EC |
| Refund rules | https://help.aliyun.com/document_detail/116043.html | T-2E81A6EC |
| MLPS / security-compliance material application form | https://page.aliyun.com/form/act294450682/index.htm | T-0631D05C, T-96F0322C |
| ECS purchase page | https://www.aliyun.com/product/ecs | T-C097A6CB |
| Simple Application Server purchase page | https://www.aliyun.com/product/swas | T-C097A6CB |
| Promotion page | https://www.aliyun.com/benefit/select/cloud-discount | T-C097A6CB |

## Ticket-cited, handoff-only (server-side scenarios outside this skill)

| Topic | URL | Note |
|---|---|---|
| Install IIS and FTP on a Windows instance | https://help.aliyun.com/zh/ecs/user-guide/how-to-install-iis-and-ftp-services-on-windows-instances | Cited in T-B57F5477; route with the server-side handoff |
| .NET Framework 3.5 installation failure on Windows Server 2012 R2 and later | https://help.aliyun.com/zh/ecs/support/how-do-i-solve-the-problem-that-the-net-framework-3-5-or-language-pack-cannot-be-installed-on-windows-server-2012-r2-and-later-instances | Cited in T-B57F5477; URL reconstructed from a partially redacted source - verify before forwarding |

## Console entry points

The script prints these under "Console entry points"; it never operates them
for the customer.

| Entry | Path |
|---|---|
| ICP Filing console | Console navigation: the ICP Filing console is where the customer reads the live filing order state and the service-code inventory. No URL for it appears in the ticket evidence or the help search this round, so do not forward a guessed address - send the customer to the console via the Alibaba Cloud console search for "ICP Filing". |
| Security-group rules | `ecs.console.aliyun.com` -> Network & Security -> Security Groups -> target group -> Inbound rules. The script prints this path as a template with `{region}` and `{groupId}` placeholders; substitute the values from the report yourself. |
| Alibaba Cloud DNS console | Console navigation: open the DNS console from the Alibaba Cloud console, select the domain, check the apex `@` record. The tickets name the console (Alibaba Cloud DNS) but contain no URL, so none is listed here as verified. |

## Known documentation gaps (do not fabricate links for these)

The following topics had NO help-search hit this round and no ticket-cited
document; answer them only from the evidence-marked wordings in
`references/icp-filing-guide__filing-rules-faq.md`, with the specialist-confirmation caveat:

- The end-to-end ICP filing process document.
- Filing service-code refund rules (the "unused codes refundable, consumed
  codes not reusable" wording comes from engineer statements in tickets
  T-C097A6CB / T-2E81A6EC, not from a retrieved official document).
- Access-filing (new access provider) migration document.
- Public-security filing guidance.
