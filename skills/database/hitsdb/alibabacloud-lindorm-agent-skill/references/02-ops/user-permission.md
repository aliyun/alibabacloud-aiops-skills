# Account and Permission Management Scenarios

## Trigger Conditions

**User intent:** Create database users, configure table-level permissions, and implement permission isolation.

**Typical questions:**
- "How do I create a read-only account?"
- "How do I configure an independent account for the development environment?"
- "Can I restrict a user to access only specified tables?"
- "How do I view a user's permission list?"
- "How do I revoke user permissions?"

---

## Agent Behavior Principles

**⚠️ Safety boundary: Provide permission configuration guidance. Do not directly create users or grant permissions.**

1. **Query capability:** The Agent currently has no API to directly query user lists or permissions.
2. **Provide solutions:** Provide best practices and operation steps for permission configuration.
3. **Guide operations:** Guide users to manage permissions through the Lindorm Insight console.
4. **Do not execute changes:** Do not directly create users, grant permissions, or revoke permissions.
5. **Permission keywords:** Lindorm SQL uses the READ/WRITE/SYSTEM/ADMIN/TRASH permission system, which is different from MySQL SELECT/INSERT/UPDATE/DELETE.
6. **V1/V2 instance differences:** Old Lindorm instances manage user permissions through Lindorm Insight, ClusterManager. **New Lindorm instances** must use the unified user authentication and permission management system. The operation method is different, so confirm the instance version first.

---

## Execution Flow

### Official Documentation Reference

**Account and permission management related documentation:**
- User and permission management: https://help.aliyun.com/zh/lindorm/user-guide/user-and-permission-management
- Ranger permission configuration: https://help.aliyun.com/zh/lindorm/user-guide/use-ranger-to-control-data-access
- SQL permission management: https://help.aliyun.com/zh/lindorm/user-guide/manage-namespaces
- Access control, RAM: https://help.aliyun.com/zh/lindorm/security-and-compliance/

### Provide Configuration Solutions Based on User Scenarios

---

## Output Examples

### Complete Conversation Example 1: Create a Read-only Account

**User:** "I want to create a read-only account for the BI team."

**Agent:**
```markdown
Sure, I can help you create a read-only account. Lindorm supports two permission management methods. I recommend using the **Lindorm Insight console** because it is more intuitive.

## Read-only Account Creation Solution

### Solution 1: Through the Lindorm Insight Console, Recommended

#### Step 1: Log on to Lindorm Insight
1. Log on to the [Lindorm console](https://lindorm.console.aliyun.com/).
2. On the instance list page, click the **target instance ID**.
3. In the left-side navigation pane, click **Database Connection**.
4. In the **Lindorm Insight** area of the wide table engine page, click **Access through ClusterManager Public Network** or private network access.
5. Enter the username and password to log on.

⚠️ **Password reset is required for first logon:**
- In the Lindorm Insight area of the wide table engine page, click **Reset UI Access Password**.
- Password rule: 2 to 30 characters, containing one or more of uppercase letters, lowercase letters, special characters, and digits.
- Allowed special characters: `_` and `-`.

#### Step 2: Create a Read-only User
1. Lindorm Insight page → left-side menu → **Data Management > User Management**.
2. Click "Create User".
3. Configure parameters:
   ```text
   Username: bi_readonly
   Password: ********, strong password containing uppercase and lowercase letters + digits + special characters
   Confirm password: ********
   ```
4. Click "OK".

#### Step 3: Grant Read-only Permission
1. User list → find `bi_readonly` → click "Authorize".
2. Select permission type:
   ```text
   Permission scope: Specified namespace and table
   Namespace: default, or your business namespace
   Table name: *, all tables, or specified table names
   Permission type: ☑️ Read-only, READ
   ```
3. Click "OK".

#### Step 4: Verify Permissions
The new user can connect in the following way:

**Connection information:**
> The Agent automatically selects the correct V1/V2 domain name format based on instance ServiceType. See `sql-client-guide.md` → "Connection domain name format".

```bash
mysql -h <connection_address> -P 33060 -u bi_readonly -p
# Address retrieval: console instance details → Database Connection, or aliyun hitsdb get-lindorm-instance-engine-list --instance-id <id>
```

**Test read-only permission:**
```sql
-- Allowed operation.
SELECT * FROM default.user_table LIMIT 10;  -- ✅ Success

