# User & Role Management (RBAC)

## User Operations

```python
# Create a user
client.create_user(user_name="analyst", password="SecureP@ss123")

# List users
users = client.list_users()

# Describe a user (shows assigned roles)
info = client.describe_user(user_name="analyst")

# Update password
client.update_password(user_name="analyst", old_password="SecureP@ss123", new_password="NewP@ss456")

# Grant role to user
client.grant_role(user_name="analyst", role_name="read_only")

# Revoke role from user
client.revoke_role(user_name="analyst", role_name="read_only")

# Drop a user
client.drop_user(user_name="analyst")
```

## Role Operations

```python
# Create a role
client.create_role(role_name="read_only")

# List roles
roles = client.list_roles()

# Grant privilege (v2 API — recommended)
client.grant_privilege_v2(
    role_name="read_only",
    privilege="Search",                 # e.g., "Search", "Insert", "Query", "Delete"
    collection_name="my_collection",    # Use "*" for all collections
    db_name="default"                   # Use "*" for all databases
)

# Built-in privilege groups
client.grant_privilege_v2(
    role_name="admin_role",
    privilege="ClusterAdmin",           # See privilege groups below
    collection_name="*",
    db_name="*"
)

# Revoke privilege
client.revoke_privilege_v2(
    role_name="read_only",
    privilege="Search",
    collection_name="my_collection",
    db_name="default"
)

# Describe role (see granted privileges)
info = client.describe_role(role_name="read_only")

# Drop a role
client.drop_role(role_name="read_only")
```

## Built-in Privilege Groups

| Group | Scope |
|-------|-------|
| `ClusterAdmin` | Full cluster access |
| `ClusterReadOnly` | Read-only cluster access |
| `ClusterReadWrite` | Read-write cluster access |
| `DatabaseAdmin` | Full database access |
| `DatabaseReadOnly` | Read-only database access |
| `DatabaseReadWrite` | Read-write database access |
| `CollectionAdmin` | Full collection access |
| `CollectionReadOnly` | Read-only collection access |
| `CollectionReadWrite` | Read-write collection access |

## Common Individual Privileges

`Search`, `Query`, `Insert`, `Delete`, `Upsert`, `CreateIndex`, `DropIndex`, `CreateCollection`, `DropCollection`, `Load`, `Release`, `CreatePartition`, `DropPartition`

## Guidance

- Recommended workflow: create role -> grant privileges -> create user -> assign role.
- Use `"*"` for collection_name/db_name to grant on all resources.
- Before dropping a user or role, confirm with the user.
