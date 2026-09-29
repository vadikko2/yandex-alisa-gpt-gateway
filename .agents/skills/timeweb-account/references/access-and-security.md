# Account Access, Sub-users, Blocking, Projects

Snapshot of the public docs (timeweb.cloud/docs/account-management, /docs/iam,
/docs/projects), not live truth: if a tool response or the panel contradicts
this file, they win.

## Sub-user rights — the traps that matter

Timeweb has no role templates: rights are set **per panel section**, at three
levels — Управление (same as owner), Только просмотр, Нет доступа — scoped to
all projects or selected ones. Four consequences worth stating out loud before
anyone delegates access:

1. **"Только просмотр" is NOT read-only in the security sense.** It shows all
   information in the section, **including service passwords** — so view-only
   on cloud servers means the person cannot delete the server but can SSH into
   it and do anything inside.
2. **Finance access is always account-wide.** Even a user limited to one
   project sees every service's spending in "Баланс и платежи".
3. **A user without finance access can still create paid services** if the
   account has money.
4. **Granting access to databases / servers / balancers automatically grants
   the same level on private networks, firewall and public IPs.**

Sub-user API tokens inherit that user's rights, not more. Sub-users cannot:
manage notifications, add/remove users, create/delete or move services between
projects, or request a server transfer between accounts — those are
owner-only. Access is revoked by blocking (temporary, settings kept) or
deleting; both look like "wrong login/password" to the person.

## 2FA, passkey, tokens (panel-only, semantics worth knowing)

- **2FA** methods: SMS, Telegram/MAX, email, authenticator apps. Disabling it
  requires a code from the active method.
- **A configured passkey disables 2FA even when 2FA is switched on** — flag
  this as a security downgrade, not a convenience. Passkeys are owner-only, not
  available to sub-users, and never replace password login, so losing all
  passkeys does not lock the account.
- **API tokens**: lifetime chosen at creation (including "бессрочно"),
  optionally limited to specific services. Shown **once** — no way to view it
  again. Reissuing invalidates the old value; a leaked token is handled by
  deleting/reissuing it in "API и Terraform".
- **Login logs** show date, device, IP, country/city; sessions can be
  terminated individually or all but the current one. A password change
  terminates other sessions automatically.

## What the public docs do NOT answer (never invent these)

- Recovery when **2FA is lost**, or when the user **locks themselves out** with
  an IP/country restriction — no procedure is documented.
- Whether IP/country restrictions and 2FA apply to **API access** (the wording
  covers "доступ в панель управления").
- Limits on the number of IPs/countries, tokens, sub-users, projects, passkeys.
- Retention of login logs, whether failed logins are recorded, any audit trail
  of sub-user actions.
- Reversibility and timing of account deletion, and what happens to remaining
  funds.

For lost email access, recovery is identity verification through support:
organizations send a signed request with company documents; individuals send a
photo with their passport and then join a short video call. Names on the
account must match the documents.

## Blocking — two different scenarios

- **Zero/negative balance**: services and all related data (including server
  images) stay available for **7 days**, then everything is deleted
  automatically. Email notice on the day of blocking. After payment, servers
  that were running come back up by themselves.
- **Terms violation** (spam, prohibited content): **no auto-deletion**, but
  **charges keep accruing** until the user deletes the service; email explains
  the violation and the deadline.

## Projects

A project is a logical grouping in the panel; it changes nothing technically.
An unassigned service lives in "Общий проект". Resources can be added or moved
at any time (`add_resource_to_project` / `transfer_resource_to_project`), but
only by the account owner. Billing stays on a **single account balance** —
projects give a per-project cost breakdown, and per-project balances are
explicitly a future feature. Docs do not say what happens to services when a
project is deleted, so don't promise anything there.

## Incidents and maintenance

`get_account_relevant_avr` returns incidents ("Авария") and scheduled
maintenance ("Профилактические работы") relevant to this account, including
ones closed in the last 24 hours — so you can tell the user their problem was
already resolved. Each entry carries status, start/end, the full history of
updates and a link. The public status page is **timeweb.cloud/live**; the term
used publicly is "инциденты"/"плановые работы" (the internal abbreviation АВР
does not appear in the docs). No availability SLA percentages are published;
first support response is stated as up to 1 hour, and Kubernetes is documented
as provided "as-is".

## Telegram-bot risk worth mentioning

The bot can be granted extended rights: powering servers on/off, rebooting,
**retrieving SSH connection data**, managing backups. Basic functions only are
enabled by default. Since the bot also works in **group chats**, extended
rights in a group mean every participant effectively controls those servers —
the docs do not flag this, so you should.
