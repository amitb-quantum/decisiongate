# DecisionGate

> **DecisionGate — a falsification-first adjudication framework for LLM-assisted decisions.**

DecisionGate is a falsification-first adjudication framework for LLM-assisted decisions. It is a small, inspectable Python engine and CLI that keeps evidence separate from the interpretations built on top of it.

Multiple LLMs can agree on a convincing conclusion while sharing the same unsupported assumption. Agreement is not independent evidence. Repeating an interpretation does not turn it into a fact.

DecisionGate does not ask whether an AI can construct a convincing argument for a decision. It asks whether the assumptions required by that decision have survived an explicit attempt to falsify them.

DecisionGate does not try to guarantee that a decision is correct. It tries to prevent an LLM-assisted reasoning process from treating unresolved assumptions as established evidence.

## What it does differently

For a proposed decision, DecisionGate separates:

- **EXPLICIT** — a supplied source says this (which is not the same as proving it true)
- **INFERENCE** — reasoning supported by evidence but not stated by it
- **ASSUMPTION** — a bridge the decision needs but evidence has not established
- **CONTRADICTED** — evidence conflicts with the claim
- **UNKNOWN** — the available corpus cannot answer it

Each claim retains its source, location, evidence class, provenance class, evidence tier, and confidence. Model output is `MODEL_INFERENCE`; it cannot create `SOURCE_EVIDENCE`.

The analysis identifies the predicates that must hold, exposes assumptions connecting evidence to the proposed decision, constructs plausible inversions of favorable assumptions, and asks what evidence would distinguish the competing interpretations.

```text
evidence
→ plausible interpretation
→ hidden assumption
→ falsification attempt
→ predicate resolved or unresolved
→ GO / NO_GO / HUMAN_VERIFY
```

## Why `HUMAN_VERIFY` matters

`HUMAN_VERIFY` is the intended result when a consequential predicate cannot be resolved from available independent evidence. It is not a generic refusal and it is not evidence against the decision. It identifies the smallest questions that a human or authoritative source must answer before the gate can safely move to `GO` or `NO_GO`.

The final gate is deterministic:

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
decisiongate evaluate --case cases/database_scaling/case.json --output build/database-scaling
```

Or evaluate files directly:

```bash
decisiongate evaluate \
  --evidence evidence/benchmark.pdf \
  --evidence evidence/production-workload.md \
  --decision "Adopt Database B" \
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

## Using DecisionGate on a government opportunity

A practical DARPA, SBIR/STTR, BAA, Broad Agency Announcement, Special Notice, or other federal opportunity usually begins with a simple question:

> **Do the authoritative documents actually support the decision to spend time and money pursuing this opportunity?**

DecisionGate treats that as an evidence problem rather than a writing problem.

### 1. Collect the authoritative source material

Provide the documents that define the opportunity. Depending on the program, that may include:

- the solicitation, BAA, SBIR/STTR topic, Special Notice, or funding-opportunity PDF;
- amendments and modifications;
- official FAQ or Q&A documents;
- eligibility and submission rules;
- statements of objectives or technical-area descriptions;
- official program presentations or other authoritative clarifications, if available.

If you already have a concept paper, white paper, abstract, or proposal draft, provide that as evidence too. This lets DecisionGate evaluate not only what the government says, but also what you are proposing to do.

Conceptually, the input is:

```text
government requirements
+
your proposed work
+
the decision you are considering
```

For example:

```text
Decision: Submit this white paper to this DARPA program.
```

or:

```text
Decision: Pursue this SBIR topic as the prime small-business applicant.
```

### 2. Run DecisionGate before substantial proposal writing

For a DARPA-style opportunity:

```bash
decisiongate evaluate \
  --provider openai \
  --evidence DARPA_BAA.pdf \
  --evidence DARPA_FAQ.pdf \
  --evidence my_white_paper.pdf \
  --decision "Submit this white paper to this DARPA program" \
  --output build/darpa-review
```

For an SBIR/STTR opportunity:

```bash
decisiongate evaluate \
  --provider openai \
  --evidence sbir_topic.pdf \
  --evidence sbir_eligibility.md \
  --evidence concept.md \
  --decision "Pursue this SBIR topic with this technical concept" \
  --output build/sbir-review
```

The model-assisted path is useful for ordinary unstructured government documents because it can propose predicates, assumptions, and evidence relationships. The model still cannot promote its own interpretation into source evidence: the deterministic DecisionGate layer applies the same trust boundary and final gate rules.

### 3. Read the report as a decision audit

The report is intended to answer questions such as:

- What does the solicitation explicitly say?
- What does my proposal explicitly claim?
- Which requirements clearly match?
- Which conclusions are only inferred from wording similarity?
- What hidden assumptions connect the opportunity to my proposed work?
- What evidence supports those assumptions?
- What evidence contradicts them?
- Which critical predicates remain unresolved?
- What single question could materially change the decision?

Every run writes:

```text
decisiongate-report.json
decisiongate-report.md
```

The Markdown report is the human-facing decision audit. The JSON report preserves the same result in machine-readable form.

### 4. Example: apparent scope fit is not enough

Suppose a government solicitation explicitly mentions **logical QCVV**, and your proposed project also concerns logical QCVV.

