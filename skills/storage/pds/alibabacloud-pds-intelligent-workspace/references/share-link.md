# 文件分享 (Share Link)

## 概述

文件分享功能允许用户对个人空间或团队空间中的文件/文件夹创建分享链接，支持跨组织向外部用户分享。可设置访问密码、有效期、权限控制（预览/下载/上传/编辑）等。

## 前提条件

1. 已完成 PDS 配置（domain_id、user_id、authentication-type），参见 `references/config.md`
2. **超级管理员或网盘管理员已启用分享功能**：管理控制台 > 安全策略 > 分享设置管理 > 开启「启用分享设置」

> **注意事项**：
> - 单日最多支持创建和访问分享各 500 次
> - 若分享链接未设置「仅企业内用户可访问」，则 APK 和 IPA 文件禁止下载（如需解除限制，需管理员完成自定义域名配置）
> - 管理员开启分享设置后，若用户界面未显示分享按钮，请刷新网页或重启客户端

---

## 工作流程

### 创建分享前：解析目标文件

创建分享必须先确认目标空间的 `drive_id`。普通文件/文件夹分享还必须取得要分享对象的 `file_id`；分享整个空间时可使用 `--share-all-files true`，此时不要解析或传入 `--file-id-list`。

- 如果用户已经提供 `drive_id` 和 `file_id`，直接进入创建分享。
- 如果用户明确要求分享整个空间，先取得 `drive_id`，创建分享时使用 `--share-all-files true`，不要传 `--file-id-list`。
- 如果用户提供的是空间名称、文件名或云端路径，先按以下顺序解析：
  1. 读取 `references/drive.md`，确定目标空间并取得 `drive_id`。
  2. 读取 `references/search-file.md`，根据文件名或路径搜索目标文件/文件夹并取得 `file_id`。
  3. 如果搜索到多个候选项，向用户展示候选项的路径、类型、更新时间，并让用户确认。
  4. 如果未找到目标文件/文件夹，停止创建分享并告知用户无法定位目标对象。

不要凭文件名猜测 `file_id`，也不要在未确认唯一目标对象时创建分享。

### 创建分享

确认 `drive_id` 后，按目标类型选择 `--file-id-list` 或 `--share-all-files true`，创建分享链接：

```bash
aliyun pds create-share-link \
  --drive-id <drive_id> \
  --file-id-list <file_id_1> <file_id_2> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pds-intelligent-workspace
```

**过期时间规则**：

- 只有用户明确要求分享在某个时间过期时，才传 `--expiration`。
- 如果用户明确说明“几天后过期”（例如“7 天后过期”），使用当前系统时间加上对应天数，并转换为 RFC 3339 格式，例如 `2026-05-28T15:04:05.000+08:00`。
- 如果用户明确给出具体日期或时间，将其转换为 RFC 3339 格式后作为 `--expiration`。
- 如果用户未明确说明过期时间，不要传 `--expiration`，表示分享链接永不过期。

**参数说明**：

| 参数 | 必填 | 说明 |
|------|------|------|
| `--drive-id` | 是 | 空间 ID |
| `--file-id-list` | 条件必填 | 要分享的文件 ID 列表（1~100个），`share-all-files` 为 true 时不生效 |
| `--share-all-files` | 否 | 是否分享整个空间的所有文件 |
| `--share-name` | 否 | 分享名称，默认使用第一个文件名，最大 128 字符 |
| `--share-pwd` | 否 | 访问密码（提取码），0~64 字节，留空则免密访问 |
| `--expiration` | 否 | 过期时间，RFC 3339 格式；用户未明确说明过期时间时不传该参数，表示永不过期 |
| `--disable-preview` | 否 | 是否禁止预览 |
| `--disable-download` | 否 | 是否禁止下载 |
| `--disable-save` | 否 | 是否禁止转存 |
| `--preview-limit` | 否 | 预览次数限制，0 表示不限 |
| `--download-limit` | 否 | 下载次数限制，0 表示不限 |
| `--save-limit` | 否 | 转存次数限制，0 表示不限 |
| `--creatable` | 否 | 是否允许上传文件到分享文件夹，需同时指定 `creatable-file-id-list` |
| `--creatable-file-id-list` | 否 | 允许上传的文件夹 ID 列表 |
| `--office-editable` | 否 | 是否允许在线编辑文档 |
| `--require-login` | 否 | 是否仅限登录后访问 |
| `--description` | 否 | 分享描述/留言，最大 1024 字符 |
| `--user-id` | 否 | 用户 ID |

**返回示例**：
```json
{
  "share_id": "<share_id>",
  "share_url": "",
  "share_pwd": "<share_pwd>",
  "share_name": "<share_name>",
  "expiration": "<RFC3339_expiration>",
  "created_at": "<RFC3339_created_at>"
}
```

**返回给用户前处理**：

