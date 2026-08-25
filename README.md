# arise experiment

what needs to change when new evidence contradicts an earlier claim?

claims / sources / confidence / dependency edges / revisions

includes the scenario format, CLI, a drug-discovery example, and metric tests.

```sh
python -m arise.cli run scenarios/drug_discovery.json --out runs/demo.json
python -m unittest discover -s tests -v
```

the included adapter is rule-based and deterministic, so the example runs without an API key. an LLM adapter is still to be added; this repository alone does not demonstrate an end-to-end LLM experiment.

## Implementation details

Claim revisions are validated before the original claim changes state. Evidence IDs are deduplicated during confidence aggregation, and revision metrics keep invalidations separate across experimental rounds.
