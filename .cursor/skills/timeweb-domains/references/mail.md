# Mail: Mailboxes, Limits, DNS, Migration

Snapshot of the public docs (timeweb.cloud/docs/mail/*), not live truth: prices
from the catalog/panel; if a tool response contradicts this file, the tool wins.

## Pricing and lifecycle

Standard plan: up to **500 mailboxes**, priced **per mailbox monthly**, up to
100 GB per box; from 501 boxes it becomes corporate mail with individual
pricing. Charges are **debited hourly and continue while at least one mailbox
exists** — to stop paying, every mailbox must be deleted (panel). Deleting a
mailbox **destroys its contents irreversibly**.

Note a documented contradiction: the mail billing page promises data availability
for **180 days** after blocking, while the platform-wide rule is **7 days**.
Don't quote either as universal — name the product or send the user to support.

## Mailbox naming and quota

Name: latin letters only (even on a Cyrillic domain), digits and `.`, `-`, `_`.
Password: digits, upper/lowercase latin, special characters **except `&`**;
minimum length is not documented. Creation is instant, single or in bulk
(`create_mailboxes_batch`, **max 50 per call** — split larger lists into
batches, and check `error_count`/`errors` because a partially failed batch still
returns HTTP 200). Quota is 100 GB by default and increasing it is
**support-only** right now.

## Sending limits (the usual cause of "письма не уходят")

- Message size up to **35 MB**; attachment via the web interface up to 1 GB.
- Up to **100 recipients** per message (only 10 through the legacy roundcube).
- **2000 messages per day** across all mailboxes and **5 per second**; a
  dedicated server with administration allows up to 10 000 per hour.
- **Mutual forwarding A→B and B→A is forbidden**, and chains break: with
  A→B→C the B→C hop does not fire. Silent failure — check this early.

## Features worth knowing

- **Aliases**: up to 10 per mailbox, free, all mail lands in the main box.
  Sending *from* an alias works **only in the Timeweb.MAIL web interface** —
  third-party clients cannot.
- **Antispam** is Rspamd, on by default for new boxes; the Spam folder is kept
  **30 days** then purged. A per-mailbox whitelist bypasses checks.
- **Catch-all** collects mail for non-existent addresses of the domain.
- **Autoreply** can be set by the admin, but the mailbox owner can switch it off
  even then.
- **Mailbox 2FA** (SMS or Telegram) protects **only the web interface** — SMTP
  and IMAP are unaffected, and there are no app passwords. An admin can force
  2FA for all mailboxes of a domain.

## DNS for mail

MX records: `mx1.timeweb.ru.` priority **10**, `mx2.timeweb.ru.` priority **20**.
**SPF and DKIM are created automatically when a mailbox is created for the
domain** — but only inside Timeweb's zone. If the domain lives on external NS,
the values must be copied from the panel into that provider's DNS by hand; this
is the number one reason mail is delivered to spam. DKIM for mail sent by
**scripts on a server** (`php mail()`) is not configured automatically at all —
it needs an own key, a `mail._domainkey` TXT record and matching selector in the
mailer. DMARC is not covered by the docs.

## Client settings

| Protocol | Host | Ports |
|---|---|---|
| SMTP | `smtp.timeweb.ru` | 587 STARTTLS, 465 SSL (25/2525 unencrypted) |
| IMAP | `imap.timeweb.ru` | 993 SSL, 143 STARTTLS |
| POP3 | `pop3.timeweb.ru` | 995 SSL, 110 STARTTLS |

Login is the full mailbox address. **POP3 deletes messages from the server after
download by default** — the standard explanation for "письма пропали на другом
устройстве"; recommend IMAP.

## Migration order matters

Migration is IMAP sync (roughly 1 GB per minute). The source needs IMAP enabled,
and Yandex/Mail.ru/VK/Gmail require **app passwords**, not the main password.
The documented ordering rule: **import first, switch MX afterwards** — some
providers (Mail.ru explicitly) cut access to the source once MX changes. After
migration, remove the domain at the old provider or mail keeps arriving there;
DNS propagation is 3–24 hours, during which messages may still reach the old
servers.

## Bulk mailing

Required by the docs: double opt-in, working SPF and DKIM, `List-Unsubscribe`
headers, a valid `Message-ID`, `Precedence: bulk`, one-click unsubscribe.
Mail.ru blocks a campaign once invalid addresses reach ~5%. Purchased or scraped
lists, spoofed sender data and link cloaking are prohibited.
