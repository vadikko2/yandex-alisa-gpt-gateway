---
name: timeweb-s3
description: Manage Timeweb Cloud S3 object storage — create buckets, inspect
  usage, manage S3 IAM sub-users and rotate access keys, attach custom domains,
  migrate data from external S3-compatible storage, and work with objects via the
  S3 API (endpoint s3.twcstorage.ru). Use when the user says "создай бакет",
  "с3 хранилище", "дай ключи от бакета", "привяжи домен к бакету", "перенеси
  файлы с другого S3", "presigned ссылка", or debugs aws-cli/rclone/s3cmd
  against Timeweb Cloud. Bucket presets and prices must come from the live MCP
  catalog, never from memory.
---

# Timeweb Cloud S3 Object Storage

## How to act

Bucket-level management goes through the Timeweb Cloud MCP (`timewebCloud`):
`search_tools` → `get_tool_definition` → `execute_tool`; `[WRITE]` uses the
two-step `confirm_token` flow (300 s TTL). **Object-level work (upload,
download, CORS, lifecycle, policies) is NOT in the MCP** — use the S3 API
directly (aws cli / rclone / s3cmd) with endpoint `https://s3.twcstorage.ru`,
region `ru-1`. Client config gotchas: references/api-and-clients.md.

## Tool map (namespace `buckets`)

Read:
- `list_buckets` — buckets (capped at 50): **actual** name, status, size,
  location, public flag. Two traps here:
  - the service usually prepends an account prefix, so a bucket requested as
    `backups` really exists as `<account-hash>-backups`. **The name in every S3
    API command must be the one from `list_buckets`/`get_bucket`, never the one
    the user asked for** — otherwise every command returns NoSuchBucket;
  - `size_gb` and `used_gb` are **not gigabytes despite the names** — they come
    in kilobytes (a 250 GB bucket reports `size_gb: 262144000`). Divide by
    1048576 before telling the user anything, or say nothing about volume.
- `get_bucket` — details incl. object count; access_key masked, secret NEVER returned
- `list_s3_users` — IAM sub-users with per-bucket permissions
- `list_bucket_subdomains` — custom domains with SSL status
- `get_bucket_transfer_status` — migration progress
- Presets/prices: `get_cloud_service_catalog(service_type="s3")` (namespace
  `catalog`). The `price` field is **rubles per month** (billing itself is
  hourly) and pay-as-you-go presets carry `price_per_gb_overage` — always say
  the unit and the period, not a bare number

Write:
- `create_bucket` `[BILLABLE]` — name + preset_id from the catalog; default
  type is private
- `update_bucket` — description, `preset_id` (**changes what the bucket
  costs**; a preset smaller than the stored data is rejected),
  `bucket_type` (`public` exposes every object to anyone with the URL — only
  on an explicit ask), `is_allow_auto_upgrade` (billable auto-growth),
  `max_size_mb` (multiple of 1024; `null` removes the cap). Renaming a bucket
  is impossible at all; static-website config stays in the panel
- `reset_s3_user_keys` — rotates keys of a sub-user; **new secret_key is
  returned ONCE — hand it to the user immediately, never log it.** Rotation
  instantly breaks everything using the old keys — warn first
- `add_bucket_subdomain` — attach custom domain(s); **the CNAME record must
  already point to the bucket host BEFORE calling**
- `generate_bucket_certificate` — force-retry the Let's Encrypt issuance for a
  subdomain. Normally NOT needed: certs are issued automatically on attach and
  a scheduled job retries failures. Only for a subdomain stuck without
  `cert_released`; a 400 means DNS hasn't propagated — wait, don't hammer
  (retries burn provider rate limits). Success = request accepted, issuance is
  async — re-check `list_bucket_subdomains`
- `transfer_bucket` — migrate objects from any external S3-compatible
  storage; destination bucket must exist; poll `get_bucket_transfer_status`

## Decision guide

