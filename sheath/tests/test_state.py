import unittest

from sheath import (
    Decision,
    EvidenceLedger,
    RunState,
    RunStateMachine,
    StateError,
    Verdict,
)


def reach_assessed(machine: RunStateMachine) -> None:
    for state in (
        RunState.CONTRACTED,
        RunState.TRIAGED,
        RunState.PROPOSED,
        RunState.ACTION_VALIDATION,
        RunState.EXECUTED,
        RunState.ASSESSED,
    ):
        machine.transition(state)


class StateMachineTests(unittest.TestCase):
    def test_records_valid_path_in_shared_ledger(self) -> None:
        ticks = iter(f"2026-08-14T00:00:{second:02d}Z" for second in range(20))
        ledger = EvidenceLedger("r1", clock=lambda: next(ticks))
        machine = RunStateMachine(ledger)

        reach_assessed(machine)
        machine.apply_decision(Decision(Verdict.ACCEPT, ("ok",), ()))
        machine.transition(RunState.EXPORTED)

        self.assertEqual(machine.state, RunState.EXPORTED)
        self.assertEqual(machine.transitions[0].from_state, None)
        self.assertEqual(machine.transitions[-1].to_state, RunState.EXPORTED)
        self.assertEqual(
            [event.sequence for event in ledger.events],
            list(range(len(ledger.events))),
        )

    def test_rejects_invalid_transition(self) -> None:
        machine = RunStateMachine(EvidenceLedger("r1"))

        with self.assertRaisesRegex(StateError, "received -> verified"):
            machine.transition(RunState.VERIFIED)

    def test_revision_returns_to_proposal(self) -> None:
        machine = RunStateMachine(EvidenceLedger("r1"))
        reach_assessed(machine)

        machine.apply_decision(Decision(Verdict.REVISE, ("missing",), ()))
        machine.transition(RunState.PROPOSED)

        self.assertEqual(machine.state, RunState.PROPOSED)

    def test_revision_can_export_when_attempt_budget_is_exhausted(self) -> None:
        machine = RunStateMachine(EvidenceLedger("r1"))
        reach_assessed(machine)

        machine.apply_decision(Decision(Verdict.REVISE, ("missing",), ()))
        machine.transition(RunState.EXPORTED)

        self.assertEqual(machine.state, RunState.EXPORTED)

    def test_decision_requires_assessed_state(self) -> None:
        machine = RunStateMachine(EvidenceLedger("r1"))

        with self.assertRaisesRegex(StateError, "only from assessed"):
            machine.apply_decision(Decision(Verdict.BLOCK, ("policy",), ()))


if __name__ == "__main__":
    unittest.main()
