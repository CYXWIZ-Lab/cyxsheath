"""Validate the privacy-minimized Phase-6 host-capacity evidence."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


COMMIT = re.compile(r"^[0-9a-f]{40}$")
SHORT_COMMIT = re.compile(r"^[0-9a-f]{7,40}$")
PINNED_IMAGE = (
    "python@sha256:dd29372629eeba2dd003fd9e9d35a5b8236c44727875a0364254b5127af88e65"
)
PINNED_IMAGE_ID = "sha256:" + PINNED_IMAGE.rsplit("sha256:", 1)[1]
FORBIDDEN_KEYS = {
    "hostname",
    "machine_name",
    "machine_id",
    "serial_number",
    "serial_numbers",
    "username",
    "user_name",
    "mac_address",
    "mac_addresses",
    "resolved_ip",
    "resolved_address",
    "raw_prompt",
    "raw_response",
    "problem_statement",
    "patch",
    "test_patch",
    "eval_script",
    "credentials",
}


class HostCapacityError(ValueError):
    pass


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise HostCapacityError(message)


def expect_number(value: object, name: str, *, positive: bool = True) -> None:
    expect(isinstance(value, (int, float)) and not isinstance(value, bool), f"{name}: not numeric")
    if positive:
        expect(value > 0, f"{name}: must be positive")


def check_forbidden_keys(value: object, where: str = "root") -> None:
    if isinstance(value, dict):
        found = FORBIDDEN_KEYS & set(value)
        expect(not found, f"{where}: forbidden sensitive keys {sorted(found)}")
        for key, child in value.items():
            check_forbidden_keys(child, f"{where}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            check_forbidden_keys(child, f"{where}[{index}]")


def validate(path: Path) -> dict:
    record = json.loads(path.read_text(encoding="utf-8"))
    check_forbidden_keys(record)

    expect(record["schema_version"] == "1.0.0", "unsupported schema")
    expect(
        record["status"] == "capacity_audited_connectivity_passed_runtime_decision_pending",
        "unsafe status",
    )
    expect(
        record["decision_scope"] == "project_runtime_feasibility_not_benchmark_authorization",
        "invalid decision scope",
    )
    expect(record["recorded_at"].endswith("Z"), "timestamp must be UTC")
    expect(COMMIT.fullmatch(record["baseline_commit"]) is not None, "malformed baseline commit")

    privacy = record["privacy"]
    expect(privacy["resolved_address_retained"] is False, "resolved address retained")
    expect("credentials" in privacy["excluded"], "credential exclusion missing")
    expect("hostname" in privacy["excluded"], "host-identity exclusion missing")

    host = record["host"]
    cpu = host["cpu"]
    expect_number(cpu["physical_cores"], "physical cores")
    expect_number(cpu["logical_processors"], "logical processors")
    expect(cpu["logical_processors"] >= cpu["physical_cores"], "inconsistent core counts")
    memory = host["memory"]
    expect_number(memory["total_bytes"], "host memory")
    expect_number(memory["available_bytes_at_audit"], "available memory")
    expect(memory["available_bytes_at_audit"] <= memory["total_bytes"], "available memory exceeds total")
    gpu = host["gpu"]
    expect_number(gpu["vram_total_mib"], "GPU memory")
    expect_number(gpu["vram_free_mib_at_audit"], "free GPU memory")
    expect(gpu["vram_free_mib_at_audit"] <= gpu["vram_total_mib"], "free GPU memory exceeds total")
    expect(len(host["storage"]) >= 1, "storage inventory empty")
    for disk in host["storage"]:
        expect_number(disk["total_bytes"], f"{disk['drive']} total storage")
        expect_number(disk["free_bytes_at_audit"], f"{disk['drive']} free storage")
        expect(disk["free_bytes_at_audit"] <= disk["total_bytes"], "free storage exceeds total")

    docker = record["docker"]
    expect_number(docker["logical_processors"], "Docker processors")
    expect_number(docker["memory_limit_bytes"], "Docker memory")
    expect(docker["probe_image"]["reference"] == PINNED_IMAGE, "probe image reference drift")
    expect(docker["probe_image"]["image_id"] == PINNED_IMAGE_ID, "probe image identity drift")
    connectivity = docker["connectivity"]
    for key in (
        "alias_resolved",
        "tcp_connected",
        "host_listener_accepted",
        "container_absent_after",
    ):
        expect(connectivity[key] is True, f"connectivity check failed: {key}")
    for key in ("resolved_address_retained", "benchmark_data_used", "model_data_used"):
        expect(connectivity[key] is False, f"unsafe connectivity record: {key}")
    expect(connectivity["host_alias"] == "host.docker.internal", "host alias drift")

    runtimes = record["runtimes"]
    expect(runtimes["ollama"]["installed"] is False, "Ollama readiness overclaim")
    lm_studio = runtimes["lm_studio_cli"]
    expect(lm_studio["installed"] is True, "LM Studio CLI observation missing")
    expect(SHORT_COMMIT.fullmatch(lm_studio["cli_commit"]) is not None, "malformed CLI commit")
    expect(lm_studio["model_inventory_status"] == "timed_out_waking_service", "inventory result drift")
    expect_number(lm_studio["inventory_timeout_seconds"], "inventory timeout")
    for key in ("server_running_before", "server_running_after", "process_observed_after", "ready"):
        expect(lm_studio[key] is False, f"runtime readiness overclaim: {key}")

    assessment = record["capacity_assessment"]
    expect(assessment["gpu_model_fit"] == "small_or_partial_offload_only", "GPU fit overclaim")
    expect(
        assessment["cpu_quantized_model_fit"] == "plausible_requires_synthetic_canary",
        "CPU fit overclaim",
    )
    expect(
        assessment["storage_status"] == "constrained_requires_workspace_drive_and_ceiling",
        "storage constraint missing",
    )
    expect(assessment["runtime_readiness"] == "not_ready", "runtime readiness overclaim")
    expect(assessment["decision"] == "pending_separate_runtime_model_record", "decision boundary drift")

    deviation = record["protocol_deviations"]
    expect(len(deviation) == 1, "unexpected deviation count")
    expect(deviation[0]["container_created"] is False, "preflight created a container")
    expect(deviation[0]["impact"] == "none", "preflight impact overclaim")

    boundary = record["execution_boundary"]
    for key in (
        "runtime_installation_authorized",
        "model_download_authorized",
        "model_selected",
        "local_canary_authorized",
        "benchmark_input_authorized",
    ):
        expect(boundary[key] is False, f"premature authorization: {key}")
    expect(boundary["next_action"] == "record_explicit_runtime_model_decision", "next action drift")
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    args = parser.parse_args()
    try:
        record = validate(args.evidence)
    except (OSError, KeyError, TypeError, json.JSONDecodeError, HostCapacityError) as exc:
        print(f"INVALID: {exc}")
        return 1
    cpu = record["host"]["cpu"]
    ram_gib = record["host"]["memory"]["total_bytes"] / (1024**3)
    vram_mib = record["host"]["gpu"]["vram_total_mib"]
    print(
        f"VALID: cpu={cpu['physical_cores']}c/{cpu['logical_processors']}t; "
        f"ram_gib={ram_gib:.2f}; vram_mib={vram_mib}; "
        "docker_host_tcp=passed; runtime=not_ready"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
