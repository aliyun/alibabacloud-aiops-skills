# Phase -2: Settle the SKU

> **Read this FIRST, before any other phase.** Nothing downstream can run without a settled SKU: Phase -1.2's
> bridging copy enumerates what the package contains, Phase -1.5 reads the SKU's product list, Phase 0.2b
> probes exactly that product set, and Phase 1 loads that SKU's yaml.
>
> - **Entry**: a deploy request arrived — **including a request that carries no package yet** (`帮我选个套餐`,
>   `哪个套餐合适`, `具体是哪个套餐`, `我想做个 X，用 OPC 套餐能实现吗`). A missing SKU is this phase's
>   reason to exist, never a reason to hand the question back to a general assistant.
> - **Exit**: one of the 7 legal SKU names is settled → go to Phase -1 (`preflight.md`).
> - **If no SKU can be settled**: STOP and wait. Entering this phase NEVER authorizes proceeding.
> - Owns: SKU recognition + the entire no-SKU recovery path (iron-rule #9). No other file restates this wording.

The 7 legal SKUs: `starter_webui` / `starter_app` / `lite_seed` / `lite_growth` / `lite_traction` / `pro_steady` / `pro_burst`.

## Step -2.1: Identify the SKU

```text
Extract the SKU name from the conversation context or user input
Validate it is one of the 7 legal SKUs
Invalid → run the "Advisor bootstrap" block below
(starter_webui no longer asks about the user's promo history — Phase 1.2.5's price inquiry decides the path automatically)

Strong-signal fast-path (aligned with the advisor dynamic-eval lesson: a weak model must not treat a clear signal as ambiguous):
  Any of the following strong signals → lock the SKU directly, skip the question, go to Phase -1 (preflight):
    - the user states a legal SKU name directly (e.g. "帮我开一个 lite_seed")
    - the advisor prescription already provided the sku field in context
  ⚠️ These are the ONLY two strong signals. A SKU name recalled from long-term memory, a daily note, or a
  previous session's summary is NOT one of them — it may be the residue of a round where the SKU was
  self-selected in violation of this gate, and reading it back would launder that mistake into fact.
  Do not name such a remembered SKU to the user, do not present it as "你上次选的", and do not let it seed
  the sizing conversation; at most treat it as a private hint that the user has deployed before. The SKU
  still has to be re-settled here from scratch.
  A token counts as stated no matter how the sentence is shaped: with no deploy verb ("starter_webui"),
  wrapped in a noun phrase ("帮我创建阿里云OPC套餐的lite_seed"), or phrased like an authoring task.
  NEVER split a token into ordinary words to re-read the intent (`lite_seed` is one package name, not
  "the seed of the lite package"), and NEVER read such a message as a request to edit this skill's own
  files just because the surrounding context mentions skill development.
  SKU missing or illegal (e.g. the user says only "帮我部署" with no SKU) → do NOT ask the user to
  pick a tier and do NOT improvise wording here: run the "Advisor bootstrap" block below, which owns
  the whole no-SKU path (availability check, install offer, restart guidance, fallback address).
  NEVER repeatedly re-confirm when a clear SKU already exists.

Self-sufficiency entry (deploy does not hard-depend on advisor context):
  deploy's **only hard dependency is the SKU name**. The advisor structured fields (scope_declaration /
  fallback_ecs_config / image / component removal) are all "use if present, else self-derive" optional enhancements:
    - advisor context present → prefer its fields
    - no advisor context (new session with a direct SKU name / cross-session) → do NOT stop or error,
      self-derive from deploy built-in defaults: image = image_families primary family,
      starter fallback = Step 1.2.5 built-in config, scope = iron-rule #23 built-in list,
      component removal = re-captured/confirmed at the Step 1.3 resource list.
```

## Advisor bootstrap: no SKU in the session (iron-rule #9)

This block owns the entire no-SKU path. It is the single source of truth for advisor availability, installation, and the install-address fallback; the SKU GATE in SKILL.md and iron-rule #9 both route here instead of restating the wording.

```text
Precondition: run this block ONLY when the conversation carries no legal SKU token AND no advisor
prescription is in context. Entering this block NEVER authorizes proceeding to any Phase — the
deployment stays stopped until the user supplies a SKU name. Inferring, guessing, or self-selecting a
SKU is forbidden here exactly as everywhere else, and offering to install advisor is subordinate to
that: an install offer is never a substitute for the user's own tier choice.

Step B.1: Determine advisor availability (three states; decide before saying anything)
  (a) callable                → advisor is available to you in this session, you can hand off now
  (b) on disk but not callable → the directory exists on disk, yet advisor is not available to you
  (c) absent                   → no such directory found

  On-disk check:
    find "$HOME" -maxdepth 4 -type d -name alibabacloud-opc-advisor -path '*/.*/skills/*' 2>/dev/null
  A hit means state (b); record that path as ADVISOR_DIR, since Step B.5 needs it. No hit means (c).

  Route: (a) → Step B.2    (b) → Step B.5    (c) → Step B.3

Step B.2: advisor callable → hand off, install nothing
  "我先带你把套餐定下来，定好了我就接着帮你开通。"
  Hand off to advisor. Never run the sizing questionnaire yourself.
  ⚠️ Wording: do NOT expose the internal tool topology to the user — words like "上游/下游/上游助手/
  advisor/skill" are internal-only. To the user this is one continuous assistant, not a chain of tools.
  This same one-liner is also the correct post-install continuation for Step B.4 (see B.5's in-session
  handoff branch).

Step B.3: advisor absent → locate the target skills directory
  Primary path (client-agnostic, needs no client lookup table): find where deploy itself is installed
  and place advisor as its sibling —
    find "$HOME" -maxdepth 4 -type d -name alibabacloud-opc-deploy -path '*/.*/skills/*' 2>/dev/null | head -1
    TARGET_DIR = that path with the trailing /alibabacloud-opc-deploy removed
  Fallback (primary returns nothing): enumerate the agent skills directories —
    find "$HOME" -maxdepth 3 -type d -name skills -path '*/.*' 2>/dev/null
      - exactly one hit → use it
      - several hits    → list them in plain language and let the user pick; NEVER pick silently
      - no hit          → Step B.6
  The `-path '*/.*'` filter is required: without it an ordinary repository that happens to contain a
  `skills/` directory gets picked up as if it were an agent directory.
  Always install into the skills directory resolved above (the tool-level location), NEVER into a
  project subdirectory — a project-level copy lands inside the user's own repository.

Step B.4: Ask once, then install
  Show what was found and what is about to happen, and wait for a yes. Writing into the user's tool
  directory without asking is forbidden:
    "开通前得先把套餐定下来——选套餐这步我这儿还缺个小工具，我直接帮你装上就行，
     装到 ${TARGET_DIR}，几秒钟。要我装吗？"
  User declines → Step B.6 (hand over the address and let them install it themselves).
  Anything that is neither a yes nor a no is NOT consent — a reply that only says they do not know
  which package to pick, a question back, or any answer that addresses something other than the
  install. Never read "the user wants help choosing" as "the user authorised a write into their tool
  directory": those are two separate permissions, and inferring the second from the first is the exact
  failure this gate exists to prevent. Re-send the one-liner once and stay on this step until the
  answer is an explicit yes or no. Do not clone, copy or create anything under the tool directory
  while you are still waiting.
  User agrees → run:
    TMP="$(mktemp -d)"
    git clone --depth 1 https://github.com/aliyun/alibabacloud-aiops-skills.git "$TMP/repo"
    mkdir -p "${TARGET_DIR}/alibabacloud-opc-advisor"
    cp -R "$TMP/repo/skills/computing/ecs/alibabacloud-opc-advisor/." "${TARGET_DIR}/alibabacloud-opc-advisor/"
  Then drop the staging copy, guarded so that only the freshly created mktemp path can ever be removed:
    [ -n "$TMP" ] && [ -d "$TMP" ] && case "$TMP" in "${TMPDIR:-/tmp}"*) rm -rf "$TMP";; esac
  Verify: test -f "${TARGET_DIR}/alibabacloud-opc-advisor/SKILL.md"
    verified → Step B.5
    any failure (git absent, network blocked, no write permission, verification fails) → say so plainly
    and go to Step B.6. Never fail silently, and never leave the user believing it succeeded.

Step B.5: files are on disk → hand off if it loaded in-session, else tell the user how to pick it up
  ADVISOR_DIR is whichever is set: the path recorded in Step B.1 (already on disk) or the
  ${TARGET_DIR}/alibabacloud-opc-advisor just created in Step B.4.
  First, re-check availability (Step B.1's callable test): a skill just installed in this session may
  already be loaded and callable right now.
    - Available in-session now (measured: QoderWork picks up a newly installed skill within the same
      session, no new conversation / no restart needed) → this is the preferred path: DO NOT tell the
      user to restart or open a new conversation. Just continue seamlessly with the Step B.2 one-liner
      ("我先带你把套餐定下来，定好了我就接着帮你开通。") and hand off in place.
    - Not yet callable, and the client is anything OTHER than QoderWork → the freshly added skill needs
      the tool to reload it. Say ONLY this (never narrate the mechanism):
      "装好了。你把工具重开一下再回来，我接着带你把套餐定下来、然后开通。"
  Then, if you did not hand off in-session, STOP and wait. Do NOT reinstall (the files are already
  there), do NOT poll in a loop, do NOT enter any Phase, and do NOT settle on a SKU yourself while waiting.
  When the user returns, re-run Step B.1 from the top.

Step B.6: fallback → hand over the install address
  "开通前得先把套餐定下来，选套餐这步需要装个小工具。你自己装一下：
   https://github.com/aliyun/alibabacloud-aiops-skills/tree/master/skills/computing/ecs/alibabacloud-opc-advisor
   （在 Qoder 这类工具里直接添加这个 Skill；其他 AI 工具就把这个地址发给它读）。
   装好后（若工具没自动认到，开个新对话或重开一下）回来找我，我接着带你把套餐定下来、然后开通。"
  Then STOP and wait.

Forbidden throughout this block: running the sizing questionnaire yourself, recommending a tier,
mapping a vague deploy request onto a SKU, and making the user guess a SKU name off the purchase-page
cards (the 4 cards do not map one-to-one to the 7 SKUs, so the user cannot report one accurately).
Also never narrate the mechanics of this block to the user — no talk of probing, gates, states, or
reloading; the user only ever sees the plain-language copy quoted above.
```
