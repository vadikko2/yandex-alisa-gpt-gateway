# Buckets: Classes, Billing, Domains, Versioning, Hosting

Snapshot of the public docs (timeweb.cloud/docs/s3-storage/*), not live truth:
quotas and rates change — take live prices from the catalog and check current
limits in the panel. If a tool response contradicts this file, the tool wins.

## Storage classes

- **Premium** (triple replication), **Standard**, **Cold**.
- Cold: always starts at 1 GB with **mandatory autoscaling**, pay-as-you-go —
  in the catalog it shows as a low `price` plus `price_per_gb_overage`.
- Only ONE standard 1 GB-tariff bucket per account.
- **The class is fixed when the bucket is created** and tariff changes stay
  inside that class, so cold↔standard is a new bucket plus a data move. Decide
  it with the user up front.
- Before recommending Cold for backups, know the limit of what is documented:
  the docs describe the pricing model but say **nothing about retrieval fees,
  minimum storage duration or access latency**. If those matter to the user, say
  the docs don't cover it and point at support instead of guessing.

## Autoscaling and tariffs

- Optional for 1/10/100 GB standard/premium tariffs; always on for cold and
  250 GB+ tariffs.
- Without autoscaling, hitting the tariff limit **suspends the service**;
  with a user-set volume cap the bucket goes **read-only**.
- Tariff changes stay within the class. The docs say **upward only**, but the
  MCP tool `update_bucket` accepts any preset the stored data fits into and
  rejects only presets smaller than the data — trust the tool's behavior and
  the operation summary over this file. Storage bills hourly, and the catalog
  `price` is rubles per month — quote the unit and period, never a bare number.

## Traffic

- Free outgoing quota per month (per docs: 100 GB, Prime — 1000 GB), shared
  across standard+cold; overage is paid per GB (rate in docs/panel). Resets
  on the 1st at 00:00 MSK.
- A user-configured traffic limit, once reached, auto-blocks access with
  **403 until the new month** — a classic "бакет отдаёт 403 у всех" cause.
- Incoming traffic and requests are not billed (per docs).

## Custom domains and SSL

- CNAME → `s3.twcstorage.ru`; third-level domains or deeper only. Free
  Let's Encrypt with auto-renewal; activation ~15–20 min; **turn off
  Cloudflare proxying before attaching**.
- No object listing via the domain — direct file links only; presigned URLs
  don't work with custom domains.
- No CDN product in the docs — the documented pattern is Nginx proxy/cache
  (`proxy_pass https://s3.twcstorage.ru/bucket/`, Host `s3.twcstorage.ru`,
  strip `Authorization`; for private buckets a bucket policy with
  `aws:SourceIp` of the proxy).

## Versioning, lifecycle, Object Lock

- **Versioning cannot be disabled once enabled** — only suspended; every
  version is billed as volume. Old versions are restored via copy-object
  with versionId.
- Lifecycle: expiration by prefix/days, noncurrent-version expiration,
  aborting incomplete multiparts. **No class transitions** (no auto-move to
  cold).
- **Object Lock**: COMPLIANCE (nobody can delete), GOVERNANCE (bypassable
  with a special permission), Legal Hold. Enabled at creation or later —
  **cannot be turned off** and force-enables versioning. Treat as a one-way
  door.

## Static website hosting

Exists: enable in bucket settings, index/error documents (index must be at
the root), URL `bucket-name.website.twcstorage.ru`. The bucket must be
public. Custom domains and SSL are NOT supported on the website endpoint;
traffic bills as usual.

## Deletion and restore

Bucket deletion removes all files; restore is possible for 2–5 days if the
bucket existed longer than 2 days. The bucket NAME is never reusable after
deletion — relevant when someone deletes to "recreate with the same name".
