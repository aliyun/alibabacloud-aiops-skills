# 账号权限管理场景

## 触发条件
**用户意图：** 创建数据库用户、配置表级权限、实现权限隔离。

**典型问法：**
- "怎么创建一个只读账号？"
- "如何给开发环境配置独立的账号？"
- "能限制某个用户只能访问指定的表吗？"
- "怎么查看用户的权限列表？"
- "如何回收用户权限？"

---

## Agent 行为原则

**⚠️ 安全边界：提供权限配置指导，不直接创建用户或授权**

1. **查询能力：** Agent 暂无直接查询用户列表和权限的 API
2. **提供方案：** 提供权限配置的最佳实践和操作步骤
3. **引导操作：** 引导用户通过 Lindorm Insight 控制台进行权限管理
4. **不执行变更：** 不直接创建用户、授权或回收权限
5. **权限关键字：** Lindorm SQL 使用 READ/WRITE/SYSTEM/ADMIN/TRASH 权限体系，与 MySQL 的 SELECT/INSERT/UPDATE/DELETE 不同
6. **V1/V2 实例区别：** Lindorm 旧版实例通过 Lindorm Insight（ClusterManager）管理用户权限；**Lindorm 新版实例**需使用「统一用户认证及权限管理系统」，操作方式不同，需先确认实例版本

---

## 执行流程

### 官方文档参考
**账号权限管理相关文档：**
- 用户权限管理：https://help.aliyun.com/zh/lindorm/user-guide/user-and-permission-management
- Ranger 权限配置：https://help.aliyun.com/zh/lindorm/user-guide/use-ranger-to-control-data-access
- SQL 权限管理：https://help.aliyun.com/zh/lindorm/user-guide/manage-namespaces
- 访问控制（RAM）：https://help.aliyun.com/zh/lindorm/security-and-compliance/

### 根据用户场景提供配置方案

---

## 输出示例

### 完整对话示例1：创建只读账号

**用户：** "我想创建一个只读账号给 BI 团队使用"

**Agent：**
```markdown
好的，我来帮您创建一个只读账号。Lindorm 支持两种权限管理方式，我推荐使用 **Lindorm Insight 控制台**（更直观）。

## 只读账号创建方案

### 方案1：通过 Lindorm Insight 控制台（推荐）

#### 步骤1：登录 Lindorm Insight
1. 登录 [Lindorm 控制台](https://lindorm.console.aliyun.com/)
2. 在实例列表页面，单击**目标实例ID**
3. 在左侧导航栏，单击**数据库连接**
4. 在宽表引擎页面的 **Lindorm Insight** 区域中，单击**通过 ClusterManager 公网访问**（或专有网络访问）
5. 输入用户名和密码登录

⚠️ **首次登录需重置密码：**
- 在宽表引擎页面的 Lindorm Insight 区域中，单击**重置 UI 访问密码**
- 密码规则：2~30位，需包含大写字母、小写字母、特殊字符和数字中的一种或多种
- 允许的特殊字符：`_` 和 `-`

#### 步骤2：创建只读用户
1. Lindorm Insight 页面 → 左侧菜单 → **数据管理 > 用户管理**
2. 点击"创建用户"
3. 配置参数：
   ```
   用户名：bi_readonly
   密码：********（强密码，包含大小写字母+数字+特殊字符）
   确认密码：********
   ```
4. 点击"确定"

#### 步骤3：授予只读权限
1. 用户列表 → 找到 `bi_readonly` → 点击"授权"
2. 选择权限类型：
   ```
   权限范围：指定命名空间和表
   命名空间：default（或您的业务命名空间）
   表名：*（所有表）或指定表名
   权限类型：☑️ 只读（READ）
   ```
3. 点击"确定"

#### 步骤4：验证权限
新用户可以使用以下方式连接：

**连接信息：**
> Agent 根据实例 ServiceType 自动选择正确的 V1/V2 域名格式，参见 `sql-client-guide.md` →「连接域名格式」

```bash
mysql -h <您的连接地址> -P 33060 -u bi_readonly -p
# 地址获取：控制台实例详情 → 数据库连接，或 aliyun hitsdb get-lindorm-instance-engine-list --instance-id <id>
```

**测试只读权限：**
```sql
-- 可以执行的操作
SELECT * FROM default.user_table LIMIT 10;  -- ✅ 成功

