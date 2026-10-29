# SPDX-License-Identifier: Apache-2.0
"""A throwaway ``postgres:18`` container on a random local port, for the chaos runs.

18 is the newest stable major on Docker Hub (19 is still a release candidate). The container is
started without ``--rm`` so it can be killed and started again with its data; it is always
removed, with its volume, when the block ends.
"""

from __future__ import annotations

import shutil
import subprocess
import time
from types import TracebackType

import psycopg
from psycopg import sql

from coalitionkit_edges.a2a.testing import free_port

IMAGE = "postgres:18"
PASSWORD = "acceptance"  # a throwaway container on a loopback port; not a secret


def docker_missing_reason() -> str | None:
    """Why Docker cannot be used, or None when it can."""
    if shutil.which("docker") is None:
        return "Docker is not installed (no docker command)"
    try:
        done = subprocess.run(
            ["docker", "info", "--format", "{{.ServerVersion}}"],
            capture_output=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return f"Docker did not answer: {type(exc).__name__}"
    return None if done.returncode == 0 else "the Docker daemon is not running"


def docker(*args: str, timeout: float = 120.0) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["docker", *args], capture_output=True, text=True, timeout=timeout, check=False
    )


class PostgresContainer:
    def __init__(self) -> None:
        self.port = free_port()
        self.name = f"coalitionkit-acceptance-{self.port}"
        self.started = False

    @property
    def url(self) -> str:
        return f"postgresql://postgres:{PASSWORD}@127.0.0.1:{self.port}/postgres"

    def __enter__(self) -> PostgresContainer:
        done = docker(
            "run", "-d", "--name", self.name, "-e", f"POSTGRES_PASSWORD={PASSWORD}",
            "-p", f"127.0.0.1:{self.port}:5432", IMAGE,
        )  # fmt: skip
        if done.returncode != 0:
            raise RuntimeError("could not start postgres: " + done.stderr.strip()[:300])
        self.started = True
        self.wait_ready(initial=True)
        return self

    def __exit__(
        self,
        kind: type[BaseException] | None,
        error: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        docker("rm", "-f", "-v", self.name)

    def wait_ready(self, timeout: float = 90.0, *, initial: bool = False) -> float:
        """Wait for a real connection; the first start restarts once after initialising."""
        started = time.perf_counter()
        until = time.monotonic() + timeout
        while time.monotonic() < until:
            settled = not initial or self.initialised()
            if settled:
                try:
                    with psycopg.connect(self.url, connect_timeout=2) as connection:
                        connection.execute("SELECT 1")
                    return time.perf_counter() - started
                except psycopg.Error:
                    pass
            time.sleep(0.1)
        raise RuntimeError("postgres did not become ready")

    def initialised(self) -> bool:
        """The image starts a temporary server to initialise, then the real one."""
        done = docker("logs", self.name)
        tail = (done.stdout + done.stderr).partition("init process complete")[2]
        return "ready to accept connections" in tail

    def kill(self) -> None:
        """SIGKILL the container: no shutdown, every connection gone."""
        docker("kill", self.name)

    def start(self) -> float:
        """Start the killed container again; return the seconds until it takes connections."""
        started = time.perf_counter()
        done = docker("start", self.name)
        if done.returncode != 0:
            raise RuntimeError("could not restart postgres: " + done.stderr.strip()[:300])
        self.wait_ready()
        return time.perf_counter() - started

    def new_database(self) -> str:
        """A fresh database in the container (a server remembers its public URL per database)."""
        name = f"db{time.time_ns()}"
        with psycopg.connect(self.url, autocommit=True) as connection:
            connection.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
        return self.url.rsplit("/", 1)[0] + "/" + name

    def drop_connections(self) -> int:
        """Terminate every other backend, as a network drop or a failover would."""
        with psycopg.connect(self.url, autocommit=True) as connection:
            rows = connection.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE pid <> pg_backend_pid() AND backend_type = 'client backend'"
            ).fetchall()
        return len(rows)
