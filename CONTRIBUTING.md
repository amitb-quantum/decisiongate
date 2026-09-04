# Contributing to DecisionGate

DecisionGate is interested in failure cases more than demonstrations of fluent model output. A useful change should preserve these invariants:

- source evidence, external evidence, inference, assumptions, and unknowns remain distinguishable;
- a provider cannot manufacture evidence or silently upgrade an interpretation;
- model agreement is not counted as independent corroboration;
- unresolved critical predicates produce `HUMAN_VERIFY`;
- gate behavior remains deterministic and testable without network access.

Set up the project with Python 3.12 or newer:

```bash
python -m pip install -e '.[dev]'
pytest
```

Please add a regression test for the failure mode a change addresses. Keep provider integrations optional and avoid adding orchestration frameworks unless a concrete requirement justifies them.

