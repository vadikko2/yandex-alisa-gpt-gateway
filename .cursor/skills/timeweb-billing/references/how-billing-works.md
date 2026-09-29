# How Timeweb Cloud Billing Works

Product semantics you cannot get from tool schemas, and a snapshot of the public
docs rather than live truth: exact figures always come from
`get_cloud_service_catalog` / `get_account_services_costs`, never from this file
or from memory. If a tool response contradicts what is written here, the tool wins.

## Charging models by service

- **Cloud servers (VDS)**: monthly price; charging starts when the server
  finishes installing. At creation the balance should cover the server for
  30 days. Public IPv4 is a separate monthly line item.
- **Backups**: billed for stored gigabytes per month, per existing copy
  (creation itself is free). Emergency copy is a fixed monthly add-on.
- **AI agents (pay-as-you-go)**: small fixed monthly fee per agent plus tokens;
  token charges are debited from the account balance **once per hour**. Input
  and output tokens are priced separately.
- **Knowledge bases**: monthly token subscription (charged immediately at
  creation and then monthly) PLUS an hourly-billed managed OpenSearch database
  under the hood. Extra token packages are valid until the end of the current
  paid period — they do not roll over.

This explains most "почему списания не совпадают с прайсом" questions: monthly
subscriptions, hourly token debits, and per-copy backup storage add up
differently within a month. `get_account_services_costs` shows the monthly
estimate per service; the panel's billing detail page shows individual debits.

## Zero / exhausted balance

When the balance runs out, service data stays available for **7 days**, after
which it is deleted — a single policy for all service types. Timeweb notifies
via email / SMS / Telegram / MAX if notifications are enabled. If
`get_account_finances` shows the balance won't cover the next month, warn the
user proactively.

## The "7 days before zero" moment

Three mechanisms all trigger at the same point — 7 days before funds run out
(figures per docs at the time of writing, verify in the panel):

- **Autopay** (if a card is bound): charges roughly one month of services;
  on failure it retries every 6 hours. Cards auto-bind after the first
  card/SBP payment; unbind in "Баланс и платежи" → "Управление".
- **Automatic invoice** (organizations only): an invoice for one month is
  generated and emailed, using the previous invoice's details; works only if
  the previous payment was also by invoice.
- **Deferred payment** window opens: extends service for up to 5 days, capped
  (a few thousand ₽), free, at most once a month, and only for accounts that
  have paid for 35+ days of service before. The debt is settled from the next
  top-up. State: `get_account_finances`.

## Top-up and discounts

Paying several months ahead gives a discount tied to the period (per docs:
3 months ≈ 5%, 6 ≈ 7%, 12 ≈ 10%; "произвольная сумма" — no discount). The
period amount is derived from the account's current monthly burn — if spending
grows later, the discount stays but the money runs out sooner.

## Individuals vs organizations

Organizations pay by invoice (bank transfer); **closing documents are issued
only for invoice payments** — paying with a corporate card gives no
accounting documents. Foreign cards work via currency conversion and are
**non-refundable**. Refunds in general: requested via a support ticket, go to
the payer (not necessarily the account owner), to the original payment method
only within a year; a FULL refund requires confirming account blocking.
Transferring money between accounts is also a support-ticket procedure.

## Where the numbers live in the panel

Most services debit **hourly**; one-time purchases (domains, SSL) appear only
in "История операций". "Подключенные сервисы" lists hourly-billed services
with monthly cost grouped by project. Gotcha: the chart shows discounted
prices while the table shows standard prices — they legitimately differ.
Table exports to CSV.

## What is panel-only or support-only (never through MCP)

Panel: top-up, payment methods and card binding, autopay, invoices and closing
documents, per-debit billing details, deferred-payment activation. Support
ticket: refunds, transferring funds between accounts. Relevant docs live under
timeweb.cloud/docs/service-payments (balance-top-up, payment-methods,
otlozhennyj-platezh, billing-details, refund, service-deletion).

## Answering "почему списалось X"

1. `get_account_finances` — balance, monthly burn, days left.
2. `get_account_services_costs` — which services cost what; name the top items.
3. If a specific debit still doesn't add up, point to the billing-details page
   in the panel and, if the user disputes it, to support. Do not speculate
   about bugs or double charging from a single number.
