# Troubleshooting Guide

## Common Issues and Solutions

### 1. Import Errors (ModuleNotFoundError)
```bash
# Error: No module named 'alibabacloud_mts20140618'
# Solution: Install missing dependencies
pip install alibabacloud-mts20140618 alibabacloud-credentials oss2

# Quick dependency check script
python scripts/dependency_check.py
```

### 2. Authentication Failures
```bash
# Error: Invalid credentials or missing configuration
# Solution: Verify Aliyun CLI configuration
aliyun configure
aliyun configure list  # Check credential status
```

### 3. Pipeline Selection Failures
```bash
# Error: No available pipeline found
# Solution: Manually set pipeline ID
export ALIBABA_CLOUD_MPS_PIPELINE_ID="your-pipeline-id"
# Or check available pipelines
aliyun mts SearchPipeline
```

### 4. Network/Timeout Issues
```bash
# Error: Connection timeout or slow installation
# Solution: Use alternative mirrors
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple alibabacloud-mts20140618 alibabacloud-credentials oss2

# Increase timeout for large installations
pip install --timeout 1800 alibabacloud-mts20140618 alibabacloud-credentials oss2
```

### 5. Permission Denied During Installation
```bash
# Error: Permission denied
# Solution: Use user installation
pip install --user alibabacloud-mts20140618 alibabacloud-credentials oss2

# Or create virtual environment
python3 -m venv .venv
source .venv/bin/activate
pip install alibabacloud-mts20140618 alibabacloud-credentials oss2
```

## Diagnostic Commands

```bash
# Check Python version
python3 --version

# Check Aliyun CLI version
aliyun version

# Verify environment variables
python3 scripts/load_env.py --check-only

# Test MPS SDK
python -c "import alibabacloud_mts20140618; print('MPS SDK OK')"

# Test OSS SDK
python -c "import oss2; print('OSS SDK OK')"
```

## Additional Resources

- [SDK Installation Guide](https://help.aliyun.com/document_detail/sdk-installation)
- [Credential Configuration](https://help.aliyun.com/document_detail/credential-config)
- [MPS Documentation](https://help.aliyun.com/product/29203.html)
