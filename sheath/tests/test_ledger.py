import unittest

from sheath import Evidence, EvidenceLedger, LedgerError


class LedgerTests(unittest.TestCase):
    def test_revision_makes_prior_evidence_stale_without_deleting_it(self) -> None:
        ledger = EvidenceLedger("r1")
        evidence = Evidence("ev-1", "tests.regression", "r1", True, "tool")
        ledger.record_evidence(evidence)

        ledger.record_revision("r2")

        self.assertEqual(ledger.evidence_for("tests.regression"), ())
        self.assertEqual(ledger.evidence_for("tests.regression", current_only=False), (evidence,))
        self.assertEqual(len(ledger.events), 3)

    def test_rejects_duplicate_evidence_id(self) -> None:
        ledger = EvidenceLedger("r1")
        evidence = Evidence("ev-1", "scope.paths", "r1", True, "rule")
        ledger.record_evidence(evidence)

        with self.assertRaisesRegex(LedgerError, "duplicate"):
            ledger.record_evidence(evidence)

    def test_rejects_evidence_for_noncurrent_revision(self) -> None:
        ledger = EvidenceLedger("r1")

        with self.assertRaisesRegex(LedgerError, "current revision"):
            ledger.record_evidence(
                Evidence("ev-future", "tests.regression", "r2", True, "tool")
            )

    def test_records_proposal_artifact_at_current_revision(self) -> None:
        ledger = EvidenceLedger("r1")

        event = ledger.record_proposal(
            "proposal-1",
            "artifact:response:" + "1" * 64,
        )

        self.assertEqual(event.kind, "proposal")
        self.assertEqual(event.revision, "r1")
        self.assertEqual(event.proposal_id, "proposal-1")
        self.assertEqual(event.content_artifact_id, "artifact:response:" + "1" * 64)
        self.assertEqual(event.status, "recorded")

    def test_rejects_duplicate_or_invalid_proposal_event(self) -> None:
        ledger = EvidenceLedger("r1")
        ledger.record_proposal("proposal-1", "artifact:response:one")

        with self.assertRaisesRegex(LedgerError, "duplicate proposal"):
            ledger.record_proposal("proposal-1", "artifact:response:two")
        with self.assertRaisesRegex(LedgerError, "proposal_id"):
            ledger.record_proposal("", "artifact:response:three")


if __name__ == "__main__":
    unittest.main()