-- 不能执行的操作
CREATE TABLE test_table (...);  -- ❌ 权限不足
INSERT INTO default.user_table VALUES (...);  -- ❌ 权限不足
DELETE FROM default.user_table WHERE ...;  -- ❌ 权限不足
```

### 方案2：通过 SQL 操作

⚠️ **注意：Lindorm SQL 权限体系与 MySQL 不同，使用 READ/WRITE/SYSTEM/ADMIN/TRASH 关键字**

#### 步骤1：使用管理员账号连接
```bash
# MySQL 协议连接（推荐）
mysql -h <您的连接地址> -P 33060 -u root -p
```

#### 步骤2：创建用户并授权
```sql
-- 1. 创建用户
CREATE USER IF NOT EXISTS bi_readonly identified BY 'YourStrongPassword123!';

-- 2. 授予指定表的只读权限（需先确认表存在）
GRANT READ ON TABLE default.user_table TO bi_readonly;
GRANT READ ON TABLE default.order_table TO bi_readonly;

-- 或授予整个数据库的只读权限（database 名若为保留字需用反引号）
GRANT READ ON DATABASE `default` TO bi_readonly;

-- 授予读写权限
GRANT READ, WRITE ON DATABASE dev TO dev_user;

-- 3. 查看所有用户权限
SHOW PRIVILEGES;

-- 查看所有用户
SHOW USERS;
```

#### 步骤3：验证权限
使用新用户登录并测试：
```bash
mysql -h <您的连接地址> -P 33060 -u bi_readonly -p
```

### 权限对照表

| 权限类型 | SQL 关键字 | 允许的操作 |
|---------|----------|-----------|
| 只读 | READ | 查询数据 |
| 读写 | READ, WRITE | 查询、插入、更新、删除 |
| 管理员 | ADMIN | 创建/删除表和索引等 DDL |
| 删除 | TRASH | TRUNCATE TABLE（清空表数据） |
| 系统 | SYSTEM | 管理用户权限、COMPACT、FLUSH 等运维操作（仅全局授权） |

### 安全建议

✅ **推荐做法：**
- 为不同环境创建独立账号（生产/测试/开发）
- 使用强密码（至少 12 位，包含大小写字母+数字+特殊字符）
- 定期轮换密码（建议 90 天）
- 遵循最小权限原则（只授予必要的权限）
- 对敏感表设置更严格的权限

❌ **避免做法：**
- 不要共享默认管理员账号
- 不要给所有用户授予管理员权限
- 不要使用弱密码（如 123456、password）

### 官方文档
- 完整权限管理指南：https://help.aliyun.com/zh/lindorm/user-guide/user-and-permission-management
- SQL 权限命令：https://help.aliyun.com/zh/lindorm/user-guide/manage-namespaces
```

---

### 完整对话示例2：配置表级权限隔离

**用户：** "开发团队和运维团队需要访问不同的表，怎么配置？"

**Agent：**
```markdown
好的，我来帮您规划表级权限隔离方案。

## 表级权限隔离方案

### 业务场景分析
- **开发团队：** 需要访问开发环境的表，可读写
- **运维团队：** 需要访问所有表，但只读（监控、排查问题）
- **隔离目标：** 开发团队不能访问生产表，运维团队不能修改数据

### 推荐方案：命名空间 + 表级权限

#### 步骤1：规划命名空间结构
```
lindorm_instance
├── namespace: prod（生产环境）
│   ├── user_table
│   ├── order_table
│   └── payment_table
├── namespace: dev（开发环境）
│   ├── test_user_table
│   └── test_order_table
└── namespace: staging（预发环境）
    └── staging_user_table
