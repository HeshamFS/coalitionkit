# SPDX-License-Identifier: Apache-2.0
"""Write the reference pages that can be read from the code, so they cannot drift from it.

Run `uv run python tools/gen_docs.py`, or add `--check` to fail when a page is out of date.
Writes the catalog, settings, command line, MCP tools, event types and Python API pages.
"""

import argparse
import inspect
import json
import os
import subprocess
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Any, cast

from pydantic.fields import FieldInfo

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs" / "reference"
NOTE = "<!-- Written by tools/gen_docs.py. Edit the source, then run it again. -->\n\n"
BLOB = "https://github.com/HeshamFS/coalitionkit/blob/main"
PACKAGES = {
    "contracts": "Envelope, payload models, signing, scope and schema validation.",
    "runtime": "The signed log, lifecycle rules and the projection for each viewer.",
    "edges": "The A2A transport: cards, the member client and the host edge.",
    "vault": "Private data, typed queries and private set intersection.",
    "steward": "The independent checker: fixed policies, then a model audit.",
    "gardener": "Deterministic planning from needs and offers.",
    "models": "The model gateway, price table and cost meter.",
    "surfaces": "The closed catalog and its renderers.",
    "server": "The reference host and the room engine.",
    "mcp_server": "The MCP tools and the MCP App view.",
    "channels": "Message channels.",
    "mint": "Turns a short recording into a policy-checked MCP server.",
    "packs": "Discipline Packs: loading, validation and signing.",
    "conformance": "The black-box conformance runner.",
    "acceptance": "Acceptance runners for the kit.",
    "cli": "The `coalitionkit` command.",
}
MODULES = {"mcp_server": "coalitionkit_mcp"}


def cell(value: object) -> str:
    return " ".join(str(value).split()).replace("|", "\\|")


def table(head: list[str], rows: Iterable[list[object]]) -> str:
    lines = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    lines += ["| " + " | ".join(cell(c) for c in row) + " |" for row in rows]
    return "\n".join(lines) + "\n"


def catalog_pages() -> dict[Path, str]:
    data = json.loads((ROOT / "spec/catalog/coalitionkit-v0_9.json").read_text(encoding="utf-8"))
    comps: dict[str, dict[str, Any]] = data["components"]
    rules = data["rules"]
    pages: dict[Path, str] = {}
    rows: list[list[object]] = []
    for number, title in data["families"].items():
        members = {k: v for k, v in comps.items() if v["family"] == number}
        rows.append([f"[{title}](family-{number}.md)", len(members)])
        body = (
            f"# {title}\n\n{NOTE}{len(members)} components in the `{data['catalogId']}` catalog.\n"
        )
        for name, spec in members.items():
            body += f"\n## {name}\n\n"
            if spec.get("doors"):
                body += f"Doors: {', '.join(spec['doors'])}.\n\n"
            if spec.get("states"):
                body += f"States: {', '.join(str(s) for s in spec['states'])}.\n\n"
            if spec.get("events"):
                body += "Events: " + ", ".join(f"`{e}`" for e in spec["events"]) + ".\n\n"
            props: dict[str, dict[str, Any]] = spec.get("props") or {}
            if props:
                body += table(
                    ["Prop", "Type", "Notes"],
                    [[f"`{p}`", v.get("type", ""), v.get("doc", "")] for p, v in props.items()],
                )
        pages[DOCS / "catalog" / f"family-{number}.md"] = body
    index = (
        f"# Component catalog\n\n{NOTE}"
        f"A surface is built only from these {len(comps)} components. The catalog is closed: a "
        f"renderer refuses any other catalog ID, and a tree that names an unknown component is "
        f"refused. Raw HTML is {rules['html']}.\n\n"
        f"A tree has at most {rules['maxComponents']} components, {rules['maxDepth']} levels deep. "
        f"A number on screen is bound as `{{value, event_ref}}`, pointing at the event it came "
        "from.\n\n"
        f"The source is [`spec/catalog/coalitionkit-v0_9.json`]({BLOB}/spec/catalog/"
        "coalitionkit-v0_9.json).\n\n"
    )
    pages[DOCS / "catalog" / "index.md"] = index + table(["Family", "Components"], rows)
    return pages


