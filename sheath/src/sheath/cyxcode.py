"""Optional CyxCode execution-to-proposal adapter."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
from typing import Mapping, Protocol

from .artifacts import ArtifactStore
from .generator import GenerationRequest, GeneratorError, GeneratorProposal
from .patches import PatchExtraction
from .snapshots import WorkspaceSnapshot


_PROTECTED_ROOTS = (".cyxcode", ".opencode")


def _digest(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.startswith("sha256:"):
        raise GeneratorError(f"{field} must be a sha256 digest")
    hexadecimal = value.removeprefix("sha256:")
    if len(hexadecimal) != 64:
        raise GeneratorError(f"{field} must be a sha256 digest")
    try:
        int(hexadecimal, 16)
    except ValueError as error:
        raise GeneratorError(f"{field} must be a sha256 digest") from error
    return value


def _canonical(value: object) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        + "\n"
    ).encode("utf-8")


def _redact(value: object, key: str = "") -> object:
    if any(name in key.lower() for name in ("key", "token", "secret", "password", "credential")):
        return "<redacted>"
    if isinstance(value, dict):
        return {name: _redact(item, name) for name, item in value.items()}
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value


def build_cyxcode_prompt(request: GenerationRequest) -> bytes:
    """Encode the complete model-visible task input without conversational state."""

    if not isinstance(request, GenerationRequest):
        raise GeneratorError("request must be a GenerationRequest")
    contract = request.contract
    return _canonical(
        {
            "schema_version": "1.0.0",
            "task_id": contract.task_id,
            "raw_request": contract.raw_request,
            "goal": contract.goal,
            "revision": request.revision,
            "source_digest": request.source_digest,
            "attempt": request.attempt,
            "feedback": list(request.feedback),
            "constraints": [
                {
                    "id": item.id,
                    "kind": item.kind,
                    "text": item.text,
                    "hard": item.hard,
                    "source": item.source,
                }
                for item in contract.constraints
            ],
            "success_criteria": [
                {
                    "id": item.id,
                    "text": item.text,
                    "verification": item.verification,
                }
                for item in contract.success_criteria
            ],
            "out_of_scope": list(contract.out_of_scope),
            "unresolved_questions": list(contract.unresolved_questions),
            "allowed_tools": list(contract.allowed_tools),
            "required_checks": list(contract.required_checks),
        }
    )


@dataclass(frozen=True, slots=True)
class CyxCodeExecution:
    status: str
    response: bytes
    prompt_digest: str
    environment_digest: str
    failure_reason: str | None = None

    def __post_init__(self) -> None:
        if self.status not in {"ok", "failed"}:
            raise GeneratorError("CyxCode status must be ok or failed")
        if not isinstance(self.response, bytes) or not self.response:
            raise GeneratorError("CyxCode response must be non-empty bytes")
        _digest(self.prompt_digest, "prompt_digest")
        _digest(self.environment_digest, "environment_digest")
        if self.status == "failed" and (
            not isinstance(self.failure_reason, str) or not self.failure_reason.strip()
        ):
            raise GeneratorError("failed CyxCode execution requires a failure reason")
        if self.status == "ok" and self.failure_reason is not None:
            raise GeneratorError("successful CyxCode execution cannot have a failure reason")
        try:
            envelope = json.loads(self.response)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise GeneratorError("CyxCode response is not valid JSON") from error
        canonical = (
            json.dumps(
                envelope,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            )
            + "\n"
        ).encode("utf-8")
        if canonical != self.response or not isinstance(envelope, dict):
            raise GeneratorError("CyxCode response is not canonical JSON")
        expected = {
            "schema_version": "1.0.0",
            "status": self.status,
            "prompt_digest": self.prompt_digest,
            "environment_digest": self.environment_digest,
            "failure_reason": self.failure_reason,
        }
        if any(envelope.get(key) != value for key, value in expected.items()):
            raise GeneratorError("CyxCode response envelope does not match its execution")


class CyxCodeExecutor(Protocol):
    def execute(
        self,
        request: GenerationRequest,
        snapshot: WorkspaceSnapshot,
    ) -> CyxCodeExecution: ...


class SubprocessCyxCodeExecutor:
    """Invoke the audited TypeScript runner through one canonical JSON bridge."""

    def __init__(
        self,
        bridge_command: tuple[str, ...],
        cyxcode_command: tuple[str, ...],
        isolation_root: Path,
        model: str,
        config: Mapping[str, object],
        executable_digest: str,
        *,
        variant: str | None = None,
        environment: Mapping[str, str] | None = None,
        timeout_seconds: float = 90,
        max_output_bytes: int = 8 * 1024 * 1024,
    ) -> None:
        for name, command in (
            ("bridge_command", bridge_command),
            ("cyxcode_command", cyxcode_command),
        ):
            if not isinstance(command, tuple) or not command or any(
                not isinstance(item, str) or not item for item in command
            ):
                raise GeneratorError(f"{name} must be a non-empty command tuple")
            if not Path(command[0]).is_absolute():
                raise GeneratorError(f"{name} executable must be absolute")
        if not isinstance(isolation_root, Path) or not isolation_root.is_absolute():
            raise GeneratorError("isolation_root must be an absolute Path")
        if not isinstance(model, str) or not model.strip():
            raise GeneratorError("model must be non-empty text")
        if variant is not None and (not isinstance(variant, str) or not variant.strip()):
            raise GeneratorError("variant must be non-empty text or null")
        if not isinstance(config, Mapping):
            raise GeneratorError("config must be a mapping")
        try:
            frozen_config = json.loads(_canonical(dict(config)))
        except (TypeError, ValueError, json.JSONDecodeError) as error:
            raise GeneratorError("config must be canonical JSON data") from error
        if not isinstance(frozen_config, dict):
            raise GeneratorError("config must encode a JSON object")
        supplied_environment = {} if environment is None else environment
        if not isinstance(supplied_environment, Mapping) or any(
            not isinstance(key, str)
            or not key
            or not isinstance(value, str)
            for key, value in supplied_environment.items()
        ):
            raise GeneratorError("environment must map text names to text values")
        _digest(executable_digest, "executable_digest")
        if (
            isinstance(timeout_seconds, bool)
            or not isinstance(timeout_seconds, (int, float))
            or not math.isfinite(timeout_seconds)
            or timeout_seconds <= 0
        ):
            raise GeneratorError("timeout_seconds must be positive")
        if (
            isinstance(max_output_bytes, bool)
            or not isinstance(max_output_bytes, int)
            or max_output_bytes < 1
        ):
            raise GeneratorError("max_output_bytes must be positive")
        self._bridge = bridge_command
        self._command = cyxcode_command
        self._isolation = isolation_root
        self._model = model
        self._config = frozen_config
        self._digest = executable_digest
        self._variant = variant
        self._environment = dict(sorted(supplied_environment.items()))
        self._timeout = float(timeout_seconds)
        self._maximum = max_output_bytes

    def execute(
        self,
        request: GenerationRequest,
        snapshot: WorkspaceSnapshot,
    ) -> CyxCodeExecution:
        if not isinstance(request, GenerationRequest):
            raise GeneratorError("request must be a GenerationRequest")
        if not isinstance(snapshot, WorkspaceSnapshot) or snapshot.closed:
            raise GeneratorError("an active snapshot is required")
        prompt = build_cyxcode_prompt(request)
        prompt_digest = "sha256:" + hashlib.sha256(prompt).hexdigest()
        self._isolation.mkdir(parents=True, exist_ok=True)
        payload = _canonical(
            {
                "schema_version": "1.0.0",
                "command": list(self._command),
                "cleanup": [*self._command, "cleanup"],
                "snapshot": str(snapshot.root),
                "isolation_root": str(self._isolation),
                "prompt": prompt.decode("utf-8"),
                "prompt_digest": prompt_digest,
                "model": self._model,
                "title": f"sheath-{request.contract.task_id}-a{request.attempt}",
                "variant": self._variant,
                "config": self._config,
                "environment": self._environment,
                "timeout_ms": int(self._timeout * 1000),
                "max_output_bytes": self._maximum,
                "executable_digest": self._digest,
            }
        )
        try:
            result = subprocess.run(
                self._bridge,
                input=payload,
                cwd=snapshot.root,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=False,
                timeout=self._timeout * 2 + 15,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise GeneratorError(f"CyxCode bridge failed: {error}") from error
        if result.returncode != 0:
            detail = result.stderr.decode("utf-8", errors="replace").strip()
            raise GeneratorError(
                f"CyxCode bridge exited {result.returncode}: {detail[:500]}"
            )
        if len(result.stdout) > self._maximum * 3 + 1_048_576:
            raise GeneratorError("CyxCode bridge envelope exceeded its bound")
        try:
            envelope = json.loads(result.stdout)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise GeneratorError("CyxCode bridge returned invalid JSON") from error
        recorded = envelope.get("request") if isinstance(envelope, dict) else None
        expected = {
            "prompt": prompt.decode("utf-8"),
            "model": self._model,
            "title": f"sheath-{request.contract.task_id}-a{request.attempt}",
            "variant": self._variant,
            "config": _redact(self._config),
            "executable_digest": self._digest,
        }
        if recorded != expected:
            raise GeneratorError("CyxCode bridge did not preserve its model-visible input")
        return CyxCodeExecution(
            envelope.get("status"),
            result.stdout,
            prompt_digest,
            envelope.get("environment_digest"),
            envelope.get("failure_reason"),
        )


class TrustedPatchExtractor(Protocol):
    def extract(
        self,
        snapshot: WorkspaceSnapshot,
        store: ArtifactStore,
    ) -> PatchExtraction: ...


def _remove(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.exists():
        shutil.rmtree(path)


def _copy(source: Path, target: Path) -> None:
    if source.is_symlink():
        os.symlink(os.readlink(source), target, target_is_directory=source.is_dir())
    elif source.is_dir():
        shutil.copytree(source, target, symlinks=True)
    elif source.exists():
        shutil.copy2(source, target, follow_symlinks=False)


def restore_cyxcode_metadata(snapshot: WorkspaceSnapshot) -> None:
    """Restore adapter-owned project metadata from the immutable source tree."""

    if not isinstance(snapshot, WorkspaceSnapshot) or snapshot.closed:
        raise GeneratorError("metadata restoration requires an active snapshot")
    for name in _PROTECTED_ROOTS:
        source = snapshot.source_root / name
        target = snapshot.root / name
        try:
            _remove(target)
            _copy(source, target)
        except OSError as error:
            raise GeneratorError(f"could not restore protected CyxCode path: {name}") from error


class CyxCodeGenerator:
    """Compose one CyxCode executor with the existing trusted patch boundary."""

    def __init__(
        self,
        generator_id: str,
        executor: CyxCodeExecutor,
        patch_extractor: TrustedPatchExtractor,
    ) -> None:
        if not isinstance(generator_id, str) or not generator_id.strip():
            raise GeneratorError("generator_id must be non-empty text")
        if not callable(getattr(executor, "execute", None)):
            raise GeneratorError("executor must expose execute")
        if not callable(getattr(patch_extractor, "extract", None)):
            raise GeneratorError("patch_extractor must expose extract")
        self._generator_id = generator_id
        self._executor = executor
        self._patch_extractor = patch_extractor

    @property
    def generator_id(self) -> str:
        return self._generator_id

    def propose(
        self,
        request: GenerationRequest,
        snapshot: WorkspaceSnapshot,
        store: ArtifactStore,
    ) -> GeneratorProposal:
        if not isinstance(request, GenerationRequest):
            raise GeneratorError("request must be a GenerationRequest")
        if not isinstance(snapshot, WorkspaceSnapshot) or snapshot.closed:
            raise GeneratorError("an active WorkspaceSnapshot is required")
        if not isinstance(store, ArtifactStore):
            raise GeneratorError("store must be an ArtifactStore")

        execution = None
        try:
            execution = self._executor.execute(request, snapshot)
            if not isinstance(execution, CyxCodeExecution):
                raise GeneratorError("executor must return CyxCodeExecution")
        finally:
            restore_cyxcode_metadata(snapshot)

        response = store.store_bytes("response", execution.response)
        if execution.status == "failed":
            raise GeneratorError(
                f"CyxCode execution failed: {execution.failure_reason}",
                artifacts=(response,),
            )

        try:
            extraction = self._patch_extractor.extract(snapshot, store)
        except Exception as error:
            raise GeneratorError(
                f"CyxCode patch extraction failed: {error}",
                artifacts=(response,),
            ) from error
        if not isinstance(extraction, PatchExtraction):
            raise GeneratorError(
                "patch_extractor must return PatchExtraction",
                artifacts=(response,),
            )

        material = json.dumps(
            {
                "attempt": request.attempt,
                "generator_id": self.generator_id,
                "patch_artifact_id": extraction.artifact.id,
                "response_artifact_id": response.id,
                "revision": request.revision,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        proposal_id = "proposal:cyxcode:" + hashlib.sha256(material).hexdigest()
        return GeneratorProposal(
            proposal_id,
            self.generator_id,
            request.revision,
            request.attempt,
            response.id,
            extraction.artifact.id,
            (),
        )
