// SPDX-License-Identifier: Apache-2.0
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { saveToken } from "../feed/config";
import type { ViewerState } from "../feed/delta";
import { OfferPanel } from "./offerPanel";

const schema = {
  type: "object",
  properties: {
    size: { type: "string", title: "Size", enum: ["small", "large"] },
    limit: { type: "string", title: "My limit", "x-private": true },
  },
  required: ["size"],
};

function state(withSchema: boolean): ViewerState {
  return {
    viewer: "p1",
    events: {
      "1": {
        seq: 1,
        type: "coalition.need",
        on_behalf_of: "host",
        payload: { need_id: "n1", description: "task t1" },
      },
    },
    ...(withSchema ? { pack: { name: "x", version: "1.0.0", schemas: { offer: schema } } } : {}),
  } as unknown as ViewerState;
}

type Call = { url: string; init: RequestInit };

function host(status = 200) {
  const calls: Call[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init: RequestInit) => {
      calls.push({ url, init });
      if (url.endsWith("/v1/agent/vault") && init.method === "GET") {
        return new Response(JSON.stringify({ keys: [] }), { status: 200 });
      }
      const body = status === 200 ? { seq: 7, offer_id: "o1", keys: ["limit"] } : { error: "x" };
      return new Response(JSON.stringify(body), { status });
    }),
  );
  return calls;
}

beforeEach(() => {
  sessionStorage.clear();
  saveToken("viewer-token");
});
afterEach(() => vi.unstubAllGlobals());

describe("offer panel", () => {
  it("shows nothing when the pack adds no offer fields", () => {
    host();
    const { container } = render(<OfferPanel state={state(false)} />);
    expect(container.textContent).toBe("");
  });

  it("sends the public fields through my agent and never the private one", async () => {
    const calls = host();
    render(<OfferPanel state={state(true)} />);
    await userEvent.selectOptions(screen.getByLabelText(/Size/), "large");
    await userEvent.click(screen.getByRole("button", { name: "Send through my agent" }));
    await screen.findByText(/sent the offer \(seq 7\)/);
    const offer = calls.find((c) => c.url.endsWith("/v1/agent/offer"));
    expect(JSON.parse(String(offer?.init.body))).toEqual({ need_id: "n1", ext: { size: "large" } });
    expect(new Headers(offer?.init.headers).get("authorization")).toBe("Bearer viewer-token");
  });

  it("keeps a private value only in my vault", async () => {
    const calls = host();
    render(<OfferPanel state={state(true)} />);
    await userEvent.type(screen.getByLabelText(/My limit/), "40");
    await userEvent.click(screen.getByRole("button", { name: "Keep in my vault" }));
    await screen.findByText(/Kept in your vault/);
    const saved = calls.find((c) => c.url.endsWith("/v1/agent/vault") && c.init.method === "POST");
    expect(JSON.parse(String(saved?.init.body))).toEqual({ values: { limit: "40" } });
    expect(
      calls.some((c) => String(c.init.body ?? "").includes("40") && c.url.endsWith("/offer")),
    ).toBe(false);
  });

  it("explains a member whose own agent sends offers", async () => {
    host(409);
    render(<OfferPanel state={state(true)} />);
    await userEvent.selectOptions(screen.getByLabelText(/Size/), "small");
    await userEvent.click(screen.getByRole("button", { name: "Send through my agent" }));
    await waitFor(() => expect(screen.getByText(/own agent sends offers/)).toBeTruthy());
  });
});
