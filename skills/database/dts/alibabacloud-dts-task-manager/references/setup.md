# Environment Setup

## Setup Workflow

### 1. Check aliyun CLI Installation

```bash
which aliyun
```

If not installed, prompt the user:
- macOS: `brew install aliyun-cli`
- Or download from https://github.com/aliyun/aliyun-cli/releases
- After installation, run `aliyun configure` to set up authentication

### 2. Check Authentication Configuration

```bash
aliyun configure list
```

If not configured, guide the user through setup:
```bash
aliyun configure --mode AK
```
Requires: AccessKey ID, AccessKey Secret, Region Id

**Important**: Never display the user's AccessKey Secret in the conversation. Protect sensitive information.

### 3. Test Connectivity

```bash
aliyun dts DescribeDtsJobs --RegionId <region> --PageSize 1 --read-timeout 30 --connect-timeout 10 --user-agent AlibabaCloud-Agent-Skills
```

Verify that the API call succeeds and confirm the environment is properly configured.