-- Disallowed operations.
CREATE TABLE test_table (...);  -- ❌ Insufficient permissions
INSERT INTO default.user_table VALUES (...);  -- ❌ Insufficient permissions
DELETE FROM default.user_table WHERE ...;  -- ❌ Insufficient permissions
```

### Solution 2: Through SQL Operations

⚠️ **Note: The Lindorm SQL permission system is different from MySQL. It uses READ/WRITE/SYSTEM/ADMIN/TRASH keywords.**

#### Step 1: Connect with an Administrator Account
```bash
# MySQL protocol connection, recommended.
mysql -h <connection_address> -P 33060 -u root -p
```

#### Step 2: Create a User and Grant Permissions
```sql
-- 1. Create a user.
CREATE USER IF NOT EXISTS bi_readonly identified BY 'YourStrongPassword123!';

-- 2. Grant read-only permission on specified tables. Confirm that the tables exist first.
GRANT READ ON TABLE default.user_table TO bi_readonly;
GRANT READ ON TABLE default.order_table TO bi_readonly;

-- Or grant read-only permission on the entire database. If database is a reserved word, use backticks.
GRANT READ ON DATABASE `default` TO bi_readonly;

-- Grant read/write permissions.
GRANT READ, WRITE ON DATABASE dev TO dev_user;

-- 3. View all user permissions.
SHOW PRIVILEGES;

-- View all users.
SHOW USERS;
```

#### Step 3: Verify Permissions
Log on as the new user and test:
```bash
mysql -h <connection_address> -P 33060 -u bi_readonly -p
```

### Permission Mapping Table

| Permission Type | SQL Keyword | Allowed Operations |
|---------|----------|-----------|
| Read-only | READ | Query data |
| Read/write | READ, WRITE | Query, insert, update, delete |
| Administrator | ADMIN | Create/drop tables, indexes, and other DDL operations |
| Delete | TRASH | TRUNCATE TABLE, clear table data |
| System | SYSTEM | Manage user permissions, COMPACT, FLUSH, and other O&M operations, global grant only |

### Security Suggestions

✅ **Recommended practices:**
- Create independent accounts for different environments, such as production, test, and development.
- Use strong passwords, at least 12 characters, containing uppercase and lowercase letters + digits + special characters.
- Rotate passwords regularly, recommended every 90 days.
- Follow the principle of least privilege and grant only necessary permissions.
- Set stricter permissions for sensitive tables.

❌ **Practices to avoid:**
- Do not share the default administrator account.
- Do not grant administrator permissions to all users.
- Do not use weak passwords, such as 123456 or password.

### Official Documentation
- Complete permission management guide: https://help.aliyun.com/zh/lindorm/user-guide/user-and-permission-management
- SQL permission commands: https://help.aliyun.com/zh/lindorm/user-guide/manage-namespaces
```

---

### Complete Conversation Example 2: Configure Table-level Permission Isolation

**User:** "The development team and O&M team need to access different tables. How do I configure this?"

**Agent:**
```markdown
Sure, I can help you plan a table-level permission isolation solution.

## Table-level Permission Isolation Solution

### Business Scenario Analysis
- **Development team:** Needs access to development environment tables, read/write.
- **O&M team:** Needs access to all tables, but read-only, for monitoring and troubleshooting.
- **Isolation goal:** The development team cannot access production tables, and the O&M team cannot modify data.

### Recommended Solution: Namespace + Table-level Permissions

#### Step 1: Plan Namespace Structure
```text
lindorm_instance
├── namespace: prod, production environment
│   ├── user_table
│   ├── order_table
│   └── payment_table
├── namespace: dev, development environment
│   ├── test_user_table
│   └── test_order_table
└── namespace: staging, pre-release environment
    └── staging_user_table
