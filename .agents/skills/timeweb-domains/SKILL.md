---
name: timeweb-domains
description: Manage Timeweb Cloud domains, DNS and mailboxes — check availability
  and register or prolong a domain, pay domain requests, manage domain
  administrators (registrant contacts), manage DNS records and nameservers, add
  subdomains, toggle autorenew, and create or update mailboxes and domain mail
  settings. Use when the user says "зарегистрируй домен", "поменяй A-запись",
  "домен не открывается", "смени NS", "создай почтовый ящик", "письма не
  приходят", "нужен MX/SPF/DKIM", "смени контакты администратора домена". Do NOT
  use for S3 bucket domains or App Platform domains. TLD lists and prices come
  from live MCP tools, never memory.
---

# Timeweb Cloud Domains, DNS and Mail

## How to act

Through the Timeweb Cloud MCP (`timewebCloud`): `search_tools` →
`get_tool_definition` → `execute_tool`. `[WRITE]` needs the two-step
`confirm_token` flow (300 s TTL); `[BILLABLE]` charges immediately — and domain
registration is **irreversible**, see Billing safety.

## Tool map

Domains (namespace `domains`):
- `get_account_domains`, `get_domain` — domains on the account
- `check_domain_availability`, `list_tlds` — availability and the zone catalog;
  `get_tld` — one zone in depth: registration/prolongation/transfer prices,
  allowed periods, WHOIS privacy, grace windows. (It lacks the struck-through
  old price — take discounts from `list_tlds`; for a domain the user ALREADY
  owns prefer `get_domain` — premium domains have their own prolongation cost)
- `register_domain` `[WRITE]` `[BILLABLE]`, `prolong_domain` `[WRITE]` `[BILLABLE]` —
  both create a domain REQUEST; an unpaid request (`money_source: null`) is then
  paid with `pay_domain_request`
- `list_domain_requests`, `get_domain_request` — registration/prolongation/
  transfer requests and what blocks them (the transfer auth code is never
  returned — it is a secret of the losing registrar)
- `pay_domain_request` `[WRITE]` `[BILLABLE]` — **moves money**: `money_source`
  `use` debits the balance immediately, `bonus` needs `bonus_id`, `invoice`
  needs `payment_type`+`payer_id`, `free` is valid ONLY for a transfer
  authorised by `auth_code`. Check the amount via `get_tld` and the balance via
  `get_account_finances` BEFORE calling; present the summary verbatim, never
  auto-confirm a payment
- Administrators (registrant contacts, «контактные лица»):
  `list_domain_administrators`, `get_domain_administrator` — their id is the
  `person_id` for register/prolong/pay. **Passport data is deliberately never
  returned** (only `has_passport_data`); `is_closed` = archived (unusable for
  new registrations), `is_blank` = incomplete card the registry may reject
- `create_domain_administrator` `[WRITE]` — new administrator. **Handles
  identity documents: passport fields pass through service logs as tool
  arguments — prefer the panel and use this only when the user knowingly
  accepts that.** Registry data is near-immutable afterwards: only the four
  contact fields are editable later; name/passport/INN fixes go through support
- `update_domain_administrator_contacts` `[WRITE]` — contacts only, and it
  REPLACES all four fields at once (PUT, not PATCH): read current values with
  `get_domain_administrator` and pass the unchanged ones back. A wrong email
  can block mandatory owner confirmation and suspend the domain
- `update_domain_autorenew` `[WRITE]`
- `add_domain_to_account` `[WRITE]` `[BILLABLE]` — publishes an externally
  registered domain on Timeweb nameservers and links it to the account; **may
  charge (paid transfer scenario)**, so present the operation summary and get
  approval like any billable call
- `add_subdomain` `[WRITE]`
- `get_domain_dns_records`, `get_domain_default_dns_records`,
  `create_dns_record`, `update_dns_record` `[WRITE]`
- `get_domain_nameservers`, `update_domain_nameservers` `[WRITE]`

Mail (namespace `mailboxes`):
- `get_domain_mail_info`, `update_domain_mail_info` — per-domain mail settings
- `list_mailboxes`, `get_mailbox`
- `create_mailbox` `[WRITE]` `[BILLABLE]`, `update_mailbox` `[WRITE]`
- `create_mailboxes_batch` `[WRITE]` `[BILLABLE]` — **up to 50 mailboxes per
  call**; returns HTTP 200 even when some rows fail, so always read
  `error_count` / `errors` and report which logins were NOT created

## Decision guide

