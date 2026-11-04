# SPDX-License-Identifier: Apache-2.0
"""Build every distribution, then prove a wheel-only install outside the checkout.

Run tools/build_web.py first. --wheelhouse supplies previously downloaded dependency
wheels for an offline run; otherwise pip downloads dependencies before the offline install.
"""

import argparse
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
import tomllib
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]


def run(command: list[str], cwd: Path, env: dict[str, str] | None = None) -> str:
    result = subprocess.run(command, cwd=cwd, env=env, capture_output=True, text=True, check=False)
    if result.returncode:
        raise RuntimeError(f"{' '.join(command)}\n{result.stdout}\n{result.stderr}")
    return result.stdout.strip()


def build_wheels(destination: Path) -> int:
    uv = shutil.which("uv")
    if uv is None:
        raise RuntimeError("Install uv to build the workspace wheels")
    projects = sorted(ROOT.glob("packages/*/pyproject.toml"))
    for project in projects:
        metadata = tomllib.loads(project.read_text(encoding="utf-8"))["project"]
        if metadata["version"] != "0.1.0":
            raise RuntimeError(f"Version mismatch: {project}")
        run(
            [
                uv,
                "build",
                str(project.parent),
                "--wheel",
                "--no-sources",
                "--out-dir",
                str(destination),
            ],
            ROOT,
        )
    print(f"Built {len(projects)} CoalitionKit wheels (0.1.0)", flush=True)
    return len(projects)


def http_get(url: str) -> tuple[int, str]:
    with urlopen(url, timeout=3) as response:
        return response.status, response.read().decode("utf-8")


def exercise(command: Path, cwd: Path, env: dict[str, str], label: str) -> None:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    base = f"http://127.0.0.1:{port}"
    flags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
    log = cwd / "host.log"
    with log.open("w", encoding="utf-8") as output:
        process = subprocess.Popen(
            [str(command), "up", "--port", str(port), "--data-dir", str(cwd / "data")],
            cwd=cwd,
            env=env,
            stdout=output,
            stderr=output,
            creationflags=flags,
        )
        try:
            deadline = time.monotonic() + 60
            while True:
                if process.poll() is not None:
                    raise RuntimeError("Host exited before readiness")
                try:
                    status, _ = http_get(base + "/healthz")
                    if status == 200:
                        break
                except URLError, TimeoutError, ConnectionError:
                    pass
                if time.monotonic() >= deadline:
                    raise RuntimeError("Host readiness timed out")
                time.sleep(0.2)
            status, html = http_get(base + "/")
            if status != 200 or '<div id="root"' not in html:
                raise RuntimeError("Room HTML missing its application root")
            assets = re.findall(r'(?:src|href)="([^"]+\.(?:js|css))"', html)
            if not assets:
                raise RuntimeError("Room HTML references no built JS/CSS")
            for asset in assets:
                code, body = http_get(base + "/" + asset.lstrip("/"))
                if code != 200 or not body or body.lstrip().startswith("<!doctype"):
                    raise RuntimeError(f"Missing room asset: {asset}")
            print(
                f"{label}: --help OK; host HTTP 200; room HTTP 200; {len(assets)} assets OK",
                flush=True,
            )
        except BaseException:
            output.flush()
            # Host startup logs contain local credentials; keep them in the temporary folder.
            raise RuntimeError(f"Smoke host failed; diagnostic log: {log}") from None
        finally:
            if process.poll() is None:
                process.send_signal(signal.CTRL_BREAK_EVENT if os.name == "nt" else signal.SIGTERM)
                try:
                    process.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
            print(f"{label}: host stopped (exit {process.returncode})", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheelhouse", type=Path, help="offline third-party dependency wheels")
    args = parser.parse_args()
    if not (ROOT / "packages/cli/src/coalitionkit_cli/web_dist/index.html").is_file():
        raise SystemExit("Run uv run python tools/build_web.py before the smoke install")
    with tempfile.TemporaryDirectory(prefix="coalitionkit-install-") as directory:
        base = Path(directory).resolve()
        if base.is_relative_to(ROOT):
            raise RuntimeError("The smoke environment must be outside the repository")
        wheels = base / "wheels"
        wheels.mkdir()
        count = build_wheels(wheels)
        venv = base / "venv"
        run([sys.executable, "-m", "venv", str(venv)], base)
        scripts = venv / ("Scripts" if os.name == "nt" else "bin")
        python = scripts / ("python.exe" if os.name == "nt" else "python")
        pip = [str(python), "-m", "pip"]
        links = ["--find-links", str(wheels)]
        if args.wheelhouse:
            links += ["--find-links", str(args.wheelhouse.resolve())]
        else:
            run(
                [
                    *pip,
                    "download",
                    "--only-binary=:all:",
                    *links,
                    "--dest",
                    str(wheels),
                    "coalitionkit==0.1.0",
                ],
                base,
            )
        env = {
            key: value
            for key, value in os.environ.items()
            if not key.startswith(("COALITIONKIT_", "PYTHON", "VIRTUAL_ENV"))
        }
        # Exclude developer tool paths; Windows still needs icacls for private key ACLs.
        paths = [str(scripts)]
        if os.name == "nt":
            paths.append(str(Path(os.environ["SYSTEMROOT"]) / "System32"))
        env["PATH"] = os.pathsep.join(paths)
        if shutil.which("node", path=env["PATH"]) is not None:
            raise RuntimeError("Node must be absent from the smoke environment")
        env["PIP_NO_INDEX"] = "1"
        run(
            [*pip, "install", "--no-index", "--only-binary=:all:", *links, "coalitionkit==0.1.0"],
            base,
            env,
        )
        run([*pip, "check"], base, env)
        probe = (
            "from coalitionkit_contracts.validate import load_schemas; "
            "from coalitionkit_server.settings import Settings; "
            "from coalitionkit_surfaces import load_catalog; "
            "from coalitionkit_mcp.view import surface_html; assert surface_html(); "
            "assert load_schemas(); assert load_catalog(Settings().catalog_file); "
            "print('resources OK')"
        )
        run([str(python), "-I", "-c", probe], base, env)
        print(
            f"Installed {count} project wheels offline in a clean external venv; pip check OK",
            flush=True,
        )
        print(
            f"Python {sys.version.split()[0]}; packaged schemas and catalog OK; Node absent",
            flush=True,
        )
        command = scripts / ("coalitionkit.exe" if os.name == "nt" else "coalitionkit")
        for label in ("external cwd", "different cwd"):
            cwd = base / label.replace(" ", "-")
            cwd.mkdir()
            help_text = run([str(command), "--help"], cwd, env)
            if "up" not in help_text:
                raise RuntimeError("coalitionkit --help did not list up")
            exercise(command, cwd, env, label)
        print("PASS: wheel-only installation and both working directories", flush=True)


if __name__ == "__main__":
    main()
