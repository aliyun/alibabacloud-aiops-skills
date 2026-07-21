# Acceptance Criteria: alibabacloud-cas-ssl-cert-purchase

**Scenario**: SSL certificate purchase and application via Alibaba Cloud CAS V2.0
**Purpose**: Skill testing acceptance criteria

---

# Correct CLI Command Patterns

## 1. Product — CAS commands use plugin mode

#### ✅ CORRECT
```bash
aliyun cas list-instances --status inactive --profile $CERT_PROFILE --region $CERT_REGION
aliyun cas update-instance --instance-id cas_dv-cn-xxx --domain example.com
aliyun cas apply-certificate --instance-id cas_dv-cn-xxx
aliyun cas get-task-attribute --task-id cas_dv-cn-xxx --task-type ApplyCertificate
```

#### ❌ INCORRECT
```bash
# Traditional API format (PascalCase) — wrong for CAS plugin
aliyun cas ListInstances --Status inactive
aliyun cas UpdateInstance --InstanceId cas_dv-cn-xxx
aliyun cas ApplyCertificate --InstanceId cas_dv-cn-xxx
```

## 2. Product — BSS commands use script wrapper (plugin mode)

BSS operations use the `bssopenapi` plugin in **plugin mode** (lowercase-hyphenated subcommands, e.g. `aliyun bssopenapi create-instance`). All BSS calls are wrapped in `scripts/bss-purchase.sh`, which constructs the `--parameter Code=... Value=...` pairs internally.

#### ✅ CORRECT
```bash
bash scripts/bss-purchase.sh create-instance --product-code cas --product-type cas_dv_public_cn
bash scripts/bss-purchase.sh check-plugin --profile $CERT_PROFILE --region $CERT_REGION
```

#### ❌ INCORRECT
```bash
# Do NOT call the bssopenapi plugin with PascalCase API names — use plugin mode via the script wrapper
aliyun bssopenapi CreateInstance --ProductCode cas
aliyun bssopenapi QueryProductList
```

## 3. Parameters — `--user-agent` on every CAS API command

#### ✅ CORRECT
```bash
aliyun cas list-instances --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-cas-ssl-cert-purchase/{session-id}" \
  --profile $CERT_PROFILE --region $CERT_REGION --status inactive
```

#### ❌ INCORRECT
```bash
# Missing --user-agent
aliyun cas list-instances --profile $CERT_PROFILE --region $CERT_REGION --status inactive
```

## 4. Parameters — BSS pricing-cycle must be 2 (monthly)

The script `scripts/bss-purchase.sh` automatically sets `--pricing-cycle 2` internally. The `--period` flag specifies months.

#### ✅ CORRECT
```bash
bash scripts/bss-purchase.sh create-instance --period 12 --cert-type dv ...
```

#### ❌ INCORRECT
```bash
# Period must be a valid duration (3/6/12/24/36 months depending on CA)
# See SKILL.md Parameter Confirmation table for per-CA duration support
```

## 5. Parameters — Site-specific product-code/product-type

#### ✅ CORRECT — China Site
```bash
bash scripts/bss-purchase.sh create-instance --product-code cas --product-type cas_dv_public_cn ...
```

#### ✅ CORRECT — International Site
```bash
bash scripts/bss-purchase.sh create-instance --product-code cas_intl --product-type cas_intl ...
```

#### ❌ INCORRECT
```bash
# Wrong product-type for China site: --product-type cas_intl
# Wrong product-code for International site: --product-code cas with --product-type cas_dv_public_cn on intl
```

## 6. Confirmation Gates — MUST stop and wait

#### ✅ CORRECT
```
About to submit certificate application:
| Item | Value |
|------|-------|
| Instance ID | cas_dv-cn-xxx |
| Domain | example.com |
Confirm submission? (Y/n)

[WAITS for user response in separate turn]
```

#### ❌ INCORRECT
```
About to submit certificate application:
| Item | Value |
|------|-------|
| Instance ID | cas_dv-cn-xxx |
| Domain | example.com |
Confirm submission? (Y/n)

[Immediately executes apply-certificate in same turn]
```

## 7. Credential Safety

#### ✅ CORRECT
```bash
aliyun configure list   # Check credential status
```

#### ❌ INCORRECT
```bash
echo $ALIBABA_CLOUD_ACCESS_KEY_ID       # FORBIDDEN — prints AK
echo $ALIBABA_CLOUD_ACCESS_KEY_SECRET    # FORBIDDEN — prints SK
aliyun configure set --access-key-id LTAI...  # FORBIDDEN — literal credential
```

## 8. No undefined variables

#### ✅ CORRECT
```bash
bash scripts/bss-purchase.sh create-instance --profile $CERT_PROFILE --region $CERT_REGION ...
```

#### ❌ INCORRECT
```bash
# Do NOT use undefined variables like $ALIYUN_CMD — always use the script wrapper
# Do NOT call bssopenapi directly with PascalCase in markdown files
```

## 9. CA Brand and Duration — never auto-select

#### ✅ CORRECT
```
Please choose a CA brand:
1. Alibaba (ali.dv.f)
2. GeoTrust (geo.dv.f)
3. DigiCert (ss.ov.f)
...
Which CA brand would you like? [User must choose]

Please choose duration: 6/12/24/36 months? [User must choose]
```

#### ❌ INCORRECT
```
Using default CA: Alibaba (ali.dv.f) with 12-month duration.
[Auto-selects without user confirmation]
```

## 10. TEST instance — China site only

#### ✅ CORRECT
```bash
# China site — TEST certificates available
bash scripts/bss-purchase.sh create-instance \
  --product-code cas --product-value testCert_product \
  --full-spec ss.dv.t --cert-type dv ...
```

#### ❌ INCORRECT
```bash
# International site does NOT support TEST certificates
# Do not use --product-value testCert_product with --product-code cas_intl
```