```

#### 步骤2：创建用户并授权

**2.1 创建开发团队账号**
```sql
-- 通过 Lindorm Insight 或 SQL 创建
CREATE USER IF NOT EXISTS dev_team identified BY 'DevPassword123!';

-- 授予 dev 数据库的读写权限
GRANT READ, WRITE ON DATABASE dev TO dev_team;

-- 查看权限
SHOW PRIVILEGES;
```

**2.2 创建运维团队账号**
```sql
-- 创建用户
CREATE USER IF NOT EXISTS ops_team identified BY 'OpsPassword123!';

-- 授予所有数据库的只读权限
GRANT READ ON DATABASE prod TO ops_team;
GRANT READ ON DATABASE dev TO ops_team;
GRANT READ ON DATABASE staging TO ops_team;

-- 查看权限
SHOW PRIVILEGES;
```

#### 步骤3：验证权限隔离

**开发团队测试：**
```sql
-- 连接：mysql -h <您的连接地址> -P 33060 -u dev_team -p

-- ✅ 可以操作 dev 命名空间
SELECT * FROM dev.test_user_table;
INSERT INTO dev.test_user_table VALUES (...);

-- ❌ 不能访问 prod 命名空间
SELECT * FROM prod.user_table;  -- 报错：权限不足
```

**运维团队测试：**
```sql
-- 连接：mysql -h <您的连接地址> -P 33060 -u ops_team -p

-- ✅ 可以查询所有命名空间
SELECT * FROM prod.user_table;
SELECT * FROM dev.test_user_table;

-- ❌ 不能修改数据
INSERT INTO prod.user_table VALUES (...);  -- 报错：权限不足
DELETE FROM prod.user_table WHERE ...;  -- 报错：权限不足
```

### 更细粒度的权限控制

如果需要更细粒度的控制（如只允许访问指定的列），可以使用 **Ranger**：

#### 步骤1：开通 Ranger
1. Lindorm 控制台 → 实例详情 → 数据库连接
2. 计算引擎 → 点击"开通 Ranger 地址"

#### 步骤2：配置 Ranger 策略
1. 访问 Ranger 管理页面
2. 创建策略：
   ```
   策略名称：dev_team_policy
   资源：
     - 命名空间：dev
     - 表：*（所有表）
     - 列：*（所有列）
   用户/组：dev_team
   权限：READ, WRITE
   ```

#### 步骤3：配置列级权限（可选）
```
策略名称：ops_sensitive_data_mask
资源：
  - 命名空间：prod
  - 表：user_table
  - 列：phone, id_card（敏感列）
用户/组：ops_team
权限：READ
```

### 权限管理最佳实践

#### 1. 使用用户组（推荐）
```
用户组划分：
- admin_group：管理员组（DBA）
- dev_group：开发组
- ops_group：运维组
- readonly_group：只读组（BI、分析）

好处：
- 新用户加入组即可继承权限
- 统一管理，避免重复授权
- 便于权限审计
```

#### 2. 权限申请流程
```
1. 开发人员提交工单申请权限
2. DBA 审核并创建账号
3. 授予最小必要权限
4. 定期审查和回收不用的权限
```

#### 3. 审计日志监控
```
开通 SQL 审计日志（控制台 → 宽表引擎 → SQL审计日志）
监控：
- 谁访问了哪些表
- 执行了哪些操作
- 是否有越权访问
```

### 官方文档
- Ranger 权限管理：https://help.aliyun.com/zh/lindorm/user-guide/use-ranger-to-control-data-access
- 命名空间管理：https://help.aliyun.com/zh/lindorm/user-guide/log-in-to-the-cluster-management-system
```

---

### 完整对话示例3：回收用户权限

**用户：** "一个员工离职了，怎么回收他的账号权限？"

