---
name: timeweb-account
description: Inspect and manage the Timeweb Cloud account itself — account status
  and blocking flags, login restrictions by IP and country, notification channel
  settings (email/SMS/Telegram/MAX/push), current incidents and
  maintenance affecting the account, projects (grouping resources), and SSH keys.
  Use when the user says "заблокирован аккаунт", "ограничь вход по IP", "почему не
  работает / это авария?", "настрой уведомления", "создай проект", "перенеси
  сервер в проект", "добавь SSH-ключ", or asks about 2FA, passkey, API tokens,
  sub-users and their rights.
  Do NOT use for balance and charges (that is the billing skill) — this skill
  covers who can get in and how resources are organized, not money.
---

# Timeweb Cloud Account, Access and Projects

## How to act

Through the Timeweb Cloud MCP (`timewebCloud`): `search_tools` →
`get_tool_definition` → `execute_tool`. `[WRITE]` needs the two-step
`confirm_token` flow (300 s TTL). Nothing here is `[BILLABLE]`, but two tools
can lock the user out of their own account — see Danger zone.

## Tool map

Account (namespace `account`):
- `get_account_status` — blocking flags, prime, customer type (person/org),
  region, 2FA method, registration date. Quick boolean flags only
- `get_account_relevant_avr` — **incidents and maintenance affecting THIS
  account**: active ones plus those closed in the last 24 h, with type
  (авария / плановые работы), status, timeline of updates and a link to the
  status page. First stop for "у меня всё сломалось, это вы?"
- `get_account_auth_access` — country and IP allowlists with per-list enabled flag
- `list_auth_access_countries` — the CATALOG of valid country codes (ISO code →
  localized name) for the allowlist, not the current list; use it to turn
  "разреши вход из Германии" into a code. Requires an admin-level API token —
  a scoped token gets 403 here
- `add_account_allowed_country`, `add_account_allowed_ip` `[WRITE]` — **append**
  to an allowlist (removal is panel-only)
- `set_account_auth_restriction_countries`,
  `set_account_auth_restriction_ips` `[WRITE]` — turn a restriction on/off
- `get_account_notification_settings` — per-event channel map. Channel values
  are FOUR, not two: `on`/`off` are changeable; `disabled_on` = forced on and
  cannot be turned off (e.g. password recovery email); `disabled_off` =
  unavailable for that event. A missing channel = not configured at all
- `update_account_notification_settings` `[WRITE]` — the backend MERGES: send
  only the events/channels being changed, with `type` codes verbatim from the
  read tool. Locked channels (`disabled_*`) silently keep their default even
  though the call "succeeds" — never promise changing them. Telegram/MAX work
  only after the user binds them (the binding itself is panel-only). Needs an
  admin-level token — scoped tokens read fine but get 403 on write
- For balance, costs and deferred payment use the **timeweb-billing** skill

Projects (namespace `projects`):
- `list_projects`, `get_project`, `list_project_resources`,
  `list_all_resources_with_projects`
- `create_project`, `update_project` `[WRITE]`
- `add_resource_to_project`, `transfer_resource_to_project` `[WRITE]`

SSH keys (namespace `ssh`):
- `list_ssh_keys`, `get_ssh_key` — public keys are returned in full (public data)
- `create_ssh_key`, `update_ssh_key_meta` `[WRITE]`
- Attaching/detaching to a server lives in the **timeweb-servers** skill

## Danger zone — locking the user out

`set_account_auth_restriction_ips` / `..._countries` allow login **only** from
the allowlist. Enabling either one with an incomplete list locks the user out of
their own account, and **removing entries from an allowlist is panel-only** —
so the agent cannot undo it. Public docs describe no recovery procedure for
self-lockout.

Mandatory sequence, no shortcuts:
1. `get_account_auth_access` — read the current lists and flags.
2. Ask the user for their **current** public IP (or country) and confirm it is
   already in the list; add it first with `add_account_allowed_ip` if not.
