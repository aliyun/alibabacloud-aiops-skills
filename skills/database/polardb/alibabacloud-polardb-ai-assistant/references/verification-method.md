# Verification Method

## How to Verify Skill Execution Success

### Step 1: Verify aliyun CLI Installation and Configuration

```bash
# Check CLI version
aliyun version
# Expected output: 3.3.1 or higher

# Check authentication configuration
aliyun configure get
# Expected output: Display current profile configuration

# Test basic connectivity
aliyun das DescribeInstanceDasPro --InstanceId "pc-test" --endpoint das.cn-shanghai.aliyuncs.com --user-agent AlibabaCloud-Agent-Skills 2>&1
# Expected: Return JSON response (even if instance doesn't exist, should return API error not connection error)
```

### Step 2: Verify jq Installation

```bash
echo '{"Content":"test"}' | jq -r '.Content'
# Expected output: test
```

### Step 3: Verify call_yaochi_agent.sh Script

```bash
# Verify script is executable
bash $SKILL_DIR/scripts/call_yaochi_agent.sh --help
# Expected: Display help information

# Verify error prompt without parameters
bash $SKILL_DIR/scripts/call_yaochi_agent.sh
# Expected: Display usage prompt and exit
```

### Step 4: Verify Actual Invocation (requires valid credentials)

```bash
# Simple query test
bash $SKILL_DIR/scripts/call_yaochi_agent.sh "Hello"
# Expected: Return YaoChi Agent response content

# With debug mode
bash $SKILL_DIR/scripts/call_yaochi_agent.sh "Hello" --debug
# Expected: Return response content, also output debug info to stderr
```

### Step 5: Verify Multi-turn Conversation

```bash
# First round query - note the session ID output to stderr
bash $SKILL_DIR/scripts/call_yaochi_agent.sh "List PolarDB clusters in Hangzhou region"
# Expected: Return cluster list, stderr outputs [SessionID] sess-xxx

# Second round query - use session ID from previous round
bash $SKILL_DIR/scripts/call_yaochi_agent.sh "Continue analyzing the first cluster" --session-id "sess-xxx"
# Expected: Continue analysis based on context
```

## Common Errors and Solutions

| Error | Cause | Solution |
|-------|-------|----------|
| `command not found: aliyun` | aliyun CLI not installed | Refer to cli-installation-guide.md for installation |
| `command not found: jq` | jq not installed | `brew install jq` or `apt install jq` |
| `InvalidAccessKeyId` | Invalid AK/SK | Check `aliyun configure get` configuration |
| `Throttling.UserConcurrentLimit` | Concurrency limit exceeded | Wait for previous query to complete and retry |
| `Forbidden.RAM` | Insufficient permissions | Refer to ram-policies.md for permission configuration |
