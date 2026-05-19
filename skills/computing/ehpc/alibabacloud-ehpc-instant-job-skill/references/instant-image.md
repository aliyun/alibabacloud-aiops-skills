# E-HPC Instant Image镜像管理
通过阿里云CLI（优先）或SDK工具，实现对E-HPC Instant计算平台镜像资源的管理。主要操作包括添加镜像、查询镜像列表、获取镜像详情、移除镜像等，支持VM虚拟机及Container容器镜像类型。

## 添加镜像
### VM虚拟机镜像
```bash
aliyun ehpcinstant AddImage \
    --region cn-shanghai \
    --Name 'Custom-VM-Image' \
    --ImageVersion '1.0' \
    --Description 'Custom VM image for E-HPC Instant' \
    --ImageType 'VM' \
    --VMImageSpec '{"ImageId":"m-xxxx"}' \
    --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ehpc-instant-job-skill
```

### Container容器镜像
```bash
aliyun ehpcinstant AddImage \
    --region cn-shanghai \
    --Name 'Custom-Container-Image' \
    --ImageVersion '1.0' \
    --Description 'Custom container image for E-HPC Instant' \
    --ImageType 'Container' \
    --ContainerImageSpec '{"RegistryUrl":"registry.cn-shanghai.aliyuncs.com/namespace/image:tag"}' \
    --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ehpc-instant-job-skill
```

## 查询镜像列表
```bash
aliyun ehpcinstant ListImages --region cn-shanghai \
    --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ehpc-instant-job-skill
```

## 获取镜像详情
```bash
aliyun ehpcinstant GetImage --region cn-shanghai --ImageId 'm-xxxx' \
    --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ehpc-instant-job-skill
```

## 移除镜像
```bash
aliyun ehpcinstant RemoveImage --region cn-shanghai --ImageId 'm-xxxx' \
    --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ehpc-instant-job-skill
**注意：** 移除镜像操作前，必须与用户确认后方可执行。