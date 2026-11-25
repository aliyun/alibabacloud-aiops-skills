# Per-engine check procedures (evidence-backed)

Concrete checks the report emits per database engine, distilled from the
tickets merged into this tier. Every "change" column entry is a customer
action; the skill never executes any of them. Official help-doc URLs are
listed only where real docs back the topic; where none was verified for this
tier, the row says so explicitly rather than guessing a URL.

## MySQL / MariaDB (port 3306)

| Check | Look for | Who changes it |
| --- | --- | --- |
| Listening and bound | `ss -antp \| grep -w 3306` shows `0.0.0.0:3306`, not `127.0.0.1:3306`; `bind-address` in the option file (`/etc/my.cnf` or `/etc/mysql/`) | Customer edits config, then restarts the service themselves |
| Host grant | The user row is granted for the client host (`%` or the client IP), not only `localhost` | Customer, via their own SQL client |
| Wrong-port family | Client dials 3306 while the instance exposes another port (ticket sample: allow-list opened 40731) | Reconcile port, SG rule and client string |
| Capacity chain | `No space left on device`, binlog/relay-log bloat, ibdata growth -> `df -h` + `df -i` + `du` on the log directory (gated) | Cleanup: capacity tier / customer, snapshot first |
| Memory chain | `mysqld` gone after boot, no pid file, `available memory` tiny (`free -m` paste); ticket practice: add swap as interim, resize via console as real fix | Console change spec (customer) https://help.aliyun.com/zh/ecs/user-guide/change-the-instance-types-of-subscription-instances ; swap interim https://help.aliyun.com/knowledge_detail/42534.html |
| Backup/restore pre-check | Free space at the target path >= backup file size; authentication mode already usable; `.bak`-format import limits are panel-product behavior, not ECS behavior | Customer; business-layer restore steps stay with the DBA |

## SQL Server (port 1433)

| Check | Look for | Who changes it |
| --- | --- | --- |
| Authentication mode | Mixed mode (SQL Server and Windows Authentication) required for non-Windows logins; the ticket-proven path: server properties -> security -> mixed mode, then enable the `sa` (or named) login and set a password | Customer in SSMS; a service restart is required after the change - their action, not this skill's |
| Dynamic port drift | After password resets or reinstalls, the TCP port went dynamic (ticket sample: 1433 became 49750) while the app still dials 1433; check `Get-NetTCPConnection -LocalPort 1433` and SQL Server Configuration Manager IP addresses tab | Customer pins the TCP port |
| Named instances | Instance publishes a browser-service port instead of 1433 | Customer aligns client string |
| Restore target | SSMS restore silently targeting another database name (ticket sample: target jumped to an auto-named db) | Customer re-runs the wizard specifying the target; business layer |

## Redis (port 6379)

| Check | Look for | Who changes it |
| --- | --- | --- |
| protected-mode / bind | `protected-mode yes` with no password refuses non-loopback clients; `bind 127.0.0.1` confines it to the guest | Customer edits redis.conf, restarts their service |
| requirepass | Client sends no AUTH or the wrong one | Client config or rotate - customer |
| Nonstandard ports | Ticket samples show deployments on 16379/16380 while guests fired up firewalls that allow only defaults - check the real port and the in-guest allow-list together | Customer |
| Exposure | 6379 open to the whole internet is the pre-condition on the ransom tickets in this set -> hardening checklist item 2 | Customer, security group console |

## PostgreSQL (port 5432)

| Check | Look for | Who changes it |
| --- | --- | --- |
| listen_addresses | Default `localhost` in `postgresql.conf` confines the socket | Customer edits config, restarts their service |
| Client authentication | `pg_hba.conf` must carry a line for the client subnet/method | Customer |
| Capacity | WAL/log directory growth is the common disk killer | Capacity path: `du` gated triage, snapshot first, then hand off |

## MongoDB (port 27017)

| Check | Look for | Who changes it |
| --- | --- | --- |
| bindIp | `security.net.bindIp` default `127.0.0.1` in the config file | Customer edits config, restarts their service |
| Auth | Access created only inside localhost context; remote first login fails until an admin user exists on the target db | Customer |
| Storage engine lock | Unclean shutdown leaves lock files; deleting them is a destructive manual step - document, never dispatch | Customer / vendor docs |

## Cross-engine layers that tickets proved again and again

* "I opened 3306 in the console" is not "MySQL accepts my connection": the
  five allow-listen-bind-grant credentials checks - the coarse model the
  customer already has, not the L0-L8 walk this skill reports - are separate
  checks.
* Application-level "database connection failed" pages were disk-full and
  out-of-memory failures wearing a database costume: always run the capacity
  and memory legs (`df -h`, `df -i`, `free -m` paste) before blaming the
  engine.
* Shared-family instances can starve a database's CPU without any fault:
  check the family level of the spec (https://help.aliyun.com/zh/ecs/user-guide/shared-instance-families).
* Historical process-level evidence after a reboot is gone unless `atop` was
  installed beforehand (https://help.aliyun.com/zh/ecs/user-guide/use-the-atop-tool-to-monitor-linux-system-metrics);
  state this up front, not as an afterthought.
* Instance-level remote login must work before any of this is answerable
  yourself: login methods overview https://help.aliyun.com/zh/ecs/user-guide/guide-and-best-practices-for-logging-into-ecs-5-methods-and-how-to-choose.md

## Documentation coverage note (honesty section)

Official customer-facing docs verified for this tier cover instance
operations (login methods, snapshots, re-initialize, spec change, swap, atop,
shared families). No official help-doc URL was verified for the engine-side
topics (SQL Server mixed authentication, MySQL host grants, redis
protected-mode, pg_hba): those procedures come from the ticket practice above
and need a manual doc search before quoting a link to the customer - do not
invent one.
