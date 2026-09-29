# Server Lifecycle: Resize, Reinstall, Clone, Images, Delete, Transfer

Snapshot of the public docs (timeweb.cloud/docs/cloud-servers/manage-servers/*),
not live truth: if the panel or an MCP response contradicts this file, they win —
say so instead of insisting on what is written here.

Most of these operations are **panel-only**, with the exceptions the MCP does
expose: cloning (`server_action` with action "clone"), image creation
(`create_image`), growing a non-system disk (`update_server_disk`), disk-backup
restore/mount (`server_disk_backup_action`) and snapshots
(`create/rollback/commit_server_restore_point`). For the rest your job is to
explain consequences correctly and point to the panel.

## Resize (tariff/configuration change) — upgrade only

- Configuration changes go **only upward**: CPU, RAM and disk can never be
  reduced. Disk grows in 5 GB steps.
- Changing CPU/RAM requires "save and reboot" — there IS downtime.
- Growing an ADDITIONAL disk is exposed via `update_server_disk` (megabytes,
  multiples of 1024, 5120–512000 MB). The SYSTEM disk of a preset server is
  tied to the tariff and resizes only with it — panel.
- After growing the disk, partitions inside the OS sometimes must be extended
  manually — warn about this.
- A custom (configurator) setup costs more than a fixed preset with the same
  specs. Up to 10 additional disks (local and network) per server.
- So for "нужно меньше/дешевле" there is exactly one honest path: create a new,
  smaller server and migrate the data, then delete the old one. Downsizing an
  existing server is impossible, and cloning does not help — a clone inherits
  the source configuration, so it cannot be smaller.
- Note for tool selection: unlike deletion, a resize request does **not** trigger
  a `not_exposed` answer from `search_tools`; it returns unrelated tools, even
  with high confidence. Nothing in that result set resizes a server.

## The snapshot blocker (global rule)

While a server has an active snapshot (точка восстановления), the following are
all blocked: any disk operations, backup create/delete, OS reinstall, cloning,
image creation. If a panel operation mysteriously refuses — ask about snapshots
first (`get_server_restore_point`), then close the snapshot out via
`commit_server_restore_point` or `rollback_server_restore_point`. Snapshots
auto-expire after 7 days; the docs call them free, but the MCP bills them as
`user_restore_point` until committed or rolled back — trust the operation
summary. See references/backups.md.

## OS reinstall

- **Wipes all data on the system disk**; panel asks to confirm by typing the
  server name. Backups survive the reinstall; private-network settings are
  kept; the IP is kept.
- Options at reinstall: clean OS, marketplace build, or your own image;
  hostname/SSH key/cloud-init can be set again.
- Blocked while a snapshot exists.

## Cloning (available via MCP: `server_action` with action "clone")

- Billable: the clone is a new server billed at the source server's rate —
  state the price and get consent before executing (two-step confirm applies).
- Copied: configuration, disk data, additional **local** disks. NOT copied:
  network disks, backups/snapshots, panel licenses (ispmanager needs a new one).
- The clone always gets a **new IP**; internal network configs referencing the
  old IP must be fixed by hand.
- Requirements: server powered ON, no snapshots, enough balance. No downtime
  for the original. GPU servers clone only via support.
- Clone is billed at current catalog prices (grandfathered/archive tariffs are
  inherited).

## Server images (available via MCP: `create_image`)

- Full server copy (OS + software + data), qcow2; billed per GB monthly,
  debited hourly. Images live independently of the server and **survive its
  deletion** — and keep costing money until removed (deletion is panel-only).
- `create_image` snapshots **every disk** of the server — a server with three
  disks yields three separately billed images. State that before confirming.
- Blocked while a restore point (snapshot) exists or a backup is in progress.
- Failure handling matters here: a partial failure does NOT roll back the
  images already created, and an "unconfirmed outcome" error may still have
  created them. Always `list_images` before any retry. Image names follow
  `image_for_server_{vds_id}_disk_{disk_id}`, so you can map them to disks;
  status moves to `created` or `failed`.
- Downloads: `create_image_download_url` (and `list_image_download_urls`).
- Custom image upload: ISO, VMDK, VHD, VHDX, VDI, RAW, IMG, QCOW2; up to 500 GB.
- Images created in Novosibirsk can be deployed only in SPb or Moscow.
- At zero balance images are kept 7 days, then auto-deleted.

## Deletion and deletion protection

- Deletion is normally **irreversible**; confirmed by phone/Telegram code or
  typing the server name.
- On deletion the public IP can be **kept on the account** for reuse — and it
  keeps being billed while it exists (Networks → Public IPs to release).
- **Deletion protection** is a paid per-server insurance: with it, a deleted
  server can be restored free within **72 hours** (everything including
  backups). Without it a one-time paid restore may be possible. Only for
  servers older than 48 hours on the account. Restore may land in a different
  location if the original has no capacity (price may change), and the server
  gets a new IP unless the old one is still held on the account.

## Transfer between accounts

- Moves the server with IP, backups and all disks (network disks included);
  a running server moves without shutdown.
- Gotchas: a server in a private network is **removed from it and rebooted**;
  the public IP **may change** (panel warns); the receiving account must have
  enough funds or the server is blocked immediately.
- Two-sided: sender can cancel until accepted, recipient can decline.

## When does the IP change? (summary)

| Operation | Public IP |
|---|---|
| OS reinstall | kept |
| Clone | always new |
| Move into a private network | may change |
| Transfer to another account | may change |
| Restore after deletion | new (old only if still held on the account) |
| Delete server | can be kept on the account — billed until released |