| User intent | Do this |
|---|---|
| "Свободен ли домен / зарегистрируй" | `check_domain_availability` → `list_tlds` / `get_tld` for the zone's terms → `list_domain_administrators` for a valid `person_id` (never guess it — a wrong one registers the domain to the wrong entity) → quote price → `register_domain` → if the request stays unpaid, `pay_domain_request`. Registration cannot be undone or refunded |
| "Заявка висит / оплати заявку" | `list_domain_requests` / `get_domain_request` — `money_source: null` means unpaid → `pay_domain_request` with the price named and confirmed |
| "Смени email/телефон администратора домена" | `get_domain_administrator` for current values → `update_domain_administrator_contacts` with ALL four fields (it replaces, not merges). Name/passport/INN changes → support |
| "Заведи контактное лицо / администратора" | Prefer the panel (passport data in tool arguments ends up in service logs — say so); `create_domain_administrator` only when the user knowingly accepts that |
| "Домен не открывается после смены NS" | Expected: delegation takes **3–24 hours**; verify records exist in the zone BEFORE the NS change (see reference) |
| "Поменяй A-запись на новый сервер" | `get_domain_dns_records` → `update_dns_record`; propagation usually up to 3 h, sometimes 24 h |
| "Сделай поддомен" | `add_subdomain`; note TXT/SPF/DKIM for a subdomain live in the **parent** zone and subdomain NS cannot be changed |
| "Продли домен / включи автопродление" | `prolong_domain` / `update_domain_autorenew`; autorenew fires ~5 days before expiry and needs funds |
| "Заведи почту на домене" | `get_domain_mail_info` → `create_mailbox` (or `create_mailboxes_batch` from a list); MX/SPF/DKIM are created automatically when mail is enabled on a Timeweb-delegated domain |
| "Письма не приходят / уходят в спам" | Triage in references/mail.md (MX priorities, SPF/DKIM on external NS, POP3 deleting mail, forwarding chains) |
| "Перенеси домен от другого регистратора" | Registrar transfer is panel/support-only — but read references/domains-and-dns.md first: AuthInfo validity, 30-day locks, the Reg.ru NS trap |
| "Нужен SSL на домен" | Not in this skill's tools; free Let's Encrypt is issued via a load balancer, paid certs require an `admin@`-style mailbox on the domain |

## Not available through MCP — send to the panel or support

Deleting domains, DNS records, subdomains and administrators; registrar
transfers (in or out) and changing which administrator OWNS a domain (editing
an administrator's contact fields IS available); fixing an administrator's
name/passport/INN (support only); viewing passport data (panel only — tools
never return it); deleting mailboxes; mailbox quota increases (support); SSL
ordering; DNS zone import from a `.zone` file.

## Billing safety

`register_domain`, `prolong_domain`, `pay_domain_request`,
`add_domain_to_account` and mailbox creation (single and batch) move real
money. `pay_domain_request` deserves extra care: verify the amount
(`get_tld`) and the balance (`get_account_finances`) first, and never
auto-confirm — a payment summary is always read back to the user verbatim.
Three more things to say out loud before confirming:

- **Domain registration is final** — "после оказания услуги отмена и возврат
  средств невозможны", because the status is already sent to the registry.
  Double-check the spelling of the name with the user before the second call.
- **Premium domains** are priced by the registry and that price may differ from
  what the panel shows; a normal-price registration attempt simply fails and
  needs support.
- Mail is billed **per mailbox monthly, debited hourly**, and charges continue
  while **at least one** mailbox exists — deleting mail means deleting them all
  (panel).

## Legal gate for .RU / .РФ / .SU

From **1 September 2026** identification through Gosuslugi (ЕСИА) is mandatory
for *any* action in these zones — registration, prolongation, registrar change,
administrator change, contact edits and **even changing nameservers**.
Individuals and sole traders need a verified Gosuslugi account; organizations
need the company in ЕСИА with a linked employee; for non-resident legal entities
the procedure is **not defined yet**. If the account data and the domain
administrator data differ, only support can proceed. The docs do not state what
happens if identification is not completed — do not guess.

## Troubleshooting

| Symptom | Cause | Action |
|---|---|---|
| Domain dead right after NS change | Zone was moved before records were copied; delegation takes 3–24 h | Reference: always add the domain and its records first, then switch NS |
| DNS records in the panel "do nothing" | The domain is delegated to third-party NS — the Timeweb zone is inactive | Manage records at the current DNS provider, or switch NS to Timeweb |
| CNAME rejected or breaks the site | CNAME is allowed **only for subdomains**, and the value must have **no trailing dot** | Fix the record |
| Mail works but lands in spam | SPF/DKIM missing because the domain sits on external NS (they are auto-created only in Timeweb's zone) | Copy the values from the panel into the external DNS |
| "Письма пропали" from one device | POP3 deletes messages from the server by default | Switch the client to IMAP |
| Forwarding not working | Mutual A→B, B→A forwarding is forbidden and chains A→B→C break at B→C | Reference |
| Registrar transfer refused | `*TransferProhibited` status, domain expires in <7 days, or <30 days since an administrator/registrar change | Reference lists all blockers |

## Anti-patterns (NEVER)

- NEVER call `register_domain` without re-reading the exact name back to the
  user — the operation is irreversible and non-refundable.
- NEVER guess or invent a `person_id` — take it from `list_domain_administrators`
  and skip `is_closed`/`is_blank` entries.
- NEVER echo passport fields back in chat when creating an administrator, and
  never promise to show passport data — the tools never return it.
- NEVER call `update_domain_administrator_contacts` with only the changed
  field — it replaces all four; stale or missing values overwrite good data.
- NEVER change nameservers before the domain and its DNS records exist in the
  panel — that takes the site down for hours.
- NEVER quote domain prices or zone requirements from memory; zones have
  residency rules (.EU, .AE, .BY, .KZ, minimum terms for .AI) — check `list_tlds`.
- NEVER promise mailbox recovery: deleting a mailbox destroys its contents
  permanently.
- NEVER promise a universal "data kept for N days" figure — the platform-wide
  rule (7 days) and the mail page (180 days) disagree; say which product you
  mean or check with support.

Deep dives:
[references/domains-and-dns.md](references/domains-and-dns.md) — registration and
zone rules, renewal/grace chains, delegation timings, DNS record specifics,
transfers and their locks; [references/mail.md](references/mail.md) — mailbox
limits and pricing, sending limits, aliases/forwarding/antispam, MX/SPF/DKIM,
client ports, migration order.
