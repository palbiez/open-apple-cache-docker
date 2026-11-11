# Optional OMR gateway deployment examples

These files document a deployment behind an existing `gui-gateway` Nginx
container and an external Docker backend network. The default `compose.yaml`
uses direct host ports and does not run any router script.

For this alternative, use `.env.router.example` as the basis for a private
`.env` and `compose.router.yaml` as your deployment `compose.yaml`. Set all IPs,
allowed networks, gateway/backend addresses, paths, image and volume UUID to
your own values. The neutral addresses in these examples are not an inventory.

The `router/` scripts retain assumptions about the original OMR layout:
`/mnt/data/cacheserver/config`, `/mnt/data/proxy-guis/config/gateway.conf`,
UCI zones, policy-routing table names, tun0, a separate ext4 data mount and
pre-existing backups under dated paths. `cacheserver-start` intentionally
contains `REPLACE_WITH_DATA_VOLUME_UUID` so it refuses an unadapted mount.
Inspect and adapt every assumption before installing. `configure-access.sh`
changes firewall and routing and requires a deliberate administrator action.
It is not called by the normal Docker build/start workflow.

Use `python3 configure_gateway.py --env-file .env --output gateway.apple-cache.conf`
to render the extra Nginx block for review. Merge only its marked block into
your gateway, validate Nginx, then reload it. Preserve the gateway's existing
TLS directives and unrelated services. The fragment is not a standalone full
Nginx configuration. Download port 8080 and admin port 8446 are example listeners.

The application sees proxied requests as the gateway IP. ACLs at the gateway
check the real client addresses; include only its specific backend /32 in the
application allowlist. Client count in the application consequently merges
those clients. The application does not use X-Forwarded-For for client tracking.

`37-apple-cache-vpn-mss.nft` is a narrowly scoped MSS workaround for a measured
VPN path issue. It is not a general requirement for Apple caching. Preserve
existing firewall/routing and keep a tested rollback when adapting these files.
