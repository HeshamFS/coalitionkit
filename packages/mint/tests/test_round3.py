# SPDX-License-Identifier: Apache-2.0
"""Round-three boundary regressions."""

import asyncio
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from coalitionkit_contracts.signing import sign_detached
from coalitionkit_mint.artifact import connect, consent_payload, generate
from coalitionkit_mint.process import Sandbox
from coalitionkit_mint.scan import scan_templates
from coalitionkit_mint.schema import ResourceConfig
from coalitionkit_mint.worker import Operations


@pytest.mark.parametrize(
    "source",
    [
        "import uuid\nuuid.os.system('unused')",
        "import typing\ntyping.sys.modules",
        "open('unused')",
        "import typing\ntyping.__import__('unused')",
        "eval('0')",
        "exec('pass')",
        "compile('0', '', 'eval')",
        "__import__('os')",
    ],
)
def test_scan_rejects_indirect_execution(tmp_path: Path, source: str) -> None:
    (tmp_path / "template.py").write_text(source)
    with pytest.raises(ValueError):
        scan_templates(tmp_path)


@pytest.mark.parametrize("config", ["resource"], indirect=True)
def test_hold_challenge_expiry_and_binding(tmp_path: Path, config: dict[str, Any]) -> None:
    config["prerequisites"] = ["ready"]
    owner = Ed25519PrivateKey.generate()
    folder = tmp_path / "artifact"
    manifest = generate(folder, ResourceConfig.model_validate(config), owner.public_key(), "p1")
    ops = Operations(folder)
    base = {"start": 540, "end": 570, "prerequisites": ["ready"]}
    challenge = ops.invoke("hold_challenge", base)
    assert challenge != ops.invoke("hold_challenge", base)
    for changed in (True, False):
        args = {**base, **challenge}
        if changed:
            args.update(start=570, end=600)
        else:
            with connect(folder) as db:
                db.execute("UPDATE hold_requests SET expires=0")
        proof = sign_detached(consent_payload(manifest, "hold_slot", args), owner, "owner")
        with pytest.raises(ValueError, match="stale_hold"):
            ops.invoke("hold_slot", args, proof)
        with connect(folder) as db:
            assert db.execute(
                "SELECT 1 FROM consumed_proofs WHERE signature=?", (proof,)
            ).fetchone()


@pytest.mark.parametrize("config", ["resource"], indirect=True)
async def test_worker_drains_stdout(
    tmp_path: Path,
    config: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    folder = tmp_path / "artifact"
    generate(
        folder,
        ResourceConfig.model_validate(config),
        Ed25519PrivateKey.generate().public_key(),
        "p1",
    )
    original = subprocess.Popen
    script = (
        "import runpy,threading,time,sys\nfrom pathlib import Path\n"
        "def noisy():\n while not Path('go').exists(): time.sleep(0.01)\n"
        " print('x'*1048576,flush=True)\n"
        " Path('drained').write_text('yes')\n"
        "threading.Thread(target=noisy,daemon=True).start()\n"
        "sys.argv=['worker','--port','0']\n"
        "runpy.run_module('coalitionkit_mint.worker',run_name='__main__')\n"
    )

    def launch(args: Any, **kwargs: Any) -> subprocess.Popen[str]:
        return original([sys.executable, "-I", "-c", script], **kwargs)

    monkeypatch.setattr(subprocess, "Popen", launch)
    sandbox = Sandbox(folder)
    try:
        await sandbox.start()
        (folder / "go").touch()
        for _ in range(100):
            if (folder / "drained").exists():
                break
            await asyncio.sleep(0.05)
        assert (folder / "drained").exists(), "worker blocked writing stdout"
    finally:
        sandbox.stop()


def test_direct_dependencies_are_pinned() -> None:
    import tomllib

    manifest = Path(__file__).resolve().parents[1] / "pyproject.toml"
    dependencies = tomllib.loads(manifest.read_text())["project"]["dependencies"]
    assert "protobuf==7.36.2" in dependencies
    assert "starlette==1.10.0" in dependencies


@pytest.mark.parametrize("config", ["resource"], indirect=True)
def test_window_check_is_independent(
    tmp_path: Path,
    config: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import inspect

    from coalitionkit_mint.templates import resource

    source = inspect.getsource(resource.act).replace(
        "if not any(w.start <= start < end <= w.end for w in config.windows):", "if False:"
    )
    namespace: dict[str, Any] = dict(vars(resource))
    exec(compile(source, "<window mutation>", "exec"), namespace)
    monkeypatch.setattr(resource, "act", namespace["act"])
    folder = tmp_path / "artifact"
    generate(
        folder,
        ResourceConfig.model_validate(config),
        Ed25519PrivateKey.generate().public_key(),
        "p1",
    )
    result = Operations(folder).invoke("hold_slot", {"start": 510, "end": 540, "prerequisites": []})
    assert result["state"] == "held"
