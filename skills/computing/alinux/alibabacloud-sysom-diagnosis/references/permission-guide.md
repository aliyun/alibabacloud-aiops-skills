# Documentation Entry (sysom-diagnosis)

To avoid repetition between **permission** and **diagnosis contract** docs, follow a single-source reading path by topic.

| Need | Document |
|------|------|
| **precheck, AK/RAM Role, three requirements, scenario matrix A-K, credential/activation issues** | [openapi-permission-guide.md](./openapi-permission-guide.md) |
| **RAM minimum permissions, action mapping, policy templates (directly reusable for custom policies)** | [ram-policies.md](./ram-policies.md) |
| **Current/remote target selection (mandatory), InvokeDiagnosis request body, `region`/`instance`, metadata completion; public CLI path is `memory ... --deep-diagnosis`** | [invoke-diagnosis.md](./invoke-diagnosis.md) |
| **Deep-diagnosis business errors** (e.g. `InvalidParameter`, `instance not found`) | [invoke-diagnosis.md](./invoke-diagnosis.md) and this section notes; trust CLI **`error`** / **`data.diagnosis_target`** / **`data.read_next`** / **`data.remediation`** |
| **ECS metadata URLs, common curl examples, IMDS** | [metadata-api.md](./metadata-api.md) |
| **`params` fields for each `service_name`** | [diagnoses/README.md](./diagnoses/README.md) → corresponding `*.md` |
| **Memory-domain quick-entry routing** | [memory-routing.md](./memory-routing.md) |
| **Skill capability overview** | [SKILL.md](../SKILL.md) |

The agent should prioritize **credential and activation** handling based on **`precheck` JSON** `data.guidance` (and `data.remediation`).  
For **deep diagnosis** (`memory ... --deep-diagnosis`) business errors, refer to [invoke-diagnosis.md](./invoke-diagnosis.md) plus returned **`error` / `data`**.

Do **not** collect AccessKey/Secret in chat.  
On auth failure, guide users to run **`./scripts/osops.sh configure`** under **`sysom-diagnosis/`** (skill root).  
If current Bash has no PTY and cannot accept interactive input, refer to **`data.guidance.credential_policy`**.
