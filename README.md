# DecisionGate

> **DecisionGate — a falsification-first adjudication framework for LLM-assisted decisions.**

DecisionGate does not ask whether an AI can construct a convincing argument for a decision. It asks whether the assumptions required by that decision have survived an explicit attempt to falsify them.

It is a small, inspectable Python engine and CLI for decisions such as proposal fit, architecture selection, investment theses, hiring, scientific hypotheses, vendor selection, security, compliance, and agent actions.

## The problem

Several frontier models can read the same material, independently produce persuasive reviews, and converge on the same wrong conclusion. Agreement is not necessarily independent validation: the models may share training data, framing, missing context, or the same unstated assumption. Repeating an interpretation does not turn it into evidence.

DecisionGate therefore separates:

- **EXPLICIT** — a supplied source says this (which is not the same as proving it true)
- **INFERENCE** — reasoning supported by evidence but not stated by it
- **ASSUMPTION** — a bridge the decision needs but evidence has not established
- **CONTRADICTED** — evidence conflicts with the claim
- **UNKNOWN** — the available corpus cannot answer it

Each claim retains its source, location, evidence class, provenance class, evidence tier, and confidence. Model output is `MODEL_INFERENCE`; it cannot create `SOURCE_EVIDENCE`.

## Falsification first

The engine compiles the decision into predicates, links existing evidence to each predicate, exposes assumptions, inverts each favorable assumption, and asks what evidence would distinguish the favorable and unfavorable interpretations. The final gate is deterministic:

- `NO_GO` when independent evidence refutes any critical predicate
- `HUMAN_VERIFY` when any critical predicate is unresolved or contradicted
- `GO` only when every critical predicate is supported by independent evidence

There is deliberately no aggregate fit score that can hide missing evidence. Confidence is bounded by the weakest critical predicate, and an unresolved critical predicate forces report confidence to zero.

## Quick start

```bash
conda create -n decisiongate python=3.12 -y
conda activate decisiongate
python -m pip install -e '.[dev]'
pytest
decisiongate evaluate --case cases/quantumeagle_scope/case.json --output build/quantumeagle
```

Or evaluate files directly:

```bash
decisiongate evaluate \
  --evidence evidence/requirements.pdf \
  --evidence evidence/proposal.pdf \
  --decision "Submit this proposal to this research program" \
  --output build/report
```

PDF, Markdown, and plain-text evidence are supported. The default deterministic analyzer is conservative. It understands the optional annotations described below; without explicit predicate/evidence links it creates one unresolved evidentiary-basis predicate and returns `HUMAN_VERIFY`.

Use the optional provider for unstructured analysis:

```bash
python -m pip install -e '.[openai]'
export OPENAI_API_KEY='...'
decisiongate evaluate --provider openai --evidence requirements.pdf \
  --decision "Adopt architecture B" --output build/architecture-b
```

The OpenAI adapter is optional. The provider boundary is generic, and the adjudicator applies the same deterministic rules to provider output. API keys belong in the environment; `.env` is ignored.

## Worked example

An auditable offline evidence file can say:

```text
[PREDICATE security_review | CRITICAL] The release has passed the required security review.
[FOR security_review | PRIMARY] Approval record SR-104 marks the release approved.
[QUESTION security_review] Is SR-104 still valid for the current build hash?
```

The first line defines a consequential predicate. The second is an explicit source statement linked in favor of it and classified as primary authoritative evidence. The question is preserved for reviewers. With no contrary evidence, the result is `GO`.

Now replace the supporting line with:

```text
[FOR security_review | MODEL] Three model reviewers predict that approval is likely.
```

That result is `HUMAN_VERIFY`: three model opinions still provide no independent evidence that the review occurred.

See [docs/annotation-format.md](docs/annotation-format.md) and the checked-in [QuantumEagle regression case](cases/quantumeagle_scope/README.md).

## Outputs

Every run writes:

- `decisiongate-report.json` — typed, machine-readable report
- `decisiongate-report.md` — human-readable evidence, predicates, inversions, contradictions, decision-changing questions, adjudication, and provenance

An example generated report is checked in at [examples/quantumeagle-report.md](examples/quantumeagle-report.md).

## Architecture

The implementation is intentionally explicit:

1. the document reader extracts source statements with stable claim IDs;
2. a deterministic or provider-assisted analyzer proposes predicates and assumptions;
3. the trust boundary rejects references to claim IDs not present in the source corpus;
4. the arbiter classifies predicates using only independent evidence;
5. deterministic gate rules select the disposition;
6. renderers produce JSON and Markdown with provenance.

The proponent and challenger views are projections over the same evidence graph. They cannot win by eloquence, and their agreement is never counted as corroboration. See [docs/architecture.md](docs/architecture.md).

## Current limitations

- The deterministic analyzer expects annotations for domain-specific predicates. It does not claim to understand arbitrary prose.
- The optional model-assisted path compiles predicates in one call in v0.1; isolated proponent/challenger model calls are planned.
- PDF extraction handles text PDFs, not OCR for scanned documents.
- Evidence authority is declared by the input annotation or provider proposal and still requires human scrutiny.
- External retrieval is a future extension point; v0.1 never invents or fetches external facts.
- The system identifies evidence insufficiency. It cannot discover a decision-maker's undisclosed intent.

## Roadmap

- pluggable external evidence retrievers with immutable provenance records
- isolated extraction, proponent, challenger, and arbiter model calls
- stronger quotation/span verification for model-proposed evidence links
- domain packs for recurring predicate families without coupling the core engine
- OCR and additional local document formats
- signed reports and reproducible evaluation manifests

## Development

```bash
python -m pip install -e '.[dev]'
pytest
```

DecisionGate is licensed under Apache-2.0. Contributions should preserve the central trust boundary: interpretations may organize evidence, but they may not become evidence.

