# Container Registry

Snapshot of the public docs — note they live under
timeweb.cloud/docs/k8s/container-registry, not under /docs/apps — and prices are
only on the marketing page, so take them from the catalog, not from here.

## Endpoint and authentication

Registry host: **`<registry-name>.registry.twcstorage.ru`**.

```bash
docker login <registry-name>.registry.twcstorage.ru
# username: anything (e.g. the registry name)
# password: the token issued when the registry was created
docker tag myapp:1.0 <registry-name>.registry.twcstorage.ru/<repo>/myapp:1.0
docker push <registry-name>.registry.twcstorage.ru/<repo>/myapp:1.0
```

Pull by tag or by `@sha256:<digest>`. **A non-existent repository is created
automatically on push** — no need to pre-create it.

Helm charts and OCI artifacts work too:
`helm registry login <name>.registry.twcstorage.ru -u iam` (password = the same
token), then `helm push chart.tgz oci://<name>.registry.twcstorage.ru/<repo>`;
Helm ≥ 3.8 (3.9+ recommended), or `oras` as an alternative. For inspection and
deletion there is `regctl` (`regctl repo ls`, `regctl tag ls`,
`regctl image inspect`, `regctl image rm`).

## Tokens

Prefixed `registry-`, **shown once and not recoverable**. Two scopes exist:
project-level (all registries in a project) and account-level (**all registries
on the account** — treat as highly sensitive). A compromised token is revoked by
deleting it in "API и Terraform". Never echo a token into chat or logs.

## Naming, storage, limits

Registry name: lowercase latin letters, digits, hyphens, unique, no spaces;
region chosen at creation. Billing is for the **allocated** volume, not the used
one, debited hourly. On resizing the sources disagree: the public docs say the
volume can only be increased, while `change_container_registry_tariff` states it
changes the limit and cost **up or down** — follow the tool, verify the result,
and don't promise a downgrade as a certainty. Documented capacity limits are generous (terabytes per repository, large
images, ~120 layers per image); outbound traffic and exchange with Managed
Kubernetes are not billed.

## Kubernetes integration and its gotcha

Connecting a registry from the cluster page creates a
`kubernetes.io/dockerconfigjson` secret **in the namespace you specify**, then
manifests reference it via `imagePullSecrets`. Since the secret is
namespace-scoped, **the registry only works in that namespace** — for other
namespaces repeat the connection. This is the usual cause of `ImagePullBackOff`
after "we already connected the registry".

## What the docs do not cover

Whether a registry can be public (it behaves as private, with no toggle),
garbage collection and whether deleting an image frees space, retention/auto
-cleanup policies, rate limits, a role model for access, and **using the
registry as an image source for App Platform** — App Platform documents only
public Docker Hub images, so don't promise a private-registry deploy there
without checking.
