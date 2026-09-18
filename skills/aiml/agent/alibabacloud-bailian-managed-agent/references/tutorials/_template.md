# Tutorial Template (copy this file to create a new tutorial)

> After adding a tutorial you **must** register a row in the "capability → tutorial mapping" of [index.md](index.md);
> if it introduces a new capability combination, also register it under "composition patterns".
> File naming: `NN-kebab-case-name.md` (e.g. `01-hello-agent.md`); the number encodes the recommended learning order.

---

# <Tutorial title: describe what the learner will build, not "introducing feature X">

| Item | Value |
| --- | --- |
| **Goal** | <what the learner can build afterwards — one sentence, verifiable> |
| **Capabilities involved** | <Agent / Environment / Deployment / Memory / Skill / Tool …> |
| **Difficulty** | Beginner / Intermediate / Advanced / Expert |
| **Prerequisites** | <bl installed and logged in / tutorial NN done / what account permissions or data are needed> |
| **Estimated time** | <n minutes> |
| **Source** | <where the original tutorial case came from + date> |

## Scenario

<One paragraph in business language describing the real problem this tutorial solves. Presales talks quote this directly.>

## Final artifacts

<What you end up with: an agents.yaml snippet, a conversational Agent, a scheduled task, a piece of integration code…>

## Steps

### 1. <Step name>

<What to do and why (explain only when non-obvious)>

```bash
<A command that can be copied and executed directly>
```

**Expected result**: <the output you should see>
**How to verify**: <which command / what observable fact confirms this step succeeded>

### 2. <Step name>

```yaml
# agents.yaml
<A config snippet that can be written to disk as-is — only the parts added/modified in this step, plus which node they sit under>
```

**Expected result**: <…>
**How to verify**: <…>

### 3. Preview and apply

```bash
bl managed-agent validate
bl managed-agent plan
# show the diff to the user; after confirmation:
bl managed-agent apply --yes
```

## FAQ

| Symptom | Cause | Fix |
| --- | --- | --- |
| <error message or abnormal behavior> | <root cause> | <the concrete action> |

## Going further

- Want to go further with <X> → <tutorial link>
- Integrate into a business system → [../integration/patterns.md](../integration/patterns.md)
