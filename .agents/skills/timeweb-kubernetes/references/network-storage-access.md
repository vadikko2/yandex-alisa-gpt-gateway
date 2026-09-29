# Network, LoadBalancers, Storage, Access

Snapshot of the public docs (timeweb.cloud/docs/k8s/*), not live truth:
StorageClass names and annotation keys must be checked against the cluster
itself (`kubectl get storageclass`) — if it disagrees with this file, the
cluster wins.

## CNI — chosen at creation, immutable

Calico (BGP, packet-level policies), Flannel (VXLAN, simple, limited
policies), Kube-router (BGP + IPVS), Cilium (eBPF, L7 policies). If the user
picked wrong, the only path is a new cluster + migration — never suggest an
in-place change.

## Nodes without public IPs / virtual router

Workers can live without public IPs and go outbound through a **virtual
router** (cheaper, safer). Router constraints: SPb, Moscow, Amsterdam only;
must sit in the same private network as the cluster with DHCP enabled and a
public IP on the router. Inbound then goes through a LoadBalancer/Ingress.

## LoadBalancer gotchas (the big one)

- A `Service type: LoadBalancer` **auto-creates a cloud balancer** (shown in
  the panel tagged "K8S"). That balancer must be managed ONLY through the
  manifest — panel/API edits conflict and get overwritten.
- Tuning via annotations `k8s.timeweb.cloud/attached-loadbalancer-*`:
  algorithm, ddos-guard, ssl + ssl-fqdn, healthcheck/timeouts,
  `no-external-ip: "true"` for a private LB (default is public).
- **force-SSL (HTTP→HTTPS), once enabled, cannot be disabled — only
  recreating the balancer removes it.** Warn before enabling.
- Protocols per port via `appProtocol`: proto-http / https / tcp (default) /
  tcp-ssl / http2.

## Persistent volumes (CSI network drives)

- StorageClasses: `nvme.network-drives.csi.timeweb.cloud` and
  `hdd.network-drives.csi.timeweb.cloud`. **HDD exists only in SPb; Moscow is
  NVMe-only.**
- **ReadWriteOnce only** — no RWX; a drive attaches to one node (pods on that
  node share it). Auto-formatted ext4, min 1 GB, live expansion by editing
  the PVC.
- **Deleting a PVC deletes the network drive itself** (it disappears from the
  panel). To attach an existing drive without that risk:
  `persistentVolumeReclaimPolicy: Retain`.
- CSI overhead: ~250 mCPU + 250 MB RAM per worker, plus ~450 mCPU + 626 MB on
  one node — budget for it on small presets.

## kubeconfig and team access

- The panel kubeconfig (`get_k8s_kubeconfig` via MCP) is **full admin** —
  never hand it to teammates or paste into chats/CI logs.
- For people/CI: ServiceAccount + RBAC (view/edit/admin/cluster-admin or
  custom roles); tokens short-lived via `kubectl create token` or long-lived
  via a service-account Secret. Revoke by deleting the
  RoleBinding/Secret/ServiceAccount. External OIDC providers are supported.

## Addons (one-click, panel)

~30 addons: nginx-ingress, Traefik, cert-manager, CSI S3, Velero, Vault,
ArgoCD, Istio, Kube Prometheus Stack, Loki, NVIDIA GPU Operator, TWC
Karpenter, TWC DBaaS Operator and more — check `list_k8s_addons` before
advising manual Helm installs.
