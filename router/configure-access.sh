#!/bin/sh
# All six gateway services: internal VLANs and client WireGuard VPN.
set -eu
cd /mnt/data/cacheserver/config
test -z "$(uci changes firewall)" || { echo 'Pending firewall changes' >&2; exit 1; }
test -z "$(uci changes network)" || { echo 'Pending network changes' >&2; exit 1; }
env_value() { sed -n "s/^$1=//p" .env | tr -d '\r'; }
address=$(env_value CACHE_IP)
cache_port=$(env_value CACHE_PORT)
admin_port=$(env_value ADMIN_PORT)
wg_network=$(env_value WIREGUARD_NETWORK)
test -n "$address" && test -n "$wg_network"
backup=/mnt/data/cacheserver/backups/all-internal-networks-20261110
test -s "$backup/firewall.before"

for zone in lan gaming vlan10 wireguard; do
    case "$zone" in
        wireguard) section=hetzner_wg_to_proxy_guis; network=$wg_network;;
        *) section=${zone}_to_proxy_guis; network=;;
    esac
    uci set "firewall.$section=rule"
    uci set "firewall.$section.name=Gateway-247-services-from-$zone"
    uci set "firewall.$section.src=$zone"
    uci set "firewall.$section.dest=lancache"
    uci set "firewall.$section.dest_ip=$address"
    uci set "firewall.$section.dest_port=$cache_port 8443 8444 8445 $admin_port 9443"
    uci set "firewall.$section.proto=tcp"
    uci set "firewall.$section.family=ipv4"
    uci set "firewall.$section.target=ACCEPT"
    uci -q delete "firewall.$section.src_ip" || true
    if [ -n "$network" ]; then uci set "firewall.$section.src_ip=$network"; fi
done
uci -q delete firewall.vpn_to_proxy_guis || true
# The consolidated gateway rules now include the two Apple-cache ports.
for section in lan_to_apple_cache gaming_to_apple_cache vlan10_to_apple_cache hetzner_wg_to_apple_cache; do
    uci -q delete "firewall.$section" || true
done

# Local service destinations take precedence over per-device Internet bypass.
# Priority 0 is deliberately before OMR's priority-1 WAN fwmark lookups.
for pair in gateway247_local:$address proxy251_local:192.168.10.251 pac252_local:192.168.10.252; do
    section=${pair%%:*}; target=${pair#*:}
    uci set "network.$section=rule"
    uci set "network.$section.dest=$target/32"
    uci set "network.$section.lookup=lan"
    uci set "network.$section.priority=0"
done
for pair in gateway247_wg_return:$address:90; do
    section=${pair%%:*}; rest=${pair#*:}; source=${rest%:*}; priority=${rest##*:}
    if ip -4 rule show | grep -q "^$priority:" && ! ip -4 rule show | grep "^$priority:" | grep -F "from $source to $wg_network lookup 10" >/dev/null; then
        echo "Priority $priority is already in use; inspect first" >&2; exit 1
    fi
    uci set "network.$section=rule"
    uci set "network.$section.src=$source/32"
    uci set "network.$section.dest=$wg_network"
    uci set "network.$section.lookup=10"
    uci set "network.$section.priority=$priority"
done

fw4 check > "$backup/access-fw4-check.log" 2>&1
uci commit firewall
uci commit network
for target in "$address" 192.168.10.251 192.168.10.252; do
    if ! ip -4 rule show | grep -F "from all to $target lookup lan" >/dev/null; then
        ip -4 rule add priority 0 to "$target/32" lookup lan
    fi
done
for pair in $address:90; do
    source=${pair%:*}; priority=${pair##*:}
    if ! ip -4 rule show | grep -F "from $source to $wg_network lookup 10" >/dev/null; then
        ip -4 rule add priority "$priority" from "$source/32" to "$wg_network" lookup 10
    fi
done
/etc/init.d/firewall reload > "$backup/access-fw4-reload.log" 2>&1
tail -1 "$backup/access-fw4-check.log"
echo 'Internal gateway access, local service routes and client-VPN return route applied'
