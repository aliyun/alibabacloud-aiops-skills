# SKU Sizing Questionnaire — Pre-Engagement Scale Assessment

> When the advisor receives a "want to deploy / go live / make it accessible" request, this questionnaire MUST be completed before Step 2. **Jumping directly to a recommendation is forbidden.**

## 1. User-Facing Questions (2) + Inference (5)

> The advisor asks the user only **2 questions**, and only when the answer is not already stated in the prompt. The other 5 internal fields are **inferred** from the project description. All 7 internal fields (Q1_pv / Q2a / Q2b / Q3 / Q4 / Q5 / Q6) are still filled for the deploy-side YAML (§6) — the compression is user-facing only, the deploy contract is unchanged.

### Asked (only if the prompt does not already contain the answer)

| # | Question (plain-language, Chinese sample) | Options | Drives |
|---|------------------------------------------|---------|--------|
| **Q-scale** | `高峰期那一分钟内，大概多少人同时打开？` with lifestyle anchors: `朋友圈点赞 ≤15` / `小红书爆款 15-80` / `头部直播 80-200` / `大流量 200+` | ≤15 / 15-80 / 80-200 / 200+ / burst | lite/pro tier (merged Q1 PV + Q3 concurrent) |
| **Q-userdata** | `有没有用户注册登录/付款，或者用户上传内容（图片/视频/文字）？` | Yes / No | Yes → lite_seed floor + 38-item hardening checklist (merged Q2a registration/payment + Q2b upload) |

### Inferred (NOT asked as blocking questions)

