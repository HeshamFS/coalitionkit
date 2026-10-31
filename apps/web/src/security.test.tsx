// SPDX-License-Identifier: Apache-2.0
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { App, EXPIRED_NOTICE } from "./App";
import { VoteTally } from "./components/consent";
import { Skeleton, Toast } from "./components/feedback";
import { AvatarStack } from "./components/primitives";
import { answerFor, focusRequest, interruptRevision, matchRequest } from "./feed/actions";
import type { OpenRequest } from "./feed/agent";
import { clearToken, readConfig, saveToken } from "./feed/config";
import { isAuthFailure, openStream, postAnswer } from "./feed/connection";
import { FeedStore } from "./feed/store";
import { m1, m2 } from "./gallery/fixtures";
import { TopBar } from "./shell/bars";
import { TrustedRequest } from "./TrustedRequest";

const plan: OpenRequest = {
  id: "plan:p1:2:u1",
  kind: "plan",
  subjectId: "p1",
  revision: 2,
  message: "Decide on Plan A",
};
const tension: OpenRequest = {
  id: "tension_option:t1:3:u1",
  kind: "tension_option",
  subjectId: "t1",
  revision: 3,
  message: "Pick an option",
};

const enc = new TextEncoder();
const sse = (events: object[]) =>
  new Response(
    new ReadableStream({
      start(c) {
        for (const e of events) c.enqueue(enc.encode(`data: ${JSON.stringify(e)}\n\n`));
      },
    }),
    { headers: { "Content-Type": "text/event-stream" } },
  );

const stubMedia = () =>
  vi.stubGlobal("matchMedia", (q: string) => ({
    matches: false,
    media: q,
    addEventListener() {},
    removeEventListener() {},
  }));

const treeOf = (component: Record<string, unknown>) => [
  { version: "v0.9", createSurface: { surfaceId: "s1", catalogId: "coalitionkit/v0_9" } },
  {
    version: "v0.9",
    updateComponents: { surfaceId: "s1", components: [{ id: "root", ...component }] },
  },
];
const ref = (value: number) => ({ value, event_ref: "e1" });
// The trees an agent can compose that emit a decision event.
const consentTree = treeOf({
  component: "ConsentCard",
  subject: { kind: "plan", id: "p1", revision: ref(2) },
  summary: "Tree consent",
  consequence: "Plan A is decided",
  decision_deadline: "2099-01-01T00:00:00Z",
});
const planTree = treeOf({
  component: "PlanCompare",
  plans: [
    {
      id: "p1",
      label: "Plan A",
      short: "A",
      objectives: [],
      subject: { kind: "plan", id: "p1", revision: ref(2) },
    },
  ],
});
const tensionTree = treeOf({
  component: "TensionCard",
  tension_id: "t1",
  subject: { kind: "tension_option", id: "t1", revision: ref(3) },
  decision_deadline: "2099-01-01T00:00:00Z",
  options: [
    { id: "o1", label: "Option 1", tradeoffs: [] },
    { id: "o2", label: "Option 2", tradeoffs: [] },
  ],
  deciders: [],
  answered: ref(0),
});

const planInterrupt = {
  id: "plan:p1:2:u1",
  reason: "consent_required",
  message: "Decide on Plan A",
  metadata: { subject: { kind: "plan", id: "p1", revision: 2 } },
};

function mockHost(posts: unknown[], messages: unknown[], interrupt: object = planInterrupt) {
  return vi.fn(async (url: string, init: RequestInit) => {
    if (url.endsWith("/v1/agent/answers")) {
      posts.push(JSON.parse(String(init.body)));
      return new Response(JSON.stringify({ status: "accepted", seq: 1 }), { status: 200 });
    }
    if (url.endsWith("/v1/feed")) {
      return sse([
        { type: "RUN_STARTED", threadId: "t", runId: "r" },
        { type: "STATE_SNAPSHOT", snapshot: { events: {} } },
        {
          type: "CUSTOM",
          name: "coalitionkit.agent",
          value: {
            type: "RUN_FINISHED",
            outcome: { type: "interrupt", interrupts: [interrupt] },
          },
        },
        {
          type: "ACTIVITY_SNAPSHOT",
          messageId: "a2ui:s1",
          activityType: "a2ui-surface",
          content: { messages },
          replace: true,
        },
      ]);
    }
    return sse([
      { type: "RUN_STARTED", threadId: "ta", runId: "ra" },
      {
        type: "RUN_FINISHED",
        threadId: "ta",
        runId: "ra",
        outcome: { type: "interrupt", interrupts: [interrupt] },
      },
    ]);
  });
}

