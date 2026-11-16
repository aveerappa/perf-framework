import json
import os
import stat
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PREFLIGHT = REPO / "preflight.sh"

IFCONFIG = {
    "ok": "utun3: flags=8051<UP> mtu 1000\n\tinet 10.55.100.238 --> 10.55.100.238 netmask 0xffffffff\n",
    "none": "en0: flags=8863<UP> mtu 1500\n\tinet 192.168.1.5 netmask 0xffffff00\n",
    "other": "utun4: flags=8051<UP> mtu 1280\n\tinet 100.64.0.7 --> 100.64.0.7 netmask 0xffffffff\n",
    "lan10": "utun2: flags=8051<UP> mtu 1500\nen0: flags=8863<UP> mtu 1500\n\tinet 10.0.0.5 netmask 0xffffff00\n",
}


def _shim(bin_dir, name, body):
    p = bin_dir / name
    p.write_text("#!/bin/bash\necho \"$(basename $0) $*\" >> \"$SHIM_LOG\"\n" + body)
    p.chmod(p.stat().st_mode | stat.S_IEXEC)


def env_for(tmp_path, *, pgrep_rc=0, ifconfig_mode="ok", kubectl_rc=0,
            kubectl_out="pod-a 1/1 Running 0 1h", kubectl_err="", sso_rc=0, python_rc=0):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = tmp_path / "shim.log"
    log.touch()
    _shim(bin_dir, "pgrep", f"exit {pgrep_rc}\n")
    _shim(bin_dir, "ifconfig", f"printf '%b' {json.dumps(IFCONFIG[ifconfig_mode])}\n")
    _shim(bin_dir, "kubectl",
          f"printf '%s\\n' {json.dumps(kubectl_out)}; printf '%s\\n' {json.dumps(kubectl_err)} >&2; exit {kubectl_rc}\n")
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


def test_missing_service_name_exits_2_before_any_check(tmp_path):
    env, log = env_for(tmp_path)
    cfg = tmp_path / "cfg.json"
    cfg.write_text(json.dumps({"base_url": "https://x"}))
    r = run_preflight(cfg, env)
    assert r.returncode == 2
    assert "service_name" in r.stderr
    assert log.read_text() == ""


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
