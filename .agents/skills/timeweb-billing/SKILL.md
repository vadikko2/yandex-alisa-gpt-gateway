---
name: timeweb-billing
description: Answer money questions about a Timeweb Cloud account — current balance
  and how long it will last, monthly cost breakdown per service, what a new service
  would cost, account status (blocks, prime level, customer type). Use when the user
  asks "сколько денег на балансе", "на сколько хватит", "почему столько списывается",
  "что у меня жрёт деньги", "сколько будет стоить сервер/агент/база", or complains
  about charges. Do NOT use to top up the balance, manage cards, invoices or
  promo codes — that is panel-only. Prices and costs must always come from live MCP
  tools, never from pre-trained knowledge.
---

# Timeweb Cloud Billing

## How to act

All reads go through the Timeweb Cloud MCP (`timewebCloud`):
`search_tools` → `get_tool_definition` → `execute_tool`. Everything in this skill
is read-only — no confirmations needed, but also no way to move money.

## Tool map (namespace `account` unless noted)

- `get_account_finances` — balance, monthly charge estimate, how long the balance
  lasts, deferred payment state. **Primary tool for "сколько у меня денег".**
  Field notes: report `days_left` (there is also `hours_left` — same thing) and
  `monthly_cost`; `*_fee` fields duplicate the `*_cost` ones, `total_balance` is
  `balance` with fractions — don't present both. **`autopay_card_info: null`
  means no card is linked**, so nothing will save the account automatically —
  say so when the balance is short.
- `get_account_services_costs` — every active service with its monthly cost plus
  **`summary_by_type`** (per-type subtotals) and the grand total. **Primary tool
  for "что жрёт деньги".** It takes optional arguments the response depends on:
  `group_by` (`"type"` — default, adds `summary_by_type`; `"project"` — adds
  `summary_by_project`; `"none"` — services only) and `project_id` to narrow to
  one project. **Read `summary_by_type` first instead of aggregating the list
  yourself** — on a large account the services array is hundreds of entries and
  tens of kilobytes, so a client may truncate it; if that happens, use
  `project_id` to work project by project.
- `get_account_status` — blocking flags, prime flag, customer type (person/org),
  region, 2FA method, registration date. Use when charges are fine but something
  is off with the account itself.
- `get_account_auth_access` — country/IP login allowlists (security, not money).
- `get_cloud_service_catalog` (namespace `catalog`) — current prices for NEW
  services: VDS configs, DBMS/K8S/S3/balancer presets, AI models with token
  packages. **The only valid source for "сколько будет стоить X".**
- `get_service_details` (namespace `catalog`) — parameters of one existing service.

## Decision guide

| User intent | Do this |
|---|---|
| "Сколько на балансе / на сколько хватит" | `get_account_finances`; report balance, monthly burn, days left |
| "Почему так много списывается / что дорогое" | `get_account_services_costs` → start from `summary_by_type`, then name the priciest individual services. Scale the answer to the account: with a handful of services the top few explain everything; with dozens, a per-type breakdown plus a note on "small things that add up" (many IPs, balancers) is the useful shape — a bare top-3 can cover a small share of the bill and mislead |
| "Что тратит проект X" | `get_account_services_costs` with `project_id`, or `group_by: "project"` for the whole picture |
| "Сколько стоит поднять сервер / агента / базу" | `get_cloud_service_catalog` with the right service type; quote exact figures |
| "Аккаунт заблокирован? Почему не могу оплатить" | `get_account_status` for block flags, then `get_account_finances` for debt |
| "Дорого, хочу дешевле" | Costs from `get_account_services_costs` + alternatives from the catalog; propose, don't execute — resizing/deleting is panel-only |
| "Дай отсрочку / обещанный платёж" | `get_account_finances` for deferred-payment state; explain the conditions (short window, cap, once a month) and send to the panel to activate |
| "Нужны закрывающие документы / счёт" | Panel only; closing documents exist only for invoice payments (see references/how-billing-works.md) |

## Worked example: "на сколько мне хватит денег и что жрёт больше всего?"

1. `execute_tool("get_account_finances", {})` → balance, monthly burn estimate,
   days left, deferred-payment state, and whether a card is linked.
2. `execute_tool("get_account_services_costs", {})` → read `summary_by_type` for
   the shape of the spending, then pick the priciest individual services from
   the list.
3. To the user: «На балансе N ₽, при текущем наборе услуг этого хватит примерно
   на M дней. Больше всего стоят: сервер X (A ₽/мес), база Y (B ₽/мес), агент Z.
   Хотите, разберу, можно ли что-то из этого удешевить?» — all figures verbatim
   from the tools, currency named explicitly.

Why charges may not match the monthly estimate — subscriptions vs hourly token
debits vs per-copy backup storage: see
[references/how-billing-works.md](references/how-billing-works.md).

## Not available through MCP — send to the panel

- Topping up the balance, cards, autopay, invoices, closing documents, promo
  codes, activating deferred payment.
- Refunds and moving money between accounts — support-ticket procedures.
- Deleting or downgrading services to cut costs (no delete; resize is panel-only
  and upward-only).

Say it plainly and point to the panel — for money matters that is
https://timeweb.cloud/my/finances ("Баланс и платежи": top-up, cards, invoices,
per-debit detail). Don't hunt for workarounds.

## Reporting rules

- All amounts are in rubles; say the currency explicitly.
- Monthly cost vs. actual charges can differ (hourly billing, mid-month changes,
  token packages bought on top). If the user disputes a specific charge you cannot
  explain from these tools, recommend support — don't guess.
- When the balance won't cover the next month, say so proactively while answering.

## Anti-patterns (NEVER)

- NEVER state a price from memory or from training data — catalog only, every time.
- NEVER promise refunds, discounts, or write-offs — you cannot do them and support
  decides them.
- NEVER speculate about "double charging" or bugs from a single number — check
  `get_account_services_costs` totals first, then defer to support.
