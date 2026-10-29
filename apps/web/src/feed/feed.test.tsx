// SPDX-License-Identifier: Apache-2.0
import { A2uiSurface } from "@a2ui/react/v0_9";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { openStream } from "./connection";
import { fixedFields } from "./derive";
import { FeedStore } from "./store";

const surfaceMessages = (components: unknown[], data: unknown = {}) => [
  { version: "v0.9", createSurface: { surfaceId: "s1", catalogId: "coalitionkit/v0_9" } },
  { version: "v0.9", updateComponents: { surfaceId: "s1", components } },
  { version: "v0.9", updateDataModel: { surfaceId: "s1", path: "/", value: data } },
];
const activity = (messages: unknown[]) => ({
  type: "ACTIVITY_SNAPSHOT",
  messageId: "a2ui:s1",
  activityType: "a2ui-surface",
  content: { messages },
  replace: true,
});

describe("delta application", () => {
  it("snapshot plus deltas gives the expected state", () => {
    const store = new FeedStore();
    store.handle({ type: "RUN_STARTED", runId: "r1" });
    store.handle({ type: "STATE_SNAPSHOT", snapshot: { coalition_id: "c1", events: {} } });
    store.handle({
      type: "STATE_DELTA",
      delta: [
        { op: "add", path: "/events/e1", value: { type: "coalition.need", seq: 1, payload: {} } },
      ],
    });
    store.handle({
      type: "STATE_DELTA",
      delta: [{ op: "add", path: "/events/e1/payload/x", value: "y" }],
    });
    expect(store.getSnapshot().state).toEqual({
      coalition_id: "c1",
      events: { e1: { type: "coalition.need", seq: 1, payload: { x: "y" } } },
    });
  });

  it("applies the root replacement the host sends", () => {
    const store = new FeedStore();
    store.handle({ type: "STATE_SNAPSHOT", snapshot: { a: 1 } });
    store.handle({ type: "STATE_DELTA", delta: [{ op: "replace", path: "", value: { b: 2 } }] });
    expect(store.getSnapshot().state).toEqual({ b: 2 });
  });

  it("drops the stream when a delta does not fit", () => {
    const store = new FeedStore();
    store.handle({ type: "STATE_SNAPSHOT", snapshot: { a: 1 } });
    const keep = store.handle({
      type: "STATE_DELTA",
      delta: [{ op: "remove", path: "/nope/deeper" }],
    });
    expect(keep).toBe(false);
    expect(store.getSnapshot().state).toEqual({ a: 1 });
    expect(store.getSnapshot().problem).toBeTruthy();
  });

  it("refuses a delta before any snapshot", () => {
    const store = new FeedStore();
    expect(store.handle({ type: "STATE_DELTA", delta: [] })).toBe(false);
  });
});

describe("fallback to the fixed view", () => {
  const drawn = (store: FeedStore) => {
    const entry = store.getSnapshot().surfaces[0];
    if (!entry) throw new Error("no surface");
    return entry;
  };

  it("draws a valid tree and keeps it", () => {
    const store = new FeedStore();
    store.handle(
      activity(surfaceMessages([{ id: "root", component: "Heading", text: "Hello 1" }])),
    );
    const entry = drawn(store);
    expect(entry.fallback).toBe(false);
    render(<A2uiSurface surface={entry.model} />);
    expect(screen.getByRole("heading", { name: "Hello 1" })).toBeInTheDocument();
  });

  const bad: [string, unknown[]][] = [
    ["an unknown component", [{ id: "root", component: "Bogus" }]],
    ["a bad prop", [{ id: "root", component: "Tag", kind: "not-a-kind" }]],
    ["an unbound number", [{ id: "root", component: "Skeleton", lines: 3 }]],
    ["a missing root", [{ id: "other", component: "Heading", text: "x" }]],
  ];
  for (const [name, components] of bad) {
    it(`replaces ${name} with the fixed layout`, () => {
      const store = new FeedStore();
      store.handle({ type: "STATE_SNAPSHOT", snapshot: { events: {} } });
      store.book.setFallbackFields(fixedFields(store.getSnapshot().state));
      store.handle(activity(surfaceMessages(components)));
      const entry = drawn(store);
      expect(entry.fallback).toBe(true);
      render(<A2uiSurface surface={entry.model} />);
      expect(screen.getByRole("group", { name: "Standard view" })).toBeInTheDocument();
    });
  }

  it("recovers when a later update is valid", () => {
    const store = new FeedStore();
    store.handle(activity(surfaceMessages([{ id: "root", component: "Bogus" }])));
    expect(drawn(store).fallback).toBe(true);
    // The host sends createSurface only once per run, so the update carries just the components.
    store.handle(
      activity(surfaceMessages([{ id: "root", component: "Heading", text: "Ok 1" }]).slice(1)),
    );
    expect(drawn(store).fallback).toBe(false);
  });

  it("starts each run from nothing", () => {
    const store = new FeedStore();
    store.handle(activity(surfaceMessages([{ id: "root", component: "Heading", text: "A1" }])));
    store.handle({ type: "RUN_STARTED", runId: "r2" });
    expect(store.getSnapshot().surfaces).toHaveLength(0);
  });
});

describe("the SSE stream", () => {
  it("sends the bearer token, parses events and reconnects with a fresh run", async () => {
    const sse = (events: object[]) =>
      new Response(
        new ReadableStream({
          start(controller) {
            const enc = new TextEncoder();
            controller.enqueue(enc.encode(": keep-alive\n\n"));
            for (const e of events) {
              controller.enqueue(enc.encode(`data: ${JSON.stringify(e)}\n\n`));
            }
            controller.close();
          },
        }),
        { headers: { "Content-Type": "text/event-stream" } },
      );
    const run = [
      { type: "RUN_STARTED", threadId: "th", runId: "r1" },
      { type: "STATE_SNAPSHOT", snapshot: { ok: true } },
    ];
    const fetchFn = vi.fn(async (_url: string, _init: RequestInit) => sse(run));
    const seen: string[] = [];
    const stop = openStream({
      config: { baseUrl: "", token: "tok-1" },
      path: "/v1/feed",
      fetchFn,
      delay: () => 5,
      onEvent: (e) => {
        seen.push(e.type);
        return true;
      },
      onStatus: () => {},
    });
    await vi.waitFor(() => expect(fetchFn.mock.calls.length).toBeGreaterThanOrEqual(2));
    stop();
    const [url, init] = fetchFn.mock.calls[0] ?? ["", {}];
    expect(url).toBe("/v1/feed");
    expect(init.method).toBe("GET");
    expect((init.headers as Record<string, string>).Authorization).toBe("Bearer tok-1");
    expect(seen.slice(0, 2)).toEqual(["RUN_STARTED", "STATE_SNAPSHOT"]);
  });
});
