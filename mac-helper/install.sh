#!/bin/sh
set -eu

if [ "$#" -ne 1 ]; then
  echo "usage: $0 REGISTRATION_JSON" >&2
  exit 64
fi

source_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
registration_json=$1
support_dir="$HOME/Library/Application Support/OpenAppleCache"
agent_dir="$HOME/Library/LaunchAgents"
agent_plist="$agent_dir/org.openapplecache.registration.plist"
temporary_plist=$(mktemp "${TMPDIR:-/tmp}/openapplecache-plist.XXXXXX")
trap 'rm -f "$temporary_plist"' EXIT HUP INT TERM

mkdir -p "$support_dir" "$agent_dir"
chmod 700 "$support_dir"
install -m 700 "$source_dir/register_once.py" "$support_dir/register_once.py"
install -m 600 "$registration_json" "$support_dir/registration.json"
xcrun clang -Wall -Wextra -fblocks -framework Foundation \
  "$source_dir/native-registration.m" -o "$support_dir/native-registration"
chmod 700 "$support_dir/native-registration"
sed "s|__SUPPORT__|$support_dir|g" \
  "$source_dir/org.openapplecache.registration.plist" > "$temporary_plist"
plutil -lint "$temporary_plist"
install -m 600 "$temporary_plist" "$agent_plist"

launchctl bootout "gui/$(id -u)" "$agent_plist" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$agent_plist"
launchctl kickstart -k "gui/$(id -u)/org.openapplecache.registration"
echo "$support_dir"
