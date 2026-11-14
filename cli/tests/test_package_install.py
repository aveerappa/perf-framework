import subprocess
import sys
from pathlib import Path

def test_package_installs():
    """Verify perf-framework package installs without errors."""
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-e", str(Path.home() / "perf-framework/cli")],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0, f"Install failed: {result.stderr}"

def test_version_importable():
    """Verify version module imports correctly."""
    import perf_framework
    assert hasattr(perf_framework, '__version__')
    assert perf_framework.__version__ == "0.1.0"
