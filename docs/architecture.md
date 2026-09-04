# Architecture

DecisionGate v0.1 uses an explicit pipeline so its epistemic behavior can be inspected.

```text
local documents
      |
      v
claim extraction -----> stable IDs + provenance + source location
      |                                  |
      v                                  |
predicate/assumption compilation         |
      |                                  |
      +---------- references only -------+
      |
      v
assumption inversion + evidence arbitration
      |
      v
deterministic gate rules
      |
      +----> JSON report
      +----> Markdown report
```

## Trust boundary

The source corpus is read before model-assisted analysis. A provider receives those claims and may return predicates, assumptions, questions, and links to existing claim IDs. Unknown IDs are discarded. Provider prose is never inserted as source evidence.

An explicit claim means only that the source explicitly made the statement. Whether it resolves a predicate depends on its linkage, provenance, tier, and any opposing evidence.

## Arbitration

A linked claim counts as independent evidence only when it is explicit, has source/external/direct-observation provenance, and belongs to the authoritative, documented-external, or directly-observed tiers. Model interpretation, supported inference, user assumption, and unsupported speculation never independently resolve a critical predicate.

For each predicate:

- independent evidence on both sides → `UNRESOLVED` plus contradiction
- independent evidence only against → `REFUTED`
- independent evidence only for → `SUPPORTED`
- anything else → `UNRESOLVED`

The gate then applies a small truth table. Any refuted critical predicate yields `NO_GO`; otherwise any unresolved critical predicate yields `HUMAN_VERIFY`; only all-supported critical predicates yield `GO`.

## Provider isolation

`ModelProvider.complete_json` is the only provider-specific boundary. `DeterministicProvider` queues fixed responses for network-free tests. `OpenAIProvider` is an optional adapter. Future adapters can implement the protocol without changing the engine.

The v0.1 provider call compiles analysis in one isolated request with no conversation history. Separate proponent and challenger calls can be added later, but the final arbiter must remain evidence-based.
