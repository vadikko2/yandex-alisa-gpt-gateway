---
name: timeweb-kubernetes
description: Manage Timeweb Cloud managed Kubernetes — create clusters, inspect
  clusters, nodes and node groups, add or scale node groups, configure
  autoscaling and autohealing, upgrade the cluster version, install and
  reconfigure addons, fetch kubeconfig, list available versions, presets, CNI
  drivers and addons. Use when the user says "создай кластер кубернетес",
  "добавь ноды", "скейлни группу", "дай kubeconfig", "обнови версию кластера",
  "поставь ingress/cert-manager", "под висит в Pending", or asks about k8s
  versions, CNI, load balancers or persistent volumes on Timeweb Cloud. Do NOT
  use for standalone VDS servers or managed databases. Node prices and versions
  must come from live MCP tools, never from pre-trained knowledge.
---

# Timeweb Cloud Managed Kubernetes

## How to act

Through the Timeweb Cloud MCP (`timewebCloud`): `search_tools` →
`get_tool_definition` → `execute_tool`. `[WRITE]` needs the two-step
`confirm_token` flow (300 s TTL); `[BILLABLE]` charges immediately.

## Tool map (namespace `kubernetes`)

Read:
- `list_k8s_clusters` — clusters: status, k8s_version, totals, network_driver, ingress flag
- `get_k8s_cluster`, `get_k8s_cluster_resources` — details and resource usage
- `list_k8s_node_groups`, `get_k8s_node_group` — groups: node_count, preset,
  autoscaling (min/max), autohealing, public IPs, labels/taints
- `list_k8s_nodes` — individual nodes
- `list_k8s_versions`, `list_k8s_presets` — available versions and node
  hardware presets with prices (the only valid price source)
- `list_k8s_network_drivers` — available CNI drivers (flannel/calico/cilium)
  for cluster creation; the choice is PERMANENT — present the options to the
  user, never pick silently
- `list_k8s_addon_configs` — catalog of AVAILABLE one-click addons;
  `list_k8s_addons` — addons already INSTALLED on a cluster (to read one
  addon's current Helm values pass `addon_id` AND `include_yaml_config: true` —
  the flag without `addon_id` is rejected)
- `get_k8s_kubeconfig` — **SENSITIVE**: full-admin kubeconfig. Never print it
  into the chat, never log it; write it to a file the user names.

Write:
- `create_k8s_cluster` `[BILLABLE]` — new cluster: `k8s_version` from
  `list_k8s_versions`, `network_driver` from `list_k8s_network_drivers`,
  master `preset_id` (type "master") from `list_k8s_presets` — never guess any
  of them. You pay per master (× `master_nodes_count`) plus every node of every
  `worker_groups` entry. Irreversible choices: CNI and availability zone.
  A cluster without worker groups cannot run workloads until
  `create_k8s_node_group`. Custom disk configurator, OIDC, cluster CIDR and
  CSI-S3 settings are NOT exposed — panel
- `create_k8s_node_group` `[BILLABLE]` — new group: cluster_id, name,
  node_count, preset_id from `list_k8s_presets`
- `scale_k8s_node_group` `[BILLABLE]` — **adds** nodes; `count` = how many to
  ADD, NOT the target total. Never pass the desired total.
- `update_k8s_node_group` — autoscaling on/off + min/max, autohealing,
  public_ip_enabled, name
- `update_k8s_cluster_version` — upgrade only, **no downgrade and no
  rollback**; control plane and nodes restart during the rollout, and
  workloads still using APIs removed in the target version break — say both
  before confirming. Optional `scheduled_at` (ISO 8601, whole minute) defers
  it to a maintenance window
- `install_k8s_addon` — install an addon (ingress, cert-manager,
  kube-prometheus-stack, argo-cd…). Take `type` and `version` from
  `list_k8s_addon_configs` verbatim; `config_type: "custom"` requires
  `yaml_config` — never invent that YAML, take it from the user or the addon
  docs and show it before confirming. Removing an addon is panel-only
- `update_k8s_addon_config` — reconfigure/upgrade an INSTALLED addon by
  `addon_id` (not the code). `yaml_config` REPLACES the stored config, no
  merging — read the current one first and resend it with only your edits;
  dropping a key drops that setting in the cluster. The addon's workloads
  restart: an ingress or CSI driver rolling update can briefly interrupt
  traffic — say it out loud, prefer a maintenance window
- `update_k8s_cluster_meta` — rename/description only

## Decision guide

