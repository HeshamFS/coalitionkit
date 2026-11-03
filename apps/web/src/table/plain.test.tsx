// SPDX-License-Identifier: Apache-2.0
// Round 3: plain words, one-screen behaviour, honest errors, one ending.
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { clearEnded } from "../room/ended";
import { EndedTable } from "./EndedTable";
import { type Call, mockIo } from "./fixtureIo";
import { rememberRoom } from "./keep";
import { needStatus } from "./needWords";
import type { Room } from "./room";
import { SCENES } from "./scenes";
import { TableView, type TableViewProps } from "./TableView";

const scene = (id: string) => {
  const s = SCENES.find((x) => x.id === id);
  if (!s) throw new Error(id);
  return s;
};

function mount(id: string, over: Partial<TableViewProps> & { room?: Room } = {}) {
  const s = scene(id);
  const calls: Call[] = [];
  const answers: unknown[] = [];
  const props: TableViewProps = {
    room: s.room,
    state: s.state,
    requests: s.requests,
    focus: null,
    setFocus: () => {},
    answer: async (a) => {
      answers.push(a);
      return { seq: 41, signature: "abcdefghijklmnop" };
    },
    outcome: async (a) => {
      answers.push(a);
      return { ok: true, ack: { seq: 40 + answers.length, signature: "abcdefghijklmnop" } };
    },
    io: mockIo(calls),
    phone: false,
    owner: true,
    status: "live",
    ...over,
  };
  const view = render(<TableView {...props} />);
  return { calls, answers, view, props };
}

describe("plain words", () => {
  it("shows the plan's name, the engine's plain line and the for-you line, and no raw numbers", () => {
    mount("plans");
    expect(screen.getByText("Lowest cost, one day missed.")).toBeInTheDocument();
    expect(screen.getAllByText("FOR YOU ONLY")).toHaveLength(3);
    expect(document.body.textContent).not.toMatch(
      /minutes of work in all|largest share|third goal|total cost|cost 36|even share/i,
    );
  });

  it("lays plans side by side and keeps every need on the table while people decide", () => {
    mount("plans");
    expect(screen.getAllByRole("button", { name: /PLAN [ABC]/ })).toHaveLength(3);
    for (const need of ["The place", "The days", "The budget", "The list", "The invitation"]) {
      expect(screen.getAllByText(need).length).toBeGreaterThan(0);
    }
    expect(document.querySelector(".tb-planstrip .tb-plans")).not.toBeNull();
    expect(document.querySelector(".tb-stage .tb-plans")).toBeNull();
  });

  it("says where a need stands in plain words", () => {
    expect(needStatus("negotiating", 2, "list")).toBe("agents comparing · 2 offers");
    expect(needStatus("proposed", 0, "list")).toBe("in a plan");
    expect(needStatus("decided", 0, "list")).toBe("agreed");
    expect(needStatus("committed", 0, "list")).toBe("being done");
    expect(needStatus("done", 0, "list")).toBe("done");
    expect(needStatus("something_new", 0, "budget")).toBe("budget");
    const s = scene("work");
    const needs = s.room.needs.map((n, i) => ({
      ...n,
      status: ["negotiating", "proposed", "decided", "committed", "done"][i] ?? "",
    }));
    mount("work", { room: { ...s.room, needs } });
    expect(screen.getByText(/agents comparing/)).toBeInTheDocument();
    expect(screen.queryByText(/negotiating|proposed|committed/)).toBeNull();
  });

  it("keeps developer talk off the main screen", () => {
    mount("brief");
    expect(document.body.textContent).not.toMatch(
      /composed tree|against the catalog|from the host's request/,
    );
  });

  it("offers 'See the other plans' on a plan, never on the charter", async () => {
    const a = mount("arrive");
    expect(screen.queryByRole("button", { name: "See the other plans" })).toBeNull();
    a.view.unmount();
    mount("plans");
    await userEvent.click(screen.getAllByRole("button", { name: /PLAN A/ })[0] as HTMLElement);
    expect(await screen.findByRole("button", { name: "See the other plans" })).toBeInTheDocument();
  });

  it("shows a resting line from the phase when nothing is running, and says 'Working on'", () => {
    const s = scene("brief");
    const done = {
      ...s.room,
      activity: [
        {
          id: "a1",
          at: "2026-11-03T10:00:01Z",
          seat: "p5",
          verb: "asking" as const,
          need: null,
          label: "Your agent is choosing what to ask you",
          state: "done" as const,
          ms: 900,
          source: "model" as const,
          event: null,
        },
      ],
    };
    const a = mount("brief", { room: done });
    const caption = () => screen.getAllByRole("status").find((e) => e.className === "tb-caption");
    expect(caption()?.textContent).toContain("Your agent has questions for you.");
    expect(caption()?.textContent).not.toContain("choosing what to ask");
    a.view.unmount();
    const w = scene("make");
    const run = {
      ...w.room,
      activity: [
        { ...(w.room.activity[3] as Room["activity"][number]), label: "Making Find a place" },
      ],
    } as Room;
    mount("make", { room: run });
    expect(caption()?.textContent).toContain("Working on: Find a place");
    expect(caption()?.textContent).not.toContain("Making Find");
  });

  it("does not keep showing a change sentence once what it moved is done", () => {
    const s = scene("change");
    const needs = s.room.needs.map((n) => ({ ...n, result: n.result ?? "r9", status: "done" }));
    mount("change", { room: { ...s.room, needs, activity: [] } });
    const caption = screen.getAllByRole("status").find((e) => e.className === "tb-caption");
    expect(caption?.textContent).not.toContain("cannot come");
  });
});

