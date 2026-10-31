// SPDX-License-Identifier: Apache-2.0
import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { readConfig } from "../feed/config";
import type { DraftReply } from "./api";
import { forgetStartCode, takeInvitation, takeStartCode } from "./fragment";
import { Genesis } from "./Genesis";
import { Join } from "./Join";

// Typing whole sentences takes a few seconds under a busy test run.
vi.setConfig({ testTimeout: 15000 });

const CODE = "abcdefghijklmnopqrstuvwxyz012345";

const reply: DraftReply = {
  draft: {
    goal: "Three of us need to agree on a plan by Friday",
    roles: [{ id: "member", label: "member", count: 3 }],
    needs: ["agree on a plan"],
    deadline: "2026-11-06T17:00:00Z",
    deciders: "all",
    pack: null,
  },
  source: "reader",
  reading: [
    { span: [0, 5], kind: "count" },
    { span: [36, 45], kind: "deadline" },
  ],
};

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

type Call = { url: string; init: RequestInit };

function host(handlers: Record<string, (init: RequestInit) => Response>) {
  const calls: Call[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init: RequestInit) => {
      calls.push({ url, init });
      const path = new URL(url, "http://127.0.0.1").pathname;
      const h = handlers[path];
      return h ? h(init) : json({ detail: "not found" }, 404);
    }),
  );
  return calls;
}

beforeEach(() => {
  forgetStartCode();
  sessionStorage.clear();
  history.replaceState(null, "", "/");
});
afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

describe("fragment secrets", () => {
  it("takes the start code once and removes it from the address", () => {
    history.replaceState(null, "", `/#start=${CODE}`);
    expect(takeStartCode()).toBe(CODE);
    expect(location.hash).toBe("");
    expect(location.href).not.toContain(CODE);
    expect(takeStartCode()).toBe(CODE);
  });
  it("ignores a malformed start fragment", () => {
    history.replaceState(null, "", "/#start=<script>");
    expect(takeStartCode()).toBe("");
  });
  it("takes an invitation from /join#secret and clears it", () => {
    history.replaceState(null, "", `/join#${CODE}`);
    expect(takeInvitation()).toBe(CODE);
    expect(location.href).not.toContain(CODE);
  });
});

describe("Genesis", () => {
  it("reads the goal, fills seats and germinates the draft cards", async () => {
    const calls = host({ "/v1/genesis/draft": () => json(reply) });
    render(<Genesis onEnter={() => {}} />);
    await userEvent.type(screen.getByLabelText("What should get done?"), reply.draft.goal);
    await screen.findByRole("img", { name: "3 of 7 seats found so far" }, { timeout: 3000 });
    const draftCall = calls.find((c) => c.url.endsWith("/v1/genesis/draft"));
    expect(JSON.parse(String(draftCall?.init.body))).toEqual({
      goal: reply.draft.goal,
      utc_offset_minutes: -new Date().getTimezoneOffset(),
    });
    expect(new Headers(draftCall?.init.headers).get("authorization")).toBeNull();
    await screen.findByDisplayValue("member", undefined, { timeout: 2000 });
    expect(await screen.findByText("agree on a plan")).toBeTruthy();
    expect(screen.getByText("Read without a model")).toBeTruthy();
  });

  it("cannot start without the start link and says how to get one", async () => {
    host({ "/v1/genesis/draft": () => json(reply) });
    render(<Genesis onEnter={() => {}} />);
    await userEvent.type(screen.getByLabelText("What should get done?"), reply.draft.goal);
    await screen.findByText("Read without a model", undefined, { timeout: 3000 });
    expect(screen.getByRole("button", { name: "Set the goal" })).toHaveProperty("disabled", true);
    expect(screen.getByText(/coalitionkit up/)).toBeTruthy();
  });

  it("an edit stops re-reading and the edited draft is what starts", async () => {
    history.replaceState(null, "", `/#start=${CODE}`);
    const calls = host({
      "/v1/genesis/draft": () => json(reply),
      "/v1/genesis/start": () =>
        json({
          coalition_id: "c1",
          owner: { participant: "p1", token: "owner-token-1" },
          host_key: { kty: "OKP", crv: "Ed25519", x: "host-x-1", kid: "host" },
        }),
    });
    const onEnter = vi.fn();
    render(<Genesis onEnter={onEnter} />);
    const input = screen.getByLabelText("What should get done?");
    await userEvent.type(input, reply.draft.goal);
    const seat = await screen.findByDisplayValue("member", undefined, { timeout: 3000 });
    await userEvent.clear(seat);
    await userEvent.type(seat, "reviewer");
    expect(screen.getByText("Edited by you")).toBeTruthy();
    const drafts = calls.filter((c) => c.url.endsWith("/v1/genesis/draft")).length;
    await userEvent.type(input, " today");
    await act(() => new Promise((r) => setTimeout(r, 900)));
    expect(calls.filter((c) => c.url.endsWith("/v1/genesis/draft")).length).toBe(drafts);

    await userEvent.click(screen.getByRole("button", { name: "Set the goal" }));
    await screen.findByText("Goal set · the Gardener is drafting the first plans");
    const start = calls.find((c) => c.url.endsWith("/v1/genesis/start"));
    expect(new Headers(start?.init.headers).get("authorization")).toBe(`Start ${CODE}`);
    const body = JSON.parse(String(start?.init.body));
    expect(body.draft.roles[0].label).toBe("reviewer");
    expect(readConfig("", {})?.token).toBe("owner-token-1");
    expect(localStorage.getItem("ck.hostkey.c1")).toBe("host-x-1");
    expect(sessionStorage.getItem("ck.start")).toBeNull();
    await userEvent.click(screen.getByRole("button", { name: "Enter the room" }));
    expect(onEnter).toHaveBeenCalled();
  });

  it("invites with the owner token and never shows the secret in full", async () => {
    history.replaceState(null, "", `/#start=${CODE}`);
    const calls = host({
      "/v1/genesis/draft": () => json(reply),
      "/v1/genesis/start": () =>
        json({ coalition_id: "c1", owner: { participant: "p1", token: "owner-token-2" } }),
      "/v1/invitations": () =>
        json({
          invitations: [
            { id: "i1", kind: "member", link: "http://127.0.0.1/join#secretsecretsecret1" },
          ],
        }),
    });
    render(<Genesis onEnter={() => {}} />);
    await userEvent.type(screen.getByLabelText("What should get done?"), reply.draft.goal);
    await screen.findByText("Read without a model", undefined, { timeout: 3000 });
    await userEvent.click(screen.getByRole("button", { name: "Set the goal" }));
    await userEvent.click(await screen.findByRole("button", { name: "Link for a person" }));
    await screen.findByText("http://127.0.0.1/join#••••");
    expect(screen.queryByText(/secretsecretsecret1/)).toBeNull();
    const inv = calls.find((c) => c.url.endsWith("/v1/invitations"));
    expect(new Headers(inv?.init.headers).get("authorization")).toBe("Bearer owner-token-2");
  });

  it("explains a used start link", async () => {
    history.replaceState(null, "", `/#start=${CODE}`);
    host({
      "/v1/genesis/draft": () => json(reply),
      "/v1/genesis/start": () => json({ detail: "start code refused" }, 401),
    });
    render(<Genesis onEnter={() => {}} />);
    await userEvent.type(screen.getByLabelText("What should get done?"), reply.draft.goal);
    await screen.findByText("Read without a model", undefined, { timeout: 3000 });
    await userEvent.click(screen.getByRole("button", { name: "Set the goal" }));
    expect((await screen.findByRole("alert")).textContent).toMatch(/used or has expired/);
  });

  it("says when the host does not take coalitions from the web", async () => {
    host({});
    render(<Genesis onEnter={() => {}} />);
    await userEvent.type(screen.getByLabelText("What should get done?"), "anything at all");
    expect((await screen.findByRole("alert", undefined, { timeout: 3000 })).textContent).toMatch(
      /does not take new coalitions/,
    );
  });
});

