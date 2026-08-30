"""Validate the accepted one-shot llmster archive-acquisition result."""

from __future__ import annotations

import argparse
from functools import lru_cache
import hashlib
import json
import re
from pathlib import Path

try:
    from .validate_llmster_storage_policy_superseding_decision import (
        validate as validate_authorization,
    )
except ImportError:
    from validate_llmster_storage_policy_superseding_decision import (
        validate as validate_authorization,
    )


DIGEST = re.compile(r"^[0-9a-f]{64}$")
SHA512 = re.compile(r"^[0-9a-f]{128}$")
COMMIT = re.compile(r"^[0-9a-f]{40}$")
FORBIDDEN = {
    "hostname",
    "machine_id",
    "serial_number",
    "username",
    "resolved_ip",
    "credential",
    "api_token",
    "problem_statement",
    "raw_prompt",
    "raw_response",
    "patch",
    "test_patch",
    "eval_script",
}


class LlmsterArchiveAcquisitionResultError(ValueError):
    pass


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise LlmsterArchiveAcquisitionResultError(message)


def check_forbidden(value: object, where: str = "root") -> None:
    if isinstance(value, dict):
        found = FORBIDDEN & set(value)
        expect(not found, f"{where}: forbidden keys {sorted(found)}")
        for key, child in value.items():
            check_forbidden(child, f"{where}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            check_forbidden(child, f"{where}[{index}]")


def file_identity(path: Path) -> dict[str, int | str]:
    content = path.read_bytes()
    return {
        "bytes": len(content),
        "lines": len(content.decode("utf-8").splitlines()),
        "sha256": hashlib.sha256(content).hexdigest(),
    }


@lru_cache(maxsize=1)
def archive_identity(path_text: str) -> dict[str, int | str]:
    path = Path(path_text)
    sha256 = hashlib.sha256()
    sha512 = hashlib.sha512()
    total = 0
    with path.open("rb") as source:
        while chunk := source.read(8 * 1024 * 1024):
            total += len(chunk)
            sha256.update(chunk)
            sha512.update(chunk)
    return {"bytes": total, "sha256": sha256.hexdigest(), "sha512": sha512.hexdigest()}


def validate(path: Path) -> dict:
    record = json.loads(path.read_text(encoding="utf-8"))
    check_forbidden(record)
    expect(record["schema_version"] == "1.0.0", "unsupported schema")
    expect(
        record["status"] == "llmster_archive_acquired_verified_extraction_blocked",
        "unsafe status",
    )
    expect(
        record["result_scope"]
        == "one_authorized_archive_request_and_identity_verification_without_inventory_extraction_installation_or_runtime",
        "invalid result scope",
    )
    expect(record["recorded_at"].endswith("Z"), "timestamp must be UTC")
    expect(COMMIT.fullmatch(record["baseline_commit"]) is not None, "malformed baseline commit")
    expect(
        record["baseline_commit"] == "f78217f63be86ca0ae0b9609f14e6e23aa810489",
        "baseline commit drift",
    )

    base = path.parent
    authorization = record["authorization"]
    expect(
        authorization["record"] == "phase6_llmster_storage_policy_superseding_decision.json",
        "authorization record drift",
    )
    authorization_path = base / authorization["record"]
    expect(
        hashlib.sha256(authorization_path.read_bytes()).hexdigest() == authorization["sha256"],
        "authorization digest drift",
    )
    decision = validate_authorization(authorization_path)
    expect(authorization["status"] == decision["status"], "authorization status drift")
    for key in ("validated_immediately_before_function_call", "consumed"):
        expect(authorization[key] is True, f"authorization state concealed: {key}")
    expect(authorization["function_invocation_count"] == 1, "invocation count drift")
    expect(authorization["automatic_retry_count"] == 0, "retry admitted")
    expect(authorization["further_request_authorized"] is False, "further request admitted")

    module = record["module_identity"]
    expect(module["path"] == "../llmster_archive_acquisition_v2.py", "module path drift")
    expect(DIGEST.fullmatch(module["sha256"]) is not None, "malformed module digest")
    target = (base / module["path"]).resolve()
    expect(
        {key: module[key] for key in ("bytes", "lines", "sha256")} == file_identity(target),
        "module identity drift",
    )

    pre = record["pre_request_gate"]
    expect(pre["observed_free_bytes"] == 21_186_654_208, "pre-request storage drift")
    expect(pre["required_free_bytes_before_request"] == 9_663_676_416, "pre-request floor drift")
    expect(
        pre["margin_bytes"]
        == pre["observed_free_bytes"] - pre["required_free_bytes_before_request"],
        "pre-request margin arithmetic drift",
    )
    for key in ("destination_present", "partial_present"):
        expect(pre[key] is False, f"unclean pre-request path: {key}")
    for key in (
        "decision_valid",
        "repository_clean",
        "storage_gate_passed",
        "preserved_identities_matched",
    ):
        expect(pre[key] is True, f"pre-request gate concealed: {key}")

    result = record["request_result"]
    expect(result["http_status"] == 200, "HTTP result drift")
    expect(result["final_url_scheme"] == "https", "final scheme drift")
    expect(result["final_url_host"] == "llmster.lmstudio.ai", "final host drift")
    expect(result["exact_bytes"] == 867_394_409, "archive size drift")
    expect(result["maximum_archive_bytes"] == 1_073_741_824, "archive ceiling drift")
    expect(result["exact_bytes"] <= result["maximum_archive_bytes"], "archive ceiling exceeded")
    expect(DIGEST.fullmatch(result["sha256"]) is not None, "malformed archive sha256")
    expect(SHA512.fullmatch(result["sha512"]) is not None, "malformed archive sha512")
    expect(
        result["sha256"] == "e6556e8edd7240c43da28aa555bac12197ba3e2199247bba773c81c6ae94170c",
        "archive sha256 drift",
    )
    expect(
        result["sha512"]
        == "ec13183ddc2f56d68b48fc13428e0cdca84c29bfc2b87a7aa2b9befeb7b79a8cdd3ea5a7c50d6e941fcf43545c8730f8b2bf2665b030b98e5ccfab6a3d43efff",
        "archive sha512 drift",
    )
    for key in (
        "published_sha512_match",
        "size_ceiling_passed",
        "destination_present_after",
        "partial_absent_after",
        "archive_git_ignored",
    ):
        expect(result[key] is True, f"request result concealed: {key}")
    expect(
        result["destination_relative_path"]
        == ".replay_cache/llmster_acquisition/0.0.21-2-win32-x64.full.zip",
        "destination drift",
    )
    repository_root = path.resolve().parents[3]
    archive_path = repository_root / result["destination_relative_path"]
    expect(archive_path.is_file(), "archive artifact missing")
    expect(
        archive_identity(str(archive_path.resolve()))
        == {
            "bytes": result["exact_bytes"],
            "sha256": result["sha256"],
            "sha512": result["sha512"],
        },
        "archive artifact identity drift",
    )
    partial = archive_path.with_name(archive_path.name + ".partial")
    expect(not partial.exists(), "partial artifact present")

    storage = record["post_request_storage"]
    expect(storage["observed_free_bytes"] == 20_319_256_576, "post-request storage drift")
    expect(storage["minimum_free_bytes_after"] == 8_589_934_592, "final reserve drift")
    expect(
        storage["margin_bytes"]
        == storage["observed_free_bytes"] - storage["minimum_free_bytes_after"],
        "post-request margin arithmetic drift",
    )
    expect(
        storage["observed_volume_delta_bytes"]
        == pre["observed_free_bytes"] - storage["observed_free_bytes"],
        "volume delta arithmetic drift",
    )
    expect(storage["final_storage_gate_passed"] is True, "final storage gate concealed")

    verified = record["independent_post_request_verification"]
    expect(
        verified["archive"]
        == {
            "bytes": result["exact_bytes"],
            "sha256": result["sha256"],
            "sha512": result["sha512"],
        },
        "independent archive identity drift",
    )
    expect(
        verified["canonical_cli"]
        == {
            "bytes": 120_772_792,
            "sha256": "976d4389f97b2cf95b38a4eb673855d8a846f2db21a20eb4fe5e79f7179722f5",
        },
        "canonical CLI identity drift",
    )
    expect(
        verified["engine"]
        == {
            "package": "llama.cpp-win-x86_64-nvidia-cuda-avx2-2.29.1",
            "file_count": 20,
            "total_bytes": 558_082_098,
            "canonical_inventory_sha256": "f40cc6918e6d17975cdcb3151f4953e8788d87bc7e565242d40bd292f7385fd0",
        },
        "engine identity drift",
    )
    expect(
        verified["weight"]
        == {
            "bytes": 4_683_073_536,
            "sha256": "509287f78cb4d4cf6b3843734733b914b2c158e43e22a7f4bf5e963800894d3c",
        },
        "weight identity drift",
    )
    expect(verified["partial_present"] is False, "partial verification concealed")
    expect(verified["cli_engine_and_weight_unchanged"] is True, "preserved state concealed")

    fixtures = record["fixture_evidence"]
    for version in ("python_3_12", "python_3_14"):
        expect(fixtures[version] == {"tests_run": 341, "tests_passed": 341}, f"fixture drift: {version}")
    expect(fixtures["acquisition_result_tests"] == 10, "result fixture count drift")
    expect(fixtures["fixture_network_request_count"] == 0, "fixture network activity admitted")

    security = record["security_and_research_boundary"]
    expect(security["archive_request_count"] == 1, "request count drift")
    expect(security["archive_download_count"] == 1, "download count drift")
    for key, value in security.items():
        if key in ("archive_request_count", "archive_download_count"):
            continue
        if key.endswith("_count"):
            expect(value == 0, f"unauthorized operation admitted: {key}")
        else:
            expect(value is False, f"research boundary widened: {key}")

    gate = record["result_gate"]
    for key in (
        "authorization_consumed",
        "archive_identity_verified",
        "storage_gate_passed",
        "clean_placement_verified",
        "existing_state_preserved",
        "archive_acquisition_accepted",
    ):
        expect(gate[key] is True, f"accepted result gate missing: {key}")
    for key in (
        "another_archive_request_authorized",
        "archive_inventory_authorized",
        "archive_extraction_authorized",
        "standalone_llmster_installation_authorized",
        "lm_studio_runtime_execution_authorized",
        "synthetic_canary_authorized",
        "benchmark_input_authorized",
    ):
        expect(gate[key] is False, f"scope widened: {key}")
    expect(
        gate["next_action"]
        == "make_a_separate_archive_inventory_and_installation_safety_review_decision_without_executing_the_archive",
        "next action drift",
    )
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    args = parser.parse_args()
    try:
        validate(args.evidence)
    except (
        OSError,
        KeyError,
        TypeError,
        json.JSONDecodeError,
        LlmsterArchiveAcquisitionResultError,
    ) as error:
        print(f"INVALID: {error}")
        return 1
    print("VALID: exact llmster archive acquired and verified; extraction remains blocked")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
