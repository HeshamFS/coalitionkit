// SPDX-License-Identifier: Apache-2.0
import { A2uiSurface } from "@a2ui/react/v0_9";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { SurfaceBook } from "../feed/surfaces";
import { examples as e05, Sheet05 } from "./sheets/Sheet05";
import { examples as e06, Sheet06 } from "./sheets/Sheet06";
import { examples as e07, Sheet07 } from "./sheets/Sheet07";

afterEach(cleanup);
const fixtures = { ...e05, ...e06, ...e07 };
describe.each([
  ["05", Sheet05, e05],
  ["06", Sheet06, e06],
  ["07", Sheet07, e07],
] as const)("sheet %s", (_, Sheet, examples) => {
  it("renders every catalog example without fallback", () => {
    const { container } = render(<Sheet />);
    expect(container.querySelector("[data-fallback]")).toBeNull();
    for (const name of Object.keys(examples)) {
      expect(container.querySelector(`section[data-component="${name}"]`)).not.toBeNull();
    }
    expect(container.querySelectorAll(".drawn").length).toBe(
      Object.values(examples).reduce((sum, variants) => sum + variants.length, 0),
    );
  });
});
function surface(name: string, override: Record<string, unknown> = {}) {
  const dispatch = vi.fn(),
    book = new SurfaceBook(dispatch),
    props = { ...fixtures[name]?.[0]?.props, ...override };
  book.apply("test", [
    { version: "v0.9", createSurface: { surfaceId: "test", catalogId: "coalitionkit/v0_9" } },
    {
      version: "v0.9",
      updateComponents: {
        surfaceId: "test",
        components: [{ id: "root", component: name, ...props }],
      },
    },
    { version: "v0.9", updateDataModel: { surfaceId: "test", path: "/", value: {} } },
  ]);
  const entry = book.list()[0];
  expect(entry?.fallback).toBe(false);
  if (!entry) throw new Error("missing surface");
  render(<A2uiSurface surface={entry.model} />);
  return { dispatch, props };
}
const cases: [string, string, string, Record<string, unknown>, Record<string, unknown>?][] = [
  ["CoalitionHeader", "Charter r2", "charter.open", {}],
  ["CharterCard", "History", "charter.history", {}],
  ["ParticipantCard", "Member A", "participant.open", { participant: "Member A" }],
  ["ActsForGraph", "Agent B", "agent.inspect", { card: "Agent B" }],
  ["SeatRing", "Member A · owes", "seat.open", { participant: "Member A" }],
  ["Roster", "Remind Member C", "member.remind", { participant: "Member C" }],
  ["PackChip", "Shared resources", "pack.open", { pack: "pack1" }],
  ["InviteList", "Revoke", "invite.revoke", { participant: "Member E" }],
  ["InviteList", "Invite", "invite.send", { role: "member" }],
  ["TaskCard", "Open", "task.open", { task_id: "t3" }],
  ["TaskCard", "Mark done", "task.done", { task_id: "t3" }, { status: "committed" }],
  ["MatchView", "Thu 09:00", "match.inspect", { offer: "Thu 09:00" }],
  ["DependencyGraph", "t2", "task.open", { id: "t2" }],
  ["Gantt", "Member A · done", "task.open", { id: "t1" }],
  ["MapView", "Place 1", "map.select", { point: expect.objectContaining({ id: "place1" }) }],
  ["MapView", "Within 12 min", "map.area", { polygon: expect.any(Array) }],
  ["IndoorMap", "Room 1", "map.select", { room: "room1" }],
  ["PlacePicker", "Use Place 1", "place.pick", { ref: "Place 1" }],
  ["AgendaList", "Join", "item.action", { item: 3, action: "Join" }],
  ["CalendarWeek", "Export .ics", "calendar.export", { range: { start: "2031-06-03" } }],
  ["CalendarWeek", "Task 2", "event.open", { event: expect.objectContaining({ task: "Task 2" }) }],
];
it.each(cases)("%s sends %s as %s", (name, label, event, data, override) => {
  const { dispatch } = surface(name, override);
  fireEvent.click(screen.getByRole("button", { name: label }));
  expect(dispatch).toHaveBeenCalledWith(expect.objectContaining({ name: event, context: data }));
});
it("requires confirmation before leaving", () => {
  const { dispatch } = surface("LeaveControl");
  fireEvent.click(screen.getByRole("button", { name: "Leave…" }));
  expect(dispatch).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Confirm leave" }));
  expect(dispatch).toHaveBeenCalledWith(expect.objectContaining({ name: "coalition.leave" }));
});
it("toggles only owned checklist items", () => {
  const { dispatch } = surface("Checklist", {
    items: [
      { text: "Owned", done: false, by: "self" },
      { text: "Other", done: false, by: "p2" },
    ],
  });
  fireEvent.click(screen.getByRole("checkbox", { name: "Owned" }));
  expect(dispatch).toHaveBeenCalledWith(
    expect.objectContaining({ name: "item.toggle", context: { item: 0, done: true } }),
  );
  expect(screen.getByRole("checkbox", { name: "Other" })).toBeDisabled();
});
it("shares the selected precision and can stop", () => {
  const { dispatch } = surface("LocationShare");
  fireEvent.click(screen.getByLabelText("Only the place"));
  fireEvent.click(screen.getByRole("button", { name: "Share for this task" }));
  expect(dispatch).toHaveBeenCalledWith(
    expect.objectContaining({
      name: "location.share",
      context: expect.objectContaining({ precision: "place-only", until: "arrival" }),
    }),
  );
  fireEvent.click(screen.getByRole("button", { name: "Stop sharing" }));
  expect(dispatch).toHaveBeenLastCalledWith(expect.objectContaining({ name: "location.stop" }));
});
it("plan decisions carry the full subject to trusted consent", () => {
  const { dispatch, props } = surface("PlanCompare");
  fireEvent.click(screen.getByRole("button", { name: "Accept Plan A" }));
  expect(dispatch).toHaveBeenCalledWith(
    expect.objectContaining({
      name: "plan.decide",
      context: {
        proposal_set_id: "set1",
        subject: (props.plans as { subject: unknown }[])[0]?.subject,
      },
    }),
  );
  fireEvent.click(screen.getAllByRole("button", { name: "Details" })[0] as HTMLElement);
  expect(dispatch).toHaveBeenLastCalledWith(
    expect.objectContaining({ name: "plan.details", context: { id: "a" } }),
  );
});
it("tension choices carry the full revision-bound subject", () => {
  const { dispatch, props } = surface("TensionCard");
  fireEvent.click(screen.getByRole("button", { name: "Choose Results Monday" }));
  expect(dispatch).toHaveBeenCalledWith(
    expect.objectContaining({
      name: "tension.choose",
      context: { subject: props.subject, option: "a" },
    }),
  );
});
it("does not emit decisions after deadline", () => {
  const { dispatch } = surface("PlanCompare", { decision_deadline: "2000-01-01T00:00:00Z" });
  expect(screen.getByRole("button", { name: "Accept Plan A" })).toBeDisabled();
  expect(dispatch).not.toHaveBeenCalled();
});
