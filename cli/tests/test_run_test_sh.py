from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RUN_TEST = REPO / "run_test.sh"


def test_run_directory_timestamp_is_computed_once():
    # Two independent strftime calls can straddle a second boundary, putting the
    # generated locustfile/config in a different directory than the one Locust cds into.
    source = RUN_TEST.read_text()
    assert source.count("strftime('%Y-%m-%dT%H-%M-%SZ')") == 1
