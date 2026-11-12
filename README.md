# Open Apple Cache in Docker

Build and run [Mau2rice0/Open-Apple-Cache](https://github.com/Mau2rice0/Open-Apple-Cache)
on a Linux Docker host. Includes a pinned multi-stage build, persistent state,
an unprivileged runtime, a healthcheck and the macOS registration helper.

This distribution applies an [origin Cache-Control policy patch](patches/README.md):
origin response directives, including private/no-cache/no-store, never prevent
storage. Retention uses the configured `max_ttl_seconds` from receipt. The rule
also applies to validated reuse across signed URL changes; original response
headers and the existing authorization, cookie, transfer and resource checks
are retained. The Docker build applies the included patch before tests/build.

The upstream project is experimental. Native Apple-device discovery requires
a successful registration by the helper on a Mac. A healthy container and a
successful smoke test do not prove native discovery.

## Build and run on a Linux Docker host

Requires Linux/amd64, Docker Engine, Docker Compose v2+, a fixed LAN IPv4 address
and enough disk space for the configured cache plus its free-space reserve.
The defaults allocate 50 GiB cache and 10 GiB reserve; allow additional room.

```sh
git clone https://github.com/palbiez/open-apple-cache-docker.git
cd open-apple-cache-docker
cp .env.example .env
```

Edit `.env`: set your host's LAN `CACHE_IP`, explicit `ALLOWED_CLIENTS` CIDRs,
host ports and absolute `CONFIG_DIR`/`DATA_DIR` paths. Create those directories
before starting; for the example paths:

```sh
sudo mkdir -p /srv/open-apple-cache/config /srv/open-apple-cache/data
docker compose config --quiet
docker compose build init
docker compose up -d
docker compose ps -a
```

`init` must finish with exit code 0; `cache` should become healthy. The default
local image is `local/open-apple-cache:docker` and is not pulled from a registry.
The build runs `go test ./...`, `go vet ./...` and compiles the pinned upstream
commit with the included patch. The Go source is pinned; base images use version tags.

Both services use the same image. Runtime config, TLS, identity, accounts and
objects persist in the two bind mounts. Runtime UID/GID is 10001, its root
filesystem is read-only, and all capabilities are dropped. `init` adjusts the
mount root permissions and config but never deletes accounts or cached objects.

## First administrator and ports

Open `https://YOUR-CACHE-IP:8443/_auth/setup` (or your chosen `ADMIN_PORT`). The
initial internal certificate must be trusted locally. Read the one-time token
privately on the host:

```sh
docker compose exec cache cat /var/lib/open-apple-cache/setup-token
```

Create your own account; no default password is supplied. Keep the token,
`auth.json`, `master.key`, generated registration and private TLS keys private.
HTTP downloads use port 8080. The default Compose file publishes both ports
on `CACHE_IP`, so that address must belong to the Docker host.

## Mac registration helper and instructions

The helper sources are in [`mac-helper/`](mac-helper/), with a full German
[installation guide](mac-helper/ANLEITUNG.md). A separate
[helper ZIP](downloads/OpenAppleCache-Helper.zip) includes that guide and a neutral
example configuration. It contains no configured private registration.

For a ZIP configured from your running container, see [HELPER.md](HELPER.md):

```sh
docker compose exec -T cache python3 - \
  --cache-ip 192.168.1.50 --client-network 192.168.1.0/24 \
  < prepare_mac_helper.py > OpenAppleCache-Helper.zip
```

Transfer that private ZIP to the Mac, extract it and run `sh INSTALL.command`
in the extracted directory as the signed-in user, without sudo. Python 3 and
the Xcode Command Line Tools are required. After a few seconds:

```sh
cat "$HOME/Library/Application Support/OpenAppleCache/status.json"
```

Expect `"state": "registered"` with a fresh timestamp. The launch agent refreshes
every 3000 seconds; sleeping, signed-out or absent Macs can interrupt renewal.
There is no measured guarantee for discovery while the Mac is offline. For a
native-device test, disable the Mac's built-in Content Caching if enabled, wait
several minutes and request the same eligible public download on two devices.

## Smoke test and connection refused

Squid is optional; this deployment does not require a forward proxy. When
discontinuing a proxy, withdraw its DHCP option 252 offers and disable explicit
proxy/PAC settings on clients. DHCP withdrawal does not clear an explicitly
configured PAC URL. If a proxy is retained, the optional selective Apple bypass
in [APPLE-PROXY.md](APPLE-PROXY.md) includes a reusable
[PAC helper](examples/apple-direct.js).

From inside the cache container, use its own HTTP listener:

```sh
docker compose exec -T cache python3 /opt/open-apple-cache/scripts/smoke.py \
  --cache http://127.0.0.1:8080
```

Expect `passed: true`, first `MISS`, then `HIT`, and a correct byte range. The
test downloads a small public Apple file and does not require a Mac or dashboard
login. From a LAN machine use `http://YOUR-CACHE-IP:8080` and a copy of the
upstream smoke script. A dashboard HTTPS port is not a smoke-test target.

When using an external gateway, its LAN address and dashboard port may be
unreachable from the cache container by design. `127.0.0.1:8080` remains the
correct internal test target. See [VERIFICATION.md](VERIFICATION.md) for checks
and limits.

## Operations

```sh
docker compose logs --tail=100 init cache
docker compose restart cache
docker stats --no-stream
docker compose down
```

Stopping retains the bind-mounted state. Back up configuration, TLS and the
metadata in the data directory securely; restore `auth.json` and `master.key`
together. Cached payloads are under `objects/` and can be downloaded again.
Do not publish metadata backups or generated runtime files.

After editing `.env`, run `docker compose up -d --force-recreate init cache`.
Init regenerates app config and renews its internal certificate when the IP
changes or fewer than 30 days remain. There is no certificate renewal scheduler
in this integration. Dashboard certificate jobs and the upstream systemd updater
are not installed; use the documented Compose build/recreate workflow.

For a published image, set your own `IMAGE_REPOSITORY`/`IMAGE_TAG`, build, log in
to that registry and push with `docker compose push init`. On the destination
use the same repository/tag and `IMAGE_PULL_POLICY=always`. Source changes to
the helper integration do not update an existing published image automatically.

## Upgrade to the origin-header policy

The policy is built into the Go binary. Pulling this source or reloading Nginx
alone does not update an already running container. Before upgrading, privately
back up `.env`, configuration/TLS and persistent metadata. Keep the old image.
Use a **new** `IMAGE_TAG` in `.env`, with `IMAGE_PULL_POLICY=never` for a local
build, then run:

```sh
git pull --ff-only
docker compose config --quiet
docker compose build init
docker compose up -d --no-build --pull never cache
docker compose ps -a
docker compose logs --tail=30 cache
```

The startup JSON log must contain `"msg":"local cache policy"` and
`"origin_cache_control":"ignored"`. The image label
`io.github.palbiez.patchset=ignore-origin-cache-control-v1` also identifies the
patch. With the generated default configuration, local retention is 86400
seconds (24 hours). The patch needs no opt-in flag or extension allowlist.

An eligible first GET is stored as `MISS`; repeating it produces `HIT`, even
when its origin response says `Cache-Control: private`, `no-cache` or `no-store`.
Those original response headers still reach the client. Client request
`no-store` and the other checks listed in [patches/README.md](patches/README.md)
continue to apply. Signed URL reuse still validates a strong ETag and object
size before serving an existing package under a new URL.

To roll back the running service, restore the saved `.env` that selects the
old image, then run `docker compose up -d --no-build --pull never cache`.
Retain the same config/data mounts; do not remove volumes or reset the helper.
The patch does not change the on-disk object format or registration identity.

## Optional OMR/router gateway integration

`compose.router.yaml`, `.env.router.example`, `configure_gateway.py`,
`gateway.apple-cache.conf`, `compose.router-build.yaml` and `router/` preserve
the separate gateway deployment approach. These are environment-specific
examples, with neutral network values; read [router/README.md](router/README.md)
before adapting them. The default standalone Compose file needs none of them.

The upstream tracker keys clients by the socket peer address. Behind Nginx,
all clients appear under the gateway address even when X-Forwarded-For is set.
Do not interpret that count as an inventory of Apple devices. The direct-port
standalone setup avoids this extra HTTP proxy. The integration does not change
upstream trust or authentication behavior.

See [NOTICE.md](NOTICE.md) for source provenance and upstream licensing.
