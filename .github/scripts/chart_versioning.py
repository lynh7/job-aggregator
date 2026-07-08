#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


COMPONENT_TAG_PATHS = {
    "job-api": ["jobApi", "image", "tag"],
    "candidate-api": ["candidateApi", "image", "tag"],
    "candidate-worker": ["candidateWorker", "image", "tag"],
    "crawler-api": ["crawlerApi", "imageVariants", "lightweight", "tag"],
    "crawler-api-browser": ["crawlerApi", "imageVariants", "browser", "tag"],
    "ui-web": ["uiWeb", "image", "tag"],
}


def bump_patch(version: str) -> str:
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", version.strip())
    if not match:
        raise ValueError(f"Unexpected semver: {version!r}")
    major, minor, patch = map(int, match.groups())
    return f"{major}.{minor}.{patch + 1}"


def _find_yaml_path_line(lines: list[str], path: list[str]) -> int:
    stack: list[tuple[int, str]] = []
    for index, line in enumerate(lines):
        match = re.match(r"^( *)([A-Za-z0-9]+):(?:\s*(.*))?$", line.rstrip("\n"))
        if not match:
            continue
        indent = len(match.group(1))
        key = match.group(2)
        while stack and stack[-1][0] >= indent:
            stack.pop()
        stack.append((indent, key))
        keys = [item[1] for item in stack]
        if keys == path:
            return index
    raise KeyError(f"Could not find YAML path: {'.'.join(path)}")


def read_yaml_string(path: Path, keys: list[str]) -> str:
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    line_index = _find_yaml_path_line(lines, keys)
    line = lines[line_index]
    value = line.split(":", 1)[1].strip()
    return value.strip('"')


def write_yaml_string(path: Path, keys: list[str], value: str) -> None:
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    line_index = _find_yaml_path_line(lines, keys)
    prefix = lines[line_index].split(":", 1)[0]
    lines[line_index] = f'{prefix}: "{value}"\n'
    path.write_text("".join(lines), encoding="utf-8")


def read_chart_version(chart_path: Path) -> str:
    for line in chart_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("version:"):
            return line.split(":", 1)[1].strip().strip('"')
    raise KeyError("Chart version not found")


def write_chart_versions(chart_path: Path, version: str) -> None:
    lines = chart_path.read_text(encoding="utf-8").splitlines(keepends=True)
    for index, line in enumerate(lines):
        if line.startswith("version:"):
            lines[index] = f"version: {version}\n"
        elif line.startswith("appVersion:"):
            lines[index] = f'appVersion: "{version}"\n'
    chart_path.write_text("".join(lines), encoding="utf-8")


def command_plan_build(args: argparse.Namespace) -> int:
    values_path = Path(args.values_file)
    chart_path = Path(args.chart_file)
    matrix = json.loads(args.matrix_json)

    for item in matrix:
        component = item["name"]
        tag_path = COMPONENT_TAG_PATHS[component]
        current = read_yaml_string(values_path, tag_path)
        item["version"] = bump_patch(current)

    payload = {
        "matrix": matrix,
        "chart_version": bump_patch(read_chart_version(chart_path)),
    }
    print(json.dumps(payload, separators=(",", ":")))
    return 0


def command_apply_release_state(args: argparse.Namespace) -> int:
    values_path = Path(args.values_file)
    chart_path = Path(args.chart_file)
    matrix = json.loads(args.matrix_json)

    for item in matrix:
        write_yaml_string(values_path, COMPONENT_TAG_PATHS[item["name"]], item["version"])
    write_chart_versions(chart_path, args.chart_version)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    plan_build = subparsers.add_parser("plan-build")
    plan_build.add_argument("--matrix-json", required=True)
    plan_build.add_argument("--values-file", default="helm-chart/values.yaml")
    plan_build.add_argument("--chart-file", default="helm-chart/Chart.yaml")
    plan_build.set_defaults(func=command_plan_build)

    apply_release = subparsers.add_parser("apply-release-state")
    apply_release.add_argument("--matrix-json", required=True)
    apply_release.add_argument("--chart-version", required=True)
    apply_release.add_argument("--values-file", default="helm-chart/values.yaml")
    apply_release.add_argument("--chart-file", default="helm-chart/Chart.yaml")
    apply_release.set_defaults(func=command_apply_release_state)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
