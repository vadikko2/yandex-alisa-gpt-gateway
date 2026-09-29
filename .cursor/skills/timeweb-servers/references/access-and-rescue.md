# Access and Rescue: SSH, Passwords, Console, Boot Modes, Monitoring

Snapshot of the public docs, not live truth: if a tool response or the panel
contradicts this file, they win. MCP covers SSH keys (`list_ssh_keys`,
`attach_ssh_key_to_server`, `detach_ssh_key_from_server`), stats/logs
(`get_server_statistics`, `get_server_logs`), boot modes
(`set_server_boot_mode`) and ISO unmounting (`unmount_server_iso`); everything
else here is panel-side knowledge for correct advice.

## SSH keys

- A key can be added to a **running** server — applies within a couple of
  minutes, **no reboot**. Keys are also set at creation and OS reinstall.
- There is a "default key" option: auto-add to every new server.
- Password login can be disabled when a key is attached — confirm with the
  user before advising that.

## Root password

- The panel shows the current root password (Dashboard → Access). If someone
  changed it **inside the OS**, the panel value is stale — a common confusion.
- Password reset is done from the panel without OS access; the new password
  appears in the panel. If both password and panel access are lost — recovery
  boot mode (below).

## Web console — the path when SSH is dead

- Works **independently of the public network and SSH** — first thing to
  suggest when the user is locked out ("не могу зайти по SSH").
- Linux has two console types: serial (recommended: copy/paste, scroll) and
  VNC. Serial console is enabled by default only on servers created after
  2024-04-04; on older ones it must be enabled from inside the OS first.

## Boot modes (MCP: `set_server_boot_mode`)

- The tool takes `default` / `recovery_disk` and **reboots the server** on
  every switch. Not every OS supports rescue mode; the server must be powered
  on and not busy.
- Vocabulary trap: `get_server` / `list_servers` report the mode in panel
  terms — `std` (= default), `cd` (= recovery_disk), `single` (legacy). Never
  pass `std` back to the tool, and don't treat it as unknown. The legacy
  `single` mode can no longer be set through the API — panel only.
- **Single-user** (panel-only now): for broken fstab/services, fsck, config
  fixes. No SSH — VNC console only; root without authentication, so advise
  returning to standard mode immediately after the fix.
- **Recovery disk**: for resetting an unknown root password, repartitioning,
  rescuing files before reinstall. SSH is blocked by its firewall by default;
  the system disk appears as a secondary device and must be mounted manually.
  Always switch back to `default` after the repair — the server keeps booting
  the rescue system otherwise.
- Hard reboot (hypervisor level) loses RAM contents and may trigger fsck —
  suggest soft reboot first, hard only when the server is truly hung.
- A server endlessly booting an OS installer usually has an ISO still
  mounted — `unmount_server_iso` detaches it (and reboots the server).
  Mounting an ISO remains panel-only.

## Tech-support access

- Linux only: a toggle on the "Access" tab adds the support team's SSH key —
  no need to hand over passwords. Reversible anytime. Support helps for free
  with panel actions, disks, root reset, standard software installs and
  transfers; it does NOT do code fixes, CMS setup, OS upgrades, Docker
  debugging, or Windows servers.

## Monitoring gotchas (get_server_statistics / panel graphs)

- **Without a public IPv4 the RAM and disk-load metrics are missing** — don't
  interpret their absence as a problem.
- Disk-space stat updates hourly and is unavailable with multiple partitions
  or LVM. At 95% disk usage the user gets an email.
- The monitoring agent uses port 10050/TCP — if the user runs a strict
  firewall, Timeweb's monitoring IPs must be allowed, otherwise graphs go
  empty.

## Cloud-init gotchas

- `runcmd` executes **once** at first boot; editing the script on a live
  server does nothing until `cloud-init clean --reboot`.
- Everything runs as root; interactive commands need `-y`; log:
  `/var/log/cloud-init-output.log`.
- Trap: a `users:` directive (and the default `ubuntu` user on Ubuntu)
  **disables root password login** — a frequent "я не могу войти после
  создания" cause; fix via `chpasswd` or SSH keys.
