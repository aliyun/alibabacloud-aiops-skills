# Acceptance Criteria: alibabacloud-cleversee-search

**Scenario**: cleversee CLI web search and credential management
**Purpose**: Skill testing acceptance criteria

---

# Correct CLI Command Patterns

## 1. cleversee web-search — basic search

#### CORRECT
```bash
cleversee web-search --query "What are the latest battery breakthroughs in electric vehicles?" --limit 5 --search-type pro -o json
```

#### INCORRECT
```bash
# Wrong: missing required --query
cleversee web-search --limit 5

# Wrong: limit out of range
cleversee web-search --query "test" --limit 20
```

## 2. cleversee web-search — date range

#### CORRECT
```bash
cleversee web-search --query "2026 trends" --start-time 2026-01-01 --end-time 2026-06-30 -o json
```

#### INCORRECT
```bash
# Wrong: invalid date format
cleversee web-search --query "test" --start-time "Jan 1 2026"
```

## 3. cleversee web-search — domain filtering

#### CORRECT
```bash
# exclude-domain requires pro mode
cleversee web-search --query "SLB config" --search-type pro \
  --exclude-domain spam-site.com -o json
```

#### INCORRECT
```bash
# Wrong: include-domain not supported in lite mode
cleversee web-search --query "test" --search-type lite --include-domain help.aliyun.com
```

## 4. cleversee doctor

#### CORRECT
```bash
cleversee doctor
```

#### INCORRECT
```bash
# Wrong: doctor doesn't accept parameters
cleversee doctor --verbose
```

#### INCORRECT
```bash
# Wrong: missing required --mode
cleversee auth set --access-key-id xxx --access-key-secret yyy
```

## 6. Security Rules

#### CORRECT
- Use `cleversee auth set` with parameters provided by user
- Use `cleversee doctor` to verify credential status

#### INCORRECT
- Echo or print AK/SK values: `echo $ALIBABA_CLOUD_ACCESS_KEY_ID`
- Ask user to input AK/SK directly in conversation
- Use interactive `cleversee auth set` or `cleversee auth switch` in non-interactive contexts

## 7. Interactive vs Non-Interactive

#### CORRECT
- `cleversee auth set --mode RamRoleArn ...` in automated/non-interactive contexts
- `cleversee auth set --mode OAuth` only when user is present with browser

#### INCORRECT
- `cleversee auth set` (no params) in automated context — triggers interactive flow
- `cleversee auth switch` in automated context — triggers interactive flow