```

#### Step 2: Create Users and Grant Permissions

**2.1 Create a development team account**
```sql
-- Create through Lindorm Insight or SQL.
CREATE USER IF NOT EXISTS dev_team identified BY 'DevPassword123!';

-- Grant read/write permissions on the dev database.
GRANT READ, WRITE ON DATABASE dev TO dev_team;

-- View permissions.
SHOW PRIVILEGES;
```

**2.2 Create an O&M team account**
```sql
-- Create a user.
CREATE USER IF NOT EXISTS ops_team identified BY 'OpsPassword123!';

-- Grant read-only permissions on all databases.
GRANT READ ON DATABASE prod TO ops_team;
GRANT READ ON DATABASE dev TO ops_team;
GRANT READ ON DATABASE staging TO ops_team;

-- View permissions.
SHOW PRIVILEGES;
```

#### Step 3: Verify Permission Isolation

**Development team test:**
```sql
-- Connection: mysql -h <connection_address> -P 33060 -u dev_team -p

-- ✅ Can operate the dev namespace.
SELECT * FROM dev.test_user_table;
INSERT INTO dev.test_user_table VALUES (...);

-- ❌ Cannot access the prod namespace.
SELECT * FROM prod.user_table;  -- Error: insufficient permissions
```

**O&M team test:**
```sql
-- Connection: mysql -h <connection_address> -P 33060 -u ops_team -p

-- ✅ Can query all namespaces.
SELECT * FROM prod.user_table;
SELECT * FROM dev.test_user_table;

-- ❌ Cannot modify data.
INSERT INTO prod.user_table VALUES (...);  -- Error: insufficient permissions
DELETE FROM prod.user_table WHERE ...;  -- Error: insufficient permissions
```

### More Fine-grained Permission Control

If finer-grained control is required, such as allowing access only to specified columns, use **Ranger**:

#### Step 1: Enable Ranger
1. Lindorm console → Instance details → Database Connection.
2. Compute engine → click "Enable Ranger Address".

#### Step 2: Configure Ranger Policies
1. Access the Ranger management page.
2. Create a policy:
   ```text
   Policy name: dev_team_policy
   Resources:
     - Namespace: dev
     - Table: *, all tables
     - Column: *, all columns
   User/group: dev_team
   Permissions: READ, WRITE
   ```

#### Step 3: Configure Column-level Permissions, Optional
```text
Policy name: ops_sensitive_data_mask
Resources:
  - Namespace: prod
  - Table: user_table
  - Columns: phone, id_card, sensitive columns
User/group: ops_team
Permissions: READ
```

### Permission Management Best Practices

#### 1. Use User Groups, Recommended
```text
User group classification:
- admin_group: administrator group, DBA
- dev_group: development group
- ops_group: O&M group
- readonly_group: read-only group, BI and analysis

Benefits:
- New users inherit permissions after joining a group.
- Unified management avoids repeated authorization.
- Convenient for permission audit.
```

#### 2. Permission Application Process
```text
1. Developer submits a ticket to request permissions.
2. DBA reviews and creates the account.
3. Grant the minimum necessary permissions.
4. Regularly review and revoke unused permissions.
```

#### 3. Audit Log Monitoring
```text
Enable SQL audit logs, console → wide table engine → SQL audit logs.
Monitor:
- Who accessed which tables
- Which operations were executed
- Whether unauthorized access occurred
```

### Official Documentation
- Ranger permission management: https://help.aliyun.com/zh/lindorm/user-guide/use-ranger-to-control-data-access
- Namespace management: https://help.aliyun.com/zh/lindorm/user-guide/log-in-to-the-cluster-management-system
```

---

### Complete Conversation Example 3: Revoke User Permissions

**User:** "An employee has left. How do I revoke their account permissions?"

