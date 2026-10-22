# ARISE experiment

An experiment around a simple question: what happens to a chain of reasoning when new evidence contradicts one of its earlier claims?

The code tracks claims, sources, confidence, dependencies, and revisions across a scenario. It includes a CLI, a drug-discovery example, and tests for the revision metrics.

```sh
python -m arise.cli run scenarios/drug_discovery.json --out runs/demo.json
python -m unittest discover -s tests -v
```

The included adapter is rule-based and deterministic, so the example runs without an API key. An LLM adapter is still to be added; this repository alone does not demonstrate an end-to-end LLM experiment.