def field_rows(model: Any, skip: frozenset[str] = frozenset()) -> list[list[object]]:
    rows: list[list[object]] = []
    fields: dict[str, FieldInfo] = model.model_fields
    for name, info in fields.items():
        if name in skip:
            continue
        kind = str(info.annotation).replace("typing.", "").replace("pydantic.types.", "")
        kind = kind.replace("<class '", "").replace("'>", "")
        secret = "SecretStr" in kind
        if info.default_factory is not None or secret:
            default: Any = "set at start" if not secret else "none (secret)"
        else:
            value: Any = info.default
            default = "none" if value is None else value
            if isinstance(value, Path):  # never the path of the checkout that wrote the page
                default = value.resolve().relative_to(ROOT).as_posix()
            if isinstance(value, set):
                default = sorted(str(v) for v in cast(set[Any], value))
        rows.append([f"`COALITIONKIT_{name.upper()}`", f"`{kind}`", f"`{default}`"])
    return rows


def settings_page() -> dict[Path, str]:
    from coalitionkit_models.settings import Settings as ModelSettings
    from coalitionkit_server.settings import Settings as ServerSettings

    body = (
        f"# Environment and settings\n\n{NOTE}"
        "Every setting comes from an environment variable with the prefix `COALITIONKIT_`. "
        "Secrets never appear in logs, errors or `repr`.\n\n"
        "`coalitionkit up` sets its own host settings and reads only the model keys below. "
        "`coalitionkit server serve` reads all of them.\n\n"
        "## Host\n\n" + table(["Variable", "Type", "Default"], field_rows(ServerSettings))
    )
    body += "\n## Models\n\n" + table(["Variable", "Type", "Default"], field_rows(ModelSettings))
    return {DOCS / "settings.md": body}


def help_text(*words: str) -> str:
    done = subprocess.run(
        [sys.executable, "-m", "coalitionkit_cli.main", *words, "--help"],
        capture_output=True,
        text=True,
        check=False,
        cwd=ROOT,
        env={**os.environ, "COLUMNS": "90", "NO_COLOR": "1", "PYTHON_COLORS": "0"},
    )
    return (done.stdout or done.stderr).strip().replace("__main__.py", "coalitionkit")


def cli_page() -> dict[Path, str]:
    body = f"# Command line\n\n{NOTE}The `coalitionkit` command comes with the package.\n"
    for words in ([], ["up"], ["server"], ["server", "serve"], ["pack"], ["conform"]):
        title = " ".join(["coalitionkit", *words])
        body += f"\n## `{title}`\n\n```text\n{help_text(*words)}\n```\n"
    return {DOCS / "cli.md": body}


def mcp_page() -> dict[Path, str]:
    from coalitionkit_mcp.resources import CHARTER_URI, LOG_URI, TASKS_URI
    from coalitionkit_mcp.server import CONSENT_WRITES, PLAIN_WRITES, VIEW_READS, WEB_READS
    from coalitionkit_mcp.tools_read import my_view

    groups = {
        "Read": [my_view, *VIEW_READS],
        "Act": list(PLAIN_WRITES),
        "Ask the person": list(CONSENT_WRITES),
        "Search the web": list(WEB_READS),
    }
    body = (
        f"# MCP tools and resources\n\n{NOTE}"
        "A member reaches the host at `<host>/mcp` with its viewer token as a bearer token. "
        "Each member sees only its own view. To connect a host, see "
        "[Bring your own agent over MCP](../guides/mcp-agents.md).\n"
    )
    for title, tools in groups.items():
        body += f"\n## {title}\n\n"
        rows: list[list[object]] = []
        for tool in tools:
            params = [
                p
                for p in inspect.signature(tool).parameters
                if p not in {"ctx", "answer", "revision"}
            ]
            rows.append(
                [
                    f"`{tool.__name__}`",
                    ", ".join(f"`{p}`" for p in params),
                    (inspect.getdoc(tool) or "").split("\n\n")[0],
                ]
            )
        body += table(["Tool", "Arguments", "What it does"], rows)
    body += (
        "\nIn the tools under **Ask the person**, the host asks the person inside the call. Only "
        "their answer is signed. No tool argument can stand in for it.\n"
        "\n## Resources\n\n"
    )
    body += table(
        ["URI", "What it holds"],
        [
            [f"`{CHARTER_URI}`", "The charter."],
            [f"`{TASKS_URI}`", "This member's tasks."],
            [f"`{LOG_URI}`", "The log, as this member may see it."],
        ],
    )
    return {DOCS / "mcp.md": body}


def events_page() -> dict[Path, str]:
    folder = ROOT / "spec/schemas/coalition/v0"
    rows: list[list[object]] = []
    skip = {"common", "envelope", "projection", "error"}
    for path in sorted(folder.glob("*.json")):
        if path.stem in skip:
            continue
        schema = json.loads(path.read_text(encoding="utf-8"))
        required = ", ".join(f"`{r}`" for r in schema.get("required", []))
        link = f"[`{path.name}`]({BLOB}/spec/schemas/coalition/v0/{path.name})"
        rows.append([f"`coalition.{path.stem}`", required, link])
    body = (
        f"# Event types\n\n{NOTE}"
        "Every message is a signed envelope in the log. The full rules are in "
        "[the protocol](protocol.md).\n\n"
    )
    return {DOCS / "events.md": body + table(["Type", "Required payload fields", "Schema"], rows)}


