---
name: timeweb-network
description: Manage Timeweb Cloud networking — public/floating IPv4 addresses
  (reserve, bind, unbind, PTR, DDoS-Guard), load balancers (create, backends,
  forwarding rules, health checks), private networks (VPC) and their attached
  services, additional server IPs and NAT mode, and network drives (create,
  mount, unmount). Use when the user says "дай IP серверу", "перенеси IP на
  другой сервер", "создай балансировщик", "распредели трафик между серверами",
  "создай приватную сеть", "подключи сетевой диск", "нужен PTR", "почему сервер
  не видит другой по локалке". Do NOT use for S3 storage or Kubernetes cluster
  networking internals. Prices come from `get_account_services_costs` and the
  catalog, never from memory.
---

# Timeweb Cloud Networking: IPs, Balancers, VPC, Network Drives

## How to act

Through the Timeweb Cloud MCP (`timewebCloud`): `search_tools` →
`get_tool_definition` → `execute_tool`. `[WRITE]` needs the two-step
`confirm_token` flow (300 s TTL); `[BILLABLE]` charges immediately.

## Tool map

Floating / public IPs (namespace `floating_ip`):
- `list_floating_ips`, `get_floating_ip`
- `create_floating_ip` `[WRITE]` `[BILLABLE]` — reserves an IPv4 in a chosen
  availability zone; **created unbound and billed from that moment**.
  `is_ddos_guard: true` costs a separate, higher tariff and **can only be
  chosen at creation** — it cannot be added to an existing IP later
- `bind_floating_ip`, `unbind_floating_ip` `[WRITE]` — attach/detach to a
  server, database, balancer or private network
- `update_floating_ip_meta` `[WRITE]` — comment and PTR

Server-side IP (namespace `servers`):
- `add_server_ip` `[WRITE]` `[BILLABLE]` — an extra IP directly on a server
- `update_server_nat_mode` `[WRITE]` — NAT / outgoing-only behaviour

Load balancers (namespace `balancers`):
- `list_balancers` (capped at 50 — when `returned_count` hits the cap and
  `total_count` is bigger, narrow the filter), `get_balancer` — config, all IPs
  (`ip` public entry, `local_ip` internal), health check, rules
- `list_balancer_ips` — BACKEND addresses the balancer forwards to (empty list
  = cannot serve traffic yet; per-backend health is not exposed);
  `list_balancer_rules` — port-forwarding rules
- `create_balancer` `[WRITE]` `[BILLABLE]` — billed per `preset_id` from
  `get_cloud_service_catalog(service_type="balancer")`. Created **EMPTY**: no
  backends and no rules, it serves nothing until `add_balancer_ips` +
  `add_balancer_rule`. Health-check params (`inter`/`timeout`/`fall`/`rise`)
  are required and have no safe defaults — propose values, let the user
  confirm. `https`/`tcp_ssl` need a certificate, which is NOT exposed here;
  placing the balancer in a private network is also panel-only
- `add_balancer_ips` `[WRITE]` — ADD backend IPv4s (never replaces; removal is
  panel-only). Check `list_balancer_ips` first; traffic flows as soon as a
  backend passes the health check, so a wrong address produces failing requests.
  Private addresses must share the balancer's VPC
- `add_balancer_rule` `[WRITE]` — listener (proto+port) → backend target
  (proto+port); a duplicate (balancer_port+proto) pair is rejected
- `update_balancer_rule` `[WRITE]` — all four fields required, the backend
  overwrites the rule, no partial merge
- `update_balancer_meta` `[WRITE]` — name/comment, algo
  (roundrobin/leastconn), listener, health check, sticky/PROXY-protocol/SSL
  redirect/keepalive flags. Unit trap: health-check fields are in SECONDS, the
  advanced timeouts (`connect_timeout` etc.) in MILLISECONDS

Private networks (namespace `vpc`):
- `list_vpcs`, `get_vpc`, `list_vpc_services` (what is inside),
  `list_vpc_ports`
- `create_vpc` `[WRITE]` `[BILLABLE]` — requires name, `subnet_v4` (CIDR that
  must not overlap another VPC in the same location) and `location`. The public
  docs call private networks free, yet the tool is marked billable — present the
  operation summary verbatim and get approval instead of assuming it is free
- `update_vpc_meta` `[WRITE]`

Network drives (namespace `network_drive`):
- `list_network_drives`, `get_network_drive`,
  `list_network_drives_available_resources` — **call this before mounting** to
  get valid targets
- `create_network_drive` `[WRITE]` `[BILLABLE]`
- `mount_network_drive`, `unmount_network_drive` `[WRITE]` — targets are
  `server` or `k8s_node`
- `update_network_drive_meta` `[WRITE]`

## Decision guide