describe("Join", () => {
  it("exchanges the invitation for a token without a token box", async () => {
    history.replaceState(null, "", `/join#${CODE}`);
    const calls = host({
      "/v1/invitations/accept": () => json({ coalition_id: "c1", participant: "p2", token: "t2" }),
    });
    const onJoined = vi.fn();
    render(<Join onJoined={onJoined} />);
    expect(screen.queryByLabelText("Viewer token")).toBeNull();
    await userEvent.click(screen.getByRole("button", { name: "Join" }));
    await waitFor(() => expect(onJoined).toHaveBeenCalled());
    const body = JSON.parse(String(calls[0]?.init.body));
    expect(body).toEqual({ invitation: CODE });
    expect(readConfig("", {})?.token).toBe("t2");
  });
  it("explains a used invitation", async () => {
    history.replaceState(null, "", `/join#${CODE}`);
    host({ "/v1/invitations/accept": () => json({ detail: "refused" }, 400) });
    render(<Join onJoined={() => {}} />);
    await userEvent.click(screen.getByRole("button", { name: "Join" }));
    expect((await screen.findByRole("alert")).textContent).toMatch(/used or withdrawn/);
  });
  it("without an invitation in the link it cannot join", () => {
    history.replaceState(null, "", "/join");
    render(<Join onJoined={() => {}} />);
    expect(screen.getByRole("button", { name: "Join" })).toHaveProperty("disabled", true);
  });
});

describe("Genesis draft freshness", () => {
  it("never starts with a draft of an older sentence", async () => {
    history.replaceState(null, "", `/#start=${CODE}`);
    host({ "/v1/genesis/draft": () => json(reply) });
    render(<Genesis onEnter={() => {}} />);
    const input = screen.getByLabelText("What should get done?");
    await userEvent.type(input, reply.draft.goal);
    await screen.findByText("Read without a model", undefined, { timeout: 3000 });
    expect(screen.getByRole("button", { name: "Set the goal" })).toHaveProperty("disabled", false);
    await userEvent.type(input, " and more");
    expect(screen.getByRole("button", { name: "Set the goal" })).toHaveProperty("disabled", true);
  });

  it("a reading that arrives after an edit does not overwrite the edit", async () => {
    let release: (r: Response) => void = () => {};
    let calls = 0;
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        calls += 1;
        if (calls === 1) return json(reply);
        return new Promise<Response>((resolve) => {
          release = resolve;
        });
      }),
    );
    render(<Genesis onEnter={() => {}} />);
    const input = screen.getByLabelText("What should get done?");
    await userEvent.type(input, reply.draft.goal);
    const seat = await screen.findByDisplayValue("member", undefined, { timeout: 3000 });
    await userEvent.type(input, "!");
    await act(() => new Promise((r) => setTimeout(r, 800)));
    await userEvent.clear(seat);
    await userEvent.type(seat, "reviewer");
    await act(async () =>
      release(
        json({
          ...reply,
          draft: { ...reply.draft, roles: [{ id: "x", label: "late", count: 2 }] },
        }),
      ),
    );
    expect(screen.getByDisplayValue("reviewer")).toBeTruthy();
    expect(screen.queryByDisplayValue("late")).toBeNull();
  });
});
