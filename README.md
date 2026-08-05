# ARISE Experiment

ARISE is a small experimental framework for testing whether an LLM can revise scientific beliefs when later evidence contradicts earlier conclusions. It tracks claims, provenance, confidence, dependency edges, invalidations, and revision quality across multi-round scenarios.

Current state: the deterministic experiment engine, strict provenance validation, canonical scenario fingerprints, repeat-verification CLI, sample drug-discovery scenario, and metric tests work locally. An LLM adapter is the next step; the included rule-based adapter keeps experiments reproducible without an API key.

```bash
python -m arise.cli run scenarios/drug_discovery.json --out runs/demo.json --verify-repeat
python -m unittest discover -s tests -v
```
