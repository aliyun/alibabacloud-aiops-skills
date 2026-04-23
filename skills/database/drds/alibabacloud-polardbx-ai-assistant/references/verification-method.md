# Verification Method

## Steps to Verify Skill Execution

### Step 1: Verify aliyun CLI installation and configuration

```bash
# Check CLI version
aliyun version
# Expected: 3.3.3 or higher

# Check auth configuration
aliyun configure get
# Expected: shows current profile configuration

# Test basic connectivity
aliyun das describe-instance-das-pro --instanceId "pxc-test" --endpoint das.cn-shanghai.aliyuncs.com --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ai-assistant 2>&1
# Expected: JSON response (API error for non-existent instance is OK, connection error is NOT)
```

### Step 2: Verify jq installation

```bash
echo '{"Content":"test"}' | jq -r '.Content'
# Expected: test
```

### Step 3: Verify call_yaochi_agent.sh script

```bash
# Verify script is runnable
bash $SKILL_DIR/scripts/call_yaochi_agent.sh --help
# Expected: shows help information

# Verify no-argument error prompt
bash $SKILL_DIR/scripts/call_yaochi_agent.sh
# Expected: shows usage prompt and exits
```

### Step 4: Verify actual invocation (requires valid credentials)

```bash
# Simple query test
bash $SKILL_DIR/scripts/call_yaochi_agent.sh "Hello"
# Expected: YaoChi Agent response content

# With debug mode
bash $SKILL_DIR/scripts/call_yaochi_agent.sh "Hello" --debug
# Expected: response content + debug info on stderr
```

### Step 5: Verify multi-turn conversation

```bash
# First query - note the session ID in stderr output
bash $SKILL_DIR/scripts/call_yaochi_agent.sh "List PolarDB-X instances in Hangzhou region"
# Expected: instance list, stderr shows [SessionID] sess-xxx

# Second query - use session ID from previous call
bash $SKILL_DIR/scripts/call_yaochi_agent.sh "Continue analyzing the first instance" --session-id "sess-xxx"
# Expected: contextual analysis based on previous conversation
```

## Common Errors and Solutions

| Error | Cause | Solution |
|-------|-------|----------|
| `command not found: aliyun` | aliyun CLI not installed | See cli-installation-guide.md |
| `command not found: jq` | jq not installed | `brew install jq` or `apt install jq` |
| `InvalidAccessKeyId` | Invalid AK/SK | Check `aliyun configure get` configuration |
| `Throttling.UserConcurrentLimit` | Concurrent session limit reached | Wait for previous query to finish, then retry |
| `Forbidden.RAM` | Insufficient permissions | See ram-policies.md for required permissions |
