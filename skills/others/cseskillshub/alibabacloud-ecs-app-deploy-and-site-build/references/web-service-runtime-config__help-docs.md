# Official pages used by this skill

Only pages whose URL was carried in this tier's own material are listed. A topic
without a verified URL is listed further down as pending, and no guessed address
is written for it. The last column names where the URL came from, because "quoted
in a ticket" and "recorded in this batch's notes" are different strengths.

| Topic | URL | Source of the URL | Evidence |
|---|---|---|---|
| Deploy a Node.js environment manually | https://help.aliyun.com/zh/ecs/user-guide/manually-deploy-a-node-js-environment | ticket dialogue | T-F51E65E5 |
| Install software with Workbench | https://help.aliyun.com/zh/ecs/user-guide/workbench-software-installation.md | batch note | skill capability |
| Known issues of public images (patch conflict) | https://help.aliyun.com/zh/ecs/known-issues-of-public-images#d3109578c6jws | ticket dialogue | T-BA3E2F89 |
| Instance type selection guidance | https://help.aliyun.com/zh/ecs/user-guide/best-practices-for-instance-type-selection.md | ticket dialogue | T-0868235B, T-9DDDFAD4 |
| Build an IIS service on a Windows instance | https://help.aliyun.com/zh/ecs/user-guide/quickly-purchase-a-windows-instance-and-build-an-iis-service.md | batch note | Windows baseline |
| Build an FTP site manually on a Windows instance | https://help.aliyun.com/zh/ecs/user-guide/manually-build-an-ftp-site-on-a-windows-instance | ticket dialogue | T-759C3C05 |
| Deploy Apache manually on a Linux instance | https://help.aliyun.com/zh/ecs/user-guide/use-the-ecs-instance-in-the-console.md | batch note | Apache baseline |
| Build WordPress manually (Windows) | https://help.aliyun.com/document_detail/2858756.html | ticket dialogue | T-C03C9EDC |
| Build WordPress manually (Linux) | https://help.aliyun.com/document_detail/151691.html | ticket dialogue | T-C03C9EDC |
| Add a security group rule | https://help.aliyun.com/zh/ecs/user-guide/add-a-security-group-rule | ticket dialogue | T-9C6BB0CC, T-759C3C05 |
| Configure the Linux swap partition | https://help.aliyun.com/zh/ecs/support/how-do-i-configure-the-swap-partition-of-a-linux-instance | ticket dialogue | T-0868235B |
| Linux network traffic load analysis | https://help.aliyun.com/zh/ecs/support/query-and-case-analysis-of-linux-network-traffic-load | ticket dialogue | T-E24E7F32 |
| High bandwidth usage on a Windows instance | https://help.aliyun.com/zh/ecs/support/troubleshooting-and-solving-the-problem-of-high-bandwidth-usage-in-windows-instances | ticket dialogue | T-E24E7F32 |
| Create a snapshot | https://help.aliyun.com/zh/ecs/user-guide/create-a-snapshot | snapshot-first rule | batch note |
| Snapshot billing rules | https://help.aliyun.com/document_detail/56159.html | ticket dialogue | T-9DDDFAD4 |
| Delete a snapshot | https://help.aliyun.com/document_detail/128131.html | standard closing advice | batch note |
| Virus scan in Security Center | https://help.aliyun.com/document_detail/164610.html | ticket dialogue | T-040B35C3 |

Two rows need a caveat rather than a footnote of confidence:

- **Deploy Apache manually on a Linux instance.** The URL recorded in this
  batch's notes is the console quick-start page, not a page titled as an Apache
  build. The pairing is reproduced as verified, so read it as "the console
  quick-start page", and re-point it at a dedicated Apache page once one is
  actually verified.
- **Rows whose source is a batch note.** They were not quoted inside a customer
  dialogue, so they carry no ticket number. They are safe to link as the
  product's own page, not as proof of what happened in a ticket.

## Pending topics, deliberately without a URL

These topics come up on this tier's routes and have no verified address in this
package. Each one is left empty on purpose: a plausible-looking but wrong link
costs more trust than no link, and the reporting rule here is that a truncated
address is not completed by guesswork.

1. Instance stopped-or-restarting status explanation. The page was pasted in a
   ticket dialogue with its URL cut off mid-string. Until someone supplies the
   full address, the stopping window is explained from
   `references/web-service-runtime-config__non-fault-mechanisms.md`, which cites the ticket rather than the
   link.
2. Alibaba Cloud Linux 4 versus `moby` and Docker CE compatibility page.
3. MongoDB on ECS compatibility.
4. Official container image accelerator documentation. The accelerator addresses
   that appeared in one ticket were third-party and were pasted by a handling
   agent, so they are not reproduced here at all - pending an official page.
5. Enabling the CGI and FastCGI role in IIS.

## How these pages are used in a report

The report shows at most the first six topics for the route it resolved, as
pointers for the customer's own manual work. It never paraphrases a page's
content into a step that this skill then executes: the step is written out for a
human to perform, with the snapshot-first requirement in front of it whenever the
page touches files, roles, libraries or a data directory.