- 创建分享后，先检查 `create-share-link` 返回的 `share_url`。
- 如果 `share_url` 非空，默认直接把该地址返回给用户。
- 如果 `share_url` 为空，必须先取得 `share_id`、`share_pwd` 和 `domain_id`，再查询当前 domain 是否配置了自定义域名：
  ```bash
  aliyun pds get-domain \
    --domain-id <domain_id> \
    --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pds-intelligent-workspace
  ```
- 计算 `<share_host>`：
  - 如果 `get-domain` 返回中存在非空 `endpoints.app_endpoint`，使用该值作为自定义域名；如果该值包含 `http://` 或 `https://` 前缀，先去掉协议前缀。
  - 如果不存在 `endpoints` 对象，或 `endpoints` 中没有 `app_endpoint` 字段，或 `app_endpoint` 为空，表示没有设置自定义域名，使用默认域名 `<domain_id>.apps.aliyunfile.com`。
- `share_url` 为空时，按以下规则组装并返回分享 URL：
  - 有分享密码时：`https://<share_host>/disk/s/<share_id>?pwd=<share_pwd>&domainId=<domain_id>`。
  - 如果 `<share_pwd>` 为空，不要拼接 `pwd` 参数：`https://<share_host>/disk/s/<share_id>?domainId=<domain_id>`。
- `<domain_id>` 使用用户提供或当前 PDS 配置中的 domain id；`<share_id>` 使用创建分享返回的 `share_id`；`<share_pwd>` 使用创建分享时设置或返回的分享密码。

---

### 查看分享列表

列出当前用户创建的所有分享：

```bash
aliyun pds list-share-link \
  --limit 20 \
  --order-by created_at \
  --order-direction DESC \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pds-intelligent-workspace
```

**参数说明**：

| 参数 | 必填 | 说明 |
|------|------|------|
| `--creator` | 否 | 创建者用户 ID |
| `--include-cancelled` | 否 | 是否包含已取消的分享 |
| `--limit` | 否 | 每页最大返回数量，0~100 |
| `--marker` | 否 | 分页标记，首次请求不填 |
| `--order-by` | 否 | 排序字段：`created_at`（默认）、`updated_at`、`share_name`、`description` |
| `--order-direction` | 否 | 排序方向：`ASC` / `DESC` |

**分页处理**：

如果返回结果中包含非空 `next_marker`，说明还有下一页数据。继续执行同一个 `list-share-link` 命令，并将返回的 `next_marker` 作为下一次请求的 `--marker` 参数，直到 `next_marker` 为空。需要统计、筛选或批量处理分享时，必须先遍历全部分页结果。

---

### 搜索分享

按条件搜索分享链接（支持模糊搜索名称、按状态/时间过滤）：

```bash
aliyun pds search-share-link \
  --query "share_name_for_fuzzy = '<share_name_keyword>'" \
  --limit 50 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pds-intelligent-workspace
```

**参数说明**：

| 参数 | 必填 | 说明 |
|------|------|------|
| `--query` | 否 | 搜索条件，支持字段：`created_at`、`updated_at`、`share_name_for_fuzzy`、`status`（enabled/disabled）、`expired_time` |
| `--creators` | 否 | 创建者 ID 列表（管理员可查所有人） |
| `--limit` | 否 | 每页最大返回数量，1~100，默认 100 |
| `--marker` | 否 | 分页标记 |
| `--order-by` | 否 | 排序字段 |
| `--order-direction` | 否 | 排序方向 |
| `--return-total-count` | 否 | 是否返回总数 |

**分页处理**：

如果返回结果中包含非空 `next_marker`，说明还有下一页数据。继续执行同一个 `search-share-link` 命令，并将返回的 `next_marker` 作为下一次请求的 `--marker` 参数，直到 `next_marker` 为空。需要统计、筛选或批量处理分享时，必须先遍历全部分页结果。

---

### 查看分享详情

根据 share_id 查询分享链接详细信息：

```bash
aliyun pds get-share-link \
  --share-id <share_id> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pds-intelligent-workspace
```

---

### 修改分享设置

修改已有分享的权限、密码、有效期等。只传用户明确要求修改的字段，不要传未请求修改的字段：

```bash
aliyun pds update-share-link \
  --share-id <share_id> \
  --<requested-field> <value> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pds-intelligent-workspace
```

**参数说明**：

| 参数 | 必填 | 说明 |
|------|------|------|
| `--share-id` | 是 | 分享 ID |
| `--share-name` | 否 | 修改分享名称 |
| `--share-pwd` | 否 | 修改访问密码 |
| `--expiration` | 否 | 修改过期时间，按创建分享的过期时间规则计算；用户未明确说明过期时间时不要修改该字段 |
| `--description` | 否 | 修改描述 |
| `--disable-preview` | 否 | 是否禁止预览 |
| `--disable-download` | 否 | 是否禁止下载 |
| `--disable-save` | 否 | 是否禁止转存 |
| `--office-editable` | 否 | 是否允许在线编辑 |
| `--preview-limit` | 否 | 预览次数限制 |
| `--download-limit` | 否 | 下载次数限制 |
| `--save-limit` | 否 | 转存次数限制 |
| `--status` | 否 | 分享状态：`enabled`（生效）/ `disabled`（取消） |