| User intent | Do this |
|---|---|
| "Дай серверу внешний IP" | `add_server_ip` for a plain extra address, or `create_floating_ip` + `bind_floating_ip` if they want a movable one |
| "Перенеси IP на другой сервер" | `unbind_floating_ip` → `bind_floating_ip`; the address stays on the account in between (and keeps billing) |
| "IP больше не нужен, отвяжи" | Unbinding does NOT stop charges — only deleting the IP does, and deletion is panel-only. Say this explicitly |
| "Нужна DDoS-защита на IP" | Only at creation (`is_ddos_guard: true`), only SPb/Moscow; for an existing IP the honest answer is "нужен новый IP" |
| "Настрой PTR" | `update_floating_ip_meta` for floating IPs, `update_server_ip_ptr` (namespace `servers`) for a server's own IP; not available in Novosibirsk |
| "Распредели нагрузку / создай балансировщик" | Catalog price → `create_balancer` (agree health-check values with the user) → `add_balancer_ips` with the backend servers → `add_balancer_rule` per port. Only then does it serve traffic |
| "Балансировщик не отвечает / 503" | `get_balancer` + `list_balancer_ips` — empty backend pool or no rules is the first suspect; then health-check settings (a too-strict check marks all backends down) |
| "Убери сервер из балансировщика" | Panel-only — `add_balancer_ips` only adds. Say so |
| "Нужен HTTPS на балансировщике" | Protocol `https`/`tcp_ssl` requires a certificate, and certificates are panel-only — configure it there |
| "Свяжи серверы по локальной сети" | `create_vpc` → attach services (server-side attach lives in the panel/server settings); then the private IP must be configured **inside the OS** on BGP networks |
| "Сервер не видит сосед по локалке" | Almost always the private IP is not configured on the interface — see references/vpc-and-routing.md triage |
| "Нужно больше места, но не на диске сервера" | `create_network_drive` → `list_network_drives_available_resources` → `mount_network_drive`; then partition/mount inside the OS |
| "Отключи сетевой диск" | Tell the user to unmount it inside the OS FIRST, then `unmount_network_drive` — data is kept |
| "Уменьши диск / убери IP" | Impossible / panel-only respectively (see below) |

## Not available through MCP — send to the panel

Deleting floating IPs, VPCs, network drives, balancers and additional server
IPs; removing a backend from a balancer or deleting its rules; balancer
certificates and placing a balancer into a private network; resizing a network
drive; virtual routers entirely (NAT gateway, DHCP, DNAT, static routes);
DDoS-Guard on an existing address. Docs also state that NAT and outgoing-only
mode are **panel-only, not automatable via API/Terraform/CLI** — so don't
promise scripting them.

## Billing safety

`create_floating_ip`, `create_network_drive`, `create_vpc` and
`create_balancer` are all billable and charge immediately, and none of them can
be deleted through the MCP — so every resource you create keeps costing money
until the user removes it in the panel. Before confirming: quote the live cost
(`get_account_services_costs` shows existing IPs under types `floating_ip` /
`floating_ip_with_ddos_guard`; balancer presets are in the catalog under
`service_type="balancer"`; drive pricing is per GB by type) and say plainly
that an idle, unbound IP — or an empty balancer with no backends — is still
billed.

## Troubleshooting

| Symptom | Cause | Action |
|---|---|---|
| Mount fails | Drive and target are in different zones, drive already mounted, or target is full | `list_network_drives_available_resources` — it only lists valid targets |
| Private IP unreachable between servers | Address not configured/downed inside the OS (BGP networks assign it manually) | Triage steps in references/vpc-and-routing.md |
| Private IP disappears after reboot | cloud-init network config overrides it | Reference explains the fix |
| No IPv6 available | Novosibirsk, or the service sits in a legacy OVN network | Reference: IPv6 works in BGP networks only |
| IP changed after moving a service between networks | Expected when zones differ | Warn before the move, not after |
| Charges continue after unbinding an IP | Unbind ≠ delete | Panel → Public IPs to release it |

## Anti-patterns (NEVER)

- NEVER create a floating IP "just in case" without saying it bills from
  creation, bound or not.
- NEVER claim an IP or drive can be removed through you — deletion is panel-only
  (the one indirect exception: deleting a PVC in Kubernetes deletes its network
  drive, see the timeweb-kubernetes skill).
- NEVER promise a smaller network drive: size only grows.
- NEVER unmount a drive without telling the user to unmount it inside the OS
  first — data loss risk.
- NEVER add an unverified address to a balancer pool — traffic goes there the
  moment the health check passes; confirm the backend actually serves the
  target port first.
- NEVER pick health-check values for `create_balancer` silently — propose and
  let the user confirm; they have no safe defaults.
- NEVER quote IP, balancer or drive prices from memory.

Deep dives: [references/ips-and-drives.md](references/ips-and-drives.md) —
floating IP semantics and billing traps, IPv6/PTR/DDoS limits, drive types,
sizes and lifecycle; [references/vpc-and-routing.md](references/vpc-and-routing.md) —
BGP vs legacy OVN, manual private IPs and their triage, NAT, virtual routers,
availability zones.