describe("fix 1: consent only from trusted UI", () => {
  beforeEach(() => {
    saveToken("tok");
    stubMedia();
  });
  afterEach(() => {
    clearToken();
    vi.unstubAllGlobals();
  });

  const tensionInterrupt = {
    id: "tension_option:t1:3:u1",
    reason: "consent_required",
    message: "Pick an option",
    metadata: { subject: { kind: "tension_option", id: "t1", revision: 3 } },
  };
  const cases: [string, unknown[], string, object][] = [
    ["decide (ConsentCard)", consentTree, "Accept", planInterrupt],
    ["plan.decide (PlanCompare)", planTree, "Accept A", planInterrupt],
    ["tension.choose (TensionCard)", tensionTree, "Choose Option 1", tensionInterrupt],
  ];
  for (const [name, messages, label, interrupt] of cases) {
    it(`a tree ${name} action posts nothing`, async () => {
      const posts: unknown[] = [];
      vi.stubGlobal("fetch", mockHost(posts, messages, interrupt));
      render(<App />);
      await waitFor(() => expect(screen.getByText("1 decision waits for you")).toBeInTheDocument());
      await userEvent.click(await screen.findByRole("button", { name: label }));
      await new Promise((r) => setTimeout(r, 60));
      expect(posts).toEqual([]);
    });
  }

  it("a tree action may only focus the trusted card", async () => {
    const posts: unknown[] = [];
    vi.stubGlobal("fetch", mockHost(posts, planTree));
    render(<App />);
    await waitFor(() => expect(screen.getByText("1 decision waits for you")).toBeInTheDocument());
    await userEvent.click(await screen.findByRole("button", { name: "Accept A" }));
    await screen.findByRole("region", { name: /Your yes is needed: Choose (plan A|this plan)/ });
    expect(posts).toEqual([]);
  });

  it("the trusted card is what posts, with the revision-bound interrupt id", async () => {
    const posts: unknown[] = [];
    vi.stubGlobal("fetch", mockHost(posts, planTree));
    render(<App />);
    await userEvent.click(await screen.findByRole("button", { name: "Decide" }));
    await userEvent.click(await screen.findByRole("button", { name: "Review and approve" }));
    await userEvent.click(await screen.findByRole("button", { name: "Confirm approval" }));
    await waitFor(() => expect(posts).toEqual([{ interrupt_id: "plan:p1:2:u1", consent: true }]));
  });
});

describe("fix 2: revision binding", () => {
  it("matches by kind, id and revision", () => {
    expect(matchRequest([plan], { kind: "plan", id: "p1", revision: 2 })).toBe(plan);
    expect(matchRequest([plan], { kind: "plan", id: "p1", revision: 1 })).toBeNull();
    expect(matchRequest([plan], { kind: "plan", id: "p2" })).toBeNull();
    expect(matchRequest([plan], { kind: "commitment", id: "p1" })).toBeNull();
  });
  it("a tree pointing at another revision focuses nothing", () => {
    const rev = (n: number) => ({
      name: "decide",
      context: { subject: { kind: "plan", id: "p1", revision: { value: n, event_ref: "e" } } },
    });
    expect(focusRequest(rev(1), [plan])).toBeNull();
    expect(focusRequest(rev(2), [plan])).toBe(plan);
    expect(focusRequest({ name: "task.done", context: rev(2).context }, [plan])).toBeNull();
  });
  it("the answer carries the revision, and a mismatch is refused", () => {
    expect(interruptRevision(plan.id)).toBe(2);
    expect(answerFor(plan, true)).toEqual({ interrupt_id: "plan:p1:2:u1", consent: true });
    expect(() => answerFor({ ...plan, revision: 3 }, true)).toThrow(/revision/);
    expect(() => answerFor(tension, true)).toThrow(/option/);
    expect(answerFor(tension, true, "o2")).toEqual({
      interrupt_id: "tension_option:t1:3:u1",
      consent: true,
      choice: "o2",
    });
  });
});

