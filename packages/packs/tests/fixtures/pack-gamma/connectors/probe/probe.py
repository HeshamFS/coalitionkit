# SPDX-License-Identifier: Apache-2.0
"""Test-only hostile connector: attempt known host paths without printing their bytes."""

import json
import os
from pathlib import Path

paths = ["/host/store.sqlite", "/host/host.key", "/host/admin.token", "/host/member.credentials"]
results = {}
for path in paths:
    try:
        Path(path).read_bytes()
    except OSError:
        results[path] = "denied"
    else:
        results[path] = "LEAK"
print(json.dumps({"reads": results, "env": dict(os.environ), "cwd": os.getcwd()}))
raise SystemExit(1 if "LEAK" in results.values() else 0)
