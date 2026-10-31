// SPDX-License-Identifier: Apache-2.0
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ChainView, chainInputFrom } from "./ChainView";
import { type Envelope, entryHash, type VerifyInput } from "./verify";

// biome-ignore lint/suspicious/noExplicitAny: vector is untyped JSON
const LOG: any = JSON.parse(
  readFileSync(join(process.cwd(), "../../spec/vectors/log.json"), "utf8"),
);
const x = Buffer.from(LOG.host_key.public_key_hex, "hex").toString("base64url");
const G = LOG.genesis;

const state = () => ({
  log: {
    coalition_id: G.coalition_id,
    host_card_url: G.host_card_url,
    created_at: G.created_at,
    host_key: { kty: "OKP", crv: "Ed25519", kid: LOG.host_key.kid, x },
    entries: structuredClone(LOG.entries),
    receipts: structuredClone(LOG.receipts),
  },
});

function input(): VerifyInput {
  const found = chainInputFrom(state());
  if (!found) throw new Error("fixture input is complete");
  return found;
}

describe("chainInputFrom", () => {
  it("is null when the state lacks the log or any needed field", () => {
    expect(chainInputFrom(undefined)).toBeNull();
    expect(chainInputFrom({})).toBeNull();
    for (const field of ["coalition_id", "host_card_url", "created_at", "host_key", "entries"]) {
      const s = state();
      delete (s.log as Record<string, unknown>)[field];
      expect(chainInputFrom(s)).toBeNull();
    }
    const noReceipts = state();
    (noReceipts.log as Record<string, unknown>).receipts = "none";
    expect(chainInputFrom(noReceipts)).toBeNull();
  });

  it("reads a complete log", () => {
    expect(input().entries).toHaveLength(4);
    expect(input().coalitionId).toBe(G.coalition_id);
  });
});

describe("ChainView", () => {
  it("says the log is not in the feed and never shows a verified claim", () => {
    render(<ChainView input={null} />);
    expect(screen.getByText("The log is not in your feed yet")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /verify/i })).toBeNull();
    expect(screen.queryByText(/verified/i)).toBeNull();
  });

  it("claims nothing before Verify, then reports the proven range and receipt", async () => {
    render(<ChainView input={input()} />);
    await screen.findByText("seq 4");
    expect(screen.queryByText(/Verified up to/)).toBeNull();
    expect(screen.queryByText("linked")).toBeNull();
    await userEvent.click(screen.getByRole("button", { name: "Verify" }));
    expect(
      await screen.findByText("Verified up to seq 4 · covered by your receipt at seq 4"),
    ).toBeInTheDocument();
    expect(screen.getByText("receipt · head matches · seq 4")).toBeInTheDocument();
    expect(screen.getAllByText("linked")).toHaveLength(4);
  });

  it("says no receipt covers the log when none was kept", async () => {
    const i = input();
    render(<ChainView input={{ ...i, receipts: [] }} />);
    await userEvent.click(screen.getByRole("button", { name: "Verify" }));
    expect(await screen.findByText(/Verified up to seq 4 · no receipt kept/)).toBeInTheDocument();
    expect(screen.queryByText(/receipt · head matches/)).toBeNull();
  });

  it("draws the broken link in red with the check name", async () => {
    const i = input();
    ((i.entries[1] as Envelope)?.payload as Record<string, unknown>).reason = "edited";
    render(<ChainView input={i} />);
    await userEvent.click(screen.getByRole("button", { name: "Verify" }));
    const text = await screen.findByText(/Broken at seq 3 · hash link check failed/);
    expect(text).toHaveClass("is-broken");
    expect(screen.getByText("link broken").closest("li")).toHaveClass("is-broken");
    expect(screen.queryByText(/Verified up to/)).toBeNull();
    expect(screen.queryByText("linked")).toBeNull();
  });

  it("names the receipt check when only a receipt catches the edit", async () => {
    const i = input();
    ((i.entries[3] as Envelope)?.payload as Record<string, unknown>).reason = "edited tail";
    render(<ChainView input={i} />);
    await userEvent.click(screen.getByRole("button", { name: "Verify" }));
    expect(await screen.findByText(/Broken at seq 4 · receipt check failed/)).toBeInTheDocument();
  });

  it("labels stubs as outside your scope and keeps the chain verifiable", async () => {
    const i = input();
    const entry = i.entries[1] as Envelope;
    i.entries[1] = { seq: 2, prev_hash: entry.prev_hash as string, hash: await entryHash(entry) };
    render(<ChainView input={i} />);
    expect(await screen.findByText("outside your scope")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Verify" }));
    await waitFor(() => expect(screen.getByText(/Verified up to seq 4/)).toBeInTheDocument());
  });
});

describe("pinned host key and stale results", () => {
  it("refuses a log whose host key differs from the one first seen", async () => {
    localStorage.setItem(`ck.hostkey.${input().coalitionId}`, "a-different-key");
    render(<ChainView input={input()} />);
    await userEvent.click(screen.getByRole("button", { name: "Verify" }));
    expect(await screen.findByText(/differs from the one pinned/)).toBeInTheDocument();
    expect(screen.queryByText("Verified")).toBeNull();
    localStorage.clear();
  });

  it("a storage error ends the run with a visible failure", async () => {
    const spy = vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    render(<ChainView input={input()} />);
    await userEvent.click(screen.getByRole("button", { name: "Verify" }));
    expect(await screen.findByText(/could not be read/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Verify again" })).toHaveProperty("disabled", false);
    spy.mockRestore();
  });

  it("says so when the key was not pinned at join", async () => {
    localStorage.clear();
    render(<ChainView input={input()} />);
    await userEvent.click(screen.getByRole("button", { name: "Verify" }));
    expect(await screen.findByRole("note")).toHaveTextContent(/did not see the host key/);
  });
});