**Agent:**
```markdown
Understood. Employee departure requires timely permission revocation to ensure security.

## Account Permission Revocation Solution

### Solution 1: Delete the User, Complete Removal

#### Through the Lindorm Insight Console
1. Log on to the [Lindorm console](https://lindorm.console.aliyun.com/) and enter the **Database Connection** page of the target instance.
2. In the **Lindorm Insight** area of the wide table engine page, click **Access through ClusterManager Public Network**.
3. After logging on to Lindorm Insight, go to **Data Management > User Management** → **User List**.
4. Find the target user → click "Delete".
5. Confirm deletion.

#### Through SQL Commands
```sql
-- 1. View existing user permissions.
SHOW PRIVILEGES;

-- 2. Delete the user. All permissions are automatically revoked.
DROP USER employee_username;

-- 3. Verify deletion.
SHOW USERS;
-- The target user is no longer in the list, indicating deletion succeeded.
```

### Solution 2: Disable the User, Keep Account but Temporarily Disable

Lindorm does not currently support directly disabling users. Recommended alternatives:

#### Solution A: Revoke All Permissions
```sql
-- View the user's current permissions.
SHOW PRIVILEGES;

-- Revoke permissions one by one.
REVOKE READ ON DATABASE prod FROM employee_username;
REVOKE READ, WRITE ON DATABASE dev FROM employee_username;

-- Verify that permissions have been revoked.
SHOW PRIVILEGES;
```

#### Solution B: Change Password, Invalidating the Original Password
```sql
-- Change to a random strong password so that the user can no longer log on.
ALTER USER employee_username SET PASSWORD = 'RandomStrongPassword!@#$%123456';
```

### Solution 3: Batch Revoke Permissions, Multiple Departed Employees

If multiple employees have left, process them in batches with scripts:

```sql
-- Delete multiple users.
DROP USER 'employee1';
DROP USER 'employee2';
DROP USER 'employee3';

-- Or execute in a script loop.
```

### Permission Revocation Checklist

After permission revocation, check the following items:

- [ ] **Database account**: deleted or disabled.
- [ ] **Whitelist IP**: removed the departed employee's office IP.
- [ ] **RAM account**: deleted or disabled the Alibaba Cloud RAM user.
- [ ] **Alert contact**: removed from alert contact groups.
- [ ] **Keys/certificates**: rotated related keys and certificates.
- [ ] **Audit logs**: checked whether abnormal operations occurred before departure.

### Security Suggestions

✅ **Recommended practices:**
1. **Immediate revocation:** Revoke all permissions on the employee's departure day.
2. **Delete after handover:** Delete the account after confirming business handover is complete.
3. **Retain audit logs:** Retain user operation audit logs for at least 180 days.
4. **Regular review:** Review user lists quarterly and clean up unused accounts.

⚠️ **Notes:**
- Before deleting a user, confirm that no running application still uses the account.
- If an application still uses it, switch to a new account before deleting the old account.
- Before deleting important accounts, back up operation logs if possible.

### Account Lifecycle Management

It is recommended to establish a complete account lifecycle management process:

```text
1. Onboarding → create account → grant least privilege
2. Employment → regularly review permissions → adjust based on responsibilities
3. Departure → disable immediately → confirm handover → delete account
```

### Official Documentation
- User and permission management: https://help.aliyun.com/zh/lindorm/user-guide/user-and-permission-management
- SQL permission commands: https://help.aliyun.com/zh/lindorm/user-guide/manage-namespaces
```

---

## Missing Parameter Follow-up

| Missing Parameter | Follow-up Wording | Default Strategy |
|---------|---------|----------|
| User type | "Do you want to create a read-only account or a read/write account?" | Recommend a read-only account by default for security |
| Permission scope | "Which namespaces or tables need to be accessed?" | Provide a specified-table permission solution by default |
| Username | "Please provide the username to create." | Provide naming convention suggestions |
| Operation type | "Are you creating a new user or modifying permissions for an existing user?" | Guide as new-user creation by default |

---

## Error Handling

### Common Issues

#### Issue 1: User Creation Failed - Username Already Exists

