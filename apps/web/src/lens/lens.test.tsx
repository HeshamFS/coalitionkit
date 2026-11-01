// SPDX-License-Identifier: Apache-2.0
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { render, screen } from "@testing-library/react";
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
    expect(steps.map((s) => s.kind)).toEqual(["info", "info", "phone", "phone"]);
    expect(steps[0]).toMatchObject({ title: "Goal 1", body: "1 member" });
    expect(steps[1]).toMatchObject({ title: "3 log entries" });
    expect(steps[2]).toMatchObject({ title: "Take Plan A?", body: "Decide on your phone" });
    expect(steps[3]?.body).toBe("Decide on your phone");
  });

  it("moves with tap and swipe and never past either end", () => {
    const steps = buildSteps(state, [request()]);
    let s: LensState = START;
    s = press(s, steps, "back");
    expect(s.index).toBe(0);
    for (let i = 0; i < 6; i++) s = press(s, steps, i % 2 ? "tap" : "next");
    expect(s.index).toBe(2);
  });

  it("a gesture has no other effect than moving", () => {
    const steps = buildSteps(state, [request()]);
    expect(Object.keys(press({ index: 2 }, steps, "tap"))).toEqual(["index"]);
  });
});

const interrupt = (id: string, revision: number, message: string) => ({
  type: "RUN_FINISHED",
  threadId: "t",
  runId: `ra${revision}`,
  outcome: {
    type: "interrupt",
    interrupts: [{ id, message, metadata: { subject: { kind: "plan", id: "p1", revision } } }],
  },
});

/** An SSE response that stays open: `push` plays the host sending a later event. */
function stream(first: object[]) {
  const enc = new TextEncoder();
  let controller: ReadableStreamDefaultController<Uint8Array> | undefined;
  const body = new ReadableStream<Uint8Array>({
    start(c) {
      controller = c;
      for (const e of first)
        c.enqueue(
          enc.encode(`data: ${JSON.stringify(e)}

`),
        );
    },
  });
  return {
    response: new Response(body, { status: 200, headers: { "Content-Type": "text/event-stream" } }),
    push: (e: object) =>
      controller?.enqueue(
        enc.encode(`data: ${JSON.stringify(e)}

`),
      ),
  };
}

// The agent channel rides on the feed stream as CUSTOM "coalitionkit.agent" events.
const viaFeed = (e: object) => ({ type: "CUSTOM", name: "coalitionkit.agent", value: e });

function host() {
  const posts: { url: string; body: unknown }[] = [];
  const feed = stream([
    { type: "RUN_STARTED", threadId: "t", runId: "r1" },
    { type: "STATE_SNAPSHOT", snapshot: state },
    viaFeed({ type: "RUN_STARTED", threadId: "t", runId: "ra0" }),
    viaFeed(interrupt("plan:p1:2:u1", 2, "Take Plan A?")),
  ]);
  const agent = { push: (e: object) => feed.push(viaFeed(e)) };
  const fetchFn = vi.fn(async (url: string, init: RequestInit) => {
    const path = new URL(url, "http://x").pathname;
    if (path === "/v1/feed") return feed.response;
    posts.push({ url: path, body: init.body });
    return new Response(JSON.stringify({ seq: 9 }), { status: 200 });
  }) as unknown as Fetch;
  return { fetchFn, posts, agent };
}

const config: HostConfig = { baseUrl: "", token: "tok-1" };

describe("the lens view", () => {
  it("shows a request as a card that sends you to the phone, and sends nothing", async () => {
    const h = host();
    const user = userEvent.setup();
    render(
      <FeedProvider config={config} fetchFn={h.fetchFn}>
        <LensView />
      </FeedProvider>,
    );
    const frame = await screen.findByRole("application", { name: /Lens display/ });
    expect(await screen.findByRole("heading", { name: "Goal 1" })).toBeInTheDocument();
    expect(frame.querySelectorAll("article")).toHaveLength(1);
    await user.click(screen.getByRole("button", { name: "Swipe next" }));
    await user.click(screen.getByRole("button", { name: "Swipe next" }));
    expect(await screen.findByRole("heading", { name: "Take Plan A?" })).toBeInTheDocument();
    expect(screen.getByText("Decide on your phone")).toBeInTheDocument();
    // Every gesture, by button and by key, at the request step.
    await user.click(screen.getByRole("button", { name: "Tap" }));
    await user.click(screen.getByRole("button", { name: "Tap" }));
    await user.keyboard("{Enter}{ }{ArrowRight}{ArrowLeft}{ArrowRight}{Enter}");
    expect(h.posts).toEqual([]);
  });

  it("sends nothing after live request updates either (a new revision, a new request)", async () => {
    const h = host();
    const user = userEvent.setup();
    render(
      <FeedProvider config={config} fetchFn={h.fetchFn}>
        <LensView />
      </FeedProvider>,
    );
    await screen.findByRole("heading", { name: "Goal 1" });
    await user.keyboard("{ArrowRight}{ArrowRight}");
    await screen.findByRole("heading", { name: "Take Plan A?" });
    h.agent.push(interrupt("plan:p1:3:u1", 3, "Take Plan A, revision 3?"));
    await screen.findByRole("heading", { name: "Take Plan A, revision 3?" });
    await user.keyboard("{Enter}{ArrowRight}{Enter}");
    await user.click(screen.getByRole("button", { name: "Tap" }));
    h.agent.push(interrupt("plan:p2:1:u1", 1, "Take Plan B?"));
    await screen.findByRole("heading", { name: "Take Plan B?" });
    await user.keyboard("{Enter}{Enter}{ArrowRight}");
    await user.click(screen.getByRole("button", { name: "Tap" }));
    expect(h.posts).toEqual([]);
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
      <FeedProvider config={config} fetchFn={host().fetchFn}>
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