| User intent | Do this |
|---|---|
| "Не хватает мощности / добавь нод" | `scale_k8s_node_group` (count = to add) or better: `update_k8s_node_group` to enable autoscaling with min/max |
| "Убери ноды / дешевле" | Not exposed — removing nodes/groups is panel-only. Suggest enabling autoscaling instead (it scales down automatically) |
| "Создай кластер" | `list_k8s_versions` + `list_k8s_network_drivers` + `list_k8s_presets` (master AND worker presets) → walk the user through the permanent choices (CNI, zone) and the total price (masters × preset + worker nodes) → `create_k8s_cluster`. Background: references/cluster-and-nodes.md |
| "Дай kubeconfig / подключи kubectl" | `get_k8s_kubeconfig` → save to file; warn it is full-admin; for teammates recommend ServiceAccount+RBAC (reference) |
| "Под висит в Pending" | Check the group's autoscaling max and whether deployments set requests/limits — autoscaler ignores pods without them |
| "Обнови версию кластера" | `get_k8s_cluster` (current) + `list_k8s_versions` (target) → warn: no downgrade/rollback, control plane and nodes restart, deprecated APIs break → `update_k8s_cluster_version`, ideally with `scheduled_at` in a quiet window |
| "Поставь ingress/cert-manager/ArgoCD" | `list_k8s_addons` (already installed?) → `list_k8s_addon_configs` for type/version → `install_k8s_addon` |
| "Перенастрой/обнови аддон" | `list_k8s_addons` for the `addon_id` → again with `addon_id` + `include_yaml_config: true` → edit the CURRENT yaml, don't write a fresh one → `update_k8s_addon_config` — warn about the addon restart |

## Not available through MCP — send to the panel

- **All deletions**: clusters, node groups, individual nodes, addons — hence
  scaling DOWN by hand is panel-only; autoscaling can do it automatically.
- **Master (control-plane) resize** — panel, upward only, reboots the master.
- **At cluster creation**: custom disk configurator, OIDC provider, cluster
  CIDR, CSI-S3 settings.

## Billing safety

Nodes are billed per preset — get the price from `list_k8s_presets` and state
total cost (nodes × price) before `create_k8s_node_group` / `scale_k8s_node_group`.
For `create_k8s_cluster` the bill is masters (preset × count) plus every worker
node of every group — spell the total out. Deleting is panel-only, so every
node and cluster you create keeps billing until someone removes it — say so.

## Troubleshooting

| Symptom | Cause | Action |
|---|---|---|
| Autoscaler doesn't add nodes | Deployments lack requests/limits, group max reached, or cluster created before 2024-11-08 | Check all three; see references/cluster-and-nodes.md for autoscaler timings |
| Autoscaler doesn't remove nodes | Pods with `safe-to-evict: false`, PodDisruptionBudget, or controller-less pods block scale-down | Reference lists the blockers |
| LB settings revert / can't edit LB in panel | LB was created by a `Service type: LoadBalancer` — panel edits conflict | Edit ONLY via manifest annotations; see references/network-storage-access.md |
| Data gone after deleting a PVC | PVC deletion deletes the network drive itself | For existing drives use `persistentVolumeReclaimPolicy: Retain` — warn BEFORE they delete |
| Cluster operations temporarily blocked | Maintenance window in progress | `get_k8s_cluster` + maintenance settings in the panel |

## Anti-patterns (NEVER)

- NEVER output kubeconfig contents into the chat or logs — file only.
- NEVER pass the desired TOTAL as `count` to `scale_k8s_node_group` — it adds.
- NEVER suggest changing CNI on a live cluster — it is fixed at creation; pick
  it WITH the user at `create_k8s_cluster` time, never silently.
- NEVER quote node prices or version lists from memory — `list_k8s_presets` /
  `list_k8s_versions` only.
- NEVER "free up money" by deleting things — you can't; panel only, user's call.
- NEVER invent addon YAML or send a partial `yaml_config` to
  `update_k8s_addon_config` — it replaces, not merges; read the current config
  first.
- NEVER upgrade a cluster version without the no-rollback warning and an
  explicit yes.

Deep dives: [references/cluster-and-nodes.md](references/cluster-and-nodes.md) —
masters, versions/upgrade policy, maintenance, autohealer, autoscaler semantics;
[references/network-storage-access.md](references/network-storage-access.md) —
CNI, virtual router, LoadBalancer gotchas, CSI volumes, kubeconfig/RBAC, addons.
