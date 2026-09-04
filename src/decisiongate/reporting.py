"""Machine-readable and human-readable report rendering."""

from __future__ import annotations

from pathlib import Path

from decisiongate.models import DecisionReport, EvidenceType, PredicateStatus


def write_reports(report: DecisionReport, output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "decisiongate-report.json"
    markdown_path = output_dir / "decisiongate-report.md"
    json_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    markdown_path.write_text(render_markdown(report), encoding="utf-8")
    return json_path, markdown_path


def render_markdown(report: DecisionReport) -> str:
    def bullets(values: list[str], empty: str = "None.") -> str:
        return "\n".join(f"- {value}" for value in values) if values else empty

    explicit = [
        f"`{c.claim_id}` — {c.text} _({c.source}, {c.source_location}; {c.tier})_"
        for c in report.claims
        if c.evidence_type == EvidenceType.EXPLICIT
    ]
    predicate_lines = [
        f"- **{p.predicate_id} — {p.status}** ({'critical' if p.critical else 'noncritical'}, "
        f"confidence {p.confidence:.2f}): {p.statement}\n  - {p.rationale}"
        for p in report.predicates
    ]
    assumptions = [f"{a.text} → {a.consequence}" for a in report.assumptions]
    for_lines = [
        f"`{cid}` — {next(c.text for c in report.claims if c.claim_id == cid)}"
        for cid in report.proponent.evidence_claim_ids
    ]
    against_lines = [
        f"`{cid}` — {next(c.text for c in report.claims if c.claim_id == cid)}"
        for cid in report.challenger.evidence_claim_ids
    ]
    tests = [
        f"**Inversion:** {t.inverted_hypothesis}  \n**Distinguishing evidence:** "
        f"{t.distinguishing_evidence}  \n**Result:** {t.result}"
        for t in report.falsification_tests
    ]
    unresolved = [p.statement for p in report.predicates if p.status == PredicateStatus.UNRESOLVED]
    contradictions = [c.explanation + f" (`{c.predicate_id}`)" for c in report.contradictions]
    provenance = [
        f"`{c.claim_id}`: **{c.provenance} / {c.evidence_type}** — {c.source}, {c.source_location}"
        for c in report.claims
    ]
    warning_section = f"\n## Warnings\n\n{bullets(report.warnings)}\n" if report.warnings else ""
    return f"""# DecisionGate Report

## Decision

{report.decision}

## Disposition

**{report.disposition}**

Confidence: **{report.confidence:.2f}**  
{report.confidence_basis}

## Explicit Evidence

{bullets(explicit)}

## Decision Predicates

{chr(10).join(predicate_lines) if predicate_lines else 'None.'}

## Hidden Assumptions

{bullets(assumptions)}

## Evidence Supporting Decision

{bullets(for_lines)}

## Evidence Against Decision

{bullets(against_lines)}

## Falsification Tests

{bullets(tests)}

## Unresolved Predicates

{bullets(unresolved)}

## Contradictions

{bullets(contradictions)}

## Decision-Changing Questions

{bullets(report.decision_changing_questions)}

## Final Adjudication

{report.final_adjudication}

## Provenance

{bullets(provenance)}
{warning_section}
"""
