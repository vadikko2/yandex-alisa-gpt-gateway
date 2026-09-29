# S3 API, Clients, Presigned URLs, Multipart

Snapshot of the public docs (timeweb.cloud/docs/s3-storage/*), not live truth:
if the client's actual error contradicts this file, trust the error and
re-check the docs before advising.

## Endpoint and addressing

- Endpoint: `https://s3.twcstorage.ru`, single region **`ru-1`**.
- Both addressing styles work: path-style
  (`https://s3.twcstorage.ru/bucket/key`) and virtual-hosted
  (`https://bucket.s3.twcstorage.ru/key`).
- Signatures: AWS SigV2 and SigV4 (scope `YYYYMMDD/ru-1/s3/aws4_request`).
  Swift API is also available. Bandwidth ~1 Gbit/s.

## Ready-to-use aws cli setup

Take the bucket name from `list_buckets` (it carries an account prefix — the
name the user typed will not work).

```bash
aws configure --profile twc     # access key + secret from the panel, region ru-1

E=https://s3.twcstorage.ru
aws --profile twc --endpoint-url $E s3 ls s3://BUCKET/
aws --profile twc --endpoint-url $E s3 cp dump.tar.gz s3://BUCKET/db/
aws --profile twc --endpoint-url $E s3 sync /var/backups s3://BUCKET/backups/
aws --profile twc --endpoint-url $E s3 cp s3://BUCKET/db/dump.tar.gz .
```

To avoid repeating the flag, recent aws cli v2 honours the endpoint in the
profile (if the installed version ignores it, fall back to the flag):

```ini
[profile twc]
region = ru-1
endpoint_url = https://s3.twcstorage.ru
```

## Per-tool config gotchas

- **aws cli**: region `ru-1`; the #1 gotcha — **every single command needs
  `--endpoint-url https://s3.twcstorage.ru`**; forgetting it sends requests
  to AWS proper and yields confusing NoSuchBucket/credential errors.
- **rclone**: `type = s3`, `provider = Other`,
  `endpoint = https://s3.twcstorage.ru`; if the config wizard errors on
  region, retry leaving region empty. Recommended for large migrations.
- **s3cmd**: `host_base = host_bucket = s3.twcstorage.ru` (effectively
  path-style), `bucket_location = ru-1`, `use_https = True`.
- **s3fs**: requires `-o use_path_request_style -o
  url=https://s3.twcstorage.ru`; docs themselves advise avoiding s3fs for
  performance/reliability.
- **boto3**: `endpoint_url="https://s3.twcstorage.ru"`,
  `region_name="ru-1"`.

## Presigned URLs

- Via CLI/SDK: GET and PUT, `--expires-in` (docs default 3600 s; the hard
  ceiling of **7 days** is the AWS SigV4 protocol limit, not a documented
  Timeweb figure).
- Via the panel: fixed **60 minutes**, private buckets only.
- Do NOT set Content-Type when generating a PUT presigned URL — uploads will
  403 otherwise.
- **Presigned URLs do not work with custom domains** — only the native
  endpoint.
- Panel "public link" on a private object lives 1 hour.

## Multipart uploads

- Part size: min 5 MB, max 5 GB. s3cmd switches to multipart automatically
  above ~15 MB.
- **Unfinished multipart sessions silently consume billable space.** Cleanup:
  panel section "Мультипарт-сессии" (complete or abort), `s3cmd abortmp`, or
  a lifecycle rule that aborts incomplete uploads — recommend the lifecycle
  rule as the permanent fix.

## What the S3 API covers here (vs MCP)

Buckets List/Create/Delete, ACL, Versioning, Lifecycle, Tagging, Policy;
objects PUT/GET/DELETE/Copy/HEAD, tagging, ACL; multipart — all via standard
AWS-compatible calls. Bucket policies: AWS-style JSON
(`aws s3api put-bucket-policy`), conditions `aws:SecureTransport`,
`aws:SourceIp`. Custom IAM user roles: JSON via `aws iam put-user-policy`,
actions down to GetObject/PutObject per prefix.
