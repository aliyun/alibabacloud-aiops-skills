# E-HPC Instant 计算资源配置

## 资源配置选项
E-HPC Instant支持两种资源配置方式：
1. **按规格配置**：指定实例规格（InstanceType）
2. **按资源配置**：指定CPU核数和内存大小

## 实例规格配置（推荐）
```bash
# 使用实例规格（高优先级）
"Resource": {
    "InstanceTypes": ["ecs.c6.xlarge"],
    "Disks": [{"Type":"System","Size":50}]
}
```

## CPU/内存配置
```bash
# 指定CPU核数和内存（GB）
"Resource": {
    "Cores": 4,
    "Memory": 8,
    "Disks": [{"Type":"System","Size":40}]
}
```

## 常用实例规格参考
| 规格类型 | CPU核数 | 内存(GB) | 适用场景 |
|---------|--------|---------|---------|
| ecs.c7.large | 2 | 4 | 轻量计算 |
| ecs.c7.xlarge | 4 | 8 | 通用计算 |
| ecs.c7.2xlarge | 8 | 16 | 中等计算 |
| ecs.gn7i-c8g1.2xlarge | 8 | 30 | GPU计算 |
| ecs.r7.xlarge | 4 | 32 | 内存密集 |

## 磁盘配置
- **系统盘**：必需，最小40GB（容器）/40GB（VM）
- **数据盘**：可选，格式：`{"Type":"Data","Size":100}`

## 完整资源配置示例
### 容器作业
```json
"Resource": {
    "Cores": 4,
    "Memory": 8,
    "InstanceTypes": ["ecs.c6.xlarge"],
    "Disks": [{"Type":"System","Size":40}]
}
```

### VM作业
```json
"Resource": {
    "Cores": 4,
    "Memory": 8,
    "InstanceTypes": ["ecs.c6.xlarge"],
    "Disks": [
        {"Type":"System","Size":50},
        {"Type":"Data","Size":100}
    ]
}
```

## 注意事项
- InstanceType配置优先级高于Cores/Memory配置
- 确保所选规格在目标区域可用
- GPU实例需要特殊镜像支持