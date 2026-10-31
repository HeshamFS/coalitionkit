// SPDX-License-Identifier: Apache-2.0
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { GermStepProvider } from "../room/germ";
import { deriveStrip } from "../room/measured";
import { Decisions, MeasuredStrip, Plans } from "../room/parts";
import { ConsentTray } from "../shell/dock";
import { TrustedRequest } from "../TrustedRequest";
import type { OpenRequest } from "./agent";
import { derivePlans, humanTime, requestLabel, visibleRequests } from "./derive";

const Now = ({ children }: { children: ReactNode }) => (
  <GermStepProvider value={0}>{children}</GermStepProvider>
);
const plan = (id: string, scores: Record<string, number>) => ({
  plan_id: id,
  assignments: [],
  objective_scores: scores,
});
const state = {
  viewer: "p1",
  events: {
    j: { seq: 1, type: "coalition.join", on_behalf_of: "p1", payload: { card: {} } },
    p: {
      seq: 2,
      type: "coalition.propose",
      payload: {
        plans: [
          plan("planA", { total_cost: 360, max_share_ratio: 2, third: 360 }),
          plan("planB", { total_cost: 420, max_share_ratio: 1.5, third: 360 }),
        ],
      },
    },
    t: {
      seq: 3,
      type: "coalition.tension",
      payload: {
        tension_id: "t1",
        revision: 1,
        options: [
          { option_id: "planA", summary: "Plan total_cost 360" },
          { option_id: "planB", summary: "Plan total_cost 420" },
        ],
        tradeoffs: [],
      },
    },
  },
};
const req = (kind: string, subjectId: string): OpenRequest => ({
  id: `${kind}:${subjectId}:1:p1`,
  kind,
  subjectId,
  revision: 1,
  message: `ask ${subjectId}`,
  expiresAt: "2026-11-01T10:00:00Z",
});
const open = [req("plan", "planA"), req("plan", "planB"), req("tension_option", "t1")];

describe("plan words", () => {
  it("names relative strengths and shows no raw keys", async () => {
    const [a, b] = derivePlans(state);
    expect(a?.strength).toBe("lowest total cost · higher largest share");
    expect(b?.strength).toBe("fairest split · higher cost");
    expect(a?.note).toBe("cost 360 · largest share 2× · third goal 360");
    render(
      <Now>
        <Plans state={state} ready requests={[]} />
      </Now>,
    );
    await screen.findByText("Plan options");
    expect(document.body.textContent).not.toMatch(/total_cost|max_share_ratio|third(?! goal)/);
  });
  it("turns an unknown key into words without inventing a meaning", () => {
    const s = {
      events: {
        p: {
          seq: 1,
          type: "coalition.propose",
          payload: { plans: [plan("x", { slow_start: 1 }), plan("y", { slow_start: 2 })] },
        },
      },
    };
    const [x] = derivePlans(s);
    expect(x?.strength).toBe("lowest slow start");
    expect(x?.note).toBe("slow start 1");
  });
});

describe("one choice is one ask", () => {
  it("folds plan requests into the tension in the tray and decisions", async () => {
    const shown = visibleRequests(state, open);
    expect(shown.map((r) => r.kind)).toEqual(["tension_option"]);
    expect(requestLabel(state, open[2] as OpenRequest)).toBe("Choose a plan · A or B");
    render(
      <Now>
        <ConsentTray
          requests={shown.map((r) => ({
            id: r.id,
            kind: "tension",
            title: requestLabel(state, r),
          }))}
        />
        <Decisions state={state} requests={open} onOpen={() => {}} ready />
      </Now>,
    );
    expect(screen.getByText("1 decision waits for you")).toBeInTheDocument();
    await screen.findByText("Needs you");
    expect(screen.getAllByText("Choose a plan · A or B")).toHaveLength(2);
    expect(screen.queryByText(/Review plan/)).toBeNull();
  });
  it("answers the tension with the chosen option and approves only that plan", async () => {
    const onAnswer = vi.fn();
    render(
      <TrustedRequest
        request={open[2] as OpenRequest}
        state={state}
        onAnswer={onAnswer}
        related={[open[0] as OpenRequest, open[1] as OpenRequest]}
      />,
    );
    await userEvent.click(screen.getByRole("radio", { name: /Plan B/ }));
    await userEvent.click(screen.getByRole("button", { name: /Choose/ }));
    // The host records assignments only for a decided plan; plan A is superseded by the host.
    expect(onAnswer.mock.calls.map((c) => c[0])).toEqual([
      { interrupt_id: "tension_option:t1:1:p1", consent: true, choice: "planB" },
      { interrupt_id: "plan:planB:1:p1", consent: true },
    ]);
  });
});

describe("deadline day", () => {
  afterEach(() => vi.useRealTimers());
  it("says today, tomorrow, weekday or date", () => {
    const now = new Date(2026, 10, 1, 12, 0);
    const at = (d: number, h: number) => new Date(2026, 10, d, h, 30).toISOString();
    expect(humanTime(at(1, 14), now)).toBe("today 14:30");
    expect(humanTime(at(2, 9), now)).toBe("tomorrow 09:30");
    expect(humanTime(at(4, 1), now)).toMatch(/^\w{3} 01:30$/);
    expect(humanTime(at(20, 1), now)).toMatch(/20/);
    expect(humanTime("not a date", now)).toBe("not a date");
  });
  it("crosses the day boundary with fake timers", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date(2026, 10, 1, 23, 50));
    const t = new Date(2026, 10, 2, 0, 10).toISOString();
    expect(humanTime(t)).toBe("tomorrow 00:10");
    vi.setSystemTime(new Date(2026, 10, 2, 0, 20));
    expect(humanTime(t)).toBe("today 00:10");
  });
});

describe("vendor", () => {
  it("reads the vendor from the card and hides an unknown one", async () => {
    const withCard = {
      events: {
        j: {
          seq: 1,
          type: "coalition.join",
          on_behalf_of: "p1",
          payload: { card: { name: "Agent", provider: { organization: "Org" } } },
        },
      },
    };
    expect(deriveStrip(withCard).vendors).toBe("1");
    expect(deriveStrip(state).vendors).toBe("");
    render(
      <Now>
        <MeasuredStrip state={state} ready />
      </Now>,
    );
    expect((await screen.findByLabelText("Measured")).textContent).toMatch(/^1 agents/);
    expect(document.body.textContent).not.toMatch(/vendors/);
  });
});
