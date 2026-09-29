# SOP: Creating a Cloud Server

Step-by-step procedure for "подними сервер", "создай VDS под сайт/бота/докер".

Product details below are a snapshot of the public docs, not live truth: every
preset, OS, location and price must come from the catalog tools at call time.

## 1. Understand the need before touching the catalog

Ask (or infer from context) three things: what will run on it (site, bot,
Docker, database), expected load, and where the audience is (Russia → SPb/Moscow;
Europe/world → international locations). Don't ask more than 2–3 questions.

## 2. Pick a configuration — preset vs configurator

- **Presets (fixed tariffs)** are cheaper than the same resources assembled in
  the configurator. Default to a preset.
- **Configurator** is for non-standard ratios (e.g. lots of RAM, little CPU).
  In `create_server` these are mutually exclusive: `preset_id` OR `configuration`
  (configurator_id + cpu + ram in MB + disk in MB).
- Tariff lines differ by location: Premium NVMe, Standard, HighCPU, Dedicated CPU,
  GPU. GPU is available only in St. Petersburg and Moscow.
- Get live options and prices: `get_cloud_service_catalog(service_type="server")`.
  Never quote prices from memory.

## 3. Pick location

St. Petersburg (several availability zones, spb-*) and Moscow (msk-1) are the
primary Russian regions; international zones include Amsterdam (ams-1),
Frankfurt (fra-1), Kazakhstan (ala-1), Kazan (kzn-1), Novosibirsk (nsk-1) and
others — the full enum is in the `create_server` schema. Some features
(private networks, IPv6, GPU) are not available in every location. The preset
determines the location: the server is pinned to an availability zone in the
preset's location and never silently lands elsewhere.

Location quirks worth knowing: Novosibirsk (nsk-1) has no IPv6 and no PTR
records, and images made there deploy only to SPb/Moscow; DDoS protection is
available only in SPb and Moscow.

## 4. Pick OS and software

- `list_os` — clean OS images (Ubuntu, Debian, AlmaLinux, Windows...).
- `list_software` — marketplace apps preinstalled on top of a compatible OS
  (WordPress, Docker, control panels...); check `os_ids` compatibility.
- For automated first-boot setup the panel supports cloud-init scripts.

## 5. Decide the options that cost money or affect access

- `is_backups` (required flag) — enables auto-backups, billed separately
  (see backups.md in this directory).
- Public IPv4 is a paid monthly add-on — mention it in the cost estimate.
  IPv4 addresses are floating (movable between services); IPv6 is free but
  not available everywhere (e.g. not in Novosibirsk).
- SSH keys (`ssh_keys_ids` from `list_ssh_keys`) — prefer keys over passwords.
- DDoS guard (`is_ddos_guard`, paid, SPb/Moscow only), private network
  (`is_local_network`, free) — optional.
- Cloud-init (panel): runs once at first boot; a `users:` directive disables
  root password login — see access-and-rescue.md in this directory.

## 6. Confirm money, then create

Billing is monthly and starts once the server finishes installing; the account
balance should cover the new server for 30 days. Before the first
`execute_tool("create_server", ...)`: state the exact monthly price from the
catalog, the location, and the extras (IPv4, backups). The tool does a two-step
confirmation and checks datacenter capacity BEFORE confirming — if the location
has no free resources, offer another location, do not retry the same one.

## 7. After creation

Creation is asynchronous: the server id returns immediately, provisioning takes
minutes. Check `status` via `get_server` before configuring anything. Then:
attach extra SSH keys if needed, verify backups schedule
(`get_server_disk_auto_backup_settings`), and give the user the IP from
`get_server`.
