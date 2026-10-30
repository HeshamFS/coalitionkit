// SPDX-License-Identifier: Apache-2.0
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  assertAllowedBase,
  clearToken,
  readConfig,
  resolveBase,
  saveToken,
  scrubAddress,
} from "./config";
import { openStream, postAnswer } from "./connection";

const ENV = { VITE_CK_HOST: "https://host.example", VITE_CK_ALLOWED_HOSTS: "https://alt.example" };

beforeEach(() => {
  clearToken();
  sessionStorage.clear();
});

describe("rule 1: the server origin never comes from the address", () => {
  it("ignores a host parameter that is not on the build-time allowlist", () => {
    expect(resolveBase("?host=https://evil.example", ENV)).toBe("https://host.example");
    expect(resolveBase("?host=https://host.example.evil.example", ENV)).toBe(
      "https://host.example",
    );
  });
  it("falls back to same origin when nothing is configured", () => {
    expect(resolveBase("?host=https://evil.example", {})).toBe("");
  });
  it("accepts an allowlisted override, compared by origin", () => {
    expect(resolveBase("?host=https://alt.example/some/path", ENV)).toBe("https://alt.example");
  });
  it("refuses to attach a token to any other origin", () => {
    expect(() => assertAllowedBase("https://evil.example", ENV)).toThrow(/not allowed/);
    expect(() => assertAllowedBase("https://alt.example", ENV)).not.toThrow();
    expect(() => assertAllowedBase("", ENV)).not.toThrow();
  });
  it("sends nothing when the base is not allowed", async () => {
    const fetchFn = vi.fn();
    await expect(
      postAnswer(
        { baseUrl: "https://evil.example", token: "t" },
        { interrupt_id: "i", consent: true },
        fetchFn,
      ),
    ).rejects.toThrow(/not allowed/);
    expect(() =>
      openStream({
        config: { baseUrl: "https://evil.example", token: "t" },
        path: "/v1/feed",
        onEvent: () => true,
        onStatus: () => {},
        fetchFn,
      }),
    ).toThrow(/not allowed/);
    expect(fetchFn).not.toHaveBeenCalled();
  });
});

describe("rule 2: the token never comes from the query string", () => {
  it("does not read a token parameter", () => {
    expect(readConfig("?token=leaky", ENV)).toBeNull();
    expect(sessionStorage.length).toBe(0);
  });
  it("uses the token from the sign-in step", () => {
    saveToken("signed-in");
    expect(readConfig("?token=other", ENV)).toEqual({
      baseUrl: "https://host.example",
      token: "signed-in",
    });
  });
  it("removes a token parameter from the address without using it", () => {
    history.replaceState(null, "", "/?token=leaky&keep=1");
    scrubAddress();
    expect(location.search).toBe("?keep=1");
    expect(readConfig("", ENV)).toBeNull();
  });
});

describe("an accepted answer", () => {
  it("carries the host's sequence and the owner's signature for the seal's receipt", async () => {
    const fetchFn = async () =>
      new Response(JSON.stringify({ status: "accepted", seq: 219, consent_sig: "h.p.s" }), {
        status: 200,
      });
    const result = await postAnswer(
      { baseUrl: "", token: "t" },
      { interrupt_id: "plan:p1:2:u1", consent: true },
      fetchFn,
    );
    expect(result).toEqual({ ok: true, seq: 219, signature: "h.p.s" });
  });
});