**Agent output:**
```text
User creation failed. The username may already exist.

Troubleshooting steps:

1. View existing user list.
   - Lindorm Insight → Data Management > User Management → User List
   - Or through SQL: `SHOW USERS;`

2. Select a solution.
   
   Solution A: Use a different username.
   ```sql
   CREATE USER new_username identified BY 'Password123!';
   ```
   
   Solution B: Delete the old user and recreate it.
   ```sql
   -- Delete first.
   DROP USER existing_username;
   -- Then create again.
   CREATE USER existing_username identified BY 'NewPassword123!';
   ```
   
   Solution C: Change the password of the existing user.
   ```sql
   ALTER USER existing_username SET PASSWORD = 'NewPassword123!';
   ```

Official documentation: https://help.aliyun.com/zh/lindorm/user-guide/user-and-permission-management
```

#### Issue 2: Permission Grant Failed - Table Does Not Exist

**Agent output:**
```text
Permission grant failed. The table may not exist.

Troubleshooting steps:

1. Check whether the table exists.
   ```sql
   -- View namespace list.
   SHOW SCHEMAS;
   
   -- View tables in the specified namespace.
   SHOW TABLES IN default;
   ```

2. Confirm table name format.
   When Lindorm SQL is connected through the MySQL protocol, the table name format is: `ON TABLE namespace.table`.
   
   Correct example:
   ```sql
   GRANT READ ON TABLE default.user_table TO username;  -- ✅
   ```
   
   Incorrect example:
   ```sql
   GRANT READ ON user_table TO username;  -- ❌ Missing TABLE keyword and namespace
   ```

3. If the table does not exist:
   - Create the table first, and then grant permissions.
   - Or grant permission on the entire database:
     ```sql
     GRANT READ ON DATABASE `default` TO username;
     ```

Official documentation: https://help.aliyun.com/zh/lindorm/user-guide/manage-namespaces
```

#### Issue 3: User Connection Failed - Authentication Error

**Agent output:**
```text
User connection failed with an authentication error. Check the following:

1. Whether the username is correct.
- Confirm that the username is spelled correctly.
- Lindorm usernames are case-sensitive.

2. Whether the password is correct.
- Confirm that the password is correct.
- Pay attention to case and special characters.

3. Whether whitelist is configured.
- Confirm that the client IP is added to the whitelist.
- Console → Access Control → Whitelist.

4. Whether the connection address is correct.
- Confirm that the correct connection address and port are used. For ports, see SKILL.md → "Port number quick reference".

5. Whether the user has connection permission.
Verify user permissions:
```sql
-- View all users and permissions.
SHOW PRIVILEGES;
SHOW USERS;
```

Test connection:
```bash
# MySQL protocol connection, recommended.
mysql -h <connection_address> -P 33060 -u username -p

# HBase API connection, configured in code.
```

Official documentation: https://help.aliyun.com/zh/lindorm/user-guide/user-and-permission-management
```

---

## Related Scenarios

- Whitelist configuration → go to `../01-dev/connection-guide.md`
- Connection information retrieval → go to `../01-dev/connection-guide.md`
- Audit log query → console operation, no API support
- RAM access control → go to official documentation

---

## Technical Notes

### Why Not Directly Create Users and Grant Permissions?

1. **Security risks:** User accounts and permissions are core security configurations. Incorrect operations may cause:
   - Permission leakage, overly broad authorization
   - Business interruption, accidental user deletion
   - Data leakage, account creation without approval

2. **Password management:** User passwords are sensitive information, and the Agent should not directly generate or manage passwords.

3. **Approval process:** Enterprises usually have strict permission application and approval processes, which should not be bypassed.

4. **Best practice compliance:** Account and permission management should be performed through the console or audited SQL operations for traceability and audit.

### Value Provided by the Agent

- ✅ Provides permission planning solutions and best practices
- ✅ Provides complete permission configuration steps and SQL commands
- ✅ Provides permission isolation and security hardening suggestions
- ✅ Provides complete troubleshooting solutions for permission issues
- ✅ Provides permission lifecycle management guidance
