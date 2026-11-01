# SPDX-License-Identifier: Apache-2.0
"""The hosted brain stops when commitment tools report pending human consent."""

from members.hosted_member.brain import HostedBrain, PolicyTransport, _run_tool
from members.kit.brain import work_instruction

from coalitionkit_models import ModelGateway, Settings


class PendingTools:
    def __init__(self) -> None:
        self.requests: list[str] = []

    async def make_offer(self, need_id: str, minutes: int, money: int, effort: str) -> str:
        return "refused: not an offer turn"

    async def commit_to_task(self, task_id: str) -> str:
        self.requests.append(task_id)
        return "pending: waiting for owner approval in the room"

    async def report_done(self, task_id: str, evidence_ref: str) -> str:
        raise AssertionError("pending consent must never authorize work")


async def test_hosted_brain_stops_at_pending_consent() -> None:
    gateway = ModelGateway(Settings(), transport=PolicyTransport())
    brain = HostedBrain(gateway, "demo", "p1")
    tools = PendingTools()
    uses = []
    try:
        await brain.run(
            work_instruction("p1", [{"task_id": "t1", "label": "task"}]), tools, uses.append
        )
        assert tools.requests == ["t1"]
        assert uses
        assert (await _run_tool(tools, "decide", {"consent": True})).startswith("refused")
        assert (await _run_tool(tools, "propose", {})).startswith("refused")
    finally:
        await gateway.aclose()
