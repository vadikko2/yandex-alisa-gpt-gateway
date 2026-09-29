---
name: timeweb-databases
description: Manage Timeweb Cloud managed databases (DBaaS) — create and resize
  clusters (MySQL, PostgreSQL, Valkey/Redis, MongoDB, OpenSearch, ClickHouse,
  Kafka, RabbitMQ), start/stop/reboot them, create and edit database users and
  their privileges, manage logical databases/instances, create backups and
  restore from them (disk and S3), configure backup schedules, manage replicas,
  read engine parameters and supported versions. Use when the user says "подними
  базу", "создай пользователя БД", "настрой бэкапы базы", "восстанови базу из
  бэкапа", "какие версии постгреса", "база в read-only". Do NOT use for
  databases the user runs on plain VDS themselves. Versions, presets and prices
  must come from live MCP tools, never from memory.
---

# Timeweb Cloud Managed Databases (DBaaS)

## How to act

Through the Timeweb Cloud MCP (`timewebCloud`): `search_tools` →
`get_tool_definition` → `execute_tool`. `[WRITE]` needs the two-step
`confirm_token` flow (300 s TTL).

## Tool map (namespace `databases`)

Read:
- `list_database_clusters` — clusters: engine+version, status, location, cpu/ram
- `get_database_cluster` — details of one cluster
- `get_database_cluster_types` — supported engines and versions (the source
  for "какие версии поддерживаются"); `is_deprecated` versions cannot be created
- `get_database_parameters` — engine parameters of a cluster (which exist, bounds);
  `get_database_default_parameters` — the recommended VALUES for an engine+RAM
  size (what the panel prefills) — feed them into `config_parameters` on create
- `get_database_privileges` — catalog of grantable privileges for THIS cluster's
  engine (GLOBAL/DATA/STRUCTURE/OTHERS) — read before creating/updating users
  instead of guessing; what a user HAS is `get_database_user`
- `list_database_instances`, `get_database_instance` — logical databases
  inside a cluster
- `list_database_users`, `get_database_user` — users (admin entities:
  login + privileges + instance assignment)
- `list_database_replicas` — replicas of a replicated cluster (pass the LEADER's
  id; empty list = single node, a normal answer)
- `list_database_backups`, `get_database_backup`,
  `get_database_backup_settings` — disk backups and their schedule
  (note: `db_id` in backup tools = cluster_id, legacy naming)
- `list_database_s3_backups`, `get_database_s3_backup` — S3 (logical) backups:
  a DIFFERENT mechanism with string UUID ids; exists only for MySQL ≥8.0 and
  PostgreSQL in a BGP private network outside the US region — other clusters
  get 400, which means "this cluster uses regular backups"
- Prices for NEW clusters: `get_cloud_service_catalog` (namespace `catalog`)

Write:
- `create_database_cluster` `[BILLABLE]` — new cluster; billing starts right
  after provisioning. EITHER `preset_id` OR `configuration` (ram/disk in
  MEGABYTES), never both; `replication.count` is the TOTAL node count (1/3/5)
  and every node is billed. Async: returns `starting` — poll
  `get_database_cluster` until `started` for host/port. **Do not pass
  `admin.password` the user wants kept secret — it travels through service
  logs; create the cluster without an admin and add users afterwards**
- `update_database_cluster_config` `[BILLABLE]` — resize (preset/configuration —
  disks GROW only, price changes immediately), replicas (lowering the count
  DESTROYS the extras), public IPv4/IPv6, TLS enforcement, disk autoscaling
  (each auto-growth step is billed and irreversible), engine parameters
  (**applying them usually RESTARTS the DBMS**)
- `database_cluster_action` — start / shutdown / reboot. Every action drops open
  client connections; **a stopped cluster is STILL BILLED** — stopping is not a
  way to save money
- `create_database_instance` — new logical database in a cluster (not billed
  separately; key-value engines reject it). It starts with NO users attached —
  grant access right after
- `create_database_user` — new user; **default privileges are FULL access to
  all databases** — narrow them explicitly when the user wants read-only
- `update_database_user` — privileges, password, instance assignment
- `update_database_instance` — rename/describe a logical database
- `create_database_backup` `[BILLABLE]` — manual disk backup; stored copies are
  billed until deleted, and deletion is panel-only
- `restore_database_from_backup` — DESTRUCTIVE: overwrites live data in place,
  no undo; cluster goes `backup_recovery` and is unavailable until `started`
- `create_database_backup_download_url` — temporary direct link to a FULL DUMP;
  anyone with the URL downloads the whole database without auth. Hand it to the
  user once, never store or repeat it. Prefer this over restore when the user
  only wants to LOOK at old data
- `update_database_backup_settings` — auto-backup schedule and copies;
  `update_database_backup_comment` — label a copy (replaces, "" clears)
- S3 backups (same availability limits as the reads):
  `create_database_s3_backup` `[BILLABLE]`, `restore_database_from_s3_backup`
  (DESTRUCTIVE, only status `success` / `is_restorable: true`),
  `update_database_s3_backup_comment`
