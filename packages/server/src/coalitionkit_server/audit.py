# SPDX-License-Identifier: Apache-2.0
"""A dedicated async loop bridges the runtime's synchronous audit hook."""

import asyncio
from threading import Thread

from coalitionkit_contracts import Envelope
from coalitionkit_models import ModelGateway
from coalitionkit_models.settings import Settings as ModelSettings
from coalitionkit_runtime.steward import Verdict
from coalitionkit_steward import Steward

from .adapter import Document


class AuditLoop:
    def __init__(self) -> None:
        self.loop = asyncio.new_event_loop()
        self.thread = Thread(target=self.loop.run_forever, daemon=True)
        self.thread.start()

    def close(self) -> None:
        self.loop.call_soon_threadsafe(self.loop.stop)
        self.thread.join()
        self.loop.close()


class StewardAdapter:
    def __init__(self, steward: Steward, runner: AuditLoop) -> None:
        self.steward, self.runner = steward, runner

    def review(self, envelope: Document) -> Verdict:
        future = asyncio.run_coroutine_threadsafe(
            self.steward.review(Envelope.model_validate(envelope)), self.runner.loop
        )
        body = future.result().body
        return Verdict(body.action, body.policy_id, tuple(body.redact))


def gateway() -> ModelGateway:
    return ModelGateway(ModelSettings())
