#!/bin/bash

# Pre-flight environment checks for performance tests
# Usage: ./preflight.sh <config.json>
# Exit codes: 0 all pass, 2 usage, 10 VPN, 11 AWS SSO, 12 kubectl, else validate_config.py's code

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="$1"

# Find AWS env file in standard locations if not explicitly set
if [ -z "$AWS_ENV_FILE" ]; then
    for candidate in \
        "$HOME/.aws/aws-env.sh" \
        "$HOME/.config/aws/aws-env.sh" \
        "$HOME/Documents/Work/workspace/aws-sso-setup/aws-env.sh"; do
        if [ -f "$candidate" ]; then
            AWS_ENV_FILE="$candidate"
            break
        fi
    done
fi

if [ -z "$CONFIG_FILE" ] || [ ! -f "$CONFIG_FILE" ]; then
    echo "Usage: ./preflight.sh <config.json>" >&2
    exit 2
fi

NAMESPACE=$(jq -r '.service_name // empty' "$CONFIG_FILE" 2>/dev/null | tr '_' '-')
if [ -z "$NAMESPACE" ]; then
    echo "Cannot read service_name from $CONFIG_FILE (is jq installed and the config valid?)" >&2
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

check_aws_sso() {
    echo ""
    echo "2️⃣  Checking AWS QA SSO session..."
    if [ ! -f "$AWS_ENV_FILE" ]; then
        echo "   ❌ aws-env.sh not found: $AWS_ENV_FILE"
        return 1
    fi
    # aws-qa-login is a zsh function; it may open a browser and block until login completes
    if zsh -c 'source "$1" && aws-qa-login' _ "$AWS_ENV_FILE" 2>&1 | sed 's/^/   /'; [ "${PIPESTATUS[0]}" -ne 0 ]; then
        echo "   ❌ AWS qa SSO login failed"
        return 1
    fi
    echo "   ✅ AWS qa profile active"
    return 0
}

check_kubectl() {
    local ns="$1" output rc count
    echo ""
    echo "3️⃣  Checking kubectl access to namespace $ns..."
    output=$(kubectl get pods -n "$ns" --no-headers --request-timeout=15s 2>&1)
    rc=$?
    count=$(printf '%s\n' "$output" | grep -c .)
    if [ "$rc" -ne 0 ] || [ "$count" -eq 0 ]; then
        echo "   ❌ Cannot list pods in $ns"
        printf '%s\n' "$output" | sed 's/^/   /'
        return 1
    fi
    echo "   ✅ $count pod(s) found in $ns"
    return 0
}

check_vpn || exit 10
check_aws_sso || exit 11
check_kubectl "$NAMESPACE" || exit 12

echo ""
echo "4️⃣  Validating configuration..."
python "$SCRIPT_DIR/validate_config.py" "$CONFIG_FILE"
rc=$?
if [ "$rc" -ne 0 ]; then
    exit "$rc"
fi

echo ""
echo "======================================================================"
echo "✅ PRE-FLIGHT PASSED"
echo "======================================================================"
exit 0
