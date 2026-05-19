# 阿里云E-HPC Instant CLI完整命令参考手册

## 概述
阿里云E-HPC Instant（弹性高性能计算即时版）提供按需、弹性的高性能计算服务。本手册详细介绍使用阿里云 CLI 进行 E-HPC Instant 计算平台的完整命令参考。

## 前置条件
1. **安装阿里云CLI**：确保已安装并配置阿里云 CLI
2. **权限配置**：AccessKey 需要具备 E-HPC Instant 相关权限
3. **区域选择**：确认操作的区域（如 cn-shanghai）
4. **User-Agent标识**：所有命令均应附加 `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-ehpc-instant-job-skill` 参数，用于服务端识别调用来源。如已通过 `aliyun configure ai-mode set-user-agent` 配置，则会自动附加，无需手动添加。

## 1. 作业管理（Job Management）

### 创建作业（CreateJob）

#### 容器作业（Container Job）
```bash
# 基本容器作业
aliyun ehpcinstant CreateJob \
    --region cn-shanghai \
    --JobName "container-job" \
    --Tasks '[{
        "TaskSpec": {
            "TaskExecutor": [{
                "Container": {
                    "Image": "registry.cn-shanghai.aliyuncs.com/registry/image:tag",
                    "Command": "[\"/bin/sh\", \"-c\", \"python /app/main.py\"]"
                }
            }],
            "Resource": {
                "Cores": 2,
                "Memory": 4,
                "Disks": [{"Type":"System","Size":40}]
            }
        },
        "ExecutorPolicy": {"MaxCount": 1}
    }]'

# 容器作业带网络及存储NAS配置
aliyun ehpcinstant CreateJob \
    --region cn-shanghai \
    --JobName "container-job-with-network" \
    --DeploymentPolicy '{"Network":{"Vswitch":["vsw-xxxxxx"]},"AllocationSpec":"Standard"}' \
    --Tasks '[{
        "TaskSpec": {
            "TaskExecutor": [{
                "Container": {
                    "Image": "registry.cn-shanghai.aliyuncs.com/registry/image:tag",
                    "Command": "[\"/bin/sh\", \"-c\", \"echo hello\"]",
                }
            }],
            "Resource": {
                "Cores": 4,
                "Memory": 8
            },
            "VolumeMount": [
              {
                "MountPath": "/mnt",
                "VolumeDriver": "alicloud/nas",
                "MountOptions": "{\"server\":\"xxx.cn-shanghai.nas.aliyuncs.com\",\"vers\":\"3\",\"path\":\"/\",\"options\":\"nolock,tcp,noresvport\"}"
              }
            ],
        },
        "ExecutorPolicy": {"MaxCount": 1}
    }]'
```

#### 虚拟机作业（VM Job）
```bash
# 基本VM作业
aliyun ehpcinstant CreateJob \
    --region cn-shanghai \
    --JobName "vm-job" \
    --JobDescription "Long-running VM job" \
    --Tasks '[{
        "TaskSpec": {
            "TaskExecutor": [{
                "VM": {
                    "Image": "m-xxxxxx",
                    "Script": "IyEvYmluL2Jhc2gKZWNobyAiSGVsbG8gZnJvbSBWTSBqb2IhIgo="
                }
            }],
            "Resource": {
                "Disks": [{"Type":"System","Size":50}],
                "InstanceTypes": ["ecs.c6.xlarge"],
                "Cores": 4,
                "Memory": 8
            }
        },
        "ExecutorPolicy": {"MaxCount": 1}
    }]' \
    --DeploymentPolicy '{"Network":{"Vswitch":["vsw-xxxxxx"]},"AllocationSpec":"Standard"}'
```

#### 参数说明
- **JobName**: 作业名称（2-64字符，支持字母、数字、中文、连字符、下划线）
- **Tasks**: 任务列表（目前只支持一个任务）
- **DeploymentPolicy**: 资源部署策略（网络配置、分配规格）
- **JobDescription**: 作业描述（可选）
- **JobScheduler**: 作业调度器类型（HPC/K8S，默认HPC）

### 查询作业列表（ListJobs）
```bash
# 基本查询
aliyun ehpcinstant ListJobs --region cn-shanghai

# 分页查询
aliyun ehpcinstant ListJobs \
    --PageSize 10 \
    --PageNumber 1 \
    --region cn-shanghai

# 条件过滤
aliyun ehpcinstant ListJobs \
    --Filter '{"Status":"Running"}' \
    --region cn-shanghai

# 排序查询
aliyun ehpcinstant ListJobs \
    --SortBy "CreateTime DESC" \
    --region cn-shanghai
```

### 获取作业详情（GetJob）
```bash
# 查询特定作业详情
aliyun ehpcinstant GetJob \
    --JobId "job-xxxxxx" \
    --region cn-shanghai
```

