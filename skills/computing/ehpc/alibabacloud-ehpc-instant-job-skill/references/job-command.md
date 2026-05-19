# E-HPC Instant 作业命令配置

## 容器作业命令配置
容器作业通过Command参数指定要执行的命令：

### 单命令执行
```json
"Container": {
    "Image": "registry.cn-shanghai.aliyuncs.com/registry/image:tag",
    "Command": "python /app/main.py"
}
```

### 多参数命令
```json
"Container": {
    "Image": "registry.cn-shanghai.aliyuncs.com/registry/image:tag",
    "Command": "bash -c 'echo hello && sleep 100'"
}
```

### 带参数的命令数组
对于复杂命令，可以使用数组格式：
```json
"Container": {
    "Image": "registry.cn-shanghai.aliyuncs.com/registry/image:tag",
    "Command": ["python", "/app/main.py", "--param1", "value1", "--param2", "value2"]
}
```

## VM作业脚本配置
VM作业通过Script参数指定初始化脚本（Base64编码）：

### 脚本编码示例
```bash
# 原始脚本
echo '#!/bin/bash
echo "Starting job..."
python /app/main.py
' | base64 -w 0

# 在API中使用
"VM": {
    "Image": "m-xxxx",
    "Script": "IyEvYmluL2Jhc2gKZWNobyAiU3RhcnRpbmcgam9iLi4uIgpweXRob24gL2FwcC9tYWluLnB5Cg=="
}
```

## 命令配置最佳实践
- **容器作业**：使用绝对路径指定可执行文件
- **环境变量**：在命令中直接设置或通过镜像预配置
- **工作目录**：确保命令路径与镜像内路径一致
- **退出码**：作业成功要求命令正常退出（exit code 0）

## 常见命令示例
### 数据处理作业
```bash
python /app/process_data.py --input /data/input.csv --output /data/output.csv
```

### 机器学习训练
```bash
python /app/train.py --epochs 100 --batch-size 32 --learning-rate 0.001
```

### 长期运行服务
```bash
sleep 1000  # 或其他长期运行命令
```

## 注意事项
- 命令必须在镜像环境中可执行
- 避免使用交互式命令（如需要用户输入）
- 对于长时间运行的作业，确保命令不会意外退出[