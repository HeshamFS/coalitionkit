// SPDX-License-Identifier: Apache-2.0
import { act, fireEvent, render, renderHook, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, expect, it, vi } from "vitest";
import type { OpenRequest } from "../feed/agent";
import { composeViewAs } from "./composeViewAs";
import { roomFixture } from "./fixture";
import { GermStepProvider } from "./germ";
import { MyPart } from "./mypart";
import { PRISM_OUT_MS, usePrism } from "./prism";
import { ViewAsMenu, ViewAsPanel } from "./viewAsPanel";

const Now = ({ children }: { children: ReactNode }) => (
  <GermStepProvider value={0}>{children}</GermStepProvider>
);
afterEach(() => vi.useRealTimers());

const CARD = "https://example.org/card";
const withSecret = {
  ...roomFixture,
  vault: { budget: "SECRET-BUDGET" },
  privacy_notes: [
    { participant: CARD, knows: "Availability", notKnows: "Private notes", because: "Consent" },
  ],
  events: {
    ...(roomFixture.events as object),
    x: { seq: 9, type: "coalition.observe", payload: { note: "SECRET-NOTE" } },
  },
};

it("composes the target from the viewer's own state only", () => {
  const view = composeViewAs(withSecret, CARD);
  expect(view).toMatchObject({ label: "Member 2", seat: 2, shared: null, agent: "" });
  expect(view?.caption).toBe("as Member 2 would see it, limited to what you may see");
  expect(view?.notes).toEqual([
    { knows: "Availability", notKnows: "Private notes", because: "Consent" },
  ]);
  expect(JSON.stringify(view)).not.toContain("SECRET");
  expect(composeViewAs(roomFixture, "someone-outside-my-scope")).toBeNull();
});

it("renders no field the viewer's state lacks", async () => {
  render(
    <Now>
      <ViewAsPanel state={withSecret} target={CARD} ready onBack={() => {}} />
    </Now>,
  );
  expect(
    await screen.findByText("as Member 2 would see it, limited to what you may see"),
  ).toBeInTheDocument();
  expect(
    await screen.findByText("Private to them. Nothing is shared with you."),
  ).toBeInTheDocument();
  expect(document.body.textContent).not.toMatch(/SECRET|Review item|Agent A/);
});

it("lists the other participants and picks one", () => {
  const onPick = vi.fn();
  render(<ViewAsMenu state={roomFixture} active={null} onPick={onPick} onLens={() => {}} />);
  fireEvent.click(screen.getByRole("button", { name: "View as…" }));
  expect(screen.queryByRole("button", { name: "Member A" })).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Member 2" }));
  expect(onPick).toHaveBeenCalledWith(CARD);
});

it("plays out, then commits the target (Prism)", () => {
  vi.useFakeTimers();
  const { result } = renderHook(() => usePrism());
  act(() => result.current.go("p2"));
  expect(result.current.phase).toBe("out");
  expect(result.current.target).toBeNull();
  act(() => {
    vi.advanceTimersByTime(PRISM_OUT_MS);
  });
  expect(result.current.target).toBe("p2");
  expect(result.current.phase).toBe("in");
  act(() => {
    vi.advanceTimersByTime(1300);
  });
  expect(result.current.phase).toBe("idle");
});

const ask: OpenRequest = {
  id: "r1",
  kind: "plan",
  subjectId: "plan-1",
  revision: 1,
  message: "Review this",
};

it("Approve opens the consent flow and never commits", async () => {
  const onApprove = vi.fn();
  const onSeePlans = vi.fn();
  render(
    <Now>
      <MyPart
        state={roomFixture}
        ready
        requests={[ask]}
        consent={null}
        onApprove={onApprove}
        onSeePlans={onSeePlans}
      />
    </Now>,
  );
  expect(await screen.findByText("Your agent asks before it commits you")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Approve" }));
  expect(onApprove).toHaveBeenCalledWith("r1");
  fireEvent.click(screen.getByRole("button", { name: "See other plans" }));
  expect(onSeePlans).toHaveBeenCalled();
});

it("shows the consent flow in place of the ask once opened", async () => {
  render(
    <Now>
      <MyPart
        state={roomFixture}
        ready
        requests={[ask]}
        consent={<div>trusted consent</div>}
        onApprove={() => {}}
        onSeePlans={() => {}}
      />
    </Now>,
  );
  expect(await screen.findByText("trusted consent")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Approve" })).not.toBeInTheDocument();
});

it("never substitutes another member for an unknown viewer", async () => {
  render(
    <Now>
      <MyPart
        state={{ ...roomFixture, viewer: undefined }}
        ready
        requests={[]}
        consent={null}
        onApprove={() => {}}
        onSeePlans={() => {}}
      />
    </Now>,
  );
  expect(await screen.findByText("Your part is not in this projection yet.")).toBeInTheDocument();
  expect(screen.queryByText("Member A")).not.toBeInTheDocument();
});