def schemas_page() -> dict[Path, str]:
    folder = ROOT / "spec/schemas/coalition/v0"
    rows: list[list[object]] = []
    for path in sorted(folder.glob("*.json")):
        schema = json.loads(path.read_text(encoding="utf-8"))
        link = f"[`{path.name}`]({BLOB}/spec/schemas/coalition/v0/{path.name})"
        rows.append([link, f"`{schema['$id']}`", schema.get("description", "")])
    body = (
        f"# Schemas\n\n{NOTE}"
        "Every message is checked against a JSON Schema (2020-12). A pack adds fields only inside "
        "`ext`, and never changes these. A message that fails is refused as `schema_invalid`.\n\n"
    )
    return {DOCS / "schemas.md": body + table(["File", "Id", "What it describes"], rows)}


def spec_section(heading: str) -> str:
    """One level-two section of the protocol, so a page can never drift from it."""
    spec = (ROOT / "spec/coalition-protocol-v0.1.md").read_text(encoding="utf-8")
    start = spec.index(f"\n## {heading}\n") + 1
    end = spec.find("\n## ", start)
    return spec[start:] if end == -1 else spec[start:end]


def spec_pages() -> dict[Path, str]:
    pack = (
        f"# Pack format\n\n{NOTE}"
        "This is the section of [the protocol](protocol.md) that defines Discipline Packs. For a "
        "walk through it, see [Write a Discipline Pack](../guides/packs/index.md).\n\n"
    )
    conformance = (
        f"# Conformance levels\n\n{NOTE}"
        "The conformance runner tests any implementation from the outside, using signed protocol "
        "messages. It never imports the server or the runtime, so it can test a host or a member "
        "written by someone else. A report says `pass`, `fail` or `not run` for each test, and "
        "incomplete coverage never exits 0.\n\n"
        "## Run it\n\n"
        "Test a host that uses the reference admin routes:\n\n"
        "```sh\ncoalitionkit conform --target CARD_URL --level host --operator reference "
        "--admin-token-file TOKEN_FILE\n```\n\n"
        "Test a host using invitations its operator gave you:\n\n"
        "```sh\ncoalitionkit conform --target CARD_URL --level host --invite CODE1 --invite CODE2 "
        "--redeem-url REDEMPTION_URL\n```\n\n"
        "The token file holds only the admin token. It is sent only to admin routes on the "
        "target's own origin, and never appears in a report. The levels are `member`, `vault`, "
        "`host` and `surface`.\n\n"
        "Other implementations can provide their own operator adapter. See the "
        f"[package's README]({BLOB.replace('/blob/', '/tree/')}/packages/conformance).\n\n"
    )
    return {
        DOCS / "pack-format.md": pack + spec_section("Discipline Pack format"),
        DOCS / "conformance.md": conformance + spec_section("Conformance tests"),
    }


def python_pages() -> dict[Path, str]:
    pages: dict[Path, str] = {}
    rows: list[list[object]] = []
    for name, what in PACKAGES.items():
        module = MODULES.get(name, f"coalitionkit_{name}")
        rows.append([f"[`{name}`]({name}.md)", f"`{module}`", what])
        pages[DOCS / "python" / f"{name}.md"] = (
            f"# {name}\n\n{NOTE}{what}\n\n::: {module}\n"
            "    options:\n      show_submodules: false\n"
        )
    pages[DOCS / "python" / "index.md"] = (
        f"# Python API\n\n{NOTE}The API each package exports. The `coalitionkit` package installs "
        "all of them.\n\n" + table(["Package", "Module", "What it holds"], rows)
    )
    return pages


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if a page is out of date")
    args = parser.parse_args()
    pages = {
        **catalog_pages(),
        **settings_page(),
        **cli_page(),
        **mcp_page(),
        **events_page(),
        **schemas_page(),
        **spec_pages(),
        **python_pages(),
    }
    stale: list[str] = []
    for path, text in pages.items():
        text = text.rstrip() + "\n"
        current = path.read_text(encoding="utf-8") if path.exists() else None
        if current == text:
            continue
        stale.append(str(path.relative_to(ROOT)))
        if not args.check:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8", newline="\n")
    print(f"{len(pages)} pages; {len(stale)} {'stale' if args.check else 'written'}")
    if args.check and stale:
        print("\n".join(stale))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
