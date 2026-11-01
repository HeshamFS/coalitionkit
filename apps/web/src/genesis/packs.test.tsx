// SPDX-License-Identifier: Apache-2.0
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { DraftReply, PackInfo } from "./api";
import { forgetStartCode } from "./fragment";
import { Genesis } from "./Genesis";

vi.setConfig({ testTimeout: 15000 });

const CODE = "abcdefghijklmnopqrstuvwxyz012345";
const GOAL = "Three of us need to agree on a plan";
const REF = { name: "kit-a", version: "1.0.0" };

const pack: PackInfo = {
  ...REF,
  label: "Kit A",
  roles: { lead: { label: "Lead", may: ["offer"] } },
  vocabulary: { need: { one: "request", other: "requests" } },
};

const plain: DraftReply = {
  draft: {
    goal: GOAL,
    roles: [{ id: "member", label: "member", count: 3 }],
    needs: ["agree on a plan"],
    deadline: null,
    deciders: "all",
    pack: null,
  },
  source: "reader",
  reading: [],
  suggested: { ...REF, why: ["agree"] },
  vocabulary: {},
};
const chosen: DraftReply = {
  ...plain,
  draft: { ...plain.draft, pack: REF, roles: [{ id: "lead", label: "Lead", count: 3 }] },
  vocabulary: pack.vocabulary,
};

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } });

type Call = { path: string; body: Record<string, unknown> | null };

function host(packs: PackInfo[]) {
  const calls: Call[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init: RequestInit) => {
      const path = new URL(url, "http://127.0.0.1").pathname;
      const body = init.body ? JSON.parse(String(init.body)) : null;
      calls.push({ path, body });
      if (path === "/v1/packs") return json(packs);
      if (path === "/v1/genesis/draft") return json(body?.pack ? chosen : plain);
      if (path === "/v1/genesis/start") {
        return json({ coalition_id: "c1", owner: { participant: "p1", token: "t" } });
      }
      return json({ detail: "not found" }, 404);
    }),
  );
  return calls;
}

beforeEach(() => {
  forgetStartCode();
  sessionStorage.clear();
  history.replaceState(null, "", `/#start=${CODE}`);
});
afterEach(() => vi.unstubAllGlobals());

const drafts = (calls: Call[]) => calls.filter((c) => c.path === "/v1/genesis/draft");
const lastPack = (calls: Call[]) => drafts(calls).at(-1)?.body?.pack;

describe("Genesis pack chip", () => {
  it("lists the installed packs and a plain-language chip", async () => {
    host([pack]);
    render(<Genesis onEnter={() => {}} />);
    await userEvent.type(screen.getByLabelText("What should get done?"), "x");
    expect(await screen.findByRole("button", { name: "Kit A" }, { timeout: 4000 })).toBeTruthy();
    expect(screen.getByRole("button", { name: "No pack: plain language" })).toBeTruthy();
  });

  it("preselects the host suggestion, says why, and re-drafts with the pack", async () => {
    const calls = host([pack]);
    render(<Genesis onEnter={() => {}} />);
    await userEvent.type(screen.getByLabelText("What should get done?"), GOAL);
    const chip = await screen.findByRole("button", { name: "Kit A" }, { timeout: 4000 });
    await waitFor(() => expect(chip.getAttribute("aria-pressed")).toBe("true"), { timeout: 4000 });
    await waitFor(() => expect(lastPack(calls)).toEqual(REF), { timeout: 4000 });
    expect(await screen.findByText(/Suggested because: agree/)).toBeTruthy();
    // the pack word replaces the core noun on the needs card
    expect(await screen.findByLabelText("Requests", undefined, { timeout: 4000 })).toBeTruthy();
  });

  it("choosing no pack re-drafts without one, and Start sends the chosen pack", async () => {
    const calls = host([pack]);
    render(<Genesis onEnter={() => {}} />);
    await userEvent.type(screen.getByLabelText("What should get done?"), GOAL);
    const plainChip = await screen.findByRole(
      "button",
      { name: "No pack: plain language" },
      { timeout: 4000 },
    );
    await waitFor(() => expect(lastPack(calls)).toEqual(REF), { timeout: 4000 });
    await userEvent.click(plainChip);
    await waitFor(() => expect(lastPack(calls)).toBeUndefined(), { timeout: 4000 });
    await userEvent.click(screen.getByRole("button", { name: "Kit A" }));
    await waitFor(() => expect(lastPack(calls)).toEqual(REF), { timeout: 4000 });
    const start = await screen.findByRole("button", { name: "Set the goal" }, { timeout: 4000 });
    await waitFor(() => expect(start).toHaveProperty("disabled", false), { timeout: 4000 });
    await userEvent.click(start);
    await screen.findByText("Goal set · the Gardener is drafting the first plans");
    const sent = calls.find((c) => c.path === "/v1/genesis/start");
    const draft = sent?.body?.draft as { pack: unknown } | undefined;
    expect(draft?.pack).toEqual(REF);
  });

  it("with no pack installed, reads as before", async () => {
    host([]);
    render(<Genesis onEnter={() => {}} />);
    await userEvent.type(screen.getByLabelText("What should get done?"), GOAL);
    await screen.findByText(/None is installed on this host/, undefined, { timeout: 4000 });
    expect(screen.queryByRole("button", { name: "No pack: plain language" })).toBeNull();
    expect(screen.getByLabelText("Needs")).toBeTruthy();
  });
});
