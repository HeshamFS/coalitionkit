// SPDX-License-Identifier: Apache-2.0
import { A2uiSurface } from "@a2ui/react/v0_9";
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { examples as f02 } from "../components/f02/examples";
import { examples as f03 } from "../components/f03/examples";
import { examples as f04 } from "../components/f04/examples";
import { SurfaceBook } from "../feed/surfaces";
import { Sheet02 } from "./sheets/Sheet02";
import { Sheet03 } from "./sheets/Sheet03";
import { Sheet04 } from "./sheets/Sheet04";

afterEach(cleanup);
describe.each([
  ["02", Sheet02, f02],
  ["03", Sheet03, f03],
  ["04", Sheet04, f04],
] as const)("sheet %s", (_family, Sheet, examples) => {
  it("renders every family component through the catalog without fallback", () => {
    const { container } = render(<Sheet />);
    expect(container.querySelector("[data-fallback]")).toBeNull();
    expect(container.textContent).not.toContain("Unresolved child reference");
    if (_family === "02")
      expect(container.querySelector('.ck-stages [aria-current="step"]')).toHaveTextContent(
        "Decide",
      );
    for (const name of Object.keys(examples)) {
      expect(container.querySelector(`section[data-component="${name}"]`), name).not.toBeNull();
    }
  });
});

