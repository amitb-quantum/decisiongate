"""Typed domain model for evidence, predicates, and reports."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field, model_validator


class EvidenceType(StrEnum):
    EXPLICIT = "EXPLICIT"
    INFERENCE = "INFERENCE"
    ASSUMPTION = "ASSUMPTION"
    UNKNOWN = "UNKNOWN"
    CONTRADICTED = "CONTRADICTED"


class ProvenanceKind(StrEnum):
    SOURCE_EVIDENCE = "SOURCE_EVIDENCE"
    EXTERNAL_EVIDENCE = "EXTERNAL_EVIDENCE"
    DIRECT_OBSERVATION = "DIRECT_OBSERVATION"
    MODEL_INFERENCE = "MODEL_INFERENCE"
    USER_ASSUMPTION = "USER_ASSUMPTION"
    SYSTEM_UNKNOWN = "SYSTEM_UNKNOWN"


class EvidenceTier(StrEnum):
    PRIMARY_AUTHORITATIVE = "PRIMARY_AUTHORITATIVE"
    DOCUMENTED_EXTERNAL = "DOCUMENTED_EXTERNAL"
    DIRECTLY_OBSERVED = "DIRECTLY_OBSERVED"
    SUPPORTED_INFERENCE = "SUPPORTED_INFERENCE"
    MODEL_INTERPRETATION = "MODEL_INTERPRETATION"
    UNSUPPORTED_SPECULATION = "UNSUPPORTED_SPECULATION"


class PredicateStatus(StrEnum):
    SUPPORTED = "SUPPORTED"
    REFUTED = "REFUTED"
    UNRESOLVED = "UNRESOLVED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class Disposition(StrEnum):
    GO = "GO"
    NO_GO = "NO_GO"
    HUMAN_VERIFY = "HUMAN_VERIFY"


class SourceDocument(BaseModel):
    name: str
    path: str
    content: str


class Claim(BaseModel):
    claim_id: str
    text: str
    source: str
    source_location: str
    evidence_type: EvidenceType
    provenance: ProvenanceKind
    tier: EvidenceTier
    confidence: float = Field(ge=0, le=1)

    @property
    def is_independent_evidence(self) -> bool:
        return (
            self.evidence_type == EvidenceType.EXPLICIT
            and self.provenance
            in {
                ProvenanceKind.SOURCE_EVIDENCE,
                ProvenanceKind.EXTERNAL_EVIDENCE,
                ProvenanceKind.DIRECT_OBSERVATION,
            }
            and self.tier
            in {
                EvidenceTier.PRIMARY_AUTHORITATIVE,
                EvidenceTier.DOCUMENTED_EXTERNAL,
                EvidenceTier.DIRECTLY_OBSERVED,
            }
        )


class Assumption(BaseModel):
    assumption_id: str
    text: str
    predicate_id: str
    consequence: str
    provenance: ProvenanceKind = ProvenanceKind.MODEL_INFERENCE
    confidence: float = Field(default=0.5, ge=0, le=1)
    inverted_hypothesis: str | None = None
    distinguishing_evidence: str | None = None


class Predicate(BaseModel):
    predicate_id: str
    statement: str
    critical: bool = True
    evidence_for: list[str] = Field(default_factory=list)
    evidence_against: list[str] = Field(default_factory=list)
    unresolved_questions: list[str] = Field(default_factory=list)
    status: PredicateStatus = PredicateStatus.UNRESOLVED
    confidence: float = Field(default=0, ge=0, le=1)
    rationale: str = ""


class FalsificationTest(BaseModel):
    assumption_id: str
    favorable_hypothesis: str
    inverted_hypothesis: str
    distinguishing_evidence: str
    result: PredicateStatus = PredicateStatus.UNRESOLVED


class ArgumentView(BaseModel):
    position: str
    propositions: list[str] = Field(default_factory=list)
    evidence_claim_ids: list[str] = Field(default_factory=list)
    caveats: list[str] = Field(default_factory=list)


class Contradiction(BaseModel):
    predicate_id: str
    supporting_claim_ids: list[str]
    opposing_claim_ids: list[str]
    explanation: str


class DecisionReport(BaseModel):
    schema_version: str = "1.0"
    decision: str
    disposition: Disposition
    confidence: float = Field(ge=0, le=1)
    confidence_basis: str
    claims: list[Claim]
    predicates: list[Predicate]
    assumptions: list[Assumption]
    falsification_tests: list[FalsificationTest]
    proponent: ArgumentView
    challenger: ArgumentView
    contradictions: list[Contradiction]
    decision_changing_questions: list[str]
    final_adjudication: str
    warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def unresolved_critical_requires_human_verification(self) -> "DecisionReport":
        unresolved = any(
            p.critical and p.status == PredicateStatus.UNRESOLVED for p in self.predicates
        )
        if unresolved and self.disposition == Disposition.GO:
            raise ValueError("GO is invalid while a critical predicate is unresolved")
        return self
