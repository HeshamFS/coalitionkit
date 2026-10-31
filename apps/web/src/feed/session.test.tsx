// SPDX-License-Identifier: Apache-2.0
import { render } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { HostConfig } from "./config";
import type { Fetch } from "./connection";
import { type FeedApi, FeedProvider, useFeedApi } from "./useFeed";

const config: HostConfig = { baseUrl: "", token: "token-a" };

function Grab({ into }: { into: (api: FeedApi) => void }) {
  into(useFeedApi());
  return null;
}

describe("a late answer from an earlier session", () => {
  it("never signs out the session that replaced it", async () => {
    let release: (r: Response) => void = () => {};
    const fetchFn: Fetch = vi.fn((url: string) => {
      if (String(url).endsWith("/v1/agent/answers")) {
        return new Promise<Response>((resolve) => {
          release = resolve;
        });
      }
      return new Promise<Response>(() => {}); // streams stay open
    }) as unknown as Fetch;
    const onSignedOut = vi.fn();
    let api: FeedApi | null = null;
    const view = render(
      <FeedProvider config={config} fetchFn={fetchFn} onSignedOut={onSignedOut}>
        <Grab into={(a) => (api = a)} />
      </FeedProvider>,
    );
    const pending = (api as unknown as FeedApi).answer({
      interrupt_id: "plan:p1:2:u1",
      consent: true,
    });
    view.unmount(); // the viewer signed in again; this provider is gone
    release(new Response("{}", { status: 401 }));
    await pending;
    expect(onSignedOut).not.toHaveBeenCalled();
  });
});

it("opens one stream per tab and delivers the agent channel on the feed", async () => {
  let push: (event: object) => void = () => {};
  const fetchFn = vi.fn(
    async (_url: string, _init: RequestInit) =>
      new Response(
        new ReadableStream({
          start(c) {
            push = (event) =>
              c.enqueue(new TextEncoder().encode(`data: ${JSON.stringify(event)}\n\n`));
          },
        }),
        { headers: { "Content-Type": "text/event-stream" } },
      ),
  );
  let api: FeedApi | undefined;
  const view = render(
    <FeedProvider config={config} fetchFn={fetchFn}>
      <Grab
        into={(a) => {
          api = a;
        }}
      />
    </FeedProvider>,
  );
  await vi.waitFor(() => expect(fetchFn).toHaveBeenCalledTimes(1));
  expect(fetchFn.mock.calls[0]?.[0]).toBe("/v1/feed");
  const agent = (value: object) => push({ type: "CUSTOM", name: "coalitionkit.agent", value });
  push({ type: "RUN_STARTED", threadId: "feed", runId: "f1" });
  push({
    type: "STATE_SNAPSHOT",
    snapshot: { events: {}, refusals: [{ type: "coalition.decide", code: "steward_blocked" }] },
  });
  agent({ type: "TEXT_MESSAGE_START", messageId: "m1", role: "assistant" });
  agent({ type: "TEXT_MESSAGE_CONTENT", messageId: "m1", delta: '{"vault_result":{"ok":true}}' });
  agent({ type: "TEXT_MESSAGE_END", messageId: "m1" });
  agent({
    type: "RUN_FINISHED",
    outcome: {
      type: "interrupt",
      interrupts: [
        { id: "plan:p1:1:a", metadata: { subject: { kind: "plan", id: "p1", revision: 1 } } },
      ],
    },
  });
  await vi.waitFor(() => expect(api?.agent.getSnapshot().requests).toHaveLength(1));
  expect(api?.agent.getSnapshot().lines[0]?.text).toBe('{"vault_result":{"ok":true}}');
  expect(api?.agent.getSnapshot().refusal).toBe("coalition.decide: steward_blocked");
  api?.agent.setRefusal(null);
  push({
    type: "STATE_DELTA",
    delta: [
      {
        op: "add",
        path: "/refusals/-",
        value: {
          type: "coalition.decide",
          code: "steward_blocked",
        },
      },
    ],
  });
  await vi.waitFor(() =>
    expect(api?.agent.getSnapshot().refusal).toBe("coalition.decide: steward_blocked"),
  );
  push({ type: "RUN_FINISHED", threadId: "feed", runId: "f1", outcome: { type: "success" } });
  agent({ type: "RUN_STARTED", threadId: "agent", runId: "a2" });
  await vi.waitFor(() => expect(api?.feed.getSnapshot().runId).toBe("f1"));
  expect(api?.agent.getSnapshot().requests).toHaveLength(1);
  expect(fetchFn).toHaveBeenCalledTimes(1);
  agent({ type: "RUN_FINISHED", outcome: { type: "success" } });
  await vi.waitFor(() => expect(api?.agent.getSnapshot().requests).toHaveLength(0));
  view.unmount();
  expect(fetchFn.mock.calls[0]?.[1].signal?.aborted).toBe(true);
});
