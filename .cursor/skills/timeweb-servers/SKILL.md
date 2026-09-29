---
name: timeweb-servers
description: Manage Timeweb Cloud servers (VDS) — create a server with the right OS,
  location and marketplace software, start/stop/reboot/clone, set up manual and auto
  backups, add disks, attach SSH keys, check CPU/RAM/disk/network usage and action
  logs. Use when the user says "подними сервер", "создай VDS", "перезагрузи сервер",
  "сервер тормозит", "настрой бэкапы", "добавь диск", or asks what happened to their
  server. Do NOT use for dedicated bare-metal servers (separate product) or for
  Kubernetes clusters. Prefer live data from the Timeweb Cloud MCP over pre-trained
  knowledge — OS lists, software and prices must come from catalog tools.
---

# Timeweb Cloud Servers (VDS)

## How to act

All operations go through the Timeweb Cloud MCP (`timewebCloud`):
`search_tools("<english keywords>")` → `get_tool_definition(tool_id)` →
`execute_tool(tool_id, arguments)`. `[WRITE]` tools return a `confirm_token`
(valid 300 s) on the first call — re-call with it after the user explicitly agrees.
`[BILLABLE]` tools charge the account immediately — always state the exact price
first (see Billing safety below).

## Tool map (namespace `servers` unless noted)

Read:
- `list_servers` — all VDS with status, resources, primary IP, location
- `get_server` — full details: disks, networks, software, DDoS-guard, availability zone
- `get_server_statistics` — CPU/RAM/disk-I/O/network time series (≤100 points/metric)
- `get_server_logs` — action log: who rebooted/restored/backed up and when
- `get_server_disk` — one disk fresh: size/used, type, status (poll it after a
  resize or while a backup runs); `get_server` already lists all disks
- `list_server_backups`, `get_server_disk_backup` (status/progress of one copy),
  `get_server_disk_auto_backup_settings`
- `list_server_restore_points`, `get_server_restore_point` — snapshots; a server
  has at most ONE, so `get_...` takes just `server_id` (404 = no snapshot, which
  is also the only state where creating one is allowed)
- `list_os`, `list_software` — OS and marketplace-app catalogs for VDS
- Catalog (namespace `catalog`): `list_locations`, `get_cloud_service_catalog` —
  locations, configurations and prices
- SSH (namespace `ssh`): `list_ssh_keys`, `get_ssh_key`

Write:
- `create_server` `[BILLABLE]` — provisions a VDS, charges start immediately
- `server_action` — start / shutdown / reboot / clone / reset password.
  `clone` is billable (a new server at the source's rate — state the price
  first); `hard_*` variants are destructive; `reset_password` is irreversible
- `update_server_meta` — rename / comment only; does NOT touch resources
- `create_server_disk` `[BILLABLE]`, `create_server_disk_backup` `[BILLABLE]`
- `update_server_disk` `[BILLABLE]` — resize (GROW only, megabytes, multiples
  of 1024, 5120–512000) and/or rename a disk. No shrink exists anywhere, so a
  wrong resize cannot be undone; the system disk of a preset server cannot be
  resized separately (that is a tariff change, panel). Growing the block device
  does not always grow the filesystem — the user may need to extend it in the OS
- `server_disk_backup_action` — `restore` / `mount` / `unmount` a disk backup.
  `restore` is DESTRUCTIVE (overwrites the disk, everything after the copy is
  lost); `mount` attaches the copy as an extra disk to pull files out —
  **prefer mount over restore when the user only needs some data back**
- `update_server_disk_auto_backup_settings` — schedule, interval, copies to keep;
  `update_server_disk_backup_comment` — label a copy (replaces, "" clears)
- Snapshots (restore points): `create_server_restore_point` `[BILLABLE]` —
  one per server, server must be ON; billed as `user_restore_point` from the
  moment it is created until commit/rollback, and it also expires on its own
  (`expired_at`). (Public docs still call snapshots free — trust the operation
  summary in the confirm step.) `rollback_server_restore_point` — DESTRUCTIVE,
  returns the whole server to the snapshot and consumes it;
  `commit_server_restore_point` — accepts the current state, deletes the
  snapshot and stops its billing (rollback becomes impossible)
- `set_server_boot_mode` — `default` / `recovery_disk` (rescue system). Switching
  REBOOTS the server. Vocabulary trap: `get_server` reports `std`/`cd`/`single`,
  this tool takes `default`/`recovery_disk`; legacy `single` cannot be set anymore.
  Never leave a server in recovery mode — it boots rescue on every restart
- `unmount_server_iso` — detaches a mounted ISO **and reboots the server** (that
  is what makes it boot from its own disk); mounting an ISO is panel-only
- `update_server_ip_ptr` — reverse DNS for one of the server's existing IPs
  (mail deliverability); `ptr: ""` clears — warn it can break working mail
