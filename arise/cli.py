from __future__ import annotations

import argparse
import json
from pathlib import Path

from .runner import run_scenario
from .benchmark import benchmark
from .report import render_report
from .validation import ScenarioError


def main() -> None:
    parser = argparse.ArgumentParser(prog="arise")
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run")
    run.add_argument("scenario", type=Path)
    run.add_argument("--policy", choices=["revision", "static"], default="revision")
    run.add_argument("--out", type=Path)
    run.add_argument("--html", type=Path)
    suite = commands.add_parser("benchmark")
    suite.add_argument("scenarios", nargs="+", type=Path)
    suite.add_argument("--seed", type=int, default=0)
    suite.add_argument("--samples", type=int, default=2000)
    suite.add_argument("--out", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "run":
            result = run_scenario(args.scenario, policy=args.policy)
            if args.html:
                args.html.parent.mkdir(parents=True, exist_ok=True)
                args.html.write_text(render_report(result) + "\n")
        else:
            result = benchmark(args.scenarios, seed=args.seed, samples=args.samples)
        rendered = json.dumps(result, indent=2, allow_nan=False)
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(rendered + "\n")
        print(rendered)
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(2, f"arise: {error}\n")


if __name__ == "__main__":
    main()