const stateWith = (revision: number) => ({
  events: {
    e1: {
      type: "coalition.tension",
      seq: 1,
      payload: {
        tension_id: "t1",
        revision,
        options: [
          { option_id: "o1", summary: "Option 1" },
          { option_id: "o2", summary: "Option 2" },
        ],
        tradeoffs: ["costs more"],
      },
    },
  },
});

describe("fix 3: tension options come from the host state", () => {
  it("answers from the viewer projection with no composed surface at all", async () => {
    const onAnswer = vi.fn();
    render(<TrustedRequest request={tension} state={stateWith(3)} onAnswer={onAnswer} />);
    await userEvent.click(screen.getByRole("radio", { name: /Option 2/ }));
    await userEvent.click(screen.getByRole("button", { name: "Choose Option 2" }));
    expect(onAnswer).toHaveBeenCalledWith({
      interrupt_id: "tension_option:t1:3:u1",
      consent: true,
      choice: "o2",
    });
  });
  it("says options unavailable and offers no answer when the state lacks them", () => {
    const onAnswer = vi.fn();
    const { rerender } = render(
      <TrustedRequest request={tension} state={null} onAnswer={onAnswer} />,
    );
    expect(screen.getByText("Options unavailable.")).toBeInTheDocument();
    expect(screen.queryByRole("button")).toBeNull();
    rerender(<TrustedRequest request={tension} state={stateWith(2)} onAnswer={onAnswer} />);
    expect(screen.getByText("Options unavailable.")).toBeInTheDocument();
    expect(onAnswer).not.toHaveBeenCalled();
  });
});

describe("fix 4: no answer is not no", () => {
  it("shows no answer for a decider who did not answer", () => {
    render(
      <VoteTally
        title="Plan A"
        closed
        outcome="expired"
        deciders={[
          { ...m1, answered: true, answer: false },
          { ...m2, answered: false },
        ]}
      />,
    );
    expect(screen.getByText("Member 1 no")).toBeInTheDocument();
    expect(screen.getByText("Member 2 no answer")).toBeInTheDocument();
    expect(screen.queryByText("Member 2 no")).toBeNull();
  });
});

describe("fix 5: every button variant is in the catalog", () => {
  // The catalog's Button variants are primary | secondary | ink | ghost; any other is refused.
  for (const [variant, accepted] of [
    ["primary", true],
    ["secondary", true],
    ["ink", true],
    ["ghost", true],
    ["danger", false],
  ] as const) {
    it(`${accepted ? "accepts" : "refuses"} ${variant}`, () => {
      const store = new FeedStore();
      store.handle({
        type: "ACTIVITY_SNAPSHOT",
        messageId: "a2ui:s1",
        activityType: "a2ui-surface",
        content: {
          messages: [
            { version: "v0.9", createSurface: { surfaceId: "s1", catalogId: "coalitionkit/v0_9" } },
            {
              version: "v0.9",
              updateComponents: {
                surfaceId: "s1",
                components: [{ id: "root", component: "Button", label: "B", variant }],
              },
            },
          ],
        },
      });
      expect(store.getSnapshot().surfaces[0]?.fallback).toBe(!accepted);
    });
  }
});