- `update_database_cluster_meta` — cluster rename/description only (cheaper
  than `..._config` for that)

## Decision guide

| User intent | Do this |
|---|---|
| "Подними базу / кластер постгреса" | `get_database_cluster_types` for engine+version → catalog for price (replicated cluster = nodes × price) → replication/limits advice from references/engines-and-replication.md → confirm cost → `create_database_cluster` → poll `get_database_cluster` until `started`, then report host/port |
| "Заведи пользователя для приложения" | `create_database_user` — and explicitly set minimal privileges; default is full access. Valid privilege codes: `get_database_privileges` |
| "Пользователь только на чтение" | `create_database_user` with SELECT-only (engines differ — `get_database_privileges` + reference) |
| "Настрой бэкапы" | `get_database_backup_settings` → `update_database_backup_settings` (daily/weekly/monthly, copies); one-off copy → `create_database_backup` (billable until deleted in the panel) |
| "Восстанови из бэкапа" | `list_database_backups` → read `created_at`, tell the user which point in time they go back to → `restore_database_from_backup`. Destructive and the cluster is unavailable during recovery. Unsure user / just wants to see old data → `create_database_backup_download_url` instead |
| "База ушла в read-only" | Disk is full (see Troubleshooting) — not a crash |
| "Какие версии / поддерживается ли репликация" | `get_database_cluster_types`; replication exists only for MySQL and PostgreSQL |
| "Смени тариф / добавь ресурсов" | `update_database_cluster_config` with preset/configuration — **upward only** for disks, price changes immediately, expect a restart — warn about both |
| "Добавь/убери реплики" | `update_database_cluster_config(replication)` — warn: lowering the count destroys the extra replicas; each node is billed |
| "Выключи базу на время" | `database_cluster_action(shutdown)` — but say plainly: a stopped cluster is still billed in full; only deletion (panel) stops charges |
| "Перезапусти базу" | `database_cluster_action(reboot)` — drops open connections |
| "Перенеси базу с другого хостинга" | Dump/import recipes in references/backups-users-migration.md |

## Not available through MCP — send to the panel

- **Deleting clusters and backups** — no delete operations exist; everything
  created keeps billing until removed in the panel. Say so when creating.
- Engine and version of an existing cluster are **immutable** — a "version
  upgrade" means a new cluster + migration.

## Billing safety

`create_database_cluster`, `update_database_cluster_config` (resize, replicas,
autoscaling), `create_database_backup` and `create_database_s3_backup` all
change what the account pays, immediately. Before confirming: quote the live
catalog price, remind that a replicated cluster costs nodes × price, that disk
growth (manual or autoscaling) is irreversible, and that stored backups bill
until deleted in the panel. `database_cluster_action(shutdown)` does NOT stop
charges — never present it as a saving.

## Troubleshooting

| Symptom | Cause | Action |
|---|---|---|
| Cluster in read-only | Disk full; auto-expansion exists only for MySQL/PG without replication (clusters created after 2024-12-12) | Free space or grow disk in panel; enabling autoscaling converts a fixed tariff to custom irreversibly — see reference |
| "Не могу подключиться извне" | No public IP on the cluster, or TLS mismatch | Public IPv4 is paid and toggled in the panel; connection via cluster domain is always TLS; MariaDB 10.10+ clients need `--skip_ssl` for MySQL |
| "Дай root на базу" | root is not available on managed DBs by design | Explain; max privileges live on the default user (`gen_user`) |
| "Удалил базу случайно" | A dropped logical database is physically deleted after ~24 h | Recreate a database with the SAME name within 24 h to restore it — act fast |
| Can't tune parameters | 1 GB RAM tariffs disable parameter management (PG: all; MySQL: key buffer/limit params) | Suggest a bigger tariff |
| IPv6 enable caused restart | Expected for most engines | Warn beforehand next time |

## Anti-patterns (NEVER)

- NEVER create a user with default privileges when the request was
  "read-only" — narrow explicitly and say what you granted.
- NEVER print passwords returned by user-management tools into logs; show
  once to the user. And never pass a secret `admin.password` into
  `create_database_cluster` — it lands in service logs; create without an
  admin and add users after.
- NEVER promise version upgrade or disk scale-down of an existing cluster —
  both are impossible; the honest path is a new cluster + migration.
- NEVER restore from a backup without naming its `created_at` and getting an
  explicit yes — everything written after it is lost, no undo. Unsure user →
  `create_database_backup_download_url` instead.
- NEVER treat a backup download URL casually — it is a full unauthenticated
  dump; hand it to the user once and don't repeat it.
- NEVER lower `replication.count` without saying the extra replicas are
  destroyed, and never apply `config_parameters` without warning about the
  DBMS restart.
- NEVER quote versions/prices from memory — `get_database_cluster_types` and
  the catalog only.

Deep dives:
[references/engines-and-replication.md](references/engines-and-replication.md) —
engines, replication semantics, tariff limits, connection/TLS, disk
autoscaling; [references/backups-users-migration.md](references/backups-users-migration.md) —
physical vs logical backups, dumps, panel import, privileges per engine,
deletion and transfer semantics.
