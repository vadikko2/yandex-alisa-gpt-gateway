# Backups and Snapshots

Snapshot of the public docs (timeweb.cloud/docs/cloud-servers/manage-servers/backup),
not live truth: the per-GB rate comes from the panel or the catalog, never from
this file. If a tool response contradicts what is written here, the tool wins.

## Two different mechanisms

- **Backups** — full copies of a single disk stored on separate storage.
  Created manually (`create_server_disk_backup`) or on a schedule
  (`update_server_disk_auto_backup_settings`). Billed.
- **Snapshots (restore points)** — instant point-in-time images of the whole
  server, at most ONE per server, auto-deleted after 7 days (`expired_at`).
  Fully manageable via MCP: `create_server_restore_point` →
  `rollback_server_restore_point` (go back, consumes the snapshot) or
  `commit_server_restore_point` (accept current state, deletes the snapshot).
  The docs page calls snapshots free, but the MCP marks creation `[BILLABLE]`
  (`user_restore_point`, billed from creation until commit/rollback) — trust
  the operation summary in the confirm step over this file and over the docs.
  The server must be powered ON for all three operations.

## Billing semantics (important for cost questions)

You pay for **storing** backups (per GB of disk size, monthly), not for creating
them. Every existing copy is billed until it is deleted — and deletion is
panel-only, so warn the user when creating manual backups that each copy keeps
costing money until they remove it in the panel. Exact per-GB rate: public docs
(timeweb.cloud/docs/cloud-servers/manage-servers/backup) or panel.

## Auto-backup schedule

`update_server_disk_auto_backup_settings` per disk: enable/disable, interval
(day / week / month), day-of-week for weekly, start date, and how many copies
to keep. With `copies = 1` each new backup overwrites the previous one — cheapest
option, but only one restore point. More copies = more restore points = more
storage billed.

## Restoring

Both paths go through `server_disk_backup_action` (only a backup in status
`done` can be acted on; the operation is async — poll `get_server_disk_backup`):

- **Full restore** (`action: "restore"`) — DESTRUCTIVE: overwrites the disk with
  the copy, everything written after it is lost, no undo. Read `created_at`
  first and tell the user which point in time they are going back to.
- **Mount** (`action: "mount"`) — attaches the copy to the server as an
  additional read-only disk to pull individual files (not available for Windows
  servers); the user mounts it inside the OS. Detach with `action: "unmount"`.
  Prefer this over restore when the user only needs some data back.

Backups can also be downloaded as `.qcow2` (SPb and Moscow locations) — panel.

## Gotchas

- An active snapshot blocks disk operations: no backup create/delete, no OS
  reinstall, no cloning, no image creation until the snapshot is gone.
- A manual backup takes seconds to minutes depending on disk size; check status
  in `list_server_backups` (`progress` 0–100) before relying on it.
- Backup belongs to a disk, not a server — on multi-disk servers confirm which
  disk the user means (`get_server` lists all disks).
