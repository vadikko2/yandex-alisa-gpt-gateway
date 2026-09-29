# Domains: Registration, Renewal, DNS, Transfers

Snapshot of the public docs (timeweb.cloud/docs/domains/*), not live truth:
zone terms and prices come from `list_tlds` / the panel; if a tool response
contradicts this file, the tool wins.

## Registration and zone rules

Over 350 zones; price depends on the zone (only .RU/.РФ renewal plans are
published). International zones register/renew for up to 10 years. Residency and
term rules that make a registration fail if ignored:

- `.AE` — UAE residents only; `.NYC` — New York residents; `.EU` — EU residents
  or entities with an EU presence.
- `.BY` / `.БЕЛ` — **non-residents of Belarus only**, via a partner registrar.
- `.AI` — minimum term **2 years**.
- `.KZ` — the server must physically sit in Kazakhstan.

**Premium domains**: the registry sets the price and does not publish it in
advance, so the panel figure can be wrong and a normal-price attempt fails —
support handles it; money paid can be refunded or moved to other services. A
name can be premium in `.ru` and ordinary in `.com`.

Registration itself is **final**: cancellation and refunds are impossible once
the status has been sent to the registry.

## Renewal, autorenew, and what happens when it lapses

- The renewal button appears roughly **60 days** before expiry.
- After expiry there is a grace period whose **length depends on the zone**. If
  the domain was already undelegated, it comes back **3–24 hours** after payment.
- **Autorenew fires 5 calendar days before expiry**, with up to 3 card attempts
  24 hours apart; email warning 3 days before the first attempt.
- International zones follow the chain: ~30 days grace → ~30 days redemption
  (recoverable, usually pricier) → 5 days → the name is free for anyone.
  **The equivalent exact timings for .RU/.РФ are not documented** — don't invent
  them.
- .RU/.РФ renewal plans differ in extras: a deferred-payment option and a
  five-year fixed renewal price on higher plans; switching plans is free.

## Delegation and nameservers

Timeweb's default NS are `ns1.timeweb.ru`, `ns2.timeweb.ru`,
`ns3.timeweb.org`, `ns4.timeweb.org`. Delegating to new NS takes **3–24 hours**
and the domain can be unreachable during it; an A-record change usually applies
within 3 hours, occasionally 24. NS can only be edited for domains registered
with Timeweb. **Subdomain NS always inherit from the parent domain.**

The ordering rule that prevents outages: add the domain to the panel and
recreate all DNS records there **first**, only then switch NS at the registrar.
While the domain is on third-party NS, records in the Timeweb panel are inert.

## DNS records

Supported: NS, A, AAAA, MX, SRV, TXT, SPF, DKIM, CNAME. Specifics:

- **CNAME only for subdomains**, never the apex, and **no trailing dot** in the
  value.
- Default **TTL 600 s**; docs advise not changing it without reason.
- TXT/SPF/DKIM **for a subdomain are created in the parent domain's zone**.
- More than one SPF record is discouraged.
- No documented limit on the number of records or subdomains.
- Zone import accepts `.zone` files but only A, AAAA, CNAME, MX, TXT, SRV are
  imported — **other types are silently skipped**, and behaviour on conflicts
  with existing records is undocumented.

## Transfers and their locks

Registrar transfer is panel/support work, but the constraints decide whether it
is even possible:

- **AuthInfo code lives 20 calendar days** (issuing can take up to 3 business
  days at the losing registrar).
- .RU/.РФ inbound is free, keeps the site and DNS working, and takes **5–7
  days**. Blockers: `serverTransferProhibited` / `clientTransferProhibited` /
  `changeProhibited`, expiry **sooner than 7 days**, or **less than 30 days**
  since the last administrator or registrar change.
- **The Reg.ru trap**: if the domain uses free `ns1.reg.ru`/`ns2.reg.ru`, after
  the transfer it is **undelegated and stops working** — move it to Timeweb NS
  first, then change registrar.
- `.COM/.ORG/.NET` transfers need the registry secret key, take 5–7 days and
  **automatically renew the domain for a year, which must be paid**.
- Any administrator change starts a **30-day lock** on both registrar change and
  a repeat owner change. Owner change for .RU/.РФ is impossible while the
  registration has lapsed, with court/state restrictions, or for a liquidated
  company.

## Transfer between Timeweb accounts

Subdomains, mailboxes and SSL certificates move with the domain. **Sites hosted
on the source account's servers do not.** Domains registered with Timeweb need a
confirmation code sent to the administrator's mailbox; domains from other
providers move immediately.

## Technical (free test) domains

Zones `.tw1.su`, `.tw1.ru`, `.webtm.ru`, `.twc1.net`. On them you **cannot**
change DNS, create mailboxes, or order SSL — so they are unsuitable for anything
resembling production.
