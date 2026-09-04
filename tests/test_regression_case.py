from __future__ import annotations

import json
from pathlib import Path

from decisiongate.engine import DecisionGate
from decisiongate.models import Disposition, ProvenanceKind
from decisiongate.reporting import write_reports


ROOT = Path(__file__).parents[1]


def test_quantumeagle_scope_regression_returns_human_verify(tmp_path: Path) -> None:
    case_path = ROOT / "cases" / "quantumeagle_scope" / "case.json"
    case = json.loads(case_path.read_text(encoding="utf-8"))
    evidence = [case_path.parent / item for item in case["evidence"]]
    report = DecisionGate().evaluate(evidence, case["decision"])

    assert report.disposition == Disposition.HUMAN_VERIFY
    assert report.predicates[0].predicate_id == "semantic_scope_fit"
    assert report.predicates[0].evidence_for
    linked_claim = next(
        claim for claim in report.claims if claim.claim_id == report.predicates[0].evidence_for[0]
    )
    assert linked_claim.tier == "MODEL_INTERPRETATION"
    assert linked_claim.provenance == ProvenanceKind.SOURCE_EVIDENCE
    assert "independent primary research objective" in report.decision_changing_questions[0]

    json_path, markdown_path = write_reports(report, tmp_path)
    assert '"disposition": "HUMAN_VERIFY"' in json_path.read_text(encoding="utf-8")
    rendered = markdown_path.read_text(encoding="utf-8")
    assert "# DecisionGate Report" in rendered
    assert "## Provenance" in rendered

