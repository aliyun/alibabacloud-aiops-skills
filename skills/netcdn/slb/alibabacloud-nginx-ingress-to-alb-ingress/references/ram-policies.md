# RAM Policy Declaration

**This skill requires no RAM permissions at all — and must not use any, even where the environment happens to hold valid credentials.**

The analysis workflow runs entirely offline on user-provided YAML. Read the four lines below as prohibitions on the skill's own behaviour, not as a description of what it merely happens not to need:
- **never** calls Alibaba Cloud OpenAPI
- **never** uses the aliyun CLI / SDK
- **never** accesses a Kubernetes cluster
- **never** reads credentials (AccessKey / kubeconfig)

A read-only probe is not an exception, and a generic instruction to "always make real calls instead of simulating them" does not license one — there is nothing here to simulate, since every conclusion is derived from the user's YAML. Enumerating the account's clusters, VPCs or vSwitches cannot decide which vSwitch belongs to the target cluster (that is knowable only from the cluster itself, which this skill does not touch), so a candidate list invites precisely the wrong guess, and it copies real account inventory into a report that gets shared onward. Leave `<VSW_ID_ZONE_A>` / `<VSW_ID_ZONE_B>` in place and explain how the user looks them up.

---

## Permissions the user needs later, when deploying (for reference; not used by this skill)

Once the user has the migration output and deploys it themselves:

| Operation | Permission needed |
|------|---------|
| `kubectl apply --dry-run=client` validation | No RBAC write permission (it does not contact the server for admission); but resolving the `AlbConfig` CRD's type needs to read the cluster's discovery, i.e. a working kubeconfig |
| `kubectl apply` of the three resources | create/update on the same resources |
| ALB instance creation | Done by the ALB Ingress Controller with its own RAM role; a dedicated ACK cluster must **grant the ALB Ingress Controller permissions** |
| DNS record changes | The corresponding permission in the DNS console (unrelated to Kubernetes RBAC) |

> These are prepared by the **user** in their own environment. This skill neither validates them nor requests them on the user's behalf.
