# Clusters, Masters, Versions, Autoscaling

Snapshot of the public docs (timeweb.cloud/docs/k8s/*), not live truth: verify
volatile numbers in the panel, and take prices from `list_k8s_presets` — the
docs contain none. If a tool response contradicts this file, the tool wins.

## Masters (control plane) — paid, chosen at creation

- **Dev**: 1 master, 2 CPU / 2 GB / 30 GB NVMe, up to 10 workers.
- **Base**: 1 master, 4 CPU / 8 GB / 60 GB NVMe, up to 100 workers.
- **Custom**: 1 or 3 masters (HA), from 4 CPU / 8 GB / 60 GB up to
  32 CPU / 140 GB / 1200 GB.
- Master config changes later go **upward only** and reboot the master.

## Node groups

- One group = one hardware config; multiple groups per cluster for mixed
  workloads. Workers range 2 CPU / 2 GB / 30 GB → 32 CPU / 256 GB / 1200 GB.
- Editable on a group: name, autoscaling, autohealing, public node IPs,
  labels (`key:value`), taints (`key:value:effect` — NoSchedule /
  PreferNoSchedule / NoExecute).

## Versions and upgrades (MCP: `update_k8s_cluster_version`)

- **No downgrade, no rollback of an upgrade.** Only a *scheduled, not yet
  started* upgrade can be cancelled. Say this before the user upgrades.
- Control plane and nodes restart during the rollout; workloads using APIs
  removed in the target version break — check deprecations first.
- `scheduled_at` (ISO 8601, aligned to a whole minute) defers the upgrade to a
  maintenance window; without it the upgrade starts immediately.
- kubectl must be within ±1 minor version of the cluster.

## Maintenance window

Security updates and certificate renewals for masters and workers run in the
window; cluster operations are blocked during it and brief disruptions are
possible. Modes: never / anytime / fixed slot. If an operation mysteriously
fails "temporarily" — check the window first.

## Autohealer (off by default)

Enabled per node group. Checks workers every 10 minutes; tries restart
(~2 min), retries ~14 min, then **recreates the node**. Not for GPU nodes or
masters; max 10 concurrent healing tasks; opt a node out with label
`kube-healer.kubernetes.io/healing-disabled: true`.

## Cluster autoscaler

- Only clusters **created after 2024-11-08**. Group min can be set to 0 after
  creation (at creation min is 1).
- Timings: scan every 2 min; scale-down after 5 min of low utilization
  (default threshold 0.5); new node provisioning up to 10 min; NotReady node
  replaced after 30 min; removes at most one node at a time.
- Scale-up triggers on Pending pods and **only when deployments define
  requests/limits** — the single most common "autoscaler is broken" cause.
- **Scale to zero**: cluster must keep ≥2 permanently active nodes for system
  components; target pods to the group via nodeSelector/nodeAffinity.
- Scale-down blockers: pod annotation
  `cluster-autoscaler.kubernetes.io/safe-to-evict: "false"`,
  PodDisruptionBudget, pods without a controller.

## Feature gates

Alpha/beta features can be toggled, but correct cluster operation is
guaranteed only at defaults; alpha features may vanish, and a version upgrade
resets gates to defaults. Recommend against them on production clusters.