| Internal field | Inference source |
|---|---|
| Q4_public | `让朋友/公开访问` → Yes; `自己/团队用` → No |
| Q5_account_type | OPC default `personal_real_name` + footnote `如是企业账号请告知（影响发票/备案主体）`; if user says `公司账号` → `company_real_name`; if truly unclear → `unknown` + guide to console (still no SKU block — see §5) |
| Q6_vlm | VLM keyword dictionary (§3); hit → Yes (lite_growth floor per iron-rule #32) |
| Q1_pv / Q3_qps | If the prompt states a scale signal (e.g., `几百人同时在线` → 80-200), map it to the internal buckets — do not re-ask. If not stated → ask Q-scale. |
| Q2a / Q2b split | When Q-userdata=Yes, infer which applies from the description (`注册/登录/付款` → Q2a; `上传/发帖/传图` → Q2b) for the hardening specifics. |

### Rule: infer stated, ask missing

- If the prompt already states a signal, **use it — do not re-ask**. E.g. `用户注册登录` → Q-userdata=Yes; `植物识别` → Q6=Yes; `几百人同时在线` → Q-scale=80-200.
- Ask Q-scale / Q-userdata **only when the prompt lacks that signal**.
- **Never fabricate a missing high-stakes field** (Q-scale, Q-userdata) — if missing, ask it. Silent mid-tier default is forbidden (§5).
- Q4/Q5/Q6 are never blocking — inferred/defaulted, with the assumption surfaced in the prescription.

### Key Design Notes
- Q2a (registration/payment) + Q2b (upload) are merged into Q-userdata for the user; they are still separate internal fields because they trigger different hardening (registration → CAPTCHA/password hashing; upload → OSS private ACL/content moderation). The split is inferred from the description.
- Q1 (PV) + Q3 (concurrent) are merged into Q-scale; concurrent is the primary axis (RDS/CPU), PV is derived for bandwidth/CDN granularity.
- The hardening checklist is output only when Q-userdata=Yes (or Q7-Q10=Yes per §4) — **never imposed if unchecked**.

## 2. SKU Recommendation Boundaries

Inputs: Q-scale (asked or inferred) + Q-userdata (asked or inferred) + Q6_vlm (inferred from §3 keywords) + Q4_public (inferred).

| Trigger (Q-scale + Q-userdata + inferred Q6/Q4) | Recommend SKU | Forbidden |
|---|---|---|
| Q-scale ≤15 + Q-userdata=No + Q6=No (no AI, personal use/portfolio) | `starter_webui` (+ ICP guidance if Q4=Yes) | starter_app (Token Plan wasted) |
| Q-scale ≤15 + Q-userdata=No + product calls text AI (chat/bookkeeping/resume, no VLM) | `starter_app` | — |
| Q-userdata=Yes (registration/payment OR upload) | Floor ≥ `lite_seed` (RDS for accounts + OSS for uploads) + 38-item hardening checklist | starter_* (no independent RDS/OSS) |
| Q-scale = 5-15 (no VLM, no user-data) | `lite_seed` | starter_* (insufficient resources) |
| Q-scale = 15-80 (no VLM) | `lite_growth` | starter_*, lite_seed |
| Q6=Yes (VLM keyword hit: recognition/detection/generation) | Floor `lite_growth` (per iron-rule #32) | starter_*, lite_seed (VLM needs more than seed) |
| Q-scale = 80-200 | `lite_traction` | starter_*/lite_seed/lite_growth |
| Q-scale = 50k-100k PV / 200+ steady | `pro_steady` | lite_* (insufficient high-availability) |
| Q-scale = burst (livestream/flash-sale/campaign) | `pro_burst` | pro_steady (no elasticity) |
| Q-scale = >1M PV / 80+ person team (inferred from prompt) | Escalate to commercial line — OPC declines | All SKUs |

**Conflict rule (take-the-higher-tier):** when Q-scale and inferred Q6/Q-userdata suggest different tiers, **take the higher tier**. Q3 (concurrent, from Q-scale) is the primary axis for RDS/CPU; Q1 (PV, derived) for bandwidth/CDN. The Q-scale buckets above are the governing mapping. Chinese rule name (zh-CN):

```text
就高不就低
```

## 3. VLM/Media Keyword Dictionary (inline at advisor Step 2)

If any of the following keywords appear in the user's description → default Q6=Yes → starter_* forbidden:

```
赛事 / 直播 / 视频 / 录播 / 短视频 / 流媒体 / 直播带货
图像识别 / 图片识别 / 图像分类 / 目标检测 / OCR / 人脸识别 / 商品识别 / 植物识别 / 动物识别
可视化 / 大屏 / Dashboard / 数据看板 / BI 报表
战报 / 解说 / 字幕生成 / 摘要生成 / 总结生成 / 标签生成
聊天机器人 / 智能客服 / 知识问答 / RAG / 向量检索 / Embedding
AI 绘画 / 文生图 / 图生图 / SD / Midjourney / 视频生成
推荐 / 算法 / 排序 / 模型推理 / GPU 推理 / 大模型
```

## 4. UGC Public-Site Deep Inquiry (when Q-userdata=Yes)

The UGC hardening checklist is output only when Q-userdata is genuinely "Yes" (Q2a or Q2b inferred Yes) — never imposed because the advisor infers "UGC keywords". Q7-Q10 are **inferred from the project description** (not asked as blocking questions); ask only if a specific hardening item cannot be determined.

| # | Inferred from description | Purpose |
|---|---|---|
| Q7 | Is user-uploaded content publicly visible (anyone can see it)? | Determines content moderation (Green Net) + DMCA process + EXIF stripping |
| Q8 | Does it collect user PII (email/phone/name/location)? | Triggers privacy policy page + cookie consent + encrypted storage + account-deletion cascade |
| Q9 | Does it allow third-party registration (non-invite-only)? | Triggers CAPTCHA + email verification + IP rate-limiting + anti-bot |
| Q10 | Does it involve minors' content/accounts? | Triggers real-name verification + age classification + parental consent |

If any of Q2a/Q2b/Q7–Q10 is "Yes" → recommended SKU mandates OSS private ACL + advisor outputs the **complete 38-item hardening checklist** from the UGC hardening checklist §1–§6 (**inline simplified 5–8 item versions are forbidden**, lint rule-19 backstop).

## 5. Handling Refusal to Answer

When the user replies `不知道 / 随便 / 你定` to Q-scale:
1. **First time**: advisor presents a "conservative vs elastic" binary choice with lifestyle anchors:
   - Assumption A (conservative): ≤15 → starter range — `就几个朋友用`
   - Assumption B (elastic): 15-80 → `lite_growth` — `一个小社区/公开让人用`
   - Ask the user to pick the closer one
2. **Second time**: default to Assumption A (most conservative), state `后续可以通过 OPC 升配`
3. **Forbidden**: silently defaulting to a mid-tier (e.g., `starter_app` or `lite_growth`) without surfacing the assumption
4. For Q-userdata refusal: re-ask with a concrete example (`有没有登录？有没有人传图？`); **never assume "Yes" for PII/VLM triggers** (must be explicit). For inferred Q4/Q5/Q6, surface the assumption in the prescription — no re-ask needed (they are non-blocking).

## 6. Deploy-Side Reverse Validation (interlocked with this questionnaire)

Deploy Phase -1, upon receiving the advisor SKU, checks `state.advisor_questionnaire_answered` for **7 fields**. The advisor fills these from **2 user questions + 5 inferred** (see §1) — the deploy contract is unchanged; only the user-facing question count was compressed.

```yaml
advisor_questionnaire_answered:
  Q1_pv: "<500|500-5k|5k-50k|50k-100k|>100k"   # derived from Q-scale
  Q2a_has_registration: true|false               # from Q-userdata + description
  Q2b_has_ugc_upload: true|false                 # from Q-userdata + description
  Q3_qps: "<5|5-15|15-80|80-200|200+"            # from Q-scale
  Q4_public: true|false                          # inferred
  Q5_account_type: "personal_real_name|company_real_name|unknown"  # inferred/defaulted
  Q6_vlm: true|false                             # inferred from §3 keywords
```

Validation rules:
- Missing any of Q1–Q6 → reject, send back to advisor for re-inquiry
- SKU = `starter_*` AND Q6=Yes → reject, prompt advisor to re-select (typically: `lite_growth` floor — recognition/detection/generation, per iron-rule #32)
- SKU = `starter_*` AND (Q2a=Yes OR Q2b=Yes) → reject, requires independent RDS/OSS, minimum lite_seed
- SKU = `starter_webui` AND Q6=Yes (mis-purchase scenario) → reject, suggest starter_app or higher
- SKU inconsistent with Q-scale boundary (e.g., Q3=80-200 but lite_seed) → suspend, AskUserQuestion to confirm "are you sure about this spec? Performance may be insufficient"
- Q5=unknown → suspend, require advisor to re-confirm account ownership (affects ICP/invoicing)
