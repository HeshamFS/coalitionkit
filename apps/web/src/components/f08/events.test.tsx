// SPDX-License-Identifier: Apache-2.0
import type { ComponentContext } from "@a2ui/web_core/v0_9";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { examples as e09 } from "../f09/examples";
import { render as r09 } from "../f09/render";
import { examples as e10 } from "../f10/examples";
import { render as r10 } from "../f10/render";
import { examples as e11 } from "../f11/examples";
import { render as r11 } from "../f11/render";
import { examples as e08 } from "./examples";
import { render as r08 } from "./render";
import type { Props } from "./shared";

const examples = [...e08, ...e09, ...e10, ...e11];
const renderer = (name: string) =>
  e08.some((e) => e.name === name)
    ? r08
    : e09.some((e) => e.name === name)
      ? r09
      : e10.some((e) => e.name === name)
        ? r10
        : r11;
afterEach(cleanup);
function draw(name: string, override: Props = {}) {
  const p = { ...examples.find((e) => e.name === name)?.states[0]?.props, ...override };
  const dispatchAction = vi.fn();
  render(renderer(name)(name, p, { dispatchAction } as unknown as ComponentContext));
  return { p, dispatchAction };
}
const actions = [
  ["ApprovalButton", "Approve", "approve"],
  ["CommitmentCard", "Approve", "commit.approve"],
  ["ConsentCard", "Accept", "decide"],
  ["DecisionLog", "10:42", "entry.open"],
  ["DisclosureLadder", "exact", "disclosure.raise"],
  ["DurableConsent", "Revoke", "grant.revoke"],
  ["PrivateField", "Reveal", "field.reveal"],
  ["ProjectionNote", "Verify", "projection.verify"],
  ["RedactionDiff", "Appeal", "redaction.appeal"],
  ["StaleNotice", "Review revision 3", "subject.review"],
  ["VaultCard", "Export", "vault.export"],
  ["WhatOthersKnow", "Export this view", "view.export"],
  ["ActivityStream", "log entry 41", "item.open"],
  ["ChainView", "Verify chain", "chain.verify"],
  ["ErrorNotice", "Retry", "error.retry"],
  ["EventRow", "Member A accepted", "entry.open"],
  ["EvidenceCard", "Open evidence", "evidence.open"],
  ["LiveDocks", "Next", "dock.open"],
  ["LogStream", "41", "entry.open"],
  ["ReceiptBadge", "ok", "receipt.verify"],
  ["RippleBanner", "What changed", "ripple.open"],
  ["StewardVerdict", "Verify signature", "verdict.verify"],
  ["VerifyPanel", "Run verification", "verify.run"],
  ["AttackTests", "Fix and re-run", "tests.rerun"],
  ["CaptureCard", "Start recording", "capture.start"],
  ["DeviceAlarm", "Stop the run", "alarm.stop"],
  ["DeviceReading", "Export CSV", "reading.export"],
  ["MintPipeline", "Open capture:1", "stage.open"],
  ["MintedAgentCard", "Logs", "agent.logs"],
  ["PublishApproval", "Approve and sign", "publish"],
  ["ScheduleTwin", "Hold", "slot.hold"],
  ["ChannelHandoff", "Open phone", "handoff.open"],
  ["ChannelSettings", "Save quiet hours", "quiet.set"],
  ["CoalitionArchive", "Coalition 1", "archive.open"],
  ["DissolveSummary", "Download sealed log", "log.download"],
  ["ExportControl", "Download ZIP", "export.zip"],
  ["LessonReview", "Save selected lessons", "lessons.save"],
  ["MessageTemplate", "Yes", "reply"],
  ["NotificationCard", "Coalition 1", "notification.open"],
  ["SkillCard", "Start from this skill", "coalition.create"],
];
describe("catalog named events", () => {
  it.each(actions)("%s emits %s as %s", (name, label, event) => {
    const { dispatchAction } = draw(name ?? "");
    fireEvent.click(
      screen.getAllByRole("button", { name: new RegExp(label ?? "") })[0] as HTMLElement,
    );
    expect(dispatchAction).toHaveBeenCalledWith({
      event: { name: event, context: expect.any(Object) },
    });
  });
  it("keeps revision-bound consent data intact", () => {
    const { p, dispatchAction } = draw("ConsentCard");
    fireEvent.click(screen.getByRole("button", { name: "Accept" }));
    expect(dispatchAction).toHaveBeenCalledWith({
      event: {
        name: "decide",
        context: {
          subject: p.subject,
          consent: true,
          consequence: p.consequence,
          decision_deadline: p.decision_deadline,
        },
      },
    });
  });
  it("prevents expired approval and publication with failed tests", () => {
    const first = draw("ApprovalButton", { decision_deadline: "2020-01-01T00:00:00Z" });
    fireEvent.click(screen.getByRole("button", { name: "Approve" }));
    expect(first.dispatchAction).not.toHaveBeenCalled();
    cleanup();
    const second = draw("PublishApproval", { tests: { state: "failed" } });
    fireEvent.click(screen.getByRole("button", { name: "Approve and sign" }));
    expect(second.dispatchAction).not.toHaveBeenCalled();
  });
  it("emits reconnect with the run reference", () => {
    const { dispatchAction } = draw("ConnectionStatus", { feed: "offline", run: "r2" });
    fireEvent.click(screen.getByRole("button", { name: "Reconnect" }));
    expect(dispatchAction).toHaveBeenCalledWith({
      event: { name: "feed.reconnect", context: { run: "r2" } },
    });
  });
  it("emits mask edits with the region and edited label", () => {
    const { dispatchAction } = draw("MediaWithMasks", {
      media_ref: "vault:media",
      labels: [{ mask: "m1", label: "display" }],
    });
    const input = screen.getByRole("textbox");
    fireEvent.change(input, { target: { value: "Control 1" } });
    fireEvent.blur(input);
    expect(dispatchAction).toHaveBeenCalledWith({
      event: { name: "mask.label", context: { id: "m1", label: "Control 1" } },
    });
  });
  it("emits channel settings from the selected control", () => {
    const { dispatchAction } = draw("ChannelSettings");
    fireEvent.change(screen.getAllByRole("combobox")[0] as HTMLElement, {
      target: { value: "off" },
    });
    expect(dispatchAction).toHaveBeenCalledWith({
      event: { name: "channel.set", context: { kind: "Push", level: "off" } },
    });
  });
});