---

### 取消分享

取消（删除）分享链接：

```bash
aliyun pds cancel-share-link \
  --share-id <share_id> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pds-intelligent-workspace
```

取消后分享链接立即失效，接收方无法再访问。

---

### 匿名访问分享（可选）

#### 匿名获取分享信息

无需登录即可查看分享的基本信息：

```bash
aliyun pds get-share-link-by-anonymous \
  --share-id <share_id> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pds-intelligent-workspace
```

#### 获取分享 Token

通过分享 ID 和提取码获取访问 Token：

```bash
aliyun pds get-share-link-token \
  --share-id <share_id> \
  --share-pwd <share_pwd> \
  --expire-sec 7200 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pds-intelligent-workspace
```

| 参数 | 必填 | 说明 |
|------|------|------|
| `--share-id` | 是 | 分享 ID |
| `--share-pwd` | 否 | 访问密码（分享设置了密码时必填） |
| `--expire-sec` | 否 | Token 有效期，范围 (0, 7200]，默认 7200 秒 |

---

## 常见场景

### 创建免密、永不过期的分享

```bash
aliyun pds create-share-link \
  --drive-id <drive_id> \
  --file-id-list <file_id> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pds-intelligent-workspace
```

### 创建有密码、7 天有效期、仅允许预览的分享

```bash
aliyun pds create-share-link \
  --drive-id <drive_id> \
  --file-id-list <file_id> \
  --share-pwd "<share_pwd>" \
  --expiration "<current_time_plus_7_days_rfc3339>" \
  --disable-download true \
  --disable-save true \
  --require-login true \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pds-intelligent-workspace
```

### 创建允许外部用户上传文件的分享

```bash
aliyun pds create-share-link \
  --drive-id <drive_id> \
  --file-id-list <folder_id> \
  --creatable true \
  --creatable-file-id-list <folder_id> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pds-intelligent-workspace
```

---

## CLI 命令速查表

| CLI 命令 | 说明 | 必需参数 |
|----------|------|----------|
| `aliyun pds create-share-link` | 创建分享链接 | `--drive-id` |
| `aliyun pds cancel-share-link` | 取消分享链接 | `--share-id` |
| `aliyun pds get-share-link` | 查询分享详情 | `--share-id` |
| `aliyun pds list-share-link` | 列出分享 | 无 |
| `aliyun pds search-share-link` | 搜索分享 | 无 |
| `aliyun pds update-share-link` | 修改分享设置 | `--share-id` |
| `aliyun pds get-share-link-by-anonymous` | 匿名获取分享信息 | `--share-id` |
| `aliyun pds get-share-link-token` | 获取分享访问 Token | `--share-id` |

**注意**：所有命令必须附带 `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-pds-intelligent-workspace`

---

## 错误处理

| 错误场景 | 可能原因 | 解决方案 |
|----------|----------|----------|
| 创建分享失败 | 管理员未开启分享功能 | 联系管理员在「安全策略 > 分享设置管理」中启用 |
| 无法勾选「允许编辑」 | 管理员未开启「分享在线编辑」 | 联系管理员开启后重启客户端 |
| 超出每日限制 | 单日创建/访问分享超过 500 次 | 等待次日或联系管理员配置自定义域名解除限制 |
| 无法下载 APK/IPA | 不支持分享访问，需仅限登录后访问 | 设置 `--require-login true` 或管理员配置自定义域名 |
| 分享链接无法访问 | 分享已过期/已取消/文件被删除 | 联系分享人重新创建 |

---

## 最佳实践

1. 敏感文件分享务必设置访问密码和有效期
2. 使用 `--require-login true` 限制仅限登录后访问，提升安全性
3. 通过 `--preview-limit` / `--download-limit` 限制操作次数防止滥用
4. 定期清理 `disabled` 状态分享：

   先搜索 `disabled` 状态的 share-link，并按分页规则遍历全部结果：

   ```bash
   aliyun pds search-share-link \
     --query "status = 'disabled'" \
     --limit 100 \
     --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pds-intelligent-workspace
   ```

   对确认需要清理的每个 `share_id` 执行取消分享：

   ```bash
   aliyun pds cancel-share-link \
     --share-id <share_id> \
     --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pds-intelligent-workspace
   ```

5. 创建分享前确认文件 ID 正确（可通过 `references/search-file.md` 搜索文件获取 file_id）
