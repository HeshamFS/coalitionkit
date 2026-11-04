// SPDX-License-Identifier: Apache-2.0
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { type Standing, StandingRoom, standingLine } from "./StandingRoom";

function standing(over: Partial<Standing> = {}): Standing {
  return {
    goal: "A one-hour world tour",
    code: "ABC-DEFG",
    link: "http://host/join#ABC-DEFG",
    seats: 12,
    filled: 3,
    open: true,
    ends_at: "2030-01-01T00:00:00Z",
    minutes_left: 11.6,
    pack: "world-tour",
    budget_usd: 1,
    spent_usd: 0.05,
    ...over,
  };
}

function hostAnswers(room: Standing | null) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => ({ ok: true, json: async () => ({ room }) })),
  );
}

afterEach(() => vi.unstubAllGlobals());

describe("StandingRoom", () => {
  it("shows the room forming now with its seats and code, and joins by the code", async () => {
    hostAnswers(standing());
    const onJoin = vi.fn();
    const onFound = vi.fn();
    render(<StandingRoom onJoin={onJoin} onFound={onFound} />);
    expect(await screen.findByText("A one-hour world tour")).toBeTruthy();
    expect(screen.getByText("3 of 12 seats · ends in 12 min")).toBeTruthy();
    expect(screen.getByText("ABC-DEFG").tagName).toBe("CODE");
    await userEvent.click(screen.getByRole("button", { name: "Take a seat" }));
    expect(onJoin).toHaveBeenCalledWith("ABC-DEFG");
    expect(onFound).toHaveBeenCalledWith(true);
  });

  it("shows nothing when the host keeps no standing room", async () => {
    hostAnswers(null);
    const onFound = vi.fn();
    const { container } = render(<StandingRoom onJoin={() => {}} onFound={onFound} />);
    await vi.waitFor(() => expect(onFound).toHaveBeenCalledWith(false));
    expect(container.textContent).toBe("");
  });

  it("offers no seat once the room is under way", () => {
    expect(standingLine(standing({ open: false, minutes_left: 4 }))).toBe(
      "3 of 12 seats · under way, ends in 4 min",
    );
  });
});
