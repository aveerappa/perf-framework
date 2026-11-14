import argparse
import sys


def main():
    """Main CLI entry point for perf-framework."""
    parser = argparse.ArgumentParser(
        description="Generic Locust Performance Testing Framework"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze service repository")
    analyze_parser.add_argument("repo_path", help="Path to repository")
    analyze_parser.add_argument("--output", required=True, help="Output test plan file")

    # prepare command
    prepare_parser = subparsers.add_parser("prepare", help="Prepare test configuration")
    prepare_parser.add_argument("--plan", required=True, help="Test plan file")
    prepare_parser.add_argument("--jwt", help="JWT token")

    # execute command
    execute_parser = subparsers.add_parser("execute", help="Execute load tests")
    execute_parser.add_argument("--config", required=True, help="Config file")
    execute_parser.add_argument("--dry-run", action="store_true", help="Dry run mode")

    # report command
    report_parser = subparsers.add_parser("report", help="Generate test report")
    report_parser.add_argument("--run-id", required=True, help="Test run ID")

    args = parser.parse_args()

    if args.command == "analyze":
        print(f"Analyzing repository: {args.repo_path}")
        print(f"Output: {args.output}")
    elif args.command == "execute":
        if args.dry_run:
            print("Dry run mode: would execute load test")
        else:
            print(f"Executing load test with config: {args.config}")
    elif args.command == "report":
        print(f"Generating report for run: {args.run_id}")
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
