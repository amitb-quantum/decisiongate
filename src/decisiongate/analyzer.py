"""Compile deterministic annotations or isolated model-produced structure into analysis."""

from __future__ import annotations

import json
from collections import defaultdict
from typing import Any

from pydantic import BaseModel, Field

from decisiongate.extractor import ANNOTATION
from decisiongate.models import Assumption, Claim, Predicate, ProvenanceKind, SourceDocument
from decisiongate.providers.base import ModelProvider


class AnalysisDraft(BaseModel):
    predicates: list[Predicate]
    assumptions: list[Assumption] = Field(default_factory=list)


def deterministic_analysis(
    documents: list[SourceDocument], claims: list[Claim], decision: str
) -> AnalysisDraft:
    claim_by_location = {(c.source, c.source_location): c for c in claims}
    predicate_specs: dict[str, tuple[str, bool]] = {}
    support: dict[str, list[str]] = defaultdict(list)
    oppose: dict[str, list[str]] = defaultdict(list)
    questions: dict[str, list[str]] = defaultdict(list)
    inversions: dict[str, str] = {}
    assumptions: list[Assumption] = []
    assumption_count = 0

    for doc in documents:
        for line_number, raw in enumerate(doc.content.splitlines(), start=1):
            match = ANNOTATION.match(raw.strip())
            if not match:
                continue
            tag, target = match.group("tag"), match.group("target")
            qualifier, text = match.group("qualifier"), match.group("text")
            if tag == "PREDICATE" and target:
                predicate_specs[target] = (text, qualifier != "NONCRITICAL")
            elif tag == "QUESTION" and target:
                questions[target].append(text)
            elif tag == "INVERSION" and target:
                inversions[target] = text
            elif tag in {"FOR", "AGAINST"} and target:
                claim = claim_by_location.get((doc.name, f"line {line_number}"))
                if claim:
                    (support if tag == "FOR" else oppose)[target].append(claim.claim_id)
            elif tag == "ASSUMPTION" and target:
                assumption_count += 1
                assumptions.append(
                    Assumption(
                        assumption_id=f"assumption-{assumption_count}",
                        text=text,
                        predicate_id=target,
                        consequence=f"The decision may fail if {target} is false.",
                        provenance=ProvenanceKind.USER_ASSUMPTION,
                    )
                )

    if not predicate_specs:
        predicate_specs["decision_evidentiary_basis"] = (
            f"Available evidence is sufficient to justify: {decision}",
            True,
        )
        questions["decision_evidentiary_basis"].append(
            "What independent authoritative evidence directly establishes the decision's critical requirements?"
        )

    predicates = [
        Predicate(
            predicate_id=predicate_id,
            statement=statement,
            critical=critical,
            evidence_for=support[predicate_id],
            evidence_against=oppose[predicate_id],
            unresolved_questions=questions[predicate_id],
        )
        for predicate_id, (statement, critical) in predicate_specs.items()
    ]
    for assumption in assumptions:
        assumption.inverted_hypothesis = inversions.get(assumption.predicate_id)
        related_questions = questions.get(assumption.predicate_id, [])
        if related_questions:
            assumption.distinguishing_evidence = related_questions[0]
    return AnalysisDraft(predicates=predicates, assumptions=assumptions)


def model_assisted_analysis(
    provider: ModelProvider,
    claims: list[Claim],
    decision: str,
) -> AnalysisDraft:
    """Ask a model for structure while limiting it to existing evidence IDs."""
    allowed_claims = [
        {
            "claim_id": claim.claim_id,
            "text": claim.text,
            "evidence_type": claim.evidence_type,
            "provenance": claim.provenance,
            "tier": claim.tier,
        }
        for claim in claims
    ]
    system = (
        "Compile decision predicates and hidden assumptions. Treat only supplied claim IDs as evidence. "
        "Semantic similarity is not scope proof. Preserve uncertainty, identify critical predicates, "
        "and include the smallest decision-changing questions. Never invent claim IDs."
    )
    payload: dict[str, Any] = provider.complete_json(
        purpose="compile_analysis",
        system_prompt=system,
        user_prompt=json.dumps({"decision": decision, "claims": allowed_claims}, default=str),
        json_schema=AnalysisDraft.model_json_schema(),
    )
    draft = AnalysisDraft.model_validate(payload)
    allowed_ids = {claim.claim_id for claim in claims}
    for predicate in draft.predicates:
        predicate.evidence_for = [cid for cid in predicate.evidence_for if cid in allowed_ids]
        predicate.evidence_against = [cid for cid in predicate.evidence_against if cid in allowed_ids]
    return draft