### 删除作业（DeleteJobs）
```bash
# 删除单个作业
aliyun ehpcinstant DeleteJobs \
    --JobSpec '[{"JobId":"job-xxxxxx"}]' \
    --region cn-shanghai

# 批量删除作业
aliyun ehpcinstant DeleteJobs \
    --JobSpec '[{"JobId":"job-xxxxxx"},{"JobId":"job-yyyyyy"}]' \
    --region cn-shanghai

# 删除执行器（按执行器ID）
aliyun ehpcinstant DeleteJobs \
    --ExecutorIds '["job-xxxxxx-Task0-0"]' \
    --region cn-shanghai
```

### 查询作业日志（DescribeJobResults）
```bash
# 查询作业日志
aliyun ehpcinstant DescribeJobResults \
    --JobId "job-xxxxxx" \
    --TaskName "Task0" \
    --ArrayIndex 0 \
    --region cn-shanghai

# 限制日志大小
aliyun ehpcinstant DescribeJobResults \
    --JobId "job-xxxxxx" \
    --LimitBytes "1048576" \
    --region cn-shanghai

# 指定时间范围
aliyun ehpcinstant DescribeJobResults \
    --JobId "job-xxxxxx" \
    --StartTime "2026-04-11T10:00:00Z" \
    --region cn-shanghai
```

## 2. 镜像管理（Image Management）

### 添加自定义镜像（AddImage）

#### 容器镜像
```bash
# 添加容器镜像
aliyun ehpcinstant AddImage \
    --region cn-shanghai \
    --Name "custom-container-image" \
    --Description "Custom container image for E-HPC" \
    --ImageType "Container" \
    --ContainerImageSpec '{"RegistryUrl":"registry.cn-shanghai.aliyuncs.com/registry/image:tag"}'
```

#### 虚拟机镜像
```bash
# 添加VM镜像
aliyun ehpcinstant AddImage \
    --region cn-shanghai \
    --Name "custom-vm-image" \
    --Description "Custom VM image for E-HPC" \
    --ImageType "VM" \
    --VMImageSpec '{"ImageId":"m-xxxxxx"}'
```

### 查询镜像列表（ListImages）
```bash
# 查询所有镜像
aliyun ehpcinstant ListImages --region cn-shanghai

# 查询容器镜像
aliyun ehpcinstant ListImages \
    --ImageType "Container" \
    --region cn-shanghai

# 查询自定义镜像
aliyun ehpcinstant ListImages \
    --ImageCategory "Custom" \
    --region cn-shanghai

# 分页查询
aliyun ehpcinstant ListImages \
    --PageSize 20 \
    --PageNumber 1 \
    --region cn-shanghai

# 合并版本查询（最新版本）
aliyun ehpcinstant ListImages \
    --Mode "Merge" \
    --region cn-shanghai
```

### 获取镜像详情（GetImage）
```bash
# 查询镜像详情
aliyun ehpcinstant GetImage \
    --ImageId "img-xxxxxx" \
    --region cn-shanghai
```

### 删除镜像（RemoveImage）
```bash
# 删除自定义镜像
aliyun ehpcinstant RemoveImage \
    --ImageId "img-xxxxxx" \
    --region cn-shanghai
```

## 3. 资源池管理（Pool Management）

### 创建资源池（CreatePool）
```bash
# 创建基本资源池
aliyun ehpcinstant CreatePool \
    --region cn-shanghai \
    --PoolName "compute-pool" \
    --PoolDescription "Resource pool for compute jobs" \
    --PoolSpec '{"InstanceTypes":["ecs.c6.xlarge"],"MaxCapacity":10}'
```

### 查询资源池列表（ListPools）
```bash
# 查询资源池列表
aliyun ehpcinstant ListPools --region cn-shanghai
```

### 获取资源池详情（GetPool）
```bash
# 查询资源池详情
aliyun ehpcinstant GetPool \
    --PoolId "pool-xxxxxx" \
    --region cn-shanghai
```

### 更新资源池（UpdatePool）
```bash
# 更新资源池配置
aliyun ehpcinstant UpdatePool \
    --PoolId "pool-xxxxxx" \
    --PoolSpec '{"InstanceTypes":["ecs.c6.2xlarge"],"MaxCapacity":20}' \
    --region cn-shanghai
```

### 删除资源池（DeletePool）
```bash
# 删除资源池
aliyun ehpcinstant DeletePool \
    --PoolId "pool-xxxxxx" \
    --region cn-shanghai
```

## 4. 执行计划管理（Action Plan Management）

