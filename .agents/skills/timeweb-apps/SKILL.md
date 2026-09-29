---
name: timeweb-apps
description: Manage Timeweb Cloud App Platform applications and Container Registry —
  create apps (from Git or Docker Hub), connect a VCS provider by token, inspect
  apps and their deploys, trigger or stop a deploy, pause/resume/reboot an
  app, read build and runtime logs and resource statistics, browse connected VCS
  providers, repositories, branches and commits, read presets and build/run
  defaults, and manage container registries. Use when the user says "создай
  приложение", "задеплой приложение", "подключи гитхаб", "приложение не
  собирается", "покажи логи деплоя", "перезапусти апп", "запушь образ в реестр",
  "docker login в тимвеб". Do NOT use for applications the user runs himself on
  a VDS or in Kubernetes. Tariffs and registry prices come from the live
  catalog, not memory.
---

# Timeweb Cloud App Platform & Container Registry

## How to act

Through the Timeweb Cloud MCP (`timewebCloud`): `search_tools` →
`get_tool_definition` → `execute_tool`. `[WRITE]` needs the two-step
`confirm_token` flow (300 s TTL); `[BILLABLE]` charges immediately.

## Tool map

Apps (namespace `apps`):
- `list_apps`, `get_app` — apps with status (`active` / `paused` / `no_paid`)
- `list_app_presets` — App Platform tariffs with prices. For BACKEND
  `price_per_month` IS the whole price; for FRONTEND it is only a small base
  fee on top of per-REQUEST billing — never present it as the full cost.
  `has_free_capacity: false` on a frontend preset means creation will be
  refused; on backend it is only a hint
- `get_app_deploy_defaults` — platform defaults (build_cmd / run_cmd /
  index_dir / env_versions) per (language, framework) pair — read BEFORE
  creating instead of guessing commands. Empty build_cmd / null run_cmd means
  "no command needed" (docker, static), not "ask the user"; next.js/nuxt are
  listed under frontend but can be created as backend SSR
- `list_app_deploys`, `get_app_deploy_logs` — deploy history and build logs
- `get_app_logs` — runtime logs; `get_app_statistics` — resource usage
- `create_app` `[WRITE]` `[BILLABLE]` — new application, charges start
  immediately and **there is no delete via MCP — the app bills until removed
  in the panel; say that BEFORE they confirm**. Three mutually exclusive
  paths: FRONTEND from Git (needs `index_dir`), BACKEND from Git (needs
  `run_cmd`), BACKEND from Docker Hub (`docker_image` + tag; `language` is
  still required). Gather real values first: `list_app_presets`
  (`available_only: true`), `get_app_deploy_defaults`, VCS tools for
  provider/repository/branch/full 40-char `commit_sha`. Gotchas that bite:
  when the stack's default command is null pass an EMPTY STRING, don't omit;
  for a backend app leave the default "new public IP" — reusing an existing
  floating IP is accepted but currently BROKEN (the app dies minutes after
  reporting success), and the IP is billed on top of the preset price; `envs`
  can ONLY be set here (editing later is panel-only) and values are never
  echoed back; `is_auto_deploy` works only when the repository has
  `is_allowed_webhook: true` (type `git` providers never do)
- `create_app_deploy` `[WRITE]` — builds and deploys a **specific commit**:
  `commit_sha` is REQUIRED and must be the full 40-character lowercase SHA
  (get it from `list_vcs_commits`, or from `get_app` to redeploy the current
  revision). A new build replaces the running revision, so a failing or slow
  build disrupts production — say that before confirming
- `stop_app_deploy` `[WRITE]` — aborts a running deploy
- `app_action` `[WRITE]` — `resume` / `pause` / `reboot`. Pause stops serving
  the public URL; reboot drops existing connections. Asynchronous — poll `get_app`
- `update_app_meta` `[WRITE]` — name, comment, **deploy branch, build_cmd,
  run_cmd, is_auto_deploy**. Does NOT touch env vars, framework, preset or the
  repository binding

VCS (namespace `apps`):
- `list_vcs_providers`, `list_vcs_repositories`, `list_vcs_branches`,
  `list_vcs_commits` — use these to pick a commit before deploying
- `add_vcs_provider` `[WRITE]` — connect GitHub/GitLab/Bitbucket by a personal
  access token, or any Git host by URL (+login/password for private ones).
  Free. The OAuth "connect with GitHub" button cannot be done here — this is
  the token-based alternative. Ask the user for the token, never invent it,
  never echo or store it. Token rights: GitHub classic PAT scope `repo`;
  fine-grained — Contents+Metadata read, Webhooks read&write; GitLab scope
  `api`. On success the response may come WITHOUT a body — then read the id
  from `list_vcs_providers`, do NOT retry (a repeat fails with
  `provider_already_exist_exception`). Rate-limited — never call in a loop.
  Type `git` providers: one entry per repository, webhooks never allowed →
  auto-deploy impossible, only manual `create_app_deploy`

Container Registry (namespace `container_registry`):
- `list_container_registries`, `get_container_registry`,
  `list_container_registry_repositories`
- `create_container_registry` `[WRITE]` `[BILLABLE]`
- `change_container_registry_tariff` `[WRITE]` `[BILLABLE]` — switches to
  another preset, changing both the storage limit and the recurring cost
  **up OR down** (the public docs claim increase-only — the tool allows both, so
  trust the tool but verify the outcome). Pick the preset from
  `get_cloud_service_catalog(service_type="container_registry")`
- `update_container_registry_meta` `[WRITE]`

## Decision guide

