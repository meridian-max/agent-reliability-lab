# Agent Reliability Lab

[![Tests](https://github.com/meridian-max/agent-reliability-lab/actions/workflows/tests.yml/badge.svg)](https://github.com/meridian-max/agent-reliability-lab/actions/workflows/tests.yml)

An offline evaluation toolkit for tool-using agent traces. It checks actions, exact tool arguments, refund approvals, citation provenance, missing traces and release criteria. It also provides deterministic mock tools with idempotent refunds and a readable HTML report.

## Run it

Requires Python 3.11 or later. No API key or third-party runtime package is needed.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m agent_reliability demo --output runs/demo
python -m unittest discover -s tests -v
```

Open `runs/demo/faulty-report.html` to inspect failed cases. The demo produces JSONL cases and traces plus JSON/HTML reports for two controls:

| Control | Contracts passed | Critical failures |
| --- | ---: | ---: |
| Oracle reading expected labels | 16/16 | 0 |
| Deliberately faulty traces | 10/16 | 6 |

These results test the evaluator, **not a language model**. Both trace generators read fixture labels. Latency and cost in these fixtures are zero-valued placeholders for local mock execution, not measured provider performance. No live external tool is called.

## Evaluate your own traces

Record one JSON object per line with a unique fixture ID:

```json
{"id":"dev-lookup","action":"tool","calls":[{"name":"lookup_order","arguments":{"order_id":"ORDER-10"}}],"citations":[],"latency_ms":123.0,"cost_usd":0.002}
```

```bash
python -m agent_reliability evaluate \
  --cases runs/demo/cases.jsonl \
  --traces runs/demo/oracle.jsonl \
  --split test \
  --minimum-pass-rate 1.0 \
  --output runs/my-report.json
```

Exit status is zero only when the pass-rate threshold is satisfied **and** no critical failure occurs. Missing cases count as failures. Duplicate or unknown trace IDs are rejected. Missing cost telemetry produces an unknown total instead of a misleading zero.

The catalogue currently contains `lookup_order`, `search_docs` and `issue_refund`. Fields are type checked, including rejection of booleans where integer refund amounts are expected. An approval flag belongs to the trusted case context; the trace cannot approve its own refund.

## Design

```text
Case contracts + recorded traces
            |
            v
 ID and split validation -> action / argument / citation checks
            |                         |
            v                         v
      category slices       critical safety failures
            \                         /
             -> JSON and HTML report -> release gate
```

`agent_reliability/core.py` contains the evaluator and mock execution model. `demo.py` contains 16 public contract fixtures, with eight categories and explicit development/test labels. The validator rejects identical family labels across splits; it cannot infer semantic leakage from arbitrary labels. These fixtures are public smoke tests, not a hidden or independently sampled benchmark.

Mock refunds reject unapproved execution and conflicting reuse of an idempotency key. Retrying the same approved request returns the same simulated refund ID without incrementing the execution count. Replay rejects a trace that fails its case contract.

## Scope

This is a local Python library and CLI, with 16 unit tests. It does not run an LLM, judge open-ended answer quality, instrument a production service or establish resistance to every prompt injection. A citation check verifies membership in allowed source IDs, not factual entailment. Extend the fixture catalogue and connect recorded provider traces before using it for model comparisons.

The repository was created in November 2026. It has no affiliation with any employer named in a résumé template and contains no customer data.

## License

MIT. See [LICENSE](LICENSE).
