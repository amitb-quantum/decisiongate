"""Falsification-first orchestration and deterministic gate rules."""

from __future__ import annotations

from pathlib import Path

from decisiongate.analyzer import deterministic_analysis, model_assisted_analysis
from decisiongate.extractor import extract_claims, read_document
from decisiongate.models import (
    ArgumentView,
    Assumption,
    Claim,
    Contradiction,
    DecisionReport,
    Disposition,
    FalsificationTest,
    Predicate,
    PredicateStatus,
)
from decisiongate.providers.base import ModelProvider


class DecisionGate:
    """Evaluate a decision without allowing interpretation to become evidence."""

    def __init__(self, provider: ModelProvider | None = None):
        self.provider = provider

    def evaluate(self, evidence_paths: list[Path], decision: str) -> DecisionReport:
        if not decision.strip():
            raise ValueError("Decision must not be empty")
        if not evidence_paths:
            raise ValueError("At least one evidence document is required")
        documents = [read_document(Path(path)) for path in evidence_paths]
        claims = [claim for document in documents for claim in extract_claims(document)]
        draft = (
            model_assisted_analysis(self.provider, claims, decision)
            if self.provider
            else deterministic_analysis(documents, claims, decision)
        )
        return self.adjudicate(decision, claims, draft.predicates, draft.assumptions)

    @staticmethod
    def adjudicate(
        decision: str,
        claims: list[Claim],
        predicates: list[Predicate],
        assumptions: list[Assumption] | None = None,
    ) -> DecisionReport:
        assumptions = assumptions or []
        claim_map = {claim.claim_id: claim for claim in claims}
        warnings: list[str] = []
        contradictions: list[Contradiction] = []

        for predicate in predicates:
            missing = [
                cid
                for cid in predicate.evidence_for + predicate.evidence_against
                if cid not in claim_map
            ]
            if missing:
                warnings.append(
                    f"Predicate {predicate.predicate_id} referenced unknown claims: {', '.join(missing)}"
                )
            predicate.evidence_for = [cid for cid in predicate.evidence_for if cid in claim_map]
            predicate.evidence_against = [cid for cid in predicate.evidence_against if cid in claim_map]
            independent_for = [cid for cid in predicate.evidence_for if claim_map[cid].is_independent_evidence]
            independent_against = [
                cid for cid in predicate.evidence_against if claim_map[cid].is_independent_evidence
            ]
            if independent_for and independent_against:
                predicate.status = PredicateStatus.UNRESOLVED
                predicate.confidence = 0.25
                predicate.rationale = "Independent evidence conflicts; the contradiction is unresolved."
                contradictions.append(
                    Contradiction(
                        predicate_id=predicate.predicate_id,
                        supporting_claim_ids=independent_for,
                        opposing_claim_ids=independent_against,
                        explanation="Independent evidence supports incompatible conclusions.",
                    )
                )
            elif independent_against:
                predicate.status = PredicateStatus.REFUTED
                predicate.confidence = min(0.99, 0.75 + 0.05 * len(independent_against))
                predicate.rationale = "Independent evidence refutes this predicate."
            elif independent_for:
                predicate.status = PredicateStatus.SUPPORTED
                predicate.confidence = min(0.99, 0.75 + 0.05 * len(independent_for))
                predicate.rationale = "Independent evidence supports this predicate."
            else:
                predicate.status = PredicateStatus.UNRESOLVED
                predicate.confidence = 0.2 if predicate.evidence_for else 0.0
                predicate.rationale = (
                    "Only inference, assumption, or model interpretation supports this predicate."
                    if predicate.evidence_for
                    else "No independent evidence resolves this predicate."
                )
                if predicate.evidence_for:
                    warnings.append(
                        f"Consensus/interpretation for {predicate.predicate_id} was not counted as independent evidence."
                    )

        critical = [p for p in predicates if p.critical and p.status != PredicateStatus.NOT_APPLICABLE]
        if any(p.status == PredicateStatus.REFUTED for p in critical):
            disposition = Disposition.NO_GO
            final = "At least one critical predicate is refuted by independent evidence."
            confidence = min(p.confidence for p in critical if p.status == PredicateStatus.REFUTED)
        elif any(p.status == PredicateStatus.UNRESOLVED for p in critical):
            disposition = Disposition.HUMAN_VERIFY
            final = "One or more critical predicates remain unresolved; obtain authoritative evidence before acting."
            confidence = 0.0
        elif critical and all(p.status == PredicateStatus.SUPPORTED for p in critical):
            disposition = Disposition.GO
            final = "Every critical predicate is supported by independent evidence and none is contradicted."
            confidence = min(p.confidence for p in critical)
        else:
            disposition = Disposition.HUMAN_VERIFY
            final = "No evaluable critical predicate establishes a safe disposition."
            confidence = 0.0

        falsification_tests: list[FalsificationTest] = []
        for assumption in assumptions:
            predicate = next(
                (p for p in predicates if p.predicate_id == assumption.predicate_id), None
            )
            falsification_tests.append(self_test(assumption, predicate))

        questions: list[str] = []
        for predicate in critical:
            if predicate.status in {PredicateStatus.UNRESOLVED, PredicateStatus.REFUTED}:
                questions.extend(predicate.unresolved_questions)
                if not predicate.unresolved_questions:
                    questions.append(f"What authoritative evidence would resolve: {predicate.statement}")
        questions = list(dict.fromkeys(questions))

        proponent_ids = [cid for p in predicates for cid in p.evidence_for]
        challenger_ids = [cid for p in predicates for cid in p.evidence_against]
        proponent = ArgumentView(
            position="FOR",
            propositions=[p.statement for p in predicates if p.evidence_for],
            evidence_claim_ids=list(dict.fromkeys(proponent_ids)),
            caveats=[p.rationale for p in predicates if p.status == PredicateStatus.UNRESOLVED],
        )
        challenger = ArgumentView(
            position="AGAINST",
            propositions=[
                f"The predicate may be false: {p.statement}"
                for p in predicates
                if p.status != PredicateStatus.SUPPORTED
            ],
            evidence_claim_ids=list(dict.fromkeys(challenger_ids)),
            caveats=["Absence of evidence is not affirmative evidence against a predicate."],
        )
        return DecisionReport(
            decision=decision,
            disposition=disposition,
            confidence=confidence,
            confidence_basis=(
                "Confidence is bounded by the weakest critical predicate; unresolved predicates force 0.0."
            ),
            claims=claims,
            predicates=predicates,
            assumptions=assumptions,
            falsification_tests=falsification_tests,
            proponent=proponent,
            challenger=challenger,
            contradictions=contradictions,
            decision_changing_questions=questions,
            final_adjudication=final,
            warnings=warnings,
        )


def self_test(assumption: Assumption, predicate: Predicate | None) -> FalsificationTest:
    return FalsificationTest(
        assumption_id=assumption.assumption_id,
        favorable_hypothesis=assumption.text,
        inverted_hypothesis=(
            assumption.inverted_hypothesis
            or f"A plausible alternative is that the favorable assumption is false: {assumption.text}"
        ),
        distinguishing_evidence=assumption.distinguishing_evidence
        or (
            f"Seek authoritative evidence that directly distinguishes both interpretations of "
            f"predicate {assumption.predicate_id}."
        ),
        result=predicate.status if predicate else PredicateStatus.UNRESOLVED,
    )
