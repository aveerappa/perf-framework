# Pre-flight environment checks and load-profile prompt

**Date:** 2026-11-16
**Status:** Approved 2026-11-16

## Intent

Before any performance test starts, verify the local environment can actually
support the run (AWS QA SSO, Barracuda VPN, kubectl access to the target pods),
and always confirm the full load profile with the user rather than only the
duration.

**Why:** the K8s metrics collector (`monitor_multi_service.sh`) depends on
`kubectl` → AWS SSO and fails silently in the background. On 2026-11-16 the SSO
token had expired mid-session and `kubectl get pods -n bcas-add-in` failed with
"Token has expired and refresh failed", so the K8s panels of that run's report
were empty. Nothing caught it.

## Goals

- Fail fast, in the foreground, before Locust or the metrics collector starts.
- Auto-remediate SSO by calling the user's existing `aws-qa-login` function.
- Make the load profile (users, spawn_rate, duration, target_rps) an explicit
  per-run decision.

## Non-goals

- Auto-connecting the VPN (Barracuda has no scriptable connect; report and stop).
- Changing how Locust or the report generator work.
- Multi-project / multi-cluster support beyond the existing `qa` profile.

## Anti-goals

- A check that passes while the real thing is broken (e.g. "Barracuda process
  is running" without a tunnel up).
- Hanging a background run on an interactive browser login.

## Constraints

- `aws-qa-login` is a zsh function defined in
  `~/Documents/Work/workspace/aws-sso-setup/aws-env.sh`; it must be sourced.
  `aws sso login` opens a browser and blocks until the user completes it.
- `run_test.sh` is bash with `set -e`; `timeout(1)` is not on this Mac.
- The skill launches `run_test.sh` in the background and tails its log, so
  interactive steps cannot live inside that background process.

## Approaches considered

- **A. New `preflight.sh` (chosen).** Standalone script runs env checks then the
  existing `validate_config.py`. Called by `run_test.sh` (step 1) and by the
  skill in the foreground before backgrounding the test.
- **B. Extend `validate_config.py`.** Single validator, but sourcing a zsh
  function and driving an interactive login from Python is clumsy.
- **C. Inline in `run_test.sh`.** Fewest files, but checks can't run standalone,
  so the background-launch hang remains.

## Design

### `preflight.sh <config.json>`

Order matters: each check is a precondition for the next.

1. **VPN** — pass if the Barracuda VPN Client process is running **and** some
   `utun*` interface holds a `10.x.x.x` address. On fail: print "Connect
   Barracuda VPN and re-run", exit 1.
2. **AWS QA SSO** — `source ~/Documents/Work/workspace/aws-sso-setup/aws-env.sh`
   then call `aws-qa-login`. It validates the session, triggers
   `aws sso login` (browser) only if expired, and refreshes kubeconfig for
   `bcas-qa-ue2-default-cluster`. Non-zero exit → stop.
3. **kubectl pod access** — `kubectl get pods -n <namespace>
   --request-timeout=15s`, where namespace is derived from `service_name` the
   same way `run_test.sh` does. Pass if exit 0 and at least one pod listed.
4. **Config validation** — `python validate_config.py <config>` (unchanged).

Output follows the existing emoji/section style. Exit 0 only if all four pass.

### `run_test.sh`

Step 1 calls `./preflight.sh "$CONFIG_FILE"` instead of `validate_config.py`
directly. No other change.

### Skill `perf-execute` (SKILL.md)

New flow, replacing the current duration-only prompt:

1. Discover/select project (unchanged).
2. **Ask load profile** — one `AskUserQuestion` with four questions (users,
   spawn_rate, duration, target_rps), each pre-filled with the config's current
   value as the first/recommended option plus a few sensible alternatives.
3. Write the answers into `projects/<config>.json` `.load_profile` with `jq`, so
   they become the next run's defaults.
4. Run `./preflight.sh projects/<config>.json` **in the foreground**. If it
   exits non-zero, show the output and stop — do not start the test.
5. Launch `./run_test.sh` in the background and monitor as today (preflight
   re-runs inside it; by then SSO is fresh so it is non-interactive).

Document `target_rps` as informational (Locust does not consume it).

## Left to the builder

- Exact Barracuda process match string (observed:
  `/Applications/Barracuda VPN Client.app/Contents/MacOS/Barracuda VPN Client`).
- Whether to also print the detected tunnel interface/IP for diagnostics.
- Phrasing of the four `AskUserQuestion` options.
