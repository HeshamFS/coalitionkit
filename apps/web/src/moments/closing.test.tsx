// SPDX-License-Identifier: Apache-2.0
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { Dissolve, type DissolveEvent } from "./Dissolve";
import { Glasses } from "./Glasses";
import { GlassesPage } from "./GlassesPage";

const event: DissolveEvent = { reason: "completed", skills_written: ["skill-a", "skill-b"] };
const full = { tasks_closed: 3, tokens_revoked: 4, invitations_revoked: 1, vaults_erased: 2 };

describe("Dissolve", () => {
  it("claims no cleanup while the host has not reported", () => {
    render(<Dissolve event={event} />);
    expect(screen.getByText(/waiting for the host/)).toBeInTheDocument();
    expect(screen.queryByText(/closed|revoked|erased|Nothing kept/)).toBeNull();
  });

  it("shows every claim under a plain lead-in, and never claims more than the counts prove", () => {
    render(<Dissolve event={event} cleanup={full} />);
    expect(screen.getByText("3 tasks closed")).toBeInTheDocument();
    expect(screen.getByText("4 viewer links revoked")).toBeInTheDocument();
    expect(screen.getByText("1 invitation revoked")).toBeInTheDocument();
    expect(screen.getByText("2 hosted vaults erased")).toBeInTheDocument();
    expect(screen.getByText(/What the host reports it closed and erased/)).toBeInTheDocument();
    expect(screen.queryByText("Nothing kept")).toBeNull();
  });

  it("shows a claim only for a count the report has", () => {
    render(<Dissolve event={event} cleanup={{ tasks_closed: 0, vaults_erased: 1 }} />);
    expect(screen.getByText("0 tasks closed")).toBeInTheDocument();
    expect(screen.getByText("1 hosted vault erased")).toBeInTheDocument();
    expect(screen.queryByText(/viewer link/)).toBeNull();
    expect(screen.queryByText(/invitation/)).toBeNull();
    expect(screen.queryByText("Nothing kept")).toBeNull();
  });

  it("names the failed step, keeps the finished claims and offers Retry", async () => {
    const retry = vi.fn();
    render(
      <Dissolve
        event={event}
        cleanup={{ failed: "vault erase", done: { tasks_closed: 3, tokens_revoked: 4 } }}
        onRetry={retry}
      />,
    );
    expect(screen.getByText("Cleanup stopped at: vault erase")).toBeInTheDocument();
    expect(screen.getByText("3 tasks closed")).toBeInTheDocument();
    expect(screen.queryByText(/hosted vault/)).toBeNull();
    expect(screen.queryByText("Nothing kept")).toBeNull();
    await userEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(retry).toHaveBeenCalledTimes(1);
  });

  it("does not say nothing is kept when a failure carries all four counts", () => {
    render(<Dissolve event={event} cleanup={{ failed: "last step", done: full }} />);
    expect(screen.queryByText("Nothing kept")).toBeNull();
  });

  it("writes skill cards and leaves out numbers it was not given", () => {
    render(
      <Dissolve
        event={event}
        outcomes={["First outcome", "Second outcome"]}
        lessons={{ "skill-a": { title: "A lesson", summary: "What it says" } }}
        measured={{ calendarsShared: 0 }}
      />,
    );
    expect(screen.getAllByText("SKILL.md")).toHaveLength(2);
    expect(screen.getByText("A lesson")).toBeInTheDocument();
    expect(screen.getByText("skill-b")).toBeInTheDocument();
    expect(screen.getByText("First outcome")).toBeInTheDocument();
    expect(screen.getByText("0")).toBeInTheDocument();
    // A number the host did not give is left out, never a placeholder.
    expect(document.body.textContent).not.toMatch(/\[MEASURED\]|\[COST\]/);
    expect(screen.queryByText("model spend")).toBeNull();
    expect(screen.getByRole("img", { name: /coalition mark/ })).toBeInTheDocument();
  });

  it("shows the measured numbers it has and no cost when there is no meter", () => {
    render(<Dissolve event={event} measured={{ calendarsShared: 5, minutes: 47, vendors: 1 }} />);
    expect(screen.getByText("calendars shared")).toBeInTheDocument();
    expect(screen.getByText("47")).toBeInTheDocument();
    expect(screen.queryByText("model spend")).toBeNull();
    expect(document.body.textContent).not.toMatch(/\[MEASURED\]|\[COST\]/);
  });

  it("draws no strip at all when nothing was measured", () => {
    const { container } = render(<Dissolve event={event} />);
    expect(container.querySelector(".ck-dis-strip")).toBeNull();
  });

  it("headlines the reason the host gave", () => {
    render(<Dissolve event={{ reason: "deadline", skills_written: [] }} />);
    expect(screen.getByRole("heading")).toHaveTextContent("Deadline reached.");
    expect(screen.getByText("No lessons were written")).toBeInTheDocument();
  });
});

describe("Glasses", () => {
  it("shows the step, the instruction and the voice line", () => {
    render(<Glasses step={2} total={3} instruction="Do the thing" detail="Details here" />);
    expect(screen.getByText("Your step · 2 of 3")).toBeInTheDocument();
    expect(screen.getByText("Do the thing")).toBeInTheDocument();
    expect(screen.getByText("Details here")).toBeInTheDocument();
    expect(
      screen.getByText("Say “done” or “skip” · agents never press buttons"),
    ).toBeInTheDocument();
    const bar = screen.getByRole("progressbar", { name: "Step 2 of 3" });
    expect(bar).toHaveAttribute("aria-valuenow", "2");
    expect(bar.children).toHaveLength(3);
  });

  it("keeps the step inside 1..total", () => {
    render(<Glasses step={9} total={3} instruction="x" />);
    expect(screen.getByText("Your step · 3 of 3")).toBeInTheDocument();
  });

  it("the page wraps the same card", () => {
    render(<GlassesPage step={1} total={1} instruction="Only step" />);
    expect(screen.getByRole("main")).toContainElement(screen.getByText("Only step"));
  });
});
