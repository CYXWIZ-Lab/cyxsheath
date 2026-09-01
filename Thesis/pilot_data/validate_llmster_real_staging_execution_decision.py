"""Validate the one-shot real LLMster owned-staging decision."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
from typing import Callable

try:
    from .validate_llmster_archive_inventory_v2_result import (
        validate as validate_inventory,
    )
    from .validate_llmster_extraction_staging_implementation_result import (
        validate as validate_implementation,
    )
except ImportError:
    from validate_llmster_archive_inventory_v2_result import (
        validate as validate_inventory,
    )
    from validate_llmster_extraction_staging_implementation_result import (
        validate as validate_implementation,
    )


class LlmsterRealStagingExecutionDecisionError(ValueError):
    pass


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise LlmsterRealStagingExecutionDecisionError(message)


def _default_free_bytes(path: Path) -> int:
    return shutil.disk_usage(path).free


def validate_live_preconditions(
    record: dict,
    repository_root: Path,
    free_bytes: Callable[[Path], int] = _default_free_bytes,
) -> None:
    """Check only staging-parent and storage state; never touch the archive."""

    expect(repository_root.is_absolute(), "repository root must be absolute")
    target = record["owned_target"]
    parent = repository_root / target["parent_repository_relative_path"]
    expect(parent.is_dir() and not parent.is_symlink(), "live staging parent invalid")
    expect(parent.resolve(strict=True).is_relative_to(repository_root), "live parent escaped repository")
    expect(not any(parent.iterdir()), "live staging parent not empty")
    child = parent / target["child_name"]
    expect(not child.exists() and not child.is_symlink(), "live staging child present")
    available = free_bytes(parent)
    expect(
        isinstance(available, int) and not isinstance(available, bool) and available >= 0,
        "live free-space observation invalid",
    )
    expect(
        available >= record["fresh_storage_preflight"]["minimum_free_bytes_before"],
        "live storage gate failed",
    )


def validate(
    path: Path,
    *,
    enforce_live_preconditions: bool = True,
    repository_root: Path | None = None,
) -> dict:
    record = json.loads(path.read_text(encoding="utf-8"))
    expect(record["schema_version"] == "1.0.0", "unsupported schema")
    expect(
        record["status"]
        == "llmster_real_archive_owned_staging_authorized_once_signature_installation_execution_blocked",
        "unsafe status",
    )
    expect(
        record["decision_scope"]
        == "one_exact_archive_identity_inventory_and_streamed_member_extraction_into_one_marker_owned_ignored_child_without_signature_tooling_installation_or_execution",
        "scope drift",
    )
    expect(record["recorded_at"].endswith("Z"), "timestamp must be UTC")
    expect(
        record["baseline_commit"] == "d9adc1da6672e939d254d8ca4b1a6e91f61ffbac",
        "baseline commit drift",
    )

    base = path.parent
    implementation_link = record["reviewed_implementation"]
    expect(
        implementation_link["record"]
        == "phase6_llmster_extraction_staging_implementation_result.json",
        "implementation record drift",
    )
    implementation_path = base / implementation_link["record"]
    expect(
        hashlib.sha256(implementation_path.read_bytes()).hexdigest()
        == implementation_link["sha256"],
        "implementation digest drift",
    )
    implementation = validate_implementation(implementation_path)
    expect(implementation["status"] == implementation_link["status"], "implementation status drift")
    expect(
        implementation_link["implementation_commit"]
        == "d9adc1da6672e939d254d8ca4b1a6e91f61ffbac",
        "implementation commit drift",
    )
    expect(
        implementation_link["generated_staging_fixtures_per_python"] == 19,
        "implementation fixture drift",
    )

    inventory_link = record["accepted_inventory"]
    expect(
        inventory_link["record"] == "phase6_llmster_archive_inventory_v2_result.json",
        "inventory record drift",
    )
    inventory_path = base / inventory_link["record"]
    expect(
        hashlib.sha256(inventory_path.read_bytes()).hexdigest() == inventory_link["sha256"],
        "inventory digest drift",
    )
    inventory = validate_inventory(inventory_path)
    expect(inventory["status"] == inventory_link["status"], "inventory status drift")
    aggregate = inventory["aggregate_inventory"]
    for key in (
        "entry_count",
        "file_count",
        "directory_count",
        "total_uncompressed_bytes",
        "canonical_inventory_sha256",
    ):
        expect(inventory_link[key] == aggregate[key], f"inventory linkage drift: {key}")

    archive = record["archive_identity"]
    accepted_archive = inventory["archive"]
    expect(
        archive
        == {
            "repository_relative_path": ".replay_cache/llmster_acquisition/0.0.21-2-win32-x64.full.zip",
            "bytes": 867_394_409,
            "sha256": "e6556e8edd7240c43da28aa555bac12197ba3e2199247bba773c81c6ae94170c",
            "sha512": "ec13183ddc2f56d68b48fc13428e0cdca84c29bfc2b87a7aa2b9befeb7b79a8cdd3ea5a7c50d6e941fcf43545c8730f8b2bf2665b030b98e5ccfab6a3d43efff",
        },
        "archive identity drift",
    )
    for key in ("repository_relative_path", "bytes", "sha256", "sha512"):
        expect(archive[key] == accepted_archive[key], f"archive linkage drift: {key}")

    target = record["owned_target"]
    expect(target["parent_repository_relative_path"] == ".replay_cache/llmster_staging", "parent drift")
    expect(target["parent_created_for_this_gate"] is True, "parent creation concealed")
    expect(target["parent_observed_existing_directory"] is True, "parent absence concealed")
    expect(target["parent_observed_symlink"] is False, "parent symlink admitted")
    expect(target["parent_observed_child_count"] == 0, "parent contamination concealed")
    expect(
        target["child_name"] == "llmster-f3895cbd1a6e421fa754386f2d144803",
        "child name drift",
    )
    expect(target["child_observed_present"] is False, "existing child concealed")
    expect(target["ownership_marker"] == ".cyxsheath-staging-owner.json", "marker drift")
    for key in (
        "parent_and_child_must_be_revalidated_immediately_before_call",
        "parent_and_archive_retained_on_every_path",
    ):
        expect(target[key] is True, f"ownership gate weakened: {key}")

    storage = record["fresh_storage_preflight"]
    expect(
        storage["measurement_method"] == "python_3_12_shutil_disk_usage_repository_root",
        "storage method drift",
    )
    expect(storage["declared_expansion_bytes"] == 1_791_678_266, "expansion drift")
    expect(storage["minimum_free_bytes_after"] == 4_294_967_296, "final reserve weakened")
    expect(storage["minimum_free_bytes_before"] == 6_086_645_562, "preflight reserve weakened")
    expect(
        storage["observed_free_bytes"] - storage["minimum_free_bytes_before"]
        == storage["observed_margin_bytes"],
        "storage margin drift",
    )
    expect(storage["observed_margin_bytes"] >= 0, "recorded storage gate failed")
    expect(storage["storage_gate_passed"] is True, "storage gate concealed")
    expect(storage["implementation_must_remeasure_before_and_after_writes"] is True, "remeasurement removed")

    call = record["one_shot_call"]
    expected_call = {
        "module": "Thesis.pilot_data.llmster_archive_staging",
        "function": "stage_archive",
        "archive_path": archive["repository_relative_path"],
        "staging_parent": target["parent_repository_relative_path"],
        "staging_name": target["child_name"],
        "expected_bytes": archive["bytes"],
        "expected_sha256": archive["sha256"],
        "expected_sha512": archive["sha512"],
        "expected_inventory_sha256": aggregate["canonical_inventory_sha256"],
        "expected_total_uncompressed_bytes": aggregate["total_uncompressed_bytes"],
        "minimum_free_bytes_after": 4_294_967_296,
        "maximum_function_invocations": 1,
        "authorization_consumed_at": "stage_archive_function_entry",
        "automatic_retry_count_maximum": 0,
        "fresh_decision_required_after_success_failure_or_interruption": True,
    }
    expect(call == expected_call, "one-shot call drift")

    required = record["result_contract"]
    for key, value in required.items():
        expected = key not in {
            "individual_member_paths_or_contents_may_be_curated",
            "absolute_local_paths_may_be_curated",
            "successful_staging_may_be_automatically_removed",
        }
        expect(value is expected, f"result contract weakened: {key}")

    for key, count in record["operation_counts_at_decision"].items():
        expect(count == 0, f"operation occurred at decision: {key}")

    fixtures = record["fixture_evidence"]
    expected_fixture = {
        "predecision_tests_passed": 467,
        "decision_tests_passed": 12,
        "postdecision_tests_passed": 479,
    }
    for version in ("python_3_12", "python_3_14"):
        expect(fixtures[version] == expected_fixture, f"fixture evidence drift: {version}")
    expect(fixtures["real_archive_member_content_reads_during_decision"] == 0, "decision member read admitted")
    expect(fixtures["real_archive_extractions_during_decision"] == 0, "decision extraction admitted")

    gate = record["execution_gate"]
    expect(gate["real_archive_identity_inventory_and_member_reads_authorized_once_inside_exact_call"] is True, "member-read authority missing")
    expect(gate["real_archive_owned_staging_authorized_once"] is True, "staging authority missing")
    expect(gate["maximum_authorized_stage_archive_invocations"] == 1, "invocation count widened")
    for key in (
        "authenticode_tool_invocation_authorized",
        "installation_authorized",
        "binary_execution_authorized",
        "network_request_authorized",
        "benchmark_input_authorized",
        "automatic_retry_authorized",
    ):
        expect(gate[key] is False, f"premature authorization: {key}")
    expect(
        gate["next_action"]
        == "commit_validate_and_revalidate_this_decision_then_invoke_the_exact_stage_archive_call_once_and_record_the_result_without_retry",
        "next action drift",
    )

    if enforce_live_preconditions:
        root = repository_root or path.resolve().parents[3]
        validate_live_preconditions(record, root.resolve(strict=True))
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    parser.add_argument(
        "--historical",
        action="store_true",
        help="validate the consumed decision record without requiring an empty live target",
    )
    args = parser.parse_args()
    try:
        record = validate(
            args.path,
            enforce_live_preconditions=not args.historical,
        )
    except (
        KeyError,
        OSError,
        TypeError,
        json.JSONDecodeError,
        LlmsterRealStagingExecutionDecisionError,
    ) as error:
        print(f"INVALID: {error}")
        return 1
    print(f"VALID: {record['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