describe("fix 6: a refused token ends the session", () => {
  it("treats 401 and 403 as auth failures", () => {
    expect(isAuthFailure(401)).toBe(true);
    expect(isAuthFailure(403)).toBe(true);
    expect(isAuthFailure(500)).toBe(false);
  });
  it("stops retrying the stream after a 401", async () => {
    const fetchFn = vi.fn(
      async (_u: string, _i: RequestInit) => new Response(null, { status: 401 }),
    );
    const onAuthError = vi.fn();
    const stop = openStream({
      config: { baseUrl: "", token: "t" },
      path: "/v1/feed",
      fetchFn,
      delay: () => 5,
      onEvent: () => true,
      onStatus: () => {},
      onAuthError,
    });
    await new Promise((r) => setTimeout(r, 100));
    stop();
    expect(onAuthError).toHaveBeenCalledTimes(1);
    expect(fetchFn).toHaveBeenCalledTimes(1);
  });
  it("a 401 on the answer POST is an auth failure; a 403 with a host code is not", async () => {
    const cfg = { baseUrl: "", token: "t" };
    const body = { interrupt_id: "i", consent: true };
    const r401 = await postAnswer(cfg, body, async () => new Response("{}", { status: 401 }));
    expect(r401).toMatchObject({ ok: false, auth: true });
    const r403 = await postAnswer(
      cfg,
      body,
      async () => new Response(JSON.stringify({ error: "not_your_request" }), { status: 403 }),
    );
    expect(r403).toMatchObject({ ok: false, error: "not_your_request" });
    expect((r403 as { auth?: boolean }).auth).toBeUndefined();
  });
  describe("in the app", () => {
    beforeEach(() => {
      saveToken("old");
      stubMedia();
    });
    afterEach(() => {
      clearToken();
      vi.unstubAllGlobals();
    });
    it("clears the token and returns to sign-in with a message", async () => {
      vi.stubGlobal(
        "fetch",
        vi.fn(async () => new Response(null, { status: 401 })),
      );
      render(<App />);
      await screen.findByRole("form", { name: "Sign in" });
      expect(screen.getByText(EXPIRED_NOTICE)).toBeInTheDocument();
      expect(readConfig("", {})).toBeNull();
    });
    it("has a sign-out control that clears the token", async () => {
      vi.stubGlobal(
        "fetch",
        vi.fn(async () => sse([{ type: "RUN_STARTED", threadId: "t", runId: "r" }])),
      );
      render(<App />);
      await userEvent.click(await screen.findByRole("button", { name: "Sign out" }));
      await screen.findByRole("form", { name: "Sign in" });
      expect(readConfig("", {})).toBeNull();
      expect(screen.queryByText(EXPIRED_NOTICE)).toBeNull();
    });
  });
  it("the top bar offers sign out", async () => {
    const out = vi.fn();
    render(<TopBar title="Room 1" stage="Gather" presence={[]} onSignOut={out} />);
    await userEvent.click(
      within(screen.getByRole("banner")).getByRole("button", { name: "Sign out" }),
    );
    expect(out).toHaveBeenCalled();
  });
});

describe("fix 7: numbers a tree controls are bounded", () => {
  it("skeleton lines are 1 to 20 and reserved height at most 2000 px", () => {
    const { container, rerender } = render(<Skeleton shape="card" lines={100000} />);
    const many = container.querySelectorAll(".skel").length;
    rerender(<Skeleton shape="card" lines={20} />);
    expect(container.querySelectorAll(".skel").length).toBe(many);
    rerender(<Skeleton shape="card" lines={-5} />);
    expect(container.querySelectorAll(".skel").length).toBe(many - 19);
    rerender(<Skeleton shape="block" reserves={9_999_999} />);
    expect(screen.getByRole("status")).toHaveStyle({ minHeight: "2000px" });
  });
  it("toast undo window is at most 60 s", () => {
    render(<Toast tone="done" text="Done" undoWindow={86400} />);
    expect(screen.getByRole("button", { name: /Undo/ })).toHaveTextContent("60 s");
  });
  it("avatar stack shows at most 20", () => {
    const people = Array.from({ length: 40 }, (_, i) => ({
      seat: 1 as const,
      label: `Member ${i}`,
    }));
    render(<AvatarStack people={people} max={1000} />);
    expect(screen.getAllByRole("img")).toHaveLength(21);
  });
  it("an oversized list is refused, so the fixed view shows", () => {
    const tree = (component: Record<string, unknown>) => ({
      type: "ACTIVITY_SNAPSHOT",
      messageId: "a2ui:s1",
      activityType: "a2ui-surface",
      content: {
        messages: [
          { version: "v0.9", createSurface: { surfaceId: "s1", catalogId: "coalitionkit/v0_9" } },
          {
            version: "v0.9",
            updateComponents: { surfaceId: "s1", components: [{ id: "root", ...component }] },
          },
        ],
      },
    });
    const plans = Array.from({ length: 9 }, (_, i) => ({
      id: `p${i}`,
      label: `Plan ${i}`,
      objectives: [],
    }));
    const big = new FeedStore();
    big.handle(tree({ component: "PlanCompare", plans }));
    expect(big.getSnapshot().surfaces[0]?.fallback).toBe(true);
    const ok = new FeedStore();
    ok.handle(tree({ component: "PlanCompare", plans: plans.slice(0, 3) }));
    expect(ok.getSnapshot().surfaces[0]?.fallback).toBe(false);
    const items = Array.from({ length: 201 }, () => ({ when: "w", title: "t", state: "next" }));
    const long = new FeedStore();
    long.handle(tree({ component: "Timeline", items }));
    expect(long.getSnapshot().surfaces[0]?.fallback).toBe(true);
  });
});
