// SPDX-License-Identifier: Apache-2.0
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { Answer } from "../feed/actions";
import { SurfaceBook } from "../feed/surfaces";
import { liveIo } from "./api";
import { type Call, mockIo } from "./fixtureIo";
import type { BriefItem } from "./room";
import { SCENES } from "./scenes";
import { TableView, type TableViewProps } from "./TableView";

const scene = (id: string) => {
  const s = SCENES.find((x) => x.id === id);
  if (!s) throw new Error(id);
  return s;
};

function mount(id: string, over: Partial<TableViewProps> = {}) {
  const s = scene(id);
  const calls: Call[] = [];
  const answers: Answer[] = [];
  const props: TableViewProps = {
    room: s.room,
    state: s.state,
    requests: s.requests,
    focus: null,
    setFocus: () => {},
    answer: async (a) => {
      answers.push(a);
      return { seq: answers.length + 40, signature: "abcdefghijklmnop" };
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

describe("the Table", () => {
  it("draws the goal, the seats, and says which seat is an agent", () => {
    mount("work");
    expect(screen.getByRole("heading", { level: 1 }).textContent).toContain("Get one shared piece");
    expect(
      screen.getByRole("button", { name: /See Budget helper's screen \(an agent\)/ }),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Your seat" })).toBeInTheDocument();
  });

  it("takes its day and night only from the room's lights", () => {
    const { view } = mount("work");
    expect(view.container.querySelector(".tb")?.getAttribute("data-lights")).toBe("night");
    view.unmount();
    const day = mount("plans");
    expect(day.view.container.querySelector(".tb")?.getAttribute("data-lights")).toBe("day");
  });

  it("uses the phone layout class and the two-part switch on a phone", () => {
    const { view } = mount("work", { phone: true });
    expect(view.container.querySelector(".tb")?.classList.contains("tb--phone")).toBe(true);
    expect(screen.getByRole("button", { name: "The table" })).toBeInTheDocument();
    view.unmount();
    const wide = mount("work");
    expect(wide.view.container.querySelector(".tb")?.classList.contains("tb--wide")).toBe(true);
    expect(screen.queryByRole("button", { name: "The table" })).toBeNull();
  });

  it("says when the connection dropped and keeps showing the last state", () => {
    mount("work", { status: "reconnecting" });
    expect(screen.getByText(/connection to the host dropped/)).toBeInTheDocument();
    expect(screen.getByText("Your agent, live")).toBeInTheDocument();
  });

  it("shows a running activity as running, with its own label as the caption", () => {
    mount("work");
    const caption = screen.getAllByRole("status").find((e) => e.className === "tb-caption");
    expect(caption?.textContent).toContain("Your agent offers your days.");
    expect(caption?.textContent?.toLowerCase()).toContain("running");
  });

  it("shows the real counts for the common times and a change", () => {
    const a = mount("work");
    // The Steward's stop arrives after the screen opened, so it is drawn as news.
    const s = scene("compare");
    a.view.rerender(<TableView {...a.props} room={s.room} state={s.state} requests={s.requests} />);
    expect(screen.getByText("Day 1 fits all 5. Your other 2 stayed private.")).toBeInTheDocument();
    expect(screen.getByText("no-contact-before-consent")).toBeInTheDocument();
    a.view.unmount();
    mount("change");
    expect(
      screen.getByText("2 of 5 re-planned · 1 person asked again · 3 untouched"),
    ).toBeInTheDocument();
  });

  it("offers begin to the one who may, with helpers or without", async () => {
    const { calls } = mount("seated");
    await userEvent.click(screen.getByRole("button", { name: /Begin, and let helpers take/ }));
    await userEvent.click(screen.getByRole("button", { name: "Begin with the people here" }));
    expect(calls.filter((c) => c.name === "begin").map((c) => c.args[0])).toEqual([true, false]);
  });
});

describe("brief", () => {
  it("posts the value the person chose, then can skip", async () => {
    const { calls } = mount("brief");
    await userEvent.click(screen.getByRole("button", { name: "Next" }));
    await waitFor(() => expect(calls.find((c) => c.name === "brief")).toBeTruthy());
    expect(calls.find((c) => c.name === "brief")?.args).toEqual(["q1", { value: ["d1"] }]);
  });
  it("posts skip", async () => {
    const { calls } = mount("brief");
    await userEvent.click(screen.getByRole("button", { name: "Skip" }));
    await waitFor(() => expect(calls.find((c) => c.name === "brief")).toBeTruthy());
    expect(calls.find((c) => c.name === "brief")?.args).toEqual(["q1", { skip: true }]);
    expect(screen.getByText(/Stays in your vault/)).toBeInTheDocument();
  });
});

describe("consent stays trusted", () => {
  it("one hold-free gesture answers every commitment and task once, and says how many", async () => {
    const { answers } = mount("commit");
    expect(screen.getByText(/2 things wait for your yes/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Review and approve" }));
    await userEvent.click(screen.getByRole("button", { name: "Confirm approval" }));
    await waitFor(() => expect(answers).toHaveLength(2));
    expect(answers).toEqual([
      { interrupt_id: "commitment:c1:1:p5", consent: true },
      { interrupt_id: "task:t1:1:p5", consent: true },
    ]);
  });

  it("never writes that the key is on the device", () => {
    mount("commit");
    expect(document.body.textContent).not.toMatch(/with your (owner )?key/i);
    expect(document.body.textContent).toMatch(/signs it for you|signed for you by the host/);
  });

  it("a consent button inside a composed tree answers nothing", async () => {
    const s = scene("brief");
    const tree = [
      { version: "v0.9", createSurface: { surfaceId: "q1", catalogId: "coalitionkit/v0_9" } },
      {
        version: "v0.9",
        updateComponents: {
          surfaceId: "q1",
          components: [
            {
              id: "root",
              component: "ConsentCard",
              subject: { kind: "plan", id: "p1", revision: { value: 1, event_ref: "e1" } },
              summary: "Tree consent",
              consequence: "Plan A is decided",
              decision_deadline: "2099-01-01T00:00:00Z",
            },
          ],
        },
      },
    ];
    const room = {
      ...s.room,
      mine: { ...s.room.mine, brief: [{ ...(s.room.mine.brief[0] as BriefItem), messages: tree }] },
    };
    const { answers } = mount("brief", { room: room as never });
    const accept = await screen.findByRole("button", { name: "Accept" });
    await userEvent.click(accept);
    await new Promise((r) => setTimeout(r, 50));
    expect(answers).toEqual([]);
  });
});

describe("say", () => {
  it("posts the sentence and shows where it went", async () => {
    const { calls } = mount("work");
    await userEvent.type(screen.getByLabelText("Tell your agent or the room"), "I like mornings");
    await userEvent.click(screen.getByRole("button", { name: "Say" }));
    expect(await screen.findByText(/Kept private/)).toBeInTheDocument();
    expect(calls.find((c) => c.name === "say")?.args).toEqual(["I like mornings"]);
  });
  it("shows a change and a stop in the host's words", async () => {
    mount("work");
    const box = screen.getByLabelText("Tell your agent or the room");
    await userEvent.type(box, "Member 3 cannot come{Enter}");
    expect(await screen.findByText(/Sent as a change/)).toBeInTheDocument();
    await userEvent.type(box, "send the phone number{Enter}");
    expect(await screen.findByText(/Stopped by the Steward\./)).toBeInTheDocument();
  });
  it("is closed once the room has ended", () => {
    mount("ended");
    expect(screen.getByLabelText("Tell your agent or the room")).toBeDisabled();
  });
});

describe("results", () => {
  it("opens a result, flips to the work with seq numbers, and exports per kind", async () => {
    mount("live");
    await userEvent.click(screen.getByRole("button", { name: /The budget/ }));
    const dialog = screen.getByRole("dialog", { name: "The budget" });
    expect(within(dialog).getByText(/from seq 12, 24/)).toBeInTheDocument();
    expect(within(dialog).getByRole("button", { name: "Export .csv" })).toBeInTheDocument();
    expect(within(dialog).queryByRole("button", { name: "Export .ics" })).toBeNull();
    await userEvent.click(within(dialog).getByRole("button", { name: "Show the work" }));
    expect(within(dialog).getByText(/seq 12 · offer/)).toBeInTheDocument();
    expect(within(dialog).getByText(/Check passed/)).toBeInTheDocument();
    await userEvent.click(within(dialog).getByRole("button", { name: "Show the result" }));
    expect(within(dialog).queryByText(/Check passed/)).toBeNull();
    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).toBeNull();
  });
  it("shows a skeleton while one is being made and marks a replaced one", () => {
    mount("make");
    expect(screen.getByText("being made")).toBeInTheDocument();
    const s = scene("live");
    const results = s.room.results.map((r, i) => (i === 0 ? { ...r, replaced_by: "r9" } : r));
    const again = mount("live", { room: { ...s.room, results } });
    expect(again.view.container.textContent).toContain("replaced");
  });
  it("lets me mark my part done only when the host allows it", async () => {
    const { calls } = mount("live");
    const buttons = screen.getAllByRole("button", { name: "Mark done" });
    await userEvent.click(buttons[0] as HTMLElement);
    await waitFor(() => expect(calls.find((c) => c.name === "done")?.args).toEqual(["t1"]));
  });
});

describe("see as", () => {
  it("fetches their view, hatches what is private, and goes back", async () => {
    const { calls } = mount("work");
    await userEvent.click(screen.getByRole("button", { name: "See Member 2's screen" }));
    await waitFor(() => expect(calls.find((c) => c.name === "viewAs")?.args).toEqual(["p2"]));
    expect(await screen.findByText(/Their free times · private to them/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Back to my side" }));
    expect(screen.getByText("Your agent, live")).toBeInTheDocument();
  });
});

describe("routes", () => {
  it("posts to the room routes with the viewer token", async () => {
    const fetchFn = vi.fn(
      async (_u: string, _i: RequestInit) => new Response("{}", { status: 200 }),
    );
    const io = liveIo(fetchFn, () => ({ baseUrl: "", token: "tok" }));
    await io.begin(true);
    await io.brief("q1", { skip: true });
    await io.say("hi");
    await io.done("t1");
    await io.viewAs("p 2");
    expect(fetchFn.mock.calls.map((c) => c[0])).toEqual([
      "/v1/room/begin",
      "/v1/room/brief",
      "/v1/room/say",
      "/v1/room/done",
      "/v1/view-as?participant=p%202",
    ]);
    const init = fetchFn.mock.calls[1]?.[1] as RequestInit;
    expect((init.headers as Record<string, string>).Authorization).toBe("Bearer tok");
    expect(JSON.parse(String(init.body))).toEqual({ question_id: "q1", skip: true });
  });
  it("answers an unreachable host with a plain failure", async () => {
    const io = liveIo(
      async () => Promise.reject(new Error("down")),
      () => ({ baseUrl: "", token: "t" }),
    );
    expect(await io.say("x")).toMatchObject({ ok: false, status: 0 });
  });
});

describe("scripted surfaces", () => {
  it("every brief question and result draws through the catalog, not the fallback", () => {
    for (const s of SCENES) {
      const lists = [
        ...s.room.mine.brief.map((b) => b.messages),
        ...s.room.results.map((r) => r.messages),
      ];
      for (const messages of lists) {
        const book = new SurfaceBook(() => {});
        book.apply("x", messages);
        expect(book.list()[0]?.fallback, JSON.stringify(messages).slice(0, 80)).toBe(false);
      }
    }
  });
});
