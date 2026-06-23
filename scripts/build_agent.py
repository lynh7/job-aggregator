#!/usr/bin/env python3
"""Watch origin/main, bump patch version, and build Docker images."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path


SEMVER_RE = re.compile(r"^v?(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)$")
IMAGE_SPECS = (
    ("job-api", "docker/job-api.Dockerfile", "job-aggregator-api"),
    ("crawler-api", "docker/crawler-api.Dockerfile", "job-aggregator-crawler-api"),
    (
        "crawler-api-browser",
        "docker/crawler-api-browser.Dockerfile",
        "job-aggregator-crawler-api-browser",
    ),
    ("candidate-api", "docker/candidate-api.Dockerfile", "job-aggregator-candidate-api"),
    ("candidate-worker", "docker/candidate-worker.Dockerfile", "job-aggregator-candidate-worker"),
)


@dataclass(frozen=True)
class BuildVersion:
    major: int
    minor: int
    patch: int

    def bump_patch(self) -> "BuildVersion":
        return BuildVersion(self.major, self.minor, self.patch + 1)

    def tag(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"


class BuildAgent:
    def __init__(
        self,
        *,
        repo_dir: Path,
        state_file: Path,
        remote: str,
        branch: str,
        registry: str | None,
        push: bool,
    ) -> None:
        self.repo_dir = repo_dir
        self.state_file = state_file
        self.remote = remote
        self.branch = branch
        self.registry = registry.rstrip("/") if registry else None
        self.push = push

    def run_once(self) -> bool:
        remote_sha = self._remote_head_sha()
        state = self._load_state()
        if state.get("last_built_sha") == remote_sha:
            print(f"No change on {self.remote}/{self.branch}; last built {remote_sha}")
            return False

        version = self._next_version(state)
        print(f"New commit detected on {self.remote}/{self.branch}: {remote_sha}")
        print(f"Building version {version.tag()}")
        self._fetch_remote_branch()
        self._build_commit(remote_sha, version)
        self._write_state(
            {
                "last_built_sha": remote_sha,
                "last_version": version.tag(),
                "updated_at_epoch": int(time.time()),
            }
        )
        return True

    def run_forever(self, poll_seconds: int) -> None:
        while True:
            try:
                self.run_once()
            except Exception as exc:  # noqa: BLE001
                print(f"Build agent error: {exc}", flush=True)
            time.sleep(poll_seconds)

    def _build_commit(self, commit_sha: str, version: BuildVersion) -> None:
        with tempfile.TemporaryDirectory(prefix="job-aggregator-build-") as temp_dir:
            worktree_dir = Path(temp_dir) / "worktree"
            self._git("worktree", "add", "--detach", str(worktree_dir), commit_sha)
            try:
                for service_name, dockerfile, image_name in IMAGE_SPECS:
                    tags = self._image_tags(image_name, version)
                    print(f"Building {service_name}: {', '.join(tags)}")
                    primary_tag, *extra_tags = tags
                    self._docker(
                        "build",
                        "-f",
                        dockerfile,
                        "-t",
                        primary_tag,
                        str(worktree_dir),
                        cwd=worktree_dir,
                    )
                    for extra_tag in extra_tags:
                        self._docker("tag", primary_tag, extra_tag)
                    if self.push:
                        for tag in tags:
                            self._docker("push", tag)
            finally:
                self._git("worktree", "remove", "--force", str(worktree_dir))

    def _image_tags(self, image_name: str, version: BuildVersion) -> list[str]:
        base_name = f"{self.registry}/{image_name}" if self.registry else image_name
        return [f"{base_name}:{version.tag()}", f"{base_name}:latest"]

    def _next_version(self, state: dict[str, object]) -> BuildVersion:
        last = state.get("last_version")
        if isinstance(last, str):
            return self._parse_version(last).bump_patch()
        return self._base_version().bump_patch()

    def _base_version(self) -> BuildVersion:
        pyproject = self.repo_dir / "pyproject.toml"
        version_line = next(
            line for line in pyproject.read_text(encoding="utf-8").splitlines() if line.startswith("version = ")
        )
        raw = version_line.split("=", 1)[1].strip().strip('"')
        return self._parse_version(raw)

    def _parse_version(self, value: str) -> BuildVersion:
        match = SEMVER_RE.match(value)
        if match is None:
            raise ValueError(f"Invalid semantic version: {value}")
        return BuildVersion(
            major=int(match.group("major")),
            minor=int(match.group("minor")),
            patch=int(match.group("patch")),
        )

    def _remote_head_sha(self) -> str:
        output = self._git("ls-remote", self.remote, f"refs/heads/{self.branch}", capture=True)
        sha, _ref = output.strip().split("	", 1)
        return sha

    def _fetch_remote_branch(self) -> None:
        self._git("fetch", self.remote, self.branch)

    def _load_state(self) -> dict[str, object]:
        if not self.state_file.exists():
            return {}
        return json.loads(self.state_file.read_text(encoding="utf-8"))

    def _write_state(self, state: dict[str, object]) -> None:
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")

    def _git(self, *args: str, capture: bool = False) -> str:
        cmd = ["git", "-C", str(self.repo_dir), *args]
        return self._run(cmd, capture=capture)

    def _docker(self, *args: str, cwd: Path | None = None) -> str:
        cmd = ["docker", *args]
        return self._run(cmd, cwd=cwd)

    def _run(self, cmd: list[str], *, cwd: Path | None = None, capture: bool = False) -> str:
        print("+", " ".join(cmd), flush=True)
        completed = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            check=True,
            text=True,
            stdout=subprocess.PIPE if capture else None,
            stderr=subprocess.STDOUT if capture else None,
        )
        return completed.stdout or ""


def parse_args() -> argparse.Namespace:
    repo_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Local Docker build agent for origin/main")
    parser.add_argument("--mode", choices=("once", "daemon"), default="once")
    parser.add_argument("--poll-seconds", type=int, default=int(os.environ.get("BUILD_AGENT_POLL_SECONDS", "60")))
    parser.add_argument("--repo-dir", default=str(repo_root))
    parser.add_argument(
        "--state-file",
        default=os.environ.get(
            "BUILD_AGENT_STATE_FILE",
            str(repo_root / ".codex" / "build-agent" / "state.json"),
        ),
    )
    parser.add_argument("--remote", default=os.environ.get("BUILD_AGENT_REMOTE", "origin"))
    parser.add_argument("--branch", default=os.environ.get("BUILD_AGENT_BRANCH", "main"))
    parser.add_argument("--registry", default=os.environ.get("BUILD_AGENT_REGISTRY"))
    parser.add_argument(
        "--push",
        action="store_true",
        default=os.environ.get("BUILD_AGENT_PUSH", "").lower() in {"1", "true", "yes"},
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    repo_dir = Path(args.repo_dir).resolve()
    state_file = Path(args.state_file).resolve()
    if shutil.which("docker") is None:
        raise SystemExit("docker is required")
    agent = BuildAgent(
        repo_dir=repo_dir,
        state_file=state_file,
        remote=args.remote,
        branch=args.branch,
        registry=args.registry,
        push=args.push,
    )
    if args.mode == "daemon":
        agent.run_forever(args.poll_seconds)
    else:
        agent.run_once()


if __name__ == "__main__":
    main()
