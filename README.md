# ARISE

A deterministic experiment framework for evidence-grounded belief revision. Claims have epistemic tags, confidence, evidence references, dependencies, and explicit revision states. New evidence can revise a claim and invalidate downstream conclusions.

## Run

Python 3.11 or newer; the experiment core uses the standard library.

```sh
python -m unittest discover -s tests -v
python -m arise.cli run scenarios/drug_discovery.json --out runs/demo.json --html runs/demo.html
python -m arise.cli run scenarios/drug_discovery.json --policy static
python -m arise.cli benchmark scenarios/*.json --seed 19 --samples 2000 --out runs/benchmark.json
```

Open `runs/demo.html` in a browser to inspect the claim table, evidence, metrics, and round trace.

## Code map

| Module | Responsibility |
| --- | --- |
| [models.py](arise/models.py) | Typed claims, evidence, epistemic statuses, state validation |
| [graph.py](arise/graph.py) | Claim insertion, revisions, descendant invalidation, evidence aggregation |
| [validation.py](arise/validation.py) | Contextual scenario validation and cross-round reference checks |
| [runner.py](arise/runner.py) | Atomic round staging, revision/static policies, trace generation |
| [analysis.py](arise/analysis.py) | Provenance explanations, topological order, revision-impact previews, graph health, source-grouped confidence |
| [metrics.py](arise/metrics.py) | Contradiction detection, invalidation F1, drift, tagging consistency |
| [benchmark.py](arise/benchmark.py) | Paired scenario comparisons and seeded bootstrap intervals |
| [report.py](arise/report.py) | Standalone escaped HTML reports |
| [cli.py](arise/cli.py) | Run and benchmark commands |

## Revision integrity

A scenario is validated before execution: duplicate IDs, missing evidence, inactive dependencies, nonfinite confidence, and invalid epistemic tags are rejected with round context. A replacement cannot depend on a claim it is about to invalidate. Each round stages changes on a copy; failures leave the input graph intact.

`analysis.explain(graph, claim_id)` returns ordered dependencies, evidence, source groups, unsupported roots, and relevant revisions. `revision_impact()` previews affected descendants without mutating the graph. Source-adjusted confidence groups evidence from the same source to avoid counting repeated measurements as independent; it is a sensitivity heuristic, not a calibrated probability model.

## Evaluation

The `revision` policy applies supplied revision instructions. The `static` ablation admits the same new candidate claims while retaining old beliefs. Both run on the same scenario pairs. Metrics preserve round identity so invalidating a claim in the wrong round does not earn credit. Drift includes claims that remain active after scenario instructions identify them as obsolete.

The suite includes drug-discovery, sensor-calibration, and material-stability examples. These are hand-authored computational scenarios. Revision instructions and expected invalidations are supplied by the fixtures; the framework does not independently discover scientific contradictions. Optional `expected_status` labels support tagging checks; absent those labels, the tagging metric only checks consistency with the supplied schema.

Bootstrap intervals resample scenario pairs. Three examples are useful for regression checks, but do not establish broad research performance. There is no LLM adapter or end-to-end model benchmark in this version.

## Tests

The suite exercises revision rollback, invalid dependency replacement, source correlation, read-only provenance, cross-round metric identity, stale-belief baseline behavior, deterministic bootstrap sampling, scenario errors, and HTML escaping.
