import unittest

from sheath import (
    Evidence,
    EvidenceLedger,
    Finding,
    Severity,
    Verdict,
    decide,
    task_contract_from_record,
)

from fixtures import task_record


def passing_ledger() -> EvidenceLedger:
    ledger = EvidenceLedger("r1")
    ledger.record_evidence(Evidence("ev-scope", "scope.paths", "r1", True, "rule"))
    ledger.record_evidence(
        Evidence("ev-tests", "tests.regression", "r1", True, "tool")
    )
    return ledger


class DecisionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = task_contract_from_record(task_record())

    def test_accepts_only_with_all_current_passing_evidence(self) -> None:
        result = decide(self.contract, passing_ledger())

        self.assertEqual(result.verdict, Verdict.ACCEPT)
        self.assertEqual(result.evidence_ids, ("ev-scope", "ev-tests"))

    def test_requires_revision_for_missing_check(self) -> None:
        ledger = EvidenceLedger("r1")
        ledger.record_evidence(Evidence("ev-scope", "scope.paths", "r1", True, "rule"))

        result = decide(self.contract, ledger)

        self.assertEqual(result.verdict, Verdict.REVISE)
        self.assertIn("mandatory_check.missing:tests.regression", result.reason_codes)

    def test_latest_current_failure_overrides_earlier_pass(self) -> None:
        ledger = passing_ledger()
        ledger.record_evidence(
            Evidence("ev-tests-2", "tests.regression", "r1", False, "tool")
        )

        result = decide(self.contract, ledger)

        self.assertEqual(result.verdict, Verdict.REVISE)
        self.assertIn("mandatory_check.failed:tests.regression", result.reason_codes)
        self.assertIn("ev-tests-2", result.evidence_ids)

    def test_revision_invalidates_all_prior_checks(self) -> None:
        ledger = passing_ledger()
        ledger.record_revision("r2")

        result = decide(self.contract, ledger)

        self.assertEqual(result.verdict, Verdict.REVISE)
        self.assertEqual(
            set(result.reason_codes),
            {
                "mandatory_check.stale:scope.paths",
                "mandatory_check.stale:tests.regression",
            },
        )

    def test_blocking_finding_has_precedence(self) -> None:
        ledger = passing_ledger()
        ledger.record_evidence(
            Evidence("ev-policy", "policy.command", "r1", False, "policy")
        )
        finding = Finding(
            id="finding-policy",
            category="unsafe_action",
            severity=Severity.BLOCKING,
            message="The requested command is forbidden.",
            evidence_ids=("ev-policy",),
        )

        result = decide(self.contract, ledger, (finding,))

        self.assertEqual(result.verdict, Verdict.BLOCK)
        self.assertEqual(result.reason_codes, ("finding.blocking:finding-policy",))

    def test_dangling_finding_evidence_escalates(self) -> None:
        finding = Finding(
            id="finding-unknown",
            category="evidence_gap",
            severity=Severity.REVISION,
            message="This finding cites an unknown observation.",
            evidence_ids=("ev-does-not-exist",),
        )

        result = decide(self.contract, passing_ledger(), (finding,))

        self.assertEqual(result.verdict, Verdict.ESCALATE)
        self.assertEqual(
            result.reason_codes,
            ("finding.unknown_evidence:finding-unknown:ev-does-not-exist",),
        )

    def test_unresolved_material_question_escalates(self) -> None:
        record = task_record()
        record["unresolved_questions"] = ["May the public API change?"]
        contract = task_contract_from_record(record)

        result = decide(contract, passing_ledger())

        self.assertEqual(result.verdict, Verdict.ESCALATE)
        self.assertEqual(result.reason_codes, ("contract.unresolved_material_question",))

    def test_contract_without_checks_cannot_be_accepted(self) -> None:
        record = task_record()
        record["required_checks"] = []
        contract = task_contract_from_record(record)

        result = decide(contract, EvidenceLedger("r1"))

        self.assertEqual(result.verdict, Verdict.ESCALATE)
        self.assertEqual(result.reason_codes, ("contract.no_required_checks",))

    def test_reverification_after_revision_restores_acceptance(self) -> None:
        ledger = passing_ledger()
        ledger.record_revision("r2")
        ledger.record_evidence(Evidence("ev-scope-r2", "scope.paths", "r2", True, "rule"))
        ledger.record_evidence(
            Evidence("ev-tests-r2", "tests.regression", "r2", True, "tool")
        )

        result = decide(self.contract, ledger)

        self.assertEqual(result.verdict, Verdict.ACCEPT)
        self.assertEqual(result.evidence_ids, ("ev-scope-r2", "ev-tests-r2"))

    def test_finding_rejects_untyped_severity(self) -> None:
        with self.assertRaisesRegex(TypeError, "Severity"):
            Finding(
                id="finding-1",
                category="unsafe_action",
                severity="blocking",  # type: ignore[arg-type]
                message="Unsafe action.",
            )


if __name__ == "__main__":
    unittest.main()
