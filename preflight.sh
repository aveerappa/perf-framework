#!/bin/bash

# Pre-flight environment checks for performance tests
# Usage: ./preflight.sh <config.json>
# Exit codes: 0 all pass, 2 usage, 10 VPN, 11 AWS SSO, 12 kubectl, else validate_config.py's code

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="$1"

if [ -z "$CONFIG_FILE" ] || [ ! -f "$CONFIG_FILE" ]; then
    echo "Usage: ./preflight.sh <config.json>" >&2
    exit 2
fi

echo "🛫 Pre-flight Checks"
echo "======================================================================"
echo "Config: $CONFIG_FILE"
echo "======================================================================"

check_vpn() {
    echo ""
    echo "1️⃣  Checking Barracuda VPN..."
    local tunnel
    tunnel=$(ifconfig | awk '/^[a-z]/{i=($1 ~ /^utun/)?$1:""} /inet 10\./{if(i){print i, $2; exit}}')
    if pgrep -f "Barracuda VPN Client.app/Contents/MacOS/Barracuda VPN Client" >/dev/null && [ -n "$tunnel" ]; then
        echo "   ✅ VPN connected ($tunnel)"
        return 0
    fi
    echo "   ❌ Barracuda VPN not connected"
    echo "   → Connect Barracuda VPN Client and re-run"
    return 1
}

check_vpn || exit 10
