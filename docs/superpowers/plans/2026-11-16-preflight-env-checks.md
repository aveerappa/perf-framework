# Pre-flight Environment Checks Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a foreground `preflight.sh` that verifies VPN, AWS QA SSO (auto-login), and kubectl pod access before `validate_config.py`, wire it into `run_test.sh`, and make the `/perf-execute` skill ask for the full load profile.

**Architecture:** One new bash script at repo root with one function per check, each with a distinct exit code so callers (and tests) can tell which precondition failed. Tests are pytest + `subprocess`, isolating the script with PATH shims (`pgrep`, `ifconfig`, `kubectl`, `python`) and an `AWS_ENV_FILE` override pointing at a fake `aws-qa-login`. `run_test.sh` swaps its step 1 to call the script. The skill document gains a load-profile prompt and a foreground preflight step.

**Tech Stack:** bash, zsh (to source the user's `aws-env.sh`), jq, kubectl, pytest (`.venv/bin/pytest`).

**Spec:** `docs/superpowers/specs/2026-11-16-preflight-env-checks-design.md`

## Global Constraints

- `aws-qa-login` is a **zsh function** in `~/Documents/Work/workspace/aws-sso-setup/aws-env.sh`; invoke it as `zsh -c 'source "$AWS_ENV_FILE" && aws-qa-login'`, never as a bare command.
- `timeout(1)` does not exist on this Mac; use `kubectl --request-timeout=15s`.
- Namespace is derived exactly as `run_test.sh` does: `jq -r '.service_name' | tr '_' '-'`.
- Output style matches `validate_config.py`: numbered emoji headings (`1️⃣  Checking ...`), indented `✅`/`❌` result lines.
- Exit codes: `0` all pass, `2` usage error, `10` VPN, `11` SSO, `12` kubectl, otherwise `validate_config.py`'s own exit code passed through.
- VPN auto-connect is out of scope; on VPN failure print the remediation and exit.
- No new Python dependencies.

## Review Focus

1. `service_name` with underscores (e.g. `web_core_api`) must map to namespace `web-core-api` — Task 2 `test_namespace_derived_from_service_name`.
2. `AWS_ENV_FILE` missing must produce a clear one-line error and exit 11, not zsh "no such file" noise — Task 2 `test_missing_aws_env_file_exits_11`.
3. A `utun` interface with a non-`10.x` address (Tailscale `100.64.x.x`) must not count as VPN — Task 1 `test_vpn_tunnel_wrong_subnet_exits_10`.
4. kubectl's real failure text ("Token has expired and refresh failed") must be surfaced in preflight output so the user sees why — Task 2 `test_kubectl_error_exits_12_and_shows_stderr`.
5. Running the script from a cwd other than the repo root must still find `validate_config.py` — Task 3 `test_runs_from_other_cwd`.

---

### Task 1: `preflight.sh` skeleton, VPN check, test harness

**Files:**
- Create: `preflight.sh`
- Create: `cli/tests/test_preflight.py`

**Interfaces:**
- Produces: `./preflight.sh <config.json>` — exit `2` on missing/nonexistent arg (usage to stderr), exit `10` on VPN failure. Functions `check_vpn` (no args; returns 0/1, prints result lines). Script-level vars `CONFIG_FILE`, `SCRIPT_DIR` (`"$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"`).
- Produces (tests): fixture `env_for(tmp_path, *, pgrep_rc=0, ifconfig_mode="ok", kubectl_rc=0, kubectl_out="pod-a Running", sso_rc=0, python_rc=0)` returning `(env: dict, log_dir: Path)`; helper `run_preflight(config_path, env, cwd=None) -> subprocess.CompletedProcess` (captures stdout+stderr as text). Shims record every invocation by appending `"$0 $*"` to `$SHIM_LOG`.

- [ ] **Step 1: Write the test harness and the first failing tests**

In `cli/tests/test_preflight.py`:

```python
import json, os, stat, subprocess
from pathlib import Path
import pytest

REPO = Path(__file__).resolve().parents[2]
PREFLIGHT = REPO / "preflight.sh"

IFCONFIG = {
    "ok":    "utun3: flags=8051<UP> mtu 1000\n\tinet 10.55.100.238 --> 10.55.100.238 netmask 0xffffffff\n",
    "none":  "en0: flags=8863<UP> mtu 1500\n\tinet 192.168.1.5 netmask 0xffffff00\n",
    "other": "utun4: flags=8051<UP> mtu 1280\n\tinet 100.64.0.7 --> 100.64.0.7 netmask 0xffffffff\n",
    "lan10": "utun2: flags=8051<UP> mtu 1500\nen0: flags=8863<UP> mtu 1500\n\tinet 10.0.0.5 netmask 0xffffff00\n",
}

def _shim(bin_dir, name, body):
    p = bin_dir / name
    p.write_text("#!/bin/bash\necho \"$(basename $0) $*\" >> \"$SHIM_LOG\"\n" + body)
    p.chmod(p.stat().st_mode | stat.S_IEXEC)

def env_for(tmp_path, *, pgrep_rc=0, ifconfig_mode="ok", kubectl_rc=0,
            kubectl_out="pod-a 1/1 Running 0 1h", kubectl_err="", sso_rc=0, python_rc=0):
    bin_dir = tmp_path / "bin"; bin_dir.mkdir()
    log = tmp_path / "shim.log"; log.touch()
    _shim(bin_dir, "pgrep", f"exit {pgrep_rc}\n")
    _shim(bin_dir, "ifconfig", f"printf '%b' {json.dumps(IFCONFIG[ifconfig_mode])}\n")
    _shim(bin_dir, "kubectl", f"printf '%s\\n' {json.dumps(kubectl_out)}; printf '%s\\n' {json.dumps(kubectl_err)} >&2; exit {kubectl_rc}\n")
    _shim(bin_dir, "python", f"exit {python_rc}\n")
    aws_env = tmp_path / "aws-env.sh"
    aws_env.write_text(f"aws-qa-login() {{ echo 'fake aws-qa-login'; return {sso_rc}; }}\n")
    env = dict(os.environ, PATH=f"{bin_dir}:{os.environ['PATH']}",
               SHIM_LOG=str(log), AWS_ENV_FILE=str(aws_env))
    return env, log

def write_config(tmp_path, service_name="bcas-add-in"):
    cfg = tmp_path / "cfg.json"
    cfg.write_text(json.dumps({"service_name": service_name, "base_url": "https://x"}))
    return cfg

def run_preflight(config, env, cwd=None):
    return subprocess.run([str(PREFLIGHT), str(config)], env=env, cwd=cwd or REPO,
                          capture_output=True, text=True)

def test_usage_error_without_config(tmp_path):
    env, _ = env_for(tmp_path)
    r = subprocess.run([str(PREFLIGHT)], env=env, cwd=REPO, capture_output=True, text=True)
    assert r.returncode == 2
    assert "Usage" in r.stderr

def test_vpn_process_missing_exits_10(tmp_path):
    env, log = env_for(tmp_path, pgrep_rc=1)
    r = run_preflight(write_config(tmp_path), env)
    assert r.returncode == 10
    assert "Barracuda" in r.stdout
    assert "kubectl" not in log.read_text()

def test_vpn_no_tunnel_exits_10(tmp_path):
    env, _ = env_for(tmp_path, ifconfig_mode="none")
    assert run_preflight(write_config(tmp_path), env).returncode == 10

def test_vpn_tunnel_wrong_subnet_exits_10(tmp_path):
    env, _ = env_for(tmp_path, ifconfig_mode="other")
    assert run_preflight(write_config(tmp_path), env).returncode == 10

def test_vpn_lan_10x_on_non_utun_exits_10(tmp_path):
    env, _ = env_for(tmp_path, ifconfig_mode="lan10")
    assert run_preflight(write_config(tmp_path), env).returncode == 10

def test_vpn_ok_reports_interface(tmp_path):
    env, _ = env_for(tmp_path)
    r = run_preflight(write_config(tmp_path), env)
    assert "utun3" in r.stdout and "10.55.100.238" in r.stdout
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest cli/tests/test_preflight.py -v`
Expected: all 6 FAIL (`preflight.sh` not found / exit code mismatch).

- [ ] **Step 3: Create `preflight.sh` with arg handling and `check_vpn`**

`#!/bin/bash`, no `set -e` (checks return codes deliberately). Header prints `🛫 Pre-flight Checks`, a `=` rule, `Config:` line. Arg handling: missing arg or nonexistent file → `Usage: ./preflight.sh <config.json>` to stderr, `exit 2`.

`check_vpn`: heading `1️⃣  Checking Barracuda VPN...`. Pass iff `pgrep -f "Barracuda VPN Client.app/Contents/MacOS/Barracuda VPN Client" >/dev/null` **and** `ifconfig | awk '/^[a-z]/{i=($1 ~ /^utun/)?$1:""} /inet 10\./{if(i){print i, $2; exit}}'` prints a line (the tracker resets on every interface header so a `10.x` LAN address on `en0` never counts). On pass print `   ✅ VPN connected (<iface> <ip>)`. On fail print `   ❌ Barracuda VPN not connected` plus `   → Connect Barracuda VPN Client and re-run`, and the script exits 10. Trailing `:` on `utun3:` from awk is acceptable in output.

Make executable: `chmod +x preflight.sh`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest cli/tests/test_preflight.py -v`
Expected: 6 PASS.

- [ ] **Step 5: Commit**

```bash
git add preflight.sh cli/tests/test_preflight.py
git commit -m "feat: add preflight.sh with Barracuda VPN check"
```

---

### Task 2: AWS QA SSO and kubectl checks

**Files:**
- Modify: `preflight.sh`
- Modify: `cli/tests/test_preflight.py`

**Interfaces:**
- Consumes: Task 1 harness (`env_for`, `write_config`, `run_preflight`), `CONFIG_FILE`.
- Produces: `check_aws_sso` (exit 11 path), `check_kubectl <namespace>` (exit 12 path), `NAMESPACE` var. `AWS_ENV_FILE` env var, default `"$HOME/Documents/Work/workspace/aws-sso-setup/aws-env.sh"`.

- [ ] **Step 1: Write failing tests**

Append to `cli/tests/test_preflight.py`:

```python
def test_sso_failure_exits_11_and_skips_kubectl(tmp_path):
    env, log = env_for(tmp_path, sso_rc=1)
    r = run_preflight(write_config(tmp_path), env)
    assert r.returncode == 11
    assert "fake aws-qa-login" in r.stdout
    assert "kubectl" not in log.read_text()

def test_missing_aws_env_file_exits_11(tmp_path):
    env, _ = env_for(tmp_path)
    env["AWS_ENV_FILE"] = str(tmp_path / "does-not-exist.sh")
    r = run_preflight(write_config(tmp_path), env)
    assert r.returncode == 11
    assert "does-not-exist.sh" in r.stdout

def test_kubectl_error_exits_12_and_shows_stderr(tmp_path):
    env, _ = env_for(tmp_path, kubectl_rc=1, kubectl_out="",
                     kubectl_err="Error when retrieving token from sso: Token has expired and refresh failed")
    r = run_preflight(write_config(tmp_path), env)
    assert r.returncode == 12
    assert "Token has expired" in r.stdout

def test_kubectl_no_pods_exits_12(tmp_path):
    env, _ = env_for(tmp_path, kubectl_rc=0, kubectl_out="")
    assert run_preflight(write_config(tmp_path), env).returncode == 12

def test_namespace_derived_from_service_name(tmp_path):
    env, log = env_for(tmp_path)
    run_preflight(write_config(tmp_path, service_name="web_core_api"), env)
    assert "kubectl get pods -n web-core-api" in log.read_text()
    assert "--request-timeout=15s" in log.read_text()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest cli/tests/test_preflight.py -v -k "sso or kubectl or namespace"`
Expected: 5 FAIL (script exits 0 after VPN; kubectl never called).

- [ ] **Step 3: Implement `check_aws_sso` and `check_kubectl`**

`check_aws_sso`: heading `2️⃣  Checking AWS QA SSO session...`. If `[ ! -f "$AWS_ENV_FILE" ]` → print `   ❌ aws-env.sh not found: $AWS_ENV_FILE` and return 1. Else run `zsh -c 'source "$1" && aws-qa-login' _ "$AWS_ENV_FILE"` with its stdout/stderr passed through, indented is optional. Non-zero → `   ❌ AWS qa SSO login failed`, return 1; zero → `   ✅ AWS qa profile active`. Caller exits 11 on failure.

`check_kubectl`: heading `3️⃣  Checking kubectl access to namespace <ns>...`. Run `kubectl get pods -n "$1" --no-headers --request-timeout=15s` capturing combined stdout+stderr into a var and the exit code. Fail (return 1) if exit non-zero **or** output has zero non-empty lines; print the captured output indented under `   ❌ Cannot list pods in <ns>`. Pass → `   ✅ <N> pod(s) found in <ns>`. Caller exits 12 on failure.

`NAMESPACE=$(jq -r '.service_name' "$CONFIG_FILE" | tr '_' '-')` computed after arg handling.

- [ ] **Step 4: Run all tests**

Run: `.venv/bin/pytest cli/tests/test_preflight.py -v`
Expected: 11 PASS.

- [ ] **Step 5: Commit**

```bash
git add preflight.sh cli/tests/test_preflight.py
git commit -m "feat: preflight checks AWS QA SSO (auto-login) and kubectl pod access"
```

---

### Task 3: Delegate to `validate_config.py`, wire into `run_test.sh`

**Files:**
- Modify: `preflight.sh`
- Modify: `run_test.sh:70-77`
- Modify: `cli/tests/test_preflight.py`

**Interfaces:**
- Consumes: `SCRIPT_DIR` from Task 1.
- Produces: `preflight.sh` final exit semantics (passes through `validate_config.py` exit code); `run_test.sh` step 1 output heading `1️⃣  Pre-flight checks...`.

- [ ] **Step 1: Write failing tests**

Append:

```python
def test_all_pass_exits_0_and_runs_validate(tmp_path):
    env, log = env_for(tmp_path)
    cfg = write_config(tmp_path)
    r = run_preflight(cfg, env)
    assert r.returncode == 0, r.stdout + r.stderr
    assert f"python {REPO / 'validate_config.py'} {cfg}" in log.read_text()
    assert "PRE-FLIGHT PASSED" in r.stdout

def test_validate_failure_propagates(tmp_path):
    env, _ = env_for(tmp_path, python_rc=1)
    assert run_preflight(write_config(tmp_path), env).returncode == 1

def test_runs_from_other_cwd(tmp_path):
    env, log = env_for(tmp_path)
    r = run_preflight(write_config(tmp_path), env, cwd=tmp_path)
    assert r.returncode == 0
    assert str(REPO / "validate_config.py") in log.read_text()
```

- [ ] **Step 2: Run to verify they fail**

Run: `.venv/bin/pytest cli/tests/test_preflight.py -v -k "validate or cwd or all_pass"`
Expected: 3 FAIL (`python` never invoked / no `PRE-FLIGHT PASSED`).

- [ ] **Step 3: Add step 4 to `preflight.sh`**

Heading `4️⃣  Validating configuration...`, then `python "$SCRIPT_DIR/validate_config.py" "$CONFIG_FILE"`; capture `rc=$?`. Non-zero → `exit $rc`. Zero → print rule, `✅ PRE-FLIGHT PASSED`, rule, `exit 0`.

- [ ] **Step 4: Run all tests**

Run: `.venv/bin/pytest cli/tests/test_preflight.py -v`
Expected: 14 PASS.

- [ ] **Step 5: Replace step 1 in `run_test.sh`**

Replace lines 70–77 (the `1️⃣  Validating configuration...` block calling `python validate_config.py`) with:

```bash
echo ""
echo "1️⃣  Pre-flight checks..."
if ! ./preflight.sh "$CONFIG_FILE"; then
    echo ""
    echo "❌ Pre-flight failed. Fix the issues above before running the test."
    exit 1
fi
```

- [ ] **Step 6: Verify `run_test.sh` wiring manually**

Run: `bash -n run_test.sh && grep -n "preflight.sh" run_test.sh`
Expected: no syntax error; one match at step 1. Then run `./preflight.sh projects/bcas-add-in-config.json` against the real environment once and confirm it stops at the first genuinely failing check (currently expected: SSO triggers a browser login, or the JWT check fails in step 4) rather than crashing.

- [ ] **Step 7: Commit**

```bash
git add preflight.sh run_test.sh cli/tests/test_preflight.py
git commit -m "feat: run preflight.sh as run_test.sh step 1, delegate to validate_config"
```

---

### Task 4: Update `/perf-execute` skill — load-profile prompt and foreground preflight

**Files:**
- Modify: `.claude/skills/perf-execute/SKILL.md:24-103` (Project Selection Workflow)
- Modify: `.claude/skills/perf-execute/SKILL.md:131-196` (Pre-Flight Validation)
- Modify: `.claude/skills/perf-execute/SKILL.md:420-486` (Common Scenarios), `:516-540` (Execution Checklist)
- Modify: `docs/superpowers/specs/2026-11-16-preflight-env-checks-design.md:4` (status → Approved)

**Interfaces:**
- Consumes: `./preflight.sh <config>` exit codes from Tasks 1–3.

- [ ] **Step 1: Rewrite "Project Selection Workflow" (lines 24–103)**

Replace the numbered list at 28–32 with:

```
1. **List Available Projects** from `projects/` directory
2. **Show project details** (service name, base URL)
3. **Ask user to select** which project to run
4. **Ask for the full load profile** (users, spawn_rate, duration, target_rps) — ALWAYS, every run
5. **Write the answers into the config** and run `./preflight.sh` in the FOREGROUND
6. **DO NOT run all projects** - only run the selected one
```

Replace "Step 2: Present Options to User" body (the duration-only prompt) with a load-profile prompt: one `AskUserQuestion` call with four questions, headers `Users`, `Spawn rate`, `Duration`, `Target RPS`. For each, read the current value from the config (`jq -r '.load_profile.users'` etc.) and make it the **first option labelled `<value> (current)`**, followed by three alternatives (Users: 50/200/500; Spawn rate: 10/25/100; Duration: 60s/300s/600s; Target RPS: 100/250/1000 — drop any alternative equal to the current value). Note that `target_rps` is informational only; Locust does not consume it.

Add "Step 3: Persist the load profile":

```bash
jq --argjson u "$USERS" --argjson s "$SPAWN" --argjson d "$DURATION" --argjson r "$TARGET_RPS" \
   '.load_profile = {users:$u, spawn_rate:$s, duration:$d, target_rps:$r}' \
   projects/<config>.json > /tmp/cfg.json && mv /tmp/cfg.json projects/<config>.json
```

Add "Step 4: Pre-flight in the foreground" — run `./preflight.sh projects/<config>.json` with a plain (non-background) Bash call, `timeout` 180000 ms because `aws-qa-login` may open a browser and wait. Table of exit codes: 2 usage, 10 VPN (tell user to connect Barracuda; stop), 11 SSO (login failed/cancelled; stop), 12 kubectl (no pod access; stop), other non-zero = `validate_config.py` failure (show output; stop). Only on exit 0 continue.

Rename old "Step 3: Execute Selected Project" to "Step 5" and change the command to `./run_test.sh <config>.json $DURATION` (background + Monitor exactly as in Core Workflow §7). Note: `run_test.sh` re-runs preflight; by then SSO is fresh so it is non-interactive.

Update the "Example Flow" block so the dialogue shows the four-question prompt and a `./preflight.sh` line before `./run_test.sh`. Update "When Argument Provided": still ask the load profile; never skip preflight.

- [ ] **Step 2: Rewrite "Pre-Flight Validation" (lines 131–196)**

Delete the duplicated heading at 131–134. Retitle 135 to `### 2. Pre-Flight Checks (environment + config)`. Replace the bash block with `./preflight.sh projects/<config>.json` and the exit-code table from Step 1. Replace "What gets validated" with the ordered list: Barracuda VPN (process + `utun` with `10.x` address) → AWS QA SSO via `aws-qa-login` (browser login only if expired, refreshes kubeconfig) → `kubectl get pods -n <namespace>` ≥1 pod → existing `validate_config.py` checks (keep the five existing bullets beneath). Replace the example output block with a trimmed `🛫 Pre-flight Checks` transcript showing the four numbered sections and `✅ PRE-FLIGHT PASSED`. Add to "Common issues caught": `🔴 Expired AWS SSO session (prevents silently empty K8s metrics)`, `🔴 VPN disconnected (prevents kubectl/metrics failures)`.

- [ ] **Step 3: Update Scenarios and Checklist**

In Scenarios 1–3 (lines 420–469), replace "Ask for duration" steps with "Ask load profile (users, spawn_rate, duration, target_rps)", insert "Write load_profile to config" and "Run ./preflight.sh in foreground; stop on non-zero" before the `run_test.sh` step. In the "Before running" checklist (518–525) add: `- [ ] Barracuda VPN connected`, `- [ ] AWS qa SSO session active (aws-qa-login)`, `- [ ] kubectl can list pods in the target namespace`, `- [ ] Load profile confirmed for this run`.

- [ ] **Step 4: Mark the design approved**

In the spec, change line 4 to `**Status:** Approved 2026-11-16`.

- [ ] **Step 5: Verify**

Run: `grep -c "preflight.sh" .claude/skills/perf-execute/SKILL.md && grep -n "How long should the test run" .claude/skills/perf-execute/SKILL.md`
Expected: count ≥ 4; the duration-only prompt string has **no** remaining matches.

- [ ] **Step 6: Commit**

```bash
git add .claude/skills/perf-execute/SKILL.md docs/superpowers/specs/2026-11-16-preflight-env-checks-design.md
git commit -m "docs(skill): perf-execute asks full load profile and runs preflight.sh in foreground"
```
