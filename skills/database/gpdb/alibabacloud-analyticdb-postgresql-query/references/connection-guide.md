# Connection Guide

## Prerequisites

### psql Installation

> **Priority**: Use the ADBPG official client package (Linux) or Docker image whenever possible — it ensures version compatibility with the ADBPG server. Only fall back to generic PostgreSQL psql when the official package is unavailable for your platform.

**Method 1: ADBPG Official Client Package (Recommended for Linux)**

Download the ADBPG client package from the [ADBPG console](https://help.aliyun.com/zh/analyticdb/analyticdb-for-postgresql/user-guide/psql) and extract:

```bash
# ADBPG 7.0 (RHEL 7 / CentOS 7)
tar -xzvf adbpg7_client_package.el7.x86_64.tar.gz
cd adbpg_client_package/bin

# ADBPG 6.0 (RHEL 7 / CentOS 7)
tar -xzvf ADBPG_client_package_el7.tar.gz
cd adbpg_client_package/bin

# The bin directory includes psql, pg_dump, and other tools
# Add to PATH (optional, for convenience)
export PATH="$(pwd):$PATH"

# Verify
psql --version
```

**Method 2: Docker Image (Cross-Platform)**

```bash
# Pull and run the ADBPG CLI container
docker run -idt --name=adbpgcli aliadbpg/adbpgcli:v6.3.0
docker exec -it adbpgcli /bin/bash -l

# Inside the container, psql is already available
psql --version
```

**Method 3: Homebrew (macOS)**

```bash
brew install libpq
echo 'export PATH="/opt/homebrew/opt/libpq/bin:$PATH"' >> ~/.zshrc && source ~/.zshrc
psql --version
```

**Method 4: apt (Debian/Ubuntu, when official package is unavailable)**

```bash
sudo apt-get install -y postgresql-client
psql --version
```

#### Windows

**Method 1: Official Installer (Recommended)**

Download the installer from the [PostgreSQL official site](https://www.postgresql.org/download/windows/). During installation, select only "Command Line Tools" (no need to install the full database server).

After installation, add psql to PATH:

```powershell
# PowerShell (adjust based on actual installation path)
$env:Path += ";C:\Program Files\PostgreSQL\16\bin"
# Permanent
[Environment]::SetEnvironmentVariable("Path", $env:Path + ";C:\Program Files\PostgreSQL\16\bin", "User")

# Verify
psql --version
```

**Method 2: Scoop**

```powershell
scoop install postgresql
psql --version
```

**Windows Environment Variable Configuration:**

```powershell
# PowerShell temporary setup
$env:PGHOST = "gp-xxx.gpdb.rds.aliyuncs.com"
$env:PGPORT = "5432"
$env:PGDATABASE = "mydb"
$env:PGUSER = "analyst"
$env:PGPASSWORD = "<YOUR_PASSWORD_HERE>"  # ⚠️ Replace with actual password; never commit to version control
$env:PGOPTIONS = "-c default_transaction_read_only=on"

# Verify connection
psql -c "SELECT 1;"
```

> On Windows, you can also use `%APPDATA%\postgresql\pgpass.conf` to manage passwords, with the same format as `.pgpass`.

### Environment Variable Configuration

The Agent connects to the database using standard PG environment variables. Users must configure these in advance:

```bash
export PGHOST="gp-xxx.gpdb.rds.aliyuncs.com"   # Database host
export PGPORT="5432"                             # Port, default 5432
export PGDATABASE="mydb"                         # Database name
export PGUSER="analyst"                          # Username
export PGPASSWORD="<YOUR_PASSWORD_HERE>"          # ⚠️ Replace with actual password; prefer ~/.pgpass instead
```

> More secure approach: Use `~/.pgpass` file (permissions `chmod 600`), format: `host:port:database:user:password`
>
> **⚠️ Security Warning**: Never hardcode passwords in scripts, commit them to version control, or store them in plain-text configuration files without restricted permissions (chmod 600). The recommended approach is `~/.pgpass` (Linux/macOS) or `%APPDATA%\postgresql\pgpass.conf` (Windows) with file permissions limited to the owning user only.

---

## Non-Interactive Shell Environment Variable Configuration

**Problem**: Agents (e.g., QoderWork) start a **non-interactive shell** for each Bash command execution, which does not load `~/.bashrc` or `~/.zshrc`. Therefore, variables exported in user profiles are not visible to the Agent.

### macOS/Linux

#### Method 1: Use .pgpass + pg_service.conf (Recommended, No Environment Variables Required)

Completely independent of environment variables; psql automatically reads connection info from files:

**Step 1: Create `~/.pg_service.conf`**
```ini
[adbpg]
host=gp-xxx.gpdb.rds.aliyuncs.com
port=5432
dbname=mydb
user=analyst
options=-c default_transaction_read_only=on
```

**Step 2: Create `~/.pgpass`**
```
gp-xxx.gpdb.rds.aliyuncs.com:5432:mydb:analyst:<YOUR_PASSWORD_HERE>
```
```bash
chmod 600 ~/.pgpass
```

**Step 3: Agent Connection Command**
```bash
psql "service=adbpg" -c "SELECT 1;"
```

No environment variables needed; psql automatically reads host, port, database name, user, and password from files.

#### Method 2: Source Environment File Before Each Agent Command

Write connection configuration to a standalone file (e.g., `~/.pgenv`), and source it before each Agent execution:

```bash
# User creates ~/.pgenv (permissions 600)
cat > ~/.pgenv << 'EOF'
export PGHOST="gp-xxx.gpdb.rds.aliyuncs.com"
export PGPORT="5432"
export PGDATABASE="mydb"
export PGUSER="analyst"
export PGPASSWORD="<YOUR_PASSWORD_HERE>"
export PGOPTIONS="-c default_transaction_read_only=on"
EOF
chmod 600 ~/.pgenv
```

> **Note**: The user must run `source ~/.pgenv` in their own shell or IDE startup script before launching the Agent. The Agent itself **must never** execute `source ~/.pgenv` or access the `.pgenv` file in any way.

Agent verifies connectivity (environment variables must already be loaded by the user):
```bash
psql -c "SELECT 1;"
```

### Windows

#### Method 1: System-Level Environment Variables (Recommended, Persistent, Visible to All Processes)

```powershell
# PowerShell set user-level environment variables
[Environment]::SetEnvironmentVariable("PGHOST", "gp-xxx.gpdb.rds.aliyuncs.com", "User")
[Environment]::SetEnvironmentVariable("PGPORT", "5432", "User")
[Environment]::SetEnvironmentVariable("PGDATABASE", "mydb", "User")
[Environment]::SetEnvironmentVariable("PGUSER", "analyst", "User")
[Environment]::SetEnvironmentVariable("PGPASSWORD", "<YOUR_PASSWORD_HERE>", "User")  # ⚠️ Replace; prefer pgpass.conf
[Environment]::SetEnvironmentVariable("PGOPTIONS", "-c default_transaction_read_only=on", "User")
```

After setting, **restart the Agent/IDE** for new processes to inherit these variables.

> You can also configure via "System Properties → Advanced → Environment Variables" GUI.

#### Method 2: pgpass.conf (Password-Free Environment Variables)

On Windows, psql reads `%APPDATA%\postgresql\pgpass.conf`:

```powershell
# Create directory and file
New-Item -ItemType Directory -Force -Path "$env:APPDATA\postgresql"
Set-Content -Path "$env:APPDATA\postgresql\pgpass.conf" -Value "gp-xxx.gpdb.rds.aliyuncs.com:5432:mydb:analyst:<YOUR_PASSWORD_HERE>"
```

Combined with system-level PGHOST/PGPORT/PGDATABASE/PGUSER environment variables (excluding PGPASSWORD), psql automatically matches the password.

#### Method 3: Dot-Source Configuration File Before Execution

Similar to macOS/Linux Method 2 (environment file), create a PowerShell configuration script that the **user** dot-sources before launching the Agent:

```powershell
# User creates ~\.pgenv.ps1
Set-Content -Path "$HOME\.pgenv.ps1" -Value @'
$env:PGHOST = "gp-xxx.gpdb.rds.aliyuncs.com"
$env:PGPORT = "5432"
$env:PGDATABASE = "mydb"
$env:PGUSER = "analyst"
$env:PGPASSWORD = "<YOUR_PASSWORD_HERE>"
$env:PGOPTIONS = "-c default_transaction_read_only=on"
'@
```

> **Note**: The user must run `. $HOME\.pgenv.ps1` in their own PowerShell session before launching the Agent. The Agent itself **must never** execute or access `.pgenv.ps1`.

Agent verifies connectivity (environment variables must already be loaded by the user):
```powershell
psql -c "SELECT 1;"
```

### Recommended Priority

```
macOS/Linux: Method 1 (pg_service.conf) > Method 2 (source file)
Windows:     Method 1 (system-level env vars) > Method 2 (pgpass.conf) > Method 3 (dot-source file)
```

### Agent Guidance Flow

When the Agent detects a connection failure:
1. Inform the user: "No database connection configuration detected in the current Agent runtime environment"
2. Explain the reason: "The Agent executes in a non-interactive shell; configurations in ~/.zshrc will not take effect"
3. Recommend the appropriate method based on the user's OS
4. Have the user configure and then restart the Agent session
5. The Agent verifies connectivity again

> **Agent Prohibition**: Concatenating credential values in commands, or asking users to provide passwords in conversation.

---

## Connection Verification

The Agent verifies connectivity before executing the first query:

```bash
psql -c "SELECT current_database(), current_user, version();"
```

Successful output of database name, username, and version number confirms connectivity.

---

## Read-Only Connection (Recommended)

To prevent accidental operations, the Agent enforces read-only mode on connection:

### Method 1: Connection Parameter Enforcement (Preferred)

```bash
# Set read-only via PGOPTIONS (preferred, already included in user's environment file)
psql -c "SELECT 1;"

# Or set inline at connection time
PGOPTIONS="-c default_transaction_read_only=on" psql -c "SELECT 1;"
```

Once set, any write operation will be rejected by the database:
```
ERROR: cannot execute INSERT in a read-only transaction
```

### Method 2: Use a Read-Only Account (Most Secure)

Have the DBA create an account with SELECT-only permissions:

```sql
-- DBA executes
CREATE ROLE readonly_user LOGIN PASSWORD '<STRONG_PASSWORD_HERE>';  -- ⚠️ Use a strong, unique password
GRANT CONNECT ON DATABASE mydb TO readonly_user;
GRANT USAGE ON SCHEMA public TO readonly_user;
-- Grant access only to business-required tables (GRANT SELECT ON ALL TABLES IN SCHEMA is prohibited)
GRANT SELECT ON public.orders, public.customers, public.products TO readonly_user;
```

The Agent connects using this account; the database level ensures no writes are possible.

### Method 3: Session-Level Setting

Execute immediately after connecting:

```bash
psql -c "SET SESSION CHARACTERISTICS AS TRANSACTION READ ONLY; SELECT 1;"
```

---

## Connection Methods

```bash
# Recommended: Environment variables + read-only mode
export PGOPTIONS="-c default_transaction_read_only=on"
psql -c "SELECT 1;"

# Explicitly specify parameters
psql -h "$PGHOST" -p "$PGPORT" -d "$PGDATABASE" -U "$PGUSER" -c "SELECT 1;"

# SSL + read-only mode (embedding options in conninfo is prohibited; use environment variables)
PGSSLMODE=require PGOPTIONS="-c default_transaction_read_only=on" psql -c "SELECT 1;"
```

---

## Connection Troubleshooting

| Symptom | Possible Cause | Resolution |
|---------|---------------|------------|
| `Connection refused` | Incorrect host/port, instance not started | Verify PGHOST and PGPORT |
| `Connection timed out` | Network unreachable, whitelist not configured | Check firewall/security group/whitelist |
| `password authentication failed` | Incorrect password | Verify PGPASSWORD is correct |
| `database "xxx" does not exist` | Incorrect database name | Use `psql -l` to list available databases |
| `permission denied` | User lacks permissions | Contact DBA to grant SELECT permissions |
| `SSL connection required` | Instance requires SSL | Set `PGSSLMODE=require` |

### Quick Diagnostic Flow

```bash
# 1. Check if environment variables are configured
echo "Host=$PGHOST Port=$PGPORT DB=$PGDATABASE User=$PGUSER"

# 2. Check network reachability
nc -zv "$PGHOST" "$PGPORT"

# 3. Attempt connection
psql -c "SELECT 1;"
```
