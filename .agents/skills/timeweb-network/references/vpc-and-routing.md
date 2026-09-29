# Private Networks (VPC), NAT, Virtual Routers

Snapshot of the public docs (timeweb.cloud/docs/vpc, /docs/virtual-routers),
not live truth: if the panel or a tool response contradicts this file, they win.

## Two network types — BGP (current) and OVN (legacy)

The docs describe private networks as free with no limit on attached services —
but `create_vpc` is marked billable, so confirm the cost from its operation
summary rather than promising "бесплатно". New networks are always **BGP**;
**OVN networks can no longer be created** but existing ones keep working. The
type decides a surprising amount:

|  | BGP | OVN (legacy) |
|---|---|---|
| New networks | yes | no |
| Kubernetes | yes (only at cluster creation) | no |
| IPv6 for services | yes | **no** |
| Private IP assignment | **manual, inside the OS** | automatic from the range |
| Extra server IPs | allowed | **not allowed** |
| Virtual routers, DHCP, DNAT, static routes | yes | not documented |
| NAT / outgoing-only mode | **not available** (use a virtual router) | yes |

BGP networks exist in SPb, Moscow, Amsterdam and Frankfurt. The last octets
**.1, .2, .3 are reserved**. The subnet shown in the panel does not restrict
what you actually configure in the OS on BGP.

## Manual private IPs (BGP) — and why they break

On BGP the address must be configured inside the OS (nmcli / interfaces /
netplan / systemd-networkd / Windows). Triage for "серверы не видят друг
друга", in order:

1. `ip a` — no `inet` on the second interface → the address was never
   configured. This is the usual answer.
2. Interface in `state DOWN` → `ip link set dev eth1 up`.
3. No second interface at all → only support can fix it.
4. Address disappears after reboot → cloud-init's network config must be
   disabled; the address may also come up with a delay, and `ip_nonlocal_bind`
   helps services bind before it exists.

## Moving services between networks

- OVN → BGP migration works **only for cloud servers** (remove from OVN, add to
  BGP, same region); databases and balancers cannot be migrated.
- BGP → BGP transfers are automatic, same region only. **Kubernetes cannot be
  moved between networks after creation at all.**
- Timing: roughly a minute per 10 GB of disk, then a reboot — expect
  **5–10 minutes of downtime**, and the **public IP may change** if zones
  differ. After the move the private IP must be reconfigured: servers by the
  user, databases and balancers via support.
- Excluding a service from a network is only possible for cloud servers; a VPC
  can be deleted only when empty.

## NAT and outgoing-only

NAT replaces the private address with the gateway's public IP for outbound
traffic. It exists **only in OVN networks — not in BGP**, needs a public IP on
the network (same zone), and enabling outgoing-only on any service switches NAT
on automatically. Inbound connections still require the service to have its own
public IP. Docs state explicitly that NAT and outgoing-only are **panel-only,
not manageable through API/Terraform/CLI** — the MCP's `update_server_nat_mode`
covers the server-side flag, so verify the outcome rather than assuming.

## Virtual routers (panel-only)

The central hub for VPC traffic: internet gateway with NAT for BGP servers
without public IPs, DHCP, port forwarding (DNAT), static routes. Constraints
worth repeating to a user:

- Only networks in the **same region and zone** attach; at least one network is
  required and the last attached one cannot be detached.
- A public IP on the router is optional — but **mandatory for DNAT**.
- HA is a two-node tariff and reserves **three addresses per attached VPC**
  (one floating gateway IP that servers point to, plus one technical per node).
- Every server needs its default route pointed at the gateway IP manually.
- DHCP can be enabled on **only one router per private network**; success shows
  as a `dynamic` flag in `ip a`.
- DNAT: TCP/UDP/both, single port or a same-sized range (`10-80`); with no
  ports specified it forwards 1–65535 and then **no other rule can use that
  public IP**. Critically: **firewall rules do not apply to traffic arriving
  through a forwarded port** — say this whenever DNAT comes up.
- Static routes work only within one location; a route conflicting with an
  already attached network is rejected.