describe("the box to say things", () => {
  const placeholder = () =>
    screen.getByLabelText("Tell your agent or the room").getAttribute("placeholder");
  it("bases the reason it is closed on this viewer's own seat", () => {
    const a = mount("arrive");
    expect(placeholder()).toBe("Take your seat to speak");
    a.view.unmount();
    const b = mount("seated");
    expect(placeholder()).toBe("Waiting for the room to begin");
    b.view.unmount();
    mount("work");
    expect(placeholder()).toBe("Tell your agent, or the room");
  });

  it("shows the reply on your side, not in the footer", async () => {
    mount("work");
    await userEvent.type(
      screen.getByLabelText("Tell your agent or the room"),
      "I like mornings{Enter}",
    );
    const note = await screen.findByLabelText("What you said");
    expect(note.closest(".tb-sidecol")).not.toBeNull();
    expect(note.closest(".tb-rail")).toBeNull();
    expect(within(note).getByText(/Kept private/)).toBeInTheDocument();
  });
});

describe("signing", () => {
  it("collapses the loud Signed banner once the room moves on, and keeps the receipt", async () => {
    const a = mount("commit");
    await userEvent.click(screen.getByRole("button", { name: "Review and approve" }));
    await userEvent.click(screen.getByRole("button", { name: "Confirm approval" }));
    expect(await screen.findByLabelText("Signed")).toBeInTheDocument();
    const live = scene("live");
    a.view.rerender(<TableView {...a.props} room={live.room} requests={[]} />);
    expect(screen.queryByLabelText("Signed")).toBeNull();
    expect(screen.getByText(/Your signatures \(/)).toBeInTheDocument();
  });

  it("counts what waits honestly: a task under an open commitment is not a second thing", async () => {
    const s = scene("commit");
    const state = {
      ...s.state,
      events: {
        ...(s.state.events as object),
        e9: { type: "coalition.commit", seq: 30, payload: { commitment_id: "c1", task_id: "t1" } },
      },
    };
    const { answers } = mount("commit", { state });
    expect(screen.getByText(/1 thing waits for your yes/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Review and approve" }));
    await userEvent.click(screen.getByRole("button", { name: "Confirm approval" }));
    await waitFor(() => expect(answers).toHaveLength(1));
  });

  it("treats a request the first yes already closed as handled, with no alert", async () => {
    let n = 0;
    const s = scene("commit");
    const second = {
      id: "commitment:c2:1:p5",
      kind: "commitment",
      subjectId: "c2",
      revision: 1,
      message: "",
    };
    const room = {
      ...s.room,
      mine: {
        ...s.room.mine,
        asks: [
          ...(s.room.mine.asks ?? []),
          { kind: "commitment", id: "c2", revision: 1, summary: "Take the second part." },
        ],
      },
    };
    mount("commit", {
      room,
      requests: [...s.requests, second],
      outcome: async () =>
        n++ === 0
          ? { ok: true, ack: { seq: 41, signature: "abcdefghijklmnop" } }
          : { ok: false, error: "not_open", detail: "" },
    });
    await userEvent.click(screen.getByRole("button", { name: "Review and approve" }));
    await userEvent.click(screen.getByRole("button", { name: "Confirm approval" }));
    expect(await screen.findByText(/already closed by an earlier yes/)).toBeInTheDocument();
    expect(screen.queryByRole("alert")).toBeNull();
  });
});

describe("alerts", () => {
  it("puts a real refusal in the fixed notice layer, where nothing can cover it", async () => {
    mount("work", { refusal: "not_your_request: wrong person" });
    const alert = screen.getByRole("alert");
    expect(alert.className).toBe("tb-notice");
    expect(alert.textContent).toContain("not_your_request");
    await userEvent.click(within(alert).getByRole("button", { name: "Dismiss" }));
    expect(screen.queryByRole("alert")).toBeNull();
  });
});

describe("the brief's clock and header", () => {
  const withCloses = (ms: number) => {
    const s = scene("brief");
    return {
      ...s.room,
      mine: { ...s.room.mine, brief_closes: new Date(Date.now() + ms).toISOString() },
    };
  };
  it("shows the time left only near the end", () => {
    const a = mount("brief", { room: withCloses(10 * 60_000) });
    expect(screen.queryByRole("timer")).toBeNull();
    a.view.unmount();
    mount("brief", { room: withCloses(60_000) });
    expect(screen.getByRole("timer").textContent).toMatch(/Questions close in 1:00|0:5\d/);
  });
  it("puts the deadline in the header", () => {
    mount("work");
    expect(document.querySelector(".tb-eyebrow")?.textContent).toMatch(/closes/);
  });
});

describe("results that were replaced", () => {
  it("stay readable but quiet", async () => {
    const s = scene("live");
    const results = s.room.results.map((r, i) => (i === 0 ? { ...r, replaced_by: "r9" } : r));
    mount("live", { room: { ...s.room, results } });
    const tile = screen.getByRole("button", { name: /replaced/ });
    expect(tile.getAttribute("data-replaced")).toBe("true");
    await userEvent.click(tile);
    const dialog = screen.getByRole("dialog", { name: "The place" });
    expect(within(dialog).getByText(/Replaced by a newer result/)).toBeInTheDocument();
    expect(within(dialog).getByText("Venue 1")).toBeInTheDocument();
  });
});

describe("one ending", () => {
  afterEach(() => {
    clearEnded();
    vi.unstubAllGlobals();
  });
  it("folds the Table for everyone, keeps the results, and says plainly where they live", () => {
    const s = scene("live");
    rememberRoom(s.room, s.state);
    render(
      <EndedTable event={{ reason: "completed", skills_written: ["l1"] }} onLeave={() => {}} />,
    );
    expect(screen.getByText("The room has ended")).toBeInTheDocument();
    expect(screen.getByText(/live only in this tab/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "The budget" })).toBeInTheDocument();
    expect(document.querySelector(".tb-stage")?.getAttribute("data-ended")).toBe("true");
    expect(screen.queryByText("What was erased")).toBeNull();
  });
  it("shows the measured numbers it has and leaves out any it could not measure", () => {
    const s = scene("ended");
    rememberRoom(
      { ...s.room, measured: { calendars_shared: 5, minutes: 47, cost: null, vendors: 1 } },
      s.state,
    );
    render(<EndedTable event={{ reason: "completed", skills_written: [] }} onLeave={() => {}} />);
    expect(screen.getByText("5 calendars shared")).toBeInTheDocument();
    expect(screen.getByText("47 minutes from start to end")).toBeInTheDocument();
    expect(screen.getByText("1 outside agent")).toBeInTheDocument();
    expect(document.body.textContent).not.toMatch(/spent on the model|\[COST\]|\[MEASURED\]/);
  });
  it("shows the cost when the host measured one", () => {
    const s = scene("ended");
    rememberRoom(s.room, s.state);
    render(<EndedTable event={{ reason: "completed", skills_written: [] }} onLeave={() => {}} />);
    expect(screen.getByText("$0.12 spent on the model")).toBeInTheDocument();
  });
  it("shows what the host erased, only from the numbers it sent", async () => {
    const s = scene("live");
    rememberRoom(s.room, s.state);
    vi.stubGlobal(
      "fetch",
      vi.fn(
        async () =>
          new Response(JSON.stringify({ vaults_erased: 5, tokens_revoked: 1 }), { status: 200 }),
      ),
    );
    render(<EndedTable run={{ token: "t", reason: "completed" }} onLeave={() => {}} />);
    expect(await screen.findByText("5 private vaults erased")).toBeInTheDocument();
    expect(screen.getByText("1 viewer link stopped")).toBeInTheDocument();
    expect(screen.queryByText(/open task/)).toBeNull();
  });
  it("falls back to the plain closing page when this tab never drew the Table", () => {
    clearEnded();
    render(<EndedTable event={{ reason: "completed", skills_written: [] }} onLeave={() => {}} />);
    expect(screen.queryByText("The room has ended")).toBeNull();
    expect(document.querySelector(".ck-ended")).not.toBeNull();
  });
});
