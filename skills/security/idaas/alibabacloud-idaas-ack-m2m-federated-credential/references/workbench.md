# User-run Kubernetes commands

The user runs Kubernetes commands in the target cluster's terminal. The agent runs Alibaba Cloud OpenAPI calls with the approved CLI identity, handles EIAM and PAM configuration, and generates the Pod probes. ACK Workbench is a supported terminal. Open the selected cluster in the ACK console and choose **Manage Cluster via Workbench**. The session loads the user's kubeconfig. Check access for that session's identity before providing workload commands. [ACK Workbench guide](https://help.aliyun.com/zh/ack/serverless-kubernetes/user-guide/use-kubectl-on-cloud-shell-to-manage-ack-clusters-1690962464408) and [check and grant ACK RBAC](preparation.md#kubernetes-access-by-login-identity)

Hand over copy-ready commands with the confirmed values filled in and shell-quoted. Templates below use variables for clarity. The user shares only the requested status, metadata or probe JSON. The verification container needs Python 3.9+ and network access to the EIAM token endpoint and, for STS, the regional EIAM Developer API and STS endpoints.

## Select and prepare the workload

Offer the existing namespace choices for user-run Kubernetes. A request for a new test namespace uses [the agent-run creation path](preparation.md#create-a-new-test-namespace), with a fresh Pod and dedicated ServiceAccount. When the user needs to discover existing namespaces and has `list` access, use the command below. For a known namespace, use the named read after the table. Ask for the name of each new Pod or ServiceAccount before generating a write command. Select the intended container explicitly.

~~~bash
kubectl --request-timeout=10s get namespaces -L pod-identity.alibabacloud.com/injection
~~~

| User's choice | Workbench sequence |
| --- | --- |
| Existing namespace and existing Pod | Select the namespace and Pod. Read the Pod's ServiceAccount and select a ready Python container. Confirm that the actual Pod already has the RRSA projection. |
| Existing namespace and new Pod | Select the namespace and the ServiceAccount, or create a dedicated ServiceAccount. Use the explicit token projection below. |

After namespace selection, read the namespace by name. Use the ServiceAccount and Pod lists only when the operator needs to discover those resources. For a known Pod, read it by name to obtain its actual ServiceAccount, then read that ServiceAccount by name.

~~~bash
kubectl get namespace "$NS" -L pod-identity.alibabacloud.com/injection
kubectl -n "$NS" get serviceaccounts -o 'custom-columns=NAME:.metadata.name,RRSA_ROLE:.metadata.annotations.pod-identity\.alibabacloud\.com/role-name'
kubectl -n "$NS" get pods -o 'custom-columns=NAME:.metadata.name,SA:.spec.serviceAccountName,PHASE:.status.phase,CONTAINERS:.spec.containers[*].name'
~~~

### Create a Pod with an explicit token projection

For a new Pod, use the cluster's ACK OIDC issuer and a [Kubernetes ServiceAccount token projection](https://kubernetes.io/docs/concepts/storage/projected-volumes/#serviceaccounttoken-projected-volumes). Use a dedicated ServiceAccount without a role annotation, or reuse an unannotated ServiceAccount. The webhook skips ServiceAccounts without the role annotation, even in an injection-enabled namespace. The PAM role for an optional STS exchange remains selected separately. [ACK webhook configuration](https://help.aliyun.com/en/ack/product-overview/ack-pod-identity-webhook)

Confirm the namespace, ServiceAccount, Pod and Python image before writing. Create the ServiceAccount only when requested. Use a Python image the target node can pull. Continue only after each approved create succeeds and ask for a new name if a create returns `AlreadyExists`. Use an approved integer lifetime for the test Pod.

~~~bash
# Run this only for a new dedicated ServiceAccount.
kubectl -n "$NS" create serviceaccount "$SA"
# Render the manifest below with the approved names and image.
kubectl -n "$NS" create -f "$POD_MANIFEST"
kubectl -n "$NS" wait --for=condition=Ready "pod/$POD" --timeout=180s
~~~

~~~yaml
apiVersion: v1
kind: Pod
metadata:
  name: APPROVED_POD_NAME
spec:
  serviceAccountName: APPROVED_SERVICE_ACCOUNT
  automountServiceAccountToken: false
  restartPolicy: Never
  activeDeadlineSeconds: 3600
  containers:
    - name: python
      image: APPROVED_PYTHON_IMAGE
      command: ["sleep", "3600"]
      env:
        - name: ALIBABA_CLOUD_OIDC_TOKEN_FILE
          value: /var/run/secrets/idaas.alibabacloud.com/token
      volumeMounts:
        - name: idaas-oidc-token
          mountPath: /var/run/secrets/idaas.alibabacloud.com
          readOnly: true
  volumes:
    - name: idaas-oidc-token
      projected:
        sources:
          - serviceAccountToken:
              audience: sts.aliyuncs.com
              expirationSeconds: 3600
              path: token
~~~

Before running the probe, check the selected Pod's actual ServiceAccount and Running status, the selected container's Ready status, the token environment variable and its `idaas-oidc-token` mount, and the projected audience `sts.aliyuncs.com`. Pass `--token-source projected` to preflight, configure and verify. For an existing webhook-injected Pod, use the default mode and check the namespace label, ServiceAccount role annotation and `rrsa-oidc-token` mount. Return only selected metadata fields. Fill in `demo-container` and `VOLUME_NAME` below.

~~~bash
kubectl -n "$NS" get pod "$POD" -o 'custom-columns=SA:.spec.serviceAccountName,PHASE:.status.phase,READY:.status.containerStatuses[?(@.name=="demo-container")].ready,ENV_NAMES:.spec.containers[?(@.name=="demo-container")].env[*].name,MOUNTS:.spec.containers[?(@.name=="demo-container")].volumeMounts[*].name,AUDIENCE:.spec.volumes[?(@.name=="VOLUME_NAME")].projected.sources[*].serviceAccountToken.audience'
~~~

For an image pull failure, ask for the selected Pod's events and distinguish scheduling, registry connectivity, authentication and missing tags. If an approved test Pod needs an image change, compare `.status.containerStatuses[].imageID` against the requested image and check that the selected container is ready. A Ready condition immediately after an image update can describe the old container. [ACK Pod troubleshooting](https://help.aliyun.com/zh/ack/ack-managed-and-ack-dedicated/support/pod-troubleshooting)

## Run preflight and verify issuance

Keep one Skill session ID for the cloud and Workbench steps. Construct `scope_args` as in [the execution workflow](workflow.md) and set `POD` and `CONTAINER` to the confirmed values. On the agent, generate the first command:

~~~bash
python3 scripts/ack.py preflight "${scope_args[@]}" --pod "$POD" --container "$CONTAINER" --workbench
~~~

Extract the decoded `workbench_command` field and give the complete shell block to the user. The command executes the packaged probe in the chosen Pod and checks the mounted token claims and EIAM token endpoint. Save the exact successful JSON returned by the user in a private `WORKBENCH_RESULT` file. It identifies this session, cluster, instance, namespace, ServiceAccount, Pod and container. A metadata listing, readable token file or generated command leaves preflight pending. Repeat the Kubernetes metadata checks and regenerate the preflight result after changing the workload.

Run the approved `configure` command from [the execution workflow](workflow.md), replacing its `--context` argument with `--workbench-result "$WORKBENCH_RESULT"` and passing the exact `--container`. Keep the result file and state on the agent. The helper rechecks the cloud prerequisites and consumes the user-run result. If a new workload falls outside an existing credential's scope, show the new binding. With approval, configure a new application credential or use the owner's credential update process to rebind an existing one. For a rebind, confirm its enabled state, trust source, Kubernetes fields and compiled condition. The previous workload loses access to new tokens through that credential. The helper's configure command creates a credential and scopes its state to the selected workload. [EIAM credential update](https://help.aliyun.com/en/idaas/eiam/developer-reference/api-eiam-2021-12-01-updateapplicationfederatedcredential)

Run `verify` locally with the same `--workbench-result`, `--state` and workload arguments. If the user also wants STS, select the PAM role and obtain approval before running `grant` as documented in the execution workflow. Run `verify --sts` afterward.

~~~bash
python3 scripts/ack.py verify "${scope_args[@]}" --pod "$POD" --container "$CONTAINER" \
  --workbench-result "$WORKBENCH_RESULT" --state "$STATE" --sts
~~~

Give the decoded `workbench_command` to the user and wait for its actual output. Mark M2M verified only when `m2m.status` is `verified`. Mark STS verified only when `sts.status` is `verified` and the result names the approved role and contains identity-check evidence. The probe checks the assumed-role identity using the newly issued STS credentials. Retain provided request IDs and report errors by stage. Keep RRSA assertions, bearer tokens, kubeconfig and STS credential values in their execution environments.