**Agent：**
```markdown
明白了，员工离职需要及时回收权限以保障安全。

## 账号权限回收方案

### 方案1：删除用户（彻底移除）

#### 通过 Lindorm Insight 控制台
1. 登录 [Lindorm 控制台](https://lindorm.console.aliyun.com/)，进入目标实例的**数据库连接**页面
2. 在宽表引擎页面的 **Lindorm Insight** 区域中，单击**通过 ClusterManager 公网访问**
3. 登录 Lindorm Insight 后，进入**数据管理 > 用户管理** → **用户列表**
4. 找到目标用户 → 点击"删除"
5. 确认删除

#### 通过 SQL 命令
```sql
-- 1. 查看现有用户权限
SHOW PRIVILEGES;

-- 2. 删除用户（自动回收所有权限）
DROP USER employee_username;

-- 3. 验证删除
SHOW USERS;
-- 目标用户不再列表中，说明已删除
```

### 方案2：禁用用户（保留账号，临时禁用）

Lindorm 暂不支持直接禁用用户，建议：

#### 方案A：回收所有权限
```sql
-- 查看用户当前权限
SHOW PRIVILEGES;

-- 逐一回收权限
REVOKE READ ON DATABASE prod FROM employee_username;
REVOKE READ, WRITE ON DATABASE dev FROM employee_username;

-- 验证权限已回收
SHOW PRIVILEGES;
```

#### 方案B：修改密码（使原密码失效）
```sql
-- 修改为随机强密码，用户无法再登录
ALTER USER employee_username SET PASSWORD = 'RandomStrongPassword!@#$%123456';
```

### 方案3：批量回收权限（多个离职员工）

如果有多个员工离职，可以使用脚本批量处理：

```sql
-- 删除多个用户
DROP USER 'employee1';
DROP USER 'employee2';
DROP USER 'employee3';

-- 或使用脚本循环执行
```

### 权限回收检查清单

完成权限回收后，请检查以下项目：

- [ ] **数据库账号**：已删除或禁用
- [ ] **白名单 IP**：已移除离职员工的办公 IP
- [ ] **RAM 账号**：已删除或禁用阿里云 RAM 子账号
- [ ] **报警联系人**：已从报警联系人组中移除
- [ ] **密钥/证书**：已轮换相关密钥和证书
- [ ] **审计日志**：检查离职前是否有异常操作

### 安全建议

✅ **推荐做法：**
1. **立即回收：** 员工离职当天立即回收所有权限
2. **交接完成后删除：** 确认业务交接完成后再删除账号
3. **审计日志保留：** 保留用户的操作审计日志至少 180 天
4. **定期审查：** 每季度审查用户列表，清理不再使用的账号

⚠️ **注意事项：**
- 删除用户前，确认没有正在运行的应用使用该账号
- 如果应用还在使用，先切换到新账号再删除旧账号
- 重要账号删除前，建议先备份操作日志

### 账号生命周期管理

建议建立完整的账号生命周期管理流程：

```
1. 入职 → 创建账号 → 授予最小权限
2. 在职 → 定期审查权限 → 根据职责调整
3. 离职 → 立即禁用 → 确认交接 → 删除账号
```

### 官方文档
- 用户权限管理：https://help.aliyun.com/zh/lindorm/user-guide/user-and-permission-management
- SQL 权限命令：https://help.aliyun.com/zh/lindorm/user-guide/manage-namespaces
```

---

## 缺参追问

| 缺失参数 | 追问话术 | 默认策略 |
|---------|---------|----------|
| 用户类型 | "请问是创建只读账号还是读写账号？" | 默认推荐只读账号（安全） |
| 权限范围 | "需要访问哪些命名空间或表？" | 默认提供指定表权限方案 |
| 用户名 | "请提供要创建的用户名" | 提供命名规范建议 |
| 操作类型 | "是创建新用户还是修改现有用户权限？" | 默认按创建新用户引导 |

---

## 错误处理

### 常见问题

#### 问题1：用户创建失败 - 用户名已存在

