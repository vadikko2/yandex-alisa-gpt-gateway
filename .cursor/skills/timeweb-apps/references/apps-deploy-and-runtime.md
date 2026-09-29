# App Platform: Types, Deploys, Runtime Rules

Snapshot of the public docs (timeweb.cloud/docs/apps/*), not live truth: if a
deploy log or the panel contradicts this file, they win.

## Four ways to deploy, two architectures

Deploy sources: a repository with auto-build (backend or frontend), a
Dockerfile, Docker Compose, or a **public** Docker Hub image.

Architecturally these split in two:
- **Backend / Docker** → a container on a dedicated cloud server; has resource
  configuration, statistics, SSH/console in the panel.
- **Frontend / static** → files in a directory behind nginx; no container, no
  resource dashboard, scaling handled by the platform. SSR is supported only for
  Next.js and Nuxt (and only those frontends get a server configuration).

## Rules that break deploys most often

1. The app must listen on **0.0.0.0**, not 127.0.0.1, or the platform's proxy
   cannot reach it. (Practical rule from how the platform works — the docs do
   not state it explicitly, so present it as a likely cause, not as policy.)
   There is no documented `PORT` variable; the port comes from the start command
   or `EXPOSE` (see the Dockerfile page for the 8080 default).
2. In a Dockerfile, **`EXPOSE` is effectively required** — without it the
   platform assumes **8080**. Externally the app is served on 443 (80 open too).
3. If the code is not in the repository root, the "project directory" parameter
   changes both the working directory and where dependencies install.
4. For frontend, "project directory" and "build directory" **add up** — the
   final path is project + build. A classic mistake.
5. Node/Express: a build script must exist in `package.json.scripts`, otherwise
   the build fails on the build instruction.
6. Django: without `ALLOWED_HOSTS` you get DisallowedHost; the docs' default
   start command serves static only with `DEBUG=True`, which is not a
   production setup — flag it rather than copying it.

## VCS deploys vs "repository by link"

Connecting a GitHub/GitLab/Bitbucket **account** enables **auto-deploy on
push** plus rollback to a commit. Two ways to connect: the OAuth button
(panel-only, browser redirect) or a personal access token via
`add_vcs_provider` (MCP — GitHub classic PAT scope `repo`, GitLab scope `api`,
Bitbucket needs the workspace login too). Panel/API authorizations overwrite
each other. A repository added **by link** (any self-hosted Git, Gitea,
GitFlic, … — `add_vcs_provider` with `provider_type: "git"` and a URL)
supports **manual deploys only** — no auto-deploy, one provider entry per
repository. **Git LFS is not supported.** Disconnecting a repository disables
deploys for all apps built from it.

## Docker Compose specifics

Host ports **80 and 443 are reserved**; use 8080/9000 and similar. Only the
first service gets auto-proxied to the main domain. A long list of directives is
forbidden — including `volumes`, `privileged`, `devices`, `network_mode: host`,
`extra_hosts`, `sysctls`, and `external`/`name` in volumes and networks. Stands
and panel-configured health checks are **not available** for Compose.

## Environment variables

Up to **100 per app**. Two kinds: local (deleted with the app) and global
(reusable across apps). A `.env` file can be uploaded. Editing them is
panel-only. There is no separate secrets product — secrets are ordinary
variables; their **values come back masked as `***` in API/MCP responses**
(`get_app`), so you cannot read a secret back for the user, only replace it in
the panel. The docs do not say whether changing a variable needs a redeploy;
changing settings or a domain does trigger one.

## Health check

GET on the given path over localhost; any **2xx** counts. During a deploy: up to
3 attempts, one success activates the app, but **3 consecutive failures or 180
seconds without success roll the deploy back**; afterwards probes run every
40 seconds. In runtime: one probe every 30 seconds, **3 consecutive failures
restart the app automatically**. A `HEALTHCHECK` in the Dockerfile overrides the
panel setting. Without a health check the platform only checks that the
container started.

## Data persistence — the most costly misunderstanding

**Every deploy creates a new environment; the previous container's data is
gone.** No FTP, no mounted network filesystems, no direct disk management.
Anything that must survive a deploy goes to S3 or an external database. State
this before a user builds an upload feature on local disk.

## Tariffs, stands, and frontend request billing

- App tariff changes **upward only** (justified by disk size) — an irreversible
  decision at selection time. No horizontal scaling/replication is documented
  for backend: one server with configurable resources.
- **Stands** (preview environments): up to 10 per app, free for backend/Docker
  but they live on the same VM and share its resources — keep headroom. Frontend
  stand requests are billed like the main app. None for Compose.
- **Frontend billing is per HTTP request**, counting static assets too, debited
  hourly, with 2 GB NVMe per app. A **request limit** stops the app (and its
  charges) when reached; if the balance is short at debit time the app also
  stops automatically.

## Domains, SSL, logs

A free technical domain plus a free Let's Encrypt certificate come with the app,
auto-renewed; several custom domains can be attached, and **changing a domain
triggers a redeploy**. **Installing your own or a paid certificate is not
possible.** Russian Trusted CA ("Минцифры") certificates can be enabled for
outbound HTTPS to state/bank APIs — that also triggers a redeploy, and for
Dockerfile/Compose apps the trust store must be wired up manually per runtime.
Frontend access logs are kept **24 hours** with downloads capped at 10 000
lines; retention for backend runtime and deploy logs is not documented.
