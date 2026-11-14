from pathlib import Path
from datetime import datetime
from dataclasses import dataclass
import subprocess
import csv


@dataclass
class LocustResult:
    """Results from Locust execution."""
    start_time: datetime
    end_time: datetime
    csv_path: Path
    exit_code: int
    stderr: str


class LocustRunner:
    """Runs Locust in headless mode and parses results."""

    def __init__(self):
        pass

    def run(
        self,
        locustfile: Path,
        users: int,
        spawn_rate: int,
        duration: str,
        host: str
    ) -> LocustResult:
        """
        Run Locust in headless mode.

        Args:
            locustfile: Path to Locustfile
            users: Number of concurrent users
            spawn_rate: Users to spawn per second
            duration: Test duration (e.g., "10m", "30s")
            host: Target host URL

        Returns:
            LocustResult with execution metadata
        """
        start_time = datetime.now()

        # Prepare output path
        csv_base = locustfile.parent / "locust-results"

        # Run Locust
        cmd = [
            "locust",
            "-f", str(locustfile),
            "--headless",
            "-u", str(users),
            "-r", str(spawn_rate),
            "-t", duration,
            "--host", host,
            "--csv", str(csv_base)
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )

        end_time = datetime.now()

        csv_path = Path(f"{csv_base}_stats.csv")

        return LocustResult(
            start_time=start_time,
            end_time=end_time,
            csv_path=csv_path,
            exit_code=result.returncode,
            stderr=result.stderr
        )

    def parse_results_csv(self, csv_path: Path) -> dict:
        """
        Parse Locust results CSV file.

        Args:
            csv_path: Path to Locust stats CSV file

        Returns:
            dict with p50, p95, p99, error_rate, requests_per_sec
        """
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        if not rows:
            return {
                "p50": 0.0,
                "p95": 0.0,
                "p99": 0.0,
                "error_rate": 0.0,
                "requests_per_sec": 0.0
            }

        # Get first data row (aggregate stats)
        row = rows[0]

        # Extract percentiles (already in ms)
        p50 = float(row.get("50%", 0))
        p95 = float(row.get("95%", 0))
        p99 = float(row.get("99%", 0))

        # Calculate error rate from Request Count and Failure Count
        request_count = int(row.get("Request Count", 0))
        failure_count = int(row.get("Failure Count", 0))

        if request_count > 0:
            error_rate = (failure_count / request_count) * 100
        else:
            error_rate = 0.0

        # Requests per sec (placeholder - would need duration data)
        requests_per_sec = 0.0

        return {
            "p50": p50,
            "p95": p95,
            "p99": p99,
            "error_rate": error_rate,
            "requests_per_sec": requests_per_sec
        }