3. Only then `set_account_auth_restriction_ips` with the two-step confirmation,
   spelling out: "если твоего адреса нет в списке, ты потеряешь доступ, а снять
   ограничение через меня нельзя — только в панели".

If the user is on a dynamic IP or behind mobile internet, say plainly that an
IP allowlist is a bad fit and suggest the country restriction instead.

## Decision guide

| User intent | Do this |
|---|---|
| "У меня всё лежит / это авария?" | `get_account_relevant_avr` FIRST — before debugging anything. Report type, status, timeline and link; if it is closed, say it was resolved |
| "Аккаунт заблокирован" | `get_account_status` for flags, then the billing skill for balance — the two causes behave differently (see references/access-and-security.md) |
| "Ограничь доступ по IP / странам" | Follow Danger zone above, never in one step; country codes come from `list_auth_access_countries`, not from memory |
| "Настрой уведомления / шли алерты в Telegram" | `get_account_notification_settings` → `update_account_notification_settings` with only the changed events. `disabled_on`/`disabled_off` channels can't be changed — say so instead of pretending; unbound Telegram/MAX → bind in the panel first |
| "Убери IP из списка / сними ограничение" | Removal from an allowlist is panel-only; disabling the restriction IS possible via `set_..._restriction_*` with `is_enabled: false` |
| "Создай проект / разложи ресурсы" | `create_project` → `add_resource_to_project`; moving an existing resource — `transfer_resource_to_project` |
| "Раздели биллинг по проектам" | Not a thing: single account balance; projects only give a per-project cost breakdown |
| "Дай доступ сотруднику" | Sub-users are panel-only — and read the rights traps in references/access-and-security.md BEFORE advising; "только просмотр" is not read-only in the security sense |
| "Добавь SSH-ключ" | `create_ssh_key`; attach to servers via the servers skill |
| 2FA, passkey, API tokens, login logs | Panel-only; the reference explains the semantics and what docs do NOT cover |

## Not available through MCP — send to the panel

Managing 2FA and passkeys, issuing/revoking API tokens, login logs and session
termination, creating and blocking sub-users and their rights, binding
Telegram/MAX for notifications (changing notification channels IS available),
deleting projects, removing entries from allowlists, account deletion (support
only), linking accounts.

## Troubleshooting

| Symptom | Cause | Action |
|---|---|---|
| Services down across the board | Provider-side incident | `get_account_relevant_avr`; public status page is timeweb.cloud/live |
| "2FA включена, но не спрашивает код" | A configured passkey disables 2FA | Explain the trade-off (reference) |
| Sub-user "с просмотром" changed things on a server | View-only still exposes service passwords → SSH access | Reference explains; the fix is removing the section access, in the panel |
| Sub-user sees other projects' spending | Finance access is always account-wide | Expected by design, not a bug |
| Token stopped working after reissue | Reissue invalidates the old token | Issue a new one in the panel; it is shown once |
| 403 on notification settings or country catalog with a working token | Those endpoints need an ADMIN-level API token; scoped tokens read other account data fine | Tell the user to use/issue an admin token |
| Notification change "succeeded" but nothing happened | The channel is `disabled_on`/`disabled_off` — locked by the platform | Read the settings back and explain the lock |

## Anti-patterns (NEVER)

- NEVER enable an IP/country restriction without verifying the user's current
  address is already allowlisted — you cannot undo the list, only the flag.
- NEVER call a view-only sub-user "safe": they can read service passwords.
- NEVER invent recovery procedures for lost 2FA or self-lockout — the docs have
  none; route to support (verification via documents/video call).
- NEVER promise per-project balances or audit logs of sub-user actions —
  neither exists today.
- NEVER paste API tokens or service passwords into the chat or logs.

Deep dive: [references/access-and-security.md](references/access-and-security.md) —
sub-user rights traps, 2FA/passkey/token semantics, blocking scenarios,
projects, Telegram-bot risk, and the list of things public docs do not answer.
