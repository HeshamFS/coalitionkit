// SPDX-License-Identifier: Apache-2.0
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "../App";
import type { OpenRequest } from "../feed/agent";
import { clearToken, saveToken } from "../feed/config";
import { commitmentTask, requestLabel, visibleRequests } from "../feed/derive";
import { isOwner, markOwner } from "../genesis/owner";
import { ConsentTray } from "../shell/dock";
import { sheetFor } from "./consentSheet";
import { beginEnd } from "./ended";

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
const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } });
const stubMedia = () =>
  vi.stubGlobal("matchMedia", (q: string) => ({
    matches: false,
    media: q,
    addEventListener() {},
    removeEventListener() {},
  }));

const room = {
  coalition_id: "c1",
  viewer: "p1",
  events: {
    j: { seq: 1, type: "coalition.join", on_behalf_of: "p1", payload: { card: {} } },
    t: { seq: 2, type: "coalition.task", payload: { task_id: "t1", title: "Bring the chairs" } },
    c: {
      seq: 3,
      type: "coalition.commit",
      on_behalf_of: "p1",
      payload: { task_id: "t1", commitment_id: "c-1", status: "pending" },
    },
  },
};
const req = (kind: string, subjectId: string): OpenRequest => ({
  id: `${kind}:${subjectId}:1:u`,
  kind,
  subjectId,
  revision: 1,
  message: "Your decision is needed",
});
const feed = () =>
  sse([
    { type: "RUN_STARTED", threadId: "t", runId: "r" },
    { type: "STATE_SNAPSHOT", snapshot: room },
  ]);

beforeEach(() => {
  sessionStorage.clear();
  stubMedia();
});
afterEach(() => {
  beginEnd(null);
  clearToken();
  sessionStorage.clear();
  vi.unstubAllGlobals();
});

describe("owner flag", () => {
  it("is cleared on sign out", async () => {
    saveToken("owner-token");
    markOwner("c1");
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => sse([{ type: "RUN_STARTED", threadId: "t", runId: "r" }])),
    );
    render(<App />);
    expect(isOwner()).toBe(true);
    await userEvent.click(await screen.findByRole("button", { name: "Sign out" }));
    await screen.findByRole("form", { name: "Sign in" });
    expect(sessionStorage.getItem("ck.owner")).toBeNull();
  });
});

describe("ending a coalition", () => {
  it("confirms, posts with the owner token and shows the report", async () => {
    saveToken("owner-token");
    markOwner("c1");
    const calls: { url: string; init: RequestInit }[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string, init: RequestInit) => {
        calls.push({ url, init });
        if (url.endsWith("/v1/coalition/dissolve"))
          return json({
            seq: 9,
            tasks_closed: 2,
            tokens_revoked: 3,
            invitations_revoked: 1,
            vaults_erased: 0,
          });
        return feed();
      }),
    );
    render(<App />);
    await userEvent.click(await screen.findByRole("button", { name: "End coalition" }));
    screen.getByText("End this coalition for everyone?");
    await userEvent.click(screen.getByRole("button", { name: "Keep going" }));
    expect(screen.queryByText("End this coalition for everyone?")).toBeNull();
    await userEvent.click(screen.getByRole("button", { name: "End coalition" }));
    const dialog = screen.getByRole("dialog");
    await userEvent.click(within(dialog).getByRole("button", { name: "End coalition" }));
    await screen.findByText("2 tasks closed");
    expect(screen.getByText("Nothing kept")).toBeTruthy();
    const post = calls.find((c) => c.url.endsWith("/v1/coalition/dissolve"));
    expect(new Headers(post?.init.headers).get("authorization")).toBe("Bearer owner-token");
    expect(JSON.parse(String(post?.init.body))).toEqual({ reason: "completed" });
  });
  it("shows the failed step and Retry asks again", async () => {
    let n = 0;
    const calls: string[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) => {
        if (!url.endsWith("/v1/coalition/dissolve")) return feed();
        calls.push(url);
        n += 1;
        return n === 1
          ? json({ failed: "vaults", done: { tasks_closed: 2 } }, 500)
          : json({ tasks_closed: 2, tokens_revoked: 1, invitations_revoked: 0, vaults_erased: 1 });
      }),
    );
    beginEnd({ token: "owner-token", reason: "cancelled" });
    render(<App />);
    await screen.findByText("Cleanup stopped at: vaults");
    expect(screen.getByText("2 tasks closed")).toBeTruthy();
    await userEvent.click(screen.getByRole("button", { name: "Retry" }));
    await screen.findByText("1 hosted vault erased");
    expect(calls).toHaveLength(2);
  });
});