### 创建执行计划（CreateActionPlan）
```bash
# 创建执行计划
aliyun ehpcinstant CreateActionPlan \
    --region cn-shanghai \
    --PlanName "scheduled-plan" \
    --PlanDescription "Scheduled execution plan" \
    --PlanSpec '{"Schedule":"0 0 * * *","JobTemplate":{...}}'
```

### 查询执行计划列表（ListActionPlans）
```bash
# 查询执行计划列表
aliyun ehpcinstant ListActionPlans --region cn-shanghai
```

### 获取执行计划详情（GetActionPlan）
```bash
# 查询执行计划详情
aliyun ehpcinstant GetActionPlan \
    --PlanId "plan-xxxxxx" \
    --region cn-shanghai
```

### 查询执行计划活动（ListActionPlanActivities）
```bash
# 查询执行计划活动状态
aliyun ehpcinstant ListActionPlanActivities \
    --PlanId "plan-xxxxxx" \
    --region cn-shanghai
```

### 更新执行计划（UpdateActionPlan）
```bash
# 更新执行计划
aliyun ehpcinstant UpdateActionPlan \
    --PlanId "plan-xxxxxx" \
    --PlanSpec '{"Schedule":"0 1 * * *","JobTemplate":{...}}' \
    --region cn-shanghai
```

### 删除执行计划（DeleteActionPlan）
```bash
# 删除执行计划
aliyun ehpcinstant DeleteActionPlan \
    --PlanId "plan-xxxxxx" \
    --region cn-shanghai
```

## 5. 监控和指标（Monitoring & Metrics）

### 查询作业监控数据（DescribeJobMetricData）
```bash
# 查询作业监控指标
aliyun ehpcinstant DescribeJobMetricData \
    --JobId "job-xxxxxx" \
    --ArrayIndex 0 \
    --MetricName "CPUUtilization" \
    --StartTime "2026-04-11T10:00:00Z" \
    --EndTime "2026-04-11T11:00:00Z" \
    --region cn-shanghai
```

### 查询作业最新指标（DescribeJobMetricLast）
```bash
# 查询作业最新监控指标
aliyun ehpcinstant DescribeJobMetricLast \
    --JobId "job-xxxxxx" \
    --ArrayIndex 0 \
    --region cn-shanghai
```

## 6. 执行器管理（Executor Management）

### 查询全局执行器信息（ListExecutors）
```bash
# 查询所有执行器
aliyun ehpcinstant ListExecutors --region cn-shanghai
```

### 查询作业执行器信息（ListJobExecutors）
```bash
# 查询特定作业的执行器
aliyun ehpcinstant ListJobExecutors \
    --JobId "job-xxxxxx" \
    --region cn-shanghai
```

### 查询执行器事件（ListExecutorEvents）
```bash
# 查询执行器运行事件
aliyun ehpcinstant ListExecutorEvents \
    --ExecutorIds '["job-xxxxxx-Task0-0"]' \
    --region cn-shanghai
```

## 7. 标签管理（Tag Management）

### 绑定标签（TagResources）
```bash
# 为资源绑定标签
aliyun ehpcinstant TagResources \
    --RegionId cn-shanghai \
    --ResourceType "Job" \
    --ResourceId.1 "job-xxxxxx" \
    --Tag.1.Key "Environment" \
    --Tag.1.Value "Production" \
    --Tag.2.Key "Project" \
    --Tag.2.Value "E-HPC"
```

### 查询标签（ListTagResources）
```bash
# 查询资源标签
aliyun ehpcinstant ListTagResources \
    --RegionId cn-shanghai \
    --ResourceType "Job" \
    --ResourceId.1 "job-xxxxxx"
```

### 解绑标签（UnTagResources）
```bash
# 解绑资源标签
aliyun ehpcinstant UnTagResources \
    --RegionId cn-shanghai \
    --ResourceType "Job" \
    --ResourceId.1 "job-xxxxxx" \
    --TagKey.1 "Environment"
```

## 8. 应用管理（Application Management）

### 同步应用（SynchronizeApp）
```bash
# 应用跨区域同步
aliyun ehpcinstant SynchronizeApp \
    --RegionId cn-shanghai \
    --AppName "my-app" \
    --TargetRegion "cn-beijing"
```

### 获取应用版本（GetAppVersions）
```bash
# 获取应用版本列表
aliyun ehpcinstant GetAppVersions \
    --RegionId cn-shanghai \
    --AppName "my-app"
```

## 9. 实用脚本示例