- `attach_ssh_key_to_server` / `detach_ssh_key_from_server` (namespace `ssh`)

Server images (namespace `images`) — snapshots you can redeploy or download:
- `list_images`, `get_image`, `update_image_meta`
- `create_image` `[WRITE]` `[BILLABLE]` — images **every disk** of the server,
  i.e. one separately-billed image per disk. Blocked while a restore point
  (snapshot) exists or a backup is running. On a partial failure images already
  made are NOT rolled back, and on an ambiguous "request sent but not
  confirmed" error some may exist — **always `list_images` before retrying**,
  or you create duplicate billable images
- `create_image_download_url`, `list_image_download_urls` — download links

## Decision guide

| User intent | Do this |
|---|---|
| "Подними сервер / создай VDS" | `get_cloud_service_catalog` for configs+prices → `list_os` → (optionally `list_software` for WordPress/Docker/panels) → confirm price → `create_server` |
| Any request naming a server by name | `list_servers` FIRST to map the name to `server_id`. Accounts often hold dozens of servers with lookalike names — if more than one matches, or the user says "другой сервер" without naming it, ask instead of guessing |
| "Сервер тормозит / не хватает ресурсов" | `get_server_statistics` first — diagnose before proposing anything; resizing is done in the panel |
| "Хочу дешевле / уменьши тариф" | Resources can only grow. Say it plainly, then offer the real path: a new smaller server + migration (prices from the catalog so the saving is concrete). Powering the server off does NOT stop charges |
| "Что происходило с сервером / кто перезагрузил" | `get_server_logs` |
| "Настрой бэкапы" | `get_server_disk_auto_backup_settings` → `update_server_disk_auto_backup_settings`; one-off copy → `create_server_disk_backup` (billable until deleted) |
| "Восстанови из бэкапа" | `list_server_backups` → read `created_at` and tell the user which point in time they go back to → `server_disk_backup_action(action="restore")` — destructive, everything after the copy is lost. If they only need a few files, `mount` the backup as an extra disk instead |
| "Сделай снапшот перед рискованной операцией" | `get_server_restore_point` first (a second snapshot is rejected) → `create_server_restore_point`. Afterwards close it out: `commit` when the change worked (stops billing), `rollback` when it didn't. Don't leave it hanging — it costs money and expires on its own |
| "Диск маловат / добавь места на диске" | `update_server_disk` with the new size in MB — grows only, never shrinks; system disk of a preset server → tariff change in the panel. Remind about extending the filesystem inside the OS |
| "ОС не грузится / нужен rescue" | `set_server_boot_mode(boot_mode="recovery_disk")` (reboots the server), repair, then ALWAYS set back to `default` — see references/access-and-rescue.md |
| "Сервер грузит установщик по кругу" | A mounted ISO — `unmount_server_iso` (warns: it reboots the server) |
| "Почта с сервера уходит в спам / нужен PTR" | `update_server_ip_ptr` — PTR must match the sending hostname's forward record |
| "Дай доступ разработчику" | `list_ssh_keys` → `attach_ssh_key_to_server` |
| "Переустанови пароль / перезагрузи" | `server_action` |
| Anything about bare-metal | `list_dedicated_servers` (namespace `dedicated`) — read-only, separate product |

## Worked example: "подними сервер под сайт"

1. `search_tools("create server")` → `create_server` (namespace `servers`).
2. `get_tool_definition("create_server")` → required: `name`, `preset_id` OR
   `configuration`, `os_id` OR `image_id`, `is_backups`. The schema says: fetch
   real ids from the catalog first, never guess them.
3. `execute_tool("get_cloud_service_catalog", {service_type: "server"})` →
   presets with prices and locations; `execute_tool("list_os", {})` → OS id.
4. To the user: «Предлагаю тариф 2 CPU / 2 ГБ RAM / 40 ГБ NVMe в Санкт-Петербурге
   за N ₽/мес (цена из каталога) + публичный IPv4 отдельной строкой. Списание
   начнётся сразу после установки. Создаю?»
5. First `execute_tool("create_server", {...})` → returns `confirm_token` and an
   operation summary with price and location. User says yes → repeat the same
   call with `confirm_token` added.
6. Creation is async: the id returns immediately, provisioning takes minutes —
   poll `get_server` for status, then report the IP.

Deep dives: [references/create-server.md](references/create-server.md) —
full SOP (preset vs configurator, locations, options);
[references/backups.md](references/backups.md) — backups vs snapshots,
billing semantics, restore, gotchas;
[references/server-lifecycle.md](references/server-lifecycle.md) — resize
rules, reinstall, cloning, images, deletion protection, IP behavior;
[references/access-and-rescue.md](references/access-and-rescue.md) — locked
out / SSH dead / boot modes / root password / monitoring quirks / cloud-init.

## Not available through MCP — send to the panel

