"""Validate the Phase-6 replacement-provider gate without retaining prompts."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


DIGEST = re.compile(r"^[0-9a-f]{64}$")
FORBIDDEN = {"problem_statement", "raw_request", "prompt", "patch", "test_patch", "eval_script"}


class ProviderGateError(ValueError):
    pass


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise ProviderGateError(message)


def check_no_raw(value: object, where: str = "root") -> None:
    if isinstance(value, dict):
        found = FORBIDDEN & set(value)
        expect(not found, f"{where}: forbidden raw-content keys {sorted(found)}")
        for key, child in value.items():
            check_no_raw(child, f"{where}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            check_no_raw(child, f"{where}[{index}]")


def validate(path: Path) -> dict:
    record = json.loads(path.read_text(encoding="utf-8"))
    check_no_raw(record)
    expect(record["schema_version"] == "1.0.0", "unsupported schema")
    expect(record["status"] == "no_candidate_approved_for_benchmark", "unsafe status")
    expect(record["decision_scope"] == "project_research_policy_not_legal_advice", "invalid scope")
    gate = record["gate"]
    expect(gate["maximum_candidates"] == 2, "candidate limit drift")
    expect(gate["synthetic_canary_requires_benchmark_exposure"] is False, "synthetic gate mismatch")
    expect(gate["benchmark_submission_requires_all"] is True, "benchmark gate weakened")

    sources = record["sources"]
    current = sources["current_zen_document"]
    expect(current["commit"] == "bcf1103a8c8653acd7afdd5fc2ebd9f6e5486b3c", "Zen revision drift")
    expect(DIGEST.fullmatch(current["sha256"]) is not None, "malformed Zen digest")
    local = sources["local_cyxcode"]
    expect(local["commit"] == "42676876b63ed5a18957e3318272eb0d875a95fc", "CyxCode revision drift")
    expect(local["current_catalog_drift"] is True, "catalog drift overclaim")
    for key in ("catalog_sha256", "provider_document_sha256", "zen_document_sha256"):
        expect(DIGEST.fullmatch(local[key]) is not None, f"malformed local digest: {key}")

    environment = record["environment"]
    expect(
        environment["credential_names_checked"]
        == [
            "OPENCODE_API_KEY",
            "OPENAI_API_KEY",
            "ANTHROPIC_API_KEY",
            "GOOGLE_GENERATIVE_AI_API_KEY",
            "GEMINI_API_KEY",
            "MISTRAL_API_KEY",
            "ZAI_API_KEY",
        ],
        "credential-check scope drift",
    )
    expect(environment["opencode_api_key_present"] is False, "unrecorded credential admission")
    expect(environment["checked_credential_present"] is False, "unrecorded checked credential")
    expect(environment["local_inference_runtime_present"] is False, "unrecorded local runtime")

    candidates = record["candidates"]
    expect(len(candidates) == gate["maximum_candidates"], "expected exactly two candidates")
    expect({item["candidate_id"] for item in candidates} == {"zen-mimo-v2.5-free", "zen-glm-5.2"}, "candidate mismatch")
    expect(all(item["benchmark_submission"] == "blocked" for item in candidates), "unsafe benchmark admission")
    expect(all(item["preexisting_benchmark_exposure"] == "unknown" for item in candidates), "exposure overclaim")
    expect(all(item["pinned_local_catalog_listing"] is False for item in candidates), "catalog support overclaim")

    mimo = next(item for item in candidates if item["candidate_id"] == "zen-mimo-v2.5-free")
    expect(mimo["cost_class"] == "free", "free-candidate mismatch")
    expect(mimo["prompt_training_use"] == "may_be_used_to_improve_model", "free data-use mismatch")
    expect(mimo["synthetic_canary"] == "blocked_policy", "unsafe free canary")
    expect(mimo["decision"] == "rejected", "unsafe free admission")

    glm = next(item for item in candidates if item["candidate_id"] == "zen-glm-5.2")
    expect(glm["prompt_retention"] == "zero_retention", "GLM retention mismatch")
    expect(glm["prompt_training_use"] == "not_used_for_training", "GLM training-use mismatch")
    expect(glm["model_revision_pinned"] is False, "GLM revision overclaim")
    expect(glm["synthetic_canary"] == "conditional_missing_credential_and_config_pin", "GLM canary overclaim")
    expect(glm["decision"] == "conditional_synthetic_only", "GLM decision mismatch")

    outcome = record["outcome"]
    expect(outcome["candidate_count"] == 2, "outcome count mismatch")
    expect(outcome["free_candidate_approved"] is False, "unsafe free outcome")
    expect(outcome["synthetic_canary_executed"] is False, "unrecorded model execution")
    expect(outcome["benchmark_candidate_approved"] is False, "unsafe benchmark outcome")
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    args = parser.parse_args()
    try:
        record = validate(args.evidence)
    except (OSError, KeyError, TypeError, json.JSONDecodeError, ProviderGateError) as exc:
        print(f"INVALID: {exc}")
        return 1
    print(f"VALID: candidates={len(record['candidates'])}; synthetic_executed=0; benchmark_approved=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