**Agent 输出：**
```
用户创建失败，可能是用户名已存在。

**排查步骤：**

1. **查看现有用户列表**
   - Lindorm Insight → 数据管理 > 用户管理 → 用户列表
   - 或通过 SQL：`SHOW USERS;`

2. **选择解决方案**
   
   **方案A：使用不同的用户名**
   ```sql
   CREATE USER new_username identified BY 'Password123!';
   ```
   
   **方案B：删除旧用户后重新创建**
   ```sql
   -- 先删除
   DROP USER existing_username;
   -- 再创建
   CREATE USER existing_username identified BY 'NewPassword123!';
   ```
   
   **方案C：修改现有用户密码**
   ```sql
   ALTER USER existing_username SET PASSWORD = 'NewPassword123!';
   ```

**官方文档：** https://help.aliyun.com/zh/lindorm/user-guide/user-and-permission-management
```

#### 问题2：权限授予失败 - 表不存在

**Agent 输出：**
```
权限授予失败，可能是表不存在。

**排查步骤：**

1. **查看表是否存在**
   ```sql
   -- 查看命名空间列表
   SHOW SCHEMAS;
   
   -- 查看指定命名空间的表
   SHOW TABLES IN default;
   ```

2. **确认表名格式**
   Lindorm SQL 通过 MySQL 协议连接时，表名格式为：`ON TABLE namespace.table`
   
   **正确示例：**
   ```sql
   GRANT READ ON TABLE default.user_table TO username;  -- ✅
   ```
   
   **错误示例：**
   ```sql
   GRANT READ ON user_table TO username;  -- ❌ 缺少 TABLE 关键字和命名空间
   ```

3. **如果表确实不存在**
   - 先创建表，再授权
   - 或授予整个数据库的权限：
     ```sql
     GRANT READ ON DATABASE `default` TO username;
     ```

**官方文档：** https://help.aliyun.com/zh/lindorm/user-guide/manage-namespaces
```

#### 问题3：用户连接失败 - 认证错误

**Agent 输出：**
```
用户连接失败，认证错误，请检查：

**1. 用户名是否正确**
- 确认用户名拼写无误
- Lindorm 用户名区分大小写

**2. 密码是否正确**
- 确认密码无误
- 注意大小写和特殊字符

**3. 白名单是否配置**
- 确认客户端 IP 已加入白名单
- 控制台 → 访问控制 → 白名单

**4. 连接地址是否正确**
- 确认使用正确的连接地址和端口（端口见 SKILL.md →「端口号速查表」）

**5. 用户是否有连接权限**
验证用户权限：
```sql
-- 查看所有用户及权限
SHOW PRIVILEGES;
SHOW USERS;
```

**测试连接：**
```bash
# MySQL 协议连接（推荐）
mysql -h <您的连接地址> -P 33060 -u username -p

# HBase API 连接（需要在代码中配置）
```

**官方文档：** https://help.aliyun.com/zh/lindorm/user-guide/user-and-permission-management
```

---

## 关联场景

- 白名单配置 → 跳转 `../01-dev/connection-guide.md`
- 连接信息获取 → 跳转 `../01-dev/connection-guide.md`
- 审计日志查询 → 控制台操作，无 API 支持
- RAM 访问控制 → 跳转官方文档

---

## 技术说明

### 为何不直接创建用户和授权？

1. **安全风险：** 用户账号和权限是核心安全配置，错误操作可能导致：
   - 权限泄漏（授权过大）
   - 业务中断（误删用户）
   - 数据泄露（未经审批的账号创建）

2. **密码管理：** 用户密码是敏感信息，Agent 不应直接生成或管理密码

3. **审批流程：** 企业通常有严格的权限申请和审批流程，不应绕过

4. **符合最佳实践：** 账号和权限管理应通过控制台或审计的 SQL 操作，便于追溯和审计

### Agent 提供的价值

- ✅ 提供权限规划方案和最佳实践
- ✅ 完整的权限配置步骤和 SQL 命令
- ✅ 权限隔离和安全加固建议
- ✅ 排查权限问题的完整方案
- ✅ 权限生命周期管理指导