- **Deleting a server, disk, or backup** — no delete operations exist at all.
  A deleted server is normally unrecoverable; paid deletion protection gives a
  72-hour restore window (see references/server-lifecycle.md). When the user
  deletes to stop paying, warn about what keeps billing afterwards: a public IP
  kept on the account, server images (they outlive the server), and stored
  backups — check `list_images` and `list_server_backups` and tell the user
  which ones to remove in the panel too.
- **Resizing CPU/RAM or changing the preset** — panel only, and only
  **upward**: resources can never be reduced; a CPU/RAM change reboots the
  server. For "хочу дешевле" the answer is a new smaller server + migration.
  (Growing an ADDITIONAL disk IS available via `update_server_disk`; the system
  disk of a preset server still means a tariff change in the panel.)
- **OS reinstall and transfer to another account** — panel only; each has
  data/IP consequences, see references/server-lifecycle.md before advising.
  (Cloning IS available via `server_action`, and images via `create_image` —
  but read the lifecycle reference first: new IP on clones, per-disk billing
  and retry hazards on images.)
- **Deleting an image** — panel only, so every image keeps billing until the
  user removes it.
- **Mounting an ISO image** — panel only (unmounting IS available via
  `unmount_server_iso`).

When `search_tools` answers `not_exposed`, quote its reason to the user, link the
panel (https://timeweb.cloud), and stop. Do not substitute a different tool.
Note on resize specifically: **no tool for it exists, and `search_tools` does
NOT return `not_exposed` for it** — it answers with unrelated tools
(`update_server_meta`, `server_action`, `create_server`) and may even report
`confidence: "high"`. High confidence here means nothing: none of those tools
resizes anything. Never pick one of them, never treat the absence of
`not_exposed` as permission — send the user to the panel.

## Billing safety

Before any `[BILLABLE]` call: fetch the current price from the catalog, tell the
user the exact monthly cost and that charging starts immediately, and get an
explicit yes. Backups and extra disks are billed separately until deleted — say so
when creating them. Two additions:

- **Disk resize is one-way** — `update_server_disk` raises the recurring cost and
  there is no shrink anywhere, so a mistake cannot be undone. State the new size
  and price before confirming.
- **A snapshot bills until closed** — `create_server_restore_point` starts the
  `user_restore_point` charge; it stops only on `commit` or `rollback`. Plan the
  exit when creating it, don't leave it hanging.

## Troubleshooting

| Symptom | Cause | Action |
|---|---|---|
| `search_tools` returns nothing useful | Query too vague or in Russian | Rephrase with different English keywords (action + resource) |
| `search_tools` returns `not_exposed` | Operation deliberately closed | Quote reason, point to panel, stop |
| `execute_tool` rejects a mutation | Missing/expired `confirm_token` (300 s TTL) | Re-run the call to get a fresh token, confirm with the user, retry |
| Stats look stale | `is_actual: false` on the metric | Tell the user data is delayed; don't diagnose from stale points |
| Server misbehaves right after create | Provisioning still in progress | Check `status` via `get_server` before deeper debugging |
| Disk/backup/reinstall/clone/image operation refused | Active snapshot blocks all of them (image creation also blocks on a running backup) | `get_server_restore_point` to confirm → close it out via `commit_server_restore_point` (keep current state) or `rollback_server_restore_point` (go back) — the user's call, both need explicit consent |
| `create_server_restore_point` rejected with 400 | A snapshot already exists (one per server) or the server is powered off | `get_server_restore_point` first; power on if needed |
| Restore/rollback finished but data looks half-old | Async operation still running | Poll `get_server_disk_backup` (restore) / `get_server_restore_point` (rollback) until done before concluding anything |
| `create_image` returned an unclear error | Upstream race — images may already exist | `list_images` FIRST; never blind-retry, it duplicates billable images |
| "Не могу зайти по SSH / забыл пароль" | Network/auth issue, not necessarily server death | Web console works without SSH; root password is shown in the panel — see references/access-and-rescue.md |

## Anti-patterns (NEVER)

- NEVER quote server prices, OS lists, or software lists from memory — catalog only.
- NEVER call a `[BILLABLE]` tool without naming the price and getting explicit consent.
- NEVER "work around" a missing delete/resize by creating a replacement resource
  unless the user explicitly asked for exactly that.
- NEVER confuse VDS (`list_servers`) with dedicated servers (`list_dedicated_servers`).
- NEVER reset a server password or detach an SSH key without spelling out that it
  changes login access.
- NEVER run `server_disk_backup_action(restore)` or `rollback_server_restore_point`
  without reading `created_at` and telling the user which point in time they go
  back to — both destroy everything written after it, with no undo. When the user
  only needs some files, mount the backup instead of restoring.
- NEVER leave a server in `recovery_disk` boot mode after the repair — it keeps
  booting the rescue system on every restart.
