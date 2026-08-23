"""Model-neutral generator boundary for reproducible repository proposals."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .artifacts import ArtifactError, ArtifactStore, StoredArtifact
from .contracts import TaskContract
from .patches import PatchError, _decode_record
from .snapshots import WorkspaceSnapshot, directory_digest


class GeneratorError(ValueError):
    """Raised when a generator request or proposal violates its boundary."""

    def __init__(
        self,
        message: str,
        *,
        artifacts: tuple[StoredArtifact, ...] = (),
    ) -> None:
        super().__init__(message)
        if not isinstance(artifacts, tuple) or any(
            not isinstance(item, StoredArtifact) for item in artifacts
        ):
            raise TypeError("generator error artifacts must be StoredArtifact records")
        self.artifacts = artifacts


def _text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise GeneratorError(f"{field} must be non-empty text")
    return value


def _text_tuple(value: object, field: str) -> tuple[str, ...]:
    if not isinstance(value, tuple):
        raise GeneratorError(f"{field} must be a tuple")
    items = tuple(_text(item, f"{field}[]") for item in value)
    if len(items) != len(set(items)):
        raise GeneratorError(f"{field} must contain unique values")
    return items


def _digest(value: object, field: str) -> str:
    text = _text(value, field)
    if not text.startswith("sha256:") or len(text) != 71:
        raise GeneratorError(f"{field} must be a sha256 digest")
    try:
        int(text.removeprefix("sha256:"), 16)
    except ValueError as error:
        raise GeneratorError(f"{field} must be a sha256 digest") from error
    return text


@dataclass(frozen=True, slots=True)
class GenerationRequest:
    contract: TaskContract
    revision: str
    source_digest: str
    attempt: int
    feedback: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.contract, TaskContract):
            raise GeneratorError("contract must be a TaskContract")
        revision = _text(self.revision, "revision")
        source_digest = _digest(self.source_digest, "source_digest")
        if isinstance(self.attempt, bool) or not isinstance(self.attempt, int):
            raise GeneratorError("attempt must be a positive integer")
        if self.attempt < 1:
            raise GeneratorError("attempt must be a positive integer")
        if self.attempt == 1:
            if revision != self.contract.repository.revision:
                raise GeneratorError("first request revision must match the task contract")
            if source_digest != self.contract.repository.snapshot_digest:
                raise GeneratorError("first source digest must match the task contract")
        _text_tuple(self.feedback, "feedback")


@dataclass(frozen=True, slots=True)
class GeneratorProposal:
    id: str
    generator_id: str
    revision: str
    attempt: int
    response_artifact_id: str
    patch_artifact_id: str
    claims: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for field in (
            "id",
            "generator_id",
            "revision",
            "response_artifact_id",
            "patch_artifact_id",
        ):
            _text(getattr(self, field), field)
        if isinstance(self.attempt, bool) or not isinstance(self.attempt, int):
            raise GeneratorError("attempt must be a positive integer")
        if self.attempt < 1:
            raise GeneratorError("attempt must be a positive integer")
        _text_tuple(self.claims, "claims")


class GeneratorAdapter(Protocol):
    """Optional adapter implemented by CyxCode or another coding agent."""

    @property
    def generator_id(self) -> str: ...

    def propose(
        self,
        request: GenerationRequest,
        snapshot: WorkspaceSnapshot,
        store: ArtifactStore,
    ) -> GeneratorProposal: ...


@dataclass(frozen=True, slots=True)
class ValidatedProposal:
    request: GenerationRequest
    proposal: GeneratorProposal
    response_artifact: StoredArtifact
    patch_artifact: StoredArtifact
    result_digest: str
    changed_paths: tuple[str, ...]


def validate_proposal(
    request: GenerationRequest,
    proposal: GeneratorProposal,
    snapshot: WorkspaceSnapshot,
    store: ArtifactStore,
    expected_generator_id: str,
) -> ValidatedProposal:
    """Bind a proposal to its request, generator, workspace, and exact artifacts."""

    if not isinstance(request, GenerationRequest):
        raise GeneratorError("request must be a GenerationRequest")
    if not isinstance(proposal, GeneratorProposal):
        raise GeneratorError("proposal must be a GeneratorProposal")
    if not isinstance(snapshot, WorkspaceSnapshot) or snapshot.closed:
        raise GeneratorError("an active WorkspaceSnapshot is required")
    if not isinstance(store, ArtifactStore):
        raise GeneratorError("store must be an ArtifactStore")
    generator_id = _text(expected_generator_id, "expected_generator_id")
    if proposal.generator_id != generator_id:
        raise GeneratorError("proposal uses another generator identity")
    if proposal.revision != request.revision:
        raise GeneratorError("proposal uses another repository revision")
    if proposal.attempt != request.attempt:
        raise GeneratorError("proposal uses another attempt")
    if snapshot.source_digest != request.source_digest:
        raise GeneratorError("workspace does not match the generation request source")

    try:
        response = store.get(proposal.response_artifact_id)
        patch = store.get(proposal.patch_artifact_id)
    except ArtifactError as error:
        raise GeneratorError(str(error)) from error
    if response.kind != "response" or response.size_bytes < 1:
        raise GeneratorError("proposal response artifact is invalid")
    if patch.kind != "patch":
        raise GeneratorError("proposal patch artifact is invalid")
    try:
        record, paths = _decode_record(
            (store.root / patch.path).read_bytes(),
            snapshot.source_digest,
        )
        result_digest = directory_digest(snapshot.root)
        source_digest = directory_digest(snapshot.source_root)
    except (OSError, PatchError) as error:
        raise GeneratorError("proposal patch could not be validated") from error
    if result_digest != record["result_digest"]:
        raise GeneratorError("proposal patch does not match its workspace result")
    if source_digest != snapshot.source_digest:
        raise GeneratorError("source changed during generation")
    return ValidatedProposal(request, proposal, response, patch, result_digest, paths)
