"""Local document loading and provenance-preserving claim extraction."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from pypdf import PdfReader

from decisiongate.models import (
    Claim,
    EvidenceTier,
    EvidenceType,
    ProvenanceKind,
    SourceDocument,
)

ANNOTATION = re.compile(
    r"^\s*(?:[-*]\s*)?\[(?P<tag>[A-Z_]+)(?:\s+(?P<target>[\w.-]+))?"
    r"(?:\s*\|\s*(?P<qualifier>[A-Z_]+))?\]\s*(?P<text>.+?)\s*$"
)


def read_document(path: Path) -> SourceDocument:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        pages = [page.extract_text() or "" for page in PdfReader(path).pages]
        content = "\n\f\n".join(pages)
    elif suffix in {".txt", ".md"}:
        content = path.read_text(encoding="utf-8")
    else:
        raise ValueError(f"Unsupported evidence format {suffix!r}: {path}")
    return SourceDocument(name=path.name, path=str(path.resolve()), content=content)


def stable_claim_id(source: str, location: str, text: str) -> str:
    digest = hashlib.sha256(f"{source}|{location}|{text}".encode()).hexdigest()[:10]
    return f"claim-{digest}"


def extract_claims(document: SourceDocument) -> list[Claim]:
    """Extract source statements; annotations classify but do not change their text."""
    claims: list[Claim] = []
    for line_number, raw in enumerate(document.content.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        match = ANNOTATION.match(line)
        tag = match.group("tag") if match else "EXPLICIT"
        if tag in {"PREDICATE", "QUESTION", "INVERSION"}:
            continue
        text = match.group("text") if match else line.lstrip("-* ")
        qualifier = match.group("qualifier") if match else None
        evidence_type = {
            "INFERENCE": EvidenceType.INFERENCE,
            "ASSUMPTION": EvidenceType.ASSUMPTION,
            "UNKNOWN": EvidenceType.UNKNOWN,
            "CONTRADICTED": EvidenceType.CONTRADICTED,
        }.get(tag, EvidenceType.EXPLICIT)
        provenance = {
            EvidenceType.INFERENCE: ProvenanceKind.MODEL_INFERENCE,
            EvidenceType.ASSUMPTION: ProvenanceKind.USER_ASSUMPTION,
            EvidenceType.UNKNOWN: ProvenanceKind.SYSTEM_UNKNOWN,
        }.get(evidence_type, ProvenanceKind.SOURCE_EVIDENCE)
        if qualifier == "EXTERNAL":
            provenance = ProvenanceKind.EXTERNAL_EVIDENCE
        elif qualifier == "OBSERVED":
            provenance = ProvenanceKind.DIRECT_OBSERVATION
        tier = {
            "PRIMARY": EvidenceTier.PRIMARY_AUTHORITATIVE,
            "EXTERNAL": EvidenceTier.DOCUMENTED_EXTERNAL,
            "OBSERVED": EvidenceTier.DIRECTLY_OBSERVED,
            "MODEL": EvidenceTier.MODEL_INTERPRETATION,
            "SPECULATION": EvidenceTier.UNSUPPORTED_SPECULATION,
        }.get(qualifier, EvidenceTier.DOCUMENTED_EXTERNAL)
        if evidence_type == EvidenceType.INFERENCE:
            tier = EvidenceTier.MODEL_INTERPRETATION
        elif evidence_type in {EvidenceType.ASSUMPTION, EvidenceType.UNKNOWN}:
            tier = EvidenceTier.UNSUPPORTED_SPECULATION
        location = f"line {line_number}"
        claims.append(
            Claim(
                claim_id=stable_claim_id(document.name, location, text),
                text=text,
                source=document.name,
                source_location=location,
                evidence_type=evidence_type,
                provenance=provenance,
                tier=tier,
                confidence=1.0 if evidence_type == EvidenceType.EXPLICIT else 0.5,
            )
        )
    return claims