A conventional LLM review can easily reason:

```text
Solicitation mentions logical QCVV
+
proposal concerns logical QCVV
=
appears in scope
```

DecisionGate asks what must additionally be true for the submission decision to be justified.

A critical predicate might be:

```text
Independent logical-QCVV methodology is eligible as a primary research objective under this program.
```

The available evidence may establish that logical QCVV is mentioned, while failing to establish whether the program accepts it as a standalone primary objective rather than only as a supporting activity inside another technical effort.

That produces an unresolved assumption rather than a fabricated answer:

```text
Predicate:
Independent logical-QCVV methodology is an eligible primary research topic.

Evidence for:
The solicitation explicitly discusses logical QCVV.

Evidence against:
None currently available.

Hidden assumption:
Mention of logical QCVV means it can be the primary standalone research objective.

Status:
UNRESOLVED

Disposition:
HUMAN_VERIFY
```

The report can then surface a decision-changing question such as:

> Does the program accept independent logical-QCVV methodology as a primary research objective, or only QCVV conducted as part of a broader FTQC development effort?

That question can be sent to the responsible Program Manager **before** substantial proposal effort is committed.

The point is not that DecisionGate can read a Program Manager's undisclosed intent. It cannot. The point is that it should recognize when the available evidence does not justify pretending that intent is already known.

### 5. `GO`, `NO_GO`, and `HUMAN_VERIFY` in this workflow

For government opportunities:

- **`GO`** means every critical predicate represented in the evidence graph is supported by independent evidence.
- **`NO_GO`** means independent evidence refutes at least one critical predicate.
- **`HUMAN_VERIFY`** means a consequential requirement, interpretation, dependency, or scope assumption remains unresolved.

`HUMAN_VERIFY` often has the highest practical value early in a proposal process because it tells you exactly what must be clarified before investing heavily in drafting.

### 6. Deterministic mode versus model-assisted mode

DecisionGate supports two useful workflows.

#### Deterministic / annotated mode

For regression tests, reproducible evaluations, or highly controlled reviews, use explicit annotations:

```text
[PREDICATE scope_fit | CRITICAL] The proposed work is within the program's intended research scope.
[FOR scope_fit | PRIMARY] The solicitation explicitly identifies logical QCVV as an area of interest.
[QUESTION scope_fit] Does this permit logical QCVV as a standalone primary research objective?
```

This mode is highly auditable, but a human must supply the predicate/evidence structure.

#### Model-assisted mode

For a real 20-page, 50-page, or 100-page solicitation, use the optional provider:

```bash
decisiongate evaluate \
  --provider openai \
  --evidence solicitation.pdf \
  --evidence proposal.pdf \
  --decision "Submit this proposal to this research program" \
  --output build/review
```

The model proposes the structure; the deterministic engine adjudicates it. Model consensus is not counted as independent corroboration.

### 7. Important v0.1 limitation

DecisionGate v0.1 analyzes the evidence corpus you supply. It does **not** yet retrieve external program history, prior awards, Program Manager presentations, procurement context, or web evidence automatically.

If those materials matter to the decision, supply them explicitly as evidence. External retrieval with preserved provenance is a planned extension.

This limitation is deliberate: v0.1 would rather return `HUMAN_VERIFY` than invent institutional context that is not present in the evidence corpus.

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

See [docs/annotation-format.md](docs/annotation-format.md) for the complete deterministic input format.

## Two domains, the same failure pattern

### Government-program scope

The applicant saw apparent textual fit, and several LLM-assisted reviews supported submission. Whether the topic was eligible as an independent primary research objective remained unresolved.

**Result: `HUMAN_VERIFY`** — ask the responsible authority to resolve the program-scope interpretation before submitting. See the [QuantumEagle scope case](cases/quantumeagle_scope/README.md).

### Database scaling

A supplied benchmark measured Database B as 35% faster than Database A at approximately 10,000 records. Production may reach approximately 50 million records, and no production-representative benchmark is available. The favorable decision therefore depends on an unresolved scalability assumption.

**Result: `HUMAN_VERIFY`** — benchmark Database B under production-representative scale and workload conditions. See the [database scaling case](cases/database_scaling/README.md).

Neither result claims that the proposed action is wrong. Both expose the same epistemic failure pattern: favorable evidence supports a plausible interpretation, but a decision-critical assumption has not survived falsification.

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

The proponent and challenger views are projections over the same evidence graph. Their prose does not affect the gate, and their agreement is not counted as corroboration. See [docs/architecture.md](docs/architecture.md).

## Current limitations

- The deterministic analyzer expects annotations for domain-specific predicates. It does not claim to understand arbitrary prose.
- The optional model-assisted path compiles predicates in one call in v0.1; isolated proponent/challenger model calls are planned.
- PDF extraction handles text PDFs, not OCR for scanned documents.
- Evidence authority is declared by the input annotation or provider proposal and still requires human scrutiny.
- External retrieval is a future extension point; v0.1 never invents or fetches external facts.
- The system identifies evidence insufficiency. It cannot discover a decision-maker's undisclosed intent.
- DecisionGate does not establish truth from insufficient evidence or replace accountable human judgment.

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
