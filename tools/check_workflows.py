# SPDX-License-Identifier: Apache-2.0
"""Parse GitHub YAML and enforce the repository's manual-only publication boundary."""

import tomllib
from pathlib import Path
from typing import Any, cast

from ruamel.yaml import YAML

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    yaml = YAML(typ="safe")
    yaml.allow_duplicate_keys = False
    files = sorted((ROOT / ".github").rglob("*.yml"))
    for path in files:
        raw: Any = yaml.load(path.read_text(encoding="utf-8"))  # pyright: ignore[reportUnknownMemberType]
        if not isinstance(raw, dict):
            raise ValueError(f"{path}: expected a YAML mapping")
        document = cast(dict[str, Any], raw)
        if path.parent.name != "workflows":
            continue
        events = cast(dict[str, Any], document["on"])
        assert isinstance(events, dict)
        assert document["permissions"] == {"contents": "read"}
        jobs = cast(dict[str, Any], document["jobs"])
        for job in jobs.values():
            assert job["runs-on"] and job["timeout-minutes"] > 0
            for step in job["steps"]:
                assert ("uses" in step) != ("run" in step)
        if path.name == "ci.yml":
            assert set(events) == {"push", "pull_request"}
        if path.name == "release.yml":
            assert set(events) == {"workflow_dispatch"}
            assert document["on"]["workflow_dispatch"]["inputs"]["publish"]["default"] is False
            publish: Any = jobs["publish"]
            assert publish["permissions"] == {"id-token": "write"}
            assert publish["needs"] == "build"
            assert publish["environment"]["name"] == "pypi-${{ matrix.package }}"
            names = {
                tomllib.loads(p.read_text(encoding="utf-8"))["project"]["name"]
                for p in (ROOT / "packages").glob("*/pyproject.toml")
            }
            assert set(publish["strategy"]["matrix"]["package"]) == names
            assert "inputs.publish" in publish["if"] and "refs/heads/main" in publish["if"]
            assert publish["steps"][-1]["uses"] == "pypa/gh-action-pypi-publish@release/v1"
    print(f"{len(files)} GitHub YAML files parsed; CI events and manual-only release guards OK")
    print("GitHub execution and PyPI trusted-publisher configuration are not checked locally.")


if __name__ == "__main__":
    main()
