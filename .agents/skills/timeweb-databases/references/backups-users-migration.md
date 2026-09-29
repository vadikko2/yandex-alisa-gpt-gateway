# Backups, Users, Migration, Deletion

Snapshot of the public docs (timeweb.cloud/docs/dbaas/*), not live truth:
privilege lists and dump flags drift with engine versions — verify against
`get_database_cluster_types` and the actual engine before promising anything.

## Physical backups (all engines)

- Filesystem-level snapshots; automatic (daily/weekly/monthly, N copies,
  start date — `update_database_backup_settings`) or manual
  (`create_database_backup` — the copy bills until deleted, deletion is
  panel-only).
- Restore: `restore_database_from_backup` — destructive, overwrites in place;
  the cluster sits in `backup_recovery` and is unavailable until `started`.
  Use `list_database_backups` to identify the copy and its `created_at` first.
- A downloadable dump without touching the cluster:
  `create_database_backup_download_url` — a temporary but UNAUTHENTICATED link
  to the full data; not available for very old or in-progress backups.
- Download as `.qcow2` — only MySQL/PostgreSQL clusters created after
  2025-01-01.

## Logical backups — S3 (beta; MySQL ≥8.0 / PG, BGP networks, non-US)

Manual only (no schedule): `create_database_s3_backup` →
`list_database_s3_backups` (string UUID ids, statuses running/success/failed) →
`restore_database_from_s3_backup` (only `success` / `is_restorable: true`).
Any other cluster gets 400 — that means "this cluster uses regular backups",
not an error. Dumps go into an auto-created read-only S3 bucket, are billed as
S3 storage until deleted (panel) and **survive cluster deletion**. They do NOT
save users and privileges — recreate those after restore. Docs explicitly say:
not a sole backup strategy — treat as an addition to physical backups.

## Dumps and imports (migration recipes)

- MySQL dump: `mysqldump --set-gtid-purged=off -y ... | gzip` — without the
  flag imports fail on GTID/privileges.
- PostgreSQL dump: `pg_dump -x` (skip GRANT/REVOKE — privileges are managed
  via the panel), port 5432.
- Valkey: export with `redis-dump-go` (password via env `REDISDUMPGO_AUTH`),
  import via `valkey-cli --pipe`.
- **Panel import** from an external MySQL/PG: the source must be reachable
  from subnet `92.53.116.0/24`, the target cluster needs a public IPv4, the
  target database name must be new. Structure+data migrate; users, roles and
  PG extensions do NOT — plan to recreate them. For MySQL imports docs advise
  temporarily lowering `innodb_buffer_pool_size` to ~50% RAM.

## Users and privileges

- Defaults: `gen_user` (MySQL/PG) / `default` (Valkey); base `default_db`;
  Kafka gets `default_topic` + `default_topic-group`.
- A NEW user gets **full access to all databases by default** — always narrow
  for app/read-only users (`create_database_user` / `update_database_user`).
- MySQL privileges include SELECT/INSERT/UPDATE/DELETE/CREATE/DROP/INDEX/
  ALTER/TRIGGER/PROCESS/CREATE_USER etc.; PostgreSQL: SELECT/INSERT/UPDATE/
  DELETE/TRUNCATE/CREATE/REFERENCES/TRIGGER/TEMPORARY/CREATEDB/CREATE_ROLE
  (finer roles — manually via SQL, needs CREATE ROLE); Valkey: ACL categories
  (READ, WRITE, ADMIN, DANGEROUS — the latter includes FLUSHALL/MIGRATE).
- Name 3–32 chars; password 8–30 chars.

## Deletion semantics

- **Dropped logical database**: physically deleted after ~24 h; within that
  window it is restored by creating a database with the same name. Tell the
  user this immediately when they report an accidental drop.
- **Cluster deletion**: irreversible, everything is lost (only logical S3
  dumps survive). No delete operations exist in the MCP at all.

## Transfer between accounts (panel)

Moves the cluster with config, users and physical backups; logical S3
backups and BGP private networks do NOT move. Unavailable for replicated
clusters and OVN networks. The cluster keeps running; the recipient needs
sufficient balance.
