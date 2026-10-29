// SPDX-License-Identifier: Apache-2.0
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";
import { CONFIRM_PREFIX, confirmCode, FAILURE_TEXT } from "./ConfirmRoute";
import { clearToken, saveToken } from "./feed/config";

const granted = {
  id: "plan:p1:1:u1",
  message: "Your decision is needed on a plan",
  expires_at: "2099-01-01T00:00:00Z",
  metadata: { subject: { kind: "plan", id: "p1", revision: 1 } },
};

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

type Call = { url: string; init: RequestInit };

function host(redeem: () => Response) {
  const calls: Call[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn((url: string, init: RequestInit) => {
      calls.push({ url: String(url), init });
      if (String(url).endsWith("/v1/confirm/redeem")) return Promise.resolve(redeem());
      if (String(url).endsWith("/v1/agent/answers")) return Promise.resolve(json({ seq: 9 }));
      return new Promise<Response>(() => {}); // the streams stay open
    }),
  );
  return calls;
}

const stubMedia = () =>
  vi.stubGlobal("matchMedia", (q: string) => ({
    matches: false,
    media: q,
    addEventListener() {},
    removeEventListener() {},
  }));

describe("confirmCode", () => {
  it("reads the code only from /confirm/<code>", () => {
    expect(confirmCode("/confirm/abc-DEF_123")).toBe("abc-DEF_123");
    expect(confirmCode("/confirm/")).toBeNull();
    expect(confirmCode("/confirm")).toBeNull();
    expect(confirmCode("/")).toBeNull();
    expect(confirmCode("/confirm/a/b")).toBeNull();
    expect(CONFIRM_PREFIX).toBe("/confirm/");
  });
});

// Each test uses its own code: a spent code is remembered for the life of the page.
let n = 0;
let code = "";

describe("the /confirm/<code> route", () => {
  beforeEach(() => {
    stubMedia();
    clearToken();
    n += 1;
    code = `code-${n}-aaaaaaaaaaaa`;
    history.replaceState(null, "", `/confirm/${code}`);
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    clearToken();
    history.replaceState(null, "", "/");
  });

  it("asks for sign-in first and sends the code nowhere before that", () => {
    const calls = host(() => json(granted));
    render(<App />);
    expect(screen.getByRole("form", { name: "Sign in" })).toBeInTheDocument();
    expect(calls).toEqual([]);
  });

  it("after sign-in redeems the code and shows the trusted request card; the answer uses the answer flow", async () => {
    saveToken("tok-1");
    const calls = host(() => json(granted));
    render(<App />);
    expect(await screen.findByText("Your decision is needed on a plan")).toBeInTheDocument();
    const redeem = calls.filter((c) => c.url.endsWith("/v1/confirm/redeem"));
    expect(redeem).toHaveLength(1);
    expect(redeem[0]?.init.method).toBe("POST");
    expect(new Headers(redeem[0]?.init.headers).get("Authorization")).toBe("Bearer tok-1");
    expect(JSON.parse(String(redeem[0]?.init.body))).toEqual({ code });
    // The code is out of the address once it was used.
    expect(location.pathname).toBe("/confirm/");

    await userEvent.click(screen.getByRole("button", { name: /agree|yes|accept/i }));
    await waitFor(() => expect(calls.some((c) => c.url.endsWith("/v1/agent/answers"))).toBe(true));
    const answer = calls.find((c) => c.url.endsWith("/v1/agent/answers"));
    expect(JSON.parse(String(answer?.init.body))).toMatchObject({
      interrupt_id: "plan:p1:1:u1",
      consent: true,
    });
  });

  it("after an ended session, signing in again retries the same link", async () => {
    saveToken("tok-old");
    let status = 401;
    const calls = host(() => (status === 401 ? json({ detail: "x" }, 401) : json(granted)));
    const first = render(<App />);
    expect(await screen.findByRole("form", { name: "Sign in" })).toBeInTheDocument();
    // The host never checked the code, so it stays in the address for the next session.
    expect(location.pathname).toBe(`/confirm/${code}`);
    first.unmount();

    status = 200;
    saveToken("tok-new");
    render(<App />);
    expect(await screen.findByText("Your decision is needed on a plan")).toBeInTheDocument();
    const redeem = calls.filter((c) => c.url.endsWith("/v1/confirm/redeem"));
    expect(redeem).toHaveLength(2);
    expect(new Headers(redeem[1]?.init.headers).get("Authorization")).toBe("Bearer tok-new");
  });

  it.each([
    [404, "unknown"],
    [409, "used"],
    [410, "expired"],
    [403, "other_person"],
  ] as const)("shows a plain reason when the host answers %i", async (status, reason) => {
    saveToken("tok-1");
    host(() => json({ detail: "x" }, status));
    render(<App />);
    expect(await screen.findByText(FAILURE_TEXT[reason])).toBeInTheDocument();
    expect(screen.queryByText("Your decision is needed on a plan")).toBeNull();
  });
});
