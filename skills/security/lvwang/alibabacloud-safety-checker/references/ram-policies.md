# RAM 权限策略

本 Skill 调用阿里云内容安全（Green）服务，需要以下 RAM 权限。

## 推荐权限策略（最小权限原则）

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "green:TextModerationPlus",
        "green:TextModeration",
        "green:ImageModeration",
        "green:AudioModeration",
        "green:VideoModeration"
      ],
      "Resource": "*"
    }
  ]
}
```

## 凭证配置

本 Skill 依赖阿里云默认凭证链自动获取凭证，无需在代码或配置中显式指定。默认凭证链按以下顺序查找：

1. 环境变量（自动读取）
2. 配置文件（~/.alibabacloud/credentials）
3. ECS 实例 RAM 角色
4. OIDC Role ARN

详见 [阿里云凭证链文档](https://help.aliyun.com/document_detail/378659.html)。
