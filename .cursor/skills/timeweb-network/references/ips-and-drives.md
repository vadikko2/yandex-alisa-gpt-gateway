# Public IPs, IPv6, PTR, DDoS-Guard, Network Drives

Snapshot of the public docs (timeweb.cloud/docs/public-ip, /docs/network-drives),
not live truth: live prices from `get_account_services_costs` and the catalog;
if a tool response contradicts this file, the tool wins.

## Public IPv4 = a floating address

A public IPv4 is an independent account resource, not a property of a server:
it can be moved between services **within the same region / availability zone**.
Attachable to cloud servers, databases, balancers and private networks.

Billing traps, in order of how often they bite:

1. **An unbound IP is still billed.** Charges stop only when the address is
   deleted — and deletion is panel-only.
2. **Deleting a service leaves the IP on the account**, still billed.
3. **Deletion is irreversible**: the same address cannot be reclaimed.
4. A bound IP can be deleted directly — the service simply loses external
   access, no need to unbind first.

Other facts: up to 10 addresses per day per account (more via support); a new
address appears within minutes; ordering requires balance covering 30 days;
binding an IP to a private network **automatically enables NAT**.

## IPv6

Free. Supported on cloud servers and databases. **Not available in
Novosibirsk, and not available to services in legacy OVN networks** (works in
BGP networks). Up to 10 per server, one per database. Unlike IPv4, **IPv6 does
not move between services**. The primary IPv6 cannot be deleted. On databases,
disabling IPv6 reserves the address — re-enabling returns the same one. Servers
need manual OS configuration; databases do not.

## PTR (reverse DNS)

Available for public IPs in **all regions except Novosibirsk**; set via
`update_floating_ip_meta` (or at creation). Propagation time, validation rules
and limits are not documented — don't invent them.

## DDoS-Guard on an IP

**SPb and Moscow only**, billed as a separate higher tariff per address (in
`get_account_services_costs` it appears as `floating_ip_with_ddos_guard`).
The critical constraint: protection **can only be enabled when the address is
created** — an existing IP cannot be upgraded, the user needs a new protected
IP and a re-bind. There is also a separate "DDoS protection + CDN" product for
servers (SPb/Moscow only) with static caching on by default and geo-blocking
for a handful of countries.

## Network drives

|  | HDD | NVMe |
|---|---|---|
| Min size | 100 GB | 10 GB |
| Max size | 50 000 GB | 20 000 GB |
| Step | 100 GB | 5 GB |

- Regions: **SPb and Moscow only**; in Moscow drives serve Kubernetes clusters
  only. Attachable to Premium NVMe and Dedicated CPU server lines and to k8s
  nodes (`resource_type` is `server` or `k8s_node`).
- **A drive mounts only to a target in the same availability zone** — the
  single most common mount failure. `list_network_drives_available_resources`
  filters to valid targets, so call it instead of guessing.
- The drive is not tied to one server: unmount and mount elsewhere. Docs
  describe sequential re-attaching and never promise multi-attach — do not
  claim two servers can share one drive.
- **Size grows only** (resize itself is panel-only); after growing, the
  filesystem must be extended inside the OS. A freshly mounted drive needs
  partitioning, a filesystem and an fstab entry — mounting via MCP only
  attaches the block device.
- Unmounting **keeps the data**, but the drive must be unmounted inside the OS
  first or data can be lost. Deleting a drive is **irreversible** and possible
  even while mounted (panel only — with one indirect route: deleting a PVC in
  Kubernetes deletes the underlying drive too).
- Not possible: boot from a network drive, create an image from it, or use
  panel backups/snapshots for it — so a network drive is not a backup target.

## Availability zones (why zone mismatches keep appearing)

A zone is an isolated part of a region. Timeweb is phasing zones out — new
customers see a single zone — but zones still hard-constrain **public IPs**,
**network drives** and attaching networks to routers. When an operation fails
"for no reason", compare zones first.
