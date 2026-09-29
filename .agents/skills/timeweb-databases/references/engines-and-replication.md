# Engines, Replication, Tariffs, Connections

Snapshot of the public docs (timeweb.cloud/docs/dbaas/*), not live truth: live
versions come from `get_database_cluster_types`, live prices from the catalog.
If a tool response contradicts this file, the tool wins.

## Engines (docs snapshot — verify live)

MySQL 8.0/8.4 (Percona XtraDB Cluster), PostgreSQL 14–18, MongoDB 7.0/8.0,
Valkey 7/8.1/9.1 (Redis-compatible fork — Redis SDKs and commands work),
OpenSearch, ClickHouse, Kafka, RabbitMQ. Locations: SPb, Moscow, Germany,
Netherlands.

## Replication — MySQL and PostgreSQL only

- **MySQL**: multi-master (Percona XtraDB) — all nodes accept writes,
  synchronous replication; a failed node doesn't stop the others.
- **PostgreSQL**: Patroni + Etcd, leader–replica, asynchronous replication,
  automatic failover to a replica.
- Replication requires a BGP network; node count is chosen at creation and
  can never be changed. Cluster cost = nodes × node price.
- Everything else (Valkey, Mongo, ClickHouse, Kafka, RabbitMQ, OpenSearch) —
  single-node only.

## Immutable after creation

Engine, version, node count. "Обнови постгрес с 14 до 17" = new cluster +
dump/restore migration — never promise an in-place upgrade.

## Tariff rules

- Lines: Premium NVMe, High CPU, Dedicated CPU + custom configurator.
- **Minimal tariff (1 CPU / 1 GB / 8 GB) is heavily limited**: exactly 1
  database and 1 user, no parameter management. Multiple databases need
  ≥2 GB RAM. Don't recommend the minimum for anything multi-tenant.
- Resize is **upward only** and reboots the cluster (downtime).

## Disk autoscaling

- Only MySQL/PostgreSQL WITHOUT replication, clusters created after
  2024-12-12. Trigger at 80/90/95% fill, step 5–100 GB, max 2 TB, hot (no
  reboot).
- **First trigger irreversibly converts a fixed tariff into a custom
  configuration** with recalculated price — warn before enabling.
- Without autoscaling a full disk flips the cluster to **read-only** — the
  top cause of "база сломалась, только чтение".

## Connection and TLS

- Paths: private network (default), paid public IPv4, free IPv6, or the
  cluster domain. Exact hosts/ports live on the cluster dashboard — send the
  user there rather than guessing ports.
- TLS is on by default in new clusters; domain connections are always TLS.
  MariaDB client 10.10+ needs `--skip_ssl` against MySQL clusters.
- Enabling IPv6 restarts the cluster for most engines — warn first.
- Web UIs (phpMyAdmin/Adminer/OpenSearch Dashboards/ClickHouse Query) require
  a public IP on the cluster.
- **No root access on managed databases** — by design; `gen_user` (MySQL/PG)
  or `default` (Valkey) is the maximum.

## Parameters

Applied cluster-wide (not per database); out-of-range values are silently
not applied. Not available on 1 GB RAM tariffs. PostgreSQL extensions
(pgvector, postgis, timescaledb, pg_stat_statements, pg_trgm, pgcrypto and
more) are enabled per database or cluster-wide from the panel; the set
depends on the PG version.
