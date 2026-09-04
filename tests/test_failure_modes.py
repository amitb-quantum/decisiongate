from __future__ import annotations

from pathlib import Path

import pytest

from decisiongate.engine import DecisionGate
from decisiongate.extractor import extract_claims, read_document
from decisiongate.models import Disposition, PredicateStatus
from decisiongate.providers.deterministic import DeterministicProvider


def evaluate(tmp_path: Path, content: str):
    evidence = tmp_path / "evidence.md"
    evidence.write_text(content.strip() + "\n", encoding="utf-8")
    return DecisionGate().evaluate([evidence], "Take the proposed action")


def test_clear_independent_evidence_supports_go(tmp_path: Path) -> None:
    report = evaluate(
        tmp_path,
        """
        [PREDICATE eligibility | CRITICAL] The applicant is eligible.
        [FOR eligibility | PRIMARY] The official register lists the applicant as eligible.
        """,
    )
    assert report.disposition == Disposition.GO
    assert report.predicates[0].status == PredicateStatus.SUPPORTED


def test_clear_independent_evidence_supports_no_go(tmp_path: Path) -> None:
    report = evaluate(
        tmp_path,
        """
        [PREDICATE eligibility | CRITICAL] The applicant is eligible.
        [AGAINST eligibility | PRIMARY] The official register lists the applicant as ineligible.
        """,
    )
    assert report.disposition == Disposition.NO_GO
    assert report.predicates[0].status == PredicateStatus.REFUTED


def test_semantic_alignment_with_hidden_assumption_requires_verification(tmp_path: Path) -> None:
    report = evaluate(
        tmp_path,
        """
        [PREDICATE scope_fit | CRITICAL] The work is an eligible primary objective.
        [ASSUMPTION scope_fit] Mention of a related technique makes it an eligible primary objective.
        [QUESTION scope_fit] Does the authority permit this as a primary objective?
        """,
    )
    assert report.disposition == Disposition.HUMAN_VERIFY
    assert len(report.assumptions) == 1
    assert report.falsification_tests[0].result == PredicateStatus.UNRESOLVED
    assert report.decision_changing_questions == [
        "Does the authority permit this as a primary objective?"
    ]


def test_conflicting_sources_create_contradiction(tmp_path: Path) -> None:
    report = evaluate(
        tmp_path,
        """
        [PREDICATE compatibility | CRITICAL] The components are compatible.
        [FOR compatibility | PRIMARY] Specification A states the components are compatible.
        [AGAINST compatibility | OBSERVED] The integration test shows they are incompatible.
        """,
    )
    assert report.disposition == Disposition.HUMAN_VERIFY
    assert report.predicates[0].status == PredicateStatus.UNRESOLVED
    assert len(report.contradictions) == 1


def test_provider_cannot_invent_evidence_claim_ids(tmp_path: Path) -> None:
    evidence = tmp_path / "source.md"
    evidence.write_text("A source makes an unrelated statement.\n", encoding="utf-8")
    provider = DeterministicProvider(
        {
            "compile_analysis": [
                {
                    "predicates": [
                        {
                            "predicate_id": "safety",
                            "statement": "The action is safe.",
                            "critical": True,
                            "evidence_for": ["claim-invented-by-model"],
                            "unresolved_questions": ["What test demonstrates safety?"],
                        }
                    ],
                    "assumptions": [],
                }
            ]
        }
    )
    report = DecisionGate(provider=provider).evaluate([evidence], "Perform the action")
    assert provider.calls == ["compile_analysis"]
    assert report.predicates[0].evidence_for == []
    assert report.disposition == Disposition.HUMAN_VERIFY


def test_provider_proposed_support_link_cannot_authorize_go(tmp_path: Path) -> None:
    evidence = tmp_path / "source.md"
    evidence.write_text("The official register lists the applicant as eligible.\n", encoding="utf-8")
    claims = extract_claims(read_document(evidence))
    provider = DeterministicProvider(
        {
            "compile_analysis": [
                {
                    "predicates": [
                        {
                            "predicate_id": "eligibility",
                            "statement": "The applicant is eligible.",
                            "critical": True,
                            "evidence_for": [claims[0].claim_id],
                            "unresolved_questions": [
                                "Does the authoritative eligibility rule apply to this applicant?"
                            ],
                        }
                    ],
                    "assumptions": [],
                }
            ]
        }
    )

    report = DecisionGate(provider=provider).evaluate([evidence], "Submit the application")

    assert report.disposition == Disposition.HUMAN_VERIFY
    assert report.predicates[0].status == PredicateStatus.UNRESOLVED
    assert any("model-proposed" in warning.lower() for warning in report.warnings)


def test_provider_proposed_refutation_link_cannot_authorize_no_go(tmp_path: Path) -> None:
    evidence = tmp_path / "source.md"
    evidence.write_text("No production-scale benchmark is available.\n", encoding="utf-8")
    claims = extract_claims(read_document(evidence))
    provider = DeterministicProvider(
        {
            "compile_analysis": [
                {
                    "predicates": [
                        {
                            "predicate_id": "scale_fit",
                            "statement": "Small-scale performance generalizes to production scale.",
                            "critical": True,
                            "evidence_against": [claims[0].claim_id],
                            "unresolved_questions": [
                                "Has performance been tested at production-representative scale?"
                            ],
                        }
                    ],
                    "assumptions": [],
                }
            ]
        }
    )

    report = DecisionGate(provider=provider).evaluate([evidence], "Adopt Database B")

    assert report.disposition == Disposition.HUMAN_VERIFY
    assert report.predicates[0].status == PredicateStatus.UNRESOLVED
    assert report.decision_changing_questions == [
        "Has performance been tested at production-representative scale?"
    ]


def test_model_consensus_is_not_independent_evidence(tmp_path: Path) -> None:
    report = evaluate(
        tmp_path,
        """
        [PREDICATE feasible | CRITICAL] The plan is feasible.
        [FOR feasible | MODEL] Model A predicts success.
        [FOR feasible | MODEL] Model B predicts success.
        [FOR feasible | MODEL] Model C predicts success.
        """,
    )
    assert report.disposition == Disposition.HUMAN_VERIFY
    assert report.predicates[0].status == PredicateStatus.UNRESOLVED
    assert any("not counted as independent evidence" in warning for warning in report.warnings)


def test_unverified_external_dependency_requires_verification(tmp_path: Path) -> None:
    report = evaluate(
        tmp_path,
        """
        [PREDICATE vendor_api | CRITICAL] The vendor API supports the required throughput.
        [QUESTION vendor_api] Will the vendor contractually guarantee the required throughput?
        """,
    )
    assert report.disposition == Disposition.HUMAN_VERIFY
    assert report.confidence == 0.0


def test_missing_structured_evidence_defaults_to_human_verify(tmp_path: Path) -> None:
    report = evaluate(tmp_path, "The proposal sounds compelling and uses relevant terminology.")
    assert report.disposition == Disposition.HUMAN_VERIFY
    assert report.predicates[0].predicate_id == "decision_evidentiary_basis"


def test_empty_decision_and_evidence_are_rejected(tmp_path: Path) -> None:
    source = tmp_path / "source.txt"
    source.write_text("data", encoding="utf-8")
    with pytest.raises(ValueError, match="Decision"):
        DecisionGate().evaluate([source], "")
    with pytest.raises(ValueError, match="evidence"):
        DecisionGate().evaluate([], "Act")
