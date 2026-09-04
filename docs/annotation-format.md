# Deterministic annotation format

DecisionGate can run without an API key. Plain unannotated lines are extracted as explicit source statements but are not silently mapped to decision predicates. Annotations add an auditable mapping.

```text
[PREDICATE <id> | CRITICAL] <statement>
[PREDICATE <id> | NONCRITICAL] <statement>
[FOR <id> | <tier>] <source statement supporting the predicate>
[AGAINST <id> | <tier>] <source statement opposing the predicate>
[ASSUMPTION <id>] <unstated bridge required by the favorable interpretation>
[INVERSION <id>] <strongest plausible negation of the favorable assumption>
[QUESTION <id>] <smallest question likely to change the disposition>
```

Evidence tiers are `PRIMARY`, `EXTERNAL`, `OBSERVED`, `MODEL`, and `SPECULATION`. When omitted, a `FOR` or `AGAINST` statement is documented source evidence. `MODEL` and `SPECULATION` do not count as independent evidence.

The annotations are an offline testing and audit format, not a claim that users should manually structure every production document. A model provider can propose the same structure for unannotated text, subject to the claim-ID trust boundary.
