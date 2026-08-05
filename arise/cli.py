from __future__ import annotations

import argparse
import json
from pathlib import Path

from .runner import run_scenario


def main() -> None:
    parser = argparse.ArgumentParser(prog="arise")
    subparsers = parser.add_subparsers(dest="command", required=True)
    run = subparsers.add_parser("run")
    run.add_argument("scenario", type=Path)
    run.add_argument("--out", type=Path)
    args = parser.parse_args()
    result = run_scenario(args.scenario)
    rendered = json.dumps(result, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered + "\n")
    print(rendered)


if __name__ == "__main__":
    main()

