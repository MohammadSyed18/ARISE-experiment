"""Deterministic scenario-suite comparisons with paired bootstrap intervals."""

from __future__ import annotations

import random
from statistics import mean
from pathlib import Path

from .runner import run_scenario


def paired_interval(deltas: list[float], *, seed: int = 0, samples: int = 2000) -> dict:
    if not deltas or not isinstance(samples, int) or samples < 100 or samples > 100000:
        raise ValueError("nonempty deltas and 100..100000 bootstrap samples required")
    rng = random.Random(seed)
    estimates = sorted(mean(rng.choices(deltas, k=len(deltas))) for _ in range(samples))
    return {
        "mean_delta": mean(deltas),
        "lower": estimates[int(samples * 0.025)],
        "upper": estimates[min(samples - 1, int(samples * 0.975))],
        "seed": seed,
        "samples": samples,
    }


def benchmark(paths: list[Path], *, seed: int = 0, samples: int = 2000) -> dict:
    paths = sorted({Path(path).resolve() for path in paths})
    if not paths:
        raise ValueError("at least one scenario is required")
    pairs = []
    for path in paths:
        revision = run_scenario(path, policy="revision")
        static = run_scenario(path, policy="static")
        pairs.append(
            {
                "scenario": revision["scenario"],
                "path": path.name,
                "revision": revision["metrics"],
                "static": static["metrics"],
                "rounds": len(revision["rounds"]),
            }
        )
    keys = list(pairs[0]["revision"])
    return {
        "scenarios": len(pairs),
        "pairs": pairs,
        "aggregate": {
            policy: {
                key: round(mean(pair[policy][key] for pair in pairs), 4) for key in keys
            }
            for policy in ("revision", "static")
        },
        "paired_intervals": {
            key: paired_interval(
                [pair["revision"][key] - pair["static"][key] for pair in pairs],
                seed=seed,
                samples=samples,
            )
            for key in keys
        },
        "interpretation": "Intervals resample scenario pairs. Lower reasoning drift is better; higher other scores are better. Hand-authored scenarios are not an external model benchmark.",
    }