| User intent | Do this |
|---|---|
| "Задеплой / обнови приложение" | `list_vcs_commits` → take the FULL 40-char sha → `create_app_deploy` → watch `list_app_deploys` and `get_app_deploy_logs`. To redeploy what is running, reuse the sha from `get_app` |
| "Смени ветку / команду сборки" | `update_app_meta` (branch / build_cmd / run_cmd / is_auto_deploy) — no need for the panel |
| "Сборка падает" | `get_app_deploy_logs` first; the frequent causes are in references/apps-deploy-and-runtime.md (0.0.0.0, EXPOSE, build directory, missing build script) |
| "Приложение запустилось, но 502/недоступно" | App must listen on **0.0.0.0**, not 127.0.0.1; check health-check path semantics in the reference |
| "Останови, чтобы не платить" | `app_action` pause stops serving traffic, but **docs do not say billing stops for backend apps** — do not promise savings; for frontend apps the documented lever is a request limit |
| "Поменяй переменные окружения" | Not exposed via MCP — panel only (and note the 100-variable cap, no separate secrets mechanism). New env vars CAN be set at `create_app` time — plan them there |
| "Создай приложение" | `list_vcs_providers`/`list_vcs_repositories`/`list_vcs_commits` (or Docker Hub image) → `get_app_deploy_defaults` for the language/framework pair → `list_app_presets(available_only: true)` → quote the price (frontend: base + per-request!) → `create_app` → watch `get_app` / `get_app_deploy_logs` |
| "Удали приложение" | Not exposed — panel only; it bills until then |
| "Подключи GitHub" | `add_vcs_provider` with a personal access token from the user (`repo` scope). The OAuth button flow stays panel-only — offer the token path first |
| "no_free_node при создании" | The preset has no capacity OR is not offered for this account/location — pick a preset in another location, don't retry the same one |
| "Нужен свой реестр образов" | `create_container_registry` (confirm price) → registry endpoint and `docker login` details in references/container-registry.md |
| "Добавь / уменьши место в реестре" | `change_container_registry_tariff` — the tool accepts both directions and changes the monthly cost; quote the new price first |

## Not available through MCP — send to the panel

Deleting applications and VCS providers, the OAuth flow for connecting a VCS
account (the token path IS available — `add_vcs_provider`), editing environment
variables of an existing app (setting them at `create_app` works), domains and
SSL, stands (preview environments), health check configuration of an existing
app, deleting a registry or its images. Two of these are worth a warning when
they come up:

- **Disconnecting a repository kills every deploy** (manual and automatic) of
  every app created from it.
- **An app's private network is fixed at deploy time and cannot be changed
  afterwards** — decide it before the first deploy.

## Billing safety

`create_app`, `create_container_registry` and `change_container_registry_tariff`
charge immediately; none of the created resources can be deleted through the
MCP, so they bill until the user removes them in the panel — say so before
confirming. For apps: BACKEND preset price is the full price, but a backend app
also needs a public IP billed separately on top; FRONTEND apps are billed
**per HTTP request** including static assets on top of a small base fee —
never quote `price_per_month` as their full cost, and mention the request
limit lever. With a custom `configuration` the confirmation summary has no
total — the API doesn't return one; do not compute or guess it. Registry
storage is billed for the **allocated** volume (not what is used). Quote live
prices (`list_app_presets`, `get_cloud_service_catalog`) before confirming.

## Troubleshooting

| Symptom | Cause | Action |
|---|---|---|
| Deploy rolled back automatically | Health check failed 3× or 180 s without success | `get_app_deploy_logs`; reference explains the exact thresholds |
| App restarts by itself in runtime | Runtime health check: 3 consecutive failures → automatic restart | Fix the endpoint or the path |
| Health-check setting in panel ignored | A `HEALTHCHECK` in the Dockerfile takes priority; Compose apps have no panel health check | Reference |
| Uploaded files vanished after a deploy | **Every deploy is a fresh environment** — container data is not persisted | Move files to S3 or an external DB; this is by design |
| Docker Compose app won't start on port 80/443 | Host ports 80 and 443 are reserved for the web server | Use 8080/9000 etc.; only the first service is auto-proxied |
| Image pulled from Docker Hub is stale | No auto-update on a new image | Redeploy manually |
| `docker push` fails auth | Login expects the registry token as the password, any username | references/container-registry.md |
| Registry secret works in one k8s namespace only | The generated secret is namespace-scoped | Connect the registry per namespace |

## Anti-patterns (NEVER)

- NEVER promise that pausing a backend app stops charges — the docs don't say so.
- NEVER promise a smaller App Platform tariff: it only grows (registry storage
  is different — that tool does accept a smaller preset).
- NEVER call `create_app_deploy` with a short sha — it requires the full 40
  characters, and never deploy an unrelated commit to "just redeploy".
- NEVER suggest storing user uploads on the app's filesystem.
- NEVER offer to install a custom or paid SSL certificate on App Platform — only
  the built-in free certificate is supported.
- NEVER print registry tokens or VCS personal access tokens into the chat or
  logs; ask the user for a token, use it once, never repeat it back.
- NEVER retry `add_vcs_provider` after a bodyless success — read the id from
  `list_vcs_providers` instead.
- NEVER pass an existing floating IP to `create_app` — the reuse path is
  currently broken on the platform (billed app dies minutes later); leave the
  default "new IP".
- NEVER quote tariffs or registry prices from memory.

Deep dives:
[references/apps-deploy-and-runtime.md](references/apps-deploy-and-runtime.md) —
app types, VCS vs link deploys, Dockerfile/Compose rules, variables, health
check, stands, logs, frontend request billing;
[references/container-registry.md](references/container-registry.md) —
endpoint, docker/helm/regctl auth, tokens, limits, k8s integration.
