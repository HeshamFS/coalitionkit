// SPDX-License-Identifier: Apache-2.0
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { OpenRequest } from "../feed/agent";
import type { HostConfig } from "../feed/config";
import type { Fetch } from "../feed/connection";
import { FeedProvider } from "../feed/useFeed";
import { LENS_COMPONENTS, LensView } from "./LensView";
import { buildSteps, type LensState, press, START } from "./machine";

const state = {
  coalition_id: "c1",
  events: {
    e1: { type: "coalition.charter", seq: 1, payload: { goal: "Goal 1" } },
    e2: { type: "coalition.join", seq: 2, payload: {} },
    e3: { type: "coalition.need", seq: 3, payload: {} },
  },
};
const request = (over: Partial<OpenRequest> = {}): OpenRequest => ({
  id: "plan:p1:2:u1",
  kind: "plan",
  subjectId: "p1",
  revision: 2,
  message: "Take Plan A?",
  ...over,
});

describe("lens steps and gestures", () => {
  it("shows where the coalition stands, then one step per open request", () => {
    const steps = buildSteps(state, [
      request(),
      request({ id: "x:t1:1:u1", kind: "tension_option" }),
    ]);
    expect(steps.map((s) => s.kind)).toEqual(["info", "info", "ask", "phone"]);
    expect(steps[0]).toMatchObject({ title: "Goal 1", body: "1 member" });
    expect(steps[1]).toMatchObject({ title: "3 log entries" });
    expect(buildSteps(state, [request()], new Set(["plan:p1:2:u1"]))).toHaveLength(2);
  });

  it("moves with tap and swipe and never past either end", () => {
    const steps = buildSteps(state, []);
    let s: LensState = START;
    s = press(s, steps, "back").state;
    expect(s.index).toBe(0);
    s = press(s, steps, "tap").state;
    s = press(s, steps, "next").state;
    expect(s.index).toBe(1);
  });

  it("sends nothing on the first tap: an answer needs a confirm step", () => {
    const steps = buildSteps(state, [request()]);
    const first = press({ ...START, index: 2 }, steps, "tap");
    expect(first.send).toBeUndefined();
    expect(first.state.confirming).toEqual({ consent: true });
    const swipe = press(first.state, steps, "next");
    expect(swipe.send).toBeUndefined();
    expect(swipe.state.confirming).toBeNull();
    const second = press(first.state, steps, "tap");
    expect(second.send).toMatchObject({ consent: true, request: { id: "plan:p1:2:u1" } });
    expect(second.state.ack).toBe("Answer sent");
  });

  it("a swipe on a request means no, and still needs the confirm step", () => {
    const steps = buildSteps(state, [request()]);
    const first = press({ ...START, index: 2 }, steps, "next");
    expect(first.send).toBeUndefined();
    expect(first.state.confirming).toEqual({ consent: false });
    expect(press(first.state, steps, "tap").send?.consent).toBe(false);
  });

  it("a request that needs an option is left to the phone", () => {
    const steps = buildSteps(state, [request({ id: "t:t1:1:u1", kind: "tension_option" })]);
    const r = press({ ...START, index: 2 }, steps, "tap");
    expect(r.send).toBeUndefined();
    expect(r.state.confirming).toBeNull();
  });
});

const sse = (events: object[]) =>
  new Response(
    new ReadableStream({
      start(controller) {
        const enc = new TextEncoder();
        for (const e of events) controller.enqueue(enc.encode(`data: ${JSON.stringify(e)}\n\n`));
      },
    }),
    { status: 200, headers: { "Content-Type": "text/event-stream" } },
  );

function host(answers: unknown[]): Fetch {
  return vi.fn(async (url: string, init: RequestInit) => {
    const path = new URL(url, "http://x").pathname;
    if (path === "/v1/feed") {
      return sse([
        { type: "RUN_STARTED", threadId: "t", runId: "r1" },
        { type: "STATE_SNAPSHOT", snapshot: state },
      ]);
    }
    if (path === "/v1/agent") {
      return sse([
        { type: "RUN_STARTED", threadId: "t", runId: "ra" },
        {
          type: "RUN_FINISHED",
          threadId: "t",
          runId: "ra",
          outcome: {
            type: "interrupt",
            interrupts: [
              {
                id: "plan:p1:2:u1",
                message: "Take Plan A?",
                metadata: { subject: { kind: "plan", id: "p1", revision: 2 } },
              },
            ],
          },
        },
      ]);
    }
    answers.push(JSON.parse(String(init.body)));
    return new Response(JSON.stringify({ seq: 9 }), { status: 200 });
  }) as unknown as Fetch;
}

const config: HostConfig = { baseUrl: "", token: "tok-1" };

describe("the lens view", () => {
  it("draws one card for one step and answers only after the confirm step", async () => {
    const answers: unknown[] = [];
    const user = userEvent.setup();
    render(
      <FeedProvider config={config} fetchFn={host(answers)}>
        <LensView />
      </FeedProvider>,
    );
    const frame = await screen.findByRole("application", { name: /Lens display/ });
    expect(await screen.findByRole("heading", { name: "Goal 1" })).toBeInTheDocument();
    expect(frame.querySelectorAll("article")).toHaveLength(1);

    await user.click(screen.getByRole("button", { name: "Swipe next" }));
    expect(screen.getByRole("heading", { name: "3 log entries" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Swipe next" }));
    await screen.findByRole("heading", { name: "Take Plan A?" });

    await user.click(screen.getByRole("button", { name: "Tap" }));
    expect(screen.getByRole("heading", { name: "Send yes?" })).toBeInTheDocument();
    expect(answers).toHaveLength(0);

    await user.click(screen.getByRole("button", { name: "Tap" }));
    await waitFor(() => expect(answers).toHaveLength(1));
    expect(answers[0]).toEqual({ interrupt_id: "plan:p1:2:u1", consent: true });
  });

  it("answers from the keyboard with the same two steps", async () => {
    const answers: unknown[] = [];
    const user = userEvent.setup();
    render(
      <FeedProvider config={config} fetchFn={host(answers)}>
        <LensView />
      </FeedProvider>,
    );
    await screen.findByRole("heading", { name: "Goal 1" });
    await user.keyboard("{ArrowRight}{ArrowRight}");
    await screen.findByRole("heading", { name: "Take Plan A?" });
    await user.keyboard("{ArrowRight}");
    expect(screen.getByRole("heading", { name: "Send no?" })).toBeInTheDocument();
    expect(answers).toHaveLength(0);
    await user.keyboard("{Enter}");
    await waitFor(() =>
      expect(answers).toEqual([{ interrupt_id: "plan:p1:2:u1", consent: false }]),
    );
  });
});

describe("the lens uses only components that list the lens door", () => {
  it("every component it draws has the lens door in the catalog file", () => {
    const file = join(process.cwd(), "..", "..", "spec", "catalog", "coalitionkit-v0_9.json");
    const catalog = JSON.parse(readFileSync(file, "utf8")) as {
      components: Record<string, { doors: string[] }>;
    };
    for (const name of LENS_COMPONENTS) expect(catalog.components[name]?.doors).toContain("lens");
  });

  it("draws nothing else", async () => {
    render(
      <FeedProvider config={config} fetchFn={host([])}>
        <LensView />
      </FeedProvider>,
    );
    await screen.findByRole("heading", { name: "Goal 1" });
    const drawn = new Set(
      [...document.querySelectorAll("[data-component]")].map((n) =>
        n.getAttribute("data-component"),
      ),
    );
    expect([...drawn]).toEqual([...LENS_COMPONENTS]);
  });
});