| User intent | Do this |
|---|---|
| "Создай бакет" | Catalog for presets/prices → confirm cost → `create_bucket` → **`get_bucket` to read the real, prefixed name** and hand that one to the user. Name rules: lowercase latin, digits, hyphens, 3–63 chars; a deleted name is never reusable. The **storage class is chosen once and cannot be switched later** — pick it with the user, don't default silently |
| "Дай доступ приложению / ключи" | `list_s3_users` → the access/secret pair is issued in the panel (bucket settings in the S3 section); the secret is never returned by the API, so the user copies it there. Rotation via `reset_s3_user_keys` (warn: old keys die instantly) |
| "Привяжи свой домен" | Check CNAME → `s3.twcstorage.ru` exists (3rd-level domain or deeper) → `add_bucket_subdomain`; free Let's Encrypt, ~15–20 min to activate; Cloudflare proxying must be OFF |
| "Перенеси данные с другого S3 / бакета" | `create_bucket` if needed → `transfer_bucket` → poll status; for live data top up with rclone afterwards |
| "Смени тариф / сделай бакет публичным" | `update_bucket` — quote the new price first; a preset smaller than the stored data is rejected. `bucket_type: "public"` only when the user asked for public access in so many words |
| "Сертификат на домене бакета не выпускается" | `list_bucket_subdomains` for `cert_released` → check the CNAME → `generate_bucket_certificate` once; issuance is async, don't retry in a loop |
| "Залей/скачай файлы, настрой CORS/lifecycle" | S3 API via shell — every aws-cli command needs `--endpoint-url https://s3.twcstorage.ru` (see reference) |
| "Дай временную ссылку на файл" | Presigned URL via CLI/SDK (max 7 days); panel gives fixed 60 min, private buckets only; custom domains do NOT work with presigned |
| "Сделай сайт из бакета" | Static hosting exists: `bucket.website.twcstorage.ru`, bucket must be public, no custom domain/SSL on the website endpoint |

## Not available through MCP

Bucket deletion and renaming, creating sub-users, static-website configuration,
CORS/lifecycle/versioning/Object Lock toggles — panel or S3 API. Object
operations — S3 API only. When `search_tools` finds nothing for these, don't
improvise with "similar" tools.

## Billing safety

`create_bucket` charges immediately per preset — state the live price first.
`update_bucket` with a new `preset_id` changes the recurring cost (a preset
smaller than the stored data is rejected by the backend), and
`is_allow_auto_upgrade` lets the bucket grow into a bigger preset on its own —
both deserve an explicit price warning. Storage bills hourly. Traffic has a
free monthly quota, overage is paid — and unfinished multipart uploads keep
consuming billable space silently (reference explains cleanup).

## Troubleshooting

| Symptom | Cause | Action |
|---|---|---|
| aws cli says NoSuchBucket / wrong region | Missing `--endpoint-url` on THIS command (needed on every one) or region ≠ ru-1 | references/api-and-clients.md has per-tool configs |
| 403 on all downloads since some date | User-set traffic limit reached — access auto-blocked until the 1st of the month | Check traffic settings in the panel |
| Bucket suddenly read-only | Volume limit reached with autoscaling off / volume cap set | `update_bucket`: bigger `preset_id`, raise/clear `max_size_mb`, or `is_allow_auto_upgrade: true` — with the price named |
| aws cli says NoSuchBucket on a name that "exists" | The real name carries an account prefix | `list_buckets` and use the exact name from there |
| Reported bucket size looks absurd (millions of "GB") | `size_gb`/`used_gb` arrive in kilobytes | Divide by 1048576 |
| "Бакет занимает больше, чем в нём файлов" | Unfinished multipart sessions and/or old versions (versioning) count as volume | Abort multipart sessions, add lifecycle cleanup rule — see reference |
| Presigned link 403 | Expired (panel: 60 min; CLI: ≤7 days) or generated with Content-Type for PUT | Regenerate correctly |
| Custom domain not serving | CNAME missing/Cloudflare proxy on, or <15–20 min since attach | Verify DNS, wait, re-check `list_bucket_subdomains` SSL status |

## Anti-patterns (NEVER)

- NEVER print a secret_key anywhere except directly to the user once.
- NEVER rotate keys without warning that current integrations break instantly.
- NEVER quote bucket prices/presets from memory — catalog only.
- NEVER enable versioning or Object Lock casually: versioning cannot be
  disabled (only suspended) and billed versions accumulate; Object Lock is
  permanent once on.
- NEVER flip a bucket to `public` without the user asking for public access in
  so many words — it exposes every object to anyone with the URL.
- NEVER change a bucket preset without naming the new price; the docs' claim
  that tariffs only grow is superseded by the tool — it accepts any preset the
  stored data fits into.

Deep dives: [references/api-and-clients.md](references/api-and-clients.md) —
endpoint, signatures, aws-cli/rclone/s3cmd/s3fs configs, presigned, multipart;
[references/buckets-billing-features.md](references/buckets-billing-features.md) —
storage classes, autoscaling, traffic quotas, domains/SSL, versioning,
lifecycle, Object Lock, static hosting, deletion semantics.