### 作业提交完整流程
```bash
#!/bin/bash
# E-HPC Instant 作业提交脚本

REGION="cn-shanghai"
JOB_NAME="e-hpc-job-$(date +%Y%m%d-%H%M%S)"
CONTAINER_IMAGE="registry.cn-shanghai.aliyuncs.com/test/test:v1.0"
COMMAND='["/bin/sh", "-c", "sleep 1000"]'
USER_AGENT="AlibabaCloud-Agent-Skills/alibabacloud-ehpc-instant-job-skill"

# 创建作业
JOB_ID=$(aliyun ehpcinstant CreateJob \
    --region $REGION \
    --JobName "$JOB_NAME" \
    --Tasks "[{\"TaskSpec\":{\"TaskExecutor\":[{\"Container\":{\"Image\":\"$CONTAINER_IMAGE\",\"Command\":$COMMAND}}],\"Resource\":{\"Cores\":4,\"Memory\":8}}},\"ExecutorPolicy\":{\"MaxCount\":1}}]" \
    --user-agent $USER_AGENT \
    --output cols=JobId rows=1)

echo "Created Job: $JOB_ID"

# 等待作业启动
sleep 10

# 查询作业状态
aliyun ehpcinstant GetJob \
    --JobId $JOB_ID \
    --region $REGION \
    --user-agent $USER_AGENT

# 查询作业日志
aliyun ehpcinstant DescribeJobResults \
    --JobId $JOB_ID \
    --TaskName "Task0" \
    --ArrayIndex 0 \
    --region $REGION \
    --user-agent $USER_AGENT
```

### 作业监控脚本
```bash
#!/bin/bash
# 作业监控脚本

JOB_ID=$1
REGION=${2:-cn-shanghai}
USER_AGENT="AlibabaCloud-Agent-Skills/alibabacloud-ehpc-instant-job-skill"

while true; do
    # 获取作业状态
    STATUS=$(aliyun ehpcinstant GetJob \
        --JobId $JOB_ID \
        --region $REGION \
        --user-agent $USER_AGENT \
        --output cols=Status rows=1)
    
    echo "Job $JOB_ID status: $STATUS"
    
    if [[ "$STATUS" == "Succeeded" || "$STATUS" == "Failed" ]]; then
        break
    fi
    
    sleep 30
done

# 获取最终日志
aliyun ehpcinstant DescribeJobResults \
    --JobId $JOB_ID \
    --TaskName "Task0" \
    --ArrayIndex 0 \
    --region $REGION \
    --user-agent $USER_AGENT
```

### 批量作业管理
```bash
# 批量查询运行中的作业
aliyun ehpcinstant ListJobs \
    --Filter '{"Status":"Running"}' \
    --region cn-shanghai \
    --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ehpc-instant-job-skill \
    --output cols=JobId,JobName,Status,CreateTime

# 批量删除已完成的作业
COMPLETED_JOBS=$(aliyun ehpcinstant ListJobs \
    --Filter '{"Status":"Succeeded"}' \
    --region cn-shanghai \
    --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ehpc-instant-job-skill \
    --output cols=JobId | tail -n +2)

if [ -n "$COMPLETED_JOBS" ]; then
    JOB_ARRAY=""
    for job in $COMPLETED_JOBS; do
        if [ -z "$JOB_ARRAY" ]; then
            JOB_ARRAY="{\"JobId\":\"$job\"}"
        else
            JOB_ARRAY="$JOB_ARRAY,{\"JobId\":\"$job\"}"
        fi
    done
    
    aliyun ehpcinstant DeleteJobs \
        --JobSpec "[$JOB_ARRAY]" \
        --region cn-shanghai \
        --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ehpc-instant-job-skill
fi
```

## 10. 故障排查

### 常见错误及解决方案
| 错误 | 解决方案 |
|------|----------|
| **InvalidCommand** | 确保Command参数使用正确的JSON数组格式 |
| **ImageNotFound** | 确认镜像ID正确且在相同区域 |
| **QuotaExceeded** | 联系阿里云增加配额 |
| **NetworkError** | 检查VSwitch ID和安全组配置 |
| **AuthenticationFailed** | 检查AccessKey配置 |

### 调试技巧
```bash
# 查看详细错误信息
aliyun ehpcinstant CreateJob --debug ...

# 验证JSON格式
echo '{"TaskSpec":{...}}' | python -m json.tool
```

## 11. 最佳实践

1. **作业命名规范**：
   - 包含用途、环境、时间戳信息
   - 示例：`prod-training-20260411-1000`

2. **资源配置优化**：
   - 根据应用需求选择合适的实例规格
   - 使用InstanceTypes优先于Cores/Memory配置

3. **错误处理**：
   - 检查作业状态后再进行后续操作
   - 实现重试机制处理临时性错误

4. **成本控制**：
   - 及时删除已完成的作业
   - 使用适当的资源规格避免浪费

5. **安全性**：
   - 使用私有镜像仓库
   - 配置适当的网络访问控制

## 12. 参考文档
- [E-HPC Instant API文档](https://api.aliyun.com/document/EhpcInstant/2023-07-01/overview)
- [阿里云CLI官方文档](https://help.aliyun.com/document_detail/121529.html)