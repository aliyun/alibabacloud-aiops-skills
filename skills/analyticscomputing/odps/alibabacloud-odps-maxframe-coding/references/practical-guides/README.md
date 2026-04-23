# MaxFrame Practical Guides

This directory contains practical guides for MaxFrame development, based on real-world experience and common troubleshooting scenarios.

## Guides

### [UDF Development Guide](./udf-development-guide.md)
Best practices for developing User-Defined Functions:
- Resource reuse patterns
- Output type specification
- Third-party package integration
- Network access configuration
- Timeout and memory handling
- Debugging strategies

### [Error Troubleshooting Guide](./error-troubleshooting.md)
Common error codes and solutions:
- Data type errors
- Dependency errors
- Job execution errors
- Memory and resource errors
- Session and table errors
- Data errors
- Shuffle errors

### [Job Configuration Guide](./job-configuration-guide.md)
Configuration and tuning options:
- SQL settings
- Session management
- PythonPack configuration
- Resource allocation
- Split and shuffle configuration
- Best practices for different scenarios

### [Data Handling Guide](./data-handling-guide.md)
Data processing patterns and techniques:
- JSON processing
- Data type handling
- Schema management
- String handling
- Data transformation patterns
- Validation techniques

### [OSS Mounting Guide](./oss-mounting-guide.md)
Mounting and using OSS as distributed storage:
- Prerequisites and RAM role setup
- Using `with_fs_mount` decorator
- Resource configuration
- Batch processing examples
- Debugging techniques

### [AI Function Guide](./ai-function-guide.md)
LLM inference with GPU resources:
- Environment setup for GU resources
- Using `ManagedTextGenLLM` for managed models
- Prompt template syntax
- Performance tuning and debugging

### [Flag Reference](./flag-reference.md)
Comprehensive flag and options reference:
- MaxCompute SQL flags configuration
- MaxFrame options reference
- Parallelism and split settings
- Resource and memory tuning
- Shuffle and stability flags
- UDF timeout and safety settings

## Quick Reference

### Common Configuration

```python
from maxframe import config, options, new_session

# Enable 2.0 data types
config.options.sql.settings = {
    "odps.sql.type.system.odps2": "true",
    "odps.session.image": "common",
}

# Session settings
options.session.max_idle_seconds = 60 * 60 * 24  # 24 hours

session = new_session()
```

### Common Issues

| Error | Solution |
|-------|----------|
| `invalid type INT` | Enable `odps.sql.type.system.odps2=true` |
| `No module named 'cloudpickle'` | Set `odps.session.image=common` |
| `User script exception` | Check UDF code, dependencies, types |
| `kInstanceMonitorTimeout` | Adjust batch size and timeout |
| `Job exceed live limit` | Increase session max_alive_seconds |
| `Table not found` | Increase temp_table_lifecycle |