describe("a refused or unreachable end", () => {
  it.each([
    [403, /refused \(403\)/],
    [0, /not known whether the coalition ended/],
  ])("keeps the room and the session (%s)", async (status, message) => {
    saveToken("owner-token");
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) => {
        if (!url.endsWith("/v1/coalition/dissolve")) return feed();
        if (status === 0) throw new TypeError("network down");
        return json({ detail: "owner required" }, status);
      }),
    );
    beginEnd({ token: "owner-token", reason: "completed" });
    render(<App />);
    expect((await screen.findByRole("alert")).textContent).toMatch(message);
    expect(screen.queryByText(/table folds away/)).toBeNull();
    await userEvent.click(screen.getByRole("button", { name: "Back to the room" }));
    expect(sessionStorage.getItem("ck.token")).toBe("owner-token");
  });
});

describe("a member whose session ends after the dissolve", () => {
  it("sees the ended view, not sign-in", async () => {
    saveToken("member-token");
    sessionStorage.setItem("ck.ended", JSON.stringify({ reason: "completed", skills_written: [] }));
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response(null, { status: 401 })),
    );
    render(<App />);
    await screen.findByRole("main", { name: "The coalition has ended" });
    expect(screen.getByText(/Goal met/)).toBeTruthy();
    expect(screen.queryByRole("form", { name: "Sign in" })).toBeNull();
  });
  it("remembers the event when the room renders it", async () => {
    saveToken("member-token");
    const events = {
      ...room.events,
      d: {
        seq: 4,
        type: "coalition.dissolve",
        payload: { reason: "cancelled", skills_written: ["s1"] },
      },
    };
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        sse([
          { type: "RUN_STARTED", threadId: "t", runId: "r" },
          { type: "STATE_SNAPSHOT", snapshot: { ...room, events } },
        ]),
      ),
    );
    render(<App />);
    await vi.waitFor(() =>
      expect(JSON.parse(sessionStorage.getItem("ck.ended") ?? "null")).toEqual({
        reason: "cancelled",
        skills_written: ["s1"],
      }),
    );
  });
});

describe("a commitment's words", () => {
  const state = room as never;
  it("names the task in the consent sheet", () => {
    expect(commitmentTask(state, "c-1")).toEqual({ id: "t1", description: "Bring the chairs" });
    expect(sheetFor(req("commitment", "c-1"), state).yes[0]).toBe(
      "You commit to: Bring the chairs",
    );
    expect(sheetFor(req("commitment", "zzz"), state).yes[0]).toBe(
      "You commit to: your part in the chosen plan",
    );
  });
  it("folds the task ask into the commitment ask and labels it", () => {
    const shown = visibleRequests(state, [req("commitment", "c-1"), req("task", "t1")]);
    expect(shown.map((r) => r.kind)).toEqual(["commitment"]);
    expect(requestLabel(state, shown[0] as OpenRequest)).toBe("Commit to Bring the chairs");
    expect(visibleRequests(state, [req("task", "t1")])).toHaveLength(1);
  });
  it("gives a task ask a badge", () => {
    render(
      <ConsentTray
        requests={[
          { id: "a", kind: "task", title: "Do a thing" },
          { id: "b", kind: "task", title: "Do another" },
        ]}
      />,
    );
    expect(screen.getAllByText("Approve")).toHaveLength(2);
  });
});
