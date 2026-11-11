#!/bin/sh
# Run as root after copying this folder to /mnt/data/cacheserver/config/.
# Updates the managed gateway block, internal service access and cache autostart.
set -eu
cd /mnt/data/cacheserver/config
backup=/mnt/data/cacheserver/backups/deployment-20261110
test -s "$backup/gateway.conf"
test -z "$(uci changes firewall)" || { echo 'Pending firewall changes; stopping' >&2; exit 1; }
docker compose config --quiet
config=$(docker compose config --format json)
image=$(printf '%s' "$config" | jq -r '.services.init.image')
address=$(printf '%s' "$config" | jq -r '.services.init.environment.CACHE_IP')
cache_port=$(sed -n 's/^CACHE_PORT=//p' .env | tr -d '\r')
admin_port=$(printf '%s' "$config" | jq -r '.services.init.environment.ADMIN_PORT')
case "$cache_port:$admin_port" in *[!0-9:]*|:*) echo 'Invalid listener ports' >&2; exit 1;; esac

# The original image is unchanged: render a host-side Nginx fragment from .env.
docker run --rm --network none --user 10001:10001 --read-only --cap-drop ALL \
    --security-opt no-new-privileges:true --memory 128m --pids-limit 32 \
    --entrypoint python3 -v /mnt/data/cacheserver/config:/workspace \
    "$image" /workspace/configure_gateway.py --env-file /workspace/.env --output /workspace/gateway.apple-cache.conf

gateway=/mnt/data/proxy-guis/config/gateway.conf
cp -p "$gateway" "$backup/gateway.before-integration.conf"
awk '
    $0 == "# BEGIN OPEN-APPLE-CACHE (managed from cachingserver/.env)" { if (inside) exit 2; inside=1; starts++; next }
    $0 == "# END OPEN-APPLE-CACHE" { if (!inside) exit 2; inside=0; ends++; next }
    !inside { print }
    END { if (inside || starts != ends) exit 2 }
' "$gateway" > "$backup/gateway.with-cache.conf"
cat gateway.apple-cache.conf >> "$backup/gateway.with-cache.conf"
# Keep the bind-mounted file's inode so the running gateway sees the new content.
cat "$backup/gateway.with-cache.conf" > "$gateway"
if ! docker exec gui-gateway nginx -t > "$backup/nginx-check.log" 2>&1; then
    cat "$backup/gateway.before-integration.conf" > "$gateway"
    cat "$backup/nginx-check.log"
    exit 1
fi
docker exec gui-gateway nginx -s reload
echo 'Existing gateway gracefully reloaded; cache listeners added'

cp router/37-apple-cache-vpn-mss.nft /etc/nftables.d/37-apple-cache-vpn-mss.nft
sh router/configure-access.sh

cp router/cacheserver-start /usr/libexec/cacheserver-start
cp router/cacheserver.init /etc/init.d/cacheserver
chmod 755 /usr/libexec/cacheserver-start /etc/init.d/cacheserver
for file in /usr/libexec/cacheserver-start /etc/init.d/cacheserver /etc/nftables.d/37-apple-cache-vpn-mss.nft; do
    if ! grep -qxF "$file" /etc/sysupgrade.conf; then
        printf '%s\n' "$file" >> /etc/sysupgrade.conf
    fi
done
/usr/libexec/cacheserver-start --check
/etc/init.d/cacheserver enable
echo 'Cache autostart enabled with mount/UUID guard and offline image reuse'