const examples = { ...f02, ...f03, ...f04 };
function mount(name: string, overrides: Record<string, unknown> = {}) {
  const action = vi.fn();
  const book = new SurfaceBook(action);
  book.apply("test", [
    { version: "v0.9", createSurface: { surfaceId: "test", catalogId: "coalitionkit/v0_9" } },
    {
      version: "v0.9",
      updateComponents: {
        surfaceId: "test",
        components: [{ id: "root", component: name, ...examples[name], ...overrides }],
      },
    },
  ]);
  const surface = book.list()[0];
  expect(surface?.fallback).toBe(false);
  if (!surface) throw new Error("Missing surface");
  render(<A2uiSurface surface={surface.model} />);
  return action;
}
const cases = [
  ["AccountMenu", "Your agent", "account.pick"],
  ["BoardTemplate", "Task 1", "card.open"],
  ["ConsentTray", "Plan A · Review", "consent.open"],
  ["Deck", "Plans 2", "deck.select"],
  ["InviteCard", "Copy invite", "invite.copy"],
  ["JoinScreen", "Observe instead", "observe"],
  ["LensCard", "Tap: on my way", "gesture"],
  ["MessageDoor", "1 · Plan 1", "reply"],
  ["NotificationCenter", "Mark all read", "notifications.read"],
  ["PhoneShell", "Plans", "tab.select"],
  ["RoomShell", "Invite", "invite.open"],
  ["SplitView", "Task 1", "split.select"],
  ["VoiceTurn", "Tell me more", "voice.more"],
  ["WiringDrawer", "Verify chain", "wiring.verify"],
  ["AgentHandoff", "Yes, share", "handoff.answer"],
  ["AgentStatus", "Pause", "agent.pause"],
  ["AskAgent", "Ask", "coalition.query"],
  ["CallInvite", "Join", "call.join"],
  ["CallSummary", "Review and post", "summary.post"],
  ["CoalitionThread", "Can we finish together by 10:00?", "message.open"],
  ["Composer", "Record", "voice.record"],
  ["DiarizedTranscript", "Review extracted items", "extract.review"],
  ["ElicitationForm", "Cancel", "elicitation.cancel"],
  ["NegotiationTheatre", "Inspect turn", "turn.inspect"],
  ["ToolCall", "✓ coalition.my_view · done", "toolcall.expand"],
  ["VideoCall", "Mute", "call.mute"],
  ["VoiceCall", "Speaker", "call.speaker"],
  ["AcceptanceForm", "Leave instead", "leave"],
  ["AvailabilityGrid", "Import calendar", "availability.import"],
  ["DocumentShare", "Share as evidence", "evidence.share"],
  ["FeedbackForm", "Save", "feedback.save"],
  ["LimitField", "Edit in vault", "limit.change"],
  ["NeedForm", "Publish need", "coalition.need"],
  ["OfferForm", "Publish offer", "coalition.offer"],
  ["OwnerSign", "Confirm with passkey", "sign.confirm"],
  ["Receipt", "Verify myself", "receipt.verify"],
  ["ReviewStep", "Publish charter", "wizard.finish"],
  ["ValidationSummary", "Add a goal", "field.focus"],
  ["Wizard", "Next", "wizard.next"],
];
it.each(cases)("%s dispatches %s as %s", (component, button, name) => {
  const action = mount(component ?? "");
  fireEvent.click(screen.getAllByRole("button", { name: button })[0] as HTMLElement);
  expect(action).toHaveBeenCalled();
  expect(JSON.stringify(action.mock.calls[0])).toContain(`"name":"${name}"`);
});
it("composers send entered text and scope", () => {
  const action = mount("Composer");
  fireEvent.change(screen.getByLabelText("Message"), { target: { value: "A new message" } });
  fireEvent.click(screen.getByRole("button", { name: "Send" }));
  expect(JSON.stringify(action.mock.calls)).toContain('"text":"A new message"');
  expect(JSON.stringify(action.mock.calls)).toContain('"scope":"me"');
});
it.each([
  ["AgentDock", "Message your agent", "Send", "agent.say"],
  ["EntryComposer", "Your goal", "Start a coalition", "coalition.create"],
])("%s sends user input", (name, field, button, event) => {
  const action = mount(name ?? "");
  fireEvent.change(screen.getByLabelText(field ?? ""), { target: { value: "A shared goal" } });
  fireEvent.click(screen.getByRole("button", { name: button }));
  expect(JSON.stringify(action.mock.calls)).toContain(`"name":"${event}"`);
  expect(JSON.stringify(action.mock.calls)).toContain("A shared goal");
});
it("Form submits editable values", () => {
  const action = mount("Form");
  fireEvent.change(screen.getByLabelText("Goal *"), { target: { value: "Finish task" } });
  fireEvent.click(screen.getByRole("button", { name: "Submit" }));
  expect(JSON.stringify(action.mock.calls)).toContain('"goal":"Finish task"');
});
it("Message retries only failed messages", () => {
  const action = mount("Message", { state: "failed" });
  fireEvent.click(screen.getByRole("button", { name: "Retry" }));
  expect(JSON.stringify(action.mock.calls)).toContain('"name":"message.retry"');
});
it("ConsentSeal allows keyboard review without manufacturing a signature", () => {
  const action = mount("ConsentSeal");
  fireEvent.keyDown(screen.getByRole("button", { name: "Hold to review consent" }), {
    key: "Enter",
  });
  expect(action).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Confirm" }));
  expect(JSON.stringify(action.mock.calls)).toContain('"name":"decide"');
  expect(JSON.stringify(action.mock.calls)).not.toContain('"signature"');
});
it("ConsentSeal cancels an early release and requests review only after the full hold", () => {
  vi.useFakeTimers();
  try {
    const action = mount("ConsentSeal");
    const button = screen.getByRole("button", { name: "Hold to review consent" });
    fireEvent.pointerDown(button);
    act(() => vi.advanceTimersByTime(600));
    fireEvent.pointerUp(button);
    act(() => vi.advanceTimersByTime(1000));
    expect(screen.queryByRole("group", { name: "Confirm consent" })).toBeNull();
    fireEvent.pointerDown(button);
    act(() => vi.advanceTimersByTime(1200));
    expect(screen.getByRole("group", { name: "Confirm consent" })).toBeInTheDocument();
    expect(action).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Confirm" }));
    expect(JSON.stringify(action.mock.calls)).toContain('"name":"decide"');
  } finally {
    vi.useRealTimers();
  }
});
it("requires acknowledgement before charter acceptance and fails closed after the deadline", () => {
  const action = mount("AcceptanceForm", { decision_deadline: "2000-01-01T00:00:00Z" });
  fireEvent.click(screen.getByRole("checkbox"));
  expect(screen.getByRole("button", { name: "Accept revision 3" })).toBeDisabled();
  expect(action).not.toHaveBeenCalled();
});
it("never renders message text hidden by a redaction", () => {
  mount("Message", { text: "Private value", state: "redacted" });
  expect(screen.queryByText("Private value")).toBeNull();
});
it("does not collect private form values without a local vault connection", () => {
  mount("Form");
  expect(screen.getByPlaceholderText("Set in your local vault")).toBeDisabled();
});
it("routes owner signing intent to trusted request review", () => {
  const action = mount("OwnerSign");
  fireEvent.click(screen.getByRole("button", { name: "Confirm with passkey" }));
  expect(JSON.stringify(action.mock.calls)).toContain('"name":"sign.confirm"');
  expect(JSON.stringify(action.mock.calls)).toContain('"name":"open"');
  expect(JSON.stringify(action.mock.calls)).toContain('"event_ref":"example:44"');
});
